import os
from dotenv import load_dotenv
import sys
import datetime
from datetime import date
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('config')

# 실행 파일 또는 스크립트 기준 경로 설정
if getattr(sys, 'frozen', False):
    # 실행 파일로 실행된 경우 (PyInstaller 등으로 빌드된 경우)
    base_dir = os.path.dirname(sys.executable)
    logger.info(f"빌드된 앱에서 실행 중 - 기본 경로: {base_dir}")
    
    # 가능한 .env 파일 위치들
    possible_paths = [
        os.path.join(base_dir, '.env'),  # 실행 파일과 같은 디렉토리
        os.path.join(os.path.dirname(base_dir), '.env'),  # 상위 디렉토리
        os.path.join(base_dir, 'config', '.env'),  # config 디렉토리 내부
        os.path.join(base_dir, 'resources', '.env')  # resources 디렉토리 내부
    ]
    
    # 현재 사용자 홈 디렉토리도 확인
    home_dir = os.path.expanduser("~")
    possible_paths.append(os.path.join(home_dir, '.naver_blog_auto.env'))
    
    # 가능한 모든 경로에서 .env 파일 찾기
    env_path = None
    for path in possible_paths:
        if os.path.exists(path):
            env_path = path
            logger.info(f".env 파일 발견: {env_path}")
            break
    
    if not env_path:
        logger.warning("빌드된 앱에서 .env 파일을 찾을 수 없습니다. 기본 경로를 사용합니다.")
        env_path = os.path.join(base_dir, '.env')
        
        # 빌드된 앱에서 .env 파일이 없으면 새로 생성
        if not os.path.exists(env_path):
            try:
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.write("# 자동 생성된 환경 변수 파일\n")
                    f.write("OPENAI_API_KEY=\n")
                logger.info(f"새 .env 파일 생성됨: {env_path}")
            except Exception as e:
                logger.error(f".env 파일 생성 실패: {str(e)}")
else:
    # 스크립트로 실행된 경우
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logger.info(f"스크립트 모드에서 실행 중 - 기본 경로: {base_dir}")
    env_path = os.path.join(base_dir, '.env')

# .env 파일 경로 로깅
logger.info(f"ENV 파일 경로: {env_path}")

# .env 파일에서 환경 변수 로드
try:
    load_dotenv(dotenv_path=env_path)
    logger.info("환경 변수 로드 성공")
    
    # OpenAI 모듈 초기화 문제 해결을 위한 임시 처리
    if 'OPENAI_API_KEY' not in os.environ or not os.environ['OPENAI_API_KEY']:
        logger.warning("API 키가 설정되지 않았습니다. 임시 API 키를 설정합니다.")
        os.environ['OPENAI_API_KEY'] = "sk-empty-key-for-initialization"
except Exception as e:
    logger.error(f"환경 변수 로드 실패: {str(e)}")

class Config:
    """애플리케이션 설정"""
    
    # 플래그: True로 설정하면 자동 로그인 사용
    AUTO_LOGIN = True
    
    # 네이버 로그인 정보 (환경 변수에서 가져옴)
    NAVER_ID = os.getenv('NAVER_ID', '')
    NAVER_PW = os.getenv('NAVER_PW', '')
    
    # GPT API 키 (환경 변수에서 가져옴)
    GPT_API_KEY = os.getenv('OPENAI_API_KEY', '')  # 환경 변수에서 API 키 가져오기
    
    # 기본 이미지 폴더
    DEFAULT_IMAGES_FOLDER = "default_images"
    
    # 로깅 설정
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 현재 날짜 기준 폴더 생성
    @staticmethod
    def get_date_folder():
        """현재 날짜 기준 폴더 경로 반환"""
        today = date.today()
        return f"{today.year}-{today.month:02d}-{today.day:02d}"
    
    # 시스템 경로 관련 설정
    @staticmethod
    def get_abs_path(rel_path):
        """상대 경로를 절대 경로로 변환"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, rel_path)

    # GPT API 설정
    GPT_MODEL = "gpt-3.5-turbo"  # GPT-3.5-turbo 모델로 변경
    GPT_MAX_TOKENS = 4000  # 토큰 수 증가
    GPT_TEMPERATURE = 0.8  # 창의성 약간 증가
    
    # 블로그 관련 설정
    BLOG_STICKER_PATH = "assets/stickers"
    POST_SAVE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 폴더 정리 설정
    RETENTION_DAYS = 2  # 보관할 날짜 수 