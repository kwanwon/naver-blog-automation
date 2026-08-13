import os
import sys
from pathlib import Path

def get_app_data_dir() -> str:
    """
    Returns the platform-specific application data directory.
    - Windows & macOS: ~/Documents/블로그자동화_데이터
    """
    documents_dir = os.path.join(os.path.expanduser('~'), 'Documents')
    base_path = os.path.join(documents_dir, '블로그자동화_데이터')
    
    # Ensure base directory exists
    os.makedirs(base_path, exist_ok=True)
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
