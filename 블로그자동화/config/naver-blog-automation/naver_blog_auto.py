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
            "dojang_name": "",
            "address": "",
            "phone": "",
            "blog_url": "",
            "naver_id": os.getenv('NAVER_ID', ''),
            "naver_pw": os.getenv('NAVER_PW', ''),
            "kakao_url": os.getenv('KAKAO_URL', 'https://open.kakao.com/o/sP6s6YZf'),
            "slogan": "바른 인성을 가진 인재를 기르는 한국체대 라이온 태권도 합기도",
            "tags": []
        }
        
        try:
            # 배포용 설정 파일 경로 처리 (우선순위 순서)
            config_paths = [
                # 1. 현재 디렉토리의 config 폴더 (개발 환경)
                os.path.join(self.base_dir, 'config', 'user_settings.txt'),
                # 2. settings 폴더의 JSON 파일 (앱 내 설정)
                os.path.join(self.base_dir, 'settings', 'user_settings.json'),
                # 3. PyInstaller 번들 리소스
                resource_path('config/user_settings.txt'),
                resource_path('settings/user_settings.json')
            ]
            
            config_found = False
            for config_path in config_paths:
                print(f"설정 파일 경로 확인 중: {config_path}")
                if os.path.exists(config_path):
                    print(f"설정 파일 발견: {config_path}")
                    config_found = True
                    break
            
            if not config_found:
                print("설정 파일을 찾을 수 없습니다. 기본값을 사용합니다.")
                return settings
            
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
                    
                    # 슬로건 로드
                    if 'slogan' in settings_data:
                        settings['slogan'] = settings_data['slogan']
                    
                    print(f"설정 파일 로드 성공: {config_path}")
                    print(f"도장 이름: {settings['dojang_name']}")
                    print(f"주소: {settings['address']}")
            else:
                print(f"설정 파일을 찾을 수 없습니다: {config_path}")
        except Exception as e:
            print(f"설정 파일 로드 중 오류 발생: {str(e)}")
            traceback.print_exc()
        
        return settings

    def _fix_chromedriver_permissions(self, driver_path):
        """macOS에서 ChromeDriver 권한 수정"""
        try:
            import subprocess
            import platform
            
            # macOS에서만 실행
            if platform.system() != "Darwin":
                return True
                
            print(f"🔧 ChromeDriver 권한 수정 중: {driver_path}")
            
            # 실행 권한 부여
            subprocess.run(["chmod", "+x", driver_path], check=True)
            print("✅ 실행 권한 부여 완료")
            
            # quarantine 속성 제거 (macOS 보안 기능)
            try:
                subprocess.run(["xattr", "-d", "com.apple.quarantine", driver_path], 
                             capture_output=True, check=False)
                print("✅ quarantine 속성 제거 완료")
            except:
                pass
            
            # provenance 속성 제거 (macOS 보안 기능)
            try:
                subprocess.run(["xattr", "-d", "com.apple.provenance", driver_path], 
                             capture_output=True, check=False)
                print("✅ provenance 속성 제거 완료")
            except:
                pass
                
            return True
            
        except Exception as e:
            print(f"⚠️ ChromeDriver 권한 수정 실패: {e}")
            return False

    def setup_driver(self):
        """Chrome 드라이버 설정"""
        try:
            print("Chrome 드라이버 설정 시작...")
            
            # 기존 크롬 프로세스 완전 정리 (충돌 방지)
            import psutil
            import subprocess
            
            try:
                print("🧹 기존 크롬 프로세스 정리 중...")
                
                # 모든 크롬 관련 프로세스 종료
                killed_count = 0
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if proc.info['name'] and ('chrome' in proc.info['name'].lower() or 'chromedriver' in proc.info['name'].lower()):
                            print(f"크롬 프로세스 종료: PID {proc.info['pid']} - {proc.info['name']}")
                            proc.terminate()
                            try:
                                proc.wait(timeout=3)
                                killed_count += 1
                            except psutil.TimeoutExpired:
                                proc.kill()  # 강제 종료
                                killed_count += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                        
                print(f"✅ {killed_count}개 프로세스 종료 완료")
                time.sleep(5)  # 충분한 대기 시간
                
            except Exception as e:
                print(f"기존 프로세스 정리 중 오류 (무시): {e}")
            
            chrome_options = Options()
            
            # 브라우저 프로필 저장 경로 설정 (로그인 상태 유지) - manual_session_helper와 동일한 경로 사용
            profile_path = os.path.join(self.base_dir, "manual_chrome_profile")
            os.makedirs(profile_path, exist_ok=True)
            chrome_options.add_argument(f"--user-data-dir={profile_path}")
            chrome_options.add_argument("--profile-directory=Default")
            
            # 프로필 충돌 방지를 위한 추가 옵션
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            
            # 기본 성능 및 보안 설정
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
            
            # 브라우저 안정성 향상 설정
            chrome_options.add_argument("--disable-hang-monitor")
            chrome_options.add_argument("--disable-prompt-on-repost")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-features=TranslateUI")
            chrome_options.add_argument("--disable-component-extensions-with-background-pages")
            chrome_options.add_argument("--disable-default-apps")
            chrome_options.add_argument("--disable-sync")
            chrome_options.add_argument("--metrics-recording-only")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--safebrowsing-disable-auto-update")
            chrome_options.add_argument("--enable-automation")
            chrome_options.add_argument("--password-store=basic")
            chrome_options.add_argument("--use-mock-keychain")
            
            # 강화된 자동화 감지 방지 설정
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 실제 사용자처럼 보이게 하는 설정
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')
            chrome_options.add_argument('--accept-lang=ko-KR,ko;q=0.9,en;q=0.8')
            
            # 추가 보안 우회 설정
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-ipc-flooding-protection')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-client-side-phishing-detection')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            
            # 권한 팝업 완전 차단을 위한 핵심 설정
            chrome_options.add_argument('--disable-permissions-api')
            chrome_options.add_argument('--disable-permission-action-reporting')
            chrome_options.add_argument('--disable-features=PermissionRequestChip,PermissionQuietChip')
            chrome_options.add_argument('--disable-features=PermissionsSecurityModel')
            chrome_options.add_argument('--disable-features=PermissionDelegation')
            chrome_options.add_argument('--disable-features=BlockInsecurePrivateNetworkRequests')
            chrome_options.add_argument('--disable-site-isolation-trials')
            chrome_options.add_argument('--autoplay-policy=no-user-gesture-required')
            chrome_options.add_argument('--disable-features=MediaRouter')
            chrome_options.add_argument('--disable-component-update')
            chrome_options.add_argument('--disable-domain-reliability')
            
            # 클립보드 권한 완전 허용을 위한 추가 설정
            chrome_options.add_argument('--disable-features=UserMediaScreenCapturing')
            chrome_options.add_argument('--disable-features=WebRtcHideLocalIpsWithMdns')
            chrome_options.add_argument('--disable-features=WebRtcUseEchoCanceller3')
            chrome_options.add_argument('--disable-features=WebRtcHybridAgc')
            chrome_options.add_argument('--allow-clipboard-read-write')
            chrome_options.add_argument('--disable-features=PermissionElement')
            chrome_options.add_argument('--disable-features=PermissionPredictionService')
            chrome_options.add_argument('--disable-features=QuietNotificationPrompts')
            chrome_options.add_argument('--disable-features=AbusiveExperienceEnforce')
            chrome_options.add_argument('--disable-features=BlockAbusiveExperiences')
            
            chrome_options.add_experimental_option("detach", True)
            
            # 클립보드 권한 완전 허용을 위한 정책 설정
            chrome_options.add_argument('--unsafely-treat-insecure-origin-as-secure=https://blog.naver.com')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-features=AudioServiceOutOfProcess')
            chrome_options.add_argument('--disable-features=AudioServiceSandbox')
            chrome_options.add_argument('--disable-features=CalculateNativeWinOcclusion')
            chrome_options.add_argument('--disable-features=GetDisplayMedia')
            chrome_options.add_argument('--disable-features=PortalsCrossOrigin,Portals')
            chrome_options.add_argument('--disable-features=ImprovedCookieControls')
            chrome_options.add_argument('--disable-features=LazyFrameLoading')
            chrome_options.add_argument('--disable-features=GlobalMediaControls,GlobalMediaControlsForCast')
            chrome_options.add_argument('--disable-features=MediaSessionService')
            chrome_options.add_argument('--disable-features=HardwareMediaKeyHandling,MediaSessionAPI')
            chrome_options.add_argument('--disable-features=PictureInPicture')
            
            chrome_options.add_experimental_option("prefs", {
                "profile.default_content_setting_values.notifications": 3,
                "profile.default_content_settings.popups": 1,
                "profile.default_content_settings.notifications": 3,
                # 클립보드 권한 자동 허용 설정 강화
                "profile.content_settings.exceptions.clipboard": {
                    "*": {"setting": 1},  # 1 = 허용, 2 = 차단
                    "https://blog.naver.com": {"setting": 1},
                    "https://naver.com": {"setting": 1},
                    "https://*.naver.com": {"setting": 1},
                    "[*.]naver.com": {"setting": 1},
                    "blog.naver.com": {"setting": 1},
                    "naver.com": {"setting": 1},
                    "*.naver.com": {"setting": 1}
                },
                "profile.default_content_setting_values.clipboard": 1,
                "profile.managed_default_content_settings.clipboard": 1,
                # 추가 권한 설정
                "profile.default_content_setting_values.media_stream_mic": 2,
                "profile.default_content_setting_values.media_stream_camera": 2,
                "profile.default_content_setting_values.geolocation": 2,
                # 권한 팝업 완전 차단
                "profile.default_content_setting_values.permission_autoblocking_data": 1,
                "profile.default_content_setting_values.mixed_script": 1,
                "profile.default_content_setting_values.protocol_handlers": 1,
                "profile.default_content_setting_values.ppapi_broker": 2,
                "profile.default_content_setting_values.automatic_downloads": 1,
                # 브라우저 권한 요청 팝업 차단
                "profile.default_content_setting_values.permission_requests": 2,
                "profile.default_content_setting_values.permission_autoblocking_data": 1,
                # 클립보드 관련 추가 설정
                "profile.content_settings.pattern_pairs": {
                    "https://blog.naver.com,*": {
                        "clipboard": {"setting": 1}
                    },
                    "https://naver.com,*": {
                        "clipboard": {"setting": 1}
                    }
                }
            })
            
            # 로컬 ChromeDriver 우선 시도
            try:
                print("로컬 ChromeDriver 사용을 시도합니다...")
                
                # 프로젝트 루트의 ChromeDriver도 포함
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(self.base_dir)))
                chromedriver_paths = [
                    os.path.join(project_root, "chromedriver"),  # 프로젝트 루트
                    os.path.join(self.base_dir, "chromedriver-mac-arm64", "chromedriver"),
                    os.path.join(self.base_dir, "chromedriver"),
                    resource_path("chromedriver-mac-arm64/chromedriver"),
                    resource_path("chromedriver")
                ]
                
                driver_found = False
                for chromedriver_path in chromedriver_paths:
                    if os.path.exists(chromedriver_path):
                        print(f"✅ 로컬 ChromeDriver 발견: {chromedriver_path}")
                        if not os.access(chromedriver_path, os.X_OK):
                            os.chmod(chromedriver_path, 0o755)
                        
                        # macOS에서 ChromeDriver 권한 수정
                        self._fix_chromedriver_permissions(chromedriver_path)
                        
                        service = Service(executable_path=chromedriver_path)
                        self.driver = webdriver.Chrome(service=service, options=chrome_options)
                        print("✅ 로컬 ChromeDriver 초기화 성공!")
                        driver_found = True
                        break
                
                if not driver_found:
                    raise Exception("로컬 ChromeDriver를 찾을 수 없습니다.")
                        
            except Exception as e:
                print(f"로컬 ChromeDriver 실패: {str(e)}")
                print("WebDriverManager를 사용하여 자동 다운로드를 시도합니다...")
                
                # 백업 방법: WebDriverManager 사용
                try:
                    # WebDriverManager를 사용하여 자동으로 최신 ChromeDriver 다운로드
                    from webdriver_manager.chrome import ChromeDriverManager
                    from selenium.webdriver.chrome.service import Service as ChromeService
                    
                    # 자동으로 Chrome 버전에 맞는 ChromeDriver 다운로드 및 설치
                    driver_path = ChromeDriverManager().install()
                    print(f"ChromeDriver 자동 설치 완료: {driver_path}")
                    
                    # WebDriverManager가 잘못된 파일을 반환하는 경우 수정
                    if driver_path.endswith('THIRD_PARTY_NOTICES.chromedriver'):
                        actual_chromedriver = os.path.dirname(driver_path) + '/chromedriver'
                        if os.path.exists(actual_chromedriver):
                            print(f"✅ 올바른 ChromeDriver 파일 사용: {actual_chromedriver}")
                            os.chmod(actual_chromedriver, 0o755)
                            driver_path = actual_chromedriver
                    
                    # macOS에서 ChromeDriver 권한 수정
                    self._fix_chromedriver_permissions(driver_path)
                    
                    service = ChromeService(executable_path=driver_path)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    print("WebDriverManager ChromeDriver 초기화 성공!")
                        
                except Exception as backup_error:
                    print(f"WebDriverManager도 실패: {str(backup_error)}")
                    raise Exception(f"ChromeDriver를 초기화할 수 없습니다. Chrome 브라우저가 설치되어 있는지 확인하세요. 원본 오류: {str(e)}")
            
            self.driver.implicitly_wait(10)
            
            # 강화된 자동화 감지 방지 및 클립보드 권한 자동 허용을 위한 JavaScript 실행
            stealth_script = """
                // webdriver 속성 숨기기
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                
                // automation 관련 속성들 숨기기
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko', 'en-US', 'en']});
                
                // Chrome 관련 속성 설정
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                
                // 클립보드 권한 자동 허용 설정
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => {
                    if (parameters.name === 'clipboard-read' || parameters.name === 'clipboard-write') {
                        return Promise.resolve({ state: 'granted' });
                    }
                    if (parameters.name === 'notifications') {
                        return Promise.resolve({ state: Notification.permission });
                    }
                    return originalQuery(parameters);
                };
                
                // 클립보드 API 오버라이드
                if (navigator.clipboard) {
                    const originalWriteText = navigator.clipboard.writeText;
                    const originalReadText = navigator.clipboard.readText;
                    
                    navigator.clipboard.writeText = function(text) {
                        return Promise.resolve();
                    };
                    
                    navigator.clipboard.readText = function() {
                        return Promise.resolve('');
                    };
                }
                
                // 권한 요청 팝업 자동 허용
                window.addEventListener('beforeunload', function() {
                    // 권한 팝업이 나타나면 자동으로 허용 버튼 클릭
                    setTimeout(() => {
                        const allowButtons = document.querySelectorAll('button[data-testid="allow"], button:contains("허용"), button:contains("Allow")');
                        allowButtons.forEach(btn => {
                            if (btn && btn.offsetParent !== null) {
                                btn.click();
                            }
                        });
                    }, 100);
                });
                
                // 페이지 로드 시 권한 팝업 처리
                document.addEventListener('DOMContentLoaded', function() {
                    setTimeout(() => {
                        const allowButtons = document.querySelectorAll('button[data-testid="allow"], button:contains("허용"), button:contains("Allow")');
                        allowButtons.forEach(btn => {
                            if (btn && btn.offsetParent !== null) {
                                btn.click();
                            }
                        });
                    }, 1000);
                });
                
                // 추가 보안 우회
                Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 1});
                Object.defineProperty(navigator, 'userAgent', {
                    get: () => 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
                });
            """
            
            try:
                self.driver.execute_script(stealth_script)
                print("자동화 감지 방지 스크립트 실행 완료")
            except Exception as e:
                print(f"자동화 감지 방지 스크립트 실행 실패: {e}")
                # 실패해도 계속 진행
            
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
        """네이버 로그인 (수동 세션 기반)"""
        import json
        cookies_path = os.path.join(self.base_dir, 'naver_cookies.json')
        
        try:
            if not self.setup_driver():
                return False

            # 수동 세션 기반 로그인 시도
            print("🔍 수동 세션 기반 로그인 시도 중...")
            
            if not os.path.exists(cookies_path):
                print("❌ 저장된 세션 파일이 없습니다!")
                print("먼저 manual_session_helper.py를 실행하여 수동 로그인을 완료해주세요.")
                print("명령어: python manual_session_helper.py")
                return False
            
            print(f"✅ 세션 파일 발견: {cookies_path}")
            
            # 네이버 메인 페이지로 이동
            print("🌐 네이버 메인 페이지로 이동...")
            self.driver.get('https://www.naver.com')
            time.sleep(2)
            
            # 쿠키 로드 및 적용
            print("🍪 저장된 쿠키 로드 중...")
            with open(cookies_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            print(f"로드된 쿠키 개수: {len(cookies)}")
            
            # 쿠키 적용
            successful_cookies = 0
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                    successful_cookies += 1
                except Exception as e:
                    print(f"쿠키 적용 실패: {cookie.get('name', 'unknown')} - {e}")
                    continue
            
            print(f"성공적으로 적용된 쿠키: {successful_cookies}/{len(cookies)}")
            
            # 페이지 새로고침하여 로그인 상태 적용
            print("🔄 페이지 새로고침...")
            self.driver.refresh()
            time.sleep(3)
            
            # 로그인 상태 확인
            page_source = self.driver.page_source
            if "로그아웃" in page_source or "님" in page_source:
                print("✅ 메인 페이지에서 로그인 상태 확인!")
                
                # 블로그 페이지로 이동하여 최종 확인
                print("📝 네이버 블로그로 이동...")
                self.driver.get('https://blog.naver.com')
                time.sleep(3)
                
                current_url = self.driver.current_url
                page_source = self.driver.page_source
                
                print(f"블로그 URL: {current_url}")
                
                if "로그아웃" in page_source or "님" in page_source:
                    print("✅ 블로그에서도 로그인 상태 확인!")
                    
                    # 글쓰기 버튼 확인
                    try:
                        write_selectors = [
                            "a[href*='write']",
                            ".btn_write",
                            "[class*='write']",
                            "a[href*='PostWriteForm']"
                        ]
                        
                        write_button_found = False
                        for selector in write_selectors:
                            try:
                                write_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                                if write_button:
                                    print("✅ 글쓰기 버튼 발견!")
                                    write_button_found = True
                                    break
                            except:
                                continue
                        
                        if write_button_found:
                            print("🎉 수동 세션 기반 로그인 성공!")
                            return True
                        else:
                            print("⚠️ 글쓰기 버튼을 찾을 수 없지만 로그인은 성공한 것 같습니다.")
                            return True
                            
                    except Exception as e:
                        print(f"글쓰기 버튼 확인 중 오류: {e}")
                        print("하지만 로그인은 성공한 것 같습니다.")
                        return True
                else:
                    print("❌ 블로그에서 로그인 상태 확인 안됨")
                    return False
            else:
                print("❌ 메인 페이지에서 로그인 상태 확인 안됨")
                return False


            
        except Exception as e:
            print(f"❌ 로그인 중 오류 발생: {str(e)}")
            print("수동 세션 파일이 손상되었거나 만료되었을 수 있습니다.")
            print("manual_session_helper.py를 다시 실행하여 새로운 세션을 생성해주세요.")
            traceback.print_exc()
            return False
            
    def go_to_blog(self):
        """블로그 글쓰기 페이지로 이동"""
        try:
            blog_url = self.settings.get('blog_url', 'gm2hapkido')
            
            # 블로그 URL 형식 처리
            if blog_url.startswith('https://blog.naver.com/'):
                # 전체 URL이 있는 경우 ID만 추출
                blog_id = blog_url.replace('https://blog.naver.com/', '')
            elif blog_url.startswith('blog.naver.com/'):
                # blog.naver.com/으로 시작하는 경우 ID만 추출
                blog_id = blog_url.replace('blog.naver.com/', '')
            else:
                # ID만 있는 경우 그대로 사용
                blog_id = blog_url
            
            # 최종 URL 생성
            final_url = f'https://blog.naver.com/{blog_id}?Redirect=Write'
            print(f"블로그 이동 URL: {final_url}")
            
            # 안정적인 페이지 이동
            try:
                self.driver.get(final_url)
                
                # 페이지 로딩 완료 대기
                WebDriverWait(self.driver, 15).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                time.sleep(3)
                
                # 현재 URL 확인
                current_url = self.driver.current_url
                print(f"현재 페이지 URL: {current_url}")
                
                # 클립보드 권한 팝업 자동 처리
                self.handle_clipboard_popup()
                
                print("블로그 글쓰기 페이지 이동 성공!")
                return True
                
            except Exception as e:
                print(f"페이지 이동 중 오류: {e}")
                return False
        except Exception as e:
            print(f"블로그 페이지 이동 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return False
            
    def handle_esc_key(self):
        """ESC 키 처리를 위한 통합 메서드"""
        try:
            # ESC 키 완전 비활성화 - 불필요한 ESC 키 전송 제거
            return True
        except Exception as e:
            print(f"ESC 키 처리 중 오류: {str(e)}")
            return False

    def handle_clipboard_popup(self):
        """클립보드 권한 요청 팝업 자동 처리 - 강화된 버전"""
        try:
            print("🔍 클립보드 권한 팝업 확인 중...")
            
            # 더 포괄적인 JavaScript 기반 팝업 처리
            script = """
            function handleClipboardPopup() {
                // 1. 모든 가능한 팝업 요소 찾기
                const popupSelectors = [
                    'div[role="dialog"]',
                    'div.modal',
                    'div.popup',
                    'div[class*="dialog"]',
                    'div[class*="popup"]',
                    'div[class*="modal"]',
                    'div.se-popup',
                    'div.se-dialog',
                    'div[data-module="popup"]',
                    '[role="alertdialog"]',
                    '.alert',
                    '.notification'
                ];
                
                let popupFound = false;
                let popupElement = null;
                
                // 팝업 찾기
                for (const selector of popupSelectors) {
                    const elements = document.querySelectorAll(selector);
                    for (const element of elements) {
                        if (element.offsetParent !== null) { // 보이는 요소만
                            const text = element.innerText || element.textContent || '';
                            if (text.includes('클립보드') || text.includes('clipboard') || 
                                text.includes('권한') || text.includes('복사된') ||
                                text.includes('텍스트') || text.includes('이미지')) {
                                popupFound = true;
                                popupElement = element;
                                console.log('클립보드 팝업 발견:', selector);
                                break;
                            }
                        }
                    }
                    if (popupFound) break;
                }
                
                if (!popupFound) {
                    // 전체 페이지에서 클립보드 관련 텍스트 검색
                    const bodyText = document.body.innerText || document.body.textContent || '';
                    if (bodyText.includes('클립보드') || bodyText.includes('clipboard') || 
                        bodyText.includes('복사된 텍스트') || bodyText.includes('이미지를 확인')) {
                        console.log('페이지에서 클립보드 관련 텍스트 발견');
                        popupFound = true;
                    }
                }
                
                if (popupFound) {
                    // 2. 허용/확인 버튼 찾기 및 클릭
                    const buttonSelectors = [
                        'button',
                        'input[type="button"]',
                        'div[role="button"]',
                        'a[role="button"]',
                        '[onclick]'
                    ];
                    
                    for (const selector of buttonSelectors) {
                        const buttons = document.querySelectorAll(selector);
                        for (const btn of buttons) {
                            if (btn.offsetParent !== null) { // 보이는 버튼만
                                const text = btn.innerText || btn.textContent || btn.value || btn.title || '';
                                if (text.includes('허용') || text.includes('확인') || 
                                    text.includes('OK') || text.includes('Allow') || 
                                    text.includes('승인') || text.includes('동의') ||
                                    text === '확인' || text === '허용') {
                                    console.log('허용 버튼 클릭:', text);
                                    btn.click();
                                    return true;
                                }
                            }
                        }
                    }
                    
                    // 3. 특정 클래스/속성 기반 버튼 찾기
                    const specificSelectors = [
                        'button[data-action="allow"]',
                        'button[data-action="confirm"]',
                        'button.confirm',
                        'button.allow',
                        'button.primary',
                        'button.btn-primary',
                        'button.btn-confirm',
                        '.popup button:last-child',
                        '.modal button:last-child',
                        '.dialog button:last-child'
                    ];
                    
                    for (const selector of specificSelectors) {
                        const btn = document.querySelector(selector);
                        if (btn && btn.offsetParent !== null) {
                            console.log('특정 선택자로 버튼 클릭:', selector);
                            btn.click();
                            return true;
                        }
                    }
                    
                    // 4. Enter 키 시뮬레이션 (마지막 수단)
                    console.log('Enter 키 시뮬레이션 시도');
                    const event = new KeyboardEvent('keydown', {
                        key: 'Enter',
                        code: 'Enter',
                        keyCode: 13,
                        which: 13,
                        bubbles: true
                    });
                    document.dispatchEvent(event);
                    return true;
                }
                
                return false;
            }
            
            return handleClipboardPopup();
            """
            
            # 첫 번째 시도
            popup_handled = self.driver.execute_script(script)
            
            if popup_handled:
                print("✅ 클립보드 권한 팝업 처리 완료")
                time.sleep(2)
                return True
            
            # 브라우저 알림창 확인
            try:
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                print(f"브라우저 알림창 발견: {alert_text}")
                if "클립보드" in alert_text or "복사" in alert_text or "허용" in alert_text:
                    alert.accept()
                    print("✅ 브라우저 알림창 허용 처리 완료")
                    time.sleep(1)
                    return True
            except:
                pass
            
            print("ℹ️ 클립보드 권한 팝업 처리 완료")
            
            print("ℹ️ 클립보드 권한 팝업이 발견되지 않았습니다")
            return False
            
        except Exception as e:
            print(f"클립보드 팝업 처리 중 오류: {str(e)}")
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
        
        print(f"계산된 이미지 삽입 위치: {line_positions}")
        return line_positions

    def write_post(self, title, content, tags=None):
        """블로그 포스트 작성"""
        try:
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
                    actions.send_keys(line + Keys.ENTER + Keys.ENTER)
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

                        # 본문 텍스트 입력 완료
            print("본문 텍스트 입력 완료")
            time.sleep(1)
            
            # 본문 영역 최종 포커스
            try:
                body_areas = self.driver.find_elements(By.CSS_SELECTOR, 
                    "div.se-component.se-text.se-l-default")
                if body_areas:
                    self.driver.execute_script("arguments[0].click();", body_areas[-1])
                    print("✅ 본문 최종 포커스 완료")
                    time.sleep(0.5)
            except Exception as refocus_error:
                print(f"❌ 본문 최종 포커스 실패: {str(refocus_error)}")

            # 푸터 추가 직접 호출
            print("add_footer 메서드 호출 시작...")
            post_finisher = NaverBlogPostFinisher(self.driver, self.settings)
            
            # 현재 상태 확인 - 디버깅을 위한 정보 출력
            print("Driver 상태: " + ("유효함" if self.driver else "유효하지 않음"))
            print("Settings 상태:")
            print(f"- 도장 이름: {self.settings.get('dojang_name', '없음')}")
            print(f"- 주소: {self.settings.get('address', '없음')}")
            print(f"- 카카오 URL: {self.settings.get('kakao_url', '없음')}")
            
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
            
            # 마지막 문구에서 사용자 설정 슬로건 사용
            custom_slogan = self.settings.get('slogan', '바른 인성을 가진 인재를 기르는 한국체대 라이온 태권도 합기도')
            final_message = f"이상 {custom_slogan} 이었습니다"
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

    def check_page_status(self):
        """현재 페이지 상태 확인 (디버깅용)"""
        try:
            current_url = self.driver.current_url
            page_title = self.driver.title
            
            print(f"🔍 페이지 상태 확인:")
            print(f"  - 현재 URL: {current_url}")
            print(f"  - 페이지 제목: {page_title}")
            
            # iframe 상태 확인
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                print(f"  - iframe 개수: {len(iframes)}")
                
                # mainFrame iframe 확인
                main_frame = self.driver.find_elements(By.ID, "mainFrame")
                print(f"  - mainFrame 존재: {'예' if main_frame else '아니오'}")
                
            except Exception as iframe_error:
                print(f"  - iframe 확인 중 오류: {str(iframe_error)}")
            
            # 페이지 로딩 상태 확인
            ready_state = self.driver.execute_script("return document.readyState")
            print(f"  - 페이지 로딩 상태: {ready_state}")
            
            # 에러 메시지 확인
            error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".error, .alert, .warning")
            if error_elements:
                print(f"  - 페이지 에러 요소 발견: {len(error_elements)}개")
                for i, error in enumerate(error_elements[:3]):  # 최대 3개만 출력
                    try:
                        error_text = error.text.strip()
                        if error_text:
                            print(f"    {i+1}. {error_text[:100]}")
                    except:
                        pass
            else:
                print("  - 페이지 에러 요소: 없음")
                
            return True
            
        except Exception as e:
            print(f"❌ 페이지 상태 확인 중 오류: {str(e)}")
            return False