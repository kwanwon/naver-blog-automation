import os
import sys
from pathlib import Path

def get_app_data_dir() -> str:
    """
    Returns the platform-specific application data directory.
    - Windows: %LOCALAPPDATA%/BlogAutomation
    - macOS/Linux: ~/.blog_automation
    """
    if sys.platform == "win32":
        local_app_data = os.environ.get('LOCALAPPDATA')
        if not local_app_data:
            local_app_data = os.path.expanduser('~\\AppData\\Local')
        base_path = os.path.join(local_app_data, 'BlogAutomation')
    else:
        base_path = os.path.join(os.path.expanduser('~'), '.blog_automation')
    
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
