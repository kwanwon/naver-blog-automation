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
from utils.path_utils import get_config_dir, get_log_dir

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
            
            # 앱 번들 경로 확인
            app_bundle_config = get_app_bundle_config_path()
            
            # 여러 경로 시도 (순서 중요: 글로벌 -> 앱 번들 -> 로컬)
            possible_paths = [
                # 1. 🆕 글로벌 설정 경로 (우선순위 1위: AppData/ 표준 경로)
                os.path.join(get_config_dir(), 'gpt_settings.txt'),
                # 1.1 레거시 경로 (마이그레이션용)
                os.path.join(os.path.expanduser("~"), '.blog_automation', 'config', 'gpt_settings.txt'),
            ]
            
            # 2. 🆕 앱 번들 경로 (macOS 빌드된 앱)
            if app_bundle_config:
                possible_paths.append(os.path.join(app_bundle_config, 'gpt_settings.txt'))
            
            # 3. 로컬 개발 환경/레거시 경로
            possible_paths.extend([
                os.path.join(parent_dir, 'config', 'gpt_settings.txt'),
                os.path.join(os.getcwd(), 'config', 'gpt_settings.txt'),
                'config/gpt_settings.txt',
                resource_path('config/gpt_settings.txt')
            ])
            
            settings_path = None
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    settings_path = abs_path
                    break
            
            # 설정 파일이 존재하면 로드
            if settings_path:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
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
            
            # 3. 로컬 개발 환경/레거시 경로
            possible_paths.extend([
                os.path.join(parent_dir, 'config', 'custom_prompts.txt'),
                os.path.join(os.getcwd(), 'config', 'custom_prompts.txt'),
                'config/custom_prompts.txt',
                resource_path('config/custom_prompts.txt')
            ])
            
            prompts_path = None
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    prompts_path = abs_path
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
                            return data['api_key']
                            
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
                weekday_str = weekdays[now.weekday()]
                now_str = now.strftime(f"%Y년 %m월 %d일 ({weekday_str}) %H시 %M분")
                
                system_message += f"\\n[작성 기준 시간(예약): {now_str}]\\n"
                system_message += "\\n[중요: 이 글은 위 '작성 기준 시간'에 업로드될 예약 글입니다. 현재 시간이 아닌 작성 기준 시간(아침/점심/저녁)에 맞춰 인사를 건네세요.]\\n"
            except Exception as e:
                logger.warning(f"타겟 시간 파싱 실패: {target_time}, error: {e}")
                weekday_str = weekdays[now.weekday()]
                now_str = now.strftime(f"%Y년 %m월 %d일 ({weekday_str}) %H시 %M분")
                system_message += f"\\n[현재 시간: {now_str}]\\n"
        else:
            weekday_str = weekdays[now.weekday()]
            now_str = now.strftime(f"%Y년 %m월 %d일 ({weekday_str}) %H시 %M분")
            system_message += f"\\n[현재 시간: {now_str}]\\n"
        
        # 🟢 [HotFix] 블로그/카페 수동 포스팅 시 시간대별 훅 주입
        # custom_system이 없는 경우(즉, generate_platform_content를 거치지 않은 경우)에만 적용
        if platform in ('blog', 'cafe') and (not post_type_config or not post_type_config.get('custom_system')):
            try:
                # 시간대 자동 판별 (task_type이 없거나 기본값이면 현재 시간 기준)
                effective_task_type = task_type
                if not effective_task_type or effective_task_type == 'regular':
                    current_hour = datetime.now().hour
                    if current_hour < 12:
                        effective_task_type = 'morning'
                    elif current_hour < 18:
                        effective_task_type = 'regular'
                    else:
                        effective_task_type = 'closing'
                
                weather_loc = settings.get('weather_location', '')
                
                if effective_task_type == 'morning' and weather_loc:
                    # 오전: 날씨 정보로 시작 (기상청 1순위 → 네이버 폴백)
                    weather_info = self._get_kma_weather(weather_loc)
                    if not weather_info:
                        weather_info = self._get_naver_weather(weather_loc)
                    if weather_info:
                        system_message += (
                            f"\n[System: 실시간 날씨 정보 (기상청/네이버) - 지역: {weather_loc}]\n"
                            f"{weather_info}\n"
                            "(위 날씨 정보를 바탕으로 글의 도입부를 작성하세요.)\n"
                            "[!!! 필수 규칙 !!!]\n"
                            "글의 첫 문단(도입부)은 반드시 위의 날씨 정보로 시작하세요.\n"
                            "⚠️ 절대 위 데이터에 없는 내용(주간 예보, 내일 이후의 날씨 등)을 지어내지 마세요.\n"
                            "그리고 자연스럽게 본론 주제로 연결하세요.\n"
                            "제목 또한 '날씨 + 주제'를 결합하여 클릭을 유도하는 형태로 작성하세요."
                        )
                else:
                    # 오후/저녁: 뉴스/이슈로 시작 + 날씨 참고 정보 포함
                    trending_info = self._get_trending_topics()
                    if trending_info:
                        system_message += (
                            f"\n[System: 오늘의 뉴스/이슈/트렌드]\n"
                            f"{trending_info}\n"
                            "(위 최신 뉴스/이슈 중 하나를 골라 자연스럽게 글의 시작으로 활용하세요.)\n"
                            "[!!! 필수 규칙 !!!]\n"
                            "글의 첫 문단(도입부)은 반드시 위의 뉴스/이슈 중 하나로 시작하세요.\n"
                            "그리고 자연스럽게 본론 주제로 연결하세요.\n"
                            "제목 또한 '뉴스/이슈 + 주제'를 결합하여 클릭을 유도하는 형태로 작성하세요."
                        )
                    
                    # 🟢 오후/저녁에도 실시간 날씨 참고 정보 제공 (할루시네이션 방지)
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
            except Exception as e:
                logger.warning(f"뉴스 훅 주입 실패: {e}")

        base_prompt = f"""주제: {topic}

다음 형식으로 작성:
[제목]
(뉴스/날씨 + 주제를 결합한 클릭유도형 제목)

[본문]
(1문단: 뉴스/날씨 훅으로 시선 끌기 -> 2문단부터: 본론 주제)
...

규칙:
- 마크다운 헤더만 사용(##, ###), HTML 태그 금지
- 자연스러운 흐름, 실용 팁 포함
- 깔끔한 마무리와 명언 포함
- **시간대 인사 금지** (좋은 아침입니다 등) -> 뉴스/날씨로 바로 시작
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
                    # 밴드는 task_type이 morning일 때만 설정된 첫 문장(보통 아침 인사)을 사용
                    # 만약 task_type이 없거나 morning이면 적용, regular/closing이면 미적용
                    if task_type == 'morning' or not task_type:
                        first_sentence = user_settings.get('band_first_sentence', '').strip()
                    else:
                        logger.info(f"밴드 {task_type} 작업이므로 설정된 첫 문장(아침 인사)을 건너뜁니다.")
                        first_sentence = ""
                elif platform in ['drive_auto', 'manual_topic']:
                    # 🟢 드라이브 자동포스팅/수동주제 포스팅은 밴드에 올라가므로 밴드 첫 문장 사용
                    first_sentence = user_settings.get('band_first_sentence', '').strip()
                    if first_sentence:
                        logger.info(f"드라이브 자동포스팅에 밴드 첫 문장 적용: {first_sentence[:30]}...")
                
                if first_sentence:
                     body = f"{first_sentence}\n\n{body}"
                
                # 플랫폼별 슬로건(마지막 문구) 추가
                slogan = ""
                if platform == 'blog':
                    # 블로그는 naver_blog_auto.py가 'slogan' 설정을 읽어서 처리하므로 여기선 추가하지 않음 (중복 방지)
                    pass 
                elif platform == 'cafe':
                    slogan = user_settings.get('cafe_slogan', '').strip()
                elif platform == 'band':
                    slogan = user_settings.get('band_slogan', '').strip()
                elif platform in ['drive_auto', 'manual_topic']:
                    # 🟢 드라이브 자동포스팅/수동주제 포스팅은 밴드 슬로건 사용
                    slogan = user_settings.get('band_slogan', '').strip()
                
                if slogan:
                    body = f"{body}\n\n{slogan}"
                
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
        
        # 🟢 밴드 지침 수정: '아침 희망 메시지' 등 특정 시간대 강제 문구가 있으면 제거/수정
        band_instr = settings.get('band_instructions', "밴드 멤버들과 소통하기 좋은 친근하고 간결한 스타일로 작성해주세요.")
        if platform == 'band':
            # '아침'이라는 단어가 포함되어 있고 태스크 타입이 아침이 아니면, '아침' 관련 문구 무력화
            if '아침' in band_instr and task_type not in ['morning', 'regular_morning']:
                 band_instr = band_instr.replace('아침', '일상') # 아침 -> 일상으로 단순 치환
                 band_instr += "\n(주의: 이 지침의 '아침' 관련 내용은 무시하고, 아래 [필수 요구사항]의 시간대를 따르세요.)"

        # 플랫폼별 시스템 메시지 조정 (사용자 설정 우선)
        platform_instructions = {
            'blog': settings.get('instructions', "자세하고 정보가 풍부한 블로그 포스트 스타일로 작성해주세요."),
            'band': band_instr,
            'cafe': settings.get('cafe_instructions', "카페 게시판 성격에 맞는 예의 바르고 정보 공유적인 스타일로 작성해주세요."),
            'idle': settings.get('idle_instructions', "블로그 이웃 소통을 위해 친근하고 짧은 응원 댓글을 작성해주세요."),
            # 🟢 드라이브 자동포스팅 전용 지침
            'drive_auto': settings.get('drive_auto_instructions', "수련 사진과 함께 올리는 짧고 따뜻한 글을 작성해주세요. 200~300자 내외로 간결하게."),
            # 🟢 수동 주제 포스팅 전용 지침 (블로그 지침 사용 안 함)
            'manual_topic': "네이버 밴드에 올리는 짧고 따뜻한 글을 작성하세요. 150~250자 내외로 간결하게."
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
        
        # 🟢 블로그/드라이브 자동포스팅/수동주제포스팅은 시간대 인사 불필요
        if platform in ['blog', 'drive_auto', 'manual_topic']:
            time_instruction = ""  # 시간대 인사 없음
        else:
            time_instruction = task_instructions.get(task_type, task_instructions['regular'])
        
        system_message = (
            f"당신은 {platform} 운영자입니다.\n"
            f"페르소나: {settings['persona']}\n"
            f"플랫폼 지침: {platform_instructions.get(platform, platform_instructions['blog'])}\n"
            f"스타일: {settings['style']}\n\n"
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
                            target_dt = datetime.now().replace(hour=t.hour, minute=t.minute, second=0)
                            if target_dt < datetime.now():
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
                        "⚠️ 절대 위 데이터에 없는 주간 예보나 다른 날짜의 날씨를 지어내지 마세요.)"
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
                        "- 만약 검색된 뉴스가 모두 그런 내용이라면, 차라리 '오늘의 생활 건강 팁'으로 주제를 변경하세요."
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
                            target_dt = datetime.now().replace(hour=t.hour, minute=t.minute, second=0)
                            if target_dt < datetime.now():
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
                            "예: '오늘 아침은 영하 3도로 춥습니다, 따뜻한 하루 보내세요' 등 구체적 언급 필수)"
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
                "✅ [블로그 상위노출 및 체류시간 증대 전략 적용]\n"
                "1. **상위노출(Exposure)**: 주제 키워드({topic})가 첫 문단에 반드시 1회, 본문 전체에 3~4회 자연스럽게 포함되도록 하세요.\n"
                "2. **클릭률(CTR)**: 제목은 [뉴스/날씨/이슈]와 [본론 주제]를 결합하되, 호기심을 자극하거나 이득을 강조하세요. (예: '오늘 비 오는데 OO 운동이 좋은 이유?', '요즘 뜨는 뉴스 속 OO의 비밀')\n"
                "3. **가독성(체류시간)**: 문단은 3~4줄 이내로 짧게 끊고, 핵심 내용은 **굵게 표시**하세요. 중간중간 글머리 기호(•)를 사용하세요.\n"
                "4. **소통 유도**: 글 마지막에 독자에게 건네는 가벼운 질문(예: '여러분은 어떻게 생각하시나요?')으로 댓글을 유도하세요.\n\n"
                "✅ 필수 규칙: 글의 첫 문단은 반드시 오늘의 뉴스 또는 날씨 이야기로 시작하세요.\n"
                "그리고 '그래서/이럴 때일수록/이런 시기에' 등의 연결어로 자연스럽게 본론 주제로 넘어가세요.\n\n"
                "반드시 아래 형식을 지켜서 출력해:\n\n"
                "[제목]\n"
                "(위 전략이 반영된 매력적인 제목)\n\n"
                "[본문]\n"
                "(1문단: 뉴스/날씨 훅 + 키워드 -> 2문단부터: 본론 + 가독성 장치 -> 마지막: 소통 질문)\n\n"
                "주의: 시간대 인사(좋은 아침 등)는 사용하지 마세요.\n"
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
        else:
            user_prompt = (
                f"주제: {topic}\n\n"
                "✅ 필수 규칙: 글의 첫 문단은 반드시 오늘의 뉴스 또는 날씨 이야기로 시작하세요.\n"
                "그리고 '그래서/이럴 때일수록/이런 시기에' 등의 연결어로 자연스럽게 본론 주제로 넘어가세요.\n\n"
                "반드시 아래 형식을 지켜서 출력해:\n\n"
                "[제목]\n"
                "(뉴스/날씨 + 주제를 결합한 클릭유도형 제목)\n\n"
                "[본문]\n"
                "(1문단: 뉴스/날씨 훅으로 시선 끌기 -> 2문단부터: 본론 주제)\n\n"
                "중요: 시간대 지침을 반드시 지켜주세요! \n"
                "- morning(오전) 유형이면 날씨 정보를 훅으로 활용\n"
                "- regular(오후) 유형이면 뉴스/이슈를 훅으로 활용\n"
                "- closing(마감/저녁) 유형이면 뉴스/이슈를 훅으로 활용\n\n"
                f"주의: \"함께 공부하며 지식을 나누는 한국체대 라이온 블로거 입니다\" 문구는\n"
                f"블로그 전용이므로, {platform}용 글에는 절대 포함하지 마세요.\n"
            )
        
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

<<<<<<< HEAD
    def generate_reply(self, system_prompt: str, user_text: str, max_tokens: int = 150, selected_models: list = None) -> str:
        """
        간단한 댓글 답글 생성용 메서드 (모델 순환 및 재시도 로직 적용)
        """
=======
    def generate_reply(self, system_prompt: str, user_text: str, max_tokens: int = 150) -> str:
        # 간단한 댓글 답글 생성용 메서드 (모델 순환 및 재시도 로직 적용)
>>>>>>> 8454879e8bd28d218ab65b03c524a12294c072f6
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
        """기상청 단기예보 API를 사용한 날씨 정보 조회
        
        forecast=True: 내일 예보 / False: 현재(오늘) 날씨
        1순위 날씨 소스. 실패 시 None 반환 → 네이버 폴백 사용
        """
        settings = self._load_settings()
        api_key = settings.get('kma_api_key', '')
        if not api_key:
            logger.info("기상청 API 키 미설정, 네이버 폴백 사용")
            return None
        
        # 지역명 → 격자좌표 매핑
        nx, ny = None, None
        
        # 정확한 매칭 시도
        for key, coords in self.KMA_GRID_MAP.items():
            if key in location or location in key:
                nx, ny = coords
                break
        
        # 부분 매칭 시도 (ex: "인천 부평구" → "부평구" 매칭)
        if nx is None:
            for part in location.split():
                if part in self.KMA_GRID_MAP:
                    nx, ny = self.KMA_GRID_MAP[part]
                    break
        
        if nx is None:
            logger.warning(f"기상청 격자좌표 매핑 실패: {location}, 기본값(서울) 사용")
            nx, ny = 60, 127  # 서울 기본값
        
        try:
            now = datetime.now()
            
            # 발표 시각 계산 (단기예보: 0200, 0500, 0800, 1100, 1400, 1700, 2000, 2300)
            base_times = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]
            current_hhmm = now.strftime("%H%M")
            
            # 가장 최근 발표 시각 찾기 (10분 여유)
            base_time = "2300"  # 기본값
            base_date = now.strftime("%Y%m%d")
            
            for bt in reversed(base_times):
                # API 발행시각보다 10분 이후에 데이터가 준비됨
                adjusted_bt = str(int(bt) + 10).zfill(4)
                if current_hhmm >= adjusted_bt:
                    base_time = bt
                    break
            else:
                # 자정~02:10 사이: 전날 23시 발표
                base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
                base_time = "2300"
            
            # forecast=True면 내일 예보
            if forecast:
                fcst_date = (now + timedelta(days=1)).strftime("%Y%m%d")
            else:
                fcst_date = now.strftime("%Y%m%d")
            
            # API 호출
            api_url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
            params = {
                "serviceKey": api_key,
                "numOfRows": 300,
                "pageNo": 1,
                "dataType": "JSON",
                "base_date": base_date,
                "base_time": base_time,
                "nx": nx,
                "ny": ny
            }
            
            query_string = urllib.parse.urlencode(params)
            full_url = f"{api_url}?{query_string}"
            
            req = urllib.request.Request(full_url)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            # 응답 검증
            result_code = data.get('response', {}).get('header', {}).get('resultCode', '')
            if result_code != '00':
                result_msg = data.get('response', {}).get('header', {}).get('resultMsg', '')
                logger.warning(f"기상청 API 오류: {result_code} - {result_msg}")
                return None
            
            items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if not items:
                logger.warning("기상청 API: 데이터 없음")
                return None
            
            # 필요한 필드 추출
            # TMP: 기온, SKY: 하늘상태(1맑음,3구름많음,4흐림), POP: 강수확률, PTY: 강수형태
            sky_map = {"1": "맑음", "3": "구름많음", "4": "흐림"}
            pty_map = {"0": "없음", "1": "비", "2": "비/눈", "3": "눈", "4": "소나기"}
            
            # 날짜별 데이터 수집
            weather_data = {}
            for item in items:
                cat = item.get('category', '')
                fdate = item.get('fcstDate', '')
                ftime = item.get('fcstTime', '')
                fvalue = item.get('fcstValue', '')
                
                key = f"{fdate}_{ftime}"
                if key not in weather_data:
                    weather_data[key] = {}
                weather_data[key][cat] = fvalue
            
            if forecast:
                # --- 내일 예보 (예약 포스팅용) ---
                tomorrow_temps = []
                tomorrow_sky = ""
                tomorrow_pop = ""
                morning_temp = None
                
                # 06~09시 사이의 기온을 '아침 기온'으로 간주
                target_morning_hours = ['0600', '0700', '0800', '0900']
                
                for key, vals in sorted(weather_data.items()):
                    if not key.startswith(fcst_date):
                        continue
                    
                    ftime = key.split('_')[1]
                    tmp = vals.get('TMP', vals.get('T1H', ''))
                    
                    if tmp:
                        try:
                            tomorrow_temps.append(float(tmp))
                        except ValueError:
                            pass
                    
                    # 오전 6~9시 기준 날씨
                    if ftime in target_morning_hours:
                        if tmp and morning_temp is None:
                            morning_temp = float(tmp)
                        sky_code = vals.get('SKY', '')
                        if sky_code:
                            morning_sky = sky_map.get(sky_code, sky_code)
                        pop_val = vals.get('POP', '')
                        if pop_val:
                            tomorrow_pop = pop_val
                
                if tomorrow_temps:
                    min_temp = min(tomorrow_temps)
                    max_temp = max(tomorrow_temps)
                    
                    # 오전 날씨가 없으면 첫 번째 값 사용
                    if not tomorrow_sky:
                        for key, vals in sorted(weather_data.items()):
                            if key.startswith(fcst_date):
                                sky_code = vals.get('SKY', '')
                                if sky_code:
                                    tomorrow_sky = sky_map.get(sky_code, sky_code)
                                    break
                    
                    result_text = (
                        f"[{location} 내일 날씨 예보 (기상청)]\n"
                        f"지역: {location}\n"
                        f"날씨: {tomorrow_sky if tomorrow_sky else '확인중'}, "
                        f"최저/최고: {min_temp:.0f}/{max_temp:.0f}도"
                    )
                    if morning_temp is not None:
                        result_text += f", 오전 기온: {morning_temp:.1f}도"
                    if tomorrow_pop:
                        result_text += f", 강수확률: {tomorrow_pop}%"

                    # 🟢 오늘(비교 대상) 아침 기온 구하기 (비교 로직)
                    today_morning_temp = None
                    try:
                        for key, vals in sorted(weather_data.items()):
                            if not key.startswith(compare_date): # 오늘 날짜
                                continue
                            ftime = key.split('_')[1]
                            if ftime in target_morning_hours:
                                t_tmp = vals.get('TMP', vals.get('T1H', ''))
                                if t_tmp:
                                    today_morning_temp = float(t_tmp)
                                    break # 가장 빠른 아침 시간대 하나만 잡음
                        
                        if today_morning_temp is not None and morning_temp is not None:
                            diff = morning_temp - today_morning_temp
                            if diff > 0:
                                result_text += f"\\n어제(오늘) 같은 아침보다 {abs(diff):.1f}도 높습니다 (↑상승)"
                            elif diff < 0:
                                result_text += f"\\n어제(오늘) 같은 아침보다 {abs(diff):.1f}도 낮습니다 (↓하강)"
                            else:
                                result_text += f"\\n어제(오늘) 아침과 비슷한 기온입니다"
                    except Exception as e:
                        logger.warning(f"내일 예보 비교 로직 실패: {e}")

                    logger.info(f"기상청 내일 예보 성공: {location} (비교 포함)")
                    return result_text
                else:
                    logger.warning("기상청 내일 예보: 기온 데이터 없음")
                    return None
            else:
                # --- 오늘 날씨 ---
                today_temps = []
                current_sky = ""
                current_temp = ""
                current_pop = ""
                
                # 현재 시간에 가장 가까운 시간대 찾기
                current_hour = now.strftime("%H00")
                closest_key = None
                first_future_key = None  # 현재 이후 가장 가까운 시간대 (폴백용)
                
                for key in sorted(weather_data.keys()):
                    if key.startswith(fcst_date):
                        ftime = key.split('_')[1]
                        if ftime <= current_hour:
                            closest_key = key
                        elif first_future_key is None:
                            first_future_key = key  # 현재 이후 첫 번째 시간대
                        
                        tmp = weather_data[key].get('TMP', weather_data[key].get('T1H', ''))
                        if tmp:
                            try:
                                today_temps.append(float(tmp))
                            except ValueError:
                                pass
                
                # 현재/과거 시간대가 없으면 가장 가까운 미래 시간대 사용
                if closest_key is None and first_future_key is not None:
                    closest_key = first_future_key
                
                if closest_key and closest_key in weather_data:
                    vals = weather_data[closest_key]
                    current_temp = vals.get('TMP', vals.get('T1H', '?'))
                    sky_code = vals.get('SKY', '')
                    current_sky = sky_map.get(sky_code, sky_code) if sky_code else ""
                    pty_code = vals.get('PTY', '0')
                    if pty_code and pty_code != '0':
                        current_sky = pty_map.get(pty_code, current_sky)
                    current_pop = vals.get('POP', '')
                
                if today_temps:
                    min_temp = min(today_temps)
                    max_temp = max(today_temps)
                else:
                    min_temp = "?"
                    max_temp = "?"
                
                # 🟢 어제 같은 시간대 기온 조회 (비교용)
                yesterday_temp = None
                try:
                    yesterday = now - timedelta(days=1)
                    yday_date = yesterday.strftime("%Y%m%d")
                    # 어제 가장 가까운 발표 시각 사용
                    yday_base_time = "0500"  # 어제 05시 발표 기준 (충분한 데이터)
                    yday_params = {
                        "serviceKey": api_key,
                        "numOfRows": 300,
                        "pageNo": 1,
                        "dataType": "JSON",
                        "base_date": yday_date,
                        "base_time": yday_base_time,
                        "nx": nx,
                        "ny": ny
                    }
                    yday_url = f"{api_url}?{urllib.parse.urlencode(yday_params)}"
                    yday_req = urllib.request.Request(yday_url)
                    with urllib.request.urlopen(yday_req, timeout=8) as yday_response:
                        yday_data = json.loads(yday_response.read().decode('utf-8'))
                    
                    yday_items = yday_data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
                    
                    # 어제 같은 시간대 기온 찾기
                    target_hour = now.strftime("%H00")
                    for item in yday_items:
                        if (item.get('fcstDate') == yday_date and 
                            item.get('fcstTime') == target_hour and 
                            item.get('category') == 'TMP'):
                            yesterday_temp = float(item.get('fcstValue', ''))
                            break
                    
                    # 같은 시간대 못 찾으면 ±1시간 범위 탐색
                    if yesterday_temp is None:
                        hour_int = int(now.strftime("%H"))
                        for offset in [-1, 1, -2, 2]:
                            check_hour = f"{(hour_int + offset) % 24:02d}00"
                            for item in yday_items:
                                if (item.get('fcstDate') == yday_date and 
                                    item.get('fcstTime') == check_hour and 
                                    item.get('category') == 'TMP'):
                                    yesterday_temp = float(item.get('fcstValue', ''))
                                    break
                            if yesterday_temp is not None:
                                break
                                
                except Exception as e:
                    logger.info(f"어제 기온 조회 실패 (무시): {e}")
                
                # 결과 텍스트 조립
                result_text = (
                    f"[{location} 현재 날씨 (기상청 단기예보)]\n"
                    f"지역: {location}\n"
                    f"현재 기온: {current_temp}도 ({current_sky})\n"
                    f"최저/최고: {min_temp if isinstance(min_temp, str) else f'{min_temp:.0f}'}"
                    f"/{max_temp if isinstance(max_temp, str) else f'{max_temp:.0f}'}도"
                )
                if current_pop:
                    result_text += f"\n강수확률: {current_pop}%"
                
                # 🟢 어제 비교 추가
                if yesterday_temp is not None and current_temp != '?':
                    try:
                        today_val = float(current_temp)
                        diff = today_val - yesterday_temp
                        if diff > 0:
                            result_text += f"\n어제 같은 시간({yesterday_temp:.0f}도)보다 {abs(diff):.1f}도 높습니다 (↑상승)"
                        elif diff < 0:
                            result_text += f"\n어제 같은 시간({yesterday_temp:.0f}도)보다 {abs(diff):.1f}도 낮습니다 (↓하강)"
                        else:
                            result_text += f"\n어제 같은 시간과 동일한 기온입니다"
                    except (ValueError, TypeError):
                        pass
                
                logger.info(f"기상청 오늘 날씨 성공: {location} → nx={nx},ny={ny}")
                return result_text
            
        except Exception as e:
            logger.warning(f"기상청 API 날씨 조회 실패: {e}")
            return None

    def _get_naver_weather(self, location="서울", forecast=False):
        # 네이버 날씨 크롤링 (urllib 사용, SSL 무시)
        # forecast=True: 내일 오전 예보 / False: 현재 날씨
        try:
            query = urllib.parse.quote(f"{location} 날씨")
            url = f"https://search.naver.com/search.naver?query={query}"
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                html = response.read().decode('utf-8')
            
            # --- 현재 날씨 (기본) ---
            # 1. 현재 온도
            temp_match = re.search(r'class="temperature_text">.*?<span class="blind">현재 온도</span>(.*?)(?:<span|\xb0)', html, re.DOTALL)
            current_temp = temp_match.group(1).strip() if temp_match else "?"
            
            # 2. 날씨 상태 (흐림, 맑음 등)
            status_match = re.search(r'class="weather before_slash">(.*?)<', html)
            weather_status = status_match.group(1).strip() if status_match else ""

            # 3. 미세먼지
            dust_match = re.search(r'미세먼지.*?class="txt">(.*?)<', html, re.DOTALL)
            fine_dust = dust_match.group(1).strip() if dust_match else "?"

            # 4. 초미세먼지
            ultra_dust_match = re.search(r'초미세먼지.*?class="txt">(.*?)<', html, re.DOTALL)
            ultra_dust = ultra_dust_match.group(1).strip() if ultra_dust_match else "?"
            
            # 5. 최저/최고 기온
            min_match = re.search(r'최저기온</span>(.*?)(?:\xb0|<)', html)
            max_match = re.search(r'최고기온</span>(.*?)(?:\xb0|<)', html)
            min_temp = min_match.group(1).strip() if min_match else "?"
            max_temp = max_match.group(1).strip() if max_match else "?"
            
            if forecast:
                # --- 내일 예보 추출 시도 ---
                # 네이버 날씨 페이지에서 내일 최저/최고/상태 추출
                tomorrow_min = "?"
                tomorrow_max = "?"
                tomorrow_status = ""
                
                # 내일 기온: "내일" 이후 최저/최고
                tomorrow_section = re.search(r'내일(.*?)(?:모레|<\/div>)', html, re.DOTALL)
                if tomorrow_section:
                    t_block = tomorrow_section.group(1)
                    t_min = re.search(r'최저기온</span>(.*?)(?:\xb0|<)', t_block)
                    t_max = re.search(r'최고기온</span>(.*?)(?:\xb0|<)', t_block)
                    t_stat = re.search(r'class="weather">(.*?)<', t_block)
                    if t_min:
                        tomorrow_min = t_min.group(1).strip()
                    if t_max:
                        tomorrow_max = t_max.group(1).strip()
                    if t_stat:
                        tomorrow_status = t_stat.group(1).strip()
                
                # 내일 예보가 파싱 안 되면 오늘 정보로 대체
                if tomorrow_min == "?" and tomorrow_max == "?":
                    return (
                        f"[내일 예보 미확인 - 오늘 기준 참고]\n"
                        f"현재: {current_temp}도 ({weather_status}), "
                        f"최저/최고: {min_temp}/{max_temp}도, "
                        f"미세먼지: {fine_dust}, 초미세먼지: {ultra_dust}"
                    )
                
                return (
                    f"[내일 날씨 예보]\n"
                    f"날씨: {tomorrow_status if tomorrow_status else '확인중'}, "
                    f"최저/최고: {tomorrow_min}/{tomorrow_max}도\n"
                    f"[오늘 기준 대기질] 미세먼지: {fine_dust}, 초미세먼지: {ultra_dust}"
                )
            else:
                # --- 현재 날씨 반환 ---
                return (
                    f"현재 기온: {current_temp}도 ({weather_status})\n"
                    f"최저/최고: {min_temp}/{max_temp}도\n"
                    f"미세먼지: {fine_dust}, 초미세먼지: {ultra_dust}"
                )
            
        except Exception as e:
            logger.warning(f"날씨 크롤링 실패: {e}")
            return None
    
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

    def _get_trending_topics(self, count=3):
        # 오후/저녁용: 최신 뉴스/이슈/트렌드 정보 수집
        # count: 가져올 뉴스 수 (기본 3, 배치 분배용 6)
        try:
            # 1순위: Brave Search로 오늘의 핫이슈 검색
            brave_result = self._search_brave("오늘 뉴스 이슈 트렌드", count=count * 2) # 필터링 고려해 더 많이 검색
            if brave_result:
                # 🟢 코드 레벨 필터링 적용
                lines = brave_result.split('\n')
                filtered_lines = []
                for line in lines:
                    if not self._filter_news_content(line):
                        filtered_lines.append(line)
                
                if filtered_lines:
                    return "\n".join(filtered_lines[:count])
            
            # 2순위: 네이버 실시간 검색어/인기 검색어 크롤링
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
                    filtered_news = []
                    for title in news_titles:
                        if not self._filter_news_content(title):
                            filtered_news.append(title)
                    
                    if filtered_news:
                        top_news = filtered_news[:count]
                        lines = []
                        for i, title in enumerate(top_news, 1):
                            lines.append(f"{i}. {title}")
                        return "\n".join(lines)
            except Exception:
                pass
            
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