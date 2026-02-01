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
        
    def post_to_cafe(self, cafe_url: str, menu_id: str, title: str, content: str, image_paths: list = None):
        """
        네이버 카페에 글을 게시합니다.
        
        Args:
            cafe_url: 카페 기본 URL (예: https://cafe.naver.com/mycafe)
            menu_id: 게시판 메뉴 ID
            title: 게시글 제목
            content: 게시글 내용
            image_paths: 업로드할 이미지 경로 리스트 (옵션)
        """
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
            
            # 3. 내용 입력 (스마트에디터 ONE 대응 - 다중 폴백)
            print("⌨️ 내용 입력 중 (다중 폴백)...")
            
            # 먼저 에디터 영역 찾기
            editor_area = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".se-content, .Editor_content__container, .se-viewer, [contenteditable='true']"))
            )
            editor_area.click()
            time.sleep(1)
            
            # 기존 내용 삭제 (Cmd+A -> Backspace)
            ActionChains(self.driver).key_down(Keys.COMMAND).send_keys('a').key_up(Keys.COMMAND).send_keys(Keys.BACKSPACE).perform()
            time.sleep(0.5)
            
            # 방법 1: 클립보드 헬퍼 사용 시도
            insert_success = False
            try:
                from utils.clipboard_helper import insert_text_to_editor
                insert_success = insert_text_to_editor(self.driver, editor_area, content, platform="cafe")
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
                            editor_text = editor_area.text.strip() if editor_area.text else ""
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
                        const editor = arguments[0];
                        const content = arguments[1];
                        if(editor) {
                            editor.innerHTML = content.split('\\n').map(line => `<p style="font-size:19px !important;">${line || '&nbsp;'}</p>`).join('');
                            editor.focus();
                            editor.dispatchEvent(new Event('input', { bubbles: true }));
                            editor.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    """, editor_area, content)
                    time.sleep(0.5)
                    editor_text = editor_area.text.strip() if editor_area.text else ""
                    if len(editor_text) >= len(content) * 0.2:
                        insert_success = True
                        print(f"✅ JS 주입 성공 ({len(editor_text)}자)")
                except Exception as js_err:
                    print(f"⚠️ JS 주입 실패: {js_err}")
            
            # 방법 4: send_keys 직접 입력 (최후의 수단)
            if not insert_success:
                print("🔄 [Fallback] send_keys 직접 입력...")
                try:
                    # 너무 긴 텍스트는 잘라서 처리
                    text_to_send = content[:2000] if len(content) > 2000 else content
                    editor_area.send_keys(text_to_send)
                    time.sleep(1)
                    print(f"✅ send_keys 완료 ({len(text_to_send)}자)")
                    insert_success = True
                except Exception as sk_err:
                    print(f"❌ send_keys 실패: {sk_err}")
            
            # 글자 크기 19px로 조정
            if insert_success:
                self.driver.execute_script("""
                    const editor = document.querySelector('.se-content') || document.querySelector('.Editor_content__container') || document.querySelector('.se-viewer') || document.querySelector('[contenteditable="true"]');
                    if(editor) {
                        const paragraphs = editor.querySelectorAll('p, span, div');
                        paragraphs.forEach(p => {
                            p.style.setProperty('font-size', '19px', 'important');
                        });
                    }
                """)
            else:
                print("❌ 모든 내용 입력 방법 실패")
            
            time.sleep(2)
            
            # 3.5 이미지 업로드 (이미지 경로가 있는 경우)
            if image_paths and len(image_paths) > 0:
                print(f"🖼️ 이미지 업로드 중 ({len(image_paths)}개)...")
                try:
                    # 1. 먼저 기존의 파일 입력 필드 탐색 및 활성화
                    file_input = self.driver.execute_script("""
                        function findFileInput() {
                            return document.querySelector('input[type="file"][accept*="image"]') || 
                                   document.querySelector('input[type="file"].se-ff-file-input') || 
                                   document.querySelector('.Editor_footer__button_image input') ||
                                   document.querySelector('input.image_upload_input') ||
                                   document.querySelector('input[type="file"]');
                        }
                        
                        let input = findFileInput();
                        
                        // 만약 입력 필드가 없다면 사진 버튼을 한번 클릭해서 생성 시도 (시스템 창 방지 위해 클릭 후 즉시 리턴)
                        if (!input) {
                            let imgBtn = document.querySelector('button.se-image-toolbar-button') || 
                                         document.querySelector('button[title*="사진"]') || 
                                         document.querySelector('button[title*="이미지"]') ||
                                         document.querySelector('.Editor_footer__button_image button');
                            if (imgBtn) {
                                // 직접 클릭하면 시스템 창이 뜰 수 있으므로, 해당 버튼의 연결된 input이 있는지 혹은 이벤트를 통해 생성되는지 확인
                                // 여기서는 일반적인 방식으로는 버튼을 눌러야 생성되기도 함
                            }
                        }
                        
                        if (input) {
                            input.style.display = 'block';
                            input.style.visibility = 'visible';
                            input.style.opacity = '1';
                            input.style.position = 'fixed';
                            input.style.top = '0';
                            input.style.left = '0';
                            input.style.width = '100px';
                            input.style.height = '100px';
                            input.style.zIndex = '9999';
                        }
                        return input;
                    """)
                    
                    if not file_input:
                        print("ℹ️ 파일 필드를 찾지 못해 사진 버튼 클릭 시도...")
                        try:
                            # 텍스트나 타이틀로 사진 버튼 찾기
                            img_btn = self.driver.find_element(By.CSS_SELECTOR, "button.se-image-toolbar-button, button[title*='사진'], .Editor_footer__button_image button")
                            img_btn.click()
                            time.sleep(1)
                            file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                        except: pass
                    
                    if file_input:
                        file_input.send_keys("\n".join(image_paths))
                        print("📤 이미지 파일 전송 완료. 팝업 대기...")
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
                        except Exception as pop_err:
                            print(f"ℹ️ 사진 첨부 방식 팝업이 표시되지 않았거나 자동으로 넘어갔습니다.")

                        time.sleep(min(15, len(image_paths) * 2))  # 업로드 대기
                        print("✅ 이미지 업로드 프로세스 완료")
                    else:
                        print("⚠️ 이미지 업로드 요소를 찾을 수 없습니다.")
                except Exception as img_err:
                    print(f"⚠️ 이미지 업로드 실패: {img_err}")
            
            # 4. 등록 버튼 클릭
            print("🚀 등록 버튼 클릭 시도...")
            time.sleep(2)
            
            # 팝업 알림이 뜨는 경우 확인 (예: "내용을 입력하세요" 혹은 다른 확인창)
            try:
                alert = self.driver.switch_to.alert
                print(f"🔔 브라우저 알림 발견: {alert.text}")
                alert.accept()
                time.sleep(1)
            except:
                pass

            submit_selectors = [
                "a.BaseButton--skinGreen", # 사용자 스크린샷 기반 (초록색 등록 버튼)
                "button.BaseButton.btn_complete", 
                "button.Editor_footer__button_publish", 
                "a.BaseButton[role='button']",
                ".publish_btn", 
                "button.BaseButton.type_filled:not(.btn_save)"
            ]
            
            for selector in submit_selectors:
                try:
                    btns = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in btns:
                        btn_text = btn.text.strip()
                        if btn.is_displayed() and "등록" in btn_text and "임시" not in btn_text:
                            submit_btn = btn
                            print(f"✅ 버튼 발견 (CSS): {selector} -> {btn_text}")
                            break
                    if submit_btn: break
                except: continue
                
            # 2. XPATH로 '등록' 글자가 포함된 모든 요소(button, a) 찾기
            if not submit_btn:
                try:
                    # '등록' 텍스트를 포함하는 모든 클릭 가능한 요소 탐색
                    xpath_selectors = [
                        "//a[@role='button'][contains(., '등록')]",
                        "//button[contains(., '등록')]",
                        "//span[text()='등록']/ancestor::a",
                        "//span[text()='등록']/ancestor::button"
                    ]
                    for xpath in xpath_selectors:
                        btns = self.driver.find_elements(By.XPATH, xpath)
                        for btn in btns:
                            btn_text = btn.text.strip()
                            if btn.is_displayed() and "임시" not in btn_text:
                                submit_btn = btn
                                print(f"✅ 버튼 발견 (XPATH): {xpath} -> {btn_text}")
                                break
                        if submit_btn: break
                except: pass
            
            if submit_btn:
                # 일반 클릭 시도 후 실패 시 JS 클릭
                try:
                    # 클릭 전 잠시 대기
                    time.sleep(1)
                    submit_btn.click()
                except:
                    self.driver.execute_script("arguments[0].click();", submit_btn)
                print("🚀 등록 버튼 클릭 완료")
            else:
                print("❌ 등록 버튼을 찾을 수 없습니다.")
            
            time.sleep(5)
            # 완료 후 게시글 페이지로 이동했는지 확인 (성공 판단)
            if "write" not in self.driver.current_url:
                print("✅ 카페 포스팅 성공 및 페이지 전환 확인!")
                return True
            else:
                print("⚠️ 포스팅 버튼을 눌렀으나 여전히 작문 페이지입니다. (수동 등록이 필요할 수 있습니다)")
                return False
            
            time.sleep(5)
            # 완료 후 게시글 페이지로 이동했는지 확인 (성공 판단)
            if "write" not in self.driver.current_url:
                print("✅ 카페 포스팅 성공 및 페이지 전환 확인!")
                return True
            else:
                print("⚠️ 포스팅 버튼을 눌렀으나 여전히 작문 페이지입니다.")
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
