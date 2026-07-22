from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class ReplyCrawler:
    def __init__(self, driver):
        self.driver = driver

    def fetch_notifications(self):
        """
        Fetches 'Reply to my comment' notifications from Naver Notification Center (m.notify.naver.com).
        This source is more reliable than the blog mobile feed.
        """
        notifications = []
        try:
            # 1. Navigate to Naver Notification Center
            notify_url = "https://m.notify.naver.com/"
            print(f"📍 [ReplyCrawler] 알림 센터로 이동: {notify_url}")
            self.driver.get(notify_url)
            time.sleep(3)
            
            # 2. Click 'Activity/News' (활동•소식) Tab
            try:
                tabs = self.driver.find_elements(By.CSS_SELECTOR, ".filter, a.filter")
                for tab in tabs:
                    if "활동" in tab.text and "소식" in tab.text:
                        self.driver.execute_script("arguments[0].click();", tab)
                        time.sleep(2)
                        print("✅ [ReplyCrawler] '활동•소식' 탭 선택 완료")
                        break
            except Exception as e:
                print(f"⚠️ [ReplyCrawler] 탭 전환 실패 (전체 목록 사용): {e}")

            # 3. Scroll to load more (optional)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            
            # 4. Find Notification Items
            items = self.driver.find_elements(By.CSS_SELECTOR, "div.component_wrap a.link_notice")
            print(f"[{len(items)}] raw notifications found.")
            
            # Patterns for context
            MY_POST_PATTERNS = ["회원님의 게시글", "회원님의 글", "내 글에", "내 게시글", "작성하신 글에"]
            MY_COMMENT_REPLY_PATTERNS = ["회원님의 댓글에", "내 댓글에", "답글을 남겼습니다"]
            EXCLUDE_PATTERNS = ["서로이웃", "이웃신청", "좋아요", "공감", "팔로우"]

            # 5. Process Notifications (Click-and-Capture)
            # Since href is empty '#', we must click to get the URL
            
            processed_count = 0
            limit = 10 # Limit to latest 10 to check
            
            # Initial scan to get count
            initial_items = self.driver.find_elements(By.CSS_SELECTOR, "a.link_notice")
            total_items = len(initial_items)
            print(f"[{total_items}] raw notifications found. Checking latest {limit}...")
            
            for i in range(min(total_items, limit)):
                try:
                    # Re-fetch items to avoid StaleElementReferenceException
                    items = self.driver.find_elements(By.CSS_SELECTOR, "a.link_notice")
                    if i >= len(items):
                        break
                        
                    item = items[i]
                    text = item.text
                    
                    # --- Filter Logic (Pre-Click) ---
                    # Filter Excludes
                    if any(p in text for p in EXCLUDE_PATTERNS):
                        continue
                    if "블로그" not in text:
                        continue
                        
                    # Context Detection Heuristics
                    context = "UNKNOWN"
                    
                    # 1. Explicit 'My Post' patterns (Comments on my content)
                    if any(p in text for p in MY_POST_PATTERNS):
                        context = "MY_POST"
                    # 2. Key indicator for 'Reply to Me': it's NOT 'My Post'
                    # and NOT a 'New Post' notification from neighbors
                    elif "님이 새 글을" in text or "블로그에서 새로운 글" in text:
                        context = "NEIGHBOR_NEW_POST"
                    elif "서로이웃" in text or "이웃 신청" in text:
                        context = "NEIGHBOR_REQUEST"
                    else:
                        # Fallback: If it's a valid blog notification and not the above, 
                        # it's likely a reply to my comment (which just shows the content).
                        # e.g. "라이온합기도님, 안녕하세요! 😊..."
                        context = "REPLY_TO_ME"

                    if context == "NEIGHBOR_NEW_POST" or context == "NEIGHBOR_REQUEST":
                        continue

                    # 🚨 USER REQUEST: Only process 'REPLY_TO_ME' (External replies)
                    # Skip comments on my own posts to avoid overlap and focus on outreach follow-up
                    if context == "MY_POST":
                        print(f"  ⏭️ Skipping 'My Post' comment: {text[:20]}...")
                        # Pass/Continue without clicking to save time
                        continue
                    
                    print(f"  👆 [{i+1}] Clicking notification (Follow-up): {text[:20]}...")
                    
                    # --- Click and Capture ---
                    original_window = self.driver.current_window_handle
                    self.driver.execute_script("arguments[0].click();", item)
                    time.sleep(3) # Wait for navigation
                    
                    if len(self.driver.window_handles) > 1:
                        for window_handle in self.driver.window_handles:
                            if window_handle != original_window:
                                self.driver.switch_to.window(window_handle)
                                break
                        current_url = self.driver.current_url
                        self.driver.close()
                        self.driver.switch_to.window(original_window)
                    else:
                        current_url = self.driver.current_url
                    
                    # Convert Mobile to PC URL
                    if "m.blog.naver.com" in current_url:
                        pc_url = current_url.replace("m.blog.naver.com", "blog.naver.com")
                    else:
                        pc_url = current_url
                        
                    print(f"    🔗 Captured URL: {pc_url}")
                    
                    notifications.append({
                        "text": text.replace("\n", " "),
                        "link": pc_url,
                        "context": context,
                        "is_reply": True
                    })
                    
                    # --- Return to List ---
                    self.driver.get(notify_url)
                    time.sleep(2)
                    
                    # Re-click tab if needed (simple check)
                    try:
                        tabs = self.driver.find_elements(By.CSS_SELECTOR, ".filter, a.filter")
                        for tab in tabs:
                            if "활동" in tab.text and "소식" in tab.text:
                                tab.click()
                                time.sleep(1)
                                break
                    except:
                        pass
                        
                except Exception as e:
                    print(f"  ⚠️ Error processing item {i}: {e}")
                    # Try to recover navigation
                    try:
                        self.driver.get(notify_url)
                        time.sleep(2)
                    except:
                        pass
                    continue
            
            print(f"✅ [ReplyCrawler] Processed {len(notifications)} valid notifications.")
            
        except Exception as e:
            print(f"Error fetching notifications: {e}")
            import traceback
            traceback.print_exc()

        return notifications
