import time
import os
import re
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

class NaverBandAutomation:
    def __init__(self, driver):
        self.driver = driver

    def _check_high_quality_option(self):
        """동영상 고화질 첨부 옵션 체크"""
        print("🔍 고화질 첨부 옵션 확인 중...")
        try:
            target = None
            # 방법 1: data-viewname 기반 (관장님 스샷 근거)
            quality_views = self.driver.find_elements(By.CSS_SELECTOR, "div[data-viewname='DPhotoUploadVideoQualityView']")
            if quality_views and quality_views[0].is_displayed():
                target = quality_views[0]
                print("  📍 고화질 옵션 뷰 발견 (data-viewname)")
            
            # 방법 2: 텍스트 기반 label
            if not target:
                labels = self.driver.find_elements(By.XPATH, "//label[contains(., '고화질 첨부하기')]")
                if labels and labels[0].is_displayed():
                    target = labels[0]
                    print("  📍 고화질 옵션 레이블 발견 (텍스트)")

            if target:
                # 내부 checkbox 상태 확인
                try:
                    checkbox = target.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                    is_checked = checkbox.is_selected() or self.driver.execute_script("return arguments[0].checked;", checkbox)
                    
                    if not is_checked:
                        print("  ✅ 고화질 첨부 옵션 켜기 (클릭)")
                        try:
                            # 1. 네이티브 클릭 시도
                            target.click()
                        except:
                            # 2. 액션 체인 시도
                            from selenium.webdriver.common.action_chains import ActionChains
                            ActionChains(self.driver).move_to_element(target).click().perform()
                        
                        time.sleep(1)
                        # 재확인
                        is_now_checked = self.driver.execute_script("return arguments[0].checked;", checkbox)
                        if not is_now_checked:
                            # 3. 마지막 수단: JS 강제 체크
                            print("  🔄 JS로 강제 체크 시도")
                            self.driver.execute_script("arguments[0].checked = true; arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", checkbox)
                        return True
                    else:
                        print("  ℹ️ 고화질 옵션 이미 활성화됨")
                        return True
                except Exception as e:
                    print(f"  ⚠️ 체크박스 제어 실패: {e}")
            else:
                print("  ⚠️ 고화질 옵션 요소를 찾을 수 없습니다.")
        except Exception as e:
            print(f"  ⚠️ 고화질 설정 중 오류: {e}")
        return False

    def _wait_for_attach_button_ready(self, timeout=60):
        """첨부하기 버튼이 활성화될 때까지 대기"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                attach_selectors = [
                    "button.uButton.-confirm._submitBtn", 
                    "button[class*='-confirm'][class*='_submitBtn']",
                    "button.uButton._submitBtn", 
                    "button._submitBtn", 
                    "//button[contains(text(), '첨부하기')]"
                ]
                for sel in attach_selectors:
                    try:
                        if sel.startswith("//"):
                            btn = self.driver.find_element(By.XPATH, sel)
                        else:
                            btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                        
                        if btn.is_displayed() and btn.is_enabled():
                            return btn
                    except: continue
            except: pass
            time.sleep(1)
        return None
    
    def _wait_for_media_count(self, expected_count: int, timeout: int = 60):
        """팝업 내 업로드된 미디어 개수가 예상치에 도달할 때까지 대기"""
        print(f"⏳ 미디어 개수 확인 중... (목표: {expected_count}개)")
        start_time = time.time()
        
        # 밴드 업로드 팝업 내 개별 미디어 아이템 셀렉터
        item_selectors = [
            "li.photoItem",
            "li[data-viewname='DPhotoUploadPhotoItemView']",
            "li[data-viewname='DPhotoUploadVideoItemView']",
            "div.photo_area"
        ]
        
        while time.time() - start_time < timeout:
            for selector in item_selectors:
                try:
                    items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    current_count = len([i for i in items if i.is_displayed()])
                    if current_count >= expected_count:
                        print(f"  ✅ 미디어 로드 완료: {current_count}/{expected_count}")
                        return True
                    if current_count > 0:
                        print(f"  📊 미디어 로딩 중... ({current_count}/{expected_count})", end='\r')
                except:
                    continue
            time.sleep(1.5)
        
        print(f"  ⚠️ 미디어 로드 타임아웃 ({timeout}초). 현재 발견된 개수로 진행합니다.")
        return False

    def _click_attach_button(self):
        """첨부하기 버튼 클릭 헬퍼"""
        attach_btn_selectors = [
            "button.uButton.-confirm._submitBtn",  # 스크린샷 기반
            "button._submitBtn",
            "button.uButton.-confirm",
            "//button[contains(text(), '첨부하기')]",
            "//button[contains(text(), '확인')]"
        ]
        
        for selector in attach_btn_selectors:
            try:
                if selector.startswith("//"):
                    attach_btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                else:
                    attach_btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                
                if attach_btn and attach_btn.is_displayed():
                    try:
                        attach_btn.click() # Native click 최우선
                    except:
                        from selenium.webdriver.common.action_chains import ActionChains
                        ActionChains(self.driver).move_to_element(attach_btn).click().perform()
                    
                    print(f"✅ 첨부하기 버튼 클릭 완료 ({selector})")
                    time.sleep(1)
                    return True
            except:
                continue
        
        print("⚠️ 첨부하기 버튼을 찾지 못함")
        return False
    
    def _wait_for_upload_complete(self, timeout: int = 120):
        """
        업로드가 완료될 때까지 대기합니다.
        실제 진행 상황(X/Y)을 감지하여 정확하게 완료를 판단합니다.
        
        Args:
            timeout: 최대 대기 시간 (초)
        
        Returns:
            업로드 완료 여부
        """
        print("⏳ 업로드 완료 대기 중...")
        
        start_time = time.time()
        last_progress = ""
        
        # 업로드 팝업 셀렉터 (사진/동영상 공통)
        popup_selector = "section.lyWrap.layer_wrap"
        progress_selector = ".progress.skin4 .fileBy"  # "25/30" 형식
        
        while time.time() - start_time < timeout:
            try:
                # 1. 업로드 팝업이 있는지 확인
                popups = self.driver.find_elements(By.CSS_SELECTOR, popup_selector)
                popup_visible = any(p.is_displayed() for p in popups if p)
                
                if not popup_visible:
                    # 팝업이 사라졌으면 업로드 완료
                    print("  ✅ 업로드 팝업 사라짐 - 완료")
                    time.sleep(2)  # 안정화 대기
                    return True
                
                # 2. 진행 상황(X/Y) 확인
                try:
                    progress_elements = self.driver.find_elements(By.CSS_SELECTOR, progress_selector)
                    for prog in progress_elements:
                        if prog and prog.is_displayed():
                            progress_text = prog.text.strip()
                            
                            # "25/30" 형식 파싱
                            if "/" in progress_text:
                                parts = progress_text.split("/")
                                if len(parts) == 2:
                                    try:
                                        current = int(parts[0].strip())
                                        total = int(parts[1].strip())
                                        
                                        # 진행 상황 출력 (변경 시에만)
                                        if progress_text != last_progress:
                                            print(f"  📊 업로드 진행: {current}/{total}")
                                            last_progress = progress_text
                                        
                                        # 완료 확인 (X >= Y 이면 팝업이 곧 사라질 것)
                                        if current >= total:
                                            time.sleep(2)  # 팝업 닫힘 대기
                                            return True
                                    except ValueError:
                                        pass
                            break
                except:
                    pass
                
            except Exception as e:
                # 요소 찾기 실패 시 계속 대기
                pass
            
            time.sleep(1)  # 1초 간격으로 확인
        
        print(f"  ⚠️ 업로드 타임아웃 ({timeout}초)")
        return False
    
    def _wait_for_submit_button_ready(self, timeout: int = 60):
        """
        게시 버튼이 활성화(클릭 가능)될 때까지 대기
        
        Returns:
            게시 버튼 element 또는 None
        """
        print("🔍 게시 버튼 활성화 대기 중...")
        
        submit_selectors = [
            "button._btnSubmitPost:not([disabled])",
            "button.uButton.-confirm:not([disabled])",
            "button._btnPost:not([disabled])",
            "button.uButton.-sizeM._btnSubmitPost.-confirm:not([disabled])"
        ]
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            for selector in submit_selectors:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if btn and btn.is_displayed() and btn.is_enabled():
                        print("✅ 게시 버튼 활성화됨")
                        return btn
                except:
                    continue
            
            time.sleep(1)
        
        print(f"⚠️ 게시 버튼 활성화 대기 타임아웃 ({timeout}초)")
        return None
        
    def post_to_band(self, band_url: str, content: str, image_paths: list = None, reservation_time: str = None):
        """
        네이버 밴드에 글을 게시합니다.
        
        Args:
            band_url: 게시할 밴드 URL
            content: 게시글 내용
            image_paths: 업로드할 이미지 경로 리스트 (옵션)
            reservation_time: 예약 시간 (문자열, "HH:MM" 24시간 형식). None이면 즉시 발행.
        """
        try:
            # [비정상 본문 체크] 쉼표 나열 등은 공백으로 취급
            if content and (re.match(r'^[\s,./]+$', content) or len(content.strip()) < 5):
                print(f"⚠️ [Stability] 비정상 본문 감지 ({len(content)}자). 기본 문구로 대체합니다.")
                content = "수련 현장의 생생한 소식을 전해드립니다. 우리 아이들의 성장을 응원해주세요! 🙏"

            print(f"🌐 밴드로 이동 중: {band_url}")
            self.driver.get(band_url)
            time.sleep(3)
            
            # 1. 전용 글쓰기 레이어(모달) 확인 및 열기
            try:
                # 2번 스샷과 같은 전용 '글쓰기 레이어'가 있는지 확인
                modal_editor = self.driver.find_elements(By.CSS_SELECTOR, "section.lyWrap.layer_wrap, div.postWriteArea")
                is_modal_open = any(m.is_displayed() for m in modal_editor)
                
                if is_modal_open:
                    print("  ✅ 전용 글쓰기 창이 이미 활성화되어 있습니다.")
                else:
                    print("  📝 전용 글쓰기 창을 엽니다 (초록색 버튼 클릭)...")
                    # 왼쪽 사이드바의 초록색 '글쓰기' 버튼 또는 메인 상단 버튼 클릭
                    write_btn_selectors = [
                        "button.roundButton.-full._btnWritePost", # 왼쪽 초록색 버튼
                        "button._btnOpenWriteLayer",
                        "div.postWriteMain button" # 메인 상단 버튼
                    ]
                    
                    clicked = False
                    for sel in write_btn_selectors:
                        try:
                            btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                            if btn and btn.is_displayed():
                                self.driver.execute_script("arguments[0].click();", btn)
                                clicked = True
                                break
                        except: continue
                    
                    if not clicked:
                        # 최후의 수단: 메인 피드 상단의 '새로운 소식을 남겨보세요' 클릭
                        feed_input = self.driver.find_element(By.CSS_SELECTOR, "div.postWriteMain, ._btnOpenWriteLayer")
                        feed_input.click()
                    
                    time.sleep(2)
            except Exception as e:
                print(f"⚠️ 글쓰기 창 열기 시도 중 오류: {e}")
            # 2. 내용 입력 (다중 폴백)
            print("⌨️ 내용 입력 중 (다중 폴백)...")
            editor = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'], textarea._postWriteInput"))
            )
            editor.click()
            time.sleep(0.5)
            
            # 방법 1: 클립보드 헬퍼 사용 시도
            insert_success = False
            try:
                from utils.clipboard_helper import insert_text_to_editor
                insert_success = insert_text_to_editor(self.driver, editor, content, platform="band")
                if insert_success:
                    print("✅ 내용 입력 완료 (클립보드 헬퍼)")
            except ImportError as ie:
                print(f"⚠️ 클립보드 헬퍼 모듈 import 실패: {ie}")
            except Exception as e:
                print(f"⚠️ 클립보드 헬퍼 실행 실패: {e}")
            
            # 방법 2: macOS 네이티브 pbcopy + 붙여넣기
            if not insert_success:
                print("🔄 [Fallback] macOS pbcopy 시도...")
                try:
                    import subprocess
                    import sys
                    if sys.platform == 'darwin':
                        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                        process.communicate(content.encode('utf-8'))
                        if process.returncode == 0:
                            time.sleep(0.3)
                            ActionChains(self.driver).key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
                            time.sleep(1)
                            # 검증
                            editor_text = editor.text.strip() if editor.text else ""
                            if len(editor_text) >= len(content) * 0.3:
                                insert_success = True
                                print(f"✅ pbcopy 성공 ({len(editor_text)}자)")
                except Exception as pb_err:
                    print(f"⚠️ pbcopy 실패: {pb_err}")
            
            # 방법 3: JavaScript 직접 주입
            if not insert_success:
                print("🔄 [Fallback] JS 직접 주입...")
                try:
                    self.driver.execute_script("""
                        arguments[0].innerText = arguments[1];
                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                        arguments[0].dispatchEvent(new KeyboardEvent('keydown', { bubbles: true }));
                        arguments[0].dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
                    """, editor, content)
                    time.sleep(0.5)
                    editor_text = editor.text.strip() if editor.text else ""
                    if len(editor_text) >= len(content) * 0.2:
                        insert_success = True
                        print(f"✅ JS 주입 성공 ({len(editor_text)}자)")
                except Exception as js_err:
                    print(f"⚠️ JS 주입 실패: {js_err}")
            
            # 방법 4: send_keys 직접 입력 (최후의 수단)
            if not insert_success:
                print("🔄 [Fallback] send_keys 직접 입력...")
                try:
                    text_to_send = content[:2000] if len(content) > 2000 else content
                    editor.send_keys(text_to_send)
                    time.sleep(1)
                    print(f"✅ send_keys 완료 ({len(text_to_send)}자)")
                    insert_success = True
                except Exception as sk_err:
                    print(f"❌ send_keys 실패: {sk_err}")
            
            if not insert_success:
                print("❌ 모든 내용 입력 방법 실패 - 포스팅 불가")
                return False
            
            time.sleep(1)
            
            # 3. 미디어 업로드 (사진/동영상 분리 처리)
            if image_paths and len(image_paths) > 0:
                # 사진과 동영상 분리
                image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif', '.bmp'}
                video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.wmv', '.flv'}
                
                photos = [p for p in image_paths if os.path.splitext(p)[1].lower() in image_exts]
                videos = [p for p in image_paths if os.path.splitext(p)[1].lower() in video_exts]
                
                print(f"📷 사진: {len(photos)}개, 🎬 동영상: {len(videos)}개")
                # [A] 미디어 업로드 전 에디터 포커스 해제 (경로 타이핑 방지)
                try:
                    self.driver.execute_script("document.activeElement.blur();")
                    time.sleep(0.5)
                except: pass

                # 3-1. 사진/영상 통합 전송 시작 (관장님 레시피 적용: 사진 -> 영상 아이콘 -> 영상)
                print(f"📤 미디어 업로드 시작 (사진: {len(photos)}개, 동영상: {len(videos)}개)")
                
                # [A] 사진 먼저 전송 및 팝업 닫기
                if photos:
                    try:
                        photo_input = self.driver.find_element(By.CSS_SELECTOR, "input[id^='postPhotoInput_']")
                        self.driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.opacity = '1';", photo_input)
                        photo_input.send_keys("\n".join(photos))
                        print(f"  📷 {len(photos)}개 사진 전송 명령 완료")
                        
                        # [개선] 사진 팝업 내 파일 인식 대기
                        photo_wait_time = max(15, len(photos) * 2) 
                        self._wait_for_media_count(len(photos), timeout=photo_wait_time)
                        
                        # [개선] 첨부하기 버튼 대기 (동적 타임아웃)
                        if self._wait_for_attach_button_ready(timeout=photo_wait_time):
                            print("  ✅ 사진 팝업 첨부하기 클릭")
                            self._click_attach_button()
                            # [핵심] 메인화면 복귀 및 모달 닫힘 확실히 대기 (충돌 방지)
                            time.sleep(3)
                            WebDriverWait(self.driver, 10).until_not(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "section.lyWrap.layer_wrap"))
                            )
                        else:
                            print("  ⚠️ 사진 첨부 버튼 활성화 지연, 강제 진행 시도")
                            self._click_attach_button()
                    except Exception as e:
                        print(f"  ⚠️ 사진 전송 중 오류: {e}")

                # [B] 동영상 전송 및 팝업 닫기
                if videos:
                    video_attempted = False
                    try:
                        # 이전 모달이 완전히 닫혔는지 재확인
                        time.sleep(2)
                        print(f"  🎬 {len(videos)}개 동영상 전송 시작...")
                        
                        video_input = self.driver.find_element(By.CSS_SELECTOR, "input[id^='postVideoInput_']")
                        self.driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.opacity = '1';", video_input)
                        
                        video_input.send_keys("\n".join(videos))
                        print(f"    ✅ 동영상 파일 전송 명령 완료")
                        video_attempted = True
                        
                        # 동영상 change 이벤트 강제 발생
                        try:
                            self.driver.execute_script("var ev = new Event('change', {bubbles:true}); arguments[0].dispatchEvent(ev);", video_input)
                        except: pass
                        
                        if video_attempted:
                            # [개선] 동영상 팝업 내 파일 인식 대기
                            video_wait_time = max(30, len(videos) * 40) # 영상은 인코딩 시간이 필요함
                            self._wait_for_media_count(len(videos), timeout=60) # 리스트업 자체는 금방 됨
                            
                            # 고화질 체크
                            self._check_high_quality_option()
                            
                            # [개선] 동영상 첨부 버튼 활성화 대기 (충분히 부여)
                            print(f"⏳ 동영상 처리 및 첨부 버튼 대기 (최대 {video_wait_time}초)...")
                            if self._wait_for_attach_button_ready(timeout=video_wait_time):
                                print("  ✅ 동영상 팝업 첨부하기 클릭")
                                self._click_attach_button()
                                time.sleep(3)
                            else:
                                print("  ⚠️ 동영상 첨부 버튼 활성화 타임아웃, 강제 클릭 시도")
                                self._click_attach_button()
                                
                    except Exception as e:
                        print(f"  ⚠️ 동영상 처리 로직 중 예외 발생: {e}")

                # [C] 모든 첨부 완료 후 메인 에디터의 업로드 프로그레스 바 대기
                max_total_wait = max(120, (len(photos) * 5) + (len(videos) * 90))
                print(f"⏳ 메인 화면 전체 업로드 프로그레스 대기 중 (최대 {max_total_wait}초)...")
                self._wait_for_upload_complete(timeout=max_total_wait)
                
                # 모든 미디어 업로드 완료 후 게시 버튼 활성화 확인
                print("🔍 최종 업로드 상태 확인 중...")
                
                # 게시 버튼이 활성화될 때까지 대기 (최대 3분)
                ready_btn = self._wait_for_submit_button_ready(timeout=180)
                
                if ready_btn:
                    print("✅ 모든 업로드 완료, 게시 준비됨")
                    # 🔧 파일 개수 기반 동적 대기 시간 (2개당 1초 + 기본 15초, 최대 90초)
                    total_files = len(photos) + len(videos) if 'photos' in dir() and 'videos' in dir() else 0
                    dynamic_wait = min(15 + (total_files // 2), 90)  # 최대 90초
                    print(f"⏳ 안전 대기 {dynamic_wait}초... (파일 {total_files}개)")
                    time.sleep(dynamic_wait)
                    print("✅ 대기 완료, 게시 진행")
                else:
                    # 버튼 활성화 실패 시 추가 안정화 대기
                    print("⚠️ 게시 버튼 활성화 확인 실패, 30초 추가 대기...")
                    time.sleep(30)
            
            # 4. 예약 설정 (reservation_time이 있는 경우)
            reservation_success = False  # 예약 성공 플래그
            
            if reservation_time:
                print(f"⏰ 예약 설정 시작: {reservation_time}")
                try:
                    # 4-0. 방해 요소(팝업 등) 제거
                    try:
                        print("  🧹 팝업 정리 시도...")
                        # ESC 키 전송으로 모달 닫기 시도
                        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                        time.sleep(0.5)
                        
                        # 닫기 버튼 등이 있으면 클릭
                        close_btns = self.driver.find_elements(By.CSS_SELECTOR, "button.btn_close, button.btnClose, .layer_wrap .uButton.-cancel")
                        for btn in close_btns:
                            if btn.is_displayed():
                                btn.click()
                                time.sleep(0.5)
                    except Exception as pop_err:
                        print(f"  ⚠️ 팝업 정리 중 무시 가능한 오류: {pop_err}")

                    # 4-1. 글쓰기 설정 버튼 클릭
                    setting_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btnSetting._btnWriteSetting"))
                    )
                    setting_btn.click()
                    time.sleep(1)
                    
                    # 4-2. 예약 체크박스 활성화 (이미 체크되어 있는지 확인 필요할 수 있음)
                    reserve_chk_label = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "label[for='reserve']")) # input은 숨겨져 있을 수 있어 label 클릭 유도
                    )
                    
                    # 체크박스 상태 확인 (input#reserve.checkInput._checkReserve)
                    reserve_input = self.driver.find_element(By.CSS_SELECTOR, "input#reserve.checkInput._checkReserve")
                    if not reserve_input.is_selected():
                        reserve_chk_label.click()
                        time.sleep(1)
                        print("  ✅ 예약 사용 체크됨")
                    else:
                        print("  ℹ️ 예약 이미 체크됨")
                    
                    # 4-2-1. 날짜 선택 (예약 시간이 현재보다 이전이면 다음 날 선택)
                    from datetime import datetime, timedelta
                    now = datetime.now()
                    h_temp, m_temp = map(int, reservation_time.split(':'))
                    target_dt_temp = now.replace(hour=h_temp, minute=m_temp, second=0, microsecond=0)
                    
                    is_tomorrow = False
                    if target_dt_temp <= now:
                        is_tomorrow = True
                        target_dt_temp += timedelta(days=1)
                        print(f"  📅 예약 시간이 현재보다 이전이므로 다음 날({target_dt_temp.strftime('%Y-%m-%d')})로 설정합니다.")
                    
                    if is_tomorrow:
                        try:
                            # 날짜 입력 필드 클릭하여 달력 열기
                            date_input_selectors = [
                                "input[id*='pickedDate']._input",
                                "input.gFs1",
                                "input[title*='날짜']",
                                ".datePickerRegion input"
                            ]
                            
                            date_input = None
                            for selector in date_input_selectors:
                                try:
                                    date_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                                    if date_input.is_displayed():
                                        break
                                except:
                                    continue
                            
                            if date_input:
                                date_input.click()
                                time.sleep(1)
                                print("  ✅ 달력 열기 성공")
                                
                                # 다음 날 날짜 셀 찾아서 클릭
                                target_day = target_dt_temp.day
                                
                                # 달력에서 날짜 셀 찾기 (disabled가 아닌 것)
                                day_cells = self.driver.find_elements(By.CSS_SELECTOR, "table.calendar._calendar td._td:not(.disabled)")
                                
                                for cell in day_cells:
                                    try:
                                        cell_text = cell.text.strip()
                                        if cell_text and int(cell_text) == target_day:
                                            cell.click()
                                            print(f"  ✅ 날짜 선택 완료: {target_day}일")
                                            time.sleep(0.5)
                                            break
                                    except:
                                        continue
                            else:
                                print("  ⚠️ 날짜 입력 필드를 찾을 수 없습니다.")
                        except Exception as date_err:
                            print(f"  ⚠️ 날짜 선택 중 오류 (무시하고 진행): {date_err}")
                    
                    # 4-3. 시간 선택창 열기
                    time_input = self.driver.find_element(By.CSS_SELECTOR, "input[class*='_timeInput']")
                    time_input.click()
                    time.sleep(1)
                    
                    # 4-4. 시간 검증 및 조정
                    from datetime import datetime, timedelta
                    now = datetime.now()
                    
                    try:
                        h, m = map(int, reservation_time.split(':'))
                        # 현재 시간과 비교를 위해 날짜 결합 (오늘)
                        target_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
                        
                        # 예약 시간이 현재보다 빠르면 내일로 간주
                        if target_dt < now:
                            target_dt += timedelta(days=1)
                        
                        # 최소 예약 가능 시간 (현재 + 40분으로 넉넉하게 설정)
                        min_reserve_time = now + timedelta(minutes=40)
                        
                        if target_dt < min_reserve_time:
                            print(f"⚠️ 예약 시간이 너무 이릅니다 ({reservation_time}). 최소 40분 뒤로 조정합니다.")
                            target_dt = min_reserve_time
                            # 다시 5분 단위 반올림
                            m_adjusted = ((target_dt.minute + 4) // 5) * 5
                            if m_adjusted >= 60:
                                target_dt += timedelta(hours=1)
                                m_adjusted = 0
                            target_dt = target_dt.replace(minute=m_adjusted, second=0)
                        
                        # 최종 설정 시간
                        h = target_dt.hour
                        m = target_dt.minute
                        
                        # 오전/오후 변환
                        period = "오전"
                        if h >= 12:
                            period = "오후"
                        
                        h_12 = h
                        if h > 12:
                            h_12 = h - 12
                        elif h == 0:
                            h_12 = 12
                        
                        # 포맷팅 (예: "오후 4:40")
                        target_time_str = f"{period} {h_12}:{m:02d}"
                        print(f"  🎯 목표 예약 시간: {target_time_str} (원본: {reservation_time})")
                        
                        # 4-5. 해당 시간 버튼 찾아서 클릭
                        # 드롭다운 리스트에서 텍스트로 찾기
                        time_btns = self.driver.find_elements(By.CSS_SELECTOR, "button.btnDropDownItem._btnTime")
                        found_time = False
                        
                        for btn in time_btns:
                            # 텍스트 비교 (공백 등 제거하고 비교)
                            btn_text = btn.text.strip()
                            if btn_text == target_time_str:
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                                time.sleep(0.5)
                                btn.click()
                                found_time = True
                                print(f"  ✅ 시간 선택 완료: {btn_text}")
                                break
                                
                        if not found_time:
                            print(f"  ❌ 예약 시간({target_time_str})을 찾을 수 없습니다.")
                            # 실패시 닫기
                            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                            reservation_success = False
                            
                    except Exception as time_err:
                        print(f"  ❌ 시간 변환/선택 중 오류: {time_err}")
                        reservation_success = False
                    
                    # 4-6. 확인 버튼 클릭 (사용자 이미지 기반: button.uButton.-confirm._btnComplete)
                    try:
                        time.sleep(1)
                        confirm_selectors = [
                            "button.uButton.-confirm._btnComplete", # 사용자 이미지 기반
                            "button.uButton.-confirm",
                            "button._btnComplete",
                            "//button[contains(text(), '확인')]"
                        ]
                        
                        clicked_confirm = False
                        for selector in confirm_selectors:
                            try:
                                if selector.startswith("//"):
                                    btn = self.driver.find_element(By.XPATH, selector)
                                else:
                                    btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                                
                                if btn.is_displayed():
                                    btn.click()
                                    clicked_confirm = True
                                    reservation_success = True
                                    print("  ✅ 예약 설정 확인 버튼 클릭함")
                                    break
                            except: continue
                        
                        if not clicked_confirm:
                            print("  ⚠️ 확인 버튼을 찾지 못해 엔터키 입력 시도")
                            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                            
                    except Exception as e: 
                        print(f"  ❌ 확인 버튼 처리 중 오류: {e}")
                    
                    # 설정 레이어 닫힘 대기
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"❌ 예약 설정 실패: {e}")
                    reservation_success = False
                    # 실패 시 알림 처리
                    try:
                        alert = self.driver.switch_to.alert
                        print(f"Alert Text: {alert.text}")
                        alert.accept()
                    except: pass
                
                # 예약 설정 실패 시 게시 중단
                if not reservation_success:
                    print("❌ 예약 설정에 실패하여 게시를 중단합니다. (다음 스케줄로 넘어갑니다)")
                    return False

            # 5. 최종 게시
            submit_btn = self._wait_for_submit_button_ready(timeout=60)
            if submit_btn:
                print("🚀 게시 완료 버튼 클릭 시도...")
                time.sleep(2)
                try: submit_btn.click()
                except: self.driver.execute_script("arguments[0].click();", submit_btn)
                
                # 🔍 [개선] 게시 성공 여부 검증 (글쓰기 창이 사라지는지 확인)
                print("⏳ 게시 완료 대기 중 (최대 15초)...")
                is_closed = False
                for _ in range(15):
                    try:
                        # 글쓰기 창이나 오버레이가 사라졌는지 확인
                        active_editors = self.driver.find_elements(By.CSS_SELECTOR, "div.postWriteArea, div[contenteditable='true']")
                        if not any(e.is_displayed() for e in active_editors):
                            is_closed = True
                            break
                    except: pass
                    time.sleep(1)
                
                if is_closed:
                    print("✅ 게시 성공 확인! 밴드 홈으로 이동합니다.")
                else:
                    print("⚠️ 게시 완료 확인 지연, 홈으로 강제 이동합니다.")
                
                # 🏠 [개선] 새로고침 대신 밴드 홈으로 이동 (무한 글쓰기 창 방지)
                home_url = band_url.replace('/post', '')
                
                # [안전장치] 이동 전 '작성 취소' 팝업 등이 뜨면 강제 확인 클릭
                try:
                    # '확인' 버튼 (uButton -confirm) 패턴
                    confirm_modal_btns = self.driver.find_elements(By.CSS_SELECTOR, "div.modal-footer button.uButton.-confirm, .uButton.-confirm._btnConfirm")
                    for btn in confirm_modal_btns:
                        if btn.is_displayed():
                            btn.click()
                            time.sleep(1)
                            print("  ✅ 작성 취소 팝업 강제 확인 완료")
                except: pass

                self.driver.get(home_url)
                time.sleep(3)
                return True
            
            print("❌ 게시 버튼을 찾을 수 없거나 활성화되지 않았습니다.")
            return False
 
        except Exception as e:
            print(f"❌ 밴드 포스팅 실패: {e}")
            return False
 
    def _enter_content(self, editor, content):
        """에디터 내용 입력 (클립보드 방식 + JS 백업)"""
        print("⌨️ 본문 입력 중...")
        try:
            # 1. 에디터 초기화 및 포커스
            self.driver.execute_script("arguments[0].innerHTML = ''; arguments[0].focus();", editor)
            time.sleep(0.5)
            
            # 2. 클립보드 복사 (macOS pbcopy)
            import subprocess
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            process.communicate(content.encode('utf-8'))
            time.sleep(0.5)
            
            # 3. 붙여넣기 실행
            ActionChains(self.driver).key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
            time.sleep(1.5)
            
            # 4. 입력 확인 및 백업 주입
            current_val = self.driver.execute_script("return arguments[0].innerText || arguments[0].value;", editor)
            if not current_val or len(current_val.strip()) < 5:
                print("  ⚠️ 클립보드 입력 실패 감지, JS 직접 주입으로 전환합니다.")
                # 🔧 innerText 대신 textContent와 innerHTML을 복합적으로 사용하여 리액트 상태 변화 유도
                self.driver.execute_script("""
                    var editor = arguments[0];
                    var text = arguments[1];
                    editor.focus();
                    editor.innerText = text;
                    // 다양한 이벤트를 발생시켜 내부 상태 업데이트 강제
                    ['input', 'change', 'blur', 'keyup', 'keydown', 'keypress'].forEach(function(eventType) {
                        var event = new Event(eventType, { bubbles: true });
                        editor.dispatchEvent(event);
                    });
                """, editor, content)
                time.sleep(1)
            
            print("✅ 본문 입력 공정 완료")
        except Exception as e:
            print(f"⚠️ 입력 중 오류 발생, 최후의 수단(send_keys) 시도: {e}")
            try: editor.send_keys(content)
            except: pass

# 테스트 코드 생략
