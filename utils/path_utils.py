import os
import sys
from pathlib import Path

# 🟢 블로그자동화_데이터 필수 16개 표준 폴더 목록 (Windows / macOS 공통 완벽 보장)
DEFAULT_APP_DATA_SUBDIRS = [
    '밴드_수동이미지',
    '밴드_수동이미지_백업',
    '밴드_수동이미지_실패',
    '밴드사진폴더',
    '블로그_카페_수동이미지',
    '블로그사진폴더',
    '수동업로드',
    '수동이미지',
    '카페사진폴더',
    'config',
    'data',
    'default_images',
    'drafts',
    'logs',
    'settings',
    'temp'
]

def get_app_data_dir() -> str:
    """
    Returns the platform-specific application data directory.
    - Windows & macOS: ~/Documents/블로그자동화_데이터
    """
    documents_dir = os.path.join(os.path.expanduser('~'), 'Documents')
    base_path = os.path.join(documents_dir, '블로그자동화_데이터')
    
    # Ensure base directory exists
    os.makedirs(base_path, exist_ok=True)

    # Ensure all 16 standard subdirectories exist
    for sub in DEFAULT_APP_DATA_SUBDIRS:
        sub_path = os.path.join(base_path, sub)
        try:
            os.makedirs(sub_path, exist_ok=True)
        except Exception:
            pass

    # 🆕 필수 설정 파일 자동 시딩 (초기 설치 후 user_settings.txt 또는 app_settings.json이 없을 때 기본값 안전 복사)
    try:
        import shutil
        config_dir = os.path.join(base_path, 'config')
        dest_user_settings = os.path.join(config_dir, 'user_settings.txt')
        if not os.path.exists(dest_user_settings):
            src_user = get_resource_path('config/user_settings.txt')
            if not os.path.exists(src_user) and getattr(sys, 'frozen', False):
                candidate = os.path.join(os.path.dirname(sys.executable), 'config', 'user_settings.txt')
                if os.path.exists(candidate):
                    src_user = candidate
            if os.path.exists(src_user):
                shutil.copy2(src_user, dest_user_settings)
                print(f"✅ 기본 user_settings.txt 자동 시딩 완료: {dest_user_settings}")

        dest_app_settings = os.path.join(config_dir, 'app_settings.json')
        if not os.path.exists(dest_app_settings):
            src_app = get_resource_path('config/app_settings.json')
            if not os.path.exists(src_app) and getattr(sys, 'frozen', False):
                candidate = os.path.join(os.path.dirname(sys.executable), 'config', 'app_settings.json')
                if os.path.exists(candidate):
                    src_app = candidate
            if os.path.exists(src_app):
                shutil.copy2(src_app, dest_app_settings)
                print(f"✅ 기본 app_settings.json 자동 시딩 완료: {dest_app_settings}")
    except Exception as ex_seed:
        pass

    return base_path

def get_log_dir() -> str:
    path = os.path.join(get_app_data_dir(), 'logs')
    os.makedirs(path, exist_ok=True)
    return path

def get_config_dir() -> str:
    path = os.path.join(get_app_data_dir(), 'config')
    os.makedirs(path, exist_ok=True)
    return path

def get_data_dir() -> str:
    path = os.path.join(get_app_data_dir(), 'data')
    os.makedirs(path, exist_ok=True)
    return path

def get_resource_path(relative_path: str) -> str:
    """ReadOnly resources inside the bundle/project"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_app_settings_path() -> str:
    """Returns the path to the main application settings file."""
    return os.path.join(get_config_dir(), 'app_settings.json')

def get_ai_settings_path() -> str:
    """AI 설정 파일(ai_settings.txt)의 전체 경로를 반환합니다."""
    return os.path.join(get_config_dir(), 'ai_settings.txt')

def get_gpt_settings_path() -> str:
    """(Deprecated) 하위 호환성을 위해 유지"""
    return os.path.join(get_config_dir(), 'gpt_settings.txt')

def get_api_key_path() -> str:
    """Returns the path to the API key file."""
    return os.path.join(get_config_dir(), 'api_key.json')

def get_user_settings_path() -> str:
    """Returns the path to the user settings file."""
    return os.path.join(get_config_dir(), 'user_settings.txt')

def get_custom_prompts_path() -> str:
    """Returns the path to the custom prompts file."""
    return os.path.join(get_config_dir(), 'custom_prompts.txt')
