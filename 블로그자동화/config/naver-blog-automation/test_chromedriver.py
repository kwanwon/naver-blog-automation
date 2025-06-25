#!/usr/bin/env python3
"""
ChromeDriver 테스트 스크립트
"""

import os
import subprocess
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService

def fix_chromedriver_permissions(driver_path):
    """ChromeDriver 권한 수정"""
    print(f"🔧 ChromeDriver 권한 수정: {driver_path}")
    
    try:
        # 실행 권한 부여
        subprocess.run(["chmod", "+x", driver_path], check=True)
        print("✅ 실행 권한 부여 완료")
        
        # quarantine 속성 제거
        subprocess.run(["xattr", "-d", "com.apple.quarantine", driver_path], 
                      capture_output=True, check=False)
        print("✅ quarantine 속성 제거 시도 완료")
        
        # provenance 속성 제거
        subprocess.run(["xattr", "-d", "com.apple.provenance", driver_path], 
                      capture_output=True, check=False)
        print("✅ provenance 속성 제거 시도 완료")
        
        return True
    except Exception as e:
        print(f"❌ 권한 수정 실패: {e}")
        return False

def test_chromedriver():
    """ChromeDriver 테스트"""
    print("🚀 ChromeDriver 테스트 시작")
    print("=" * 50)
    
    try:
        # Chrome 옵션 설정
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 헤드리스 모드
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        print("📥 ChromeDriverManager로 ChromeDriver 다운로드 중...")
        
        # WebDriverManager 사용
        from webdriver_manager.chrome import ChromeDriverManager
        
        driver_path = ChromeDriverManager().install()
        print(f"✅ ChromeDriver 다운로드 완료: {driver_path}")
        
        # 권한 수정
        fix_chromedriver_permissions(driver_path)
        
        # 브라우저 시작 테스트
        print("🌐 브라우저 시작 테스트...")
        service = ChromeService(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 간단한 페이지 로드 테스트
        driver.get("https://www.google.com")
        title = driver.title
        print(f"✅ 페이지 로드 성공: {title}")
        
        # 브라우저 종료
        driver.quit()
        print("✅ 브라우저 종료 완료")
        
        print("\n" + "=" * 50)
        print("🎉 ChromeDriver 테스트 성공!")
        print("이제 블로그 자동화 프로그램을 실행할 수 있습니다.")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        print("\n💡 해결 방법:")
        print("1. Chrome 브라우저가 설치되어 있는지 확인")
        print("2. 터미널에서 다음 명령어 실행:")
        print("   sudo xattr -rd com.apple.quarantine ~/.wdm/")
        print("3. 시스템 환경설정 > 보안 및 개인정보 보호에서 ChromeDriver 허용")
        return False

if __name__ == "__main__":
    try:
        test_chromedriver()
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)