
import sys
import os
import time
import threading
from unittest.mock import MagicMock

# Add current dir to path
sys.path.append(os.getcwd())

# Mock flet to avoid UI startup issues
sys.modules['flet'] = MagicMock()

from blog_writer_app import BlogWriterApp
from modules.serial_auth import BlogSerialAuth

def simulate_startup_update():
    print("--- 2. 시뮬레이션 시작: 앱 시작 시 업데이트 호출 확인 ---")
    
    # Mock update_device_info_and_usage to verify it's called
    original_update = BlogSerialAuth.update_device_info_and_usage
    update_called_event = threading.Event()
    
    def mock_update(self, serial_number):
        print(f"✅ Mock Update Called with: {serial_number}")
        update_called_event.set()
        # Call original to actually test the logic (optional, but good for integration test)
        return original_update(self, serial_number)
        
    BlogSerialAuth.update_device_info_and_usage = mock_update
    
    try:
        print("🚀 BlogWriterApp 인스턴스 생성 (앱 시작 시뮬레이션)...")
        app = BlogWriterApp()
        
        print("⏳ 스레드 실행 대기 중 (최대 5초)...")
        if update_called_event.wait(timeout=5.0):
            print("✅ 성공: 앱 시작 시 update_device_info_and_usage가 호출되었습니다!")
        else:
            print("❌ 실패: 타임아웃 내에 함수가 호출되지 않았습니다.")
            
    except Exception as e:
        print(f"❌ 시뮬레이션 중 오류: {e}")
    finally:
        # Restore logic
        BlogSerialAuth.update_device_info_and_usage = original_update

if __name__ == "__main__":
    simulate_startup_update()
