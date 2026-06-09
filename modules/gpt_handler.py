# -*- coding: utf-8 -*-
from config.config import Config
import logging
import random
import os
import sys
import json
import urllib.request
import urllib.parse
import time
import traceback
import re
import ssl
from datetime import datetime, timedelta
from typing import Any, List
from utils.path_utils import get_config_dir, get_log_dir, get_gpt_settings_path, get_api_key_path
from utils.security_utils import deobfuscate, deobfuscate_dict_fields

# OpenAI 최신 SDK 대응
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# 로깅 설정
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format=Config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# 리소스 경로 처리 함수 추가
def resource_path(relative_path):
    """앱이 번들되었을 때와 그렇지 않을 때 모두 리소스 경로를 올바르게 가져옵니다."""
    try:
        # PyInstaller가 만든 임시 폴더에서 실행될 때
        base_path = sys._MEIPASS
    except Exception:
        # 일반적인 Python 인터프리터에서 실행될 때
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def get_app_bundle_config_path():
    """macOS 앱 번들 내 config 경로를 반환합니다."""
    try:
        if getattr(sys, 'frozen', False):
            # 빌드된 앱에서 실행 중
            exe_path = sys.executable
            # /Users/.../BlogAutomation_Mac.app/Contents/MacOS/BlogAutomation_Mac
            macos_dir = os.path.dirname(exe_path)
            # /Users/.../BlogAutomation_Mac.app/Contents/MacOS
            macos_dir = os.path.dirname(exe_path)
            
            # 1. MacOS/config 확인
            macos_config = os.path.join(macos_dir, 'config')
            if os.path.exists(macos_config):
                return macos_config
                
            # 2. Resources/config 확인 (PyInstaller 기본)
            resources_config = os.path.join(os.path.dirname(macos_dir), 'Resources', 'config')
            if os.path.exists(resources_config):
                return resources_config
            
            # 3. Frameworks/config 확인 (GitHub Actions 빌드 등)
            frameworks_config = os.path.join(os.path.dirname(macos_dir), 'Frameworks', 'config')
            if os.path.exists(frameworks_config):
                return frameworks_config

            # 4. Frameworks 루트 확인
            frameworks_root = os.path.join(os.path.dirname(macos_dir), 'Frameworks')
            if os.path.exists(os.path.join(frameworks_root, 'gpt_settings.txt')):
                return frameworks_root
                
            return macos_config
    except Exception:
        pass
    return None

class GPTHandler:
    def __init__(self, use_dummy=False):
        # GPT 핸들러를 초기화합니다.
        self.use_dummy = use_dummy
        self.settings = self._load_settings()
        
        # 🆕 크로스 플랫폼: 로그 경로 (path_utils 사용)
        try:
            self._log_path = os.path.join(get_log_dir(), 'debug.log')
        except Exception:
            # fallback
            user_home = os.path.expanduser("~")
            self._log_path = os.path.join(user_home, ".blog_automation", 'logs', 'debug.log')
        except Exception:
            # fallback: temp directory
            import tempfile
            self._log_path = os.path.join(tempfile.gettempdir(), 'blog_automation_debug.log')

        os.makedirs(os.path.dirname(self._log_path), exist_ok=True)
        
        self._session_id = "debug-session"
        self._run_id = "run-model"
        self._hypothesis_rotation = "M1"
        instance_id = id(self)

        def _dbg(location: str, message: str, data: dict | None = None, hypothesis_id: str | None = None):
            payload = {
                "sessionId": self._session_id,
                "runId": self._run_id,
                "hypothesisId": hypothesis_id or self._hypothesis_rotation,
                "location": location,
                "message": message,
                "data": {"instance_id": instance_id, **(data or {})},
                "timestamp": int(time.time() * 1000),
            }
            try:
                # #region agent log
                with open(self._log_path, "a", encoding="utf-8") as lf:
                    lf.write(json.dumps(payload, ensure_ascii=False) + "\n")
                # #endregion
            except Exception:
                pass

        self._dbg = _dbg
        
        # 모델 선택 로드
        self.selected_models = self.settings.get('selected_models', [])
        
        # 삭제된/미지원 모델 정리 (경고만 하고 유지)
        original_models = self.selected_models
        self.selected_models = []
        for m in original_models:
            if m in Config.AI_MODELS:
                self.selected_models.append(m)
            else:
                # 설정에 없어도 이름 기반으로 공급자 추론하여 허용
                inferred_provider = "gemini" if "gemini" in m.lower() else "openai"
                # 런타임에 Config에 추가 (임시 지원)
                Config.AI_MODELS[m] = {
                    "provider": inferred_provider,
                    "name": m,
                    "manual_add": True
                }
                self.selected_models.append(m)
                logger.warning(f"⚠️ 설정에 없는 모델 '{m}'이 감지되었습니다. 임시로 {inferred_provider} 공급자로 등록합니다.")
        if not self.selected_models:
            self.selected_models = [Config.GPT_MODEL]
        self.current_model_index = 0
        self.model = self.selected_models[self.current_model_index]
        import inspect
        caller = None
        try:
            stack = inspect.stack()
            if len(stack) >= 2:
                caller = f"{stack[1].filename}:{stack[1].lineno}"
        except Exception:
            caller = None
        self._dbg(
            "gpt_handler.__init__",
            "init models",
            {"selected_models": self.selected_models, "current_model_index": self.current_model_index, "caller": caller},
        )
        
        # Gemini API 키 보관
        self.gemini_api_key = self.settings.get('gemini_api_key', '') or Config.GEMINI_API_KEY
        
        try:
            api_key = None
            if self.settings and 'api_key' in self.settings and self.settings['api_key']:
                api_key = self.settings['api_key']
                logger.info("GPT 설정 파일에서 API 키를 로드했습니다.")
            else:
                # 🆕 api_key.json 파일 확인
                file_api_key = self._load_api_key_from_file()
                if file_api_key:
                    api_key = file_api_key
                    logger.info("api_key.json 파일에서 API 키를 로드했습니다.")
                else:
                    api_key = Config.GPT_API_KEY
                    logger.info("환경변수에서 API 키를 로드했습니다.")
            
            if api_key == 'your-api-key-here' or not api_key:
                logger.warning("API 키가 설정되지 않았습니다. 더미 모드로 전환합니다.")
                self.use_dummy = True
            else:
                if OpenAI:
                    self.openai_client = OpenAI(api_key=api_key)
                    logger.info("OpenAI 클라이언트 초기화 성공 (new SDK)")
                else:
                    import openai  # fallback
                    openai.api_key = api_key
                    self.openai_client = openai
                    logger.info("OpenAI 클라이언트 초기화 성공 (legacy)")
            
        except Exception as e:
            logger.error(f"OpenAI 클라이언트 초기화 중 오류 발생: {str(e)}")
            logger.warning("오류로 인해 더미 모드로 전환합니다.")
            self.use_dummy = True
        
        self.custom_prompt = self._load_custom_prompt()
        self._print_usage_status()

    def _print_usage_status(self):
        # 현재 AI 사용량 로그 출력 (초기화 여부 확인용)
        try:
            data = self._load_ai_usage()
            usage = data.get("usage", {})
            
            f_usage = usage.get("gemini-2.5-flash", 0)
            f_limit = Config.AI_MODELS["gemini-2.5-flash"]["daily_limit"]
            
            l_usage = usage.get("gemini-2.5-flash-lite", 0)
            l_limit = Config.AI_MODELS["gemini-2.5-flash-lite"]["daily_limit"]
            
            logger.info(f"📊 [AI 사용량 체크] Flash: {f_usage}/{f_limit}회 | Lite: {l_usage}/{l_limit}회 (오늘 누적)")
        except:
            pass

    def _load_settings(self):
        # GPT 설정을 로드합니다.
        default_settings = {
            'persona': '친근하고 전문적인 블로그 작성자',
            'style': '쉽고 재미있게 설명하는 스타일',
            'tone': '친근하고 대화하듯이',
            'writing_style': {
                'intro': '흥미로운 질문이나 사례로 시작',
                'body': '구체적인 예시와 함께 단계별로 설명',
                'conclusion': '핵심 내용 요약과 독자 참여 유도'
            },
            'formatting': {
                'paragraph_length': '2-3문장',
                'use_emojis': True,
                'use_bullet_points': True
            }
        }
        
        # 고정 검토 지침 (사용자가 수정할 수 없음)
        fixed_review_instructions = """글 작성 후 반드시 다음 사항을 검토해주세요:
1. 오타와 맞춤법 오류가 없는지 확인
2. 문장 간 연결이 자연스러운지 확인
3. 논리적 흐름이 일관되는지 확인
4. 불필요한 반복이나 중복 표현이 없는지 확인
5. 전체적인 글의 통일성과 완성도 검토

"""  # 끝에 줄바꿈 두 개 추가하기
        
        try:
            # 스크립트 파일의 위치를 기준으로 경로 계산
            script_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(script_dir)
            
            # 설정 파일 여러 경로 시도 (순서 중요: 글로벌 -> 앱 번들 -> 로컬)
            settings_path = get_gpt_settings_path()
            if not os.path.exists(settings_path):
                # 앱 번들 내 설정 확인
                app_bundle_config = get_app_bundle_config_path()
                if app_bundle_config:
                    settings_path = os.path.join(app_bundle_config, 'gpt_settings.txt')
                
                if not os.path.exists(settings_path):
                    # 레거시 경로 시도... (중략: 간단하게 로컬/번들 fallback)
                    settings_path = resource_path('config/gpt_settings.txt')

            if not os.path.exists(settings_path):
                settings_path = None
            
            # 설정 파일이 존재하면 로드
            if settings_path:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # 🔐 민감 데이터 복호화 시도
                    loaded_settings = deobfuscate_dict_fields(loaded_settings)
                    
                    # 모든 키를 병합하여 selected_models, gemini_api_key 등도 반영
                    default_settings.update(loaded_settings)
                
                print(f"GPT 설정 파일 로드 성공: {settings_path}")
            else:
                print(f"GPT 설정 파일을 찾을 수 없습니다")
        except Exception as e:
            print(f"GPT 설정 파일 로드 중 오류 발생: {str(e)}")
            traceback.print_exc()
        
        # 고정 검토 지침 추가
        instr = default_settings.get('instructions', '')
        if fixed_review_instructions not in instr:
            default_settings['instructions'] = instr + fixed_review_instructions
            
        return default_settings

    def _get_common_system_rules(self, platform='blog'):
        """모든 플랫폼에 적용되는 핵심 품질 및 보안 지침 (Background Rules)"""
        rules = """
[필수 준수 사항: Anti-AI Filter]
1. 가짜 이름 사용 금지: 특정 학생의 이름을 임의로 지어내지 마세요. 대신 "우리 아이들", "제자들", "수련생들"이라는 표현을 사용하세요.
2. [중요] 주제 준수 및 환각 방지: 오직 제공된 [주제(Topic)] 또는 [수련내용]에 명시된 사실만 기술하세요. 주제에 없는 구체적인 지명(예: 남대천, 양양초), 특정 기술(예: 낙법, 줄넘기), 특정 학생 이름을 절대 지어내지 마세요. 오늘 날짜는 **{current_date}**이며, 반드시 이 날짜에 기반한 계절감(봄, 여름, 가을, 겨울)을 반영하세요. 현재 계절과 맞지 않는 묘사(예: 봄인데 가을바람 언급)를 절대 금지합니다.
3. 용어의 교육적 변환: 무도 용어를 학부모가 이해하기 쉬운 교육적 가치와 연결하여 서술하세요. (예: 기술 수련 -> '자신의 몸을 보호하고 집중력을 기르는 안전 교육')
4. 가독성 최우선: 한 문장은 짧고 간결하게 작성하고, 문단 사이에는 반드시 빈 줄을 추가하세요.
5. 자기소개 금지: "관장 OOO입니다"와 같은 자기소개는 생략하고 바로 본론으로 들어가세요.
6. 따옴표 사용 절대 금지: 제목과 본문 모두에서 큰따옴표(" ")와 작은따옴표(' ')를 절대 사용하지 마세요. 강조가 필요한 경우 반드시 **[대괄호]**나 볼드체를 사용하세요.
7. 휴먼라이크 리스트: 숫자(1. 2. 3.) 형태의 나열 대신 '첫 번째는', '둘째로', '하나 더 말씀드리면' 등 사람의 대화 호흡처럼 자연스럽게 서술하세요.
8. 금지 단어: 최고, 최선, 소중한, 놀라운, 발전하는, 결론적으로, 요약하자면 등 AI가 즐겨 쓰는 표현은 피하고 담백하게 서술하세요.
"""
        if platform in ['band', 'drive_auto', 'idle']:
            rules += "5. 이모티콘 제한: 그래픽 이미지 이모티콘(😊, 🥋 등) 대신 문자 이모티콘(^^, ㅎㅎ)을 상황에 맞춰 절제하여 사용하세요.\n"
        
        if platform == 'idle':
            rules += "6. 소통 진정성: 반드시 상대방 포스팅의 본문 내용 중 핵심 키워드나 상황을 언급하여 '정성스럽게 읽고 쓴 댓글'임을 증명하세요.\n"
            rules += "7. 홍보 금지: 본인의 비즈니스 홍보나 방문 유도 멘트를 절대 사용하지 마세요.\n"
            rules += "8. 날씨 언급 절대 금지: '오늘 날씨가 화창하네요' 등 날씨 관련 표현을 절대 사용하지 마세요. 지역마다 날씨가 다르기 때문입니다.\n"
            rules += "9. 계절감 규칙: 계절 표현이 꼭 필요한 경우에만 글의 주제와 직접 연관된 간접적 표현만 허용합니다. (예: 봄나들이 글 → '봄에 딱 맞는 글이네요'는 OK, '오늘 날씨가 맑아서'는 금지)\n"
        
        return rules

    def _load_custom_prompt(self):
        # 커스텀 프롬프트를 로드합니다.
        custom_prompts = {}
        
        try:
            # 스크립트 파일의 위치를 기준으로 경로 계산
            script_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(script_dir)
            
            # 앱 번들 경로 확인
            app_bundle_config = get_app_bundle_config_path()
            
            # 여러 경로 시도 (순서 중요: 글로벌 -> 앱 번들 -> 로컬)
            possible_paths = [
                # 1. 🆕 글로벌 설정 경로 (우선순위 1위: AppData/ 표준 경로)
                os.path.join(get_config_dir(), 'custom_prompts.txt'),
                # 1.1 레거시 경로
                os.path.join(os.path.expanduser("~"), '.blog_automation', 'config', 'custom_prompts.txt'),
            ]
            
            # 2. 🆕 앱 번들 경로 (macOS 빌드된 앱)
            if app_bundle_config:
                possible_paths.append(os.path.join(app_bundle_config, 'custom_prompts.txt'))
            
            # 3. 로컬 번들 경로 (resource_path)
            possible_paths.append(resource_path('config/custom_prompts.txt'))
            
            prompts_path = None
            for path in possible_paths:
                if path and os.path.exists(path):
                    prompts_path = path
                    break
            
            # 프롬프트 파일이 존재하면 로드
            if prompts_path:
                with open(prompts_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # 파일이 비어있지 않은 경우만 JSON 파싱
                        custom_prompts = json.loads(content)
                    else:
                        print(f"커스텀 프롬프트 파일이 비어있습니다: {prompts_path}")
                print(f"커스텀 프롬프트 파일 로드 성공: {prompts_path}")
            else:
                print(f"커스텀 프롬프트 파일을 찾을 수 없습니다")
        except json.JSONDecodeError as e:
            print(f"커스텀 프롬프트 파일 JSON 파싱 오류: {str(e)}")
            print(f"파일이 비어있거나 잘못된 JSON 형식입니다. 기본 설정을 사용합니다.")
        except Exception as e:
            print(f"커스텀 프롬프트 파일 로드 중 오류 발생: {str(e)}")
            traceback.print_exc()
            
        return custom_prompts

    def _load_api_key_from_file(self):
        # api_key.json 파일에서 API 키를 로드합니다.
        try:
            # 스크립트 파일의 위치를 기준으로 경로 계산
            script_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(script_dir)
            
            # 앱 번들 경로 확인
            app_bundle_config = get_app_bundle_config_path()
            
            # 여러 경로 시도
            possible_paths = [
                # 1. 글로벌 설정
                os.path.join(get_config_dir(), 'api_key.json'),
                # 1.1 레거시
                os.path.join(os.path.expanduser("~"), '.blog_automation', 'config', 'api_key.json'),
            ]
            
            # 2. 앱 번들
            if app_bundle_config:
                possible_paths.append(os.path.join(app_bundle_config, 'api_key.json'))
            
            # 3. 로컬/리소스
            possible_paths.extend([
                os.path.join(parent_dir, 'config', 'api_key.json'),
                os.path.join(os.getcwd(), 'config', 'api_key.json'),
                'config/api_key.json',
                resource_path('config/api_key.json')
            ])
            
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, dict) and 'api_key' in data and data['api_key']:
                            key = data['api_key']
                            # 🔐 암호화된 키인 경우 복호화
                            if key.startswith("OBF:"):
                                key = deobfuscate(key[4:])
                            return key
                            
        except Exception as e:
            # print(f"API 키 파일 로드 실패: {e}")
            pass
            
        return None

    def _load_user_settings(self):
        # 사용자 설정을 로드합니다.
        user_settings = {}
        
        try:
            # 스크립트 파일의 위치를 기준으로 경로 계산
            script_dir = os.path.dirname(os.path.abspath(__file__))  # modules 디렉토리
            parent_dir = os.path.dirname(script_dir)  # naver-blog-automation 디렉토리
            
            # 앱 번들 경로 확인
            app_bundle_config = get_app_bundle_config_path()
            
            # 다양한 경로 시도 (순서 중요: 글로벌 -> 앱 번들 -> 로컬)
            possible_paths = [
                # 1. 🆕 글로벌 설정 경로 (우선순위 1위) - 사용자 홈 디렉토리
                os.path.join(os.path.expanduser("~"), '.blog_automation', 'config', 'user_settings.txt'),
            ]
            
            # 2. 🆕 앱 번들 경로 (macOS 빌드된 앱)
            if app_bundle_config:
                possible_paths.append(os.path.join(app_bundle_config, 'user_settings.txt'))
            
            # 3. 상대 경로들 및 레거시 경로들
            possible_paths.extend([
                os.path.join(parent_dir, 'config', 'user_settings.txt'),
                os.path.join(os.getcwd(), 'config', 'user_settings.txt'),
                os.path.join(script_dir, '..', 'config', 'user_settings.txt'),
                'config/user_settings.txt',
                './config/user_settings.txt',
                '../config/user_settings.txt',
                resource_path('config/user_settings.txt'),
                os.path.abspath(os.path.join(parent_dir, 'config', 'user_settings.txt'))
            ])
            
            settings_path = None
            current_dir = os.getcwd()
            print(f"🔥 현재 작업 디렉토리: {current_dir}")
            print(f"🔥 스크립트 디렉토리: {script_dir}")
            print(f"🔥 부모 디렉토리: {parent_dir}")
            
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                print(f"🔥 경로 시도: {path} -> {abs_path}")
                if os.path.exists(abs_path):
                    settings_path = abs_path
                    print(f"🔥 파일 발견: {abs_path}")
                    break
                else:
                    print(f"🔥 파일 없음: {abs_path}")
            
            # 설정 파일이 존재하면 로드
            if settings_path:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    user_settings = json.load(f)
                print(f"🔥 사용자 설정 파일 로드 성공: {settings_path}")
                print(f"🔥 로드된 first_sentence: '{user_settings.get('first_sentence', '없음')}'")
            else:
                print(f"🔥 사용자 설정 파일을 어떤 경로에서도 찾을 수 없습니다.")
                print(f"🔥 시도한 경로들:")
                for path in possible_paths:
                    print(f"🔥   - {os.path.abspath(path)}")
        except Exception as e:
            print(f"🔥 사용자 설정 파일 로드 중 오류 발생: {str(e)}")
            traceback.print_exc()
            
        return user_settings

    def _get_usage_path(self):
        # AI 사용량 기록 파일 경로
        try:
            return os.path.join(get_config_dir(), 'ai_usage.json')
        except:
            return os.path.join(self.settings.get('base_dir', '.'), 'config', 'ai_usage.json')

    def _load_ai_usage(self):
        # AI 사용량 로드
        path = self._get_usage_path()
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {"date": datetime.now().strftime("%Y-%m-%d"), "usage": {}}

    def _save_ai_usage(self, data):
        # AI 사용량 저장
        try:
            path = self._get_usage_path()
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def _check_daily_limit(self, model_name):
        # 일일 사용량 한도 체크
        model_info = Config.AI_MODELS.get(model_name, {})
        limit = model_info.get('daily_limit')
        
        if limit is None: # 제한 없음
            return True
            
        data = self._load_ai_usage()
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 날짜 변경 체크 및 초기화
        if data.get("date") != today:
            data = {"date": today, "usage": {}}
            self._save_ai_usage(data)
            
        used = data["usage"].get(model_name, 0)
        
        if used >= limit:
            logger.warning(f"⛔ {model_name} 일일 한도 초과 ({used}/{limit}) - 건너뜀")
            return False
            
        return True

    def _increment_usage(self, model_name):
        # 사용량 증가
        try:
            data = self._load_ai_usage()
            today = datetime.now().strftime("%Y-%m-%d")
            
            if data.get("date") != today:
                data = {"date": today, "usage": {}}
            
            data["usage"][model_name] = data["usage"].get(model_name, 0) + 1
            self._save_ai_usage(data)
            logger.info(f"📈 {model_name} 사용량 업데이트: {data['usage'][model_name]}회")
        except Exception as e:
            logger.error(f"사용량 업데이트 실패: {e}")

    def generate_content(self, topic, post_order=1, post_type_config=None, platform='blog', task_type=None, target_time=None):
        # 주어진 주제로 블로그 콘텐츠를 생성합니다.
        settings = self._load_settings()
        custom_prompt = self._load_custom_prompt()
        user_settings = self._load_user_settings()
        
        is_promotional = False
        promo_instructions = ""
        info_instructions = ""
        selected_models = self.selected_models
        gemini_api_key = self.gemini_api_key
        if post_type_config:
            is_promotional = post_type_config.get("is_promotional", False)
            promo_instructions = post_type_config.get("promotional_instructions", "")
            info_instructions = post_type_config.get("informational_instructions", "")
            sel = post_type_config.get("selected_models", [])
            if sel:
                selected_models = sel
            if post_type_config.get("gemini_api_key"):
                gemini_api_key = post_type_config.get("gemini_api_key")
        
        # 타입별 지침 합성
        type_instructions = promo_instructions if is_promotional else info_instructions
        
        # 🟢 플랫폼별 맞춤 지침이 있으면 그것을 사용, 없으면 기존 블로그 지침 사용
        system_message = post_type_config.get('custom_system') if post_type_config and post_type_config.get('custom_system') else f"""당신은 블로그 작성자입니다.
페르소나: {settings['persona']}
지침: {settings['instructions']}
스타일: {settings['style']}
추가 타입 지침: {type_instructions}
금지: HTML 태그 사용 금지 (<h2>, <p> 등), 자기소개(OOO입니다) 금지
필수: 문단 사이에는 반드시 빈 줄을 추가하여 가독성을 높이세요.
필수: 문장 간 띄어쓰기와 맞춤법을 정확히 지키세요.
"""
        
        # 🟢 Brave Search (실시간 정보 검색) - 모든 플랫폼(블로그/밴드/카페) 공통 적용
        if topic:
            search_results = self._search_brave(topic)
            if search_results:
                search_hint = f"\n\n[System: 실시간 검색 결과 (Brave Search)]\n다음 최신 정보를 참고하여 글을 풍성하게 작성하세요:\n{search_results}\n(검색된 내용을 자연스럽게 본문에 녹여내세요.)"
                system_message += search_hint
        

        # 🟢 현재 날짜/시간 정보 주입 (AI가 '오늘'을 알 수 있게 함)
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        now = datetime.now()
        
        # 🟢 타임머신 기능: 예약 시간(target_time)이 있으면 그 시간을 기준으로 설정
        if target_time:
            try:
                target_hour, target_minute = map(int, target_time.split(':'))
                target_dt = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
                # 만약 타겟 시간이 현재보다 과거라면 내일로 간주
                if target_dt < now:
                    target_dt += timedelta(days=1)
                
                # 기준 시간 업데이트
                now = target_dt
            except Exception as e:
                logger.warning(f"타겟 시간 파싱 실패: {target_time}, error: {e}")

        weekday_str = weekdays[now.weekday()]
        now_str = now.strftime(f"%Y년 %m월 %d일 ({weekday_str}) %H시 %M분")
        
        if target_time:
            system_message += f"\n[작성 기준 시간(예약): {now_str}]\n"
            system_message += "\n[중요: 이 글은 위 '작성 기준 시간'에 업로드될 예약 글입니다. 현재 시간이 아닌 작성 기준 시간(아침/점심/저녁)에 맞춰 인사를 건네세요.]\n"
        else:
            system_message += f"\n[현재 시간: {now_str}]\n"
        
        # 🟢 [Smart Hooks] 플랫폼별/시간대별 지능형 훅 주입 (Phase 2)
        # 모든 플랫폼(blog, cafe, band, drive_auto 등)에 대해 지능형 훅 적용 시도
        if platform in ('blog', 'cafe', 'band', 'drive_auto', 'manual_topic'):
            try:
                # 1. 예약 포스팅 여부 확인 (내일 아침 인사를 위해)
                is_forecast = self._check_is_forecast(target_time)
                
                # 2. 작업 타입 결정 (오전/정규/마감)
                effective_task_type = task_type
                if not effective_task_type or effective_task_type == 'regular':
                    current_hour = now.hour # 🟢 타임머신 반영된 now 사용
                    if current_hour < 11:
                        effective_task_type = 'morning'
                    elif current_hour >= 18:
                        effective_task_type = 'closing'
                
                weather_loc = settings.get('weather_location', '')
                
                # 3. 훅 생성 및 주입
                # [상시 날씨 주입] 모든 시간대에 현재 날씨 정보를 기본 제공하여 할루시네이션 방지
                weather_hook = ""
                if weather_loc:
                    weather_hook = self._build_weather_hook_message(weather_loc, is_forecast, platform)
                    if weather_hook:
                        system_message += weather_hook
                
                # 4. 시간대별 추가 훅 (뉴스 등)
                if effective_task_type != 'morning':
                    # 오후/저녁: 뉴스 훅 추가 (날씨와 함께 제공 가능)
                    news_hook = self._build_news_hook_message(platform)
                    if news_hook:
                        system_message += news_hook
                    
                    # 저녁(마감) 포스팅 시 하단에 내일 날씨 꿀팁 추가
                    if effective_task_type == 'closing' and weather_loc:
                        closing_weather = self._build_closing_weather_message(weather_loc)
                        if closing_weather:
                            system_message += closing_weather

            except Exception as e:
                logger.warning(f"⚠️ 지능형 훅 주입 실패 (platform={platform}): {e}")

        base_prompt = f"""주제: {topic}

다음 형식으로 작성:
[제목]
(제공된 뉴스나 날씨 정보가 있다면 이를 적극 활용하여 클릭유도형 제목 작성. **[주의] 만약 아래 제공된 '날씨 정보'에 구체적인 소식(비, 눈, 맑음 등)이 없다면 절대 임의로 상상하여 "비가 온다"거나 "눈이 내린다"고 작성하지 마세요.** 데이터가 없으면 주제에만 집중하여 작성하세요.)

[본문]
(1문단: 제공된 뉴스/날씨 정보가 있을 경우 해당 데이터로 흥미를 유발하며 시작 -> 2문단부터: 본론 주제)
...

규칙:
- 마크다운 헤더만 사용(##, ###), HTML 태그 금지
- 친절하고 다정한 말투 (학부모님께 이야기하듯 세심하게)
- 리스트나 순차적 설명 시 '1., 2.' 대신 '하나., 둘., 셋.' 또는 '첫째로, 둘째로' 같은 한글 표기를 사용하여 부드럽게 표현할 것
- 자연스러운 흐름, 실용 팁 포함
- 깔끔한 마무리와 명언 포함
- **시간대 인사 금지** (좋은 아침입니다 등) -> 뉴스/날씨로 바로 시작
- **[경고] 날씨 정보 누락 시**: 아래 [System: 날씨 정보] 섹션이 없거나 비어있다면, 절대 "비", "미세먼지", "추위" 등 기상 상태를 언급하지 마세요. 대신 "활기찬 수련 시간", "오늘의 운동 팁" 등으로 시작하세요.
"""
        user_prompt = post_type_config.get('custom_user') if post_type_config and post_type_config.get('custom_user') else (f"{custom_prompt}\n\n{base_prompt}" if custom_prompt else base_prompt)
        
        # 모델 순회 (체크된 순서대로 라운드 로빈)
        if not selected_models:
            selected_models = [Config.GPT_MODEL]
        last_error = None
        total = len(selected_models)
        start_idx = self.current_model_index if self.current_model_index < total else 0
        self._dbg(
            "gpt_handler.generate_blog_post",
            "loop start",
            {"selected_models": selected_models, "current_model_index": self.current_model_index, "start_idx": start_idx, "total": total},
        )
        for step in range(total):
            model_idx = (start_idx + step) % total
            model_name = selected_models[model_idx]

            # 🟢 일일 한도 체크
            if not self._check_daily_limit(model_name):
                logger.info(f"{model_name} 한도 초과로 스킵")
                continue

            provider = Config.AI_MODELS.get(model_name, {}).get("provider", "openai")
            logger.info(f"모델 시도 {step+1}/{total}: {model_name} ({provider})")
            try:
                if provider == "openai":
                    # OpenAI 최신 SDK 사용
                    resp = self.openai_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=2000,
                        top_p=0.9,
                        frequency_penalty=0.5,
                        presence_penalty=0.5
                    )
                    content = resp.choices[0].message.content.strip()
                elif provider == "gemini":
                    content = self._generate_with_gemini(model_name, system_message, user_prompt, api_key=gemini_api_key)
                else:
                    logger.warning(f"{model_name} 공급자 {provider}는 지원되지 않습니다. 건너뜀.")
                    continue
                title, body = self._parse_content(content)
                # 🟢 짧은 글 플랫폼은 블로그용 검증 건너뛰기
                if platform not in ['manual_topic', 'drive_auto', 'idle']:
                    if not self._validate_content(body):
                        raise ValueError("검증 실패")
                body = self._format_content_for_mobile(body)
                body = self._enhance_formatting(body)
                
                # 플랫폼별 첫 문장 추가
                first_sentence = ""
                if platform == 'blog':
                    first_sentence = user_settings.get('blog_first_sentence', user_settings.get('first_sentence', '')).strip()
                elif platform == 'cafe':
                    first_sentence = user_settings.get('cafe_first_sentence', '').strip()
                elif platform == 'band':
                    first_sentence = user_settings.get('band_first_sentence', '').strip()
                    if not first_sentence:
                        first_sentence = user_settings.get('first_sentence', '').strip()
                    if first_sentence:
                        logger.info(f"밴드 포스팅에 사용자 설정 첫 문장 적용: {first_sentence[:30]}...")
                        print(f"🔥 밴드 첫 문장 적용! ({len(first_sentence)}자)")
                    else:
                        print(f"🔥 밴드 첫 문장을 찾을 수 없습니다. (band_first_sentence/first_sentence 없음)")
                elif platform in ['drive_auto', 'manual_topic']:
                    # 🟢 드라이브 자동포스팅/수동주제 포스팅은 밴드에 올라가므로 밴드 첫 문장 사용
                    first_sentence = user_settings.get('band_first_sentence', '').strip()
                    if not first_sentence:
                        first_sentence = user_settings.get('first_sentence', '').strip()
                    if first_sentence:
                        logger.info(f"드라이브 자동포스팅에 밴드 첫 문장 적용: {first_sentence[:30]}...")
                        print(f"🔥 드라이브/수동 밴드 첫 문장 적용! ({len(first_sentence)}자)")
                    else:
                        print(f"🔥 드라이브/수동 밴드 첫 문장을 찾을 수 없습니다.")
                
                if first_sentence:
                     body = f"{first_sentence}\n\n{body}"
                
                # 플랫폼별 슬로건(마지막 문구) 추가
                slogan = ""
                if platform == 'blog':
                    slogan = user_settings.get('blog_slogan', user_settings.get('slogan', '')).strip()
                elif platform == 'cafe':
                    slogan = user_settings.get('cafe_slogan', '').strip()
                elif platform == 'band':
                    slogan = user_settings.get('band_slogan', '').strip()
                    if slogan:
                        print(f"🔥 밴드 슬로건 적용! ({len(slogan)}자)")
                    else:
                        print("🔥 밴드 슬로건 없음!")
                elif platform in ['drive_auto', 'manual_topic']:
                    # 🟢 드라이브 자동포스팅/수동주제 포스팅은 밴드 슬로건 사용
                    slogan = user_settings.get('band_slogan', '').strip()
                
                if slogan:
                    body = f"{body}\n\n{slogan}"
                
                # 🟢 플랫폼별 고정 태그 추가 (밴드)
                if platform in ['band', 'drive_auto', 'manual_topic']:
                    # 밴드는 blog_tags를 공용으로 사용하거나, 따로 없으면 blog_tags를 fallback으로 사용
                    band_hashtags = settings.get('band_hashtags', user_settings.get('blog_tags', '')).strip()
                    print(f"🔥 밴드 태그 추출 시도: {band_hashtags[:30]}...")
                    if band_hashtags:
                        # 콤마나 띄어쓰기로 구분된 태그 파싱
                        tags = [t.strip() for t in band_hashtags.replace(',', ' ').split() if t.strip()]
                        # 앞의 5개만 추출 후 # 붙이기
                        fixed_tags = [t if t.startswith('#') else f"#{t}" for t in tags[:5]]
                        if fixed_tags:
                            body = f"{body}\n\n" + " ".join(fixed_tags)
                            print(f"🔥 밴드 태그 적용: {' '.join(fixed_tags)}")
                
                # 성공 시 다음 호출은 그다음 모델부터 시작
                self._increment_usage(model_name)  # 🟢 사용량 증가
                self.current_model_index = (model_idx + 1) % total
                self._dbg(
                    "gpt_handler.generate_blog_post",
                    "success",
                    {"used_model": model_name, "next_index": self.current_model_index, "step": step, "total": total},
                )
                return {"title": title, "content": body, "model": model_name}
            except Exception as e:
                last_error = e
                logger.error(f"{model_name} 실패: {e}")
                self._dbg(
                    "gpt_handler.generate_blog_post",
                    "fail",
                    {"failed_model": model_name, "step": step, "error": str(e)},
                )
                continue
        
        raise RuntimeError(f"모든 선택된 모델 실패: {last_error}")

    def generate_blog_content(self, topic, post_order=1, post_type_config=None):
        # 기존 블로그 콘텐츠 생성 (alias)
        return self.generate_content(topic, post_order, post_type_config, platform='blog')

    def generate_platform_content(self, topic, platform='blog', task_type='regular', target_time=None, news_pool=None, previous_news=None):
        # 플랫폼별 맞춤형 콘텐츠 생성
        settings = self._load_settings() # settings를 먼저 로드
        
        band_instr = settings.get('band_instructions', "밴드 멤버들과 소통하기 좋은 친근하고 간결한 스타일로 작성해주세요. (공백 포함 300~400자 이내)")
        if platform == 'band':
            band_instr += "\n[밴드 전용 필수 지침]\n1. 모바일 가독성을 위해 문단과 문단 사이에는 반드시 빈 줄을 넣어 간격을 띄워주세요.\n2. 학부모님들이 보는 공간이므로 무의미한 체육관 홍보, 종목 어필, 상업적 광고는 절대 금지합니다. 오직 학부모님들이 관심 가질 만한 순수하고 유익한 정보만 담아주세요.\n3. 포스팅 내용 작성을 모두 마친 후, 맨 마지막 줄에 오늘 수련 내용과 어울리는 해시태그 5개를 반드시 포함하세요. (형식: #태그1 #태그2)"
            # '아침'이라는 단어가 포함되어 있고 태스크 타입이 아침이 아니면, '아침' 관련 문구 무력화
            if '아침' in band_instr and task_type not in ['morning', 'regular_morning']:
                 band_instr = band_instr.replace('아침', '일상') # 아침 -> 일상으로 단순 치환
                 band_instr += "\n(주의: 이 지침의 '아침' 관련 내용은 무시하고, 아래 [필수 요구사항]의 시간대를 따르세요.)"

        # 플랫폼별 시스템 메시지 조정 (사용자 설정 우선)
        platform_instructions = {
            'blog': settings.get('instructions', "자세하고 정보가 풍부한 블로그 포스트 스타일로 작성해주세요."),
            'band': band_instr,
            'cafe': settings.get('cafe_instructions', "카페 게시판 성격에 맞는 예의 바르고 정보 공유적인 스타일로 작성해주세요."),
            'idle': settings.get('idle_instructions', (
                "이웃의 글에 공감하며 따뜻하게 소통하는 댓글을 작성해주세요.\n"
                "- 분량: 공백 포함 50~80자 내외 (2문장 정도)\n"
                "- 구조: [상대 내용 공감/칭찬] + [핵심 키워드 언급] + [오늘을 응원하는 마무리 인사]"
            )),
            # 🟢 드라이브 자동포스팅 전용 지침 (백그라운드 고정 지침)
            'drive_auto': (
                "당신은 체육관 관장으로서 매 수련 시간의 모습을 기록합니다.\n"
                "- 분량: 공백 포함 150~250자 내외로 매우 짧게 작성 (가독성 최우선)\n"
                "- 말투: 신뢰의 '~합니다'(60%)와 다정한 '~해요/죠?'(40%) 비율 준수\n"
                "- 이모티콘: 그래픽 이모티콘 절대 금지. 텍스트 웃음( ^^ )만 전체에서 딱 1번 사용\n"
                "- 구조: [타이틀: {부수} 수련 모습] -> [본문: 교육 가치 중심 2문장] -> [맺음: 사진/영상 확인 권유]"
            ),
            # 🟢 수동 주제 포스팅 전용 지침
            'manual_topic': "네이버 밴드에 올리는 짧고 따뜻한 글을 작성하세요. 공백 포함 250~350자 내외로 간결하게."
        }
        
        # task_type별 시간대 지침 (더 명확하고 구체적으로)
        task_instructions = {
            'morning': (
                "[현재 시간대: 오전/아침]\n"
                "- 독자들에게 아침 인사를 건네며 시작하세요. (구체적인 문구는 톤앤매너에 맞게 자유롭게 변형 가능)\n"
                "- 활기차고 긍정적인 하루 시작을 응원하세요.\n"
                "- (주의: 저녁/마무리 인사는 절대 금지)"
            ),
            
            'regular': (
                "[현재 시간대: 오후/낮]\n"
                "- 독자들에게 오후 인사를 건네며 시작하세요. (구체적인 문구는 톤앤매너에 맞게 자유롭게 변형 가능)\n"
                "- 주제와 관련된 유익한 정보를 중심으로 작성하세요.\n"
                "- (주의: 아침/저녁 인사가 혼재되지 않도록 주의)"
            ),
            
            'closing': (
                "[현재 시간대: 저녁/밤]\n"
                "- 독자들에게 하루 마무리 인사를 건네며 시작하세요. (구체적인 문구는 톤앤매너에 맞게 자유롭게 변형 가능)\n"
                "- 차분하고 따뜻하게 하루를 정리하고 위로하세요.\n"
                "- (주의: 아침/시작 인사는 절대 금지)"
            )
        }
        
        # 🟢 블로그/드라이브 자동포스팅/수동주제포스팅/이웃소통은 시간대 인사 불필요
        if platform in ['blog', 'drive_auto', 'manual_topic', 'idle']:
            time_instruction = ""  # 시간대 인사 없음
        else:
            time_instruction = task_instructions.get(task_type, task_instructions['regular'])
        
        system_message = (
            f"당신은 {platform} 운영자입니다.\n"
            f"인성 교육 가치: {settings.get('persona', '기본 페르소나')}\n"
            f"스타일: {settings['style']}\n\n"
            f"### [플랫폼별 필수 지침 (사용자 설정)]\n"
            f"{platform_instructions.get(platform, '')}\n\n"
            f"### [기본 시스템 수칙]\n"
            f"{self._get_common_system_rules(platform)}\n"
            f"{time_instruction}\n"
        )

        # 🟢 밴드 포스팅: 시간대별 실시간 정보 주입
        if platform == 'band':
            weather_loc = settings.get('weather_location', '')
            
            # --- 아침형: 날씨 + 기온 + 미세먼지 ---
            if task_type == 'morning' and weather_loc:
                # 예약인지 실시간인지 판단
                is_forecast = False
                if target_time:
                    from datetime import datetime as dt_cls
                    try:
                        if isinstance(target_time, str):
                            t = dt_cls.strptime(target_time, "%H:%M")
                            # 현재 시간 기준으로 동일한 시/분의 datetime 객체 생성
                            target_dt = datetime.now().replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
                            
                            # ✨ [Fix] 스케줄러가 정각에 실행될 때 미세한 시간차로 오늘로 인식되는 문제 방지
                            # 현재 시간보다 5분 이상 과거인 시간(ex: 현재 14:00인데 target이 07:00)이라면 내일로 간주
                            if target_dt < datetime.now() - timedelta(minutes=5):
                                target_dt += timedelta(days=1)
                                is_forecast = True
                        else:
                            target_dt = target_time
                            if target_dt.date() > datetime.now().date():
                                is_forecast = True
                    except Exception:
                        is_forecast = False
                
                # 🟢 기상청 1순위 → 네이버 폴백
                weather_info = self._get_kma_weather(weather_loc, forecast=is_forecast)
                if not weather_info:
                    weather_info = self._get_naver_weather(weather_loc, forecast=is_forecast)
                if weather_info:
                    if is_forecast:
                        weather_label = "오늘 오전 날씨 (발행 시점 기준)"
                        weather_guide = (
                            "(위 날씨 정보는 글이 발행되는 시점의 날씨입니다. "
                            "'내일'이라는 표현을 절대 사용하지 말고, **'오늘'** 또는 **'오늘 아침'**으로 표현하세요. "
                            "예: '오늘 아침은 영하 3도로 춥습니다, 따뜻하게 입혀 보내주세요', "
                            "'오늘 미세먼지가 나쁨이니 마스크 준비해주세요' 등 구체적 언급 필수)"
                        )
                    else:
                        weather_label = "실시간 날씨 정보 (네이버)"
                    
                    system_message += (
                        f"\n[System: {weather_label} (기상청/네이버)]\n"
                        f"{weather_info}\n"
                        "(위 날씨 정보를 바탕으로 회원들에게 건넬 따뜻한 인사말과 옷차림/건강 팁을 작성하세요. "
                        "⚠️ 절대 위 데이터에 없는 주간 예보나 다른 날짜의 날씨를 지어내지 마세요.)\n"
                        "[!!! 필수 규칙 !!!]\n"
                        "날씨 인사말은 1문단으로 짧게 끝내고, **반드시 빈 줄(엔터 2번)을 넣어 완전히 문단을 나눈 뒤** 2문단부터 본론 주제(수련 내용 등)를 작성하세요.\n"
                        "날씨 인사와 수련 내용을 억지로 한 문장에 섞어 쓰지 마세요."
                    )


            # --- 오후형 / 저녁형: 뉴스, 이슈, 실검 등 ---
            elif task_type in ('regular', 'closing'):
                # 🟢 방안 A: 외부에서 분배된 뉴스 풀 우선 사용
                trending_info = news_pool if news_pool else self._get_trending_topics()
                if trending_info:
                    if task_type == 'regular':
                        topic_guide = (
                            "(위 최신 뉴스/이슈 중 하나를 골라 자연스럽게 글의 시작으로 활용하세요. "
                            "예: '요즘 OOO가 화제인데요', '오늘 뉴스에서 이런 소식을 봤습니다' 등. "
                            "주변 사람들과 대화할 때 아는 척 할 수 있는 정도의 가벼운 정보로 시작하세요.)"
                        )
                    else:
                        topic_guide = (
                            "(위 최신 뉴스/이슈 중 하나를 골라 자연스럽게 글의 시작으로 활용하세요. "
                            "예: '오늘 하루 이런 소식이 있었는데요', '저녁 식사 자리에서 나눌 만한 이야기' 등. "
                            "가족이나 동료와 대화할 때 유익한 정보로 시작하세요.)"
                        )
                    # 🟢 방안 C: 이전 뉴스 컨텍스트 전달 (중복 방지)
                    dedup_guide = ""
                    if previous_news:
                        dedup_guide = (
                            f"\n\n[중요: 이전 포스팅에서 이미 다룬 뉴스]\n"
                            f"{previous_news}\n"
                            f"(위 뉴스는 이미 이전 포스팅에서 사용했으므로, 반드시 다른 뉴스를 선택하세요. "
                            f"같은 내용을 반복하면 독자가 지루해합니다.)"
                        )
                    system_message += (
                        f"\n[System: 오늘의 뉴스/이슈/트렌드]\n"
                        f"{trending_info}\n"
                        f"{topic_guide}"
                        f"{dedup_guide}\n"
                        "[⚠️ 뉴스 인용 안전 규칙]\n"
                        "- 정치(여당/야당/대통령 등), 종교, 범죄, 선정적, 자극적인 내용은 절대 인용하지 마세요.\n"
                        "- 만약 검색된 뉴스가 모두 그런 내용이라면, 차라리 '오늘의 생활 건강 팁'으로 주제를 변경하세요.\n"
                        "[!!! 필수 규칙 !!!]\n"
                        "인사말/도입부는 1문단으로 짧게 끝내고, **반드시 빈 줄(엔터 2번)을 넣어 완전히 문단을 나눈 뒤** 2문단부터 본론 주제(수련 내용 등)를 작성하세요.\n"
                        "도입부와 수련 내용을 억지로 한 문장에 섞어 쓰지 마세요."
                    )
                    
                    # 🟢 밴드 오후/저녁에도 실시간 날씨 참고 정보 제공 (할루시네이션 방지)
                    if weather_loc:
                        weather_info_ref = self._get_kma_weather(weather_loc)
                        if not weather_info_ref:
                            weather_info_ref = self._get_naver_weather(weather_loc)
                        if weather_info_ref:
                            system_message += (
                                f"\n[System: 참고 - 현재 {weather_loc} 실시간 날씨 (기상청)]\n"
                                f"{weather_info_ref}\n"
                                "⚠️ 위 날씨는 참고용입니다. 날씨를 언급할 경우 반드시 위 데이터 기준으로만 작성하세요.\n"
                                "절대 위 데이터에 없는 주간 예보나 다른 날짜 날씨를 지어내지 마세요."
                            )

        # 🟢 블로그 / 카페: 시간대별 뉴스/날씨 훅 (밴드와 동일 전략)
        if platform in ('blog', 'cafe'):
            weather_loc = settings.get('weather_location', '')
            
            # --- 오전형: 날씨 정보로 시작 ---
            if task_type == 'morning' and weather_loc:
                # 예약인지 실시간인지 판단 (밴드와 동일 로직)
                is_forecast = False
                if target_time:
                    from datetime import datetime as dt_cls
                    try:
                        if isinstance(target_time, str):
                            t = dt_cls.strptime(target_time, "%H:%M")
                            # 현재 시간 기준으로 동일한 시/분의 datetime 객체 생성
                            target_dt = datetime.now().replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
                            
                            # ✨ [Fix] 스케줄러가 정각에 실행될 때 미세한 시간차로 오늘로 인식되는 문제 방지
                            # 현재 시간보다 5분 이상 과거인 시간(ex: 현재 14:00인데 target이 07:00)이라면 내일로 간주
                            if target_dt < datetime.now() - timedelta(minutes=5):
                                target_dt += timedelta(days=1)
                                is_forecast = True
                        else:
                            target_dt = target_time
                            if target_dt.date() > datetime.now().date():
                                is_forecast = True
                    except Exception:
                        is_forecast = False
                
                # 🟢 기상청 1순위 → 네이버 폴백
                weather_info = self._get_kma_weather(weather_loc, forecast=is_forecast)
                if not weather_info:
                    weather_info = self._get_naver_weather(weather_loc, forecast=is_forecast)
                if weather_info:
                    if is_forecast:
                        weather_label = "내일 오전 발행용 계절 및 시즌 배경 정보"
                        current_date = datetime.now() + timedelta(days=1)
                        month = current_date.month
                        season_info = f"{month}월의 계절감, 시즌 이슈(입학, 개학, 환절기 등)"
                        weather_guide = (
                            f"(위 날씨 정보는 '내일' 발행용입니다. 기상청 정보가 부정확할 수 있으므로, "
                            f"**구체적인 기온보다는 {season_info}** 등 자연스러운 계절 변화나 일상 소식으로 시작하세요. "
                            f"예: '벌써 {month}월이라 꽃샘추위가 있네요', '새학기가 시작되는 계절입니다' 등.)"
                        )
                    else:
                        weather_label = "실시간 날씨 정보 (네이버)"
                    
                    system_message += (
                        f"\n[System: {weather_label} (기상청/네이버)]\n"
                        f"{weather_info}\n"
                        "(위 날씨 정보를 바탕으로 글의 도입부를 작성하세요. "
                        "⚠️ 절대 위 데이터에 없는 주간 예보나 다른 날짜의 날씨를 지어내지 마세요.)\n"
                        "[!!! 필수 규칙 !!!]\n"
                        "글의 첫 문단(도입부)은 반드시 위의 날씨 정보로 시작하세요.\n"
                        "그리고 자연스럽게 본론 주제로 연결하세요."
                    )
            
            # --- 오후형 / 저녁형: 뉴스/이슈로 시작 (날씨 불필요) ---
            elif task_type in ('regular', 'closing'):
                trending_info = self._get_trending_topics()
                if trending_info:
                    if task_type == 'regular':
                        topic_guide = (
                            "(위 최신 뉴스/이슈 중 하나를 골라 자연스럽게 글의 시작으로 활용하세요. "
                            "예: '요즘 OOO가 화제인데요', '오늘 뉴스에서 이런 소식을 봤습니다' 등.)"
                        )
                    else:
                        topic_guide = (
                            "(위 최신 뉴스/이슈 중 하나를 골라 자연스럽게 글의 시작으로 활용하세요. "
                            "예: '오늘 하루 이런 소식이 있었는데요', '저녁에 나눌 만한 이야기' 등.)"
                        )
                    system_message += (
                        f"\n[System: 오늘의 뉴스/이슈/트렌드]\n"
                        f"{trending_info}\n"
                        f"{topic_guide}\n"
                        "[!!! 필수 규칙 !!!]\n"
                        "글의 첫 문단(도입부)은 반드시 위의 뉴스/이슈 중 하나로 시작하세요.\n"
                        "그리고 자연스럽게 본론 주제로 연결하세요."
                    )
                    
                    # 🟢 저녁 포스팅용 '내일의 준비' 특급 팁 추가 (관장님 요청사항)
                    if task_type == 'closing' and weather_loc:
                        tomorrow_weather = self._get_kma_weather(weather_loc, forecast=True)
                        if tomorrow_weather:
                            system_message += (
                                f"\n[System: 내일의 준비 (저녁형 포스팅용 필수 팁)]\n"
                                f"{tomorrow_weather}\n"
                                "(위 내일 날씨 정보를 참고하여, 글 마무리 단계에서 이웃들에게 세심한 배려를 보여주세요. "
                                "예: '내일은 비 소식이 있으니 우산을 챙기세요', '아침 기온이 뚝 떨어진다고 하니 바람막이를 입으세요' 등.)"
                            )
                    
                    # 🟢 카페 오후/저녁에도 실시간 날씨 참고 정보 제공 (할루시네이션 방지)
                    if weather_loc:
                        weather_info_ref = self._get_kma_weather(weather_loc)
                        if not weather_info_ref:
                            weather_info_ref = self._get_naver_weather(weather_loc)
                        if weather_info_ref:
                            system_message += (
                                f"\n[System: 참고 - 현재 {weather_loc} 실시간 날씨 (기상청)]\n"
                                f"{weather_info_ref}\n"
                                "⚠️ 위 날씨는 참고용입니다. 날씨를 언급할 경우 반드시 위 데이터 기준으로만 작성하세요.\n"
                                "절대 위 데이터에 없는 주간 예보나 다른 날짜 날씨를 지어내지 마세요."
                            )

        
        # 🟢 플랫폼별 user_prompt 분리
        if platform == 'blog':
            user_prompt = (
                f"주제: {topic}\n\n"
                "✅ [블로그 상위노출 및 고품질 정보성 글쓰기 전략]\n"
                f"1. **콘텐츠 길이**: 독자가 충분한 정보를 얻을 수 있도록 **총 공백 포함 1,200 ~ 1,300자** 내외로 풍성하게 작성하세요.\n"
                f"2. **현지 밀착형 도입**: 양양의 계절감, 풍경, 날씨로 시작하여 학부모님의 고민을 자연스럽게 언급하며 독자의 공감을 이끌어내세요.\n"
                f"3. **전문성 및 친절한 설명**: 전문 용어(예: 근방추, 성장판, 코어 등)를 반드시 포함하되, 반드시 **[쉽게 말해 ~라는 뜻입니다]**와 같은 친절한 설명을 덧붙이세요.\n"
                "4. **상위노출(Exposure)**: 주제 키워드가 첫 문단과 본문 곳곳에 자연스럽게 포함되도록 하세요.\n"
                "5. **소통 유도 및 제안**: 글 마지막에 오늘 밤 아이에게 해줄 수 있는 작은 격려나 신체 활동을 구체적으로 제안하며 마무리하세요.\n\n"
                "✅ [필수 금기 사항]\n"
                "- 제목과 본문에 **따옴표(\" \", ' ') 사용을 절대 금지**합니다.\n"
                "- 숫자 리스트(1. 2.) 대신 사람의 호흡으로 서술하세요.\n\n"
                "반드시 아래 형식을 지켜서 출력해:\n\n"
                "[제목]\n"
                "(따옴표 없이, 뉴스/날씨 + 주제를 결합하여 호기심을 자극하는 제목)\n\n"
                "[본문]\n"
                "(도입: 양양 현지 이야기 -> 본문: 전문 정보 + 쉬운 설명 -> 결론: 부모님을 위한 실천 팁)\n\n"
            )
        elif platform == 'drive_auto':
            # 🟢 드라이브 자동포스팅 + 수동주제포스팅 전용
            # topic에서 폴더명(시간대) 추출 시도
            folder_hint = ""
            training_content = ""
            
            #  종목 설정값 가져오기 (기본값: 합기도)
            gym_sport = settings.get('gym_sport', '합기도')
            
            if "[" in topic and "]" in topic:
                folder_hint = topic.split("]")[0].replace("[", "").strip()
            
            # "수련내용:" 부분 추출
            if "수련내용:" in topic:
                training_content = topic.split("수련내용:")[-1].strip()
            
            # 캠프활동/특별활동 여부 확인
            is_special_activity = any(keyword in folder_hint.lower() or keyword in training_content.lower() 
                                      for keyword in ['캠프', '키즈카페', '견학', '체험', '행사', '대회'])
            
            if is_special_activity:
                # 캠프/특별활동용 프롬프트
                user_prompt = (
                    f"주제: {topic}\n\n"
                    f"### 오늘의 활동 내용:\n"
                    f"{training_content if training_content else '(활동내용 없음)'}\n\n"
                    "위 내용을 바탕으로 밴드 글을 작성해줘.\n\n"
                    "[제목]\n"
                    f"(짧고 따뜻한 제목, \"{training_content}\"를 언급)\n\n"
                    "[본문]\n"
                    "(200~300자 내외로 간결하게 작성)\n\n"
                    "- 특별활동 글쓰기 규칙:\n"
                    f"1. **\"{training_content}\"가 핵심 주제** - 이 활동에 대해서만 작성\n"
                    "2. 운동/수련 관련 내용(셔틀런, 스트레칭, 품새, 격파 등)은 언급하지 마세요 (오늘은 특별활동입니다)\n"
                    "3. 아이들이 즐겁게 활동하는 모습 묘사\n"
                    "4. 키즈카페면 -> 재미있는 놀이, 친구들과의 교류\n"
                    "5. 캠프면 -> 새로운 경험, 협동심, 즐거운 추억\n"
                    "6. 학부모님께 감사 인사\n"
                    "7. 이모지는 1~2개만 사용\n"
                    "8. 맞춤법: 캠프(O) 갬프(X), 키즈카페(O)\n"
                    f"9. 이 체육관의 종목은 {gym_sport}입니다 (다른 종목 용어 사용 금지)\n"
                    "10. **어투: \"~습니다\", \"~했습니다\", \"~였습니다\" 형식 사용 (해요체 금지)**\n\n"
                    "[참고] 올바른 예시:\n"
                    f"\"오늘 {folder_hint} 친구들과 함께 {training_content}을 다녀왔습니다. 아이들이 즐겁게 활동했으며, 좋은 추억을 만들었습니다. 참여해주신 학부모님들께 감사드립니다.\"\n"
                )
            else:
                # 일반 수련용 프롬프트
                user_prompt = (
                    f"주제: {topic}\n\n"
                    f"### 오늘의 수련 내용 (핵심 주제):\n"
                    f"{training_content if training_content else '(수련내용 없음)'}\n\n"
                    "위 주제에 맞춰서 수련 사진/영상과 함께 올릴 밴드 글을 작성해줘.\n\n"
                    f"[주의] 중요: 이 체육관의 주 종목은 **{gym_sport}**입니다!\n\n"
                    "[제목]\n"
                    f"(짧고 따뜻한 제목, \"{folder_hint}\" 시간대와 오늘 수련 내용을 언급)\n\n"
                    "[본문]\n"
                    "(200~300자 내외로 간결하게 작성)\n\n"
                    "[중요] 중요 규칙:\n"
                    f"1. **오늘의 수련 내용({training_content})을 반드시 본문에서 구체적으로 언급**\n"
                    "2. 수련 내용의 효과/의미를 간단히 설명\n"
                    "3. 아이들이 해당 수련을 열심히 하는 모습 칭찬\n"
                    f"4. \"{folder_hint}\" 시간대를 제목과 본문 첫 부분에서 언급\n"
                    "5. 학부모님께 감사 인사\n"
                    "6. 시간대 인사(좋은 아침, 좋은 오후 등)는 사용하지 마세요\n"
                    "7. 이모지는 1~2개만 사용\n"
                    "8. 매일 다른 표현과 내용으로 작성 (반복적인 문구 사용 금지)\n"
                    f"9. **다른 종목의 용어는 사용하지 마세요** - 오직 {gym_sport} 관련 용어만 사용\n"
                    "10. **어투: \"~습니다\", \"~했습니다\", \"~였습니다\" 형식 사용 (해요체 \"~요\" 금지)**\n\n"
                    "[참고] 올바른 예시:\n"
                    f"\"오늘 {folder_hint} 친구들과 함께 {training_content} 수련을 진행했습니다. 모두 열심히 참여했으며, 기술이 한층 성장했습니다. 응원해주시는 학부모님들께 감사드립니다. \"\n"
                )
        elif platform == 'manual_topic':
            # 🟢 수동 주제 포스팅 전용 - 사용자 입력 주제 기반 (밴드용 짧은 글)
            # topic에서 카테고리 추출
            category_hint = ""
            main_topic = topic
            
            if "[" in topic and "]" in topic:
                category_hint = topic.split("]")[0].replace("[", "").strip()
                main_topic = topic.split("]")[1].strip() if "]" in topic else topic
            
            #  종목 설정값 가져오기
            gym_sport = settings.get('gym_sport', '합기도')
            
            # 무도/수련 관련 키워드 확인
            martial_keywords = ['스텝', '발차기', '대련', '품새', '기술', '호신술', '낙법', '수련', '격파', '시범']
            is_martial_content = any(kw in main_topic for kw in martial_keywords)
            
            if is_martial_content:
                # 무도 수련 내용인 경우
                sport_instruction = f"이 체육관의 종목은 {gym_sport}입니다. 주제에 맞게 {gym_sport} 수련 내용으로 작성하세요."
            else:
                # 요가, 외발자전거 등 비무도 활동인 경우
                sport_instruction = f"주제가 {gym_sport} 수련이 아니므로, {gym_sport}는 언급하지 마세요. 사용자가 입력한 활동만 언급하세요."
            
            user_prompt = (
                "당신은 네이버 밴드에 짧은 글을 쓰는 작가입니다.\n\n"
                f"[정보] 카테고리: {category_hint if category_hint else '일반'}\n"
                f"[정보] 주제: {main_topic}\n"
                f"[정보] 종목 안내: {sport_instruction}\n\n"
                "[주의] 절대 금지 사항:\n"
                "- 블로그처럼 길게 쓰지 마세요\n"
                "- \"알려드릴게요\", \"함께해요\" 같은 표현 금지\n"
                "- 시간대 인사(좋은 아침, 활기찬 오후 등) 금지\n"
                "- 마크다운 헤딩(###) 사용 금지\n"
                "- 소제목 나누기 금지\n"
                "- **대상 언급 금지** (회원님들, 친구들, 어린이들, 수련생들, 학부모님 등 대상 표현 사용 금지)\n"
                "- 설명이나 효능을 나열하듯 길게 쓰지 마세요\n\n"
                "[확인] 반드시 지켜야 할 규칙:\n"
                "1. 전체 글 길이: 250~300자 (5~6문장)\n"
                "2. **수업 내용**에 대해 간단히 소개\n"
                "3. 사용자가 입력한 **모든 활동**을 언급 (요가, 외발자전거 등 누락 금지)\n"
                "4. **효과/효능**을 자연스럽게 언급 (유연성, 균형감각, 근력 등)\n"
                "5. **건강/다이어트 관련** 내용 포함\n"
                "6. 따뜻하고 부드러운 어투로 마무리\n"
                "7. **매번 다른 표현과 내용** 사용 (같은 활동이라도 매번 새로운 관점, 다른 표현으로 작성)\n\n"
                "[팁] 다양성을 위한 표현 예시:\n"
                "- 시작: \"오늘 수업에서는...\", \"이번 시간에는...\", \"활기찬 수업 시간...\"\n"
                "- 효과: \"유연성이 좋아지는...\", \"몸이 가벼워지는...\", \"균형감각을 키우는...\"\n"
                "- 마무리: \"건강한 하루 되세요!\", \"활기찬 하루 보내세요!\", \"오늘도 건강하게!\"\n\n"
                "[형식] 형식:\n"
                "[제목]\n"
                "(이모지 1개 + 짧은 제목)\n\n"
                "[본문]\n"
                "(250~300자, 5~6문장의 짧고 따뜻한 글)\n\n"
                "[참고] 올바른 예시:\n"
                "[제목]  오전 요가와 외발자전거 수업!\n"
                "[본문] 오늘 오전에 요가와 외발자전거 수업을 진행했어요. 요가로 몸의 유연성을 기르고 깊은 호흡으로 마음을 차분하게 다스렸습니다. 이어서 외발자전거로 균형감각과 하체 근력을 키우는 시간도 가졌어요. 두 가지 운동 모두 다이어트와 건강 유지에 효과적이랍니다. 꾸준히 하면 몸이 더욱 가벼워지는 것을 느낄 수 있어요. 건강한 하루 되세요! \n"
            )
        elif platform == 'band':
            # 🟢 밴드 전용 포스팅: 체육관 홍보 절대 금지, 학부모 맞춤형 육아/건강/교육 칼럼
            user_prompt = (
                f"주제: {topic}\n\n"
                f"### [작성 규칙]\n"
                "1. **작성 방향 및 어조 (절대 엄수)**: \n"
                "   - 당신은 아이들의 성장을 돕는 따뜻한 교육 전문가(관장)입니다.\n"
                "   - **도장 자랑, 종목 홍보, 원생 모집, '우리 체육관에서는~' 등의 어필을 절대 금지합니다.** (무술, 단련, 수련, 입관, 등록 등 금지)\n"
                "   - **[중요] 절대로 가르치거나 훈계하는 듯한 딱딱한 어조를 사용하지 마세요.**\n"
                "   - 같은 학부모의 입장에서 **깊이 공감하고, 다정하게 경험을 공유하며, 함께 고민을 나누는 듯한 부드러운 어조**를 사용하세요.\n\n"
                "2. **도입부 (시간대별 훅) - [중요: 본문과 연결 금지]**:\n"
                "   - 오전 (morning): 오늘 하루의 상쾌한 날씨/계절 인사\n"
                "   - 오후/저녁 (regular/closing): 주요 뉴스나 트렌디한 이슈\n"
                "   - 저녁 (closing) 특별: 내일의 날씨(기온)를 언급하며 아이들 옷차림/준비물 등을 세심하게 챙기는 멘트\n"
                "   - **주의: 이 도입부(날씨/뉴스)는 본론 주제와 억지로 연결하지 마세요. 독립적인 안부 인사로만 끝내세요.**\n\n"
                "3. **본론 (주제 준수)**: 독립적인 새로운 문단으로 본론을 시작하세요.\n"
                "   - 유익한 육아/건강/마인드셋 정보를 다룹니다.\n"
                "   - 학부모의 일상적 고민에 대한 공감 형성 -> 일상에서 실천할 수 있는 가벼운 조언 공유 -> 따뜻한 응원의 마무리 순으로 자연스럽게 전개하세요.\n\n"
                f"4. **분량**: 학부모님들께 깊이 있는 공감과 충분한 정보가 전달되도록 **400~500자 내외**로 넉넉하게 작성하세요.\n\n"
                "5. **태그**: 글 맨 마지막에 본문 주제와 관련된 해시태그 5개를 생성하세요.\n\n"
                "반드시 아래 형식을 지켜서 출력해:\n\n"
                "[제목]\n"
                "(학부모의 눈길을 끄는 정보성/공감형 제목)\n\n"
                "[본문]\n"
                "(1문단: 날씨/뉴스 훅 (본론과 연결 금지))\n\n"
                "(2문단: 학부모 공감 및 본론 주제 설명)\n\n"
                "(3문단: 가정 내 실천 팁 및 따뜻한 마무리)\n\n"
                "(AI 생성 해시태그 5개: #태그1 #태그2 ...)\n\n"
                f"주의: {platform}용 글에는 블로그 전용 문구(한국체대 라이온 블로거 등)를 절대 포함하지 마세요.\n"
            )
        else:
            # 🟢 카페 포스팅 (기존 로직 유지)
            user_prompt = (
                f"주제: {topic}\n\n"
                f"### [작성 규칙]\n"
                "1. 도입부 (시간대별 훅): 첫 문단은 아래 가이드에 따라 자연스럽게 시작하세요.\n"
                "   - 오전 (morning): 오늘 하루의 상쾌한 날씨 정보로 시작\n"
                "   - 오후/저녁 (regular/closing): 주요 뉴스나 트렌틱한 이슈로 시작\n"
                "   - 저녁 (closing) 특별: 내일의 기온(최저/최고)과 날씨를 언급하며 부모님들이 아이들 옷차림을 준비할 수 있게 안내 문구를 포함하세요.\n"
                "2. 본론 (주제 준수): '그래서/이럴 때일수록' 등의 연결어로 본론 주제로 넘어가세요. [중요] 주제에 없는 구체적인 지명이나 수련 활동(낙법, 줄넘기 등)을 절대 창작하지 마세요.\n"
                f"3. 분량 준수: {platform} 플랫폼 전용 글자 수 제한을 엄격히 지키세요.\n\n"
                "반드시 아래 형식을 지켜서 출력해:\n\n"
                "[제목]\n"
                "(뉴스/날씨 + 주제를 결합한 클릭유도형 제목)\n\n"
                "[본문]\n"
                "(1문단: 뉴스/날씨 훅 -> 2문단: 주제 본론 -> 3문단: 마무리)\n\n"
                f"주의: {platform}용 글에는 블로그 전용 문구(한국체대 라이온 블로거 등)를 절대 포함하지 마세요.\n"
            )


        # 🟢 [Smart Context] 학기/방학 시즌 자동 감지 및 지침 주입
        semester_context = self._get_semester_context()
        if semester_context:
            system_message += f"\n\n[System: {semester_context['period_name']} 시즌 가이드]\n{semester_context['instruction']}"
        
        # 블로그는 기존 parse_content 사용, 밴드/카페는 별도 처리 고려 가능
        result = self.generate_content(
            topic, 
            post_type_config={'custom_system': system_message, 'custom_user': user_prompt}, 
            platform=platform,
            task_type=task_type,  # task_type 전달
            target_time=target_time  # 🟢 타임머신 시간 전달 
        )
        return result
    
    def _generate_with_gemini(self, model_name: str, system_message: str, user_prompt: str, api_key: str = None) -> str:
        # Gemini 모델로 콘텐츠 생성
        # 1. 파라미터로 전달된 키 우선
        # 2. 인스턴스에 저장된 키 (self.gemini_api_key) 차순위
        target_api_key = api_key if api_key else self.gemini_api_key

        if not target_api_key:
            raise ValueError("Gemini API 키가 설정되지 않았습니다.")
        try:
            import google.generativeai as genai
        except ImportError as e:
            raise ImportError("google-generativeai 패키지가 필요합니다. pip install google-generativeai") from e
        
        genai.configure(api_key=target_api_key)
    
        # [System] 날짜 정보 자동 주입 (시점 오류 방지)
        current_date_str = datetime.now().strftime("%Y년 %m월 %d일")
        date_instruction = f"\n\n[System: 시점 고정]\n오늘은 {current_date_str}입니다. 글의 시점은 반드시 오늘({current_date_str})을 기준으로 작성되어야 합니다. 과거 데이터(2024년 등)에 얽매이지 말고 현재 시점에 맞춰 서술하세요."

        if system_message:
            system_message += date_instruction
        else:
            system_message = date_instruction

        model = genai.GenerativeModel(model_name)
        prompt_text = f"{system_message}\n\n{user_prompt}"
        response = model.generate_content(
            prompt_text,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 8192,
                "top_p": 0.9,
            }
        )
        content = self._extract_gemini_text(response)
        if not content:
            raise ValueError("Gemini 응답에서 본문을 추출할 수 없습니다.")
        return content.strip()

    def _extract_gemini_text(self, response: Any) -> str:
        # Gemini 응답 객체에서 텍스트 추출
        if hasattr(response, "text") and response.text:
            return response.text
        # candidates.parts 구조 처리
        if hasattr(response, "candidates"):
            parts: List[Any] = []
            for cand in getattr(response, "candidates", []):
                content = getattr(cand, "content", None)
                if not content:
                    continue
                for part in getattr(content, "parts", []):
                    txt = getattr(part, "text", None)
                    if txt:
                        parts.append(txt)
            if parts:
                return "\n".join(parts)
        # dict-like 응답 대비
        if isinstance(response, dict) and "text" in response:
            return response.get("text", "")
        return ""

    def _validate_content(self, content):
        # 생성된 콘텐츠가 요구사항을 충족하는지 검증합니다.
        if not content:  # 콘텐츠가 비어있는 경우만 체크
            return False
            
        # 길이 제한 검증 (더 유연하게 조정)
        content_length = len(content.strip())
        if content_length < 100:  # 너무 짧은 경우만 체크
            return False
            
        # 기본적인 형식만 체크 (제목과 본문이 구분되어 있는지)
        if '[제목]' not in content and '[본문]' not in content:
            if '\n\n' not in content:  # 최소한 문단 구분이라도 있는지 확인
                return False
            
        return True

    def _parse_content(self, content):
        # GPT 응답을 제목과 본문으로 분리합니다.
        try:
            # [제목]과 [본문] 태그를 기준으로 분리
            parts = content.split('[본문]')
            if len(parts) != 2:
                # 다른 형식 시도
                lines = content.split('\n')
                title = lines[0].replace('[제목]', '').strip()
                body = '\n'.join(lines[1:]).strip()
                return title, body
            
            title_part = parts[0].split('[제목]')
            if len(title_part) != 2:
                title = title_part[0].strip()
            else:
                title = title_part[1].strip()
            
            body = parts[1].strip()
            
            # 사용자 설정에 따른 후처리 (기호 사용 금지 설정 확인)
            settings = self._load_settings()
            if '기호' in settings.get('instructions', '') and '사용하지 말' in settings.get('instructions', ''):
                # 기호 사용 금지 설정인 경우 기호 제거
                body = body.replace('-', '')
                body = body.replace('-', '')
                body = body.replace('- ', '')
                body = body.replace('>', '')
                body = body.replace('*', '')
            else:
                # 기호 사용이 허용된 경우에만 통일
                body = body.replace('-', '-')
                body = body.replace('- ', '- ')
            
            return title, body
            
        except Exception as e:
            logger.error(f"콘텐츠 파싱 중 오류 발생: {str(e)}")
            # 기본 파싱 방식으로 폴백
            lines = content.strip().split("\n")
            title = lines[0].strip()
            body = "\n".join(lines[2:]).strip()
            return title, body

    def _get_dummy_content(self, topic):
        # 테스트용 더미 콘텐츠를 반환합니다.
        
        exercise_content = (
            "[도입] 도입: 건강한 삶을 위해 어떤 운동을 시작해야 할까요?\n\n"
            "- 많은 분들이 고민하시는 부분입니다.\n\n"
            "[장점] 장점: 꾸준한 운동의 특별한 매력\n\n"
            "- 체력 향상과 활기찬 일상\n"
            "- 전신 운동으로 근력 발달\n"
            "- 유연성과 균형감각 향상\n"
            "- 바른 자세 형성\n\n"
            "- 스트레스 해소와 집중력\n"
            "- 긍정적인 마인드 함양\n"
            "- 자기 관리 능력 향상\n"
            "- 목표 달성의 즐거움\n\n"
            "[팁] 운동의 긍정적 효과\n\n"
            "- 자신감 향상\n"
            "- 단계별 성장 경험\n"
            "- 성취감 획득\n"
            "- 건강한 에너지 발산\n\n"
            "[결론] 결론: 운동은 단순한 신체 활동이 아닌 \n"
            "삶의 질을 높이는 도구입니다.\n\n"
            "[제안] 제안: 더 건강하고 활기찬 내일, \n"
            "오늘부터 시작해보는 건 어떨까요?\n\n"
            "가까운 체육관이나 공원에서\n"
            "변화된 일상을\n"
            "직접 경험해보세요!"
        )

        default_content = (
            f"[도입] 안녕하세요! 오늘은 {topic}에 \n"
            "대해 이야기 나눠볼까요?\n\n"
            "[확인] 주제 살펴보기\n"
            "- 이것은 테스트용 더미 \n"
            "콘텐츠입니다.\n\n"
            "[팁] 핵심 포인트\n"
            "- 첫 번째 중요 사항\n"
            "- 두 번째 중요 사항\n"
            "- 세 번째 중요 사항\n\n"
            "[결론] 정리하며\n"
            "이 글이 도움이 되셨나요?\n"
            "아래 댓글로 여러분의 생각을\n"
            "들려주세요!"
        )

        dummy_contents = {
            "운동 효과의 장점": {
                "title": "꾸준한 운동의 놀라운 효과, 이것 하나로 활기찬 일상 UP!",
                "content": exercise_content
            },
            "default": {
                "title": f"[메모] {topic}에 대한 전문가의 특별한 이야기",
                "content": default_content
            }
        }
        
        # 더미 콘텐츠 가져오기
        dummy_content = dummy_contents.get(topic, dummy_contents["default"])
        
        # 사용자 설정에서 첫 문장 추가 처리
        user_settings = self._load_user_settings()
        first_sentence = user_settings.get('first_sentence', '').strip()
        if first_sentence:
            logger.info(f"🔥 더미 콘텐츠에 첫 문장 추가: '{first_sentence}'")
            logger.info(f"🔥 더미 원본 본문: '{dummy_content['content'][:100]}...'")
            
            # 무조건 설정된 첫 문장을 본문 맨 앞에 추가
            dummy_content["content"] = f"{first_sentence}\n\n{dummy_content['content']}"
            
            logger.info(f"🔥 더미 첫 문장 추가 후: '{dummy_content['content'][:100]}...'")
        else:
            logger.info("🔥 더미 콘텐츠: 첫 문장 설정이 없습니다.")
        
        return dummy_content

    def _create_prompt(self, topic, style):
        # GPT 프롬프트를 생성합니다.
        prompt = (
            f"다음 주제로 블로그 포스트를 작성해주세요:\n"
            f"주제: {topic}\n"
            f"스타일: {style}\n\n"
            "포맷:\n"
            "- 첫 줄은 제목으로 작성해주세요\n"
            "- 제목 다음에 빈 줄을 넣어주세요\n"
            "- 그 다음부터 본문을 작성해주세요\n"
            "- 적절한 단락 구분을 해주세요\n"
            "- 읽기 쉽고 자연스러운 문체로 작성해주세요\n"
            "- 전문적이면서도 친근한 톤을 유지해주세요\n"
        )
        return prompt

    def _format_content_for_mobile(self, content):
        # 모바일 환경에 최적화된 형식으로 콘텐츠를 변환합니다.
        formatted_lines = []
        for paragraph in content.split('\n'):
            if not paragraph.strip():
                formatted_lines.append('')
                continue
            
            current_line = ''
            for word in paragraph.split():
                if not current_line:
                    current_line = word
                else:
                    # 현재 줄의 길이가 5-25자 사이의 랜덤한 길이에 도달하면 줄바꿈
                    max_line_length = random.randint(5, 25)
                    
                    # 문맥을 고려하여 줄바꿈 (마침표, 쉼표, 느낌표, 물음표 등 문장 부호 뒤에서 우선적으로 줄바꿈)
                    if len(current_line) >= max_line_length and any(current_line.endswith(p) for p in ['.', ',', '!', '?', ':', ';', ')', '>', '』', '」', '》', '"']):
                        formatted_lines.append(current_line)
                        current_line = word
                    # 최대 길이를 초과하면 줄바꿈
                    elif len(current_line + ' ' + word) > 25:
                        formatted_lines.append(current_line)
                        current_line = word
                    else:
                        current_line += ' ' + word
            
            if current_line:
                formatted_lines.append(current_line)
            formatted_lines.append('')  # 문단 사이 여백
        
        return '\n'.join(formatted_lines)

    def _enhance_formatting(self, content):
        # 콘텐츠의 가독성을 향상시킵니다.
        # 사용자 설정 확인
        settings = self._load_settings()
        
        # 기호나 이모티콘 사용 금지 설정 확인
        if ('기호' in settings.get('instructions', '') and '사용하지 말' in settings.get('instructions', '')) or \
           ('이모티콘' in settings.get('instructions', '') and '사용하지 말' in settings.get('instructions', '')):
            # 기호와 이모티콘 제거
            formatted_content = content
            formatted_content = formatted_content.replace('-', '')
            formatted_content = formatted_content.replace('-', '')
            formatted_content = formatted_content.replace('- ', '')
            formatted_content = formatted_content.replace('>', '')
            formatted_content = formatted_content.replace('*', '')
            # 이모티콘 제거 (일반적인 이모티콘들) - 인코딩 문제로 주석 처리
            # import re
            # formatted_content = re.sub(r'[이모지들]', '', formatted_content)
        else:
            # 기호와 이모티콘 사용이 허용된 경우
            emoji_map = {
                '도입': '[도입]',
                '소개': '[메모]',
                '장점': '[장점]',
                '특징': '[확인]',
                '방법': '📌',
                '팁': '[팁]',
                '주의': '⚠️',
                '결론': '[결론]',
                '요약': '📋',
                '제안': '[제안]'
            }
            
            # 이모지 추가
            formatted_content = content
            for key, emoji in emoji_map.items():
                formatted_content = formatted_content.replace(f"- {key}", f"{emoji} {key}")
            
            # 강조 표시 개선
            formatted_content = formatted_content.replace('-', '-')
            formatted_content = formatted_content.replace('- ', '- ')
        
        # 문단 구분 개선
        paragraphs = formatted_content.split('\n\n')
        formatted_paragraphs = []
        for p in paragraphs:
            if p.strip():
                formatted_paragraphs.append(p.strip())
        
        return '\n\n'.join(formatted_paragraphs)

    def generate_reply(self, system_prompt: str, user_text: str, max_tokens: int = 150, selected_models: list = None) -> str:
        """
        간단한 댓글 답글 생성용 메서드 (모델 순환 및 재시도 로직 적용)
        """
        fallback_msg = "잘 보고 갑니다! 좋은 하루 되세요~"
        
        if self.use_dummy:
            return fallback_msg
        
        # 인자로 전달된 모델 목록이 있으면 사용, 없으면 설정된 모델 사용
        models_to_use = selected_models if selected_models else self.selected_models
        
        if not models_to_use:
            models_to_use = [Config.GPT_MODEL]
            
        total = len(models_to_use)
        # 로드 밸런싱: 현재 인덱스부터 시작 (단, 모델 목록이 변경되었을 수 있으므로 인덱스 조정 필요)
        start_idx = self.current_model_index % total
        
        for step in range(total):
            model_idx = (start_idx + step) % total
            model_name = models_to_use[model_idx]
            
            # 일일 한도 체크 (선택 사항)
            if not self._check_daily_limit(model_name):
                continue

            provider = Config.AI_MODELS.get(model_name, {}).get("provider", "openai")
            
            try:
                if provider == "openai":
                    resp = self.openai_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_text}
                        ],
                        temperature=0.8,
                        max_tokens=max_tokens,
                        top_p=0.9
                    )
                    content = resp.choices[0].message.content.strip()
                elif provider == "gemini":
                    # Flash-Lite 등 쿼터 에러 대응
                    content = self._generate_with_gemini(model_name, system_prompt, user_text)
                else:
                    continue

                if content:
                    # 성공 시 다음 모델 인덱스 업데이트
                    self._increment_usage(model_name)
                    self.current_model_index = (model_idx + 1) % total
                    return content
                    
            except Exception as e:
                logger.error(f"답글 생성 오류 ({model_name}): {e}")
                continue
        
        # 모든 모델 실패 시 더미 반환
        logger.warning("모든 모델 답글 생성 실패, 기본 문구 사용")
        return fallback_msg

    # 🟢 기상청 단기예보 격자 좌표 매핑 (지역명 → nx, ny)
    KMA_GRID_MAP = {
        # 서울
        "서울": (60, 127), "서울특별시": (60, 127), "서울시": (60, 127),
        "강남구": (61, 126), "강동구": (62, 126), "강북구": (61, 128),
        "강서구": (58, 126), "관악구": (59, 125), "광진구": (62, 126),
        "구로구": (58, 125), "금천구": (59, 124), "노원구": (61, 129),
        "도봉구": (61, 129), "동대문구": (61, 127), "동작구": (59, 125),
        "마포구": (59, 127), "서대문구": (59, 127), "서초구": (61, 125),
        "성동구": (61, 127), "성북구": (61, 128), "송파구": (62, 126),
        "양천구": (58, 126), "영등포구": (58, 126), "용산구": (60, 126),
        "은평구": (59, 128), "종로구": (60, 127), "중구": (60, 127),
        "중랑구": (62, 128),
        # 인천
        "인천": (55, 124), "인천광역시": (55, 124), "인천시": (55, 124),
        "부평구": (55, 124), "인천 부평구": (55, 124), "부평": (55, 124),
        "남동구": (56, 124), "연수구": (56, 123), "미추홀구": (54, 124),
        "계양구": (56, 126), "서구": (55, 126), "중구 인천": (54, 125),
        "동구 인천": (54, 125), "강화군": (51, 130),
        # 경기
        "수원": (60, 121), "수원시": (60, 121), "성남": (63, 124), "성남시": (63, 124),
        "고양": (57, 128), "고양시": (57, 128), "용인": (64, 119), "용인시": (64, 119),
        "부천": (56, 125), "부천시": (56, 125), "안산": (58, 121), "안산시": (58, 121),
        "안양": (59, 123), "안양시": (59, 123), "남양주": (64, 128), "남양주시": (64, 128),
        "화성": (57, 119), "화성시": (57, 119), "평택": (62, 114), "평택시": (62, 114),
        "의정부": (61, 130), "의정부시": (61, 130), "시흥": (57, 123), "시흥시": (57, 123),
        "파주": (56, 131), "파주시": (56, 131), "김포": (55, 128), "김포시": (55, 128),
        "광명": (58, 125), "광명시": (58, 125), "광주시": (65, 123),
        "군포": (59, 122), "군포시": (59, 122), "하남": (64, 126), "하남시": (64, 126),
        "오산": (62, 118), "오산시": (62, 118), "이천": (68, 121), "이천시": (68, 121),
        "양평": (69, 125), "양평군": (69, 125),
        # 광역시
        "부산": (98, 76), "부산광역시": (98, 76), "부산시": (98, 76),
        "대구": (89, 90), "대구광역시": (89, 90), "대구시": (89, 90),
        "광주": (58, 74), "광주광역시": (58, 74),
        "대전": (67, 100), "대전광역시": (67, 100), "대전시": (67, 100),
        "울산": (102, 84), "울산광역시": (102, 84), "울산시": (102, 84),
        "세종": (66, 103), "세종특별자치시": (66, 103), "세종시": (66, 103),
        # 강원
        "춘천": (73, 134), "춘천시": (73, 134),
        "원주": (76, 122), "원주시": (76, 122),
        "강릉": (92, 131), "강릉시": (92, 131),
        "속초": (87, 141), "속초시": (87, 141),
        "양양": (88, 138), "양양군": (88, 138),
        # 충청
        "청주": (69, 107), "청주시": (69, 107),
        "천안": (63, 110), "천안시": (63, 110),
        "충주": (76, 114), "충주시": (76, 114),
        # 전라
        "전주": (63, 89), "전주시": (63, 89),
        "익산": (60, 91), "익산시": (60, 91),
        "여수": (73, 66), "여수시": (73, 66),
        "순천": (70, 70), "순천시": (70, 70),
        "목포": (50, 67), "목포시": (50, 67),
        # 경상
        "포항": (102, 94), "포항시": (102, 94),
        "경주": (100, 91), "경주시": (100, 91),
        "김해": (95, 77), "김해시": (95, 77),
        "진주": (81, 75), "진주시": (81, 75),
        "창원": (89, 77), "창원시": (89, 77),
        "거제": (90, 69), "거제시": (90, 69),
        # 제주
        "제주": (52, 38), "제주시": (52, 38), "제주특별자치도": (52, 38),
        "서귀포": (52, 33), "서귀포시": (52, 33),
    }

    def _get_kma_weather(self, location="서울", forecast=False):
        """기상청 단기예보 API를 사용한 날씨 정보 조회 (로컬 캐시 우선)
        
        forecast=True: 내일 예보 / False: 현재(오늘) 날씨
        """
        try:
            from modules.weather_cache_manager import WeatherCacheManager
            delta = 1 if forecast else 0
            
            # 캐시 매니저를 통해 포맷팅된 날씨 정보 가져오기
            cached_weather = WeatherCacheManager.get_cached_weather(location, delta_days=delta)
            
            if cached_weather:
                logger.info(f"로컬 캐시에서 날씨 정보를 성공적으로 불러왔습니다: {location} (forecast={forecast})")
                return cached_weather
            
            logger.warning(f"날씨 캐시 정보가 없거나 오래되었습니다. 즉시 캐시 업데이트를 시도합니다: {location}")
            
            # 캐시가 없으면 즉시 한 번 업데이트를 시도합니다.
            settings = self._load_settings()
            api_key = settings.get('kma_api_key', '')
            if api_key:
                # KMA 업데이트 시도
                success = WeatherCacheManager.update_weather_cache(location, api_key)
                if success:
                    cached_weather = WeatherCacheManager.get_cached_weather(location, delta_days=delta)
                    if cached_weather:
                        return cached_weather
            
            # KMA 업데이트 실패 혹은 api_key 없으면 Naver 업데이트 시도
            success = WeatherCacheManager.update_weather_cache_via_naver(location)
            if success:
                cached_weather = WeatherCacheManager.get_cached_weather(location, delta_days=delta)
                if cached_weather:
                    return cached_weather
                    
            return None
            
        except Exception as e:
            logger.error(f"날씨 정보 로딩 실패: {e}")
            return None

    def _get_naver_weather(self, location="서울", forecast=False):
        # 이제 네이버 폴백 로직도 WeatherCacheManager에 통합되었으므로, KMA 로직을 재호출합니다.
        return self._get_kma_weather(location, forecast=forecast)
    
    def _filter_news_content(self, text: str) -> bool:
        """뉴스 내용에 금칙어가 포함되어 있는지 확인"""
        forbidden_keywords = [
            '정치', '여당', '야당', '대통령', '의원', '선거', '투표', '탄핵', '시위', 
            '종교', '교회', '성당', '불교', '기독교', '목사', '스님', '사이비',
            '살인', '성범죄', '마약', '도박', '자살', '충격', '경악', '속보', '19금', '성인'
        ]
        
        for keyword in forbidden_keywords:
            if keyword in text:
                return True
        return False

    def _get_trending_topics(self, count=3, force_refresh=False):
        # 오후/저녁용: 최신 뉴스/이슈/트렌드 정보 수집
        # count: 가져올 뉴스 수 (기본 3, 배치 분배용 6)
        
        # 0순위: 로컬 캐시 확인
        cache_file = os.path.join("config", "news_cache.json")
        try:
            if not force_refresh and os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                last_updated_str = cache_data.get('last_updated', '')
                if last_updated_str:
                    last_updated = datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
                    if datetime.now() - last_updated < timedelta(hours=6):
                        news_lines = cache_data.get('news', [])
                        if news_lines:
                            logger.info("로컬 뉴스 캐시를 사용합니다.")
                            return "\n".join(news_lines[:count])
        except Exception as e:
            logger.warning(f"뉴스 캐시 읽기 실패 (무시됨): {e}")

        try:
            fetched_news = []
            
            # 1순위: Brave Search로 오늘의 핫이슈 검색
            brave_result = self._search_brave("오늘 뉴스 이슈 트렌드", count=count * 2) # 필터링 고려해 더 많이 검색
            if brave_result:
                # 🟢 코드 레벨 필터링 적용
                lines = brave_result.split('\n')
                for line in lines:
                    if line.strip() and not self._filter_news_content(line):
                        fetched_news.append(line.strip())
            
            # 2순위: 네이버 실시간 검색어/인기 검색어 크롤링
            if not fetched_news:
                try:
                    url = "https://search.naver.com/search.naver?query=" + urllib.parse.quote("오늘 뉴스")
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                        html = response.read().decode('utf-8')
                    
                    # 뉴스 제목 추출
                    news_titles = re.findall(r'class="news_tit"[^>]*>(.*?)<', html)
                    if news_titles:
                        idx = 1
                        for title in news_titles:
                            if not self._filter_news_content(title):
                                fetched_news.append(f"{idx}. {title}")
                                idx += 1
                except Exception:
                    pass
            
            # 검색 결과를 캐시에 저장
            if fetched_news:
                try:
                    os.makedirs("config", exist_ok=True)
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "news": fetched_news
                        }, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    logger.warning(f"뉴스 캐시 저장 실패: {e}")
                
                return "\n".join(fetched_news[:count])
                
            # 3순위: 기본 안내 (검색 실패 시)
            return (
                "[최신 이슈를 찾지 못했습니다]\n"
                "최근 뉴스, 유행어, 생활 꿀팁, 재미있는 상식 중에서\n"
                "하나를 선택하여 자유롭게 글을 시작해주세요."
            )
        except Exception as e:
            logger.warning(f"트렌드 정보 수집 실패: {e}")
            return None

    def _search_brave(self, query: str, count: int = 3) -> str:
        # Brave Search API를 사용하여 실시간 검색 결과를 반환합니다.
        api_key = self.settings.get('brave_key')
        if not api_key:
            return ""
            
        try:
            # 기본 검색 URL
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {"X-Subscription-Token": api_key, "Accept": "application/json"}
            
            # 🟢 1단계: 검색어 원천 차단 (부정 키워드 추가)
            safe_query = query
            if any(k in query for k in ["뉴스", "소식", "이슈", "동향", "트렌드"]):
                safe_query += " -정치 -여당 -야당 -종교 -사건 -사고 -성인 -19금"
                
            # 검색어 인코딩 및 파라미터 설정 (상위 count개 결과)
            params_dict = {"q": safe_query, "count": count}
            
            # 🟢 뉴스/날씨/이슈 관련 검색이면 '최신성(Past Day)' 필터 적용
            if any(k in query for k in ["뉴스", "소식", "이슈", "동향", "트렌드", "날씨", "미세먼지", "오늘", "속보", "최신"]):
                params_dict["freshness"] = "pd"  # pd: Past Day (지난 24시간)
                logger.info(f"Brave Search 최신성 필터 적용 (freshness=pd): {safe_query}")
            
            params = urllib.parse.urlencode(params_dict)
            
            req = urllib.request.Request(f"{url}?{params}", headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                
            results = []
            for item in data.get('web', {}).get('results', []):
                title = item.get('title', '')
                desc = item.get('description', '')
                link = item.get('url', '')
                results.append(f"- **{title}**: {desc} (출처: {link})")
                
            if results:
                logger.info(f"Brave Search 성공: '{safe_query}' 관련 {len(results)}건 검색됨")
                return "\n".join(results)
            return ""
            
        except Exception as e:
            logger.warning(f"Brave Search 실패 (무시됨): {e}")
            return ""

    def _check_is_forecast(self, target_time: str = None) -> bool:
        """
        예약 시간(target_time)을 기준으로 '내일' 발행용 포스팅인지 판단합니다.
        
        Args:
            target_time: "HH:MM" 형식의 예약 시간
            
        Returns:
            bool: 내일 발행용이면 True, 오늘 발행용이면 False
        """
        if not target_time:
            return False
            
        try:
            now = datetime.now()
            target_hour, target_minute = map(int, target_time.split(':'))
            target_dt = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
            
            # 예약 시간이 현재보다 과거라면 '내일'로 간주 (Scheduler 로직과 동일)
            if target_dt < now:
                return True
            return False
        except Exception as e:
            logger.warning(f"forecast 판단 실패: {e}")
            return False

    def _build_weather_hook_message(self, weather_loc, is_forecast, platform):
        """오전 포스팅용 날씨 훅 메시지 생성"""
        if not weather_loc:
            return ""
            
        weather_info = self._get_kma_weather(weather_loc, forecast=is_forecast)
        if not weather_info:
            weather_info = self._get_naver_weather(weather_loc, forecast=is_forecast)
            
        if not weather_info:
            return ""
            
        weather_label = "내일 오전 발행용 기상 예보" if is_forecast else "실시간 날씨 정보"
        
        # 계절 정보 및 가이드 추가
        current_date = datetime.now() + timedelta(days=1 if is_forecast else 0)
        month = current_date.month
        
        hook_msg = f"\n[System: {weather_label} ({weather_loc})]\n{weather_info}\n"
        
        # --- 🚨 비/소나기/강수 감지 로직 추가 ---
        if any(keyword in weather_info for keyword in ["비", "소나기", "눈", "강수", "폭우"]):
            hook_msg += (
                "⚠️ [시스템 긴급 경고]: 현재 일기예보에 '비/소나기/강수'가 포함되어 있습니다. "
                "절대로 '활동하기 좋은 날씨'나 '화창하다'는 긍정적인 표현을 하지 마세요!! "
                "반드시 '외출 시 우산을 챙기세요', '비가 오니 실내 활동을 추천합니다' 등 궂은 날씨에 대비하는 당부의 말로 작성하세요.\n"
            )
        
        if is_forecast:
            hook_msg += (
                f"(위 정보는 '내일' 발행용입니다. 구체적인 수치보다는 {month}월의 계절감과 "
                "일상적인 날씨 변화를 언급하며 글을 시작하세요.)\n"
            )
        else:
            hook_msg += "(위 실시간 날씨를 바탕으로 이웃들에게 인사를 건네며 자연스럽게 시작하세요.)\n"
            
        hook_msg += "[!!! 필수 !!!] 첫 문단(도입부)은 반드시 위 날씨 정보로 시작하고 본론으로 연결하세요.\n"
        return hook_msg

    def _build_news_hook_message(self, platform):
        """오후/저녁 포스팅용 뉴스/이슈 훅 메시지 생성"""
        trending_info = self._get_trending_topics(count=3)
        if not trending_info:
            return ""
            
        hook_msg = f"\n[System: 오늘의 뉴스/이슈/트렌드]\n{trending_info}\n"
        hook_msg += (
            "(위 이슈 중 하나를 선택해 '요즘 이런 소식이 화제인데요'와 같이 자연스럽게 언급하며 "
            "글의 서두를 여세요.)\n"
            "[!!! 필수 !!!] 첫 문단(도입부)은 반드시 위 뉴스/이슈 중 하나로 시작하세요.\n"
        )
        return hook_msg

    def _build_closing_weather_message(self, weather_loc):
        """저녁 포스팅 하단 가이드(내일 날씨 꿀팁) 생성"""
        if not weather_loc:
            return ""
            
        tomorrow_weather = self._get_kma_weather(weather_loc, forecast=True)
        if not tomorrow_weather:
            return ""
            
        hook_msg = f"\n[System: 내일의 준비 (배려 팁)]\n{tomorrow_weather}\n"
        
        # --- 🚨 비/소나기/강수 감지 로직 추가 ---
        if any(keyword in tomorrow_weather for keyword in ["비", "소나기", "눈", "강수", "폭우"]):
            hook_msg += (
                "⚠️ [시스템 긴급 경고]: 내일 일기예보에 '비/소나기/강수'가 포함되어 있습니다. "
                "반드시 마무리 멘트에서 '내일은 비 소식이 있으니 우산을 꼭 챙기세요', '비굣길 조심하세요' 등 비에 대비하는 세심한 당부 멘트를 포함하세요.\n"
            )
        else:
            hook_msg += (
                "(위 내일 날씨를 참고하여, 글 마무리에서 '내일은 비 소식이 있으니 우산을 챙기세요' 같은 "
                "세심한 당부 멘트를 포함하세요.)\n"
            )
            
        return hook_msg

    def _get_semester_context(self):

        """
        현재 날짜를 기준으로 한국 학교 학사 일정(방학/개학) 시즌을 감지하여
        AI에게 적절한 지침(금지어/권장어)을 반환합니다.
        """

        now = datetime.now()
        month = now.month
        day = now.day
        

        # 1. 겨울 방학 & 봄방학 (1월 1일 ~ 2월 28일)
        # - 특징: 학교 안 감. 날씨 추움. 새학기 준비 기간. 졸업 시즌(2월).
        if month in [1, 2]:
            period_name = "겨울방학 및 졸업 시즌"
            instruction = (
                "- [상황] 현재는 초/중/고등학교 '겨울방학' 기간입니다.\n"
                "- [⛔ 금지] '학교 가는 길', '등하교', '급식', '교복' 등 **현재 학교에 다니는 상황**을 묘사하지 마세요.\n"
                "- [✅ 권장] '방학 생활', '가정 보육', '새학기 준비', '졸업 축하', '실내 활동' 등을 소재로 삼으세요.\n"
                "- [💡 필살기] 만약 주제가 '등하교'나 '급식'이라면, 문맥을 **'곧 다가올 새학기엔 이렇게 변해요'** 또는 **'미리 준비하는 꿀팁'**으로 자연스럽게 돌려서 작성하세요."
            )
            
        # 2. 새학기 적응 기간 (3월 1일 ~ 3월 15일)
        # - 특징: 입학식, 개학식, 새로운 친구, 긴장과 설렘. 
        elif month == 3 and day <= 15:
            period_name = "새학기 시작 (적응 기간)"
            instruction = (
                "- [상황] 3월 신학기가 막 시작되었습니다. 입학식과 개학식이 있는 시기입니다.\n"
                "- [✅ 강조] '새로운 출발', '입학 축하', '새 친구', '학교 적응', '등하굣길 안전(교통안전)'을 적극적으로 언급하세요.\n"
                "- [Tip] 학부모님들의 설렘과 걱정을 공감해주는 따뜻한 멘트가 좋습니다."
            )
            
        # 3. 1학기 중반 (3월 16일 ~ 7월 20일)
        # - 특징: 평범한 학기 중. 5월 가정의 달. 6월 호국보훈/초여름.
        elif (month == 3 and day > 15) or month in [4, 5, 6] or (month == 7 and day <= 20):
            # 5월 가정의 달 특수 처리
            if month == 5:
                period_name = "1학기 중 (가정의 달)"
                instruction = (
                    "- [상황] 활기찬 1학기가 진행 중이며, 5월은 가정의 달입니다.\n"
                    "- [✅ 권장] '어린이날', '어버이날', '스승의 날', '가족 나들이', '운동회/체육대회' 관련 소재를 적극 활용하세요."
                )
            else:
                period_name = "1학기 중 (봄/여름)"
                instruction = (
                    f"- [상황] 현재는 {month}월로 활발하게 학기가 진행 중인 시기입니다.\n"
                    "- [✅ 강조] 현재 날짜에 맞는 계절감을 표현하세요. (3~5월: 봄꽃, 산뜻함 / 6~7월: 초여름, 더위 대비)\n"
                    "- [⛔ 금지] 주제에 명시되지 않은 낙법, 줄넘기 등 특정 수련 활동을 임의로 언급하지 마세요."
                )
                return {"period_name": period_name, "instruction": instruction}

        # 4. 여름 방학 (7월 21일 ~ 8월 15일)
        # - 특징: 학교 안 감. 매우 더움. 휴가철.
        elif (month == 7 and day > 20) or (month == 8 and day <= 15):
            period_name = "여름방학 및 휴가 시즌"
            instruction = (
                "- [상황] 현재는 초/중/고등학교 '여름방학' 기간입니다.\n"
                "- [⛔ 금지] '등하교', '학교 급식', '교복' 언급을 피하세요. (학생들이 학교에 가지 않습니다.)\n"
                "- [✅ 권장] '여름 휴가', '물놀이 안전', '냉방병 예방', '폭염 건강 관리', '방학 숙제' 등을 소재로 삼으세요.\n"
                "- [💡 필살기] 만약 '등하교 안전' 같은 주제가 나오면 **'학기 중엔 등하교가 걱정이었지만, 방학 땐 학원 오가는 길 안전이 중요하죠!'** 라고 센스있게 비틀어주세요."
            )
            
        # 5. 2학기 개학 (8월 16일 ~ 8월 31일)
        # - 특징: 짧은 방학 끝, 다시 등교. 처서(가을 기운).
        elif month == 8 and day > 15:
            period_name = "2학기 개학 시즌"
            instruction = (
                "- [상황] 짧은 여름방학이 끝나고 2학기가 시작되는 시기입니다.\n"
                "- [✅ 권장] '개학', '다시 시작된 등교', '2학기 준비', '환절기 건강'을 언급하세요."
            )
            
        # 6. 2학기 중반 & 연말 (9월 1일 ~ 12월 31일)
        # - 특징: 가을 운동회, 소풍, 수능(11월), 학기 마무리.
        else: # 9, 10, 11, 12월
            # 11월 수능 시즌 특수 처리
            if month == 11 and 10 <= day <= 20: # 대략적 수능 기간
                period_name = "2학기 중 (수능 시즌)"
                instruction = (
                    "- [상황] 대학수학능력시험(수능)이 있는 중요한 시기입니다.\n"
                    "- [✅ 권장] '수험생 응원', '합격 기원', '차분한 분위기', '따뜻한 격려'의 메시지를 담으세요."
                )
            # 12월 말 방학 직전
            elif month == 12 and day >= 25:
                period_name = "겨울방학 시작 및 연말"
                instruction = (
                    "- [상황] 한 해를 마무리하고 겨울방학을 맞이하는 시기입니다.\n"
                    "- [✅ 권장] '한 해 정리', '새해 다짐', '크리스마스/연말 인사', '방학 계획'을 언급하세요."
                )
            else:
                return None # 특별한 지침 없는 평시 (가을 학기)

        return {"period_name": period_name, "instruction": instruction}

if __name__ == "__main__":
    # 테스트 코드
    handler = GPTHandler(use_dummy=False)  # 실제 GPT API 사용
    
    test_topics = [
        "태권도 수업의 장점",
        "효과적인 시간 관리 방법",
        "건강한 식습관 만들기"
    ]
    
    for topic in test_topics:
        print(f"\n{'='*50}")
        print(f"주제: {topic}")
        print('='*50)
        
        try:
            result = handler.generate_content(topic)
            print("\n[제목]")
            print(result["title"])
            print("\n[본문]")
            print(result["content"])
        except Exception as e:
            print(f"\n오류 발생: {str(e)}")
        
        print('\n' + '='*50) 