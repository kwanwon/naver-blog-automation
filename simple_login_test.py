#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
간단한 로그인 테스트
- 브라우저 열기
- 수동 로그인 후 쿠키 저장
- 자동화 없이 단순하게
"""

import os
import time
import pickle
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def simple_login_test():
    print("🚀 간단한 로그인 테스트 시작")
    
    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # 드라이버 설정
    driver_path = ChromeDriverManager().install()
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        print("🌐 네이버 로그인 페이지로 이동...")
        driver.get('https://nid.naver.com/nidlogin.login')
        
        print("\n" + "="*60)
        print("📋 수동 로그인 안내")
        print("="*60)
        print("1. 브라우저에서 네이버 로그인을 완료해주세요")
        print("   - ID: gm2hapkido")
        print("   - PW: km909090##")
        print("2. 로그인 완료 후 아무 키나 누르고 Enter를 눌러주세요")
        print("="*60)
        
        # 사용자 입력 대기
        input("로그인 완료 후 Enter를 눌러주세요...")
        
        # 블로그 페이지로 이동해서 로그인 확인
        print("🔍 로그인 상태 확인 중...")
        driver.get('https://blog.naver.com')
        time.sleep(3)
        
        current_url = driver.current_url
        print(f"현재 URL: {current_url}")
        
        # 쿠키 저장
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cookies_path = os.path.join(base_dir, 'naver_cookies.pkl')
        
        print("💾 쿠키 저장 중...")
        with open(cookies_path, 'wb') as f:
            pickle.dump(driver.get_cookies(), f)
        
        print(f"✅ 쿠키 저장 완료: {cookies_path}")
        print("🎉 로그인 정보 저장 완료!")
        print("\n이제 블로그 자동화 앱에서 자동 로그인이 작동할 것입니다.")
        
        # 5초 후 종료
        print("5초 후 브라우저를 종료합니다...")
        time.sleep(5)
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    
    finally:
        driver.quit()
        print("✅ 브라우저 종료 완료")

if __name__ == "__main__":
    simple_login_test()