
import sys
import os
import shutil
import json
import time

# Add current dir to path
sys.path.append(os.getcwd())
from modules.serial_auth import BlogSerialAuth

def simulate_reauth():
    print("--- 1. 시뮬레이션 시작: 시리얼 재인증 ---")
    
    # 1. Backup existing config
    config_path = "modules/serial_config.json"
    backup_path = "modules/serial_config.json.bak_sim"
    
    if os.path.exists(config_path):
        shutil.copy(config_path, backup_path)
        print(f"✅ 기존 설정 백업 완료: {backup_path}")
        
    # 2. Delete config (Simulate user deleting/resetting)
    if os.path.exists(config_path):
        os.remove(config_path)
        print("🗑️ 기존 시리얼 설정 파일 삭제됨 (초기화)")
        
    auth = BlogSerialAuth()
    
    # 3. Simulate User Inputting Serial (Using the known testing serial)
    test_serial = "ea920794-39ca-458d-b2ad-4681b6a4aaa7"
    print(f"🔑 시리얼 입력 시뮬레이션: {test_serial}")
    
    # 4. Check Serial (like the UI does)
    valid, msg, expiry = auth.check_serial(test_serial)
    if valid:
        print(f"✅ 시리얼 검증 성공: {msg}")
        
        # 5. Save Config (like the UI does)
        auth.save_config(test_serial)
        print("💾 설정 저장 완료")
        
        # 6. Update Device Info (CRITICAL STEP - This is what happens in the auth window)
        print("📡 디바이스 정보 업데이트 및 활성화 시도...")
        success = auth.update_device_info_and_usage(test_serial)
        
        if success:
             print("✅ 디바이스 정보 업데이트 성공!")
        else:
             print("❌ 디바이스 정보 업데이트 실패!")
             
    else:
        print(f"❌ 시리얼 검증 실패: {msg}")

    # 7. Restore Config
    if os.path.exists(backup_path):
        shutil.move(backup_path, config_path)
        print("✅ 기존 설정 복구 완료")

if __name__ == "__main__":
    simulate_reauth()
