"""
네이버 카페 댓글 자동 답글 모듈
- 네이버 알림 센터(https://m.notify.naver.com/)에서 카페 관련 알림을 확인하고 답글을 작성합니다.
- 카페 게시글의 '답글쓰기' 기능을 사용하여 AI 기반 자동 답글을 등록합니다.
"""
import time
import random
import traceback
import re
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains

class NaverCafeCommentReply:
    def __init__(self, driver, gpt_handler=None, my_cafe_url=None, base_dir=None):
        self.driver = driver
        self.gpt_handler = gpt_handler
        self.stop_flag = False
        self.my_cafe_url = my_cafe_url
        self.base_dir = base_dir
        
    def auto_reply_all_cafe_notifications(self, limit=10):
        """
        알림 센터에서 모든 미답변 카페 댓글을 수집하고 AI 답글을 작성합니다.
        스케줄러에서 주로 호출됩니다.
        """
        print("🤖 카페 자동 답글 시스템 시작...")
        notifications = self.get_unread_comment_notifications(limit=limit)
        
        if not notifications:
            print("ℹ️ 처리할 새 카페 알림이 없습니다.")
            return True
            
        success_count = 0
        for idx, notify in enumerate(notifications):
            if self.stop_flag:
                print("🛑 작업 중단 요청됨")
                break
                
            print(f"🔄 [{idx+1}/{len(notifications)}] 답글 작성 시도 중...")
            if self.reply_to_comment_in_new_window(notify['url'], use_ai=True):
                success_count += 1
                time.sleep(random.uniform(3, 5))
            
        print(f"✅ 카페 자동 답글 작업 종료 (성공: {success_count}/{len(notifications)})")
        return True

    def get_unread_comment_notifications(self, limit=30):
        """
        네이버 알림 센터에서 카페 댓글/답글 알림을 수집합니다.
        반환 형식: [{'url': str, 'type': 'my_post' | 'my_comment_reply'}]
        """
        unread_links = []
        try:
            notify_url = "https://m.notify.naver.com/"
            print(f"📍 알림 센터로 이동합니다: {notify_url}")
            self.driver.get(notify_url)
            time.sleep(3)
            
            # 1. "활동•소식" 탭 클릭
            try:
                tabs = self.driver.find_elements(By.CSS_SELECTOR, ".filter, a.filter")
                for tab in tabs:
                    if "활동" in tab.text and "소식" in tab.text:
                        self.driver.execute_script("arguments[0].click();", tab)
                        time.sleep(2)
                        break
            except: pass
            
            # 2. 스크롤하여 알림 로드
            for _ in range(2):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)
            
            # 3. 카페 관련 알림 필터링
            items = self.driver.find_elements(By.CSS_SELECTOR, "a.link_notice")
            cafe_notifications = []
            
            for item in items:
                try:
                    text = item.text
                    if "카페" in text and ("댓글" in text or "답글" in text):
                        # 알림 타입 판단
                        item_type = 'my_comment_reply' if "답글을 남겼습니다" in text else 'my_post'
                        # 텍스트가 중복될 수 있으므로 일단 텍스트와 함께 저장
                        cafe_notifications.append({'text': text, 'type': item_type})
                        if len(cafe_notifications) >= limit: break
                except: continue
            
            print(f"📋 총 {len(cafe_notifications)}개의 카페 알림 발견")
            
            # 4. 알림 클릭하여 URL 수집
            for idx, notify in enumerate(cafe_notifications):
                try:
                    # Stale element 방지 위해 매번 다시 찾기
                    current_items = self.driver.find_elements(By.CSS_SELECTOR, "a.link_notice")
                    
                    target_item = None
                    for itm in current_items:
                        try:
                            if itm.text == notify['text']:
                                target_item = itm
                                break
                        except: continue
                    
                    if not target_item: continue
                    
                    self.driver.execute_script("arguments[0].click();", target_item)
                    time.sleep(2)
                    
                    new_url = self.driver.current_url
                    if "cafe.naver.com" in new_url:
                        # 중복 URL 체크
                        if not any(link['url'] == new_url for link in unread_links):
                            unread_links.append({'url': new_url, 'type': notify['type']})
                            print(f"  ✅ URL 수집: {new_url[:50]}...")
                    
                    # 다시 알림 센터로
                    self.driver.get(notify_url)
                    time.sleep(1.5)
                    # 탭 다시 선택
                    tabs = self.driver.find_elements(By.CSS_SELECTOR, ".filter, a.filter")
                    for tab in tabs:
                        if "활동" in tab.text and "소식" in tab.text:
                            self.driver.execute_script("arguments[0].click();", tab)
                            time.sleep(1)
                            break
                except: continue
                
        except Exception as e:
            print(f"❌ 카페 알림 수집 중 오류: {e}")
            
        return unread_links

    def reply_to_comment_in_new_window(self, url, use_ai=True):
        """새 창에서 카페 게시글을 열고 답글을 작성합니다."""
        original_window = self.driver.current_window_handle
        success = False
        
        try:
            print(f"  🔗 카페 게시글 이동: {url[:60]}...")
            self.driver.execute_script(f"window.open('{url}', '_blank');")
            time.sleep(3)
            
            # 새 창 전환
            new_window = [w for w in self.driver.window_handles if w != original_window][-1]
            self.driver.switch_to.window(new_window)
            
            # 1. cafe_main 프레임 전환
            try:
                WebDriverWait(self.driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "cafe_main")))
                print("  🔲 cafe_main 프레임 전환 완료")
            except:
                print("  ⚠️ cafe_main 프레임을 찾을 수 없습니다. 기본 페이지에서 시도.")

            # 2. 답글 작성 로직 수행
            success = self._perform_cafe_reply_logic(use_ai)
            
        except Exception as e:
            print(f"❌ 카페 답글 작업 중 오류: {e}")
        finally:
            if len(self.driver.window_handles) > 1:
                # 현재 창이 오리지널이 아니면 닫기
                if self.driver.current_window_handle != original_window:
                    self.driver.close()
            self.driver.switch_to.window(original_window)
            
        return success

    def _perform_cafe_reply_logic(self, use_ai):
        """카페 게시글 내의 미답변 댓글을 찾아 답글을 작성합니다."""
        try:
            # 댓글 목록 로딩 대기
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.comment_list")))
            
            comment_items = self.driver.find_elements(By.CSS_SELECTOR, "li.CommentItem")
            print(f"  📋 총 {len(comment_items)}개의 댓글 발견")
            
            replied_count = 0
            for item in comment_items:
                try:
                    # 1. '답글쓰기' 버튼 찾기
                    buttons = item.find_elements(By.CSS_SELECTOR, "a.comment_info_button")
                    reply_btn = None
                    for btn in buttons:
                        if "답글쓰기" in btn.text:
                            reply_btn = btn
                            break
                    
                    if not reply_btn: continue
                    
                    # 2. 이미 내 답글이 있는지 체크 (생략 가능하나 중복 방지 위해 권장)
                    # 여기서는 일단 모든 '답글쓰기' 가능한 곳에 시도하거나, 첫 번째 미답변만 처리
                    
                    # 댓글 내용 추출
                    comment_text = item.find_element(By.CSS_SELECTOR, "span.text_comment").text
                    print(f"  📝 댓글 감지: {comment_text[:30]}...")
                    
                    # 3. 답글 버튼 클릭
                    self.driver.execute_script("arguments[0].click();", reply_btn)
                    time.sleep(1.5)
                    
                    # 4. 나타난 입력창에 텍스트 입력
                    writer_area = item.find_element(By.CSS_SELECTOR, "div.CommentWriter")
                    textarea = writer_area.find_element(By.CSS_SELECTOR, "textarea.comment_inbox_text")
                    
                    # AI 답글 생성
                    if use_ai and self.gpt_handler:
                        # 카페 맥락을 위해 별도의 프롬프트나 가이드라인이 필요할 수 있으나 일단 기본 사용
                        reply_content = self.gpt_handler.generate_reply(comment_text)
                    else:
                        reply_content = "댓글 감사합니다! 좋은 하루 되세요. ^^"
                    
                    print(f"  💬 답글 입력: {reply_content}")
                    textarea.send_keys(reply_content)
                    time.sleep(0.5)
                    
                    # 5. 등록 버튼 클릭
                    register_btn = writer_area.find_element(By.CSS_SELECTOR, "a.button.btn_register")
                    self.driver.execute_script("arguments[0].click();", register_btn)
                    
                    print("  ✅ 답글 등록 완료")
                    replied_count += 1
                    time.sleep(2)
                    
                    # 한 게시글에서 하나만 달고 넘어가기 (안전성)
                    break 
                    
                except Exception as e:
                    print(f"  ⚠️ 개별 댓글 처리 중 오류: {e}")
                    continue
            
            return replied_count > 0
            
        except Exception as e:
            print(f"  ❌ 카페 댓글 로직 실패: {e}")
            return False

    def generate_ai_reply(self, comment_text):
        """GPT를 이용한 답글 생성 (gpt_handler 연동)"""
        if self.gpt_handler:
            return self.gpt_handler.generate_reply(comment_text)
        return "감사합니다! 좋은 하루 되세요. ^^"
