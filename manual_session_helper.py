#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
수동 로그인 세션 헬퍼
1. 브라우저를 열어서 사용자가 직접 로그인
2. 로그인 완료 후 세션 정보 저장
3. 저장된 세션으로 블로그 자동화 실행
"""

import os
import time
import json
import pickle
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

class ManualSessionHelper:
    def __init__(self):
        self.driver = None
        # 기준 디렉토리 설정 (blog_writer_app.py와 동일한 위치)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.session_file = os.path.join(self.base_dir, "naver_session.pkl")
        self.cookies_file = os.path.join(self.base_dir, "naver_cookies.json")
        
    def setup_driver(self):
        """브라우저 설정 및 시작"""
        print("🌐 브라우저 설정 중...")
        
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # 자동화 감지 방지 (최소한만)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 고유한 사용자 데이터 디렉토리 설정 (프로필 충돌 방지)
        import time
        timestamp = int(time.time())
        user_data_dir = os.path.join(self.base_dir, f"manual_chrome_profile_{timestamp}_{os.urandom(4).hex()}")
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        
        # 프로젝트 루트의 ChromeDriver 사용
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(self.base_dir)))
        chromedriver_path = os.path.join(project_root, "chromedriver")
        
        if os.path.exists(chromedriver_path):
            print(f"✅ 프로젝트 ChromeDriver 사용: {chromedriver_path}")
            service = Service(executable_path=chromedriver_path)
        else:
            print("⚠️ 프로젝트 ChromeDriver 없음. WebDriverManager 사용...")
            driver_path = ChromeDriverManager().install()
            
            # WebDriverManager가 잘못된 파일을 반환하는 경우 수정
            if driver_path.endswith('THIRD_PARTY_NOTICES.chromedriver'):
                actual_chromedriver = os.path.dirname(driver_path) + '/chromedriver'
                if os.path.exists(actual_chromedriver):
                    print(f"✅ 올바른 ChromeDriver 파일 사용: {actual_chromedriver}")
                    os.chmod(actual_chromedriver, 0o755)
                    driver_path = actual_chromedriver
            
            service = Service(executable_path=driver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 최소한의 자동화 감지 방지
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        
        print("✅ 브라우저 시작 완료")
        
    def open_login_page(self):
        """네이버 로그인 페이지 열기"""
        print("🔐 네이버 로그인 페이지로 이동...")
        self.driver.get('https://nid.naver.com/nidlogin.login')
        time.sleep(2)
        
        print("=" * 60)
        print("🙋‍♂️ 수동 로그인을 진행해주세요!")
        print("1. 브라우저에서 직접 아이디와 비밀번호를 입력하세요")
        print("2. 로그인 버튼을 클릭하세요")
        print("3. 추가 인증(SMS, 이메일 등)이 있다면 완료하세요")
        print("4. 로그인이 완전히 완료되면 터미널에서 Enter를 눌러주세요")
        print("=" * 60)
        
    def wait_for_manual_login(self):
        """사용자의 수동 로그인 완료 대기"""
        input("로그인 완료 후 Enter를 눌러주세요...")
        
        # 로그인 상태 확인
        current_url = self.driver.current_url
        print(f"현재 URL: {current_url}")
        
        if "nidlogin" not in current_url:
            print("✅ 로그인 성공으로 보입니다!")
            return True
        else:
            print("❌ 아직 로그인 페이지에 있습니다. 로그인을 완료해주세요.")
            return False
    
    def save_session(self):
        """로그인 세션 정보 저장"""
        print("💾 세션 정보 저장 중...")
        
        try:
            # 드라이버가 없으면 기존 브라우저 세션에 연결 시도
            if not self.driver:
                self.setup_driver()
            
            # 쿠키 저장
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 쿠키 저장 완료: {len(cookies)}개")
            
            # 현재 URL과 페이지 정보 저장
            session_info = {
                'current_url': self.driver.current_url,
                'title': self.driver.title,
                'timestamp': time.time()
            }
            
            with open(self.session_file, 'wb') as f:
                pickle.dump(session_info, f)
            
            print("✅ 세션 정보 저장 완료")
            
            # 세션 저장 후 즉시 브라우저 종료 (프로필 충돌 방지)
            if self.driver:
                print("🔚 세션 저장 완료. 브라우저를 종료합니다...")
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
                time.sleep(3)  # 완전 종료 대기
            
            return True
            
        except Exception as e:
            print(f"❌ 세션 저장 실패: {e}")
            return False
    
    def test_blog_access(self):
        """네이버 블로그 접근 테스트"""
        print("📝 네이버 블로그 접근 테스트...")
        
        self.driver.get('https://blog.naver.com')
        time.sleep(3)
        
        current_url = self.driver.current_url
        page_source = self.driver.page_source
        
        print(f"블로그 URL: {current_url}")
        
        # 로그인 상태 확인
        if "로그아웃" in page_source or "님" in page_source:
            print("✅ 블로그에서 로그인 상태 확인됨!")
            
            # 글쓰기 버튼 확인
            try:
                write_button = self.driver.find_element(By.CSS_SELECTOR, "a[href*='write'], .btn_write, [class*='write']")
                print("✅ 글쓰기 버튼 발견!")
                return True
            except:
                print("⚠️ 글쓰기 버튼을 찾을 수 없습니다")
                return False
        else:
            print("❌ 블로그에서 로그인 상태 확인 안됨")
            return False
    
    def load_saved_session(self):
        """저장된 세션 로드"""
        print("📂 저장된 세션 로드 중...")
        
        if not os.path.exists(self.cookies_file):
            print("❌ 저장된 쿠키 파일이 없습니다")
            return False
        
        try:
            self.setup_driver()
            
            # 네이버 메인 페이지로 이동
            self.driver.get('https://www.naver.com')
            time.sleep(2)
            
            # 쿠키 로드
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    print(f"쿠키 추가 실패: {cookie.get('name', 'unknown')} - {e}")
            
            print(f"✅ 쿠키 로드 완료: {len(cookies)}개")
            
            # 페이지 새로고침하여 로그인 상태 적용
            self.driver.refresh()
            time.sleep(3)
            
            return True
            
        except Exception as e:
            print(f"❌ 세션 로드 실패: {e}")
            return False
    
    def run_manual_login_process(self):
        """전체 수동 로그인 프로세스 실행"""
        print("🚀 수동 로그인 프로세스 시작")
        
        try:
            # 1. 브라우저 설정
            self.setup_driver()
            
            # 2. 로그인 페이지 열기
            self.open_login_page()
            
            # 3. 수동 로그인 대기
            login_success = False
            while not login_success:
                login_success = self.wait_for_manual_login()
                if not login_success:
                    print("다시 로그인을 시도해주세요...")
            
            # 4. 세션 저장
            self.save_session()
            
            # 5. 블로그 접근 테스트
            blog_success = self.test_blog_access()
            
            if blog_success:
                print("\n🎉 수동 로그인 프로세스 완료!")
                print("이제 저장된 세션으로 블로그 자동화를 실행할 수 있습니다.")
                
                # 브라우저를 열어둘지 물어보기
                keep_open = input("\n브라우저를 열어둘까요? (y/n): ").lower().strip()
                if keep_open != 'y':
                    self.driver.quit()
                else:
                    print("브라우저를 열어둡니다. 수동으로 닫아주세요.")
            else:
                print("❌ 블로그 접근에 실패했습니다")
                
        except Exception as e:
            print(f"❌ 프로세스 실패: {e}")
            if self.driver:
                self.driver.quit()
    
    def test_saved_session(self):
        """저장된 세션으로 로그인 테스트"""
        print("🧪 저장된 세션 테스트")
        
        if self.load_saved_session():
            # 네이버 메인에서 로그인 상태 확인
            page_source = self.driver.page_source
            if "로그아웃" in page_source or "님" in page_source:
                print("✅ 메인 페이지에서 로그인 상태 확인!")
                
                # 블로그 접근 테스트
                if self.test_blog_access():
                    print("🎉 저장된 세션으로 블로그 접근 성공!")
                else:
                    print("❌ 블로그 접근 실패")
            else:
                print("❌ 로그인 상태 확인 안됨")
            
            # 10초 후 브라우저 종료
            print("10초 후 브라우저를 종료합니다...")
            time.sleep(10)
            self.driver.quit()
        else:
            print("❌ 세션 로드 실패")

def main():
    helper = ManualSessionHelper()
    
    print("네이버 블로그 수동 로그인 헬퍼")
    print("1. 새로운 수동 로그인")
    print("2. 저장된 세션 테스트")
    
    choice = input("선택하세요 (1 또는 2): ").strip()
    
    if choice == "1":
        helper.run_manual_login_process()
    elif choice == "2":
        helper.test_saved_session()
    else:
        print("잘못된 선택입니다.")

if __name__ == "__main__":
    main() 