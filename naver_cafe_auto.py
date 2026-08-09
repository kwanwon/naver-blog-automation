import time
import os
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# pyperclip은 clipboard_helper에서 관리 (빌드 호환성을 위해 상단 import 제거)
from selenium.webdriver.common.action_chains import ActionChains

class NaverCafeAutomation:
    def __init__(self, driver):
        self.driver = driver
        
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
            file_input = self.driver.execute_script("""
                var el = window.__fileInputIntercepted;
                if (el && !el.parentNode) {
                    document.body.appendChild(el);
                }
                return el;
            """)
            if file_input:
                break
            import time
            time.sleep(0.3)
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
            if (!el.parentNode) {
                document.body.appendChild(el);
            }
            el.style.display = 'block';
            el.style.visibility = 'visible';
            el.style.opacity = '1';
            el.style.width = '1px';
            el.style.height = '1px';
            el.style.position = 'absolute';
            el.style.top = '0';
            el.style.left = '0';
        """, file_input)
        import time
        time.sleep(0.1)
        file_input.send_keys(file_path)
        
    def post_to_cafe(self, cafe_url: str, menu_id: str, title: str, content: str, image_paths: list = None):
        """
        네이버 카페에 글을 게시합니다. (이미지가 10장 초과 시 자동 분할 포스팅 지원)
        """
        if not image_paths or len(image_paths) <= 10:
            return self._do_single_post(cafe_url, menu_id, title, content, image_paths)
            
        print(f"ℹ️ 업로드할 이미지가 {len(image_paths)}장입니다. 10장 단위로 분할하여 포스팅합니다.")
        chunk_size = 10
        chunks = [image_paths[i:i + chunk_size] for i in range(0, len(image_paths), chunk_size)]
        
        success = True
        for idx, chunk in enumerate(chunks):
            current_title = title if idx == 0 else f"{title} (이어지는 사진 {idx+1})"
            current_content = content if idx == 0 else f"이전 게시글에 이어지는 사진입니다."
            
            print(f"🚀 [Cafe] 파트 {idx+1}/{len(chunks)} 포스팅 중... (이미지 {len(chunk)}장)")
            res = self._do_single_post(cafe_url, menu_id, current_title, current_content, chunk)
            if not res:
                print(f"❌ [Cafe] 파트 {idx+1} 포스팅 실패.")
                success = False
                break
                
            if idx < len(chunks) - 1:
                print("⏳ 연속 포스팅 방지를 위해 10초 대기...")
                time.sleep(10)
                
        return success

    def _do_single_post(self, cafe_url: str, menu_id: str, title: str, content: str, image_paths: list = None):
        try:
            # 0. clubid 추출
            club_id = self._get_club_id(cafe_url)
            if not club_id:
                print("❌ 카페 ID(clubid)를 찾을 수 없습니다.")
                return False

            # 1. 카페 글쓰기 페이지로 직접 이동 (새로운 URL 형식 지원)
            write_url = f"https://cafe.naver.com/ca-fe/cafes/{club_id}/menus/{menu_id}/articles/write"
            print(f"🌐 카페 글쓰기 페이지로 이동 중: {write_url}")
            self.driver.get(write_url)
            time.sleep(5)
            
            # 🟢 새로운 에디터는 iFrame이 없습니다 (ca-fe URL 기준)
            # 만약 구버전 URL인 경우에만 iFrame 전환 시도
            if "ca-fe" not in write_url:
                try:
                    if "cafe_main" in self.driver.page_source:
                        self.driver.switch_to.frame("cafe_main")
                        print("🔲 cafe_main 프레임 전환 완료 (구버전)")
                except:
                    pass
            
            # 2. 제목 입력
            print("⌨️ 제목 입력 중...")
            try:
                title_input = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "textarea.Editor_title__textarea, input.input_title, textarea.textarea_input"))
                )
                title_input.click()
                time.sleep(0.5)
                # JS를 사용하여 제목 입력 (기존 내용 제거 및 확실한 입력)
                self.driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", title_input, title)
                # 혹시 모르니 send_keys 한 번 더 (이벤트 발생용)
                title_input.send_keys(Keys.SPACE)
                title_input.send_keys(Keys.BACKSPACE)
            except Exception as e:
                print(f"⚠️ 제목 JS 입력 실패, 일반 입력 시도: {e}")
                title_input.send_keys(title)
            time.sleep(1)
            
            # 3. 내용 입력 (스마트에디터 ONE - 키보드 직접 입력만 사용!)
            # 중요: React 기반 에디터는 클립보드/JS 삽입으로 상태 인식 불가
            # 따라서 send_keys 키보드 입력만 사용 (pyautogui는 한글 미지원)
            print("⌨️ 내용 입력 중 (send_keys 전용)...")
            
            # 에디터 영역 찾기
            editor_selectors = [
                ".se-component-content .se-text-paragraph",  # 스마트에디터 ONE 본문
                ".se-content",
                ".Editor_content__container", 
                ".se-viewer",
                "[contenteditable='true']",
                ".se-text-paragraph"
            ]
            
            editor_area = None
            for selector in editor_selectors:
                try:
                    editor_area = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if editor_area:
                        print(f"✅ 에디터 발견: {selector}")
                        break
                except:
                    continue
            
            if not editor_area:
                print("❌ 에디터 영역을 찾을 수 없습니다.")
                return False
            
            # 에디터 클릭 및 포커스
            editor_area.click()
            time.sleep(1)
            
            # 기존 내용 삭제 (Cmd+A -> Backspace)
            ActionChains(self.driver).key_down(Keys.COMMAND).send_keys('a').key_up(Keys.COMMAND).send_keys(Keys.BACKSPACE).perform()
            time.sleep(0.5)
            
            # === 핵심: send_keys 분할 입력 (유일한 방법) ===
            print("⌨️ send_keys 분할 입력 시작...")
            insert_success = False
            
            try:
                # 다시 에디터 클릭 (포커스 확인)
                editor_area.click()
                time.sleep(0.3)
                
                # 줄 단위로 입력
                lines = content.split('\n')
                total_lines = len(lines)
                
                for i, line in enumerate(lines):
                    # 진행 상황 표시 (10줄마다)
                    if i % 10 == 0:
                        print(f"  📝 입력 중... {i}/{total_lines}줄")
                    
                    if line.strip():
                        # 300자씩 나누어 입력 (더 안정적)
                        chunks = [line[j:j+300] for j in range(0, len(line), 300)]
                        for chunk in chunks:
                            ActionChains(self.driver).send_keys(chunk).perform()
                            time.sleep(0.03)  # 청크 사이 대기
                    
                    # 마지막 줄이 아니면 Enter
                    if i < len(lines) - 1:
                        ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                        time.sleep(0.01)
                
                time.sleep(0.5)
                
                # 검증
                editor_text = editor_area.text.strip() if editor_area.text else ""
                if len(editor_text) >= len(content) * 0.2:
                    insert_success = True
                    print(f"✅ send_keys 입력 완료 ({len(editor_text)}자 / 원본 {len(content)}자)")
                else:
                    print(f"⚠️ 입력 후 검증 실패 (확인된 글자: {len(editor_text)}자)")
                    # 검증 실패해도 일단 진행 (에디터 텍스트 추출이 불완전할 수 있음)
                    if len(editor_text) > 0:
                        insert_success = True
                        print("⚠️ 내용이 일부 입력됨, 계속 진행...")
                        
            except Exception as e:
                print(f"❌ send_keys 입력 오류: {e}")
                import traceback
                traceback.print_exc()
            
            if not insert_success:
                print("❌ 내용 입력 실패 - 포스팅 중단")
                return False
            
            # 글자 크기 조정 및 가운데 정렬 시도
            try:
                # 텍스트 전체 선택 (정렬을 위해)
                editor_area.click()
                time.sleep(0.2)
                ActionChains(self.driver).key_down(Keys.COMMAND).send_keys('a').key_up(Keys.COMMAND).perform()
                time.sleep(0.5)
                
                # 정렬 드롭다운이 닫혀있다면 열기 (스마트에디터 버전에 따라 다름)
                self.driver.execute_script("""
                    const dropdown = document.querySelector('button[title*="정렬"], .se-toolbar-option-align-justify-button, .se-toolbar-option-align-left-button');
                    if (dropdown && !document.querySelector('button.se-toolbar-option-align-center-button')) {
                        dropdown.click();
                    }
                """)
                time.sleep(0.5)
                
                # 가운데 정렬 버튼 클릭
                self.driver.execute_script("""
                    const centerBtn = document.querySelector('button.se-toolbar-option-align-center-button') || 
                                      document.querySelector('button[data-value="center"]');
                    if (centerBtn) {
                        centerBtn.click();
                    }
                """)
                time.sleep(0.5)
                
                # 폰트 크기 변경 (보조 수단)
                self.driver.execute_script("""
                    const editor = document.querySelector('.se-content') || 
                                   document.querySelector('.Editor_content__container') ||
                                   document.querySelector('[contenteditable="true"]');
                    if(editor) {
                        const paragraphs = editor.querySelectorAll('p, span, div');
                        paragraphs.forEach(p => {
                            p.style.setProperty('font-size', '19px', 'important');
                            p.style.setProperty('text-align', 'center', 'important');
                        });
                    }
                """)
                
                # 선택 해제 (오른쪽 화살표 키)
                ActionChains(self.driver).send_keys(Keys.ARROW_RIGHT).perform()
                time.sleep(0.5)
            except Exception as align_e:
                print(f"⚠️ 텍스트 서식 적용 중 오류: {align_e}")

            
            time.sleep(1)
            
            # 3.5 이미지 업로드 (이미지 경로가 있는 경우)
            if image_paths and len(image_paths) > 0:
                print(f"🖼️ 이미지 업로드 중 ({len(image_paths)}개)...")
                try:
                    # 1. 가로채기 설정 (Finder 열림 방지)
                    self._intercept_file_input()
                    
                    # 2. 사진 버튼 클릭 (시스템 창 열리지 않고 가로채짐)
                    print("ℹ️ 사진 버튼 클릭 (Finder 없이 모드 시도)...")
                    try:
                        img_btn = self.driver.find_element(By.CSS_SELECTOR, "button.se-image-toolbar-button, button[title*='사진'], .Editor_footer__button_image button")
                        img_btn.click()
                    except:
                        self.driver.execute_script("document.querySelector('button.se-image-toolbar-button, button[title*=\"사진\"], .Editor_footer__button_image button')?.click();")
                    time.sleep(0.5)
                    
                    # 3. 가로챈 input 획득
                    file_input = self._get_intercepted_input()
                    
                    if not file_input:
                        print("⚠️ 가로채기 실패, DOM에서 직접 검색...")
                        inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
                        if inputs:
                            file_input = inputs[-1]
                            
                    if file_input:
                        import os
                        abs_paths = [os.path.abspath(p) for p in image_paths]
                        self._send_file_to_input(file_input, "\n".join(abs_paths))
                        print(f"✅ 이미지 파일 전송 성공 (Finder 없이)")
                        time.sleep(3)
                        
                        # 📸 사진 첨부 방식 팝업 처리
                        try:
                            # 팝업이 나타날 때까지 대기
                            WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '사진 첨부 방식')]"))
                            )
                            print("✨ 사진 첨부 방식 팝업 감지됨. '개별사진' 선택 중...")
                            
                            # 여러 벌의 셀렉터로 '개별사진' 클릭 시도
                            click_success = False
                            selectors = [
                                "//button[contains(., '개별사진')]",
                                "//li[contains(., '개별사진')]",
                                "//span[contains(text(), '개별사진')]/ancestor::button",
                                "//div[contains(@class, 'individual')]//button"
                            ]
                            
                            for sel in selectors:
                                try:
                                    target = self.driver.find_element(By.XPATH, sel)
                                    if target.is_displayed():
                                        self.driver.execute_script("arguments[0].click();", target)
                                        click_success = True
                                        print(f"✅ '개별사진' 선택 완료 (Selector: {sel})")
                                        break
                                except: continue
                                
                            if not click_success:
                                # 텍스트 기반으로 모든 요소를 뒤져서 클릭
                                self.driver.execute_script("""
                                    const elements = document.querySelectorAll('button, li, span, div, strong');
                                    for (const el of elements) {
                                        if (el.innerText.includes('개별사진')) {
                                            el.click();
                                            return true;
                                        }
                                    }
                                    return false;
                                """)
                                
                            time.sleep(0.5)
                            
                            # 📸 '확인' 버튼 클릭하여 팝업 닫기 (매우 중요: 안 닫으면 등록 버튼 안 눌림)
                            self.driver.execute_script("""
                                const confirmBtns = Array.from(document.querySelectorAll('button'));
                                const confirmTarget = confirmBtns.find(b => 
                                    b.offsetParent !== null && 
                                    (b.innerText.includes('확인') || b.innerText.includes('적용'))
                                );
                                if(confirmTarget) {
                                    confirmTarget.click();
                                }
                            """)
                            print("✅ '개별사진' 확인 버튼 클릭 완료")
                            
                        except Exception as pop_err:
                            print(f"ℹ️ 사진 첨부 방식 팝업이 표시되지 않았거나 자동으로 넘어갔습니다.")

                        time.sleep(min(15, len(image_paths) * 2))  # 업로드 대기
                        print("✅ 이미지 업로드 프로세스 완료")
                    else:
                        print("⚠️ 이미지 업로드 요소를 찾을 수 없습니다.")
                        
                    # 이미지 업로드 후 React 상태 업데이트를 위해 에디터에 강제 이벤트 발생
                    try:
                        print("ℹ️ 이미지 업로드 후 에디터 상태 갱신 중...")
                        self.driver.execute_script("""
                            const editor = document.querySelector('.se-main-container, .se-content, [contenteditable="true"]');
                            if(editor) {
                                editor.focus();
                                const inputEvent = new Event('input', { bubbles: true });
                                editor.dispatchEvent(inputEvent);
                                const keyupEvent = new KeyboardEvent('keyup', { bubbles: true, key: ' ' });
                                editor.dispatchEvent(keyupEvent);
                            }
                        """)
                        time.sleep(1)
                    except Exception as e:
                        print(f"⚠️ 에디터 상태 갱신 실패 (무시됨): {e}")
                        
                except Exception as img_err:
                    print(f"⚠️ 이미지 업로드 실패: {img_err}")
            
            # 4. 등록 버튼 클릭 및 검증 루프 (최대 5회 시도)
            print("🚀 등록 버튼 클릭 시도...")
            success_post = False
            for attempt in range(5):
                submit_btn = None
                try:
                    # 상단/하단 등록 버튼 모두 검색
                    xpath_candidates = [
                        "//a[contains(@class, 'BaseButton--skinGreen') and contains(text(), '등록')]",
                        "//button[contains(@class, 'BaseButton--skinGreen') and contains(text(), '등록')]",
                        "//a[contains(text(), '등록')]",
                        "//button[contains(text(), '등록')]"
                    ]
                    for xpath in xpath_candidates:
                        try:
                            btns = self.driver.find_elements(By.XPATH, xpath)
                            for btn in btns:
                                btn_text = btn.text.strip()
                                if btn.is_displayed() and "임시" not in btn_text:
                                    submit_btn = btn
                                    break
                        except: pass
                        if submit_btn: break
                except: pass
                
                if submit_btn:
                    try:
                        self.driver.execute_script("""
                            arguments[0].removeAttribute('disabled');
                            arguments[0].removeAttribute('aria-disabled');
                            arguments[0].classList.remove('disabled');
                            arguments[0].scrollIntoView({block: 'center'});
                        """, submit_btn)
                        time.sleep(0.5)
                        
                        # 강력한 JS 이벤트 트리거 (React 감지 우회)
                        self.driver.execute_script("""
                            var el = arguments[0];
                            var ev1 = new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window});
                            var ev2 = new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window});
                            var ev3 = new MouseEvent('click', {bubbles: true, cancelable: true, view: window});
                            el.dispatchEvent(ev1);
                            el.dispatchEvent(ev2);
                            el.dispatchEvent(ev3);
                        """, submit_btn)
                        
                        # Fallback click
                        submit_btn.click()
                        print(f"🚀 등록 버튼 클릭 완료 (시도 {attempt+1}/5)")
                    except Exception as e:
                        pass
                else:
                    print(f"⚠️ 요소를 찾지 못했습니다. JS 강제 클릭 (시도 {attempt+1}/5)")
                    try:
                        self.driver.execute_script("""
                            const btns = Array.from(document.querySelectorAll('button, a'));
                            const target = btns.find(b => 
                                (b.innerText && b.innerText.includes('등록') && !b.innerText.includes('임시')) || 
                                b.classList.contains('BaseButton--skinGreen')
                            );
                            if(target) {
                                target.removeAttribute('disabled');
                                target.removeAttribute('aria-disabled');
                                target.classList.remove('disabled');
                                target.click();
                            }
                        """)
                    except: pass
                
                time.sleep(4)
                
                # 등록 후 팝업(경고창)이 뜨는지 확인
                try:
                    alert = self.driver.switch_to.alert
                    print(f"⚠️ 등록 중 알림 발생: {alert.text}")
                    alert.accept()
                    time.sleep(2)
                except: pass
                
                # 완료 후 게시글 페이지로 이동했는지 확인
                if "write" not in self.driver.current_url:
                    print("✅ 카페 포스팅 성공 및 페이지 전환 확인!")
                    success_post = True
                    break
                else:
                    print(f"⏳ 페이지 전환 대기 중... (현재 URL: {self.driver.current_url})")
            
            if success_post:
                return True
            else:
                print("⚠️ 5회 클릭 시도에도 작문 페이지를 벗어나지 못했습니다. (수동 등록 필요)")
                return False
                
        except Exception as e:
            print(f"❌ 카페 포스팅 중 오류 발생: {e}")
            traceback.print_exc()
            return False

    def _get_club_id(self, cafe_url):
        """카페 URL에서 clubid를 추출하거나 메타 태그에서 찾음"""
        try:
            print(f"🔍 카페 정보를 가져오는 중: {cafe_url}")
            self.driver.get(cafe_url)
            time.sleep(2)
            
            # 페이지 소스에서 g_sClubId 변수 검색
            page_source = self.driver.page_source
            import re
            
            # 패턴 1: g_sClubId = "12345678"
            match = re.search(r"g_sClubId\s*=\s*['\"](\d+)['\"]", page_source)
            if match:
                club_id = match.group(1)
                print(f"🎯 Club ID 발견 (Pattern 1): {club_id}")
                return club_id
                
            # 패턴 2: URL에 포함된 경우
            match = re.search(r"clubid=(\d+)", self.driver.current_url)
            if match:
                print(f"🎯 Club ID 발견 (Pattern 2): {match.group(1)}")
                return match.group(1)
                
            print("⚠️ Club ID를 자동으로 찾지 못했습니다.")
            return None
        except Exception as e:
            print(f"❌ Club ID 추출 실패: {e}")
            return None
