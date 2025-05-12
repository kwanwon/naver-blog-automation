import openai
# OpenAI 모듈 임포트 후 바로 임시 API 키 설정 (오류 방지)
try:
    openai.api_key = openai.api_key or "sk-empty-key-for-initialization"
except:
    openai.api_key = "sk-empty-key-for-initialization"

from config.config import Config
import logging
import random
import os
import sys
import json
import time
import traceback
from datetime import datetime
import requests
import re

# 로깅 설정
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format=Config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# 리소스 경로 처리 함수 추가
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class GPTHandler:
    def __init__(self, api_key=None, model="gpt-4o", use_dummy=False):
        """GPT 핸들러 초기화"""
        # 로거 초기화
        self.logger = logging.getLogger('gpt_handler')
        
        # 핸들러 및 포맷터 초기화
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # 더미 데이터 사용 여부
        self.use_dummy = use_dummy
        self.api_key_error = None  # API 키 오류 메시지 저장용
        
        if self.use_dummy:
            self.logger.warning("더미 데이터 모드로 실행합니다. API 호출이 이루어지지 않습니다.")
            self.api_key = None
        else:
            # API 키 설정 (우선순위: 1. 직접 전달된 키, 2. 환경 변수)
            self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
            
            # 디버깅을 위한 로그 추가
            if api_key:
                self.logger.info("API 키가 직접 전달됨")
            elif os.environ.get('OPENAI_API_KEY'):
                self.logger.info("API 키가 환경 변수에서 로드됨")
            else:
                self.logger.warning("API 키를 찾을 수 없음")
            
            # API 키 유효성 검사
            if self.api_key and self.api_key != "sk-empty-key-for-initialization":
                if self.api_key.startswith('sk-') or self.api_key.startswith('sk-proj-'):
                    self.logger.info(f"API 키 설정됨 (첫 8자: {self.api_key[:8]}...)")
                    
                    # openai 모듈에 API 키 설정
                    openai.api_key = self.api_key
                    
                    # API 키 테스트
                    if self._test_api_key():
                        self.logger.info("API 키 테스트 성공: 유효한 키입니다")
                    else:
                        self.api_key_error = "API 키 테스트 실패: 유효하지 않은 키이거나 OpenAI 서버에 접속할 수 없습니다."
                        self.logger.error(self.api_key_error)
                        # API 키가 유효하지 않더라도 더미 데이터로 자동 전환하지 않음
                else:
                    self.api_key_error = "API 키가 잘못된 형식입니다. 'sk-' 또는 'sk-proj-'로 시작해야 합니다."
                    self.logger.error(self.api_key_error)
                    # 잘못된 형식이더라도 더미 데이터로 자동 전환하지 않음
            else:
                self.api_key_error = "API 키가 설정되지 않았습니다. GPT 설정에서 API 키를 입력해주세요."
                self.logger.warning(self.api_key_error)
                # API 키가 없더라도 더미 데이터로 자동 전환하지 않음
        
        self.model = model
        self.settings = self._load_settings()
        self.custom_prompts = self._load_custom_prompt()
        
        self.logger.info(f"GPT 핸들러 초기화 완료. 모델: {self.model}")
        self.logger.info(f"API 키 상태: {'설정됨' if self.api_key and self.api_key != 'sk-empty-key-for-initialization' and not self.api_key_error else '설정되지 않음'}")
        self.logger.info(f"더미 데이터 모드: {'활성화' if self.use_dummy else '비활성화'}")
        self.logger.info(f"GPT 설정 로드됨: {self.settings}")
        self.logger.info(f"커스텀 프롬프트 로드됨: {self.custom_prompts}")
    
    def _test_api_key(self):
        """API 키의 유효성을 테스트합니다."""
        try:
            # 간단한 요청으로 API 키 테스트
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": "gpt-3.5-turbo",  # 테스트용으로 가장 저렴한 모델 사용
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 5  # 최소한의 토큰만 요청
                },
                timeout=5  # 5초 이내 응답이 없으면 타임아웃
            )
            
            self.logger.info(f"API 키 테스트 응답 코드: {response.status_code}")
            
            # 응답 코드가 200이면 API 키가 유효
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"API 키 테스트 중 오류 발생: {str(e)}")
            return False
    
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

"""  # 끝에 줄바꿈 두 개 추가하여 다음 텍스트와 구분

        try:
            # 먼저 일반 경로에서 시도
            config_path = 'config/gpt_settings.txt'
            
            # 빌드된 환경에서 경로 시도
            if not os.path.exists(config_path):
                config_path = resource_path('config/gpt_settings.txt')
                if os.path.exists(config_path):
                    self.logger.info(f"빌드 환경에서 GPT 설정 파일 찾음: {config_path}")
                else:
                    self.logger.warning(f"GPT 설정 파일을 찾을 수 없음: {config_path}")
                    return default_settings
            
            with open(config_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                self.logger.info(f"GPT 설정 파일 로드됨: {config_path}")
                
                # 최종 업데이트 시간 기록
                settings['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 고정 검토 지침 추가
                settings['review_instructions'] = fixed_review_instructions
                
                return settings
                
        except Exception as e:
            self.logger.error(f"GPT 설정 로드 중 오류 발생: {str(e)}")
            self.logger.error(traceback.format_exc())
            return default_settings
    
    def _load_custom_prompt(self):
        """사용자 정의 프롬프트를 로드합니다."""
        default_prompt = {
            "base_prompt": "블로그 게시물을 작성할 때는 자연스럽고 유익한 내용을 제공해 주세요."
        }
        
        try:
            # 먼저 일반 경로에서 시도
            config_path = 'config/custom_prompts.txt'
            
            # 빌드된 환경에서 경로 시도
            if not os.path.exists(config_path):
                config_path = resource_path('config/custom_prompts.txt')
                if os.path.exists(config_path):
                    self.logger.info(f"빌드 환경에서 커스텀 프롬프트 파일 찾음: {config_path}")
                else:
                    self.logger.warning(f"커스텀 프롬프트 파일을 찾을 수 없음: {config_path}")
                    return default_prompt
            
            with open(config_path, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
                self.logger.info(f"커스텀 프롬프트 파일 로드됨: {config_path}")
                return custom_prompts
                
        except Exception as e:
            self.logger.error(f"커스텀 프롬프트 로드 중 오류 발생: {str(e)}")
            self.logger.error(traceback.format_exc())
            return default_prompt

    def generate_content(self, topic, keywords=None, depth=None):
        """주어진 주제에 대한 블로그 내용을 생성합니다."""
        if self.use_dummy:
            self.logger.info(f"더미 데이터 모드: 주제 '{topic}'에 대한 더미 콘텐츠를 생성합니다.")
            return self._get_dummy_content(topic)
            
        # API 키 오류가 있는 경우, 오류 메시지를 반환
        if self.api_key_error:
            self.logger.error(f"API 키 오류로 인해 콘텐츠 생성 불가: {self.api_key_error}")
            return {
                "title": f"API 키 오류",
                "content": f"""⚠️ API 키 오류

{self.api_key_error}

GPT 설정 메뉴에서 유효한 OpenAI API 키를 입력해주세요.
API 키는 https://platform.openai.com/account/api-keys 에서 생성할 수 있습니다.

문제가 지속되면 관리자에게 문의해주세요."""
            }
            
        if not self.api_key:
            self.logger.error("API 키가 설정되지 않았습니다.")
            return {
                "title": "API 키가 설정되지 않았습니다",
                "content": """⚠️ API 키 오류

OpenAI API 키가 설정되지 않았습니다.
GPT 설정 메뉴에서 유효한 OpenAI API 키를 입력해주세요.
API 키는 https://platform.openai.com/account/api-keys 에서 생성할 수 있습니다.

문제가 지속되면 관리자에게 문의해주세요."""
            }
            
        # 키워드가 없으면 빈 리스트로 초기화
        if keywords is None:
            keywords = []
            
        # 심도 설정
        content_depth = depth or "중간"  # 기본값은 "중간" 심도
        
        # 시스템 프롬프트 구성
        system_prompt = ""
        
        # 기본 프롬프트 추가 (custom_prompts에서 가져옴)
        if 'base_prompt' in self.custom_prompts:
            system_prompt += self.custom_prompts['base_prompt'] + "\n\n"
        
        # 페르소나 정보 추가
        if 'persona' in self.settings:
            system_prompt += f"### 페르소나\n{self.settings['persona']}\n\n"
            
        # 지시사항 추가
        if 'instructions' in self.settings:
            system_prompt += f"### 지시사항\n{self.settings['instructions']}\n\n"
            
        # 글 스타일 추가
        if 'style' in self.settings:
            system_prompt += f"### 스타일\n{self.settings['style']}\n\n"
            
        # 검토 지침 추가
        if 'review_instructions' in self.settings:
            system_prompt += f"### 검토 지침\n{self.settings['review_instructions']}\n\n"
        
        # 사용자 프롬프트 구성
        user_prompt = f"주제: {topic}\n"
        
        if keywords and len(keywords) > 0:
            user_prompt += f"키워드: {', '.join(keywords)}\n"
            
        user_prompt += f"심도: {content_depth}\n"
            
        # API 요청 데이터 구성
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
        }
        
        # 요청 시작 시간 기록
        start_time = time.time()
        
        try:
            # API 요청 보내기
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json=data
            )
            
            # 요청 소요 시간 계산
            elapsed_time = time.time() - start_time
            self.logger.info(f"GPT API 요청 처리 시간: {elapsed_time:.2f}초")
            
            # 응답 확인 및 디버깅
            self.logger.info(f"API 응답 상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                # 기존 모델 형식과 새로운 모델 형식 모두 처리
                if 'choices' in result and len(result['choices']) > 0:
                    if 'message' in result['choices'][0]:
                        # 기존 형식 (gpt-3.5-turbo, gpt-4 등)
                        generated_text = result['choices'][0]['message']['content']
                    elif 'content' in result['choices'][0]:
                        # 새로운 API 형식 (추가 필드 구조 대응)
                        generated_text = result['choices'][0]['content']
                    else:
                        self.logger.error(f"알 수 없는 응답 형식: {result}")
                        return self._get_api_error_content("알 수 없는 응답 형식")
                else:
                    self.logger.error(f"API 응답에 'choices' 필드가 없거나 비어 있습니다: {result}")
                    return self._get_api_error_content("API 응답 형식 오류")
                
                # 생성된 텍스트를 제목과 본문으로 분리
                title, body = self._parse_content(generated_text)
                
                # 본문 포맷팅
                formatted_body = self._enhance_formatting(body)
                
                # 최종 결과 반환
                return {
                    "title": title,
                    "content": formatted_body
                }
            else:
                # 오류 응답 상세 로깅
                self.logger.error(f"GPT API 오류: {response.status_code}")
                self.logger.error(f"오류 세부 정보: {response.text}")
                
                # 응답 내용 확인
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', {}).get('message', '알 수 없는 오류')
                    error_type = error_data.get('error', {}).get('type', '알 수 없는 유형')
                    error_code = error_data.get('error', {}).get('code', '')
                    
                    error_info = f"오류 메시지: {error_message}\n오류 유형: {error_type}\n오류 코드: {error_code}"
                    self.logger.error(error_info)
                    
                    return self._get_api_error_content(f"API 오류 ({response.status_code}): {error_message}")
                except:
                    self.logger.error("JSON 형식이 아닌 오류 응답")
                    return self._get_api_error_content(f"API 오류 ({response.status_code})")
                
        except Exception as e:
            self.logger.error(f"GPT 내용 생성 중 오류 발생: {str(e)}")
            self.logger.error(traceback.format_exc())
            return self._get_api_error_content(f"네트워크 오류: {str(e)}")

    def _get_api_error_content(self, error_message):
        """API 오류 메시지를 포함한 콘텐츠를 반환합니다."""
        return {
            "title": "API 요청 중 오류가 발생했습니다",
            "content": f"""⚠️ OpenAI API 오류

{error_message}

다음을 확인해주세요:
1. 입력한 API 키가 유효한지 확인
2. 인터넷 연결 상태 확인
3. OpenAI 서비스 상태 확인 (https://status.openai.com)

문제가 지속되면 관리자에게 문의해주세요."""
        }

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
                return self._clean_title(title), body
            
            title_part = parts[0].split('[제목]')
            if len(title_part) != 2:
                title = title_part[0].strip()
            else:
                title = title_part[1].strip()
            
            body = parts[1].strip()
            
            # 본문의 가독성 향상을 위한 후처리
            body = body.replace('•', '◆')  # 글머리 기호 통일
            body = body.replace('- ', '◆ ')  # 하이픈을 글머리 기호로 변경
            
            return self._clean_title(title), body
            
        except Exception as e:
            logger.error(f"콘텐츠 파싱 중 오류 발생: {str(e)}")
            # 기본 파싱 방식으로 폴백
            lines = content.strip().split("\n")
            title = lines[0].strip()
            body = "\n".join(lines[2:]).strip()
            return self._clean_title(title), body

    def _clean_title(self, title):
        """제목에서 마크다운 태그를 제거합니다."""
        # 헤더 마크다운 제거 (## 또는 ### 등)
        cleaned_title = re.sub(r'^#+\s+', '', title)
        
        # 굵은 텍스트 마크다운 제거 (**텍스트**)
        cleaned_title = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned_title)
        
        # 기울임 텍스트 마크다운 제거 (*텍스트*)
        cleaned_title = re.sub(r'\*(.*?)\*', r'\1', cleaned_title)
        
        # 밑줄 마크다운 제거 (_텍스트_)
        cleaned_title = re.sub(r'_(.*?)_', r'\1', cleaned_title)
        
        # 백틱(`) 제거
        cleaned_title = re.sub(r'`(.*?)`', r'\1', cleaned_title)
        
        return cleaned_title

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
        
        return dummy_contents.get(topic, dummy_contents["default"])

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
            # 문단 사이 여백 - 더 넓은 간격을 위해 빈 줄 두 개 추가
            formatted_lines.append('')
            formatted_lines.append('')  # 추가된 빈 줄
        
        return '\n'.join(formatted_lines)

    def _enhance_formatting(self, content):
        """콘텐츠의 가독성을 향상시킵니다."""
        # 마크다운 포맷 제거 (##, ###, **, ___ 등)
        cleaned_content = content
        
        # 헤더 마크다운 제거 (## 또는 ### 등)
        cleaned_content = re.sub(r'^#+\s+', '', cleaned_content, flags=re.MULTILINE)
        
        # 굵은 텍스트 마크다운 제거 (**텍스트**)
        cleaned_content = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned_content)
        
        # 기울임 텍스트 마크다운 제거 (*텍스트*)
        cleaned_content = re.sub(r'\*(.*?)\*', r'\1', cleaned_content)
        
        # 밑줄 마크다운 제거 (_텍스트_)
        cleaned_content = re.sub(r'_(.*?)_', r'\1', cleaned_content)
        
        # 구분선 제거 (---, ___, *** 등)
        cleaned_content = re.sub(r'^([-_*]{3,})$', '', cleaned_content, flags=re.MULTILINE)
        
        # 이모지 매핑
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
        formatted_content = cleaned_content
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
    handler = GPTHandler()  # 실제 GPT API 사용
    
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