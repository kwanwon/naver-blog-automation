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
    
    # 앱 실행 디렉토리 기준 경로
    base_dir = os.path.abspath(".")
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
        if not fallback_folder:
            self.fallback_folder = 'default_images'
        else:
            self.fallback_folder = fallback_folder
            
        self.used_images = []
        self.sentence_end_markers = ['. ', '다. ', '요. ', '죠. ', '!', '?']
        self.insert_mode = insert_mode
        self.current_line = 0
        
        print(f"이미지 인서터 초기화: 주 폴더={self.images_folder}, 대체 폴더={self.fallback_folder}")

    def get_image_files(self):
        """이미지 폴더에서 사용 가능한 이미지 파일 목록을 가져옵니다."""
        # 1. 날짜 폴더 먼저 확인 (우선순위)
        primary_images = []
        if self.images_folder and os.path.exists(self.images_folder):
            print(f"날짜 폴더 확인: {self.images_folder}")
            try:
                for file in os.listdir(self.images_folder):
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        full_path = os.path.join(self.images_folder, file)
                        if full_path not in self.used_images:
                            primary_images.append(full_path)
            except Exception as e:
                print(f"날짜 폴더 읽기 오류: {str(e)}")
        
        # 2. 날짜 폴더에 이미지가 있으면 그것을 사용
        if primary_images:
            print(f"날짜 폴더에서 {len(primary_images)}개의 이미지를 찾았습니다.")
            return sorted(primary_images)
            
        # 3. 날짜 폴더에 이미지가 없는 경우 대체 폴더 사용
        print(f"날짜 폴더에 이미지가 없어 대체 폴더들을 확인합니다.")
        
        # 3.1 대체 폴더 목록 구성
        fallback_folders = []
        
        # 기본 fallback_folder 확인
        if os.path.exists(self.fallback_folder):
            fallback_folders.append(self.fallback_folder)
        
        # 빌드된 앱에서 resource_path 사용하여 대체 폴더 확인
        bundled_path = resource_path(self.fallback_folder)
        if os.path.exists(bundled_path) and bundled_path not in fallback_folders:
            fallback_folders.append(bundled_path)
        
        # 3.2 숫자가 붙은 대체 폴더 확인 (default_images_1, default_images_2, ...)
        for i in range(1, 12):  # 1부터 11까지
            folder_name = f"{self.fallback_folder}_{i}"
            
            # 일반 경로 확인
            if os.path.exists(folder_name):
                fallback_folders.append(folder_name)
            
            # 빌드된 앱에서 경로 확인
            bundled_path = resource_path(folder_name)
            if os.path.exists(bundled_path) and bundled_path not in fallback_folders:
                fallback_folders.append(bundled_path)
        
        print(f"확인할 대체 폴더들: {fallback_folders}")
        
        # 3.3 대체 폴더들에서 이미지 수집
        fallback_images = []
        for folder in fallback_folders:
            if not os.path.exists(folder):
                continue
                
            try:
                for file in os.listdir(folder):
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        full_path = os.path.join(folder, file)
                        if full_path not in self.used_images:
                            fallback_images.append(full_path)
            except Exception as e:
                print(f"폴더 {folder} 읽기 오류: {str(e)}")
        
        if fallback_images:
            print(f"대체 폴더들에서 총 {len(fallback_images)}개의 이미지를 찾았습니다.")
            return sorted(fallback_images)
                
        # 4. 어떤 폴더에도 이미지가 없는 경우
        print(f"이미지를 찾을 수 없습니다. 날짜 폴더: {self.images_folder}, 대체 폴더들: {fallback_folders}")
        return []

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
            config_paths = [
                'config/image_positions.json',  # 기본 경로
                resource_path('config/image_positions.json')  # 빌드된 앱 경로
            ]
            
            for config_path in config_paths:
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

    def insert_images_in_content(self, content_lines):
        """본문 내용에 이미지 삽입"""
        try:
            image_files = self.get_image_files()
            if not image_files:
                print("삽입할 이미지가 없습니다.")
                return False
                
            total_images = len(image_files)
            print(f"총 {total_images}장의 이미지를 삽입합니다.")
            
            # 저장된 위치 정보 로드
            image_positions = self.load_image_positions()
            
            if image_positions and image_positions['mode'] == self.insert_mode:
                print("저장된 이미지 위치 정보를 사용합니다.")
                positions = [p['line'] for p in image_positions['positions']]
            else:
                print("새로운 이미지 위치를 계산합니다.")
                positions = self.calculate_image_positions(content_lines)
            
            if not positions and self.insert_mode != "end":
                print("이미지 삽입 위치를 찾을 수 없습니다. 모든 이미지를 마지막에 삽입합니다.")
                self.insert_mode = "end"
            
            if self.insert_mode == "end":
                print("모든 이미지를 마지막에 삽입합니다.")
                # 마지막 줄로 이동
                self.move_cursor_to_end()
                for image in image_files:
                    if self.insert_single_image(image):
                        # 이미지 삽입 간 딜레이 제거 
                        pass
                return True
            
            # 이미지 파일과 위치 매칭
            image_insertions = list(zip(positions[:len(image_files)-1], image_files[:len(positions)]))
            
            # 위치별로 이미지 삽입
            for pos, image in image_insertions:
                print(f"이미지 삽입 - 위치: {pos}번째 줄")
                # 해당 위치로 커서 이동
                self.move_cursor_to_line(pos)
                if self.insert_single_image(image):
                    # 이미지 삽입 간 딜레이 제거
                    pass
            
            # 남은 이미지들은 마지막에 삽입
            remaining_images = image_files[len(positions):]
            if remaining_images:
                print(f"마지막에 {len(remaining_images)}장의 이미지를 삽입합니다.")
                self.move_cursor_to_end()
                for image in remaining_images:
                    if self.insert_single_image(image):
                        pass  # 딜레이 완전 제거
            
            return True
            
        except Exception as e:
            print(f"이미지 삽입 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return False

    def insert_single_image(self, image_path):
        """단일 이미지 삽입"""
        try:
            print(f"이미지 삽입 시도: {os.path.basename(image_path)}")
            
            # 파일 선택 버튼을 클릭하지 않고 직접 파일 입력 요소에 접근
            try:
                # 자바스크립트로 파일 입력 요소 확인
                js_script = """
                // 기존의 파일 입력 요소가 있는지 확인
                var fileInputs = document.querySelectorAll('input[type="file"]');
                if (fileInputs.length > 0) {
                    return true;
                }
                
                // 없으면 이미지 버튼 클릭하여 요소 생성
                var imgButtons = document.querySelectorAll('button.se-image-toolbar-button, button[title*="이미지"]');
                if (imgButtons.length > 0) {
                    imgButtons[0].click();
                    return true;
                }
                return false;
                """
                
                input_ready = self.driver.execute_script(js_script)
                if not input_ready:
                    print("파일 입력 요소를 찾거나 생성할 수 없습니다.")
                    return False
                
                time.sleep(0.05)  # 요소 생성 대기 시간 단축
                
                # 파일 입력 요소 직접 찾기 (생성된 요소 또는 기존 요소)
                file_input = None
                try:
                    # 여러 가능한 선택자 시도
                    selectors = [
                        'input[type="file"]',
                        'input.se-file-selector-button',
                        '.se-toolbar-item-image input[type="file"]'
                    ]
                    
                    for selector in selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            if elements:
                                file_input = elements[0]
                                print(f"파일 입력 요소 발견: {selector}")
                                break
                        except:
                            continue
                    
                    if not file_input:
                        # 자바스크립트로 모든 파일 입력 요소 찾기
                        js_script = """
                        return document.querySelectorAll('input[type="file"]').length;
                        """
                        input_count = self.driver.execute_script(js_script)
                        print(f"JS로 확인된 파일 입력 요소 수: {input_count}")
                        
                        if input_count > 0:
                            file_input = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')[0]
                            print("JS로 파일 입력 요소 발견")
                except Exception as e:
                    print(f"파일 입력 요소 검색 중 오류: {str(e)}")
                
                if not file_input:
                    print("파일 입력 요소를 찾을 수 없습니다. 이미지 버튼을 먼저 클릭합니다.")
                    file_button = self.find_file_button()
                    if file_button:
                        file_button.click()
                        time.sleep(0.05)
                        # 다시 파일 입력 요소 찾기
                        file_input = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
                        )
                
                if not file_input:
                    print("파일 입력 요소를 찾을 수 없습니다.")
                    return False
                
                # 절대 경로 확인
                abs_image_path = os.path.abspath(image_path)
                print(f"전송할 파일 경로: {abs_image_path}")
                
                # 자바스크립트로 파일 경로 설정 시도
                try:
                    js_set_file = f"""
                    arguments[0].style.display = 'block';
                    arguments[0].style.visibility = 'visible';
                    arguments[0].style.opacity = '1';
                    return true;
                    """
                    self.driver.execute_script(js_set_file, file_input)
                    # 불필요한 대기 시간 완전 제거
                except Exception as e:
                    print(f"JS로 파일 입력 요소 표시 중 오류: {str(e)}")
                
                # 파일 경로 전송
                file_input.clear()
                file_input.send_keys(abs_image_path)
                print("파일 경로 전송 완료")
                
                # 이미지 업로드 완료 대기
                WebDriverWait(self.driver, 1).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.se-image-container img[src*='http']"))
                )
                print("이미지 업로드 확인됨")
                
                # 이미지 레이아웃 선택 대기 및 처리
                try:
                    # 레이아웃 선택과 확인 버튼 클릭을 하나의 JavaScript 함수로 통합
                    js_complete_upload = """
                    function autoCompleteImageUpload() {
                        // 1. 레이아웃 목록 찾기
                        const layoutList = document.querySelector('ul.se-image-type-list');
                        if (!layoutList) {
                            console.log('레이아웃 목록을 찾을 수 없습니다.');
                            return false;
                        }
                        
                        // 2. 레이아웃 옵션 선택 (중앙 정렬 선호)
                        const layoutOptions = layoutList.querySelectorAll('label.se-image-type-label');
                        if (layoutOptions.length > 0) {
                            // 중앙 정렬 선택 (3번째 옵션이 있으면 사용)
                            const targetOption = layoutOptions.length >= 3 ? layoutOptions[2] : layoutOptions[0];
                            targetOption.click();
                            console.log('레이아웃 선택 완료');
                            
                            // 3. 즉시 확인 버튼 클릭
                            setTimeout(() => {
                                // 확인 버튼 찾기 시도
                                const confirmSelectors = [
                                    'button.se-image-dialog-btn-submit',
                                    'button.se-dialog-btn-submit',
                                    'button.se-btn-confirm'
                                ];
                                
                                let confirmClicked = false;
                                for (const selector of confirmSelectors) {
                                    const confirmBtn = document.querySelector(selector);
                                    if (confirmBtn) {
                                        confirmBtn.click();
                                        confirmClicked = true;
                                        console.log('확인 버튼 클릭 성공: ' + selector);
                                        break;
                                    }
                                }
                                
                                if (!confirmClicked) {
                                    // 모든 버튼 검색
                                    const buttons = document.querySelectorAll('button');
                                    for (const btn of buttons) {
                                        if ((btn.innerText && (btn.innerText.includes('확인') || btn.innerText.includes('적용'))) || 
                                            (btn.title && (btn.title.includes('확인') || btn.title.includes('적용'))) ||
                                            (btn.className && (btn.className.includes('submit') || btn.className.includes('confirm')))) {
                                            btn.click();
                                            confirmClicked = true;
                                            console.log('확인 버튼 발견 및 클릭!');
                                            break;
                                        }
                                    }
                                }
                                
                                return confirmClicked;
                            }, 100);
                            
                            return true;
                        } else {
                            console.log('레이아웃 옵션을 찾을 수 없습니다.');
                            return false;
                        }
                    }
                    
                    return autoCompleteImageUpload();
                    """
                    layout_result = self.driver.execute_script(js_complete_upload)
                    if layout_result:
                        print("JavaScript로 레이아웃 선택 및 확인 프로세스 통합 실행")
                    else:
                        print("JavaScript 레이아웃/확인 자동화 실패")
                    
                    # 성공 이벤트 후 대기 - 이미 업로드는 완료됨
                    # 대기 시간 최소화
                    time.sleep(0.05)
                    
                    # 이미지 업로드 창 무시 전략 - 이미지는 이미 삽입되었으므로 계속 진행
                    print("이미지는 이미 삽입되었습니다. 창이 닫히지 않아도 계속 진행합니다.")
                    
                    # 이미지 창 닫기 시도를 제거 - 진행에 방해되지 않으므로 불필요
                    print("이미지가 삽입되었으므로, 대화창 닫기 시도 없이 계속 진행합니다.")
                
                except Exception as e:
                    print(f"레이아웃 선택 중 오류: {str(e)}")
                    traceback.print_exc()
                    
                    # 레이아웃 선택 오류 발생 시에도 계속 진행
                    print("레이아웃 선택 중 오류가 발생했지만, 이미지는 이미 업로드되었으므로 계속 진행합니다.")
                
                # 이미지 사용 목록에 추가
                self.used_images.append(image_path)
                print(f"이미지 삽입 완료: {os.path.basename(image_path)}")
                # 작업 완료 후 대기 시간 대폭 감소
                time.sleep(0.05)
                return True
                
            except Exception as e:
                print(f"이미지 파일 업로드 중 오류: {str(e)}")
                traceback.print_exc()
                return False
                
        except Exception as e:
            print(f"이미지 삽입 중 오류: {str(e)}")
            traceback.print_exc()
            return False

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