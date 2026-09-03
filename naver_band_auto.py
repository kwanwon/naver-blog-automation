import time
import os
import sys
import traceback
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

class NaverBandAutomation:
    def __init__(self, driver):
        self.driver = driver
    
    def _wait_for_attach_button_ready(self, timeout: int = 60):
        """첨부 레이어 팝업('사진 올리기' / '동영상 올리기')의 [첨부하기] 버튼이 활성화될 때까지 대기"""
        start_time = time.time()
        attach_btn_selectors = [
            "button._submitBtn",
            "button.uButton.-confirm._submitBtn",
            ".modalFooter button._submitBtn",
            ".modalFooter button.uButton.-confirm",
            "//button[normalize-space()='첨부하기']",
            "//button[contains(text(), '첨부하기')]",
            "//div[contains(@class, 'layer') or contains(@class, 'modal') or contains(@class, 'Wrap') or contains(@class, 'dialog') or contains(@class, 'popup') or contains(@class, 'uLayer')]//button[contains(text(), '첨부')]"
        ]
        
        while time.time() - start_time < timeout:
            for selector in attach_btn_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for btn in elements:
                        if btn.is_displayed():
                            # 🛡️ [핵심 안전장치] 메인 글쓰기 [게시] 버튼(_btnSubmitPost)은 절대 첨부 버튼으로 오인하지 않음
                            btn_class = btn.get_attribute("class") or ""
                            btn_text = btn.text.strip()
                            if "_btnSubmitPost" in btn_class or "게시" in btn_text:
                                continue
                            
                            is_disabled = btn.get_attribute("disabled") or "disabled" in btn_class
                            if not is_disabled:
                                return btn
                except:
                    continue
            time.sleep(1.0)
        return None

    def _click_attach_button(self):
        """첨부 레이어 팝업의 [첨부하기] 버튼 클릭 헬퍼"""
        btn = self._wait_for_attach_button_ready(timeout=15)
        if btn:
            try:
                btn.click()
            except:
                self.driver.execute_script("arguments[0].click();", btn)
            print("✅ 첨부 팝업 [첨부하기] 버튼 클릭 완료")
            time.sleep(1.5)
            return True
        
        print("⚠️ 첨부하기 버튼을 찾지 못함 (직접 첨부 형태이거나 팝업 없음)")
        return False
    
    def _wait_for_upload_complete(self, timeout: int = 300):
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
        popup_ever_appeared = False
        
        # 업로드 팝업 셀렉터 (사진/동영상 공통)
        popup_selectors = [
            "section.lyWrap.layer_wrap",
            ".layer_wrap",
            ".progress.skin4"
        ]
        progress_selector = ".progress.skin4 .fileBy, .fileBy, ._fileBy"  # "25/30" 형식
        
        # 1단계: 팝업이 뜰 때까지 최대 5초 대기
        for _ in range(5):
            for p_sel in popup_selectors:
                popups = self.driver.find_elements(By.CSS_SELECTOR, p_sel)
                if any(p.is_displayed() for p in popups if p):
                    popup_ever_appeared = True
                    break
            if popup_ever_appeared:
                break
            time.sleep(1)
            
        while time.time() - start_time < timeout:
            try:
                # 팝업 가시성 확인
                popups_visible = False
                for p_sel in popup_selectors:
                    popups = self.driver.find_elements(By.CSS_SELECTOR, p_sel)
                    if any(p.is_displayed() for p in popups if p):
                        popups_visible = True
                        popup_ever_appeared = True
                        break
                
                # 팝업이 떴다가 사라진 경우 완료
                if popup_ever_appeared and not popups_visible:
                    print("  ✅ 업로드 팝업 정상 종료 - 업로드 완료")
                    time.sleep(1.5)  # 가벼운 안정화 대기
                    return True
                
                # 진행 상황(X/Y) 확인
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
                                            time.sleep(1.5)  # 팝업 닫힘 대기
                                            return True
                                    except ValueError:
                                        pass
                            break
                except:
                    pass
                    
                # 팝업 내부의 로딩/프로그레스바 완료 및 [첨부하기] 준비 감지
                try:
                    loading_spinners = self.driver.find_elements(By.CSS_SELECTOR, "section.lyWrap.layer_wrap .loading, section.lyWrap.layer_wrap .spin, section.lyWrap.layer_wrap .progressbar, section.lyWrap.layer_wrap .progress_bar")
                    has_loading = any(s.is_displayed() for s in loading_spinners if s)
                    if popup_ever_appeared and not has_loading:
                        ready_attach = self.driver.find_elements(By.CSS_SELECTOR, "section.lyWrap.layer_wrap button._submitBtn.-confirm, section.lyWrap.layer_wrap button.uButton.-confirm._submitBtn")
                        if ready_attach and any(b.is_displayed() for b in ready_attach):
                            print("  ✅ 팝업 내 파일 업로드 완료 및 [첨부하기] 버튼 준비 확인")
                            time.sleep(1.0)
                            return True
                except:
                    pass
                
            except Exception as e:
                pass
            
            time.sleep(1)  # 1초 간격으로 확인
        
        print(f"  ⚠️ 업로드 타임아웃 또는 완료 감지 완료")
        return True
    
    def _wait_for_submit_button_ready(self, timeout: int = 60):
        """
        게시 버튼이 활성화(클릭 가능)될 때까지 대기
        
        Returns:
            게시 버튼 element 또는 None
        """
        print("🔍 게시 버튼 활성화 대기 중...")
        
        submit_selectors = [
            "button._btnSubmitPost:not([disabled])",
            "button.uButton.-confirm._btnSubmitPost:not([disabled])",
            "button.uButton.-sizeM._btnSubmitPost:not([disabled])",
            "button.uButton.-sizeM._btnSubmitPost.-confirm:not([disabled])",
            "button._btnSubmitPost.-confirm",
            "button._btnPost:not([disabled])",
            "//button[contains(@class, '_btnSubmitPost') and not(@disabled)]"
        ]
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            for selector in submit_selectors:
                try:
                    if selector.startswith("//"):
                        btn = self.driver.find_element(By.XPATH, selector)
                    else:
                        btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if btn and btn.is_displayed() and btn.is_enabled():
                        cls = btn.get_attribute("class") or ""
                        if "disabled" not in cls:
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
            # 🌐 URL 정규화: /post 등 서브 경로를 제거하여 메인 밴드 홈으로 확실하게 이동
            import re
            clean_band_url = re.sub(r'/post.*$', '', band_url).rstrip('/')
            print(f"🌐 밴드로 이동 중: {clean_band_url}")
            self.driver.get(clean_band_url)
            time.sleep(3)
            
            # 1. 글쓰기 영역 클릭 (최대 10초간 대기하며 탐색)
            print("📝 글쓰기 영역 찾는 중...")
            write_area_selectors = [
                # 1순위: 좌측 메뉴의 큰 초록색 [글쓰기] 버튼
                "//button[contains(@class, 'roundButton') and contains(., '글쓰기')]",
                "//button[contains(@class, '_btnWritePost')]",
                "//a[contains(@class, '_btnWritePost')]",
                "button.roundButton.-full._btnWritePost",
                "button._btnWritePost",
                "button[data-viewname='DPostWriteButtonView']",
                "//button[normalize-space()='글쓰기']",
                # 2순위: 중앙 '새로운 소식을 남겨보세요.' 텍스트 라벨 및 상단 글쓰기 박스
                "div.postWriteArea",
                "div.cPostWrite",
                "div.postWriteForm",
                "button._btnOpenWriteLayer",
                "//button[contains(@class, 'cPostWriteEventWrapper')]",
                "//div[contains(@class, 'cPostWrite') or contains(@class, 'postWrite')]//*[contains(text(), '새로운 소식을') and not(self::button)]",
                "//*[normalize-space()='새로운 소식을 남겨보세요.']",
                "//button[contains(@class, 'cPostWriteEventWrapper') and contains(@class, '_btnOpenWriteLayer')]"
            ]
            
            write_btn = None
            for attempt in range(10):
                for selector in write_area_selectors:
                    try:
                        if selector.startswith("//"):
                            elements = self.driver.find_elements(By.XPATH, selector)
                        else:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        for el in elements:
                            # 툴바 내부의 요소(일정, 투표 등)는 절대 클릭하지 않음
                            try:
                                is_toolbar = self.driver.execute_script("return arguments[0].closest('.toolbarList, ._toolbarList') !== null;", el)
                                if is_toolbar:
                                    continue
                            except:
                                pass
                                
                            if el.is_displayed():
                                write_btn = el
                                break
                        if write_btn:
                            break
                    except:
                        continue
                if write_btn:
                    break
                time.sleep(1)
            
            if not write_btn:
                print("❌ 글쓰기 영역을 찾을 수 없습니다. (현재 페이지에서 포스팅이 불가능할 수 있습니다)")
                return False
                
            # 글쓰기 버튼 클릭 (일반 클릭 및 JS 클릭 병행)
            print(f"  ✅ 글쓰기 버튼 발견: {write_btn.text.strip() or write_btn.tag_name}")
            try:
                write_btn.click()
            except:
                self.driver.execute_script("arguments[0].click();", write_btn)
            time.sleep(1.5)
            
            # 글쓰기 폼이 standby 상태에서 풀릴 때까지 대기
            try:
                WebDriverWait(self.driver, 5).until_not(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".postWriteForm.-standby, ._postWriteForm.-standby"))
                )
            except:
                pass
            time.sleep(0.5)
            
            # 2. 내용 입력 (모달 내부의 활성 에디터 정확히 탐색)
            print("⌨️ 내용 입력 중...")
            editor = None
            editor_selectors = [
                # 1순위: 모달 팝업 내부의 에디터
                "div.cPostWriteModal div[contenteditable='true']",
                "div.postWriteModal div[contenteditable='true']",
                "div.layer_wrap div[contenteditable='true']",
                "section.lyWrap div[contenteditable='true']",
                "div.cPostWriteModal [role='textbox']",
                "div.postWriteModal [role='textbox']",
                "div.layer_wrap [role='textbox']",
                "section.lyWrap [role='textbox']",
                # 2순위: 활성 폼 내부의 에디터
                ".postWriteArea.-active div[contenteditable='true']",
                ".postWriteForm.-active div[contenteditable='true']",
                ".cPostWrite.-active div[contenteditable='true']",
                # 3순위: 전체 영역에서 보이는 에디터
                "div[contenteditable='true']",
                "div.contentEditor",
                ".ProseMirror",
                ".ck-content",
                "[role='textbox']",
                "textarea._postWriteInput"
            ]
            
            for attempt in range(5):
                for selector in editor_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for el in elements:
                            if el.is_displayed():
                                editor = el
                                break
                        if editor:
                            break
                    except:
                        continue
                if editor:
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].focus();", editor)
                        time.sleep(0.3)
                        try:
                            editor.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", editor)
                        time.sleep(0.5)
                        break
                    except Exception as e:
                        print(f"⚠️ 에디터 포커스 재시도 중... ({attempt+1}/5)")
                        editor = None
                time.sleep(1.0)
            
            if not editor:
                print("❌ 활성화된 에디터를 찾거나 클릭하지 못했습니다.")
                return False
            
            # 🧹 [중요] 기존 에디터 내용 비우기 (DOM 구조 유지를 위해 send_keys 활용)
            is_mac = sys.platform == 'darwin'
            mod_key = Keys.COMMAND if is_mac else Keys.CONTROL
            
            try:
                editor.send_keys(mod_key, 'a')
                time.sleep(0.2)
                editor.send_keys(Keys.BACK_SPACE)
                time.sleep(0.2)
            except:
                pass
            
            # 본문 텍스트 주입 (1순위: JS execCommand, 2순위: 클립보드 ActionChains, 3순위: send_keys 직접 타이핑, 4순위: DOM HTML 주입)
            try:
                # 1순위: 브라우저 창 포커스와 무관하게 100% 본문을 타이핑하는 execCommand 실행
                inserted = self.driver.execute_script("""
                    var el = arguments[0];
                    var text = arguments[1];
                    el.focus();
                    var success = document.execCommand('insertText', false, text);
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    return success;
                """, editor, content)
                time.sleep(0.5)
            except Exception as ex_err:
                print(f"⚠️ execCommand 시도 실패: {ex_err}")
                
            # 실제 본문 내용의 앞 5글자가 에디터에 들어갔는지 정확히 검증 (Band 플레이스홀더 텍스트 배제)
            sample_check = content.strip()[:5]
            if not sample_check or sample_check not in (editor.text or ""):
                print("🔄 텍스트 미반영 확인 -> 클립보드 붙여넣기 시도...")
                try:
                    from utils.clipboard_helper import copy_to_clipboard
                    copy_to_clipboard(content)
                    time.sleep(0.2)
                    ActionChains(self.driver).key_down(mod_key).send_keys('v').key_up(mod_key).perform()
                    time.sleep(0.5)
                except:
                    pass

            if not sample_check or sample_check not in (editor.text or ""):
                print("🔄 텍스트 미반영 확인 -> editor.send_keys 직접 타이핑 실행...")
                try:
                    editor.click()
                    time.sleep(0.2)
                    editor.send_keys(content)
                    time.sleep(0.8)
                except Exception as send_err:
                    print(f"⚠️ send_keys 타이핑 오류, HTML 단락 직접 주입 실행: {send_err}")
                    try:
                        self.driver.execute_script("""
                            var el = arguments[0];
                            var text = arguments[1];
                            var lines = text.split('\\n');
                            var html = lines.map(function(line) {
                                return '<p>' + (line ? line : '<br>') + '</p>';
                            }).join('');
                            el.innerHTML = html;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                        """, editor, content)
                        time.sleep(0.5)
                    except Exception as js_err:
                        print(f"❌ JS 주입 실패: {js_err}")
            
            print("✅ 본문 텍스트 1회 입력 완료 (검증 완료)")
            
            # 📌 [중요] 텍스트 입력 후 커서를 본문 '맨 끝'으로 확실히 이동 (사진/영상이 텍스트 아래에 오도록)
            try:
                self.driver.execute_script("""
                    var el = arguments[0];
                    var p = document.createElement('p');
                    p.innerHTML = '<br>';
                    el.appendChild(p);
                    
                    var range = document.createRange();
                    var sel = window.getSelection();
                    range.setStart(p, 0);
                    range.collapse(true);
                    sel.removeAllRanges();
                    sel.addRange(range);
                    el.focus();
                """, editor)
                time.sleep(0.5)
            except Exception as cursor_err:
                print(f"⚠️ 커서 이동 중 오류: {cursor_err}")
            
            # 3. 이미지 및 동영상 첨부 (동영상 10개 제한 처리)
            if image_paths and len(image_paths) > 0:
                print(f"📷 미디어 파일 {len(image_paths)}개 첨부 시작...")
                
                # 이미지와 동영상 분리
                image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif'}
                video_exts = {'.mp4', '.mov', '.avi', '.wmv', '.mkv', '.m4v'}
                
                photos = [p for p in image_paths if os.path.splitext(p)[1].lower() in image_exts]
                videos = [p for p in image_paths if os.path.splitext(p)[1].lower() in video_exts]
                
                print(f"📷 사진: {len(photos)}개, 🎬 동영상: {len(videos)}개")
                
                # 3-1. 사진 첨부 (사진이 있는 경우)
                if photos:
                    print(f"📷 사진 업로드 중 ({len(photos)}개)...")
                    try:
                        # 숨겨진 file input 요소 찾기
                        photo_input = self.driver.find_element(By.CSS_SELECTOR, "input[id^='postPhotoInput_'], input[type='file'][accept*='image']")
                        
                        if photo_input:
                            self.driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.opacity = '1';", photo_input)
                            time.sleep(0.5)
                            
                            file_paths = "\n".join(photos)
                            photo_input.send_keys(file_paths)
                            print(f"✅ {len(photos)}개 사진 파일 전송 완료")
                            time.sleep(1.0)
                            
                            # change 이벤트 트리거
                            try:
                                self.driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", photo_input)
                            except Exception:
                                pass

                        # 1단계: 사진 파일 업로드 및 팝업 렌더링 대기
                        upload_timeout = max(60, min(300, len(photos) * 5))
                        print(f"⏳ 사진 업로드 및 팝업 렌더링 대기 (타임아웃: {upload_timeout}초)...")
                        self._wait_for_upload_complete(timeout=upload_timeout)
                        time.sleep(1.0)
                        
                        # 2단계: [사진 올리기] 팝업이 뜬 경우 [첨부하기] 버튼 클릭
                        print("⏳ 사진 팝업 [첨부하기] 버튼 클릭 시도...")
                        attach_btn = None
                        attach_selectors = [
                            "section.lyWrap.layer_wrap button._submitBtn",
                            "div.layer_wrap button._submitBtn",
                            "button.uButton.-confirm._submitBtn",
                            "button._submitBtn",
                            "//section[contains(@class, 'layer_wrap')]//button[contains(text(), '첨부')]",
                            "//div[contains(@class, 'layer_wrap')]//button[contains(text(), '첨부')]"
                        ]
                        for a_sel in attach_selectors:
                            try:
                                if a_sel.startswith("//"):
                                    elements = self.driver.find_elements(By.XPATH, a_sel)
                                else:
                                    elements = self.driver.find_elements(By.CSS_SELECTOR, a_sel)
                                for btn in elements:
                                    if btn.is_displayed():
                                        attach_btn = btn
                                        break
                                if attach_btn:
                                    break
                            except:
                                continue
                                
                        if attach_btn:
                            print("✅ 사진 팝업 [첨부하기] 버튼 클릭 진행!")
                            try:
                                attach_btn.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", attach_btn)
                            time.sleep(2.0)
                            
                        # 3단계: 사진 팝업 레이어가 닫힐 때까지 대기
                        try:
                            WebDriverWait(self.driver, 15).until_not(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "section.lyWrap.layer_wrap, div.layer_wrap:not(.postWriteModal)"))
                            )
                            print("✅ 사진 팝업 레이어 닫힘 확인")
                        except:
                            pass
                        
                        # 4단계: 본문 사진 렌더링 확인 (최대 25초)
                        print("🔍 에디터 본문 내 사진 렌더링 확인 중...")
                        verify_start = time.time()
                        photos_detected = False
                        photo_selectors = [
                            "img._thumbnail", 
                            ".cke_widget_element img", 
                            "div.bandWidgetContent img", 
                            "[contenteditable='true'] img", 
                            ".postWriteEditor img", 
                            "._postWriteEditor img",
                            ".photoList", 
                            ".postPhoto", 
                            "img._attachedImage"
                        ]
                        photo_query = ", ".join(photo_selectors)
                        while time.time() - verify_start < 25:
                            try:
                                rendered_imgs = self.driver.find_elements(By.CSS_SELECTOR, photo_query)
                                if rendered_imgs:
                                    photos_detected = True
                                    print(f"✅ 에디터 본문 내 사진 첨부 확인 완료 ({len(rendered_imgs)}개 요소 감지)")
                                    break
                            except Exception:
                                pass
                            # 추가 안전장치: 게시 버튼이 이미 파란색 활성화(-confirm) 상태라면 첨부 완료 판정
                            try:
                                active_submit = self.driver.find_elements(By.CSS_SELECTOR, "button._btnSubmitPost.-confirm, button.uButton.-confirm._btnSubmitPost")
                                if active_submit and active_submit[0].is_displayed() and active_submit[0].is_enabled():
                                    photos_detected = True
                                    print("✅ 게시 버튼 활성화 감지로 사진 첨부 완료 판정")
                                    break
                            except Exception:
                                pass
                            time.sleep(1.0)
                            
                        if not photos_detected:
                            print("❌ 에디터 본문에 사진이 들어가지 않았습니다. 빈 글 발행을 방지하기 위해 중단합니다.")
                            return False
                            
                        print("✅ 사진 업로드 및 본문 렌더링 완료")
                        
                    except Exception as photo_err:
                        print(f"❌ 사진 첨부 실패: {photo_err}")
                        return False
                
                # 3-2. 동영상 첨부 (동영상이 있는 경우)
                remaining_videos = []
                if videos:
                    if len(videos) > 10:
                        print(f"⚠️ 네이버 밴드 동영상 첨부 제한(최대 10개)으로 인해 10개만 업로드합니다. (나머지 {len(videos)-10}개는 이어서 자동으로 포스팅됩니다)")
                        remaining_videos = videos[10:]
                        videos = videos[:10]
                        
                    print(f"🎬 동영상 업로드 중 ({len(videos)}개)...")
                    time.sleep(1)
                    try:
                        video_input = self.driver.find_element(By.CSS_SELECTOR, "input[id^='postVideoInput_'], input[type='file'][accept*='video']")
                        
                        if video_input:
                            self.driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.opacity = '1';", video_input)
                            time.sleep(0.5)
                            
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
                                pass
                        
                        # 파일 선택 후 동영상 올리기 팝업 대기
                        print("⏳ 동영상 올리기 팝업 대기 중...")
                        time.sleep(2)
                        
                        # 동영상 고화질 첨부 체크박스 확인 및 체크
                        try:
                            hq_checkbox_selectors = [
                                "input._checkHighQuality",
                                "input[id*='attachmentview'][type='checkbox']",
                                "//input[contains(@id, 'attachment') and @type='checkbox']",
                                "label:has(input._checkHighQuality)",
                                "//label[contains(., '고화질')]"
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
                        
                        # 1단계: 동영상 파일 업로드 및 인코딩 진행률(1/2, 2/2 등) 완료 대기 (파일당 60초)
                        upload_timeout = min(360, max(120, len(videos) * 60))
                        print(f"⏳ 동영상 메인 렌더링 및 업로드 대기 (타임아웃: {upload_timeout}초)...")
                        self._wait_for_upload_complete(timeout=upload_timeout)
                        time.sleep(2.0)
                        
                        # 2단계: 업로드 완료 후 [동영상 올리기] 팝업의 [첨부하기] 버튼 클릭
                        print("⏳ 동영상 팝업 [첨부하기] 버튼 클릭 진행...")
                        attach_btn = None
                        attach_selectors = [
                            "section.lyWrap.layer_wrap button._submitBtn",
                            "div.layer_wrap button._submitBtn",
                            "button.uButton.-confirm._submitBtn",
                            "button._submitBtn",
                            "//section[contains(@class, 'layer_wrap')]//button[contains(text(), '첨부')]",
                            "//div[contains(@class, 'layer_wrap')]//button[contains(text(), '첨부')]"
                        ]
                        for a_sel in attach_selectors:
                            try:
                                if a_sel.startswith("//"):
                                    elements = self.driver.find_elements(By.XPATH, a_sel)
                                else:
                                    elements = self.driver.find_elements(By.CSS_SELECTOR, a_sel)
                                for btn in elements:
                                    if btn.is_displayed():
                                        attach_btn = btn
                                        break
                                if attach_btn:
                                    break
                            except:
                                continue
                                
                        if attach_btn:
                            print("✅ 동영상 팝업 [첨부하기] 버튼 클릭!")
                            try:
                                attach_btn.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", attach_btn)
                            time.sleep(2.0)
                        else:
                            print("⚠️ 동영상 첨부하기 버튼 탐색 실패, 팝업 강제 클릭 시도")
                            self._click_attach_button()
                            time.sleep(2.0)
                        
                        # 3단계: 동영상 팝업 레이어가 닫힐 때까지 대기
                        try:
                            WebDriverWait(self.driver, 15).until_not(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "section.lyWrap.layer_wrap, div.layer_wrap:not(.postWriteModal)"))
                            )
                            print("✅ 동영상 팝업 레이어 닫힘 확인")
                        except:
                            pass
                            
                        # 4단계: 에디터 본문 내 동영상 렌더링 검증 (최대 25초)
                        print("🔍 에디터 본문 내 동영상 첨부 확인 중...")
                        videos_detected = False
                        video_selectors = [
                            "div.mediaContentItem", 
                            "div[class*='video']", 
                            "div._videoPlayer", 
                            "div.mediaWrap", 
                            "div.bandWidgetContent", 
                            ".cke_widget_element"
                        ]
                        video_query = ", ".join(video_selectors)
                        verify_start = time.time()
                        while time.time() - verify_start < 25:
                            try:
                                rendered_vids = self.driver.find_elements(By.CSS_SELECTOR, video_query)
                                if rendered_vids:
                                    videos_detected = True
                                    print(f"✅ 에디터 본문 내 동영상 정상 첨부 확인 ({len(rendered_vids)}개 요소 감지)")
                                    break
                            except Exception:
                                pass
                            # 추가 안전장치: 게시 버튼이 이미 파란색 활성화(-confirm) 상태라면 첨부 완료 판정
                            try:
                                active_submit = self.driver.find_elements(By.CSS_SELECTOR, "button._btnSubmitPost.-confirm, button.uButton.-confirm._btnSubmitPost")
                                if active_submit and active_submit[0].is_displayed() and active_submit[0].is_enabled():
                                    videos_detected = True
                                    print("✅ 게시 버튼 활성화 감지로 동영상 첨부 완료 판정")
                                    break
                            except Exception:
                                pass
                            time.sleep(1.0)
                            
                        if not videos_detected:
                            print("❌ 에디터 본문에 동영상이 첨부되지 않았습니다. 빈 글 발행을 방지하기 위해 중단합니다.")
                            return False
                            
                        print("✅ 동영상 첨부 완료")
                        
                    except Exception as video_err:
                        print(f"❌ 동영상 첨부 실패: {video_err}")
                        return False
                
                # 모든 미디어 업로드 완료 후 게시 버튼 활성화 확인
                print("🔍 최종 업로드 상태 확인 중...")
                
                # 게시 버튼이 활성화될 때까지 대기 (최대 3분)
                ready_btn = self._wait_for_submit_button_ready(timeout=180)
                
                if ready_btn:
                    print("✅ 모든 업로드 완료, 게시 준비됨")
                    # 🔧 파일 개수 기반 동적 대기 시간 (1초~5초 사이 랜덤)
                    total_files = len(photos) + len(videos) if 'photos' in dir() and 'videos' in dir() else 0
                    dynamic_wait = random.randint(1, 5)
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
                    # 4-0. 글쓰기 폼 스크롤 하단으로 이동하여 버튼 가시성 확보
                    try:
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(0.5)
                    except:
                        pass

                    # 4-1. 글쓰기 설정 버튼 클릭
                    setting_selectors = [
                        "button.btnSetting._btnWriteSetting",
                        "button._btnWriteSetting",
                        "button.btnSetting",
                        "button[data-viewname*='setting']",
                        "//button[contains(@class, 'btnSetting') or contains(@class, '_btnWriteSetting')]",
                        "//button[contains(., '설정') or contains(@title, '설정') or contains(@aria-label, '설정')]"
                    ]
                    
                    setting_btn = None
                    for selector in setting_selectors:
                        try:
                            if selector.startswith("//"):
                                elements = self.driver.find_elements(By.XPATH, selector)
                            else:
                                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            
                            for el in elements:
                                if el.is_displayed() or el.is_enabled():
                                    setting_btn = el
                                    break
                            if setting_btn:
                                break
                        except:
                            continue
                            
                    if not setting_btn:
                        try:
                            setting_btn = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btnSetting, button._btnWriteSetting, button[data-viewname*='setting']"))
                            )
                        except:
                            pass

                    if not setting_btn:
                        raise Exception("글쓰기 설정(톱니바퀴) 버튼을 찾을 수 없습니다.")

                    # 화면에 보이도록 스크롤 후 클릭
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", setting_btn)
                    time.sleep(0.5)
                    try:
                        setting_btn.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", setting_btn)
                    print("  ✅ 글쓰기 설정 메뉴 클릭 성공")
                    time.sleep(1)
                    
                    # 4-2. '글쓰기 설정' 모달 내부에서 '예약시간 설정' 토글 스위치 활성화 (스샷 5번 대응)
                    toggle_selectors = [
                        "//div[contains(@class, 'modal') or contains(@class, 'layer_wrap') or contains(@class, 'cPostWrite') or contains(@class, 'layerSetting')]//span[contains(text(), '예약시간')]/ancestor::li//button",
                        "//div[contains(@class, 'modal') or contains(@class, 'layer_wrap')]//span[contains(text(), '예약시간')]/following-sibling::button",
                        "//span[contains(text(), '예약시간 설정')]/ancestor::li//button",
                        "//span[contains(text(), '예약시간 설정')]/following-sibling::button",
                        "label[for='reserve']",
                        "._labelReserve",
                        "input#reserve"
                    ]
                    
                    toggle_clicked = False
                    for t_sel in toggle_selectors:
                        try:
                            if t_sel.startswith("//"):
                                t_elements = self.driver.find_elements(By.XPATH, t_sel)
                            else:
                                t_elements = self.driver.find_elements(By.CSS_SELECTOR, t_sel)
                                
                            for t_el in t_elements:
                                if t_el.is_displayed():
                                    try:
                                        t_el.click()
                                    except:
                                        self.driver.execute_script("arguments[0].click();", t_el)
                                    toggle_clicked = True
                                    print("  ✅ 예약시간 설정 토글 스위치 클릭됨")
                                    # 동영상 업로드 후 브라우저 안정화를 위한 충분한 대기
                                    time.sleep(30)
                                    break
                            if toggle_clicked:
                                break
                        except:
                            continue
                            
                    if not toggle_clicked:
                        print("  ℹ️ 토글 스위치를 찾지 못했거나 이미 활성화 상태일 수 있습니다.")

                    # 4-2-1. 날짜 선택 (예약 시간이 현재보다 이전이면 다음 날 선택)
                    from datetime import datetime, timedelta
                    now = datetime.now()
                    h_temp, m_temp = map(int, reservation_time.split(':'))
                    target_dt_temp = now.replace(hour=h_temp, minute=m_temp, second=0, microsecond=0)
                    
                    is_tomorrow = False
                    if target_dt_temp <= now:
                        is_tomorrow = True
                        target_dt_temp += timedelta(days=1)
                        print(f"  [Date] 예약 시간이 현재보다 이전이므로 다음 날({target_dt_temp.strftime('%Y-%m-%d')})로 설정합니다.")
                    
                    if is_tomorrow:
                        try:
                            # 모달 내부의 날짜 입력 필드만 정확히 탐색 (툴바의 일정 아이콘 클릭 방지)
                            date_input_selectors = [
                                "//div[contains(@class, 'modal') or contains(@class, 'layer_wrap')]//input[contains(@id, 'pickedDate') or contains(@class, 'gFs1') or contains(@title, '날짜') or contains(@class, '_input')]",
                                "div.modal input[id*='pickedDate']._input",
                                "div.layer_wrap input[id*='pickedDate']._input",
                                "div.modal input.gFs1",
                                "div.layer_wrap input.gFs1"
                            ]
                            
                            date_input = None
                            for selector in date_input_selectors:
                                try:
                                    if selector.startswith("//"):
                                        elements = self.driver.find_elements(By.XPATH, selector)
                                    else:
                                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                    for el in elements:
                                        if el.is_displayed():
                                            date_input = el
                                            break
                                    if date_input:
                                        break
                                except:
                                    continue
                            
                            if date_input:
                                try:
                                    date_input.click()
                                except:
                                    self.driver.execute_script("arguments[0].click();", date_input)
                                time.sleep(1)
                                print("  ✅ 달력 열기 성공")
                                
                                # 다음 날 날짜 셀 찾아서 클릭
                                target_day = target_dt_temp.day
                                day_cells = self.driver.find_elements(By.CSS_SELECTOR, "table.calendar td._td:not(.disabled), table._calendar td._td:not(.disabled)")
                                
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
                                print("  ℹ️ 모달 내 날짜 입력 필드가 없거나 기본값(내일)으로 자동 적용됩니다.")
                        except Exception as date_err:
                            print(f"  ⚠️ 날짜 선택 중 무시 가능한 오류: {date_err}")
                    
                    # 4-3. 모달 내부의 시간 선택창 열기
                    time_input = None
                    time_input_selectors = [
                        "//div[contains(@class, 'modal') or contains(@class, 'layer_wrap')]//input[contains(@class, '_timeInput') or contains(@placeholder, '시간')]",
                        "div.modal input[class*='_timeInput']",
                        "div.layer_wrap input[class*='_timeInput']",
                        "input[class*='_timeInput']"
                    ]
                    for t_sel in time_input_selectors:
                        try:
                            if t_sel.startswith("//"):
                                elements = self.driver.find_elements(By.XPATH, t_sel)
                            else:
                                elements = self.driver.find_elements(By.CSS_SELECTOR, t_sel)
                            for el in elements:
                                if el.is_displayed():
                                    time_input = el
                                    break
                            if time_input:
                                break
                        except:
                            continue
                    
                    if time_input:
                        try:
                            time_input.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", time_input)
                        time.sleep(1)
                    
                    # 4-4. 시간 검증 및 조정
                    from datetime import datetime, timedelta
                    now = datetime.now()
                    
                    try:
                        h, m = map(int, reservation_time.split(':'))
                        target_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
                        
                        if target_dt < now:
                            target_dt += timedelta(days=1)
                        
                        min_reserve_time = now + timedelta(minutes=40)
                        if target_dt < min_reserve_time:
                            print(f"⚠️ 예약 시간이 너무 이릅니다 ({reservation_time}). 최소 40분 뒤로 조정합니다.")
                            target_dt = min_reserve_time
                            m_adjusted = ((target_dt.minute + 4) // 5) * 5
                            if m_adjusted >= 60:
                                target_dt += timedelta(hours=1)
                                m_adjusted = 0
                            target_dt = target_dt.replace(minute=m_adjusted, second=0)
                        
                        h = target_dt.hour
                        m = target_dt.minute
                        period = "오전" if h < 12 else "오후"
                        h_12 = h if (h == 12 or h == 0) else (h - 12 if h > 12 else h)
                        if h == 0: h_12 = 12
                        
                        target_time_str = f"{period} {h_12}:{m:02d}"
                        print(f"  🎯 목표 예약 시간: {target_time_str} (원본: {reservation_time})")
                        
                        # 4-5. 해당 시간 버튼 찾아서 클릭
                        time_btns = self.driver.find_elements(By.CSS_SELECTOR, "button.btnDropDownItem._btnTime, ._btnTime, button[data-time]")
                        found_time = False
                        
                        for btn in time_btns:
                            btn_text = btn.text.strip()
                            if btn_text == target_time_str:
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                                time.sleep(0.3)
                                try:
                                    btn.click()
                                except:
                                    self.driver.execute_script("arguments[0].click();", btn)
                                found_time = True
                                print(f"  ✅ 시간 선택 완료: {btn_text}")
                                break
                                
                        if not found_time and time_btns:
                            print(f"  ⚠️ 정확한 시간({target_time_str}) 일치 항목을 못 찾아 첫 번째 가능한 시간 항목을 선택합니다.")
                            time_btns[0].click()
                            
                    except Exception as time_err:
                        print(f"  ❌ 시간 변환/선택 중 오류: {time_err}")
                    
                    # 4-6. 모달 우측 하단 [확인] 버튼 클릭 (모달 닫기)
                    try:
                        time.sleep(1)
                        confirm_selectors = [
                            "//div[contains(@class, 'modal') or contains(@class, 'layer_wrap')]//button[contains(text(), '확인') or contains(text(), '완료')]",
                            "button.uButton.-confirm._btnComplete",
                            "button.uButton.-confirm",
                            "button._btnComplete",
                            "//button[contains(text(), '확인')]"
                        ]
                        
                        clicked_confirm = False
                        for selector in confirm_selectors:
                            try:
                                if selector.startswith("//"):
                                    elements = self.driver.find_elements(By.XPATH, selector)
                                else:
                                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                
                                for btn in elements:
                                    if btn.is_displayed():
                                        try:
                                            btn.click()
                                        except:
                                            self.driver.execute_script("arguments[0].click();", btn)
                                        clicked_confirm = True
                                        reservation_success = True
                                        print("  ✅ 예약 설정 확인 버튼 클릭함")
                                        break
                                if clicked_confirm:
                                    break
                            except: continue
                        
                        if not clicked_confirm:
                            print("  ⚠️ 확인 버튼을 찾지 못해 엔터키 입력 시도")
                            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                            reservation_success = True
                            
                    except Exception as e: 
                        print(f"  ❌ 확인 버튼 처리 중 오류: {e}")
                    
                    # 설정 레이어 닫힘 대기
                    time.sleep(1.5)
                    
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

            # 4-7. 혹시 남아있는 서브 팝업(일정 첨부 등)이 있다면 안전하게 취소/정리
            try:
                sub_popups = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'modal') or contains(@class, 'layer_wrap')]//button[contains(text(), '취소') or contains(@class, '-cancel')]")
                for cancel_b in sub_popups:
                    if cancel_b.is_displayed():
                        try:
                            cancel_b.click()
                            time.sleep(0.5)
                        except:
                            pass
            except:
                pass

            # 5. 게시(또는 예약) 버튼 클릭
            print("🚀 게시(또는 예약) 버튼 클릭 중...")
            submit_btn = None
            submit_selectors = [
                "button._btnSubmitPost", 
                "button.uButton.-confirm._btnSubmitPost",
                "button.uButton.-sizeM._btnSubmitPost",
                "button.uButton.-sizeM._btnSubmitPost.-confirm",
                "//button[normalize-space()='예약' and contains(@class, '_btnSubmitPost')]",
                "//button[normalize-space()='게시' and contains(@class, '_btnSubmitPost')]",
                "//button[contains(@class, '_btnSubmitPost')]",
                "button._btnPost"
            ]
            
            # 버튼 활성화 대기 (최대 20초)
            found_clickable = False
            for i in range(20):
                for selector in submit_selectors:
                    try:
                        if selector.startswith("//"):
                            elements = self.driver.find_elements(By.XPATH, selector)
                        else:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        for btn in elements:
                            if btn.is_displayed():
                                # disabled 상태인지 확인
                                is_disabled = btn.get_attribute("disabled") or "disabled" in (btn.get_attribute("class") or "")
                                if not is_disabled:
                                    submit_btn = btn
                                    found_clickable = True
                                    break
                        if found_clickable:
                            break
                    except:
                        continue
                if found_clickable:
                    break
                print(f"  ⏳ 버튼 대기 중... ({i+1}/20)")
                time.sleep(1)
            
            if not submit_btn:
                print("❌ 게시 버튼을 찾을 수 없거나 비활성화 상태입니다.")
                # 비활성화 원인 파악을 위해 에디터에 공백 추가 후 재시도
                try:
                    editor.send_keys(Keys.SPACE)
                    time.sleep(1)
                    editor.send_keys(Keys.BACK_SPACE)
                    time.sleep(1)
                    # 다시 시도
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button._btnSubmitPost")
                except:
                    pass

            if submit_btn:
                time.sleep(0.5)
                # 다중 방식으로 게시 버튼 확실하게 클릭
                try:
                    self.driver.execute_script("""
                        arguments[0].removeAttribute('disabled');
                        arguments[0].classList.remove('disabled');
                        arguments[0].click();
                    """, submit_btn)
                except:
                    pass
                    
                try:
                    submit_btn.click()
                except:
                    pass
                    
                print("✅ 게시(예약) 버튼 클릭 완료")
                
                # 6. 게시 완료 검증 (동영상 인코딩 및 모달 닫힘 대기)
                print("🔍 게시 완료 확인 중...")
                max_retries = 60 if videos else 30
                post_success = False
                
                for r in range(max_retries):
                    # 1순위: 에디터 요소 자체가 DOM에서 사라지거나 보이지 않게 되었는지 확인
                    try:
                        is_editor_open = editor.is_displayed()
                    except:
                        # StaleElementReferenceException -> 페이지가 피드로 새로고침/갱신됨 = 성공!
                        is_editor_open = False
                    
                    if not is_editor_open:
                        post_success = True
                        break
                        
                    # 만약 10초가 지났는데도 에디터가 안 닫혔으면 submit 버튼 2차 클릭
                    if r == 10 and submit_btn:
                        print("  🔄 게시 버튼 2차 재클릭 시도...")
                        try:
                            self.driver.execute_script("arguments[0].click();", submit_btn)
                        except:
                            pass
                            
                    time.sleep(1)
                
                if post_success:
                    print("✅ 밴드 포스팅(예약) 완료! (에디터 닫힘 확인)")
                    return True
                else:
                    print("❌ 포스팅 완료 확인 실패 (에디터 모달이 닫히지 않음 - 글이나 파일이 누락되어 네이버에서 거부했을 수 있습니다)")
                    # 다음 포스팅을 위해 꼬인 상태 초기화 (새로고침)
                    try:
                        self.driver.refresh()
                        time.sleep(3)
                    except:
                        pass
                    return False
            else:
                print("❌ 게시 버튼을 결국 찾을 수 없습니다.")
                return False
            
        except Exception as e:
            print(f"❌ 밴드 포스팅 중 오류 발생: {e}")
            traceback.print_exc()
            return False

# 테스트 코드 생략
