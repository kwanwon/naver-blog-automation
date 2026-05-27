from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import os
import sys
import random
import traceback
import json
import datetime
from pathlib import Path
from folder_manager import ImageFolderManager
from utils.image_processor import process_image  # Import image processor
from utils.path_utils import get_app_data_dir  # AppData 경로를 위해 import
from os_file_picker import OSFilePicker  # 🆕 OS 파일 선택기 추가

# 리소스 경로 처리 함수
def resource_path(relative_path):
    """앱이 번들되었을 때와 그렇지 않을 때 모두 리소스 경로를 올바르게 가져옵니다."""
    try:
        # PyInstaller가 만든 임시 폴더에서 실행될 때
        base_path = sys._MEIPASS
    except Exception:
        # 일반적인 Python 인터프리터에서 실행될 때
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# 실행 경로 기준으로 날짜 폴더 경로 구성
def get_date_folder(date_str=None):
    """날짜 폴더 경로를 구성합니다. date_str이 없으면 오늘 날짜 사용"""
    if not date_str:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # 앱 실행 디렉토리 대신 안전한 AppData 하위 data 폴더 사용
    base_dir = os.path.join(get_app_data_dir(), "data")
    date_folder = os.path.join(base_dir, date_str)
    
    # 폴더가 없으면 생성 시도
    try:
        if not os.path.exists(date_folder):
            os.makedirs(date_folder, exist_ok=True)
            print(f"날짜 폴더 생성: {date_folder}")
        
        # images 서브폴더도 확인
        images_folder = os.path.join(date_folder, "images")
        if not os.path.exists(images_folder):
            os.makedirs(images_folder, exist_ok=True)
            print(f"이미지 폴더 생성: {images_folder}")
        
        return date_folder
    except Exception as e:
        print(f"날짜 폴더 생성 중 오류: {str(e)}")
        return None

class NaverBlogImageInserter:
    def __init__(self, driver, images_folder=None, insert_mode="random", fallback_folder=None):
        self.driver = driver
        
        # 이미지 폴더 설정
        if images_folder:
            self.images_folder = images_folder
        else:
            # 오늘 날짜 폴더의 images 하위 폴더 사용
            date_folder = get_date_folder()
            if date_folder:
                self.images_folder = os.path.join(date_folder, "images")
                print(f"기본 이미지 폴더 설정: {self.images_folder}")
            else:
                self.images_folder = None
        
        # 대체 이미지 폴더 설정
        # custom_images_folder가 넘어오면 해당 폴더만 사용 (폴더 순환 비활성화)
        self.fallback_folder = fallback_folder if fallback_folder else 'default_images'
        
        # fallback_folder가 상대 경로이고 존재하지 않으면 resource_path로 시도
        if not os.path.isabs(self.fallback_folder) and not os.path.exists(self.fallback_folder):
             res_path = resource_path(self.fallback_folder)
             if os.path.exists(res_path):
                 print(f"내장 리소스 이미지 폴더 사용: {res_path}")
                 self.fallback_folder = res_path
        
        self.use_single_folder = bool(fallback_folder)  # True면 폴더 순환을 건너뛰고 지정 폴더만 사용
            
        self.used_images = []
        self.sentence_end_markers = ['. ', '다. ', '요. ', '죠. ', '!', '?']
        self.insert_mode = insert_mode # 예: random, three_parts, five_parts, end
        self.media_position = "middle" # start, middle, end, random
        self.media_order = "image_first" # image_first, video_first, mixed
        self.current_line = 0
        
        # 🆕 OS 파일 선택기 초기화
        self.os_picker = OSFilePicker()
        
        # 🆕 비디오 메타데이터 초기화
        self.video_metadata = {
            'title': '네이버뉴스',
            'info': '네이버뉴스',
            'tags': '양양합기도, 등등'
        }
        
        # 폴더 관리자 초기화 (현재 파일 위치 기준)
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        self.folder_manager = ImageFolderManager(base_dir=current_file_dir)
        
        print(f"이미지 인서터 초기화: 주 폴더={self.images_folder}, 대체 폴더={self.fallback_folder}")
        
        # 임시 업로드 폴더 설정 (AppData 폴더 내에 생성)
        self.temp_upload_dir = os.path.join(get_app_data_dir(), "temp", "_temp_upload")
        os.makedirs(self.temp_upload_dir, exist_ok=True)
        self.cleanup_temp_images()  # 초기화 시 기존 임시 파일 정리

    def get_media_files(self):
        """폴더에서 이미지와 동영상 파일 목록을 가져와 분류합니다."""
        all_files = []
        
        # 1순위: 단일 폴더 지정 모드
        if self.use_single_folder:
            folder = self.fallback_folder
            if folder and os.path.exists(folder):
                valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov", ".avi", ".mkv", ".webm"}
                all_files = [
                    os.path.join(folder, f)
                    for f in os.listdir(folder)
                    if os.path.splitext(f)[1].lower() in valid_exts
                ]
            
            # 💡 [지능형 하이브리드 폴백] 만약 지정된 단일 폴더가 존재하지 않거나,
            # 폴더 안에 실제 이미지/영상 파일이 한 장도 없는 경우(빈 폴더)라면
            # 포스팅이 멈추거나 이미지가 누락되는 것을 원천 차단하기 위해
            # 폴더 순환 모드로 긴급 전환하여 이미지가 있는 폴더를 순차 탐색합니다.
            if not all_files:
                print(f"⚠️ [ImageInserter] 지정된 폴더('{folder}')에 이미지가 없거나 비어 있습니다. 이미지가 있는 폴더를 순차 탐색하기 위해 순환 모드로 긴급 전환합니다.")
                self.use_single_folder = False
                
        # 2순위: 기본 순환 폴더 모드 (또는 위에서 폴백된 경우)
        if not self.use_single_folder:
            current_folder = self.folder_manager.get_current_folder()
            if current_folder:
                all_files = self.folder_manager.get_images_from_folder(current_folder)
                self.folder_manager.get_next_folder()
                
            # 만약 선택된 순환 폴더에도 이미지가 없다면, 이미지가 있는 다른 순환 폴더를 찾기 위해 최대 10회까지 다음 폴더를 돌며 탐색
            attempts = 0
            while not all_files and attempts < 10:
                print(f"⚠️ [ImageInserter] 선택된 폴더('{current_folder}')가 비어 있습니다. 다음 폴더를 탐색합니다. (시도: {attempts+1}/10)")
                current_folder = self.folder_manager.get_current_folder()
                if current_folder:
                    all_files = self.folder_manager.get_images_from_folder(current_folder)
                    self.folder_manager.get_next_folder()
                attempts += 1
        
        images = [f for f in all_files if os.path.splitext(f)[1].lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}]
        videos = [f for f in all_files if os.path.splitext(f)[1].lower() in {".mp4", ".mov", ".avi", ".mkv", ".webm"}]
        
        return images, videos

    def get_image_files(self):
        """하위 호환성을 위해 유지"""
        images, _ = self.get_media_files()
        return images

    def find_file_button(self):
        """파일 선택 버튼을 찾는 메서드"""
        try:
            button = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.se-image-toolbar-button"))
            )
            return button
        except Exception:
            print("파일 선택 버튼을 찾을 수 없습니다.")
            return None

    def load_image_positions(self):
        """저장된 이미지 위치 정보 로드"""
        try:
            # 1. 사용자 데이터 폴더 (최우선)
            user_config_path = os.path.join(os.path.expanduser('~'), '.blog_automation', 'config', 'image_positions.json')
            
            # 2. 실행 위치 Config
            local_config_path = 'config/image_positions.json'
            
            # 3. 앱 내장 리소스 (마지막)
            bundled_config_path = resource_path('config/image_positions.json')
            
            check_paths = [user_config_path, local_config_path, bundled_config_path]
            
            for config_path in check_paths:
                if os.path.exists(config_path):
                    print(f"이미지 위치 설정 파일 발견: {config_path}")
                    with open(config_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
            
            print("이미지 위치 설정 파일을 찾을 수 없습니다.")
            return None
        except Exception as e:
            print(f"이미지 위치 정보 로드 중 오류: {str(e)}")
            traceback.print_exc()
            return None

    def insert_media_in_content(self, content_lines, media_position=None, media_order=None):
        """본문 내용에 이미지와 동영상 삽입 (통합 제어)"""
        try:
            if media_position: self.media_position = media_position
            if media_order: self.media_order = media_order

            image_files, video_files = self.get_media_files()
            if not image_files and not video_files:
                print("삽입할 미디어가 없습니다.")
                return False
                
            print(f"총 {len(image_files)}장의 이미지와 {len(video_files)}개의 영상을 삽입합니다.")
            
            # 미디어 믹싱 및 정렬 루틴
            media_list = []
            if self.media_order == "image_first":
                media_list = [(f, "image") for f in image_files] + [(f, "video") for f in video_files]
            elif self.media_order == "video_first":
                media_list = [(f, "video") for f in video_files] + [(f, "image") for f in image_files]
            elif self.media_order == "off":
                # 사용자의 요청: '사용 안함'은 영상만 제외하고 사진은 정상 삽입
                print("🚫 영상 삽입 제외 설정 (사진만 삽입)")
                media_list = [(f, "image") for f in image_files]
            else:  # mixed
                temp_all = [(f, "image") for f in image_files] + [(f, "video") for f in video_files]
                random.shuffle(temp_all)
                media_list = temp_all

            # 위치 계산
            if self.media_position == "start":
                self.move_cursor_to_line(0)
                for f, mtype in media_list:
                    self.insert_single_media(f, mtype)
            elif self.media_position == "end":
                self.move_cursor_to_end()
                for f, mtype in media_list:
                    self.insert_single_media(f, mtype)
            elif self.media_position == "middle" or self.media_position == "random":
                positions = self.calculate_image_positions(content_lines)
                if not positions:
                    self.move_cursor_to_end()
                    for f, mtype in media_list:
                        self.insert_single_media(f, mtype)
                else:
                    # 위치별로 분산 배치
                    pos_idx = 0
                    for f, mtype in media_list:
                        target_pos = positions[pos_idx % len(positions)]
                        self.move_cursor_to_line(target_pos)
                        self.insert_single_media(f, mtype)
                        pos_idx += 1
            
            return True
        except Exception as e:
            print(f"미디어 삽입 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return False

    def insert_images_in_content(self, content_lines):
        """기존 코드와의 호환성 유지"""
        return self.insert_media_in_content(content_lines)

    def insert_single_media(self, file_path, media_type):
        """단일 미디어 삽입 (타입 자동 판별 등 처리)"""
        if media_type == "image":
            return self.insert_single_image(file_path)
        elif media_type == "video":
            return self.insert_single_video(file_path)
        return False

    def handle_image_popups(self):
        """이미지 삽입 과정에서 발생하는 팝업 처리"""
        try:
            print("🔍 이미지 관련 팝업 확인 및 처리 중...")
            
            # 1. 브라우저 알림 창 처리
            try:
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                print(f"이미지 관련 알림 창 발견: {alert_text}")
                if "클립보드" in alert_text or "파일" in alert_text or "이미지" in alert_text or "허용" in alert_text:
                    alert.accept()  # 허용 클릭
                    print("✅ 이미지 관련 알림 창 허용 처리 완료")
                else:
                    alert.dismiss()  # 취소 클릭
                    print("✅ 이미지 관련 알림 창 취소 처리 완료")
                time.sleep(1)
            except:
                pass  # 알림 창이 없으면 무시
            
            # 2. 페이지 내 팝업 처리
            popup_handled = self.driver.execute_script("""
            function handleImagePopups() {
                let handled = false;
                
                // 파일 업로드 관련 팝업 버튼들 찾기
                const popupButtons = document.querySelectorAll('button');
                for (const btn of popupButtons) {
                    const text = btn.innerText.trim();
                    const isVisible = btn.offsetWidth > 0 && btn.offsetHeight > 0;
                    
                    if (isVisible && (text === '허용' || text === '확인' || text === 'Allow' || text === 'OK' || 
                                     text === '허용하기' || text === '파일 선택' || text === '업로드')) {
                        console.log('이미지 팝업 버튼 클릭:', text);
                        btn.click();
                        handled = true;
                        break;
                    }
                }
                
                // 파일 접근 권한 관련 처리
                if (navigator.permissions) {
                    navigator.permissions.query({name: 'clipboard-read'}).then(result => {
                        console.log('클립보드 읽기 권한 상태:', result.state);
                    }).catch(e => console.log('클립보드 권한 확인 오류:', e));
                }
                
                return handled;
            }
            
            return handleImagePopups();
            """)
            
            if popup_handled:
                print("✅ 이미지 관련 페이지 팝업 처리 완료")
                time.sleep(1)
            
            # 3. ESC 키로 불필요한 팝업 정리
            try:
                actions = ActionChains(self.driver)
                actions.send_keys(Keys.ESCAPE).perform()
                time.sleep(0.5)
                print("✅ ESC 키로 이미지 관련 팝업 정리 완료")
            except Exception as e:
                print(f"ESC 키 처리 중 오류: {str(e)}")
                
        except Exception as e:
            print(f"이미지 팝업 처리 중 오류: {str(e)}")

    def _intercept_file_input(self):
        """input[type=file]의 click()을 가로채서 Finder가 열리지 않게 설정"""
        self.driver.execute_script("""
            window.__fileInputIntercepted = null;
            var origClick = HTMLInputElement.prototype.click;
            window.__origInputClick = origClick;
            HTMLInputElement.prototype.click = function() {
                if (this.type === 'file') {
                    window.__fileInputIntercepted = this;
                    return;
                }
                return origClick.apply(this, arguments);
            };
        """)

    def _get_intercepted_input(self, max_wait=10):
        """가로챈 input[type=file] 요소를 가져오고 원래 click 복원"""
        file_input = None
        for _ in range(max_wait):
            file_input = self.driver.execute_script("return window.__fileInputIntercepted;")
            if file_input:
                break
            time.sleep(0.3)
        # 원래 click 복원
        self.driver.execute_script("""
            if (window.__origInputClick) {
                HTMLInputElement.prototype.click = window.__origInputClick;
            }
        """)
        return file_input

    def _send_file_to_input(self, file_input, file_path):
        """input[type=file]에 파일 경로를 send_keys로 전달"""
        self.driver.execute_script("""
            var el = arguments[0];
            el.style.display = 'block';
            el.style.visibility = 'visible';
            el.style.opacity = '1';
            el.style.width = '1px';
            el.style.height = '1px';
            el.style.position = 'absolute';
        """, file_input)
        file_input.send_keys(file_path)

    def insert_single_image(self, image_path):
        """단일 이미지 삽입 (Finder 열지 않음 - input click 가로채기 방식)"""
        try:
            abs_path = os.path.abspath(image_path)
            print(f"📸 이미지 삽입 시도: {os.path.basename(image_path)}")

            # 1. mainFrame 전환
            self.driver.switch_to.default_content()
            WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, "mainFrame")))
            self.driver.switch_to.frame("mainFrame")

            # 2. input[type=file] click 가로채기 설정
            self._intercept_file_input()

            # 3. 이미지 버튼 클릭 (input 생성되지만 Finder 안 열림)
            self.driver.execute_script("document.querySelector('button.se-image-toolbar-button')?.click();")
            time.sleep(0.5)

            # 4. 가로챈 input 가져오기
            file_input = self._get_intercepted_input()

            if not file_input:
                # 폴백: DOM에서 직접 검색
                print("⚠️ click 가로채기 실패, DOM에서 직접 검색...")
                inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
                if inputs:
                    file_input = inputs[-1]

            if file_input:
                self._send_file_to_input(file_input, abs_path)
                print(f"✅ 이미지 파일 전송 성공 (Finder 없이)")
                time.sleep(2)
                self.used_images.append(image_path)
                return True
            else:
                print("❌ input[type=file]을 찾을 수 없습니다")
                try:
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                except:
                    pass
                return False

        except Exception as e:
            print(f"이미지 삽입 중 오류: {e}")
            traceback.print_exc()
            return False

    def insert_single_video(self, video_path):
        """단일 동영상 삽입 (Finder 열지 않음 - input click 가로채기 방식)"""
        try:
            abs_path = os.path.abspath(video_path)
            print(f"🎬 동영상 삽입 시도: {os.path.basename(video_path)}")

            # 1. 동영상 툴바 버튼 클릭 (mainFrame 내부)
            try:
                self.driver.switch_to.default_content()
                WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, "mainFrame")))
                self.driver.switch_to.frame("mainFrame")
                self.driver.execute_script("document.querySelector('button.se-video-toolbar-button')?.click();")
                time.sleep(1.5)
            except Exception as e:
                print(f"동영상 버튼 클릭 실패: {e}")
                return False

            # 2. 동영상 팝업은 default_content에 열림
            self.driver.switch_to.default_content()

            # 3. input[type=file] click 가로채기 설정
            self._intercept_file_input()

            # 4. '동영상 추가' 버튼 클릭 (Finder 대신 input이 가로채어짐)
            self.driver.execute_script("""
                var selectors = ['.se-video-dialog-btn-upload', '.se-video-dialog-content-upload-button', '.se-popup-button-upload'];
                for (var i = 0; i < selectors.length; i++) {
                    var btn = document.querySelector(selectors[i]);
                    if (btn) { btn.click(); return true; }
                }
                var buttons = Array.from(document.querySelectorAll('button')).filter(function(b) {
                    return b.innerText.indexOf('추가') >= 0 || b.innerText.indexOf('파일') >= 0;
                });
                if (buttons.length > 0) { buttons[0].click(); return true; }
                return false;
            """)
            time.sleep(1)

            # 5. 가로챈 input 가져오기
            file_input = self._get_intercepted_input()

            if not file_input:
                inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
                if inputs:
                    file_input = inputs[-1]

            if file_input:
                self._send_file_to_input(file_input, abs_path)
                print(f"✅ 동영상 파일 전송 성공 (Finder 없이)")
                time.sleep(3)

                # 6. 메타데이터 입력
                print("📝 동영상 제목 및 태그 입력 중...")
                self.driver.execute_script("""
                    var titleInput = document.querySelector('input[class*="title"], input[placeholder*="제목"]');
                    var descInput = document.querySelector('textarea[class*="description"], textarea[placeholder*="설명"]');
                    var tagInput = document.querySelector('input[class*="tag"], input[placeholder*="태그"]');
                    if (titleInput) { titleInput.value = arguments[0]; titleInput.dispatchEvent(new Event('input', {bubbles:true})); }
                    if (descInput) { descInput.value = arguments[1]; descInput.dispatchEvent(new Event('input', {bubbles:true})); }
                    if (tagInput) { tagInput.value = arguments[2]; tagInput.dispatchEvent(new Event('input', {bubbles:true})); }
                """, self.video_metadata.get('title', ''), self.video_metadata.get('info', ''), self.video_metadata.get('tags', ''))
                time.sleep(1)

                # 7. 완료 버튼 클릭
                self.driver.execute_script("""
                    var selectors = ['.se-video-dialog-btn-submit', '.se-popup-button-confirm', 'button[class*="submit"]'];
                    for (var i = 0; i < selectors.length; i++) {
                        var btn = document.querySelector(selectors[i]);
                        if (btn && !btn.disabled) { btn.click(); return true; }
                    }
                    var buttons = Array.from(document.querySelectorAll('button')).filter(function(b) {
                        return b.innerText.indexOf('완료') >= 0 || b.innerText.indexOf('올리기') >= 0;
                    });
                    if (buttons.length > 0) { buttons[0].click(); return true; }
                    return false;
                """)
                print("✅ 동영상 업로드 완료")
                self.used_images.append(video_path)
                return True
            else:
                print("❌ 동영상 input[type=file]을 찾을 수 없습니다")
                return False
            
        finally:
            # 🎯 중요: 실패하든 성공하든 무조건 팝업을 닫고 mainFrame으로 복귀해야 함!
            try:
                print("🧹 남아있는 팝업 정리 시도...")
                self.driver.switch_to.default_content()
                
                # 강제 닫기 버튼 클릭
                self.driver.execute_script("""
                    document.querySelectorAll('.se-popup-button-cancel, .se-popup-close-button, button[class*="close"], button[title*="닫기"], .se-video-dialog-btn-close').forEach(btn => {
                        try { btn.click(); } catch(e) {}
                    });
                """)
                
                # ESC 키 입력
                for _ in range(3):
                    self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    time.sleep(0.2)
                    
                # mainFrame으로 복귀
                frame = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.ID, "mainFrame"))
                )
                self.driver.switch_to.frame(frame)
                print("✅ 팝업 정리 완료 및 mainFrame 복귀 성공")
            except Exception as e:
                print(f"팝업 정리 및 프레임 복귀 중 오류 (무시됨): {str(e)}")

    def _simulate_video_drop(self, video_path):
        """드래그 앤 드롭 시뮬레이션을 통한 동영상 삽입"""
        try:
            print("🖱️ 드래그 앤 드롭 시뮬레이션 시작...")
            
            target = None
            
            # 1. 다이얼로그 안의 드롭존을 먼저 찾습니다 (default_content에 있음)
            dropzone_selectors = [".se-video-dialog-dropzone", ".se-video-dialog-content", ".se-video-dialog", ".se-popup"]
            for sel in dropzone_selectors:
                try:
                    el = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if el.is_displayed():
                        target = el
                        print(f"✅ 다이얼로그 안의 드롭존( {sel} ) 발견")
                        break
                except:
                    continue
            
            # 2. 다이얼로그 드롭존이 없으면 에디터 본문(mainFrame 안)에 직접 드롭 시도!
            if not target:
                print("⚠️ 팝업 드롭존을 찾지 못했습니다. 에디터 본문에 직접 드롭을 시도합니다.")
                try:
                    self.driver.switch_to.frame("mainFrame")
                    target = self.driver.find_element(By.CSS_SELECTOR, ".se-main-container, body")
                    print("✅ 에디터 본문 드롭존 발견")
                except:
                    print("❌ 어떤 드롭존도 찾을 수 없습니다.")
                    return False

            js_drop_script = """
                var target = arguments[0];
                var offsetX = 0;
                var offsetY = 0;
                var document = target.ownerDocument || document;
                var window = document.defaultView || window;

                var input = document.createElement('input');
                input.type = 'file';
                input.style.display = 'none';
                input.onchange = function () {
                    var rect = target.getBoundingClientRect();
                    var x = rect.left + (offsetX || (rect.width >> 1));
                    var y = rect.top + (offsetY || (rect.height >> 1));
                    var dataTransfer = { files: this.files };

                    ['dragenter', 'dragover', 'drop'].forEach(function (name) {
                        var evt = document.createEvent('MouseEvent');
                        evt.initMouseEvent(name, true, true, window, 0, 0, 0, x, y, false, false, false, false, 0, null);
                        evt.dataTransfer = dataTransfer;
                        target.dispatchEvent(evt);
                    });

                    setTimeout(function () { document.body.removeChild(input); }, 20);
                };
                document.body.appendChild(input);
                return input;
            """
            fake_input = self.driver.execute_script(js_drop_script, target)
            fake_input.send_keys(video_path)
            print("✅ 드롭 시뮬레이션 이벤트 발송 완료")
            
            # 다시 default_content로 돌아와 업로드 화면 대기
            self.driver.switch_to.default_content()
            time.sleep(3)
            
            self.driver.execute_script("""
                const btn = document.querySelector('.se-video-dialog-btn-submit, .se-popup-button-confirm');
                if (btn) btn.click();
            """)
            return True
        except Exception as e:
            print(f"❌ 드롭 시뮬레이션 실패: {e}")
            return False
            
    def cleanup_temp_images(self):
        """임시 업로드 폴더의 파일들을 정리합니다."""
        try:
            if not os.path.exists(self.temp_upload_dir):
                return
                
            print(f"🧹 임시 이미지 폴더 정리 중: {self.temp_upload_dir}")
            for filename in os.listdir(self.temp_upload_dir):
                file_path = os.path.join(self.temp_upload_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"임시 파일 삭제 실패 ({filename}): {e}")
            print("✅ 임시 이미지 정리 완료")
        except Exception as e:
            print(f"임시 폴더 정리 중 오류: {e}")

    def calculate_image_positions(self, content_lines):
        """본문 내용을 분석하여 이미지 삽입 위치 계산"""
        total_lines = len(content_lines)
        sentence_ends = []
        
        # 문장 끝 위치 찾기
        for i, line in enumerate(content_lines):
            if any(line.strip().endswith(marker) for marker in self.sentence_end_markers):
                sentence_ends.append(i)
        
        if not sentence_ends:
            print("문장 끝 위치를 찾을 수 없습니다.")
            return []
            
        print(f"삽입 모드: {self.insert_mode}")
        image_positions = []
        
        # 선택된 모드에 따라 이미지 위치 계산
        if self.insert_mode == "random":
            # 3~5등분 중 랜덤 선택
            num_sections = random.randint(3, 5)
            print(f"본문을 {num_sections}등분하여 이미지 삽입")
            
            for section in range(1, num_sections):
                target_line = (total_lines * section) // num_sections
                closest_end = min(sentence_ends, key=lambda x: abs(x - target_line))
                if closest_end not in image_positions:
                    image_positions.append(closest_end)
                    
        elif self.insert_mode == "three_parts":
            print("본문을 3등분하여 이미지 삽입")
            # 3등분 위치에 삽입
            for section in range(1, 3):  # 1, 2 (2개 지점)
                target_line = (total_lines * section) // 3
                closest_end = min(sentence_ends, key=lambda x: abs(x - target_line))
                if closest_end not in image_positions:
                    image_positions.append(closest_end)
                    
        elif self.insert_mode == "five_parts":
            print("본문을 5등분하여 이미지 삽입")
            # 5등분 위치에 삽입
            for section in range(1, 5):  # 1, 2, 3, 4 (4개 지점)
                target_line = (total_lines * section) // 5
                closest_end = min(sentence_ends, key=lambda x: abs(x - target_line))
                if closest_end not in image_positions:
                    image_positions.append(closest_end)
                    print(f"이미지 삽입 위치 추가: {closest_end}번째 줄")
        
        elif self.insert_mode == "end":
            print("모든 이미지를 마지막에 삽입")
            return []  # 마지막 모드는 위치 계산 불필요
        
        image_positions = sorted(image_positions)
        print(f"계산된 이미지 삽입 위치: {image_positions}")
        return image_positions

    def move_cursor_to_line(self, line_number):
        """특정 줄로 커서 이동"""
        try:
            # 에디터 영역 찾기
            editor = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.se-component-content"))
            )
            
            # 현재 줄에서 목표 줄까지 이동
            actions = ActionChains(self.driver)
            current_line = self.current_line
            
            if line_number > current_line:
                # 아래로 이동
                for _ in range(line_number - current_line):
                    actions.key_down(Keys.DOWN).perform()
                    # 커서 이동 속도 개선을 위해 대기 시간 제거
            else:
                # 위로 이동
                for _ in range(current_line - line_number):
                    actions.key_down(Keys.UP).perform()
                    # 커서 이동 속도 개선을 위해 대기 시간 제거
            
            self.current_line = line_number
            print(f"커서를 {line_number}번째 줄로 이동했습니다.")
            return True
            
        except Exception as e:
            print(f"커서 이동 중 오류 발생: {str(e)}")
            return False

    def move_cursor_to_end(self):
        """커서를 문서 끝으로 이동"""
        try:
            actions = ActionChains(self.driver)
            actions.key_down(Keys.CONTROL).send_keys(Keys.END).key_up(Keys.CONTROL).perform()
            # 문서 끝으로 이동 후 대기 시간 제거
            print("커서를 문서 끝으로 이동했습니다.")
            return True
        except Exception as e:
            print(f"커서를 문서 끝으로 이동하는 중 오류 발생: {str(e)}")
            return False