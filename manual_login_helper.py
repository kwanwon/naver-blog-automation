#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
수동 로그인 도우미
- 한 번만 수동으로 로그인
- 완벽한 쿠키 및 세션 저장
- 이후 자동 로그인 보장
"""

import os
import sys
import time
import pickle
import uuid
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class ManualLoginHelper:
    def __init__(self):
        self.driver = None
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
    def setup_driver(self):
        """Chrome 드라이버 설정"""
        try:
            print("🚀 Chrome 드라이버 초기화 중...")
            
            chrome_options = Options()
            
            # 고유한 프로필 디렉토리 생성
            timestamp = str(int(time.time()))
            unique_id = str(uuid.uuid4())[:8]
            profile_path = os.path.join(self.base_dir, f"chrome_profile_manual_{timestamp}_{unique_id}")
            os.makedirs(profile_path, exist_ok=True)
            
            # Chrome 옵션 설정
            chrome_options.add_argument(f"--user-data-dir={profile_path}")
            chrome_options.add_argument("--profile-directory=NaverBlogManual")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-notifications")
            
            # WebDriverManager 사용
            driver_path = ChromeDriverManager().install()
            service = Service(executable_path=driver_path)
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(10)
            
            print("✅ Chrome 드라이버 초기화 완료!")
            return True
            
        except Exception as e:
            print(f"❌ Chrome 드라이버 초기화 실패: {e}")
            return False
    
    def manual_login_process(self):
        """수동 로그인 프로세스"""
        try:
            if not self.setup_driver():
                return False
            
            print("\n" + "="*50)
            print("🔐 네이버 수동 로그인 도우미")
            print("="*50)
            print("1. 브라우저가 열리면 네이버에 로그인해주세요")
            print("2. 로그인 완료 후 이 창에서 Enter를 눌러주세요")
            print("3. 로그인 정보가 자동으로 저장됩니다")
            print("="*50)
            
            # 네이버 로그인 페이지로 이동
            print("🌐 네이버 로그인 페이지로 이동 중...")
            self.driver.get('https://nid.naver.com/nidlogin.login')
            time.sleep(3)
            
            # 사용자 입력 대기
            input("\n👆 브라우저에서 로그인을 완료한 후 여기서 Enter를 눌러주세요...")
            
            # 로그인 확인
            print("🔍 로그인 상태 확인 중...")
            self.driver.get('https://blog.naver.com')
            time.sleep(5)
            
            current_url = self.driver.current_url
            print(f"현재 URL: {current_url}")
            
            # 로그인 상태 확인
            if "nid.naver.com" in current_url or "login" in current_url.lower():
                print("❌ 로그인이 완료되지 않았습니다. 다시 시도해주세요.")
                return False
            
            # 추가 확인: 페이지 소스에서 로그인 관련 요소 찾기
            page_source = self.driver.page_source
            login_indicators = ["로그아웃", "님", "글쓰기", "PostWriteForm"]
            
            login_confirmed = False
            for indicator in login_indicators:
                if indicator in page_source:
                    login_confirmed = True
                    print(f"✅ 로그인 확인: '{indicator}' 발견")
                    break
            
            if not login_confirmed:
                print("⚠️ 로그인 상태가 확실하지 않습니다.")
                confirm = input("그래도 계속 진행하시겠습니까? (y/n): ")
                if confirm.lower() != 'y':
                    return False
            
            # 쿠키 저장
            print("💾 로그인 정보 저장 중...")
            cookies_path = os.path.join(self.base_dir, 'naver_cookies.pkl')
            
            try:
                with open(cookies_path, 'wb') as f:
                    pickle.dump(self.driver.get_cookies(), f)
                print(f"✅ 쿠키 저장 완료: {cookies_path}")
            except Exception as e:
                print(f"❌ 쿠키 저장 실패: {e}")
                return False
            
            # 세션 정보도 저장
            session_path = os.path.join(self.base_dir, 'naver_session.txt')
            try:
                with open(session_path, 'w', encoding='utf-8') as f:
                    f.write(f"login_time: {time.time()}\n")
                    f.write(f"current_url: {current_url}\n")
                    f.write(f"user_agent: {self.driver.execute_script('return navigator.userAgent;')}\n")
                print(f"✅ 세션 정보 저장 완료: {session_path}")
            except Exception as e:
                print(f"⚠️ 세션 정보 저장 실패: {e}")
            
            print("\n🎉 로그인 정보 저장 완료!")
            print("이제 블로그 자동화 앱에서 자동 로그인이 작동할 것입니다.")
            
            return True
            
        except Exception as e:
            print(f"❌ 수동 로그인 프로세스 실패: {e}")
            return False
        
        finally:
            if self.driver:
                print("🔄 5초 후 브라우저를 종료합니다...")
                time.sleep(5)
                self.driver.quit()

def main():
    helper = ManualLoginHelper()
    success = helper.manual_login_process()
    
    if success:
        print("\n✅ 성공! 이제 블로그 자동화 앱을 실행해보세요.")
    else:
        print("\n❌ 실패! 다시 시도해주세요.")

if __name__ == "__main__":
    main()