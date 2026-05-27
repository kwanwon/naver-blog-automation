import os

def fix_finisher():
    file_path = "/Users/gm2hapkido/Desktop/라이온개발자/naver_blog_post_finisher.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the start index of add_footer
    start_str = "    def add_footer(self):"
    start_idx = content.find(start_str)
    if start_idx == -1:
        print("Error: Could not find 'def add_footer(self):' in the file.")
        return

    # Find the end index which is the start of _switch_to_main_frame_robust
    end_str = "    def _switch_to_main_frame_robust(self):"
    end_idx = content.find(end_str)
    if end_idx == -1:
        print("Error: Could not find 'def _switch_to_main_frame_robust(self):' in the file.")
        return

    new_add_footer = """    def add_footer(self):
        \"\"\"
        Add footer to the blog post:
        1. Ensure space by adding newlines.
        2. Add KakaoTalk Open Chat link (with graceful exception bypass).
        3. Add Dojang location/map using the robust add_location method.
        \"\"\"
        try:
            print("\\n=== [Footer] Starting footer addition ====")
            success = True
            
            # 1. Add 3 newlines
            try:
                actions = ActionChains(self.driver)
                for _ in range(3):
                    actions.send_keys(Keys.ENTER).perform()
                    time.sleep(0.3)
                print("✅ [Footer] Added 3 spacing newlines")
            except Exception as e:
                print(f"⚠️ [Footer] Spacing newlines failed (skipping): {str(e)}")
            
            # 2. Add KakaoTalk link (Isolated & Bypassed)
            try:
                kakao_url = self.settings.get('kakao_url')
                link_button_found = False
                
                if kakao_url:
                    print(f"[Footer] KakaoTalk URL detected: '{kakao_url}'")
                    
                    if not kakao_url.startswith('http'):
                        print(f"⚠️ [Footer] Invalid Kakao URL format: {kakao_url}")
                    
                    # Enter KakaoTalk link guidance text
                    actions = ActionChains(self.driver)
                    actions.send_keys("카카오톡 오픈채팅 바로가기 👉").perform()
                    time.sleep(0.5)
                    
                    try:
                        actions = ActionChains(self.driver)
                        actions.send_keys(Keys.ESCAPE).perform()
                        time.sleep(0.5)
                    except Exception as e:
                        print(f"[Footer] Error sending ESC: {str(e)}")
                    
                    link_button_selectors = [
                        "button.se-oglink-toolbar-button",
                        "button[data-log='dot.link']",
                        "button[data-role='button-container'][data-log='dot.link']"
                    ]
                    
                    print("[Footer] Clicking link button...")
                    for selector in link_button_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            if elements:
                                for element in elements:
                                    if element.is_displayed() and element.is_enabled():
                                        element.click()
                                        print(f"✅ [Footer] Clicked link button: {selector}")
                                        link_button_found = True
                                        break
                            if link_button_found:
                                break
                        except Exception as e:
                            print(f"[Footer] Error trying selector {selector}: {str(e)}")
                            continue
                    
                    if not link_button_found:
                        print("⚠️ [Footer] CSS selector failed. Attempting fallback via JS...")
                        link_button_found = self.driver.execute_script(\"\"\"
                        const buttons = document.querySelectorAll('button');
                        for (const btn of buttons) {
                            const text = btn.innerText ? btn.innerText.trim() : '';
                            const title = btn.getAttribute('title') || '';
                            const dataLog = btn.getAttribute('data-log') || '';
                            if (text === '링크' || title === '링크' || dataLog === 'dot.link') {
                                btn.click();
                                return true;
                            }
                        }
                        return false;
                        \"\"\")
                    
                    if link_button_found:
                        print("[Footer] Link button clicked. Waiting for input window...")
                        link_input_appeared = False
                        for attempt in range(30):
                            try:
                                link_input = self.driver.find_element(By.CSS_SELECTOR, 
                                    "input.se-popup-oglink-input, input[placeholder*='URL'], input[placeholder*='url'], input[placeholder*='링크']")
                                if link_input.is_displayed():
                                    link_input_appeared = True
                                    break
                            except:
                                pass
                            time.sleep(0.5)
                        
                        if link_input_appeared:
                            time.sleep(1)
                            # Focus and fill
                            self.driver.execute_script(\"\"\"
                            if (document.activeElement) document.activeElement.blur();
                            window.tempKeyboardBlocked = true;
                            \"\"\")
                            time.sleep(0.3)
                            
                            if self.fill_link_input(kakao_url):
                                print("✅ [Footer] Kakao link URL filled.")
                                time.sleep(4)
                                
                                confirm_clicked = self.driver.execute_script(\"\"\"
                                function findAndClickConfirmButton() {
                                    console.log('=== Clicking Kakao Confirm Button ===');
                                    const exactSelectors = [
                                        'button.se-popup-button-confirm',
                                        'button.se-popup-button.se-popup-button-confirm', 
                                        'button[data-log="pog.ok"]',
                                        '.se-popup-button-confirm',
                                        '.se-popup .se-popup-button-confirm',
                                        '.se-popup button[class*="confirm"]',
                                        'button[class*="se-popup"][class*="confirm"]'
                                    ];
                                    for (const selector of exactSelectors) {
                                        const btn = document.querySelector(selector);
                                        if (btn && btn.offsetWidth > 0 && btn.offsetHeight > 0 && !btn.disabled) {
                                            btn.click();
                                            return true;
                                        }
                                    }
                                    const visibleButtons = Array.from(document.querySelectorAll('button')).filter(
                                        btn => btn.offsetWidth > 0 && btn.offsetHeight > 0 && !btn.disabled
                                    );
                                    for (const btn of visibleButtons) {
                                        const text = btn.innerText?.trim();
                                        if (text === '확인' || text === 'OK' || text === '삽입' || text === 'Insert') {
                                            btn.click();
                                            return true;
                                        }
                                    }
                                    
                                    // 5. Fallback popup last button
                                    console.log('5단계: 팝업 마지막 버튼 시도...');
                                    const popups = document.querySelectorAll('.se-popup, [class*="popup"]');
                                    for (const popup of popups) {
                                        if (popup.offsetWidth > 0 && popup.offsetHeight > 0) {
                                            const popupButtons = popup.querySelectorAll('button');
                                            if (popupButtons.length > 0) {
                                                const lastBtn = popupButtons[popupButtons.length - 1];
                                                if (lastBtn.offsetWidth > 0 && lastBtn.offsetHeight > 0 && !lastBtn.disabled) {
                                                    console.log('✅ 팝업 마지막 버튼 클릭:', lastBtn.innerText?.trim());
                                                    lastBtn.click();
                                                    return true;
                                                }
                                            }
                                        }
                                    }
                                    
                                    console.log('❌ 모든 방법으로도 확인 버튼을 찾을 수 없음');
                                    return false;
                                }
                                return findAndClickConfirmButton();
                                \"\"\")
                                
                                if confirm_clicked:
                                    print("✅ [Footer] Kakao link inserted successfully!")
                                    time.sleep(2)
                                else:
                                    print("⚠️ [Footer] Confirm button click failed for Kakao link")
                            else:
                                print("⚠️ [Footer] Failed to fill link input")
                        else:
                            print("⚠️ [Footer] Link input window did not appear")
                    else:
                        print("⚠️ [Footer] Link button not found or clicked")
                else:
                    print("ℹ] [Footer] Kakao URL not configured. Skipping link insertion.")
                    
            except Exception as e:
                # Bypass Kakao link insertion to prevent skipping location addition
                print(f"⚠️ [Footer] Kakao link insertion failed: {str(e)}. Bypassing to location addition...")
            
            # 3. Add Location (Maps) using the robust separate method
            print("[Footer] Proceeding to location/map addition...")
            try:
                location_success = self.add_location()
                if location_success:
                    print("✅ [Footer] Location information added successfully")
                else:
                    print("⚠️ [Footer] Location addition returned False (non-blocking)")
            except Exception as loc_err:
                print(f"⚠️ [Footer] Location addition failed with exception (bypassed): {str(loc_err)}")

            return True
            
        except Exception as e:
            print(f"⚠️ [Footer] Critical error in add_footer (bypassed): {str(e)}")
            return True

"""

    fixed_content = content[:start_idx] + new_add_footer + content[end_idx:]

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(fixed_content)
    print("Success: naver_blog_post_finisher.py has been fixed successfully!")

if __name__ == "__main__":
    fix_finisher()
