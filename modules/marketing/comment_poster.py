import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class CommentPoster:
    def __init__(self, driver):
        self.driver = driver

    def post_comment(self, url, comment_text, platform='blog'):
        """
        Navigates to the post and submits a comment based on platform.
        Returns (success, message).
        """
        # Remove non-BMP characters (emojis) to prevent ChromeDriver crash
        comment_text = self._remove_non_bmp(comment_text)

        try:
            print(f"🚀 [CommentPoster] 이동 중 ({platform}): {url}")
            self.driver.get(url)
            time.sleep(random.uniform(2, 4)) # Wait for page load
            
            if platform == 'blog':
                return self._post_blog_comment(comment_text)
            elif platform == 'cafe':
                return self._post_cafe_comment(comment_text)
            elif platform == 'band':
                return self._post_band_comment(comment_text)
            else:
                return self._post_blog_comment(comment_text) # Default

        except Exception as e:
            print(f"❌ [CommentPoster] 작성 중 오류: {e}")
            return False, f"댓글 작성 중 오류: {str(e)}"

    def _post_blog_comment(self, comment_text):
        # Switch to main iframe if it exists
        try:
            self.driver.switch_to.frame("mainFrame")
            print("✅ [CommentPoster] iframe 전환 성공")
        except:
            pass 

        # Find the comment button/area
        print("🔍 [CommentPoster] 댓글 버튼 찾는 중...")
        
        comment_btn = None
        try:
            # Try finding by class names common in Naver Blog
            comment_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn_comment, a.btn_reply, div.area_comment a"))
            )
        except:
            # Fallback to xpath searching for text
            try:
                comment_btn = self.driver.find_element(By.XPATH, "//a[contains(., '댓글')]")
            except:
                pass

        # Try to find input area (div contenteditable or textarea)
        text_area = None
        try:
            text_area = self.driver.find_element(By.CSS_SELECTOR, "div.u_cbox_text[contenteditable='true'], textarea.u_cbox_text")
            print("✅ [CommentPoster] 입력창이 이미 열려있습니다.")
        except:
            # If not found, click the button
            if comment_btn:
                try:
                    # JS Click to bypass overlays
                    self.driver.execute_script("arguments[0].click();", comment_btn)
                    print("✅ [CommentPoster] 댓글 버튼 클릭(JS)")
                    time.sleep(random.uniform(1, 2))
                except Exception as e:
                    print(f"Error clicking comment button: {e}")

        # Now look for the input text area again
        if not text_area:
            print("🔍 [CommentPoster] 입력창 찾는 중...")
            try:
                text_area = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.u_cbox_text[contenteditable='true'], textarea.u_cbox_text"))
                )
            except TimeoutException:
                # Retry click if text area not found
                print("⚠️ [CommentPoster] 입력창 미발견 -> 버튼 재클릭 시도")
                if comment_btn:
                        try:
                            comment_btn.click() # Standard click retry
                            print("✅ [CommentPoster] 댓글 버튼 재클릭(Standard)")
                            time.sleep(1)
                        except:
                            self.driver.execute_script("arguments[0].click();", comment_btn)
                
                try:
                    text_area = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.u_cbox_text[contenteditable='true'], textarea.u_cbox_text"))
                    )
                except:
                    return False, "댓글 입력창을 찾을 수 없습니다."

        return self._fill_and_submit(text_area, comment_text, "button.u_cbox_btn_upload, a.u_cbox_btn_upload")

    def _post_cafe_comment(self, comment_text):
        # Switch to cafe_main iframe if it exists
        try:
            self.driver.switch_to.default_content() # Reset frame first
            WebDriverWait(self.driver, 3).until(EC.frame_to_be_available_and_switch_to_it("cafe_main"))
            print("✅ [CommentPoster] cafe_main 프레임 전환 성공")
        except:
            print("⚠️ [CommentPoster] cafe_main 프레임 전환 실패 (본문이 iFrame이 아닐 수 있음)")
            pass
            
        # Check for membership/permission barriers common in Naver Cafe
        try:
            # Check for "Join" button or "Level Up" messages if feasible
            pass
        except:
            pass

        # Try to find input area
        text_area = None
        try:
            text_area = WebDriverWait(self.driver, 4).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea.comment_inbox_text, div.comment_inbox_text"))
            )
            
            # Check if text_area is disabled or has specific placeholder indicating no permission
            # e.g. "멤버만 작성할 수 있습니다."
            placeholder = text_area.get_attribute("placeholder")
            if placeholder and ("가입" in placeholder or "멤버" in placeholder or "권한" in placeholder or "등업" in placeholder):
                 msg = f"댓글 작성 권한 없음: {placeholder}"
                 print(f"❌ [CommentPoster] 실패: {msg}")
                 return False, msg

        except:
            # If text area is not found, likely not a member or restricted post
            msg = "댓글 입력창 미발견 (카페 가입 또는 등업 필요 예상)"
            print(f"❌ [CommentPoster] 실패: {msg}")
            return False, msg
            
        return self._fill_and_submit(text_area, comment_text, "a.btn_register, button.btn_register", is_cafe=True)

    def _post_band_comment(self, comment_text):
        # Band is strict SPA, no iframes usually but logic is tricky
        try:
            # Input area
            text_area = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.pCommentForm textarea.commentWrite, div[contenteditable='true'].commentWrite"))
            )
        except:
             return False, "밴드 댓글 입력창을 찾을 수 없습니다."
             
        # Band often requires activating the field
        try:
            text_area.click()
            time.sleep(1)
        except: 
            pass
            
        # Submit button
        submit_selector = "button.uButton.-sizeS.-confirm, button.uButton.submit"
        
        return self._fill_and_submit(text_area, comment_text, submit_selector)

    def _fill_and_submit(self, text_area, comment_text, submit_selector, is_cafe=False):
        # Focus and Enter Text
        if text_area:
            try:
                text_area.click()
                time.sleep(0.5)
            except:
                self.driver.execute_script("arguments[0].click();", text_area)
            
            tag_name = text_area.tag_name.lower()
            is_contenteditable = text_area.get_attribute("contenteditable") == "true"
            
            # Method: Pyperclip Paste
            import pyperclip
            from selenium.webdriver.common.action_chains import ActionChains
            
            pyperclip.copy(comment_text)
            try:
                if is_contenteditable:
                    self.driver.execute_script("arguments[0].innerText = '';", text_area)
                else:
                    text_area.clear()
            except:
                pass

            try:
                if is_cafe and not is_contenteditable:
                    # Cafe textarea sometimes blocks paste if not focused correctly or uses specific events
                    text_area.send_keys(comment_text)
                else:
                    actions = ActionChains(self.driver)
                    actions.key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
                    time.sleep(0.5)
            except:
                text_area.send_keys(comment_text)
            
            # Verification
            current_val = ""
            if is_contenteditable:
                current_val = text_area.get_attribute("innerText")
            else:
                current_val = text_area.get_attribute("value")
            
            if not current_val or len(current_val.strip()) == 0:
                    try:
                        text_area.send_keys(comment_text)
                    except Exception as e:
                        print(f"❌ [CommentPoster] 텍스트 입력 최종 실패: {e}")

            time.sleep(1)

            # Submit button
            print("📤 [CommentPoster] 등록 버튼 찾는 중...")
            try:
                submit_btn = self.driver.find_element(By.CSS_SELECTOR, submit_selector)
                submit_btn.click()
                print("✅ [CommentPoster] 댓글 등록 완료")
                
                time.sleep(random.uniform(2, 3))
                return True, "댓글 작성 완료"
            except Exception as e:
                # Try JS Click
                try:
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, submit_selector)
                    self.driver.execute_script("arguments[0].click();", submit_btn)
                    return True, "댓글 작성 완료(JS)"
                except:
                    return False, f"등록 버튼 클릭 실패: {e}"
        
        return False, "알 수 없는 오류"

    def _remove_non_bmp(self, text):
        """
        Removes characters not in the Basic Multilingual Plane (BMP) (e.g., emojis)
        to prevent ChromeDriver crashes on some platforms.
        """
        import re
        return re.sub(r'[^\u0000-\uFFFF]', '', text)
