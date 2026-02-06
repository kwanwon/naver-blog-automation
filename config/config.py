import os
from dotenv import load_dotenv
import sys
import datetime
from datetime import date

# 실행 파일 또는 스크립트 기준 경로 설정
if getattr(sys, 'frozen', False):
    # 실행 파일로 실행된 경우 (PyInstaller 등으로 빌드된 경우)
    base_dir = os.path.dirname(sys.executable)
    # 상위 디렉토리 확인 (배포 구조에 따라 조정)
    if not os.path.exists(os.path.join(base_dir, '.env')):
        parent_dir = os.path.dirname(base_dir)
        if os.path.exists(os.path.join(parent_dir, '.env')):
            base_dir = parent_dir
else:
    # 스크립트로 실행된 경우
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# .env 파일 경로
env_path = os.path.join(base_dir, '.env')
print(f"ENV 파일 경로: {env_path}")

# .env 파일에서 환경 변수 로드
load_dotenv(dotenv_path=env_path)

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
    
    # Gemini API 키 (환경 변수에서 가져옴)
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    
    # AI 모델 정보
    AI_MODELS = {
        "gpt-4o-mini": {
            "provider": "openai",
            "name": "GPT-4o Mini",
            "context": "128K",
            "input_cost_per_1k_krw": 0.2,   # 참고 추정치
            "output_cost_per_1k_krw": 0.8
        },
        "gpt-4o": {
            "provider": "openai",
            "name": "GPT-4o",
            "context": "128K",
            "input_cost_per_1k_krw": 1.6,   # 참고 추정치
            "output_cost_per_1k_krw": 8.0
        },
        "gpt-3.5-turbo": {
            "provider": "openai",
            "name": "GPT-3.5 Turbo",
            "context": "16K",
            "input_cost_per_1k_krw": 0.7,   # 참고 추정치
            "output_cost_per_1k_krw": 2.0
        },

        "gemini-2.5-flash-lite": {
            "provider": "gemini",
            "name": "Gemini 2.5 Flash-Lite",
            "context": "1M",
            "free": True,
            "input_cost_per_1k_krw": 0.0,
            "output_cost_per_1k_krw": 0.0,
            "daily_limit": 990
        },
        "gemini-2.5-flash": {
            "provider": "gemini",
            "name": "Gemini 2.5 Flash",
            "context": "1M",
            "input_cost_per_1k_krw": 0.0,
            "output_cost_per_1k_krw": 0.0,
            "description": "안정적으로 작동하는 최신 2.5 Flash 모델 (추천)",
            "description": "안정적으로 작동하는 최신 2.5 Flash 모델 (추천)",
            "daily_limit": 48
        }
    }
    
    @staticmethod
    def calculate_monthly_cost(model_name, posts_per_day=10):
        """월간 비용 계산 (단순 추정, 무료 모델은 0)"""
        if model_name not in Config.AI_MODELS:
            return (0, 0)
        model = Config.AI_MODELS[model_name]
        if model.get("free"):
            return (0, 0)
        # 기본 단가(USD/1M) 추정치
        input_cost = model.get("input_cost", 0.001)
        output_cost = model.get("output_cost", 0.002)
        monthly_posts = posts_per_day * 30
        input_tokens = monthly_posts * 1000 / 1000
        output_tokens = monthly_posts * 2000 / 1000
        usd = input_tokens * input_cost + output_tokens * output_cost
        krw = usd * 1330
        return (usd, krw)
    
    # 블로그 관련 설정
    BLOG_STICKER_PATH = "assets/stickers"
    POST_SAVE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 폴더 정리 설정
    RETENTION_DAYS = 2  # 보관할 날짜 수 