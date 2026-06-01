import os
import sys
import time
import traceback
import random
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add project root to sys.path to resolve parent modules
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from utils.path_utils import get_data_dir, get_gpt_settings_path
from naver_blog_auto_image import NaverBlogImageInserter
from naver_blog_post_finisher import NaverBlogPostFinisher

class SeleniumPoster:
    def __init__(self):
        self.driver = None
        self.base_dir = root_dir

    def _init_driver(self):
        """Initializes ChromeDriver using the exact shared session profile."""
        print("[Step] [SeleniumPoster] Initializing ChromeDriver...")
        try:
            options = Options()
            # Run in standard headful mode so Naver doesn't trigger security blocks on post actions
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument('--allow-clipboard-read-write')
            
            # Shared session profile
            user_data_dir = os.path.join(get_data_dir(), "naver_blog_automation_profile")
            options.add_argument(f"--user-data-dir={user_data_dir}")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.implicitly_wait(10)
            self.driver.maximize_window()
            print("[Step] [SeleniumPoster] ChromeDriver initialized successfully with shared profile.")
            return True
        except Exception as e:
            print(f"[Error] [SeleniumPoster] Failed to create driver: {e}")
            traceback.print_exc()
            return False

    def _set_font_and_alignment(self):
        """Subtle formatting: Apply nanum gothic and center align."""
        print("[Step] [SeleniumPoster] Setting font and alignment...")
        try:
            # Click font family dropdown button
            font_button = None
            font_selectors = [
                "button.se-font-family-toolbar-button",
                "button[data-name='font-family']",
                "button.se-toolbar-button[title*='글꼴']"
            ]
            for sel in font_selectors:
                try:
                    font_button = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if font_button:
                        font_button.click()
                        break
                except:
                    continue
            
            time.sleep(0.3)
            # Select NanumBarunGothic or similar
            try:
                options = self.driver.find_elements(By.CSS_SELECTOR, ".se-toolbar-option-text-button")
                for opt in options:
                    if "나눔바른고딕" in opt.text or "나눔고딕" in opt.text:
                        opt.click()
                        print("[Step] [SeleniumPoster] Font set to NanumGothic.")
                        break
            except:
                pass

            time.sleep(0.2)
            # Center Align
            align_button = None
            align_selectors = [
                "button.se-toolbar-align",
                "button[data-name='align']"
            ]
            for sel in align_selectors:
                try:
                    align_button = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if align_button:
                        align_button.click()
                        break
                except:
                    continue

            time.sleep(0.3)
            try:
                center_opts = self.driver.find_elements(By.CSS_SELECTOR, "button[data-value='center'], .se-toolbar-option-align-center-button")
                if center_opts:
                    center_opts[0].click()
                    print("[Step] [SeleniumPoster] Alignment set to Center.")
            except:
                pass
        except Exception as e:
            print(f"[Warning] [SeleniumPoster] Font or alignment setting encountered issue: {e}")

    def post_to_naver(self, title, content, image_folder, tags=None, driver=None, naver_id=None, status_callback=None, settings=None):
        """
        Performs the complete posting cycle to Naver Blog:
        Goes to editor -> inserts title -> configures body -> writes paragraphs ->
        inserts 5 processed watermarked images sequentially -> appends footers ->
        inserts tags -> publishes instantly.
        """
        is_external_driver = driver is not None
        
        # ⛅ [날씨 꼬리표 삽입] 본문 뒤에 날씨 정보를 스마트하게 자동 결합
        try:
            from modules.weather_cache_manager import WeatherCacheManager
            resolved_settings = settings
            if not resolved_settings:
                from utils.path_utils import get_gpt_settings_path
                gpt_path = get_gpt_settings_path()
                if os.path.exists(gpt_path):
                    with open(gpt_path, 'r', encoding='utf-8') as f:
                        resolved_settings = json.load(f)
                else:
                    resolved_settings = {}
            
            weather_loc = resolved_settings.get('weather_location') or resolved_settings.get('blog_location') or '서울'
            weather_text = WeatherCacheManager.generate_posting_weather_text(weather_loc)
            if weather_text:
                content += weather_text
                print(f"⛅ [SeleniumPoster] 날씨 결합 완료 ({weather_loc} 기준)")
        except Exception as we:
            print(f"[Warning] [SeleniumPoster] 날씨 결합 로직 중 오류 발생: {we}")
        
        if is_external_driver:
            self.driver = driver
            print("[Step] [SeleniumPoster] Reusing active external ChromeDriver (Main Window).")
            # 기존 메인 창을 그대로 사용 (새 창 띄우기 코드 제거됨)
        else:
            if not self._init_driver():
                return False

        def update_status(msg):
            if status_callback:
                status_callback(msg)
            print(f"[SeleniumPoster] {msg}")

        try:
            # 1. Navigation to Editor using dedicated Naver ID
            target_id = naver_id if naver_id else "gm2hapkido"
            target_write_url = f"https://blog.naver.com/{target_id}?Redirect=Write&"
            update_status(f"Navigating to Naver Blog write page: {target_write_url}")
            self.driver.get(target_write_url)
            time.sleep(2.0)

            # 1.1 Naver Login Check and Intelligent Wait for up to 3 minutes
            login_check_start = time.time()
            wait_timeout = 180  # 3 minutes
            login_prompted = False
            
            while True:
                try:
                    current_url = self.driver.current_url
                except Exception as ce:
                    # In case browser is closed during manual login
                    update_status(f"⚠️ Browser interaction error (maybe closed by user): {ce}")
                    return False

                # Check if we are redirected to nid.naver.com or other login paths
                if "nid.naver.com" in current_url:
                    if not login_prompted:
                        update_status("⚠️ [로그인 필요] 네이버 로그인이 풀려 있습니다. 열린 창에서 로그인을 마쳐주세요! (로그인 감지 시 자동으로 계속 진행됩니다)")
                        login_prompted = True
                        
                    # Calculate remaining time
                    elapsed = time.time() - login_check_start
                    remaining = int(wait_timeout - elapsed)
                    if remaining <= 0:
                        update_status("❌ [타임아웃] 3분 동안 네이버 로그인이 감지되지 않아 작업을 안전하게 종료합니다.")
                        return False
                        
                    if int(elapsed) % 10 == 0:  # Update status every 10 seconds
                        update_status(f"⏳ 로그인 대기 중... ({remaining}초 남음)")
                        
                    time.sleep(1.5)
                else:
                    if login_prompted:
                        update_status("✅ 로그인 성공 감지! 3초 후 글쓰기 페이지로 재진입합니다...")
                        time.sleep(3.0)
                        try:
                            self.driver.get(target_write_url)
                            time.sleep(2.5)
                        except Exception as ge:
                            update_status(f"⚠️ Re-entry navigation failed: {ge}")
                            return False
                    break

            # 2. Main Frame Switch
            try:
                # Clear frame context to make sure we start from top-level
                self.driver.switch_to.default_content()
                
                iframe = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.ID, "mainFrame"))
                )
                self.driver.switch_to.frame(iframe)
                update_status("Switched to mainFrame iframe.")
            except Exception as e:
                # Capture current page screenshot for debug
                try:
                    screenshot_path = os.path.join(get_data_dir(), "logs", f"iframe_fail_screenshot_{int(time.time())}.png")
                    self.driver.save_screenshot(screenshot_path)
                    update_status(f"📸 디버깅용 화면 캡처 저장 완료: {screenshot_path}")
                except Exception as se:
                    print(f"[Warning] Failed to capture debug screenshot: {se}")

                update_status(f"❌ Failed to switch to mainFrame iframe: {e}")
                return False

            # 3. Handle Auto-Saved Draft Popup
            try:
                cancel_btn = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "se-popup-button-cancel"))
                )
                cancel_btn.click()
                print("[Step] [SeleniumPoster] Dismissed auto-saved draft popup.")
                time.sleep(0.5)
            except:
                print("[Step] [SeleniumPoster] No auto-saved draft popup detected.")

            # 4. Insert Title
            try:
                title_area = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".se-title-text .se-text-paragraph"))
                )
                title_area.click()
                time.sleep(0.3)
                
                actions = ActionChains(self.driver)
                actions.send_keys(title).perform()
                print("[Step] [SeleniumPoster] Title inserted successfully.")
                time.sleep(0.5)
            except Exception as e:
                print(f"[Error] [SeleniumPoster] Title entry failed: {e}")
                return False

            # 5. Focus and Format Body
            try:
                body_area = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.se-component.se-text.se-l-default"))
                )
                body_area.click()
                print("[Step] [SeleniumPoster] Body area focused.")
                time.sleep(0.5)

                self._set_font_and_alignment()
                time.sleep(0.5)
            except Exception as e:
                print(f"[Error] [SeleniumPoster] Body area initialization failed: {e}")
                return False

            # 6. Setup Image Inserter
            image_inserter = None
            image_files = []
            if os.path.exists(image_folder):
                image_files = [os.path.join(image_folder, f) for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                image_files.sort() # Ensure consistent ordering
                
            if image_files:
                try:
                    image_inserter = NaverBlogImageInserter(
                        self.driver,
                        images_folder=image_folder,
                        insert_mode="random", # Use standard insertion helper
                        fallback_folder=image_folder
                    )
                    print(f"[Step] [SeleniumPoster] Image inserter active. Found {len(image_files)} processed images.")
                except Exception as e:
                    print(f"[Warning] [SeleniumPoster] Failed to initialize image inserter: {e}")

            # 7. Write Paragraphs and Interweave Images
            # Split into individual lines to keep native typing behavior and avoid breakages
            content_lines = [line.strip() for line in content.split('\n')]
            cleaned_lines = []
            for line in content_lines:
                if line:
                    cleaned_lines.append(line)
                else:
                    # Avoid multiple empty lines
                    if cleaned_lines and cleaned_lines[-1] != "":
                        cleaned_lines.append("")

            total_lines = len(cleaned_lines)
            total_images = len(image_files)
            
            # Distribute images: Intersperse 5 images across the lines evenly
            img_indices = []
            if total_images > 0 and total_lines > 5:
                step = max(1, total_lines // (total_images + 1))
                img_indices = [step * (i + 1) for i in range(total_images)]
                img_indices = [min(idx, total_lines - 1) for idx in img_indices]
                img_indices = sorted(list(set(img_indices)))
            else:
                img_indices = [total_lines - 1] if total_lines > 0 else []

            print(f"[Step] [SeleniumPoster] Line insertion schedule for images: {img_indices}")

            image_inserted_count = 0
            for idx, line in enumerate(cleaned_lines):
                if not line:
                    # Empty line -> insert ENTER to split paragraphs nicely
                    actions = ActionChains(self.driver)
                    actions.send_keys(Keys.ENTER)
                    actions.perform()
                    time.sleep(0.1)
                    continue

                actions = ActionChains(self.driver)
                actions.send_keys(line + Keys.ENTER)
                actions.perform()
                time.sleep(0.15)

                # Insert scheduled image
                if image_inserter and idx in img_indices and image_inserted_count < total_images:
                    try:
                        target_img = image_files[image_inserted_count]
                        print(f"[Step] [SeleniumPoster] Inserting image {image_inserted_count + 1}: {os.path.basename(target_img)}")
                        image_inserter.insert_single_image(target_img)
                        image_inserted_count += 1
                        time.sleep(1.2)
                        
                        # Refocus body
                        self.driver.switch_to.default_content()
                        self.driver.switch_to.frame("mainFrame")
                        body_areas = self.driver.find_elements(By.CSS_SELECTOR, "div.se-component.se-text.se-l-default")
                        if body_areas:
                            self.driver.execute_script("arguments[0].click();", body_areas[-1])
                            time.sleep(0.5)
                    except Exception as img_err:
                        print(f"[Warning] [SeleniumPoster] Image insertion at line index {idx} failed: {img_err}")

            # Append any remaining images at the very end
            if image_inserter and image_inserted_count < total_images:
                print(f"[Step] [SeleniumPoster] Appending remaining {total_images - image_inserted_count} images at the end.")
                for img_idx in range(image_inserted_count, total_images):
                    try:
                        target_img = image_files[img_idx]
                        image_inserter.insert_single_image(target_img)
                        image_inserted_count += 1
                        time.sleep(1.2)
                    except Exception as img_err:
                        print(f"[Warning] [SeleniumPoster] End image insertion failed: {img_err}")

            # 7.5 Apply global center-alignment and font styling to all components
            print("[Step] [SeleniumPoster] Enforcing center-alignment and fonts globally via Select All...")
            try:
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame("mainFrame")
                body_areas = self.driver.find_elements(By.CSS_SELECTOR, "div.se-component.se-text.se-l-default")
                if body_areas:
                    # Focus editor
                    body_areas[-1].click()
                    time.sleep(0.5)
                    
                    # Keyboard shortcut select all (Ctrl+A or Cmd+A based on OS)
                    actions = ActionChains(self.driver)
                    is_mac = sys.platform == 'darwin'
                    modifier_key = Keys.COMMAND if is_mac else Keys.CONTROL
                    
                    actions.key_down(modifier_key).send_keys('a').key_up(modifier_key).perform()
                    print("[Step] [SeleniumPoster] Sent Select-All command.")
                    time.sleep(0.5)
                    
                    # Enforce the alignment and font to the selection
                    self._set_font_and_alignment()
                    time.sleep(0.5)
                    
                    # Click body once to release selection
                    body_areas[-1].click()
                    time.sleep(0.2)
            except Exception as format_err:
                print(f"[Warning] [SeleniumPoster] Global styling selection encountered issue: {format_err}")

            # Refocus one last time
            try:
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame("mainFrame")
                body_areas = self.driver.find_elements(By.CSS_SELECTOR, "div.se-component.se-text.se-l-default")
                if body_areas:
                    self.driver.execute_script("arguments[0].click();", body_areas[-1])
                    time.sleep(0.5)
            except:
                pass

            # 8. Post Finisher Integration
            print("[Step] [SeleniumPoster] Adding standard footer, location and tags...")
            try:
                # Enforce using unified settings from parent app, fallback to gpt_settings
                resolved_settings = settings
                if not resolved_settings:
                    gpt_settings = {}
                    gpt_path = get_gpt_settings_path()
                    if os.path.exists(gpt_path):
                        with open(gpt_path, 'r', encoding='utf-8') as f:
                            gpt_settings = json.load(f)
                    resolved_settings = gpt_settings

                post_finisher = NaverBlogPostFinisher(self.driver, resolved_settings)
                
                # Double line breaks for formatting
                actions = ActionChains(self.driver)
                actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
                actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
                
                update_status("🔗 카카오 오픈채팅 링크가 포함된 푸터 정보를 본문에 삽입합니다...")
                post_finisher.add_footer()
                time.sleep(1.0)

                update_status("📍 체육관 장소 및 지도 정보를 검색하여 삽입합니다...")
                post_finisher.add_location()
                time.sleep(1.0)
                
                # Tag resolution
                resolved_tags = tags
                if not resolved_tags:
                    resolved_tags = resolved_settings.get('tags', ["소아비만", "어린이건강", "체육관"])
                
                print(f"[Step] [SeleniumPoster] Writing tags and triggering final publish: {resolved_tags}")
                # NaverBlogPostFinisher's add_tags handles typing and clicking publish
                publish_success = post_finisher.add_tags(resolved_tags, skip_publish=False)
                
                if publish_success:
                    print("[Step] [SeleniumPoster] Complete Auto-posting cycle executed successfully!")
                    return True
                else:
                    print("[Warning] [SeleniumPoster] Posting executed, but failed to confirm final publish click.")
                    return False
            except Exception as finish_err:
                print(f"[Error] [SeleniumPoster] Post finishing failed: {finish_err}")
                traceback.print_exc()
                return False

        except Exception as ex:
            print(f"[Error] [SeleniumPoster] Exception during posting: {ex}")
            traceback.print_exc()
            return False
            
        finally:
            if self.driver:
                try:
                    if is_external_driver:
                        # 기존 메인 창을 그대로 사용했으므로 창을 닫지 않고 유지합니다.
                        print("[Step] [SeleniumPoster] Main window kept open (no temporary tab to close).")
                    else:
                        self.driver.quit()
                        print("[Step] [SeleniumPoster] Isolated browser session closed.")
                except Exception as close_err:
                    print(f"[Warning] [SeleniumPoster] Wrapping up session error: {close_err}")
