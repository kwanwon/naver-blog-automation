
import os
import sys
import time
import json
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# 현재 디렉토리 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules.ai_handler import AIHandler
from naver_blog_post_finisher import NaverBlogPostFinisher

# 로깅 설정
def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}")

def get_chromedriver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # 사용자 데이터 디렉토리 사용 (로그인 유지)
    user_data_dir = os.path.expanduser("~/.blog_automation/chrome_data")
    chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    
    # ChromeDriver 경로 명시적 설정
    driver_path = ChromeDriverManager().install()
    # THIRD_PARTY_NOTICES 파일이 잡히는 경우 수정
    if "THIRD_PARTY_NOTICES" in driver_path:
        base_dir = os.path.dirname(driver_path)
        driver_path = os.path.join(base_dir, "chromedriver")
        if not os.path.exists(driver_path): # mac-arm64 폴더가 더 있을 수 있음
             driver_path = os.path.join(base_dir, "chromedriver")

    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def main():
    driver = None
    try:
        log("🚀 브라우저 시작 중...")
        driver = get_chromedriver()
        
        # 1. 네이버 블로그 글쓰기 페이지 접속
        log("📝 네이버 블로그 글쓰기 페이지로 이동...")
        driver.get("https://blog.naver.com/BlogWrite.naver?blogId=gm2hapkido") # ID는 예시, 실제 로그인된 계정으로 이동
        time.sleep(5)
        
        # 프레임 전환 (필요한 경우)
        try:
            driver.switch_to.frame("mainFrame")
            log("프레임 전환 완료")
        except:
            pass

        # 2. 설정 로드 (테스트용 가짜 데이터)
        settings = {
            "dojang_name": "라이온태권도",
            "address": "서울 강동구",
            "kakao_url": "https://open.kakao.com/o/test_link_1234",
            "tags": ["태권도", "합기도", "테스트"]
        }
        
        log(f"⚙️ 테스트 설정: {settings}")
        
        # 3. Finisher 인스턴스 생성
        finisher = NaverBlogPostFinisher(driver, settings)
        
        # 4. 푸터(링크 + 장소) 추가 테스트
        log("\n🧪 [테스트 1] 푸터 추가 (링크 & 장소) 시작")
        
        # 본문 영역 클릭 (포커스)
        try:
            body_area = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.se-component.se-text.se-l-default"))
            )
            body_area.click()
            log("본문 포커스 성공")
        except:
            log("⚠️ 본문 영역을 찾을 수 없음 (새 글이 아닐 수 있음)")
        
        # add_footer 실행
        finisher.add_footer()
        
        log("\n✅ 테스트 완료! 브라우저를 닫지 않고 대기합니다.")
        input("종료하려면 엔터키를 누르세요...")

    except Exception as e:
        log(f"❌ 오류 발생: {str(e)}")
        if driver:
             log("📄 페이지 버튼 정보 덤프:")
             buttons = driver.find_elements(By.TAG_NAME, "button")
             for btn in buttons:
                 try:
                     if btn.is_displayed():
                         test_attrs = {
                             "text": btn.text,
                             "class": btn.get_attribute("class"),
                             "data-log": btn.get_attribute("data-log"),
                             "title": btn.get_attribute("title")
                         }
                         log(f"🔘 Button: {test_attrs}")
                 except: pass
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
            log("브라우저 종료")

if __name__ == "__main__":
    main()
