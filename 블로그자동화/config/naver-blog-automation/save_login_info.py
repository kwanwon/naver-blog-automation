#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
수동 로그인 후 정보 저장
- 기존 로그인된 브라우저에 연결
- 쿠키 및 세션 정보 저장
"""

import os
import time
import pickle
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def save_current_login():
    print("🔍 현재 로그인 상태 확인 및 저장")
    
    # Chrome 옵션 설정 (기존 세션 사용)
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # 드라이버 설정
    driver_path = ChromeDriverManager().install()
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        print("🌐 네이버 블로그로 이동...")
        driver.get('https://blog.naver.com')
        time.sleep(3)
        
        current_url = driver.current_url
        print(f"현재 URL: {current_url}")
        
        # 로그인 상태 확인
        if "nid.naver.com" in current_url or "login" in current_url.lower():
            print("❌ 로그인이 필요합니다.")
            print("브라우저에서 수동으로 로그인해주세요.")
            input("로그인 완료 후 Enter를 눌러주세요...")
            
            # 다시 확인
            driver.refresh()
            time.sleep(3)
            current_url = driver.current_url
            print(f"로그인 후 URL: {current_url}")
        
        # 페이지 소스에서 로그인 확인
        page_source = driver.page_source
        login_indicators = ["로그아웃", "님", "글쓰기", "PostWriteForm"]
        
        login_confirmed = False
        found_indicators = []
        
        for indicator in login_indicators:
            if indicator in page_source:
                login_confirmed = True
                found_indicators.append(indicator)
        
        if login_confirmed:
            print(f"✅ 로그인 확인됨! 발견된 지표: {', '.join(found_indicators)}")
        else:
            print("⚠️ 로그인 상태가 확실하지 않습니다.")
            print("그래도 쿠키를 저장하겠습니다.")
        
        # 쿠키 저장
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cookies_path = os.path.join(base_dir, 'naver_cookies.pkl')
        
        print("💾 쿠키 저장 중...")
        cookies = driver.get_cookies()
        with open(cookies_path, 'wb') as f:
            pickle.dump(cookies, f)
        
        print(f"✅ 쿠키 저장 완료: {cookies_path}")
        print(f"   저장된 쿠키 개수: {len(cookies)}")
        
        # 세션 정보 저장
        session_info = {
            "login_time": time.time(),
            "current_url": current_url,
            "user_agent": driver.execute_script('return navigator.userAgent;'),
            "login_confirmed": login_confirmed,
            "found_indicators": found_indicators
        }
        
        session_path = os.path.join(base_dir, 'naver_session.json')
        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(session_info, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 세션 정보 저장 완료: {session_path}")
        
        print("\n🎉 로그인 정보 저장 완료!")
        print("이제 블로그 자동화 앱에서 자동 로그인이 작동할 것입니다.")
        
        # 테스트: 글쓰기 페이지로 이동해보기
        print("\n🧪 글쓰기 페이지 접근 테스트...")
        write_url = "https://blog.naver.com/PostWriteForm.naver?blogId=gm2hapkido"
        driver.get(write_url)
        time.sleep(3)
        
        final_url = driver.current_url
        print(f"글쓰기 페이지 URL: {final_url}")
        
        if "PostWriteForm" in final_url:
            print("✅ 글쓰기 페이지 접근 성공!")
        else:
            print("⚠️ 글쓰기 페이지 접근 실패 - 추가 인증이 필요할 수 있습니다.")
        
        print("\n5초 후 브라우저를 종료합니다...")
        time.sleep(5)
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()
        print("✅ 브라우저 종료 완료")

if __name__ == "__main__":
    save_current_login()