#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chrome 브라우저 클립보드 권한 자동 설정 스크립트
브라우저 시작 전에 클립보드 권한을 미리 허용하도록 설정합니다.
"""

import os
import json
import platform
import subprocess
from pathlib import Path

def setup_chrome_clipboard_permissions():
    """Chrome 브라우저의 클립보드 권한을 자동으로 허용하도록 설정"""
    
    print("🔧 Chrome 클립보드 권한 자동 설정 시작...")
    
    # 운영체제별 Chrome 설정 경로
    system = platform.system()
    
    if system == "Darwin":  # macOS
        chrome_config_path = os.path.expanduser("~/Library/Application Support/Google/Chrome")
        preferences_path = os.path.join(chrome_config_path, "Default", "Preferences")
    elif system == "Windows":
        chrome_config_path = os.path.expanduser("~/AppData/Local/Google/Chrome/User Data")
        preferences_path = os.path.join(chrome_config_path, "Default", "Preferences")
    else:  # Linux
        chrome_config_path = os.path.expanduser("~/.config/google-chrome")
        preferences_path = os.path.join(chrome_config_path, "Default", "Preferences")
    
    print(f"Chrome 설정 경로: {chrome_config_path}")
    
    # Chrome이 실행 중인지 확인하고 종료
    try:
        if system == "Darwin":
            subprocess.run(["pkill", "-f", "Google Chrome"], check=False)
        elif system == "Windows":
            subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], check=False)
        else:
            subprocess.run(["pkill", "-f", "chrome"], check=False)
        print("✅ Chrome 프로세스 종료 완료")
    except Exception as e:
        print(f"Chrome 프로세스 종료 중 오류 (무시): {e}")
    
    # 설정 디렉토리 생성
    os.makedirs(os.path.dirname(preferences_path), exist_ok=True)
    
    # 기존 설정 로드 또는 새로 생성
    preferences = {}
    if os.path.exists(preferences_path):
        try:
            with open(preferences_path, 'r', encoding='utf-8') as f:
                preferences = json.load(f)
            print("✅ 기존 Chrome 설정 로드 완료")
        except Exception as e:
            print(f"기존 설정 로드 실패, 새로 생성: {e}")
            preferences = {}
    
    # 클립보드 권한 설정 추가
    if "profile" not in preferences:
        preferences["profile"] = {}
    
    if "default_content_setting_values" not in preferences["profile"]:
        preferences["profile"]["default_content_setting_values"] = {}
    
    if "content_settings" not in preferences["profile"]:
        preferences["profile"]["content_settings"] = {}
    
    if "exceptions" not in preferences["profile"]["content_settings"]:
        preferences["profile"]["content_settings"]["exceptions"] = {}
    
    # 클립보드 권한 자동 허용 설정
    preferences["profile"]["default_content_setting_values"]["clipboard"] = 1  # 1 = 허용
    
    # 네이버 도메인에 대한 클립보드 권한 명시적 허용
    clipboard_exceptions = {
        "https://blog.naver.com:443,*": {
            "last_modified": "13000000000000000",
            "setting": 1
        },
        "https://naver.com:443,*": {
            "last_modified": "13000000000000000", 
            "setting": 1
        },
        "[*.]naver.com:443,*": {
            "last_modified": "13000000000000000",
            "setting": 1
        }
    }
    
    preferences["profile"]["content_settings"]["exceptions"]["clipboard"] = clipboard_exceptions
    
    # 권한 요청 팝업 차단 설정
    preferences["profile"]["default_content_setting_values"]["permission_autoblocking_data"] = 1
    preferences["profile"]["default_content_setting_values"]["permission_requests"] = 2  # 2 = 차단
    
    # 설정 파일 저장
    try:
        with open(preferences_path, 'w', encoding='utf-8') as f:
            json.dump(preferences, f, indent=2, ensure_ascii=False)
        print("✅ Chrome 클립보드 권한 설정 저장 완료")
        print(f"설정 파일 위치: {preferences_path}")
        return True
    except Exception as e:
        print(f"❌ 설정 저장 실패: {e}")
        return False

def create_chrome_policy_file():
    """Chrome 정책 파일을 생성하여 클립보드 권한을 강제로 허용"""
    
    print("📋 Chrome 정책 파일 생성 시작...")
    
    system = platform.system()
    
    # 정책 내용
    policy_content = {
        "DefaultClipboardSetting": 1,  # 1 = 허용
        "ClipboardAllowedForUrls": [
            "https://blog.naver.com",
            "https://naver.com", 
            "https://*.naver.com"
        ],
        "DefaultNotificationsSetting": 2,  # 2 = 차단
        "DefaultPopupsSetting": 1,  # 1 = 허용
        "PermissionRequestChipEnabled": False,
        "QuietNotificationPromptsEnabled": False
    }
    
    try:
        if system == "Darwin":  # macOS
            # macOS용 정책 파일 경로
            policy_dir = "/Library/Managed Preferences"
            policy_file = os.path.join(policy_dir, "com.google.Chrome.plist")
            
            # plist 형식으로 저장 (macOS)
            import plistlib
            os.makedirs(policy_dir, exist_ok=True)
            with open(policy_file, 'wb') as f:
                plistlib.dump(policy_content, f)
            print(f"✅ macOS Chrome 정책 파일 생성: {policy_file}")
            
        elif system == "Windows":
            # Windows 레지스트리 설정
            import winreg
            
            key_path = r"SOFTWARE\Policies\Google\Chrome"
            try:
                key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path)
                winreg.SetValueEx(key, "DefaultClipboardSetting", 0, winreg.REG_DWORD, 1)
                winreg.CloseKey(key)
                print("✅ Windows Chrome 정책 레지스트리 설정 완료")
            except PermissionError:
                print("⚠️ 관리자 권한이 필요합니다. 일반 설정으로 대체합니다.")
                
        else:  # Linux
            # Linux용 정책 파일
            policy_dir = "/etc/opt/chrome/policies/managed"
            policy_file = os.path.join(policy_dir, "clipboard_policy.json")
            
            os.makedirs(policy_dir, exist_ok=True)
            with open(policy_file, 'w') as f:
                json.dump(policy_content, f, indent=2)
            print(f"✅ Linux Chrome 정책 파일 생성: {policy_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ 정책 파일 생성 실패: {e}")
        return False

def main():
    """메인 실행 함수"""
    print("🚀 Chrome 클립보드 권한 자동 설정 도구")
    print("=" * 50)
    
    # 1. Chrome 설정 파일 수정
    success1 = setup_chrome_clipboard_permissions()
    
    # 2. Chrome 정책 파일 생성 (선택사항)
    success2 = create_chrome_policy_file()
    
    print("=" * 50)
    if success1:
        print("✅ Chrome 클립보드 권한 설정 완료!")
        print("이제 Chrome을 다시 시작하면 클립보드 권한이 자동으로 허용됩니다.")
    else:
        print("❌ 설정 실패. 수동으로 Chrome 설정을 확인해주세요.")
    
    print("\n📌 참고사항:")
    print("- Chrome을 완전히 종료한 후 다시 시작해야 설정이 적용됩니다.")
    print("- 일부 시스템에서는 관리자 권한이 필요할 수 있습니다.")
    print("- 설정이 적용되지 않으면 Chrome 설정에서 수동으로 허용해주세요.")

if __name__ == "__main__":
    main() 