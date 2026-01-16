from config.config import Config
import logging
import random
import os
import sys
import json
import time
import traceback
from datetime import datetime
from typing import Any, List

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

class GPTHandler:
    def __init__(self, use_dummy=False):
        """GPT 핸들러를 초기화합니다."""
        self.use_dummy = use_dummy
        self.settings = self._load_settings()
        
        # 🆕 크로스 플랫폼: 상대 경로 사용
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        self._log_path = os.path.join(parent_dir, 'logs', 'debug.log')
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
        # 삭제된/미지원 모델 정리
        self.selected_models = [
            m for m in self.selected_models if m in Config.AI_MODELS
        ]
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

    def _load_settings(self):
        """GPT 설정을 로드합니다."""
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
            
            # 여러 경로 시도
            possible_paths = [
                os.path.join(parent_dir, 'config', 'gpt_settings.txt'),
                os.path.join(os.getcwd(), 'config', 'gpt_settings.txt'),
                'config/gpt_settings.txt',
                resource_path('config/gpt_settings.txt')
            ]
            
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
        """커스텀 프롬프트를 로드합니다."""
        custom_prompts = {}
        
        try:
            # 스크립트 파일의 위치를 기준으로 경로 계산
            script_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(script_dir)
            
            # 여러 경로 시도
            possible_paths = [
                os.path.join(parent_dir, 'config', 'custom_prompts.txt'),
                os.path.join(os.getcwd(), 'config', 'custom_prompts.txt'),
                'config/custom_prompts.txt',
                resource_path('config/custom_prompts.txt')
            ]
            
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

    def _load_user_settings(self):
        """사용자 설정을 로드합니다."""
        user_settings = {}
        
        try:
            # 스크립트 파일의 위치를 기준으로 경로 계산
            script_dir = os.path.dirname(os.path.abspath(__file__))  # modules 디렉토리
            parent_dir = os.path.dirname(script_dir)  # naver-blog-automation 디렉토리
            
            # 다양한 경로 시도 (더 robust하게)
            possible_paths = [
                # 상대 경로들
                os.path.join(parent_dir, 'config', 'user_settings.txt'),
                os.path.join(os.getcwd(), 'config', 'user_settings.txt'),
                os.path.join(script_dir, '..', 'config', 'user_settings.txt'),
                # 레거시 경로들
                'config/user_settings.txt',
                './config/user_settings.txt',
                '../config/user_settings.txt',
                # 리소스 경로
                resource_path('config/user_settings.txt'),
                # 절대 경로 시도
                os.path.abspath(os.path.join(parent_dir, 'config', 'user_settings.txt'))
            ]
            
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

    def generate_content(self, topic, post_order=1, post_type_config=None, platform='blog', task_type=None):
        """주어진 주제로 블로그 콘텐츠를 생성합니다."""
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
"""
        base_prompt = f"""주제: {topic}

다음 형식으로 작성:
[제목]
...
[본문]
...

규칙:
- 마크다운 헤더만 사용(##, ###), HTML 태그 금지
- 자연스러운 흐름, 실용 팁 포함
- 깔끔한 마무리와 명언 포함
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
                    content = self._generate_with_gemini(model_name, system_message, user_prompt)
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
        """기존 블로그 콘텐츠 생성 (alias)"""
        return self.generate_content(topic, post_order, post_type_config, platform='blog')

    def generate_platform_content(self, topic, platform='blog', task_type='regular'):
        """플랫폼별 맞춤형 콘텐츠 생성"""
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
            'morning': """[오전/아침 포스팅 필수 요구사항]
- 반드시 "좋은 아침", "상쾌한 하루", "오늘 하루도", "아침 에너지" 등 아침/오전과 관련된 인사와 메시지를 포함해주세요.
- 하루를 시작하는 활기차고 긍정적인 톤으로 작성해주세요.
- 예시: "좋은 아침이에요!", "상쾌한 하루 시작하세요!", "오늘도 힘찬 하루 되세요!"
- 절대 저녁, 밤, 마무리, 오늘도 수고하셨습니다 등의 표현을 사용하지 마세요.""",
            
            'regular': """[오후/일반 포스팅 필수 요구사항]
- "오후", "점심 후", "한낮", "활기찬 오후" 등 오후 시간대에 맞는 인사를 포함해주세요.
- 주제와 관련된 유익한 정보를 중심으로 작성해주세요.
- 예시: "활기찬 오후 보내고 계신가요?", "좋은 오후입니다!", "오후에도 화이팅!"
- 아침 인사나 저녁 마무리 인사는 사용하지 마세요.""",
            
            'closing': """[저녁/마감 포스팅 필수 요구사항]
- 반드시 "오늘 하루도 수고하셨습니다", "편안한 저녁", "굿나잇", "내일 또 만나요" 등 저녁/마감과 관련된 인사를 포함해주세요.
- 하루를 마무리하는 차분하고 따뜻한 톤으로 작성해주세요.
- 예시: "오늘도 수고 많으셨어요!", "편안한 저녁 되세요!", "내일도 좋은 하루 되세요!"
- 절대 좋은 아침, 하루 시작 등의 아침 표현을 사용하지 마세요."""
        }
        
        # 🟢 블로그/드라이브 자동포스팅/수동주제포스팅은 시간대 인사 불필요
        if platform in ['blog', 'drive_auto', 'manual_topic']:
            time_instruction = ""  # 시간대 인사 없음
        else:
            time_instruction = task_instructions.get(task_type, task_instructions['regular'])
        
        system_message = f"""당신은 {platform} 운영자입니다.
페르소나: {settings['persona']}
플랫폼 지침: {platform_instructions.get(platform, platform_instructions['blog'])}
스타일: {settings['style']}

{time_instruction}
"""
        
        # 🟢 플랫폼별 user_prompt 분리
        if platform == 'blog':
            user_prompt = f"""주제: {topic}

위 주제와 지침에 맞춰서 {platform}에 올릴 글을 작성해줘.
반드시 아래 형식을 지켜서 출력해:

[제목]
(여기에 주제와 어울리는 강력한 제목 작성)

[본문]
(여기에 본문 내용 작성)

주의: 시간대 인사(좋은 아침, 좋은 오후, 활기찬 오후 등)는 사용하지 마세요. 주제에 바로 들어가세요.
"""
        elif platform == 'drive_auto':
            # 🟢 드라이브 자동포스팅 + 수동주제포스팅 전용
            # topic에서 폴더명(시간대) 추출 시도
            folder_hint = ""
            training_content = ""
            
            # 🥋 종목 설정값 가져오기 (기본값: 합기도)
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
                user_prompt = f"""주제: {topic}

### 오늘의 활동 내용:
{training_content if training_content else "(활동내용 없음)"}

위 내용을 바탕으로 밴드 글을 작성해줘.

[제목]
(짧고 따뜻한 제목, "{training_content}"를 언급)

[본문]
(200~300자 내외로 간결하게 작성)

🎯 특별활동 글쓰기 규칙:
1. **"{training_content}"가 핵심 주제** - 이 활동에 대해서만 작성
2. 운동/수련 관련 내용(셔틀런, 스트레칭, 품새, 격파 등)은 언급하지 마세요 (오늘은 특별활동입니다)
3. 아이들이 즐겁게 활동하는 모습 묘사
4. 키즈카페면 → 재미있는 놀이, 친구들과의 교류
5. 캠프면 → 새로운 경험, 협동심, 즐거운 추억
6. 학부모님께 감사 인사
7. 이모지는 1~2개만 사용
8. 맞춤법: 캠프(O) 갬프(X), 키즈카페(O)
9. 이 체육관의 종목은 {gym_sport}입니다 (다른 종목 용어 사용 금지)
10. **어투: "~습니다", "~했습니다", "~였습니다" 형식 사용 (해요체 금지)**

📌 올바른 예시:
"오늘 {folder_hint} 친구들과 함께 {training_content}을 다녀왔습니다. 아이들이 즐겁게 활동했으며, 좋은 추억을 만들었습니다. 참여해주신 학부모님들께 감사드립니다."
"""
            else:
                # 일반 수련용 프롬프트
                user_prompt = f"""주제: {topic}

### 오늘의 수련 내용 (핵심 주제):
{training_content if training_content else "(수련내용 없음)"}

위 주제에 맞춰서 수련 사진/영상과 함께 올릴 밴드 글을 작성해줘.

⚠️ 중요: 이 체육관의 주 종목은 **{gym_sport}**입니다!

[제목]
(짧고 따뜻한 제목, "{folder_hint}" 시간대와 오늘 수련 내용을 언급)

[본문]
(200~300자 내외로 간결하게 작성)

🔥 중요 규칙:
1. **오늘의 수련 내용({training_content})을 반드시 본문에서 구체적으로 언급**
2. 수련 내용의 효과/의미를 간단히 설명
3. 아이들이 해당 수련을 열심히 하는 모습 칭찬
4. "{folder_hint}" 시간대를 제목과 본문 첫 부분에서 언급
5. 학부모님께 감사 인사
6. 시간대 인사(좋은 아침, 좋은 오후 등)는 사용하지 마세요
7. 이모지는 1~2개만 사용
8. 매일 다른 표현과 내용으로 작성 (반복적인 문구 사용 금지)
9. **다른 종목(태권도, 유도 등)의 용어는 사용하지 마세요** - 오직 {gym_sport} 관련 용어만 사용
10. **어투: "~습니다", "~했습니다", "~였습니다" 형식 사용 (해요체 "~요" 금지)**

📌 올바른 예시:
"오늘 {folder_hint} 친구들과 함께 {training_content} 수련을 진행했습니다. 모두 열심히 참여했으며, 기술이 한층 성장했습니다. 응원해주시는 학부모님들께 감사드립니다. 🥋"
"""
        elif platform == 'manual_topic':
            # 🟢 수동 주제 포스팅 전용 - 사용자 입력 주제 기반 (밴드용 짧은 글)
            # topic에서 카테고리 추출
            category_hint = ""
            main_topic = topic
            
            if "[" in topic and "]" in topic:
                category_hint = topic.split("]")[0].replace("[", "").strip()
                main_topic = topic.split("]")[1].strip() if "]" in topic else topic
            
            # 🥋 종목 설정값 가져오기
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
            
            user_prompt = f"""당신은 네이버 밴드에 짧은 글을 쓰는 작가입니다.

📋 카테고리: {category_hint if category_hint else "일반"}
📋 주제: {main_topic}
📋 종목 안내: {sport_instruction}

⛔ 절대 금지 사항:
- 블로그처럼 길게 쓰지 마세요
- "알려드릴게요", "함께해요" 같은 표현 금지
- 시간대 인사(좋은 아침, 활기찬 오후 등) 금지
- 마크다운 헤딩(###) 사용 금지
- 소제목 나누기 금지
- **대상 언급 금지** (회원님들, 친구들, 어린이들, 수련생들, 학부모님 등 대상 표현 사용 금지)
- 설명이나 효능을 나열하듯 길게 쓰지 마세요

✅ 반드시 지켜야 할 규칙:
1. 전체 글 길이: 250~300자 (5~6문장)
2. **수업 내용**에 대해 간단히 소개
3. 사용자가 입력한 **모든 활동**을 언급 (요가, 외발자전거 등 누락 금지)
4. **효과/효능**을 자연스럽게 언급 (유연성, 균형감각, 근력 등)
5. **건강/다이어트 관련** 내용 포함
6. 따뜻하고 부드러운 어투로 마무리
7. **매번 다른 표현과 내용** 사용 (같은 활동이라도 매번 새로운 관점, 다른 표현으로 작성)

💡 다양성을 위한 표현 예시:
- 시작: "오늘 수업에서는...", "이번 시간에는...", "활기찬 수업 시간..."
- 효과: "유연성이 좋아지는...", "몸이 가벼워지는...", "균형감각을 키우는..."
- 마무리: "건강한 하루 되세요!", "활기찬 하루 보내세요!", "오늘도 건강하게!"

🎨 형식:
[제목]
(이모지 1개 + 짧은 제목)

[본문]
(250~300자, 5~6문장의 짧고 따뜻한 글)

📌 올바른 예시:
[제목] 🧘 오전 요가와 외발자전거 수업!
[본문] 오늘 오전에 요가와 외발자전거 수업을 진행했어요. 요가로 몸의 유연성을 기르고 깊은 호흡으로 마음을 차분하게 다스렸습니다. 이어서 외발자전거로 균형감각과 하체 근력을 키우는 시간도 가졌어요. 두 가지 운동 모두 다이어트와 건강 유지에 효과적이랍니다. 꾸준히 하면 몸이 더욱 가벼워지는 것을 느낄 수 있어요. 건강한 하루 되세요! 🌿
"""
        else:
            user_prompt = f"""주제: {topic}

위 주제와 지침에 맞춰서 {platform}에 올릴 글을 작성해줘.
반드시 아래 형식을 지켜서 출력해:

[제목]
(여기에 주제와 어울리는 강력한 제목 작성)

[본문]
(여기에 본문 내용 작성)

중요: 시간대 지침을 반드시 지켜주세요! 
- morning(오전) 유형이면 아침 인사로 시작
- regular(오후) 유형이면 오후 인사로 시작  
- closing(마감/저녁) 유형이면 저녁 마무리 인사로 시작

주의: "함께 공부하며 지식을 나누는 한국체대 라이온 블로거 입니다" 문구는 블로그 전용이므로, {platform}용 글에는 절대 포함하지 마세요.
"""
        
        # 블로그는 기존 parse_content 사용, 밴드/카페는 별도 처리 고려 가능
        result = self.generate_content(
            topic, 
            post_type_config={'custom_system': system_message, 'custom_user': user_prompt}, 
            platform=platform,
            task_type=task_type  # task_type 전달
        )
        return result
    
    def _generate_with_gemini(self, model_name: str, system_message: str, user_prompt: str) -> str:
        """Gemini 모델로 콘텐츠 생성"""
        if not self.gemini_api_key:
            raise ValueError("Gemini API 키가 설정되지 않았습니다.")
        try:
            import google.generativeai as genai
        except ImportError as e:
            raise ImportError("google-generativeai 패키지가 필요합니다. pip install google-generativeai") from e
        
        genai.configure(api_key=self.gemini_api_key)
        model = genai.GenerativeModel(model_name)
        prompt_text = f"{system_message}\n\n{user_prompt}"
        response = model.generate_content(
            prompt_text,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 2000,
                "top_p": 0.9,
            }
        )
        content = self._extract_gemini_text(response)
        if not content:
            raise ValueError("Gemini 응답에서 본문을 추출할 수 없습니다.")
        return content.strip()

    def _extract_gemini_text(self, response: Any) -> str:
        """Gemini 응답 객체에서 텍스트 추출"""
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
        """생성된 콘텐츠가 요구사항을 충족하는지 검증합니다."""
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
        """GPT 응답을 제목과 본문으로 분리합니다."""
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
                body = body.replace('◆', '')
                body = body.replace('•', '')
                body = body.replace('- ', '')
                body = body.replace('▶', '')
                body = body.replace('★', '')
            else:
                # 기호 사용이 허용된 경우에만 통일
                body = body.replace('•', '◆')
                body = body.replace('- ', '◆ ')
            
            return title, body
            
        except Exception as e:
            logger.error(f"콘텐츠 파싱 중 오류 발생: {str(e)}")
            # 기본 파싱 방식으로 폴백
            lines = content.strip().split("\n")
            title = lines[0].strip()
            body = "\n".join(lines[2:]).strip()
            return title, body

    def _get_dummy_content(self, topic):
        """테스트용 더미 콘텐츠를 반환합니다."""
        dummy_contents = {
            "태권도 수업의 장점": {
                "title": "태권도의 놀라운 효과, 이것 하나로 우리 아이 자신감 UP!",
                "content": """👋 도입: 우리 아이들의 건강한 성장을 위해 어떤 운동을 시켜야 할까요?

◆ 많은 부모님들이 고민하시는 부분입니다.

✨ 장점: 태권도의 특별한 매력

◆ 체력 향상과 건강한 성장
- 전신 운동으로 근력 발달
- 유연성과 균형감각 향상
- 바른 자세 형성

◆ 정신 수양과 집중력
- 예의 바른 태도 습득
- 자기 절제력 향상
- 목표 달성의 즐거움

💡 태권도의 교육적 가치

◆ 자신감 향상
- 단계별 승급 경험
- 성취감 획득
- 또래와의 건강한 경쟁

✅ 결론: 태권도는 단순한 운동이 아닌 
전인적 성장의 도구입니다.

💪 제안: 우리 아이의 건강한 성장, 
이번 주부터 시작해보는 건 어떨까요?

태권도장 무료 체험 신청하고
우리 아이의 변화된 모습을
직접 확인해보세요!"""
            },
            "default": {
                "title": f"📝 {topic}에 대한 전문가의 특별한 이야기",
                "content": f"""👋 안녕하세요! 오늘은 {topic}에 
대해 이야기 나눠볼까요?

🔍 주제 살펴보기
◆ 이것은 테스트용 더미 
콘텐츠입니다.

💡 핵심 포인트
◆ 첫 번째 중요 사항
◆ 두 번째 중요 사항
◆ 세 번째 중요 사항

✅ 정리하며
이 글이 도움이 되셨나요?
아래 댓글로 여러분의 생각을
들려주세요!"""
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
        """GPT 프롬프트를 생성합니다."""
        return f"""
다음 주제로 블로그 포스트를 작성해주세요:
주제: {topic}
스타일: {style}

포맷:
- 첫 줄은 제목으로 작성해주세요
- 제목 다음에 빈 줄을 넣어주세요
- 그 다음부터 본문을 작성해주세요
- 적절한 단락 구분을 해주세요
- 읽기 쉽고 자연스러운 문체로 작성해주세요
- 전문적이면서도 친근한 톤을 유지해주세요
"""

    def _format_content_for_mobile(self, content):
        """모바일 환경에 최적화된 형식으로 콘텐츠를 변환합니다."""
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
        """콘텐츠의 가독성을 향상시킵니다."""
        # 사용자 설정 확인
        settings = self._load_settings()
        
        # 기호나 이모티콘 사용 금지 설정 확인
        if ('기호' in settings.get('instructions', '') and '사용하지 말' in settings.get('instructions', '')) or \
           ('이모티콘' in settings.get('instructions', '') and '사용하지 말' in settings.get('instructions', '')):
            # 기호와 이모티콘 제거
            formatted_content = content
            formatted_content = formatted_content.replace('◆', '')
            formatted_content = formatted_content.replace('•', '')
            formatted_content = formatted_content.replace('- ', '')
            formatted_content = formatted_content.replace('▶', '')
            formatted_content = formatted_content.replace('★', '')
            # 이모티콘 제거 (일반적인 이모티콘들)
            import re
            formatted_content = re.sub(r'[👋📝✨🔍📌💡⚠️✅📋💪🎯💯🌟⭐️🚀💝]', '', formatted_content)
        else:
            # 기호와 이모티콘 사용이 허용된 경우
            emoji_map = {
                '도입': '👋',
                '소개': '📝',
                '장점': '✨',
                '특징': '🔍',
                '방법': '📌',
                '팁': '💡',
                '주의': '⚠️',
                '결론': '✅',
                '요약': '📋',
                '제안': '💪'
            }
            
            # 이모지 추가
            formatted_content = content
            for key, emoji in emoji_map.items():
                formatted_content = formatted_content.replace(f"◆ {key}", f"{emoji} {key}")
            
            # 강조 표시 개선
            formatted_content = formatted_content.replace('•', '◆')
            formatted_content = formatted_content.replace('- ', '◆ ')
        
        # 문단 구분 개선
        paragraphs = formatted_content.split('\n\n')
        formatted_paragraphs = []
        for p in paragraphs:
            if p.strip():
                formatted_paragraphs.append(p.strip())
        
        return '\n\n'.join(formatted_paragraphs)

    def generate_reply(self, system_prompt: str, user_text: str, max_tokens: int = 150) -> str:
        """
        간단한 댓글 답글 생성용 메서드
        - system_prompt: AI 역할 및 지침
        - user_text: 사용자(회원) 댓글 내용
        - max_tokens: 최대 토큰 수
        """
        if self.use_dummy:
            return "감사합니다! 좋은 하루 보내세요!"
        
        try:
            model_name = self.selected_models[self.current_model_index] if self.selected_models else "gpt-4o-mini"
            provider = Config.AI_MODELS.get(model_name, {}).get("provider", "openai")
            
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
                return resp.choices[0].message.content.strip()
            elif provider == "gemini":
                prompt_text = f"{system_prompt}\n\n{user_text}"
                content = self._generate_with_gemini(model_name, system_prompt, user_text)
                return content.strip()
            else:
                return "감사합니다! 좋은 하루 보내세요!"
        except Exception as e:
            logger.error(f"답글 생성 오류: {e}")
            return "감사합니다! 좋은 하루 보내세요!"

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