#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
개선된 네이버 블로그 자동화 시스템
- 완벽한 로그인 처리
- 안정적인 글 작성
- 자동 발행까지 완료
"""

import os
import sys
import time
import json
import random
import pickle
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from naver_blog_auto_image import NaverBlogImageInserter

class ImprovedNaverBlogAuto:
    def __init__(self, base_dir=None):
        self.driver = None
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.settings = self.load_settings()
        self.wait_time = 10  # 기본 대기 시간
        
    def load_settings(self):
        """설정 파일 로드"""
        settings_path = os.path.join(self.base_dir, 'config', 'user_settings.txt')
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 설정 파일 로드 실패: {e}")
            return {}
    
    def setup_driver(self):
        """Chrome 드라이버 설정 및 초기화"""
        try:
            print("🚀 Chrome 드라이버 초기화 시작...")
            
            chrome_options = Options()
            
            # 고유한 프로필 디렉토리 생성
            import uuid
            timestamp = str(int(time.time()))
            unique_id = str(uuid.uuid4())[:8]
            profile_path = os.path.join(self.base_dir, f"chrome_profile_{timestamp}_{unique_id}")
            os.makedirs(profile_path, exist_ok=True)
            
            # Chrome 옵션 설정
            chrome_options.add_argument(f"--user-data-dir={profile_path}")
            chrome_options.add_argument("--profile-directory=NaverBlog")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            
            # 자동화 감지 방지
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')
            
            # WebDriverManager를 사용한 자동 드라이버 관리
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service as ChromeService
            
            driver_path = ChromeDriverManager().install()
            service = ChromeService(executable_path=driver_path)
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(self.wait_time)
            
            # 자동화 감지 방지 스크립트 실행
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko', 'en-US', 'en']});
                window.chrome = {runtime: {}, loadTimes: function() {}, csi: function() {}, app: {}};
            """)
            
            print("✅ Chrome 드라이버 초기화 완료!")
            return True
            
        except Exception as e:
            print(f"❌ Chrome 드라이버 초기화 실패: {e}")
            traceback.print_exc()
            return False
    
    def login_naver(self):
        """네이버 로그인 - 3단계 전략"""
        try:
            if not self.setup_driver():
                return False
            
            print("🔐 네이버 로그인 시작...")
            
            # 1단계: 브라우저 프로필 기반 로그인 확인
            print("1️⃣ 브라우저 프로필 기반 로그인 확인...")
            self.driver.get('https://blog.naver.com')
            time.sleep(3)
            
            current_url = self.driver.current_url
            if "nid.naver.com" not in current_url and "login" not in current_url.lower():
                print("✅ 브라우저 프로필 기반 자동 로그인 성공!")
                return True
            
            # 2단계: 쿠키 기반 로그인 시도
            cookies_path = os.path.join(self.base_dir, 'naver_cookies.pkl')
            if os.path.exists(cookies_path):
                print("2️⃣ 쿠키 기반 로그인 시도...")
                try:
                    self.driver.get('https://naver.com')
                    time.sleep(2)
                    
                    with open(cookies_path, 'rb') as f:
                        cookies = pickle.load(f)
                    
                    for cookie in cookies:
                        try:
                            if 'domain' in cookie:
                                if not cookie['domain'].startswith('.'):
                                    cookie['domain'] = '.' + cookie['domain']
                            else:
                                cookie['domain'] = '.naver.com'
                            
                            if 'sameSite' in cookie:
                                del cookie['sameSite']
                                
                            self.driver.add_cookie(cookie)
                        except:
                            continue
                    
                    self.driver.refresh()
                    time.sleep(3)
                    self.driver.get('https://blog.naver.com')
                    time.sleep(3)
                    
                    current_url = self.driver.current_url
                    if "nid.naver.com" not in current_url and "login" not in current_url.lower():
                        print("✅ 쿠키 기반 자동 로그인 성공!")
                        return True
                        
                except Exception as e:
                    print(f"쿠키 로그인 실패: {e}")
            
            # 3단계: 자동 ID/PW 입력 로그인
            print("3️⃣ 자동 ID/PW 입력 로그인...")
            return self._auto_login_with_credentials()
            
        except Exception as e:
            print(f"❌ 로그인 중 오류: {e}")
            traceback.print_exc()
            return False
    
    def _auto_login_with_credentials(self):
        """자동 로그인 (ID/PW 입력)"""
        try:
            # 로그인 페이지로 이동
            self.driver.get('https://nid.naver.com/nidlogin.login')
            time.sleep(2)
            
            # 로그인 정보 확인
            naver_id = self.settings.get('naver_id')
            naver_pw = self.settings.get('naver_pw')
            
            if not naver_id or not naver_pw:
                print("❌ 네이버 로그인 정보가 설정되지 않았습니다.")
                return False
            
            print(f"🔑 로그인 시도: {naver_id}")
            
            # ID 입력
            if not self._input_field_with_retry("id", naver_id, "아이디"):
                return False
            
            # 비밀번호 입력
            if not self._input_field_with_retry("pw", naver_pw, "비밀번호"):
                return False
            
            # 로그인 버튼 클릭
            if not self._click_login_button():
                return False
            
            # 로그인 성공 확인
            time.sleep(3)
            current_url = self.driver.current_url
            
            if "nid.naver.com" not in current_url and "login" not in current_url.lower():
                print("✅ 자동 로그인 성공!")
                self._save_login_info()
                return True
            else:
                print("❌ 로그인 실패 - 추가 인증이 필요할 수 있습니다.")
                return False
                
        except Exception as e:
            print(f"❌ 자동 로그인 실패: {e}")
            return False
    
    def _input_field_with_retry(self, field_id, value, field_name):
        """입력 필드에 값 입력 (재시도 로직 포함)"""
        selectors = [
            (By.ID, field_id),
            (By.NAME, field_id),
            (By.CSS_SELECTOR, f"input[name='{field_id}']"),
            (By.CSS_SELECTOR, f"input[id='{field_id}']"),
            (By.XPATH, f"//input[@id='{field_id}']"),
            (By.XPATH, f"//input[@name='{field_id}']")
        ]
        
        for selector_type, selector_value in selectors:
            try:
                print(f"🔍 {field_name} 필드 찾는 중... ({selector_type}: {selector_value})")
                field = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((selector_type, selector_value))
                )
                
                # 필드 클릭 및 입력
                field.click()
                time.sleep(0.5)
                field.clear()
                time.sleep(0.5)
                field.send_keys(value)
                time.sleep(0.5)
                
                print(f"✅ {field_name} 입력 완료")
                return True
                
            except Exception as e:
                continue
        
        print(f"❌ {field_name} 필드를 찾을 수 없습니다.")
        return False
    
    def _click_login_button(self):
        """로그인 버튼 클릭"""
        selectors = [
            (By.ID, 'log.login'),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, ".btn_login"),
            (By.XPATH, "//input[@value='로그인']"),
            (By.XPATH, "//button[contains(text(), '로그인')]")
        ]
        
        for selector_type, selector_value in selectors:
            try:
                print(f"🔍 로그인 버튼 찾는 중... ({selector_type}: {selector_value})")
                button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((selector_type, selector_value))
                )
                
                button.click()
                print("✅ 로그인 버튼 클릭 완료")
                return True
                
            except Exception as e:
                continue
        
        print("❌ 로그인 버튼을 찾을 수 없습니다.")
        return False
    
    def _save_login_info(self):
        """로그인 정보 저장 (쿠키)"""
        try:
            cookies_path = os.path.join(self.base_dir, 'naver_cookies.pkl')
            with open(cookies_path, 'wb') as f:
                pickle.dump(self.driver.get_cookies(), f)
            print("✅ 로그인 정보 저장 완료")
        except Exception as e:
            print(f"⚠️ 로그인 정보 저장 실패: {e}")
    
    def go_to_blog_write(self):
        """블로그 글쓰기 페이지로 이동"""
        try:
            print("📝 블로그 글쓰기 페이지로 이동...")
            
            blog_url = self.settings.get('blog_url', 'gm2hapkido')
            if blog_url.startswith('https://blog.naver.com/'):
                blog_id = blog_url.replace('https://blog.naver.com/', '')
            else:
                blog_id = blog_url
            
            write_url = f"https://blog.naver.com/PostWriteForm.naver?blogId={blog_id}"
            self.driver.get(write_url)
            time.sleep(3)
            
            # 글쓰기 페이지 로드 확인
            if "PostWriteForm" in self.driver.current_url:
                print("✅ 블로그 글쓰기 페이지 이동 완료")
                return True
            else:
                print("❌ 블로그 글쓰기 페이지 이동 실패")
                return False
                
        except Exception as e:
            print(f"❌ 블로그 이동 중 오류: {e}")
            return False
    
    def calculate_image_positions(self, content):
        """이미지 삽입 위치를 계산하는 메서드 - 100자/200자 기준 문장 끝에 삽입"""
        content_lines = content.split('\n')
        sentence_end_markers = ['다.', '요.', '죠.', '.', '!', '?']
        line_positions = []
        char_count = 0
        is_first_image = True
        
        for i, line in enumerate(content_lines):
            line_text = line.strip()
            char_count += len(line)
            is_sentence_end = any(line_text.endswith(marker) for marker in sentence_end_markers)
            
            if is_first_image and char_count >= 100 and is_sentence_end:
                line_positions.append(i)
                char_count = 0
                is_first_image = False
            elif not is_first_image and char_count >= 200 and is_sentence_end:
                line_positions.append(i)
                char_count = 0
                
        return line_positions

    def write_post(self, title, content, tags=None, images_folder=None, videos_folder=None):
        """블로그 포스트 작성 및 발행"""
        try:
            print("✍️ 블로그 포스트 작성 시작...")
            
            # 이미지/동영상 인서터 설정
            if images_folder or videos_folder:
                self.image_inserter = NaverBlogImageInserter(self.driver, images_folder=images_folder)
            else:
                self.image_inserter = None
                
            # 제목 입력
            if not self._input_title(title):
                return False
            
            # 내용 입력 (텍스트 + 미디어 삽입)
            if not self._input_content(content):
                return False
            
            # 태그 입력
            if tags and not self._input_tags(tags):
                print("⚠️ 태그 입력 실패 (계속 진행)")
            
            # 발행
            if not self._publish_post():
                return False
            
            print("🎉 블로그 포스트 작성 및 발행 완료!")
            return True
            
        except Exception as e:
            print(f"❌ 포스트 작성 중 오류: {e}")
            traceback.print_exc()
            return False
            
    def _input_title(self, title):
        """제목 입력"""
        try:
            print("📝 제목 입력 중...")
            
            title_selectors = [
                (By.CSS_SELECTOR, "input[placeholder*='제목']"),
                (By.CSS_SELECTOR, "input.se-input"),
                (By.CSS_SELECTOR, "#title"),
                (By.NAME, "title"),
                (By.XPATH, "//input[@placeholder='제목을 입력해 주세요.']")
            ]
            
            for selector_type, selector_value in title_selectors:
                try:
                    title_field = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    
                    title_field.click()
                    title_field.clear()
                    title_field.send_keys(title)
                    
                    print(f"✅ 제목 입력 완료: {title}")
                    return True
                    
                except:
                    continue
            
            print("❌ 제목 입력 필드를 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            print(f"❌ 제목 입력 실패: {e}")
            return False

    def _input_content(self, content):
        """내용 입력 (이미지 및 동영상 삽입 포함)"""
        try:
            print("📝 내용 입력 중...")
            
            # 에디터 프레임으로 전환
            iframe_selectors = [
                "se-main-container iframe",
                ".se-main-container iframe",
                "iframe[title='Rich Text Area']",
                "iframe.se-iframe"
            ]
            
            iframe_found = False
            for selector in iframe_selectors:
                try:
                    iframe = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    self.driver.switch_to.frame(iframe)
                    iframe_found = True
                    print("✅ 에디터 프레임 전환 완료")
                    break
                except:
                    continue
            
            if not iframe_found:
                print("⚠️ 에디터 프레임을 찾을 수 없음 - 직접 입력 시도")
            
            # 본문 영역 클릭 포커스 확보
            try:
                body_area = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.se-component.se-text.se-l-default"))
                )
                body_area.click()
                time.sleep(0.5)
            except:
                print("본문 영역 클릭 실패 (무시하고 계속)")

            # 미디어 준비
            media_list = []
            if hasattr(self, 'image_inserter') and self.image_inserter:
                image_files, video_files = self.image_inserter.get_media_files()
                temp_all = [(f, "image") for f in image_files] + [(f, "video") for f in video_files]
                random.shuffle(temp_all)
                media_list = temp_all
                print(f"📊 삽입 대기 미디어: 총 {len(media_list)}개 (사진 {len(image_files)}, 영상 {len(video_files)})")

            # 위치 계산
            image_positions = self.calculate_image_positions(content)
            print(f"계산된 미디어 위치 정보: {image_positions}")

            def _exec_insert_text(text):
                self.driver.execute_script("""
                    var iframes = document.querySelectorAll('iframe[id^="input_buffer"]');
                    if (iframes.length > 0) {
                        var bufferDoc = iframes[0].contentDocument || iframes[0].contentWindow.document;
                        bufferDoc.body.focus();
                        bufferDoc.execCommand('insertText', false, arguments[0]);
                    }
                """, text)

            def _exec_enter_key(shift=False):
                self.driver.execute_script("""
                    var iframes = document.querySelectorAll('iframe[id^="input_buffer"]');
                    if (iframes.length > 0) {
                        var bufferDoc = iframes[0].contentDocument || iframes[0].contentWindow.document;
                        bufferDoc.body.focus();
                        var opts = {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, shiftKey: arguments[0]};
                        bufferDoc.body.dispatchEvent(new KeyboardEvent('keydown', opts));
                        bufferDoc.body.dispatchEvent(new KeyboardEvent('keypress', opts));
                        bufferDoc.body.dispatchEvent(new KeyboardEvent('keyup', opts));
                    }
                """, shift)

            def _refocus_input_buffer():
                try:
                    self.driver.switch_to.default_content()
                    if iframe_found:
                        for selector in iframe_selectors:
                            try:
                                frame = self.driver.find_element(By.CSS_SELECTOR, selector)
                                self.driver.switch_to.frame(frame)
                                break
                            except: pass
                    self.driver.execute_script("""
                        var iframes = document.querySelectorAll('iframe[id^="input_buffer"]');
                        if (iframes.length > 0) {
                            var bufferDoc = iframes[0].contentDocument || iframes[0].contentWindow.document;
                            bufferDoc.body.focus();
                        }
                    """)
                except Exception as e:
                    print(f"input_buffer 포커스 복구 실패: {e}")

            # 본문 내용 입력 (미디어 삽입과 병행)
            content_lines = content.split('\n')
            current_media_index = 0
            
            for i, line in enumerate(content_lines):
                current_line = i
                is_text_line = bool(line.strip())
                
                if is_text_line:
                    _exec_insert_text(line)
                _exec_enter_key(shift=True) # 줄바꿈

                time.sleep(0.08)

                # 미디어 삽입 시점 확인
                if (hasattr(self, 'image_inserter') and self.image_inserter and
                    current_line in image_positions and 
                    current_media_index < len(media_list)):
                    
                    try:
                        file_path, mtype = media_list[current_media_index]
                        print(f"줄 {current_line}: {mtype} 삽입 시도... ({current_media_index + 1}/{len(media_list)})")
                        
                        if mtype == "image":
                            self.image_inserter.insert_single_image(file_path)
                        else:
                            success = self.image_inserter.insert_single_video(file_path)
                            if not success:
                                # 실패 시 에스케이프
                                self.driver.switch_to.default_content()
                                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                                time.sleep(0.5)
                        
                        current_media_index += 1
                        _refocus_input_buffer()
                    except Exception as e:
                        print(f"미디어 삽입 오류: {e}")

            _refocus_input_buffer()
            time.sleep(0.5)

            # 남은 미디어 일괄 삽입
            if hasattr(self, 'image_inserter') and self.image_inserter:
                remaining_media = media_list[current_media_index:]
                for file_path, mtype in remaining_media:
                    try:
                        print(f"마지막 미디어 추가 삽입: {mtype}")
                        if mtype == "image":
                            self.image_inserter.insert_single_image(file_path)
                        else:
                            self.image_inserter.insert_single_video(file_path)
                        time.sleep(0.5)
                    except: pass
            
            print("✅ 내용 입력 완료")
            if iframe_found:
                self.driver.switch_to.default_content()
            return True
            
        except Exception as e:
            print(f"❌ 내용 입력 실패: {e}")
            if iframe_found:
                self.driver.switch_to.default_content()
            return False
    
    def _input_tags(self, tags):
        """태그 입력"""
        try:
            print("🏷️ 태그 입력 중...")
            
            tag_selectors = [
                (By.CSS_SELECTOR, "input[placeholder*='태그']"),
                (By.CSS_SELECTOR, ".tag_input"),
                (By.CSS_SELECTOR, "#tag"),
                (By.NAME, "tag")
            ]
            
            for selector_type, selector_value in tag_selectors:
                try:
                    tag_field = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    
                    for tag in tags:
                        tag_field.click()
                        tag_field.send_keys(tag.strip())
                        tag_field.send_keys(Keys.ENTER)
                        time.sleep(0.5)
                    
                    print(f"✅ 태그 입력 완료: {', '.join(tags)}")
                    return True
                    
                except:
                    continue
            
            print("❌ 태그 입력 필드를 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            print(f"❌ 태그 입력 실패: {e}")
            return False
    
    def _publish_post(self):
        """포스트 발행"""
        try:
            print("🚀 포스트 발행 중...")
            
            publish_selectors = [
                (By.CSS_SELECTOR, "button[data-nclicks-code='posting.write']"),
                (By.CSS_SELECTOR, ".publish_btn"),
                (By.CSS_SELECTOR, "button.se-publish-btn"),
                (By.XPATH, "//button[contains(text(), '발행')]"),
                (By.XPATH, "//button[contains(text(), '등록')]")
            ]
            
            for selector_type, selector_value in publish_selectors:
                try:
                    publish_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    
                    publish_btn.click()
                    print("✅ 발행 버튼 클릭 완료")
                    
                    # 발행 완료 대기
                    time.sleep(5)
                    
                    # 발행 완료 확인
                    current_url = self.driver.current_url
                    if "PostView" in current_url or "blog.naver.com" in current_url:
                        print("🎉 포스트 발행 완료!")
                        return True
                    
                except:
                    continue
            
            print("❌ 발행 버튼을 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            print(f"❌ 포스트 발행 실패: {e}")
            return False
    
    def close(self):
        """브라우저 종료"""
        try:
            if self.driver:
                self.driver.quit()
                print("✅ 브라우저 종료 완료")
        except Exception as e:
            print(f"⚠️ 브라우저 종료 중 오류: {e}")

# 사용 예시
if __name__ == "__main__":
    blog_auto = ImprovedNaverBlogAuto()
    
    try:
        # 로그인
        if blog_auto.login_naver():
            # 글쓰기 페이지로 이동
            if blog_auto.go_to_blog_write():
                # 포스트 작성 및 발행
                title = "테스트 제목"
                content = "테스트 내용입니다."
                tags = ["테스트", "블로그"]
                
                if blog_auto.write_post(title, content, tags, images_folder=None, videos_folder=None):
                    print("🎉 모든 작업 완료!")
                else:
                    print("❌ 포스트 작성 실패")
            else:
                print("❌ 글쓰기 페이지 이동 실패")
        else:
            print("❌ 로그인 실패")
    
    finally:
        blog_auto.close()