import openai
from config.config import Config
import logging
import random
import os
import sys
import json
import time
import traceback
from datetime import datetime

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
        # model 속성을 기본값으로 초기화
        self.model = Config.GPT_MODEL
        
        try:
            # 먼저 GPT 설정 파일에서 API 키 확인
            api_key = None
            if self.settings and 'api_key' in self.settings and self.settings['api_key']:
                api_key = self.settings['api_key']
                logger.info("GPT 설정 파일에서 API 키를 로드했습니다.")
            else:
                # 환경변수에서 API 키 확인
                api_key = Config.GPT_API_KEY
                logger.info("환경변수에서 API 키를 로드했습니다.")
            
            if api_key == 'your-api-key-here' or not api_key:
                # 오류 대신 자동으로 더미 모드로 설정
                logger.warning("API 키가 설정되지 않았습니다. 더미 모드로 전환합니다.")
                self.use_dummy = True
                self.client = None  # 더미 모드에서는 client를 None으로 설정
            else:
                # OpenAI 클라이언트 초기화 (최신 버전)
                openai.api_key = api_key
                self.client = openai.OpenAI(api_key=api_key)
                # model은 이미 위에서 초기화되었으므로 여기서는 다시 할당하지 않아도 됨
                logger.info("OpenAI 클라이언트 초기화 성공")
            
        except Exception as e:
            logger.error(f"OpenAI 클라이언트 초기화 중 오류 발생: {str(e)}")
            # 오류 발생 시 더미 모드로 자동 전환
            logger.warning("오류로 인해 더미 모드로 전환합니다.")
            self.use_dummy = True
            self.client = None  # 오류 시에도 client를 None으로 설정
        
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
            # 환경 감지: 개발자 모드 vs 배포 모드
            is_developer_mode = self._is_developer_mode()
            
            # 스크립트 파일의 위치를 기준으로 경로 계산
            script_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(script_dir)
            
            # 환경에 따른 경로 설정
            if is_developer_mode:
                # 개발자 환경: 프로젝트 루트의 config 디렉토리 우선
                # 빌드된 앱에서 실제 프로젝트 디렉토리 찾기
                project_config_paths = self._find_project_config_paths()
                
                possible_paths = project_config_paths + [
                    os.path.join(parent_dir, 'config', 'gpt_settings.txt'),
                    os.path.join(os.getcwd(), 'config', 'gpt_settings.txt'),
                    'config/gpt_settings.txt'
                ]
                logger.info("🔧 개발자 모드: 프로젝트 config 디렉토리에서 설정 로드")
            else:
                # 배포 환경: 사용자 홈 디렉토리 우선, 그 다음 번들 내부
                user_config_dir = os.path.expanduser("~/Documents/블로그자동화/config")
                os.makedirs(user_config_dir, exist_ok=True)
                
                possible_paths = [
                    os.path.join(user_config_dir, 'gpt_settings.txt'),
                    resource_path('config/gpt_settings.txt'),
                    os.path.join(parent_dir, 'config', 'gpt_settings.txt')
                ]
                logger.info("📦 배포 모드: 사용자 설정 디렉토리에서 설정 로드")
            
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
                    
                    # 기본 설정 업데이트
                    for key in ['persona', 'instructions', 'style']:
                        if key in loaded_settings:
                            default_settings[key] = loaded_settings[key]
                
                print(f"GPT 설정 파일 로드 성공: {settings_path}")
            else:
                print(f"GPT 설정 파일을 찾을 수 없습니다")
                # 배포 환경에서 설정 파일이 없으면 기본 템플릿 생성
                if not is_developer_mode:
                    self._create_default_settings_template()
                    
        except Exception as e:
            print(f"GPT 설정 파일 로드 중 오류 발생: {str(e)}")
            traceback.print_exc()
        
        # 고정 검토 지침 추가
        if 'instructions' not in default_settings:
            default_settings['instructions'] = fixed_review_instructions
        else:
            default_settings['instructions'] += fixed_review_instructions
            
        return default_settings

    def _is_developer_mode(self):
        """개발자 모드 여부를 확인합니다."""
        # 환경변수 확인
        if os.getenv('DEVELOPER_MODE') == 'true' or os.getenv('SKIP_SERIAL_AUTH') == 'true':
            return True
        
        # .developer_mode 파일 확인
        script_dir = os.path.dirname(os.path.abspath(__file__))
        developer_mode_file = os.path.join(script_dir, '.developer_mode')
        if os.path.exists(developer_mode_file):
            return True
            
        # PyInstaller 번들 내부의 .developer_mode 파일 확인
        try:
            if hasattr(sys, '_MEIPASS'):
                bundle_developer_file = os.path.join(sys._MEIPASS, 'modules', '.developer_mode')
                if os.path.exists(bundle_developer_file):
                    return True
        except:
            pass
            
        return False

    def _create_default_settings_template(self):
        """배포 환경에서 기본 설정 템플릿을 생성합니다."""
        try:
            user_config_dir = os.path.expanduser("~/Documents/블로그자동화/config")
            os.makedirs(user_config_dir, exist_ok=True)
            
            template_path = os.path.join(user_config_dir, 'gpt_settings.txt')
            if not os.path.exists(template_path):
                template_settings = {
                    "api_key": "",
                    "persona": "친근하고 전문적인 블로그 작성자",
                    "instructions": "1500자 이상 ~ 1600자 이내로 작성하며, 도입-본문-결론 구조로 구성해주세요.",
                    "style": "친근하고 따뜻한 부드러운 존댓말 사용",
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                with open(template_path, 'w', encoding='utf-8') as f:
                    json.dump(template_settings, f, ensure_ascii=False, indent=2)
                
                logger.info(f"기본 설정 템플릿 생성: {template_path}")
                
        except Exception as e:
            logger.error(f"기본 설정 템플릿 생성 실패: {e}")

    def _find_project_config_paths(self):
        """개발자 빌드에서 실제 프로젝트의 config 디렉토리 경로들을 찾습니다."""
        project_paths = []
        
        try:
            # PyInstaller 빌드에서 실행 중인 경우
            if hasattr(sys, '_MEIPASS'):
                # 실행 파일 경로에서 프로젝트 루트 찾기
                executable_dir = os.path.dirname(sys.executable)
                
                # 여러 단계 상위 디렉토리 확인
                current_dir = executable_dir
                for i in range(5):  # 최대 5단계 상위까지 확인
                    current_dir = os.path.dirname(current_dir)
                    config_path = os.path.join(current_dir, 'config', 'gpt_settings.txt')
                    if os.path.exists(config_path):
                        project_paths.append(config_path)
                        logger.info(f"🔍 프로젝트 config 발견: {config_path}")
                        
                # 현재 작업 디렉토리에서도 확인
                cwd_config = os.path.join(os.getcwd(), 'config', 'gpt_settings.txt')
                if os.path.exists(cwd_config) and cwd_config not in project_paths:
                    project_paths.append(cwd_config)
                    logger.info(f"🔍 작업 디렉토리 config 발견: {cwd_config}")
                    
        except Exception as e:
            logger.warning(f"프로젝트 config 경로 탐색 중 오류: {e}")
            
        return project_paths

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

    def generate_content(self, topic):
        """주어진 주제로 블로그 콘텐츠를 생성합니다."""
        max_retries = 3  # 최대 재시도 횟수
        retry_count = 0
        last_error = None
        
        # 사용자 설정 로드
        settings = self._load_settings()
        custom_prompt = self._load_custom_prompt()
        user_settings = self._load_user_settings()  # 사용자 설정 로드 추가
        
        # 시스템 메시지 구성 (페르소나와 지침 적용)
        system_message = f"""당신은 블로그 작성자입니다.
페르소나: {settings['persona']}

지침:
{settings['instructions']}

글쓰기 스타일:
{settings['style']}

작성 규칙:
1. 제목
- SEO 최적화된 매력적인 제목
- 핵심 키워드 포함
- 독자의 호기심을 자극하는 표현

2. 콘텐츠 구성
- 자연스러운 도입과 전개
- 핵심 정보 위주의 설명
- 실용적인 조언이나 팁 제공
- 깔끔한 마무리

3. 기본 요구사항
- 검색 키워드 자연스럽게 포함
- 위에 명시된 페르소나, 지침, 글쓰기 스타일을 엄격히 준수"""

        # 사용자 프롬프트 구성 (커스텀 프롬프트 적용)
        base_prompt = f"""주제: {topic}

위 주제로 다음 형식에 맞춰 블로그 포스트를 작성해주세요.

1. 먼저 [제목] 아래에 SEO 최적화된 제목을 작성해주세요.
2. 그 다음 [본문] 아래에 본문을 작성해주세요.

예시 형식:
[제목]
(여기에 제목 작성)

[본문]
(여기에 본문 작성)

작성 시 다음 사항을 반드시 지켜주세요:
- 위에서 명시한 페르소나, 지침, 글쓰기 스타일을 엄격히 준수
- 자연스러운 글의 흐름을 유지하면서 정보 전달
- 실제 사례나 통계 자료 포함 (가능한 경우)
- 실용적인 정보와 조언 제공
- 전문적인 내용을 쉽게 설명
- 깔끔한 마무리

중요: 모든 작성 규칙은 위에서 설정한 지침과 스타일을 최우선으로 따라주세요."""

        # 커스텀 프롬프트가 있으면 추가
        user_prompt = base_prompt
        if custom_prompt:
            user_prompt = f"{custom_prompt}\n\n{base_prompt}"
        
        while retry_count < max_retries:
            try:
                logger.info(f"OpenAI API 호출 시작: 주제 '{topic}' (시도 {retry_count + 1}/{max_retries})")
                
                # API 호출 (최신 버전)
                response = self.client.chat.completions.create(
                    model=self.model,
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
                
                # 응답 파싱 및 포맷팅
                content = response.choices[0].message.content.strip()
                title, body = self._parse_content(content)
                
                # 응답 검증
                if not self._validate_content(body):
                    retry_count += 1
                    if retry_count >= max_retries:
                        raise ValueError(f"{max_retries}회 시도 후에도 유효한 응답을 받지 못했습니다.")
                    logger.warning(f"응답이 요구사항을 충족하지 않아 다시 시도합니다. (시도 {retry_count}/{max_retries})")
                    continue
                
                # 모바일 최적화 및 포맷팅
                body = self._format_content_for_mobile(body)
                body = self._enhance_formatting(body)
                
                # 사용자 설정에서 첫 문장 추가 처리
                first_sentence = user_settings.get('first_sentence', '').strip()
                if first_sentence:
                    logger.info(f"🔥 첫 문장 설정 발견: '{first_sentence}'")
                    logger.info(f"🔥 원본 본문 시작 부분: '{body[:100]}...'")
                    
                    # 무조건 설정된 첫 문장을 본문 맨 앞에 추가
                    body = f"{first_sentence}\n\n{body}"
                    
                    logger.info(f"🔥 첫 문장 추가 후 본문 시작 부분: '{body[:100]}...'")
                else:
                    logger.info("🔥 첫 문장 설정이 없습니다.")
                
                logger.info(f"OpenAI API 호출 완료: 제목 '{title}'")
                
                return {
                    "title": title,
                    "content": body
                }
                
            except Exception as e:
                last_error = e
                if "rate_limit" in str(e).lower():
                    wait_time = 5
                    logger.warning(f"API 속도 제한에 도달했습니다. {wait_time}초 후 재시도합니다.")
                    time.sleep(wait_time)
                    retry_count += 1
                    continue
                else:
                    logger.error(f"OpenAI API 호출 중 오류 발생: {str(e)}")
                    raise  # 알 수 없는 오류는 즉시 상위로 전파
        
        # 최대 재시도 횟수 초과
        error_msg = f"최대 재시도 횟수({max_retries}회)를 초과했습니다."
        if last_error:
            error_msg += f" 마지막 오류: {str(last_error)}"
        raise RuntimeError(error_msg)

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