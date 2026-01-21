import time
import os
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
                    self.driver.execute_script("arguments[0].click();", attach_btn)
                    print("✅ 첨부하기 버튼 클릭 완료")
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
            print(f"🌐 밴드로 이동 중: {band_url}")
            self.driver.get(band_url)
            time.sleep(3)
            
            # 1. 글쓰기 영역 클릭
            print("📝 글쓰기 영역 찾는 중...")
            write_area_selectors = [
                "button.roundButton.-full._btnWritePost",  # 🆕 녹색 글쓰기 버튼
                "button.cPostWriteEventWrapper._btnOpenWriteLayer",  # 🆕 글쓰기 레이어 열기
                "div.buttonArea._btnOpenWriteLayer",  # 🆕 버튼 영역
                "button._btnPostWrite",
                "div.postWriteArea",
                "textarea._postWriteInput",
                "._btnPostWriteShow",
                "button.uButtonPostWrite",
                "[data-test-id='post-write-button']"
            ]
            
            write_btn = None
            for selector in write_area_selectors:
                try:
                    write_btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if write_btn:
                        break
                except:
                    continue
            
            # 텍스트로 찾기 (백업)
            if not write_btn:
                try:
                    print("🔍 텍스트('글쓰기', 'Post')로 영역 찾는 중...")
                    search_texts = ["글쓰기", "Post", "새로운 소식을"]
                    for text in search_texts:
                        btns = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{text}')]")
                        for btn in btns:
                            if btn.is_displayed():
                                write_btn = btn
                                break
                        if write_btn: break
                except: pass

            if not write_btn:
                print("❌ 글쓰기 영역을 찾을 수 없습니다. (현재 페이지에서 포스팅이 불가능할 수 있습니다)")
                return False
                
            self.driver.execute_script("arguments[0].click();", write_btn)
            time.sleep(2)
            
            # 2. 내용 입력
            print("⌨️ 내용 입력 중...")
            editor = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'], textarea._postWriteInput"))
            )
            
            # 클립보드를 통한 입력 시도 (한글 깨짐 방지)
            try:
                import pyperclip
                
                # 🔧 클립보드 복사 및 검증
                pyperclip.copy(content)
                time.sleep(0.5)  # 클립보드 안정화 대기
                
                # 클립보드 내용 검증
                clipboard_content = pyperclip.paste()
                if len(clipboard_content) < len(content) * 0.9:  # 90% 미만이면 재시도
                    print(f"⚠️ 클립보드 복사 불완전, 재시도 중... (원본: {len(content)}자, 복사됨: {len(clipboard_content)}자)")
                    pyperclip.copy(content)
                    time.sleep(0.5)
                
                editor.click()
                time.sleep(0.3)  # 클릭 후 대기
                
                if os.name == 'nt':  # Windows
                    ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                else:  # macOS
                    ActionChains(self.driver).key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
                
                time.sleep(0.5)  # 붙여넣기 후 대기
            except Exception as e:
                print(f"⚠️ 클립보드 입력 실패, send_keys 사용: {e}")
                editor.send_keys(content)
            
            time.sleep(1)
            
            # 3. 미디어 업로드 (사진/동영상 분리 처리)
            if image_paths and len(image_paths) > 0:
                # 사진과 동영상 분리
                image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif', '.bmp'}
                video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.wmv', '.flv'}
                
                photos = [p for p in image_paths if os.path.splitext(p)[1].lower() in image_exts]
                videos = [p for p in image_paths if os.path.splitext(p)[1].lower() in video_exts]
                
                print(f"📷 사진: {len(photos)}개, 🎬 동영상: {len(videos)}개")
                
                # 3-1. 사진 첨부 (사진이 있는 경우)
                if photos:
                    print(f"📷 사진 업로드 중 ({len(photos)}개)...")
                    try:
                        # 숨겨진 file input 요소 찾기
                        photo_input = self.driver.find_element(By.CSS_SELECTOR, "input[id^='postPhotoInput_']")
                        
                        if photo_input:
                            # input 요소를 보이게 만들기 (send_keys가 작동하도록)
                            self.driver.execute_script("""
                                var el = arguments[0];
                                el.style.cssText = 'opacity: 1 !important; width: 200px !important; height: 50px !important; position: relative !important; z-index: 9999 !important; display: block !important;';
                            """, photo_input)
                            time.sleep(1)
                            
                            # 여러 파일 경로를 줄바꿈으로 연결하여 전송
                            file_paths = "\n".join(photos)
                            photo_input.send_keys(file_paths)
                            print(f"✅ {len(photos)}개 사진 파일 전송됨")
                            
                            # input 요소 원래대로 복원
                            try:
                                self.driver.execute_script("""
                                    var el = arguments[0];
                                    el.style.cssText = '';
                                """, photo_input)
                            except:
                                pass
                        
                        # 파일 선택 후 첨부하기 버튼이 활성화될 때까지 대기
                        # (팝업 감지가 안 되어도 실제 업로드는 진행 중일 수 있음)
                        print(f"⏳ 첨부하기 버튼 활성화 대기 중... (파일 {len(photos)}개)")
                        
                        # 파일 개수에 따라 최대 대기 시간 설정 (최소 60초, 파일당 3초)
                        max_wait = max(60, len(photos) * 3)
                        attach_button_found = False
                        
                        for wait_count in range(max_wait):
                            try:
                                # 첨부하기 버튼 찾기
                                attach_selectors = [
                                    "button.uButton.-confirm._submitBtn",
                                    "button._submitBtn",
                                    "//button[contains(text(), '첨부하기')]"
                                ]
                                for selector in attach_selectors:
                                    try:
                                        if selector.startswith("//"):
                                            btn = self.driver.find_element(By.XPATH, selector)
                                        else:
                                            btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                                        
                                        if btn and btn.is_displayed() and btn.is_enabled():
                                            attach_button_found = True
                                            print(f"✅ 첨부하기 버튼 활성화됨 ({wait_count+1}초 경과)")
                                            break
                                    except:
                                        continue
                                
                                if attach_button_found:
                                    break
                                    
                            except:
                                pass
                            
                            time.sleep(1)
                            if wait_count > 0 and wait_count % 15 == 0:
                                print(f"  ⏳ 대기 중... {wait_count}초 경과")
                        
                        if not attach_button_found:
                            print(f"⚠️ 첨부하기 버튼을 {max_wait}초 내에 찾지 못함, 계속 진행...")
                        
                        # "첨부하기" 버튼 클릭 (이 시점에 이미 업로드 완료됨)
                        time.sleep(1)
                        self._click_attach_button()
                        
                        # 첨부 완료 후 짧은 안정화 대기
                        print("⏳ 사진 첨부 완료, 3초 안정화 대기...")
                        time.sleep(3)
                        print("✅ 사진 첨부 완료")
                        
                    except Exception as photo_err:
                        print(f"⚠️ 사진 업로드 중 오류: {photo_err}")
                
                # 3-2. 동영상 첨부 (동영상이 있는 경우)
                if videos:
                    print(f"🎬 동영상 업로드 중 ({len(videos)}개)...")
                    time.sleep(3)  # 사진 업로드 완료 후 안정화 대기 (3초로 줄임)
                    try:
                        # 숨겨진 동영상 file input 요소 찾기 - 새로 찾기 (stale 방지)
                        video_input = self.driver.find_element(By.CSS_SELECTOR, "input[id^='postVideoInput_']")
                        
                        if video_input:
                            # 여러 파일 경로를 줄바꿈으로 연결하여 전송
                            file_paths = "\n".join(videos)
                            video_input.send_keys(file_paths)
                            print(f"✅ {len(videos)}개 동영상 파일 전송됨")
                            
                            # send_keys 후 change 이벤트를 명시적으로 dispatch
                            try:
                                self.driver.execute_script("""
                                    var event = new Event('change', { bubbles: true });
                                    arguments[0].dispatchEvent(event);
                                """, video_input)
                                print("✅ change 이벤트 dispatch됨")
                            except Exception as ev_err:
                                print(f"⚠️ change 이벤트 dispatch 실패: {ev_err}")
                        
                        # 파일 선택 후 첨부하기 팝업이 나타나기 대기
                        print("⏳ 첨부 팝업 대기 중...")
                        time.sleep(5)  # 5초로 줄임
                        
                        # 동영상도 고화질 첨부 체크박스 확인 및 체크
                        try:
                            hq_checkbox_selectors = [
                                "input._checkHighQuality",
                                "input[id*='attachmentview'][type='checkbox']",
                                "//input[contains(@id, 'attachment') and @type='checkbox']",
                            ]
                            for selector in hq_checkbox_selectors:
                                try:
                                    if selector.startswith("//"):
                                        checkbox = self.driver.find_element(By.XPATH, selector)
                                    else:
                                        checkbox = self.driver.find_element(By.CSS_SELECTOR, selector)
                                    if checkbox and not checkbox.is_selected():
                                        self.driver.execute_script("arguments[0].click();", checkbox)
                                        print("✅ 동영상 고화질 첨부 체크됨")
                                        break
                                except:
                                    continue
                        except:
                            pass
                        
                        # "첨부하기" 버튼 클릭
                        time.sleep(1)
                        self._click_attach_button()
                        
                        # 동영상 업로드 완료 대기 - 파일 개수에 따라 타임아웃 조절
                        upload_timeout = max(120, len(videos) * 60)  # 최소 2분, 동영상당 1분
                        print(f"⏳ 업로드 대기 (타임아웃: {upload_timeout}초)...")
                        self._wait_for_upload_complete(timeout=upload_timeout)
                        
                        # 동영상 첨부 완료 후 안정화 대기 (파일 개수 기반)
                        stabilize_time = min(10, max(5, len(videos) * 3))  # 5~10초 범위
                        print(f"⏳ 동영상 첨부 완료, {stabilize_time}초 안정화 대기...")
                        time.sleep(stabilize_time)
                        print("✅ 동영상 첨부 완료")
                        
                    except Exception as video_err:
                        print(f"⚠️ 동영상 업로드 중 오류: {video_err}")
                
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

            # 5. 게시 버튼 클릭
            print("🚀 게시(또는 예약) 버튼 클릭 중...")
            submit_btn = None
            submit_selectors = [
                "button._btnSubmitPost", 
                "button.uButton.-confirm",
                "button._btnPost",
                "button.uButton.-sizeM._btnSubmitPost.-confirm" # 스크린샷 기반
            ]
            
            for selector in submit_selectors:
                try:
                    submit_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if submit_btn:
                        break
                except:
                    continue
            
            if submit_btn:
                try:
                    submit_btn.click()
                except:
                    self.driver.execute_script("arguments[0].click();", submit_btn)
                print("✅ 게시(예약) 버튼 클릭 완료")
            else:
                print("❌ 게시 버튼을 찾을 수 없습니다.")
                return False
            
            time.sleep(3)
            print("✅ 밴드 포스팅(예약) 완료!")
            return True
            
        except Exception as e:
            print(f"❌ 밴드 포스팅 중 오류 발생: {e}")
            traceback.print_exc()
            return False

# 테스트 코드 생략
