import os
import sys
import time
import json
import random
import urllib.parse
import traceback
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime, timedelta
import hashlib
import psutil
from queue import Queue
from dotenv import load_dotenv
from config.naver_api_config import NAVER_API_CONFIG, NAVER_URLS
from naver_blog_auto_image import NaverBlogImageInserter  # 새로운 이미지 처리 클래스 import
from naver_blog_post_finisher import NaverBlogPostFinisher  # 포스트 마무리 처리 클래스 import
import pyperclip
import requests
from selenium.webdriver.chrome.options import Options
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    StaleElementReferenceException, WebDriverException
)

# .env 파일에서 환경변수 로드
load_dotenv()

# PyInstaller 번들 환경에서 리소스 경로 처리를 위한 함수
def resource_path(relative_path):
    """앱이 번들되었을 때와 그렇지 않을 때 모두 리소스 경로를 올바르게 가져옵니다."""
    try:
        # PyInstaller가 만든 임시 폴더에서 실행될 때
        base_path = sys._MEIPASS
    except Exception:
        # 일반적인 Python 인터프리터에서 실행될 때
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class NaverBlogAutomation:
    def __init__(self, auto_mode=True, image_insert_mode="random", use_stickers=False, custom_images_folder=None):
        self.driver = None
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.post_folder = os.path.join(self.base_dir, self.today)
        self.images_folder = os.path.join(self.post_folder, "images")
        self.default_images_folder = os.path.join(self.base_dir, "default_images")  # 기본 이미지 폴더
        self.custom_images_folder = custom_images_folder  # 커스텀 이미지 폴더 추가
        self.used_images = []
        self.auto_mode = auto_mode
        self.image_insert_mode = image_insert_mode
        self.use_stickers = False  # 스티커 사용 기능 비활성화
        self.image_inserter = None
        self.need_escape_key = True
        
        # 폴더 생성
        self.create_folders()
        
        # 설정 로드
        self.settings = self.load_settings()
        
    def create_folders(self):
        """필요한 폴더들을 생성합니다."""
        try:
            # 오늘과 내일 날짜 계산
            today = datetime.now()
            tomorrow = today + timedelta(days=1)
            
            # 날짜별 폴더 생성
            for date in [today, tomorrow]:
                date_str = date.strftime("%Y-%m-%d")
                post_folder = os.path.join(self.base_dir, date_str)
                images_folder = os.path.join(post_folder, "images")
                
                # 포스트 폴더 생성
                if not os.path.exists(post_folder):
                    os.makedirs(post_folder)
                    print(f"포스트 폴더 생성 완료: {post_folder}")
                
                # 이미지 폴더 생성
                if not os.path.exists(images_folder):
                    os.makedirs(images_folder)
                    print(f"이미지 폴더 생성 완료: {images_folder}")
            
            # 기본 이미지 폴더 생성
            if not os.path.exists(self.default_images_folder):
                os.makedirs(self.default_images_folder)
                print(f"기본 이미지 폴더 생성 완료: {self.default_images_folder}")
                
        except Exception as e:
            print(f"폴더 생성 중 오류 발생: {str(e)}")
            traceback.print_exc()

    def load_settings(self):
        """설정 파일에서 사용자 정보 로드"""
        settings = {
            "dojang_business_name": "",
            "dojang_name": "",
            "address": "",
            "phone": "",
            "blog_url": "",
            "naver_id": os.getenv('NAVER_ID', ''),
            "naver_pw": os.getenv('NAVER_PW', ''),
            "kakao_url": os.getenv('KAKAO_URL', 'https://open.kakao.com/o/sP6s6YZf'),
            "tags": [],
            "footer_message": ""
        }
        
        try:
            # 일반 경로 시도
            config_path = 'config/user_settings.txt'
            
            # 빌드된 앱에서 경로 시도
            if not os.path.exists(config_path):
                bundled_path = resource_path('config/user_settings.txt')
                if os.path.exists(bundled_path):
                    config_path = bundled_path
                    print(f"빌드 환경에서 설정 파일 발견: {bundled_path}")
            
            # 설정 파일 로드
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    settings_data = json.load(f)
                    
                    # 설정 값 업데이트
                    for key in settings.keys():
                        if key in settings_data:
                            settings[key] = settings_data[key]
                    
                    # 태그 로드
                    if 'blog_tags' in settings_data:
                        tags_str = settings_data['blog_tags']
                        settings['tags'] = [tag.strip() for tag in tags_str.split(',')]
                    
                    print(f"설정 파일 로드 성공: {config_path}")
                    print(f"도장 상호: {settings['dojang_business_name']}")
                    print(f"도장 이름: {settings['dojang_name']}")
                    print(f"주소: {settings['address']}")
                    print(f"푸터 메시지: '{settings['footer_message']}'")
                    print(f"푸터 메시지 길이: {len(settings['footer_message'])}")
                    print(f"푸터 메시지 공백 제거 후 길이: {len(settings['footer_message'].strip())}")
            else:
                print(f"설정 파일을 찾을 수 없습니다: {config_path}")
        except Exception as e:
            print(f"설정 파일 로드 중 오류 발생: {str(e)}")
            traceback.print_exc()
        
        return settings

    def setup_driver(self):
        """Chrome 드라이버 설정"""
        try:
            print("Chrome 드라이버 설정 시작...")
            
            chrome_options = Options()
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-crash-reporter")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-in-process-stack-traces")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_argument("--output=/dev/null")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_experimental_option("detach", True)
            chrome_options.add_experimental_option("prefs", {
                "profile.default_content_setting_values.notifications": 3,
                "profile.default_content_settings.popups": 1,
                "profile.default_content_settings.notifications": 3,
                "profile.content_settings.exceptions.clipboard": {
                    "*": {"setting": 2}
                }
            })
            
            try:
                # PyInstaller 번들에서 실행되는 경우 chromedriver 경로 처리
                chromedriver_path = resource_path("chromedriver")
                print(f"ChromeDriver 경로: {chromedriver_path}")
                
                if os.path.exists(chromedriver_path):
                    print(f"ChromeDriver 파일 존재 확인: {chromedriver_path}")
                    service = Service(executable_path=chromedriver_path)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    print(f"ChromeDriver 파일을 찾을 수 없습니다: {chromedriver_path}")
                    # 기본 방식으로 시도
                    service = Service()
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                print(f"기본 드라이버 초기화 실패, 대체 방법 시도: {str(e)}")
                # 대체 방법: ChromeDriverManager 사용
                from selenium.webdriver.chrome.service import Service as ChromeService
                from webdriver_manager.chrome import ChromeDriverManager
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            self.driver.implicitly_wait(10)
            
            # 자동화 감지 방지를 위한 JavaScript 실행
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 이미지 삽입 핸들러 초기화
            if self.auto_mode:
                print("이미지 삽입 핸들러 초기화 중...")
                fallback_folder = self.custom_images_folder if self.custom_images_folder else self.default_images_folder
                print(f"사용할 이미지 폴더: {fallback_folder}")
                self.image_inserter = NaverBlogImageInserter(
                    driver=self.driver,
                    images_folder=self.images_folder,
                    insert_mode=self.image_insert_mode,
                    fallback_folder=fallback_folder
                )
                print("이미지 삽입 핸들러 초기화 완료")
            else:
                print("자동 이미지 삽입이 비활성화되어 있습니다.")
                self.image_inserter = None
            
            print("Chrome 드라이버 설정 완료!")
            return True
        except Exception as e:
            print(f"드라이버 설정 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return False
        
    def login_naver(self):
        """네이버 로그인"""
        try:
            if not self.setup_driver():
                return False

            self.driver.get('https://nid.naver.com/nidlogin.login')
            time.sleep(0.2)  # 파일 버튼 클릭 후 대기 시간 단축  # 로그인 페이지 로딩 대기 시간 단축
            
            naver_id = self.settings.get('naver_id') or os.getenv('NAVER_ID')
            naver_pw = self.settings.get('naver_pw') or os.getenv('NAVER_PW')
            
            if not naver_id or not naver_pw:
                raise Exception("네이버 로그인 정보가 설정되지 않았습니다.")
            
            self.driver.execute_script(
                """
                document.querySelector("#id").value = arguments[0];
                document.querySelector("#pw").value = arguments[1];
                """,
                naver_id, naver_pw
            )
            # 불필요한 대기 시간 제거  # 로그인 정보 입력 후 대기 시간 단축
            
            login_button = self.driver.find_element(By.ID, 'log.login')
            login_button.click()
            time.sleep(0.2)  # 이미지 컨테이너 대기 시간 단축  # 로그인 버튼 클릭 후 대기 시간 단축
            
            print("네이버 로그인 성공!")
            return True
            
        except Exception as e:
            print(f"로그인 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return False
            
    def go_to_blog(self):
        """블로그 글쓰기 페이지로 이동"""
        try:
            blog_url = self.settings.get('blog_url', 'gm2hapkido')
            self.driver.get(f'https://blog.naver.com/{blog_url}?Redirect=Write')
            time.sleep(0.5)  # 블로그 페이지 로딩 대기 시간 단축
            
            print("블로그 글쓰기 페이지 이동 성공!")
            return True
        except Exception as e:
            print(f"블로그 페이지 이동 중 오류 발생: {str(e)}")
            return False
            
    def handle_esc_key(self):
        """ESC 키 처리를 위한 통합 메서드"""
        try:
            # ESC 키 완전 비활성화 - 불필요한 ESC 키 전송 제거
            return True
        except Exception as e:
            print(f"ESC 키 처리 중 오류: {str(e)}")
            return False

    def find_file_button(self):
        """파일 선택 버튼을 찾는 통합 메서드"""
        file_button_selectors = [
            "button.se-image-file-upload",
            "button[title*='파일']",
            "button.se-image-toolbar-button",
            "button.se-toolbar-button",
            "button[aria-label*='이미지']",
            "button.se-document-toolbar-basic-button",
            "button[data-name='image']",
            "button.se-toolbar-item-image"
        ]
        
        for selector in file_button_selectors:
            try:
                button = WebDriverWait(self.driver, 4).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if button:
                    print(f"파일 선택 버튼 발견: {selector}")
                    return button
            except Exception:
                continue
        
        print("파일 선택 버튼을 찾을 수 없습니다.")
        return None

    def insert_image(self, num_images=1):
        """이미지 삽입을 위한 통합 메서드"""
        try:
            print(f"{num_images}장의 이미지 삽입 시도...")
            
            file_button = self.find_file_button()
            if not file_button:
                return False
                
            # 파일 버튼 클릭 - 다이얼로그를 1번만 열도록 함
            file_button.click()
            print("파일 버튼 클릭 - 이미지 삽입 다이얼로그 열기")
            
            # 대기 시간 최소화 (0.1초만 대기)
            try:
                WebDriverWait(self.driver, 0.1, poll_frequency=0.02).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.se-image-container"))
                )
                print("이미지 컨테이너 영역 확인됨")
            except:
                print("이미지 컨테이너 대기 시간(0.1초) 초과 - 진행 계속")
            
            return True
            
        except Exception as e:
            print(f"이미지 삽입 실패: {str(e)}")
            return False

    def set_font_and_alignment(self):
        """글꼴 및 정렬 설정"""
        try:
            print("글꼴 및 정렬 설정 시작...")
            
            # 글꼴 설정
            try:
                # 랜덤으로 글꼴 선택
                font_options = ["나눔바른고딕", "바른히피"]  # '다시시작해' 제거
                selected_font = random.choice(font_options)
                print(f"선택된 글꼴: {selected_font}")
                
                # '나눔고딕' 텍스트가 있는 버튼을 찾아 클릭
                font_button_found = False
                
                # 1. 버튼 텍스트로 찾기
                try:
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    for button in buttons:
                        try:
                            if "나눔고딕" in button.text or "글꼴" in button.text:
                                button.click()
                                print("'나눔고딕' 텍스트가 있는 버튼 클릭 성공")
                                font_button_found = True
                                break
                        except:
                            continue
                except:
                    print("버튼 텍스트 검색 실패")
                
                # 2. 일반적인 선택자로 찾기
                if not font_button_found:
                    font_selectors = [
                        "button.se-font-family-toolbar-button",
                        "button[data-name='font-family']",
                        "button.se-toolbar-button[title*='글꼴']", 
                        "button.se-toolbar-font-family",
                        "button.__se-sentry.se-toolbar-option-text-button",
                        "button[data-type='label-select'][data-name='font-family']",
                        "div.se-toolbar-dropdown button"
                    ]
                    
                    for selector in font_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for element in elements:
                                try:
                                    if "나눔고딕" in element.text or "글꼴" in element.text:
                                        element.click()
                                        print(f"CSS 선택자로 글꼴 버튼 발견: {selector}")
                                        font_button_found = True
                                        break
                                except:
                                    continue
                            if font_button_found:
                                break
                        except:
                            continue
                
                # 3. JavaScript로 찾기
                if not font_button_found:
                    script = """
                    // 나눔고딕 텍스트가 있는 버튼 찾기
                    function findFontButton() {
                        // 모든 버튼 요소 찾기
                        const buttons = document.querySelectorAll('button');
                        for (const btn of buttons) {
                            if (btn.innerText && (btn.innerText.includes('나눔고딕') || btn.innerText.includes('글꼴'))) {
                                btn.click();
                                return true;
                            }
                        }
                        
                        // 다른 요소들도 확인
                        const allElements = document.querySelectorAll('*');
                        for (const el of allElements) {
                            if (el.innerText && (el.innerText.includes('나눔고딕') || el.innerText.includes('글꼴')) && 
                                (el.tagName === 'BUTTON' || el.tagName === 'DIV' || 
                                el.tagName === 'SPAN' || el.onclick || 
                                el.getAttribute('role') === 'button')) {
                                el.click();
                                return true;
                            }
                        }
                        return false;
                    }
                    return findFontButton();
                    """
                    font_button_found = self.driver.execute_script(script)
                    if font_button_found:
                        print("JavaScript로 글꼴 드롭다운 버튼 클릭 성공")
                    else:
                        print("글꼴 드롭다운 버튼을 찾을 수 없습니다.")
                
                if not font_button_found:
                    print("모든 방법으로 글꼴 버튼을 찾을 수 없습니다.")
                    return False
                
                # 드롭다운 메뉴가 나타날 때까지 충분히 대기
                # 드롭다운 메뉴 로딩 대기 시간 단축
                time.sleep(0.3)
                
                # 글꼴 목록에서 선택한 글꼴 찾기
                font_found = False
                
                # 1. 직접 옵션 요소 찾기
                font_option_selectors = [
                    ".se-toolbar-option-text-button", 
                    ".se-toolbar-option-font-family-button", 
                    "div[role='listbox'] button",
                    "ul.se-toolbar-font-family-list button",
                    "div.se-tooltip-layer button"
                ]
                
                for selector in font_option_selectors:
                    if font_found:
                        break
                    
                    try:
                        option_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for option in option_elements:
                            try:
                                option_text = option.text.strip()
                                if selected_font in option_text:
                                    option.click()
                                    print(f"{selected_font} 글꼴 선택 완료 (선택자: {selector})")
                                    font_found = True
                                    # 글꼴 선택 후 대기 시간 제거
                                    break
                            except:
                                continue
                    except:
                        continue
                
                # 2. JavaScript로 선택
                if not font_found:
                    script = f"""
                    function selectFont() {{
                        const fontItems = document.querySelectorAll('button, div, span, li');
                        for (const item of fontItems) {{
                            if (item.innerText && item.innerText.includes('{selected_font}')) {{
                                item.click();
                                return true;
                            }}
                        }}
                        return false;
                    }}
                    return selectFont();
                    """
                    font_selected = self.driver.execute_script(script)
                    if font_selected:
                        print(f"JavaScript로 {selected_font} 글꼴 선택 성공")
                        font_found = True
                
                if not font_found:
                    print(f"{selected_font} 글꼴을 찾을 수 없어 기본 글꼴을 사용합니다.")
            except Exception as e:
                print(f"글꼴 설정 중 오류 발생: {str(e)}")
                traceback.print_exc()

            # 가운데 정렬 설정
            try:
                # 정렬 버튼 찾기
                align_button_found = False
                
                # 1. 버튼 텍스트나 제목으로 찾기
                try:
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    for button in buttons:
                        try:
                            if "정렬" in button.text or (button.get_attribute("title") and "정렬" in button.get_attribute("title")):
                                button.click()
                                print("정렬 버튼 클릭 성공 (텍스트/제목)")
                                align_button_found = True
                                break
                        except:
                            continue
                except:
                    print("버튼 텍스트/제목 검색 실패")
                
                # 2. CSS 선택자로 찾기
                if not align_button_found:
                    align_selectors = [
                        "button.se-toolbar-align",
                        "button[data-name='align']",
                        "button[title*='정렬']",
                        "button.se-align-toolbar-button"
                    ]
                    
                    for selector in align_selectors:
                        try:
                            align_button = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                            align_button.click()
                            print(f"정렬 버튼 발견: {selector}")
                            align_button_found = True
                            break
                        except:
                            continue
                
                # 3. JavaScript로 찾기
                if not align_button_found:
                    script = """
                    function findAlignButton() {
                        const buttons = document.querySelectorAll('button');
                        for (const btn of buttons) {
                            if ((btn.title && btn.title.includes('정렬')) || 
                                (btn.getAttribute('data-name') === 'align') ||
                                (btn.innerText && btn.innerText.includes('정렬'))) {
                                btn.click();
                                return true;
                            }
                        }
                        
                        const allElements = document.querySelectorAll('*');
                        for (const el of allElements) {
                            if ((el.title && el.title.includes('정렬')) || 
                                (el.getAttribute('data-name') === 'align') ||
                                (el.innerText && el.innerText.includes('정렬'))) {
                                el.click();
                                return true;
                            }
                        }
                        return false;
                    }
                    return findAlignButton();
                    """
                    align_button_found = self.driver.execute_script(script)
                    if align_button_found:
                        print("JavaScript로 정렬 버튼 클릭 성공")
                    else:
                        print("정렬 버튼을 찾을 수 없습니다.")
                
                if not align_button_found:
                    print("모든 방법으로 정렬 버튼을 찾을 수 없습니다.")
                
                # 드롭다운 메뉴가 나타날 때까지 대기
                time.sleep(0.3)  # 대기 시간 대폭 단축
                
                # 가운데 정렬 옵션 찾기
                align_found = False
                
                # 1. CSS 선택자로 찾기
                align_option_selectors = [
                    ".se-toolbar-option-align-center-button", 
                    "button[data-value='center']",
                    "button.se-toolbar-option-icon-button[data-value='center']",
                    "button.__se-sentry.se-toolbar-option-icon-button.se-toolbar-option-align-center-button",
                    "button[title*='가운데']", 
                    "button[aria-label*='가운데']",
                    "ul.se-toolbar-align-list button"
                ]
                
                for selector in align_option_selectors:
                    if align_found:
                        break
                        
                    try:
                        align_options = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for option in align_options:
                            try:
                                print(f"정렬 옵션 검사: {option.get_attribute('class')} - {option.get_attribute('data-value')}")
                                title = option.get_attribute("title") or ""
                                aria_label = option.get_attribute("aria-label") or ""
                                data_value = option.get_attribute("data-value") or ""
                                
                                if "center" in data_value or "가운데" in title or "가운데" in aria_label or "center" in title.lower() or "center" in aria_label.lower():
                                    option.click()
                                    print(f"가운데 정렬 선택 완료 (선택자: {selector})")
                                    align_found = True
                                    # 정렬 선택 후 대기 시간 제거
                                    break
                            except:
                                continue
                    except:
                        continue
                
                # 2. JavaScript로 찾기
                if not align_found:
                    script = """
                    function selectCenterAlign() {
                        console.log('가운데 정렬 옵션 찾기 시작...');
                        
                        // 특정 클래스 이름으로 찾기
                        const centerButtons = document.querySelectorAll('.se-toolbar-option-align-center-button');
                        if (centerButtons.length > 0) {
                            console.log('se-toolbar-option-align-center-button 클래스로 버튼 발견');
                            centerButtons[0].click();
                            return true;
                        }
                        
                        // data-value가 center인 버튼 찾기
                        const centerValueButtons = document.querySelectorAll('button[data-value="center"]');
                        if (centerValueButtons.length > 0) {
                            console.log('data-value="center"로 버튼 발견');
                            centerValueButtons[0].click();
                            return true;
                        }
                        
                        // 모든 버튼 요소 검사
                        const allButtons = document.querySelectorAll('button');
                        for (const btn of allButtons) {
                            console.log(`버튼 검사: ${btn.className}, data-value: ${btn.getAttribute('data-value')}`);
                            
                            if (btn.getAttribute('data-value') === 'center' || 
                                (btn.className && btn.className.includes('center')) ||
                                (btn.title && (btn.title.includes('가운데') || btn.title.toLowerCase().includes('center'))) ||
                                (btn.getAttribute('aria-label') && 
                                    (btn.getAttribute('aria-label').includes('가운데') || 
                                     btn.getAttribute('aria-label').toLowerCase().includes('center')))) {
                                
                                console.log('가운데 정렬 버튼 발견!');
                                btn.click();
                                return true;
                            }
                        }
                        
                        // 다른 요소들도 확인
                        const allElements = document.querySelectorAll('*');
                        for (const el of allElements) {
                            if (el.getAttribute('data-value') === 'center' || 
                                (el.className && el.className.includes('center')) ||
                                (el.title && (el.title.includes('가운데') || el.title.toLowerCase().includes('center'))) ||
                                (el.getAttribute('aria-label') && 
                                (el.getAttribute('aria-label').includes('가운데') || 
                                 el.getAttribute('aria-label').toLowerCase().includes('center')))) {
                                
                                if (el.tagName === 'BUTTON' || el.tagName === 'DIV' || el.tagName === 'SPAN' || 
                                    el.onclick || el.getAttribute('role') === 'button') {
                                    console.log(`가운데 정렬 요소 발견: ${el.tagName}`);
                                    el.click();
                                    return true;
                                }
                            }
                        }
                        
                        console.log('가운데 정렬 옵션을 찾을 수 없습니다.');
                        return false;
                    }
                    return selectCenterAlign();
                    """
                    
                    align_selected = self.driver.execute_script(script)
                    if align_selected:
                        print("JavaScript로 가운데 정렬 선택 성공")
                        align_found = True
                
                if not align_found:
                    print("가운데 정렬 옵션을 찾을 수 없어 기본 정렬을 사용합니다.")
            except Exception as e:
                print(f"정렬 설정 중 오류 발생: {str(e)}")
                traceback.print_exc()
            
            print("글꼴 및 정렬 설정 완료")
            return True
        except Exception as e:
            print(f"글꼴 및 정렬 설정 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return False

    def calculate_image_positions(self, content):
        """이미지 삽입 위치를 계산하는 메서드 - 첫 이미지는 100자 이후 문장 끝, 이후 200자 간격으로 문장 끝에 이미지 삽입"""
        content_lines = content.split('\n')
        
        # 문장 끝 표시
        sentence_end_markers = ['다.', '요.', '죠.', '.', '!', '?']
        
        # 단순하게 줄 번호 기반으로 위치 계산
        line_positions = []
        char_count = 0
        is_first_image = True
        
        for i, line in enumerate(content_lines):
            line_text = line.strip()
            char_count += len(line)
            
            # 문장 끝 조건 확인 - 줄의 마지막이 문장 끝 표시인지
            is_sentence_end = any(line_text.endswith(marker) for marker in sentence_end_markers)
            
            # 첫 번째 이미지는 100자 정도에 도달한 후 문장이 끝나는 곳에 삽입
            if is_first_image and char_count >= 100 and is_sentence_end:
                line_positions.append(i)
                print(f"첫 번째 이미지 위치 추가: 줄 {i} (누적 글자 수: {char_count}, 문장 끝 위치)")
                char_count = 0  # 글자 수 리셋
                is_first_image = False
            # 이후 이미지는 200자마다 문장이 끝나는 곳에 삽입
            elif not is_first_image and char_count >= 200 and is_sentence_end:
                line_positions.append(i)
                print(f"이미지 위치 추가: 줄 {i} (누적 글자 수: {char_count}, 문장 끝 위치)")
                char_count = 0  # 글자 수 리셋
        
        # 충분한 이미지 위치를 찾지 못한 경우 (문장 끝 조건이 충족되지 않은 경우)
        if len(line_positions) < 3:
            print(f"충분한 문장 끝 위치를 찾지 못했습니다. 글자 수만으로 위치를 계산합니다.")
            
            # 초기화
            line_positions = []
            char_count = 0
            is_first_image = True
            
            for i, line in enumerate(content_lines):
                char_count += len(line)
                
                # 첫 번째 이미지는 100자 정도에 삽입
                if is_first_image and char_count >= 100:
                    line_positions.append(i)
                    print(f"첫 번째 이미지 위치 추가(글자 수 기준): 줄 {i} (누적 글자 수: {char_count})")
                    char_count = 0  # 글자 수 리셋
                    is_first_image = False
                # 이후 이미지는 200자마다 삽입
                elif not is_first_image and char_count >= 200:
                    line_positions.append(i)
                    print(f"이미지 위치 추가(글자 수 기준): 줄 {i} (누적 글자 수: {char_count})")
                    char_count = 0  # 글자 수 리셋
        
        print(f"계산된 이미지 위치: {line_positions} (총 {len(line_positions)}개)")
        return line_positions

    def write_post(self, title, content, tags=None):
        """블로그 포스트 작성"""
        try:
            # 설정 확인 (디버깅용)
            print("\n===== 설정 확인 (write_post 시작) =====")
            print(f"도장 상호: {self.settings.get('dojang_business_name', '없음')}")
            print(f"도장 이름: {self.settings.get('dojang_name', '없음')}")
            print(f"주소: {self.settings.get('address', '없음')}")
            print(f"푸터 메시지: '{self.settings.get('footer_message', '없음')}'")
            if 'footer_message' in self.settings:
                print(f"푸터 메시지 존재함: '{self.settings['footer_message']}'")
            else:
                print("푸터 메시지가 settings 객체에 존재하지 않음")
            print("===== 설정 확인 완료 =====\n")
            
            # 이미지 삽입 위치 간단하게 계산
            image_positions = self.calculate_image_positions(content)
            print(f"계산된 이미지 위치 정보를 사용합니다: {image_positions}")
            
            # 블로그 글쓰기 페이지로 이동
            self.driver.get("https://blog.naver.com/gm2hapkido?Redirect=Write&")
            time.sleep(1)

            # iframe 전환
            try:
                iframe = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.ID, "mainFrame"))
                )
                self.driver.switch_to.frame(iframe)
                print("iframe 전환 성공")
            except Exception as e:
                print(f"iframe 전환 실패: {str(e)}")
                return False
            
            # 이전 글 확인 팝업 처리
            try:
                popup = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "se-popup-button-cancel"))
                )
                popup.click()
                time.sleep(0.2)
            except:
                print("이전 글 확인 팝업이 없습니다.")

            # 제목 입력
            try:
                title_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".se-title-text .se-text-paragraph"))
                )
                title_element.click()
                time.sleep(0.2)
                
                actions = ActionChains(self.driver)
                actions.send_keys(title).perform()
                time.sleep(0.2)
                print("제목 입력 성공")
            except Exception as e:
                print(f"제목 입력 실패: {str(e)}")
                return False

            # 본문 설정
            try:
                body_area = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.se-component.se-text.se-l-default"))
                )
                body_area.click()
                print("본문 영역 클릭 성공")
                time.sleep(0.5)

                # 글꼴 및 정렬 설정
                self.set_font_and_alignment()
                time.sleep(0.3)
            except Exception as e:
                print(f"본문 영역 설정 실패: {str(e)}")
                return False
            
            # 본문 입력을 위한 변수 초기화
            current_line = 0
            current_image_index = 0
            consecutive_text_lines = 0
            
            def should_add_blank_line(current_text, next_text=None):
                """줄바꿈이 필요한지 확인하는 함수"""
                if not current_text:
                    return False
                    
                # 특수 문자(⸻) 앞뒤로 빈 줄 추가
                if '⸻' in current_text:
                    return True
                    
                # 리스트 항목 앞뒤로 빈 줄 추가
                if current_text.strip().startswith('•') or (next_text and next_text.strip().startswith('•')):
                    return True
                    
                # 긴 문단(3줄 이상) 후에 빈 줄 추가
                if consecutive_text_lines >= 3:
                    return True
                    
                # 문장 끝에 마침표가 있고, 다음 줄이 새로운 문단의 시작인 경우
                if current_text.strip().endswith(('.', '?', '!', '다.', '요.', '죠.')) and next_text:
                    if not next_text.strip().startswith('•'):
                        return True
                        
                return False
            
            # 본문 내용 입력
            content_lines = content.split('\n')
            for i, line in enumerate(content_lines):
                current_line = i
                
                # 현재 줄이 실제 텍스트를 포함하는지 확인
                is_text_line = bool(line.strip())
                
                # 연속된 텍스트 줄 수 추적
                if is_text_line:
                    consecutive_text_lines += 1
                else:
                    consecutive_text_lines = 0
                
                # 줄바꿈 추가 여부 확인
                next_line = content_lines[i + 1] if i + 1 < len(content_lines) else None
                if should_add_blank_line(line, next_line):
                    actions = ActionChains(self.driver)
                    actions.send_keys(line)
                    actions.perform()
                    time.sleep(0.05)
                    
                    # 두 번의 Enter 키를 명시적으로 개별 작업으로 보냄
                    actions = ActionChains(self.driver)
                    actions.send_keys(Keys.ENTER)
                    actions.perform()
                    actions.send_keys(Keys.ENTER)
                    actions.perform()
                    
                    consecutive_text_lines = 0
                else:
                    actions = ActionChains(self.driver)
                    actions.send_keys(line + Keys.ENTER)
                    actions.perform()
                    time.sleep(0.05)  # 입력 사이 최소 대기 시간
                
                # 이미지 삽입 조건 확인 (미리 계산된 줄 번호에 도달했을 때)
                if (self.auto_mode and
                    self.image_inserter and
                    current_line in image_positions and 
                    current_image_index < len(self.image_inserter.get_image_files())):
                    
                    try:
                        print(f"줄 {current_line}: 이미지 삽입 시도...")
                        
                        image_files = self.image_inserter.get_image_files()
                        if image_files and current_image_index < len(image_files):
                            image_path = image_files[current_image_index]
                            print(f"이미지 삽입 중: {os.path.basename(image_path)}")
                            self.image_inserter.insert_single_image(image_path)
                            print(f"줄 {current_line}: 이미지 삽입 성공!")
                            current_image_index += 1
                            
                            # 본문 재포커스
                            try:
                                body_areas = self.driver.find_elements(By.CSS_SELECTOR, 
                                    "div.se-component.se-text.se-l-default")
                                if body_areas:
                                    self.driver.execute_script("arguments[0].click();", body_areas[-1])
                                    print("이미지 삽입 후 본문 재포커스 성공")
                            except Exception as refocus_error:
                                print(f"본문 재포커스 실패: {str(refocus_error)}")
                        else:
                            print(f"줄 {current_line}: 삽입할 이미지가 없습니다.")
                    except Exception as e:
                        print(f"이미지 삽입 중 오류: {str(e)}")
                        traceback.print_exc()

            # 본문 영역 다시 클릭하여 포커스 확보
            try:
                body_areas = self.driver.find_elements(By.CSS_SELECTOR, 
                    "div.se-component.se-text.se-l-default")
                if body_areas:
                    self.driver.execute_script("arguments[0].click();", body_areas[-1])
                    print("남은 이미지 삽입 전 본문 재포커스 성공")
                    time.sleep(0.5)
            except Exception as refocus_error:
                print(f"본문 재포커스 실패: {str(refocus_error)}")

            # 남은 이미지들 마지막에 삽입
            if self.auto_mode and self.image_inserter:
                image_files = self.image_inserter.get_image_files()
                remaining_images = len(image_files) - current_image_index
                if remaining_images > 0:
                    print(f"마지막에 {remaining_images}개의 이미지를 삽입합니다.")
                    for i in range(current_image_index, len(image_files)):
                        try:
                            image_path = image_files[i]
                            print(f"이미지 삽입 중: {os.path.basename(image_path)}")
                            self.image_inserter.insert_single_image(image_path)
                            time.sleep(0.3)  # 이미지 삽입 사이에 약간의 딜레이 추가
                        except Exception as e:
                            print(f"이미지 삽입 중 오류: {str(e)}")
                            traceback.print_exc()
                    
                    # 마지막 이미지 삽입 후 본문 재포커스
                    try:
                        body_areas = self.driver.find_elements(By.CSS_SELECTOR, 
                            "div.se-component.se-text.se-l-default")
                        if body_areas:
                            self.driver.execute_script("arguments[0].click();", body_areas[-1])
                            print("최종 이미지 삽입 후 본문 재포커스 성공")
                    except Exception as refocus_error:
                        print(f"본문 재포커스 실패: {str(refocus_error)}")
            
            # 푸터 추가 직접 호출
            print("add_footer 메서드 호출 시작...")
            
            # 현재 settings 객체 상태 출력
            print("\n===== NaverBlogAuto 현재 settings 상태 =====")
            for key in ['dojang_business_name', 'dojang_name', 'footer_message', 'address']:
                print(f"{key}: '{self.settings.get(key, '<없음>')}'")
            print("settings 객체 모든 키:", list(self.settings.keys()))
            
            # 설정을 명시적으로 복사하여 새 객체 생성
            post_settings = self.settings.copy() if isinstance(self.settings, dict) else {}
            
            # 설정 파일 확인 (footer_message가 누락되었을 수 있음)
            try:
                with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config/user_settings.txt'), 'r', encoding='utf-8') as f:
                    file_settings = json.load(f)
                    if 'footer_message' in file_settings:
                        post_settings['footer_message'] = file_settings['footer_message']
                        print(f"설정 파일에서 footer_message 확인: '{post_settings['footer_message']}'")
                    if 'dojang_business_name' in file_settings:
                        post_settings['dojang_business_name'] = file_settings['dojang_business_name']
                        print(f"설정 파일에서 dojang_business_name 확인: '{post_settings['dojang_business_name']}'")
            except Exception as e:
                print(f"설정 파일 확인 중 오류 발생: {str(e)}")
            
            # NaverBlogPostFinisher 생성 시 명시적 설정 전달
            post_finisher = NaverBlogPostFinisher(self.driver, post_settings)
            
            # 현재 상태 확인 - 디버깅을 위한 정보 출력
            print("Driver 상태: " + ("유효함" if self.driver else "유효하지 않음"))
            print("Settings 객체가 전달됐는지 확인: " + ("전달됨" if post_finisher.settings else "전달 안됨"))
            if post_finisher.settings:
                print("전달된 Settings 내용:")
                for key in ['dojang_name', 'footer_message', 'address']:
                    print(f"- {key}: '{post_finisher.settings.get(key, '<없음>')}'")
            
            # 줄바꿈 추가
            print("줄바꿈 추가...")
            actions = ActionChains(self.driver)
            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
            print("줄바꿈 추가 완료")
            
            # 푸터 추가 직접 호출
            print("add_footer 메서드 호출 시작...")
            footer_result = post_finisher.add_footer()
            print(f"add_footer 메서드 결과: {footer_result}")
            
            # 태그 추가
            if tags:
                print("add_tags 메서드 호출 시작 (사용자 제공 태그)...")
                tags_result = post_finisher.add_tags(tags)
                print(f"add_tags 메서드 결과: {tags_result}")
            else:
                # 설정에서 로드한 태그 사용
                print("add_tags 메서드 호출 시작 (설정 태그)...")
                load_tags = self.settings.get('tags', [])
                if load_tags:
                    print(f"설정에서 로드한 태그 수: {len(load_tags)}")
                    tags_result = post_finisher.add_tags(load_tags)
                    print(f"add_tags 메서드 결과: {tags_result}")
                else:
                    print("설정된 태그가 없습니다. 태그 추가를 건너뜁니다.")
            
            print("============ 푸터 및 링크 추가 완료 ============\n")
            
            # 마지막 문구에서 상호명과 푸터 메시지 사용
            footer_message = self.settings.get('footer_message', '')
            
            # 도장 상호 또는 도장 이름 가져오기
            dojang_business_name = self.settings.get('dojang_business_name', '')
            if not dojang_business_name:  # 도장 상호가 없으면 도장 이름을 대신 사용
                dojang_business_name = self.settings.get('dojang_name', '')
                
            if footer_message and footer_message.strip():
                final_message = f"이상 {footer_message} {dojang_business_name} 이었습니다"
            else:
                final_message = f"이상 이었습니다"
            print(final_message)
            
            return True
            
        except Exception as e:
            print(f"본문 입력 중 오류 발생: {str(e)}")
            traceback.print_exc()
            
            # 오류 발생 시 복구 시도
            try:
                # ESC 키를 눌러 열린 대화상자를 닫음
                actions = ActionChains(self.driver)
                actions.send_keys(Keys.ESCAPE).perform()
                time.sleep(0.1)
                actions.send_keys(Keys.ESCAPE).perform()
                
                # 본문 영역 클릭 시도
                body_areas = self.driver.find_elements(By.CSS_SELECTOR, 
                    "div.se-component.se-text.se-l-default")
                if body_areas:
                    self.driver.execute_script("arguments[0].click();", body_areas[-1])
                    print("글로벌 오류 복구: 본문 영역 재포커스 성공")
                
                # 푸터 추가 시도
                try:
                    post_finisher = NaverBlogPostFinisher(self.driver, self.settings)
                    post_finisher.add_footer()
                    post_finisher.add_tags(self.settings.get('tags', []))
                except Exception as footer_error:
                    print(f"푸터 추가 중 오류: {str(footer_error)}")
                
                return False
            except Exception as recovery_error:
                print(f"복구 중 추가 오류: {str(recovery_error)}")
                return False 

    def setup_image_inserter(self):
        """이미지 삽입 도우미 설정"""
        try:
            from naver_blog_auto_image import NaverBlogImageInserter
            
            # 날짜별 이미지 폴더 확인
            image_folder = self.images_folder if os.path.exists(self.images_folder) else None
            
            # 이미지 삽입 도우미 초기화
            fallback_folder = self.custom_images_folder if self.custom_images_folder else self.default_images_folder
            
            self.image_inserter = NaverBlogImageInserter(
                self.driver,
                images_folder=image_folder,
                insert_mode=self.image_insert_mode,
                fallback_folder=fallback_folder
            )
            
            print(f"이미지 삽입 도우미 초기화 완료: {self.image_insert_mode} 모드")
            print(f"이미지 폴더: {image_folder}")
            print(f"대체 이미지 폴더: {fallback_folder}")
            
            return True
        except Exception as e:
            print(f"이미지 삽입 도우미 설정 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return False 