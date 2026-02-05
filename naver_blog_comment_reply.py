"""
네이버 블로그 댓글 자동 답글 모듈
- 블로그 홈(https://section.blog.naver.com/)에서 알림을 확인하고 답글을 작성합니다.
- 읽은 알림(중복)은 건너뛰고, 새 창에서 작업을 수행한 뒤 닫습니다.
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import random
import traceback
import re
import os

class NaverBlogCommentReply:
    def __init__(self, driver, gpt_handler=None, my_blog_id=None):
        self.driver = driver
        self.gpt_handler = gpt_handler
        self.stop_flag = False  # 중지 플래그
        self.default_reply_index = 0  # 기본 답글 순차 인덱스
        
        # 🆕 내 블로그 아이디 설정 (URL에서 내 글인지 판단용)
        self.my_blog_id = my_blog_id or self._load_my_blog_id()
        print(f"📝 내 블로그 아이디: {self.my_blog_id}")
    
    def _load_my_blog_id(self):
        """설정 파일에서 내 블로그 아이디 로드"""
        import json
        
        def extract_id_from_url(value):
            """URL 또는 ID에서 순수 ID만 추출"""
            if not value:
                return None
            value = value.strip()
            # URL 형식이면 ID만 추출
            if 'blog.naver.com/' in value:
                match = re.search(r'blog\.naver\.com/([^/\?]+)', value)
                if match:
                    return match.group(1)
            # 이미 ID 형식이면 그대로 반환
            return value
        
        try:
            # 🆕 user_settings.txt (JSON 형식)에서 blog_url 로드 시도
            settings_paths = [
                os.path.join(os.path.dirname(__file__), '..', 'config', 'user_settings.txt'),
                os.path.join(os.path.dirname(__file__), 'config', 'user_settings.txt'),
            ]
            for path in settings_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            try:
                                # JSON 형식인 경우
                                data = json.loads(content)
                                blog_url = data.get('blog_url', '')
                                if blog_url:
                                    blog_id = extract_id_from_url(blog_url)
                                    if blog_id:
                                        print(f"📝 블로그 ID 로드 완료: {blog_id}")
                                        return blog_id
                            except json.JSONDecodeError:
                                # 키=값 형식인 경우 (레거시)
                                for line in content.split('\n'):
                                    if line.startswith('blog_id=') or line.startswith('blog_url='):
                                        value = line.split('=', 1)[1].strip()
                                        blog_id = extract_id_from_url(value)
                                        if blog_id:
                                            print(f"📝 블로그 ID 로드 완료: {blog_id}")
                                            return blog_id
        except Exception as e:
            print(f"⚠️ 블로그 ID 로드 중 오류: {e}")
        
        # 🆕 기본값 (설정 파일에서 못 찾으면 하드코딩 사용)
        print("ℹ️ 블로그 ID: 기본값 사용 (gm2hapkido)")
        return "gm2hapkido"
    
    def set_my_blog_id(self, blog_id):
        """내 블로그 아이디 설정"""
        self.my_blog_id = blog_id
        print(f"📝 내 블로그 아이디 설정됨: {self.my_blog_id}")
    
    def extract_blog_owner_from_url(self, url):
        """
        🆕 URL에서 블로그 주인 아이디 추출
        예: https://blog.naver.com/gm2hapkido/224141826542 → gm2hapkido
        """
        try:
            # PC 버전: blog.naver.com/아이디/글번호
            match = re.search(r'blog\.naver\.com/([^/]+)/', url)
            if match:
                return match.group(1)
            
            # 모바일 버전: m.blog.naver.com/아이디/글번호
            match = re.search(r'm\.blog\.naver\.com/([^/]+)/', url)
            if match:
                return match.group(1)
        except:
            pass
        return None
    
    def is_my_blog(self, url):
        """🆕 URL이 내 블로그인지 확인"""
        blog_owner = self.extract_blog_owner_from_url(url)
        if blog_owner and self.my_blog_id:
            return blog_owner.lower() == self.my_blog_id.lower()
        return False
        
    def find_notification_bell(self):
        """네이버 GNB 알림(종 모양) 버튼 찾기"""
        # 브라우저 실습 결과 반영: 블로그 홈의 경우 .gnb_notice_li 내부의 a태그/아이콘
        selectors = [
            ".gnb_notice",           # 블로그 홈 활성화 아이콘
            "a.gnb_notice", 
            "#gnb_notice", 
            ".gnb_btn_notice", 
            ".nav_item_alarm",       # 네이버 메인
            ".service_icon.type_alarm"
        ]
        for selector in selectors:
            try:
                # 가시성 있는 요소만 찾기
                elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elems:
                    if elem.is_displayed():
                        return elem
            except:
                continue
        return None

    def is_notification_read(self, element):
        """알림 항목이 이미 읽은(클릭한) 것인지 판단"""
        try:
            # 1. 클래스로 확인 (모바일/PC 공통 패턴)
            cls = element.get_attribute("class") or ""
            if "visited" in cls or "read" in cls or "checked" in cls:
                return True
                
            # 2. 내부 '읽음' 텍스트 확인 (접근성 태그)
            try:
                blind_text = element.find_element(By.CSS_SELECTOR, ".blind").text
                if "읽음" in blind_text:
                    return True
            except:
                pass
                
            # 3. 스타일 투명도 확인 (링크가 흐릿하면 읽은 것)
            try:
                link = element.find_element(By.TAG_NAME, "a")
                opacity = link.value_of_css_property("opacity")
                if opacity and float(opacity) < 0.9: # 보통 0.5~0.7 등
                    return True
            except:
                pass
                
            return False
        except:
            return False

    def get_unread_comment_notifications(self, limit=50):
        """
        [Click-and-Capture 방식]
        모바일 알림 센터에서 블로그 관련 알림을 직접 클릭하여 URL을 수집합니다.
        
        🆕 반환 형식: [{'url': '...', 'type': 'my_post' | 'my_comment_reply'}]
        - my_post: 내 글에 달린 댓글 → 모든 미답변 댓글에 답글
        - my_comment_reply: 내 댓글에 달린 답글 → 해당 답글에만 1회 답글
        """
        unread_links = []  # 🆕 {'url': str, 'type': str} 형식으로 저장
        
        try:
            # 1. 모바일 알림 센터로 이동
            notify_url = "https://m.notify.naver.com/"
            print(f"📍 알림 센터로 이동합니다: {notify_url}")
            self.driver.switch_to.default_content()
            self.driver.get(notify_url)
            time.sleep(3)
            
            # 로그인 체크
            if "nid.naver.com" in self.driver.current_url:
                print("❌ 로그인이 필요합니다.")
                return []
            
            # 2. "활동•소식" 탭 클릭 (블로그 댓글이 여기에 있음)
            # 인덱스 대신 텍스트로 찾아서 클릭 (네이버가 순서를 바꿔도 작동)
            try:
                tabs = self.driver.find_elements(By.CSS_SELECTOR, ".filter, a.filter")
                clicked = False
                for tab in tabs:
                    tab_text = tab.text.strip()
                    if "활동" in tab_text and "소식" in tab_text:
                        self.driver.execute_script("arguments[0].click();", tab)
                        time.sleep(2)
                        print("✅ '활동•소식' 탭 클릭 완료")
                        clicked = True
                        break
                if not clicked:
                    print("⚠️ '활동•소식' 탭을 찾지 못함, 전체 목록에서 진행")
            except Exception as e:
                print(f"⚠️ 필터 탭 클릭 실패: {e}")
            
            # 3. 스크롤하여 더 많은 알림 로드
            print("📜 알림 목록 스캔 중...")
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)
            
            # 4. 블로그 관련 알림 아이템 찾기 (a.link_notice 중 "블로그" 텍스트가 있는 것)
            items = self.driver.find_elements(By.CSS_SELECTOR, "a.link_notice")
            print(f"📋 총 {len(items)}개의 알림 항목 발견")
            
            # 🔧 개선: 모바일 알림센터 형식에 맞게 필터링
            # 모바일 알림 형식: "작성자명\n블로그\n날짜\n댓글내용..."
            # 
            # ✅ 처리 대상: 
            #    1. 내 블로그 글에 달린 댓글
            #    2. 내 댓글에 대한 답글 (남의 글에서)
            # ❌ 제외 대상: 
            #    1. 서로이웃, 좋아요 등
            #    2. 남의 글에 다른 사람이 남긴 댓글 (나와 무관)
            
            EXCLUDE_PATTERNS = [
                "서로이웃", "이웃신청", "이웃 신청", 
                "좋아요를 눌렀습니다", "구독", "팔로우",
                "님의 글에 공감", "님이 팔로우"
            ]
            
            # 🔑 내 글 여부 판단 패턴 (있으면 확실히 내 글)
            MY_POST_PATTERNS = [
                "회원님의 게시글", "회원님의 글", "회원님의 블로그",
                "내 글에", "내 게시글", "작성하신 글에"
            ]
            
            # 🆕 내 댓글에 대한 답글 패턴 (남의 글에서 내 댓글에 답글이 달린 경우)
            MY_COMMENT_REPLY_PATTERNS = [
                "회원님의 댓글에", "내 댓글에", "작성하신 댓글에",
                "님이 답글을 남겼습니다", "님이 회원님의 댓글에"
            ]
            
            # 🔑 다른 사람 글 판단 패턴 (있으면 제외)
            OTHER_POST_PATTERNS = [
                "님의 글에 댓글",  # "OOO님의 글에 댓글" = 다른 사람 글
                "님의 게시글에 댓글",
            ]
            
            blog_items = []
            debug_count = 0  # 디버그 출력 제한
            
            for item in items:
                try:
                    text = item.text
                    
                    # 1. 제외 패턴 확인 (서로이웃, 좋아요 등)
                    if any(exclude in text for exclude in EXCLUDE_PATTERNS):
                        continue
                    
                    # 2. 블로그 관련인지 확인
                    if "블로그" not in text:
                        continue
                    
                    # 3. 다른 사람 글 패턴 확인 (명확히 제외해야 할 경우)
                    is_other_post = any(pattern in text for pattern in OTHER_POST_PATTERNS)
                    
                    if is_other_post:
                        # ❌ 다른 사람 글에 달린 댓글 → 제외
                        if debug_count < 5:
                            print(f"  ⏭️ 제외됨 (다른 사람 글): {text[:50]}...")
                            debug_count += 1
                        continue
                    
                    # 4. 내 글 패턴 확인
                    is_my_post = any(pattern in text for pattern in MY_POST_PATTERNS)
                    is_reply_to_my_comment = any(pattern in text for pattern in MY_COMMENT_REPLY_PATTERNS)
                    
                    # 🆕 타입 결정: 내 글 댓글 vs 내 댓글에 대한 답글
                    if is_my_post:
                        # 내 글 댓글 → 모든 미답변 댓글에 답글
                        blog_items.append({'item': item, 'type': 'my_post', 'text': text[:50]})
                        print(f"  ✅ 내 글 댓글 알림: {text[:50]}...")
                    elif is_reply_to_my_comment:
                        # 내 댓글에 대한 답글 → 해당 답글에만 1회 답글
                        blog_items.append({'item': item, 'type': 'my_comment_reply', 'text': text[:50]})
                        print(f"  ✅ 내 댓글 답글 알림 (1회만 답글): {text[:50]}...")
                    else:
                        # 패턴 없음 → 내 글로 간주 (모바일 알림 형식)
                        blog_items.append({'item': item, 'type': 'my_post', 'text': text[:50]})
                        print(f"  ✅ 블로그 댓글 알림: {text[:50]}...")
                    
                    if len(blog_items) >= limit:
                        break
                            
                except Exception:
                    continue
            
            # 블로그 알림 개수 저장
            blog_count = len(blog_items)
            print(f"🎯 처리 대상 알림: {blog_count}개")
            
            # 5. 인덱스 기반으로 알림 클릭 (stale element 방지)
            processed_count = 0
            max_to_process = min(blog_count, limit)
            
            # 🆕 원본 blog_items에서 타입 정보 저장
            notification_types = {i: blog_items[i]['type'] for i in range(len(blog_items))}
            
            for idx in range(max_to_process):
                try:
                    # 원본 알림의 타입 확인
                    notification_type = notification_types.get(idx, 'my_post')
                    print(f"  [{idx+1}/{max_to_process}] 알림 클릭 중... (타입: {notification_type})")
                    
                    # 매번 새로 요소 찾기 (stale element 방지) - 동일한 필터링 적용
                    items = self.driver.find_elements(By.CSS_SELECTOR, "a.link_notice")
                    blog_items_fresh = []
                    for itm in items:
                        try:
                            txt = itm.text
                            # 제외 패턴 확인
                            if any(exclude in txt for exclude in EXCLUDE_PATTERNS):
                                continue
                            # 블로그 관련인지 확인
                            if "블로그" not in txt:
                                continue
                            
                            # 다른 사람 글 패턴 확인 (명확히 제외)
                            is_other_post = any(pattern in txt for pattern in OTHER_POST_PATTERNS)
                            
                            if is_other_post:
                                continue  # 다른 사람 글 → 제외
                            else:
                                # 🆕 타입 정보도 함께 저장
                                is_my_post = any(pattern in txt for pattern in MY_POST_PATTERNS)
                                is_reply = any(pattern in txt for pattern in MY_COMMENT_REPLY_PATTERNS)
                                item_type = 'my_comment_reply' if is_reply else 'my_post'
                                blog_items_fresh.append({'item': itm, 'type': item_type})
                        except:
                            continue
                    
                    if idx >= len(blog_items_fresh):
                        print(f"    ⚠️ 알림 항목 부족, 종료")
                        break
                    
                    # 현재 URL 저장
                    current_url = self.driver.current_url
                    
                    # 🆕 현재 아이템의 타입 확인
                    current_item_info = blog_items_fresh[idx]
                    current_type = current_item_info['type']
                    
                    # 인덱스 기반 클릭
                    self.driver.execute_script("arguments[0].click();", current_item_info['item'])
                    time.sleep(2)
                    
                    # 이동된 URL 캡처
                    new_url = self.driver.current_url
                    
                    if new_url != current_url and "blog.naver.com" in new_url:
                        # 🆕 URL과 타입을 함께 저장
                        unread_links.append({'url': new_url, 'type': current_type})
                        print(f"    ✅ URL 수집: {new_url[:50]}... (타입: {current_type})")
                        processed_count += 1
                    elif "m.blog.naver.com" in new_url:
                        pc_url = new_url.replace("m.blog.naver.com", "blog.naver.com")
                        unread_links.append({'url': pc_url, 'type': current_type})
                        print(f"    ✅ URL 수집 (모바일→PC 변환): {pc_url[:50]}... (타입: {current_type})")
                        processed_count += 1
                    else:
                        print(f"    ⚠️ 블로그 URL 아님: {new_url[:50]}...")
                    
                    # 알림 센터로 복귀
                    self.driver.get(notify_url)
                    time.sleep(2)
                    
                    # 필터 탭 다시 클릭 (활동•소식) - 텍스트로 찾기
                    try:
                        tabs = self.driver.find_elements(By.CSS_SELECTOR, ".filter, a.filter")
                        for tab in tabs:
                            if "활동" in tab.text and "소식" in tab.text:
                                self.driver.execute_script("arguments[0].click();", tab)
                                time.sleep(1)
                                break
                    except:
                        pass
                        
                    # 스크롤 복원 (더 정확하게)
                    self.driver.execute_script(f"window.scrollTo(0, {idx * 80})")
                    time.sleep(0.5)
                            
                except Exception as e:
                    print(f"    ❌ 처리 중 오류: {e}")
                    # 알림 센터로 복귀 시도
                    try:
                        self.driver.get(notify_url)
                        time.sleep(2)
                    except:
                        pass
                    continue
                    
        except Exception as e:
            print(f"❌ 알림 목록 수집 중 오류: {e}")
            traceback.print_exc()
            
        # 🆕 URL 기반 중복 제거 (딕셔너리 형식)
        seen_urls = set()
        unique_links = []
        for link_info in unread_links:
            url = link_info['url']
            if url not in seen_urls:
                seen_urls.add(url)
                unique_links.append(link_info)
        
        print(f"🎯 최종 처리 대상: {len(unique_links)}개")
        return unique_links

    def switch_to_main_frame(self):
        """블로그 본문 Iframe으로 전환"""
        try:
            self.driver.switch_to.default_content()
            time.sleep(0.5)
            iframe = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "mainFrame"))
            )
            self.driver.switch_to.frame(iframe)
            return True
        except:
            return False

    def reply_to_comment_in_new_window(self, url, use_ai=True, notification_type='my_post'):
        """
        새 창에서 댓글 URL을 열고 답글 작성 후 닫음
        
        🆕 URL에서 블로그 주인을 확인하여:
        - 내 블로그 → 모든 미답변 댓글에 답글
        - 남의 블로그 → 건너뛰기
        """
        original_window = self.driver.current_window_handle
        success = False
        
        # 🆕 URL에서 블로그 주인 확인
        blog_owner = self.extract_blog_owner_from_url(url)
        is_my_blog = self.is_my_blog(url)
        
        if not is_my_blog:
            # 남의 글 → 건너뛰기
            print(f"  ⏭️ 건너뜀 (남의 글: {blog_owner}) - 내 블로그가 아닙니다.")
            return False
        
        print(f"  ✅ 내 블로그 확인됨 ({blog_owner})")
        
        try:
            # 1. 새 창 열기
            print(f"  🔗 링크 이동: {url[:60]}...")
            self.driver.execute_script(f"window.open('{url}', '_blank');")
            time.sleep(4)  # 페이지 로딩 대기 시간 늘림
            
            # 2. 새 창으로 전환
            new_window = [w for w in self.driver.window_handles if w != original_window][-1]
            self.driver.switch_to.window(new_window)
            
            # 3. Iframe 전환 및 답글 작성 시도
            if self.switch_to_main_frame():
                # 내 글 → 모든 미답변에 답글
                success = self._perform_reply_logic(use_ai)
            else:
                print("⚠️ mainFrame 전환 실패 (블로그 글이 아니거나 구조가 다름)")
                success = self._perform_reply_logic(use_ai)
                
        except Exception as e:
            print(f"❌ 답글 작업 중 오류: {e}")
            traceback.print_exc()
        finally:
            # 4. 창 닫기 및 복귀
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                self.driver.switch_to.window(original_window)
            except:
                pass
                
        return success

    def _perform_single_reply_logic(self, use_ai):
        """
        🆕 1회만 답글 작성 로직 (내 댓글에 대한 답글용)
        
        남의 글에서 내 댓글에 누군가 답글을 달았을 때:
        - 해당 답글에만 1회 답글
        - 그 글의 다른 댓글에는 답글하지 않음
        """
        wait = WebDriverWait(self.driver, 5)
        
        try:
            # 1. 댓글 영역 확장
            try:
                comment_btn = self.driver.find_elements(By.CSS_SELECTOR, ".btn_comment")
                if comment_btn and comment_btn[0].is_displayed():
                    if not self.driver.find_elements(By.CSS_SELECTOR, ".u_cbox_focus"):
                        self.driver.execute_script("arguments[0].click();", comment_btn[0])
                        time.sleep(2)
            except:
                pass

            # 2. 첫 번째 미답변 댓글 찾기 (1회만)
            all_boxes = self.driver.find_elements(By.CSS_SELECTOR, ".u_cbox_comment_box")
            if not all_boxes:
                print("⚠️ 댓글을 찾을 수 없습니다.")
                return False
            
            print(f"  📋 총 {len(all_boxes)}개 댓글 영역 발견 (1회만 답글 모드)")
            
            for idx, comment_box in enumerate(all_boxes):
                try:
                    # [건너뛰기 조건 1] 내가 작성한 글인지 확인
                    my_markers = comment_box.find_elements(By.CSS_SELECTOR, ".u_cbox_mine, .u_cbox_btn_delete, .u_cbox_my")
                    if my_markers and any(m.is_displayed() for m in my_markers):
                        continue
                    
                    # [건너뛰기 조건 2] 이미 답글이 있는지 확인
                    reply_btns = comment_box.find_elements(By.CSS_SELECTOR, ".u_cbox_btn_reply")
                    if not reply_btns:
                        continue
                    
                    reply_btn = reply_btns[0]
                    btn_text = reply_btn.text.strip() if reply_btn.text else ""
                    
                    # 이미 답글이 있는 경우 건너뛰기
                    if btn_text and any(c.isdigit() for c in btn_text):
                        continue
                    
                    # 첫 번째 미답변 댓글 발견! 답글 작성
                    comment_text_elem = comment_box.find_elements(By.CSS_SELECTOR, ".u_cbox_contents")
                    original_comment = comment_text_elem[0].text if comment_text_elem else ""
                    
                    print(f"  💬 [1회 답글] 댓글 발견: {original_comment[:30]}...")
                    
                    # 답글 작성
                    success = self._write_single_reply(comment_box, reply_btn, original_comment, use_ai)
                    
                    if success:
                        print("  ✅ 1회 답글 완료!")
                        return True
                    else:
                        print("  ⚠️ 답글 작성 실패")
                        return False
                        
                except Exception as e:
                    continue
            
            print("  📭 답글할 댓글이 없습니다.")
            return False
            
        except Exception as e:
            print(f"❌ 1회 답글 로직 오류: {e}")
            traceback.print_exc()
            return False

    def _write_single_reply(self, comment_box, reply_btn, original_comment, use_ai):
        """🆕 단일 답글 작성 헬퍼"""
        try:
            # 답글 버튼 클릭
            self.driver.execute_script("arguments[0].click();", reply_btn)
            time.sleep(1)
            
            # 답글 입력창 찾기
            reply_input = comment_box.find_elements(By.CSS_SELECTOR, ".u_cbox_write_box textarea, .u_cbox_text")
            if not reply_input:
                # 페이지 전체에서 찾기
                reply_input = self.driver.find_elements(By.CSS_SELECTOR, ".u_cbox_reply_area textarea, .u_cbox_text.ub_cbox_write_textarea")
            
            if not reply_input:
                print("  ⚠️ 답글 입력창을 찾을 수 없습니다.")
                return False
            
            input_elem = reply_input[0]
            
            # 답글 내용 생성
            if use_ai and self.gpt_handler:
                reply_text = self.gpt_handler.generate_reply(original_comment)
            else:
                reply_text = self._get_default_reply()
            
            # 답글 입력
            self.driver.execute_script("arguments[0].click();", input_elem)
            time.sleep(0.5)
            input_elem.clear()
            input_elem.send_keys(reply_text)
            time.sleep(0.5)
            
            # 등록 버튼 클릭
            submit_btns = self.driver.find_elements(By.CSS_SELECTOR, ".u_cbox_btn_upload, .u_cbox_btn_submit, button[type='submit']")
            for btn in submit_btns:
                if btn.is_displayed():
                    self.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(1.5)
                    return True
            
            return False
            
        except Exception as e:
            print(f"  ⚠️ 답글 작성 오류: {e}")
            return False

    def _perform_reply_logic(self, use_ai):
        """실제 답글 작성 로직 (Iframe 내부)"""
        wait = WebDriverWait(self.driver, 5)
        
        try:
            # 1. 댓글 영역 확장
            try:
                comment_btn = self.driver.find_elements(By.CSS_SELECTOR, ".btn_comment")
                if comment_btn and comment_btn[0].is_displayed():
                    if not self.driver.find_elements(By.CSS_SELECTOR, ".u_cbox_focus"):
                         self.driver.execute_script("arguments[0].click();", comment_btn[0])
                         time.sleep(2)  # 댓글 로딩 대기 시간 늘림 (긴 댓글도 처리)
            except:
                pass

            # 2. 원본 댓글만 찾기 (대댓글은 제외)
            # 답글/대댓글은 .u_cbox_reply_area 안에 있거나 .u_cbox_mine 클래스가 있음
            replied_count = 0
            processed_indices = set()  # 이미 처리한 인덱스
            
            # 초기 댓글 수 확인
            initial_boxes = self.driver.find_elements(By.CSS_SELECTOR, ".u_cbox_comment_box")
            print(f"  📋 총 {len(initial_boxes)}개 댓글 영역 발견 (원본+답글 포함)")
            
            while True:
                # 매번 새로 탐색 (stale element 방지)
                all_boxes = self.driver.find_elements(By.CSS_SELECTOR, ".u_cbox_comment_box")
                if not all_boxes:
                    print("⚠️ 댓글을 찾을 수 없습니다.")
                    break
                
                found_unanswered = False
                
                for idx, comment_box in enumerate(all_boxes):
                    if idx in processed_indices:
                        continue
                    
                    try:
                        # [건너뛰기 조건 1] 내가 작성한 글인지 확인
                        try:
                            # .u_cbox_mine 클래스나 삭제 버튼이 있으면 내 글
                            my_markers = comment_box.find_elements(By.CSS_SELECTOR, ".u_cbox_mine, .u_cbox_btn_delete, .u_cbox_my")
                            if my_markers and any(m.is_displayed() for m in my_markers):
                                processed_indices.add(idx)
                                continue
                        except:
                            pass
                        
                        # [건너뛰기 조건 2] 대댓글(답글)인지 확인 (부모 요소 확인)
                        try:
                            # 대댓글은 .u_cbox_reply_area 안에 있음
                            parent = comment_box.find_element(By.XPATH, "./ancestor::div[contains(@class, 'u_cbox_reply_area')]")
                            if parent:
                                processed_indices.add(idx)
                                continue
                        except:
                            pass  # 원본 댓글 (대댓글 아님)
                        
                        # [중복 방지] 해당 댓글에 내 답글이 이미 있는지 확인
                        has_my_reply = False
                        try:
                            # 대댓글 영역 확인
                            reply_area = comment_box.find_element(By.XPATH, "./following-sibling::div[contains(@class, 'u_cbox_reply_area')]")
                            if reply_area:
                                my_replies = reply_area.find_elements(By.CSS_SELECTOR, ".u_cbox_mine, .u_cbox_btn_delete, .u_cbox_my")
                                if my_replies:
                                    for my_reply in my_replies:
                                        if my_reply.is_displayed():
                                            has_my_reply = True
                                            break
                        except:
                            pass
                        
                        if has_my_reply:
                            print(f"  [{idx+1}] ⚠️ 이미 내 답글 있음, 건너뜀")
                            processed_indices.add(idx)
                            continue
                        
                        # 미답글 원본 댓글 발견!
                        target_comment = comment_box
                        print(f"  [{idx+1}] ✅ 미답글 원본 댓글 발견")
                        found_unanswered = True
                        processed_indices.add(idx)

                        # 2-1. 내용 읽기
                        try:
                            content_el = target_comment.find_element(By.CSS_SELECTOR, ".u_cbox_contents, .u_cbox_text_wrap")
                            comment_text = content_el.text
                            print(f"  📝 댓글 내용: {comment_text[:50]}")
                        except:
                            comment_text = "안녕하세요"

                        # 3. '답글' 버튼 클릭
                        try:
                            reply_btn = target_comment.find_element(By.CSS_SELECTOR, ".u_cbox_btn_reply")
                            self.driver.execute_script("arguments[0].click();", reply_btn)
                            time.sleep(1)
                        except NoSuchElementException:
                            print("  ⚠️ 답글 버튼이 없습니다.")
                            continue  # 다음 댓글로

                        # 4. 입력창 찾기 및 답글 작성
                        try:
                            # 게시글 제목 가져오기
                            try:
                                blog_title = self.driver.find_element(By.CSS_SELECTOR, ".se-title-text, .pcol1, .se-component-content").text
                                print(f"  📄 게시글 제목: {blog_title[:40]}...")
                            except:
                                blog_title = ""
                            
                            # [브라우저 테스트 결과] 입력창은 contenteditable div
                            input_selector = ".u_cbox_text[contenteditable='true'], .u_cbox_text.u_cbox_text_mention[contenteditable='true']"
                            text_area = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, input_selector)))
                            
                            reply_content = self.generate_ai_reply(comment_text) if use_ai else self._get_next_default_reply()
                            
                            # 답글 내용 로그
                            print(f"  💬 작성할 답글: {reply_content}")
                            
                            # JavaScript로 텍스트 입력 (contenteditable div 전용)
                            self.driver.execute_script("""
                                var el = arguments[0];
                                el.focus();
                                el.innerText = arguments[1];
                                el.dispatchEvent(new Event('input', { bubbles: true }));
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                            """, text_area, reply_content)
                            time.sleep(0.5)
                            
                            # 5. 등록 버튼 찾기 및 클릭
                            submit_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".u_cbox_btn_upload")))
                            self.driver.execute_script("arguments[0].click();", submit_btn)
                            
                            # 최종 결과 로그
                            print(f"  ✅ 답글 등록 성공!")
                            print(f"     📌 요약: [{blog_title[:20] if blog_title else '제목없음'}] 댓글: '{comment_text[:20]}...' → 답글: '{reply_content}'")
                            
                            replied_count += 1
                            time.sleep(2)
                            
                            # 답글 등록 후 다음 미답글 댓글 찾기 위해 루프 break (stale element 방지)
                            break
                            
                        except Exception as e:
                            print(f"  ❌ 입력창 찾기/입력 실패: {e}")
                            break  # 이 댓글 포기하고 다음 탐색으로
                            
                    except Exception as e:
                        print(f"  ❌ 댓글 처리 중 오류: {e}")
                        processed_indices.add(idx)
                        continue  # 다음 댓글로
                
                # 더 이상 미답글 댓글이 없으면 종료
                if not found_unanswered:
                    break
            
            # 모든 댓글 처리 완료
            if replied_count > 0:
                print(f"  🎯 이 게시글에서 {replied_count}개 댓글에 답글 완료")
                return True
            else:
                print("  ℹ️ 모든 댓글에 이미 답글이 있습니다.")
                return True  # 처리 완료로 간주
                
        except Exception as e:
            print(f"❌ 답글 로직 수행 실패: {e}")
            return False

    def generate_ai_reply(self, comment_text, blog_title=""):
        """
        GPT 답글 생성 - 댓글 내용에 맞는 짧은 답변
        블로그 생성 로직 대신 직접 API 호출로 간결한 답글 생성
        상담 관련 댓글에는 전화번호 포함
        """
        if not self.gpt_handler:
            return "감사합니다! 행복한 하루 되세요~😊"
        
        # 상담 관련 키워드 체크
        consultation_keywords = ["상담", "문의", "연락", "등록", "가입", "수업", "체험", "비용", "가격", "시간표"]
        is_consultation = any(keyword in comment_text for keyword in consultation_keywords)
        
        # 전화번호 로드 (상담 관련일 때만)
        phone_number = None
        if is_consultation:
            phone_number = self._load_phone_number()
            print(f"📞 상담 관련 댓글 감지 - 전화번호 포함 예정: {phone_number}")
        
        # 사용자 커스텀 답글 지침 로드
        custom_instruction = self._load_custom_reply_instruction()
        
        # 기본 지침 (더 명확하게)
        default_instruction = """- 댓글에 직접 공감하며 짧게 감사 표현
- 반드시 20자 이내로 작성
- 이모지 1개만 포함
- 예시: "감사합니다😊", "좋은 말씀 감사해요💕", "응원 감사합니다🙏"
- 답글만 출력 (설명, 제목, 본문 태그 없이)"""
        
        instruction = custom_instruction if custom_instruction else default_instruction
        
        # 상담 관련일 때 추가 지침
        if is_consultation and phone_number:
            instruction += f"\n- 상담 문의이면 '연락주세요 {phone_number}' 형식으로 전화번호 포함"
        
        # 댓글 답글 전용 프롬프트 (매우 간결하게)
        prompt = f"""다음 블로그 댓글에 대한 짧은 답글을 작성해.

댓글: "{comment_text[:100]}"

규칙:
{instruction}

답글:"""

        try:
            # 통합 GPTHandler 사용 (OpenAI/Gemini 모두 지원)
            if self.gpt_handler and hasattr(self.gpt_handler, 'generate_reply'):
                # 시스템 메시지 구성
                system_msg = "당신은 친근한 블로그 주인(관장)입니다. 사용자가 제공한 지침을 정확히 따라 댓글에 답글을 남깁니다."
                if is_consultation and phone_number:
                    system_msg += f" 상담/문의 댓글에는 전화번호({phone_number})를 반드시 포함하세요."
                
                # 지침을 시스템 메시지에 추가
                system_msg += f"\n\n[답글 작성 지침]\n{instruction}"
                
                content = self.gpt_handler.generate_reply(
                    system_prompt=system_msg,
                    user_text=f"댓글: \"{comment_text}\"\n위 댓글에 대한 답글을 작성해주세요.",
                    max_tokens=300
                )
            else:
                return "감사합니다! 행복한 하루 되세요~😊"
            

            
            # 후처리: 불필요한 prefix 제거
            prefixes_to_remove = ["답글:", "답변:", "Reply:", "[답글]", "[본문]", "[제목]"]
            for prefix in prefixes_to_remove:
                if content.startswith(prefix):
                    content = content[len(prefix):].strip()
            
            # 따옴표 제거
            content = content.strip('"\'')
            
            # 길이 제한 제거 (사용자 지침의 고정 문구가 잘리지 않도록)
            # 네이버 댓글 글자 수 제한은 약 300자이므로 그 이상만 자름
            if len(content) > 300:
                content = content[:300]
                
            print(f"🤖 AI 답글 생성: {content}")
            return content.strip()
            
        except Exception as e:
            print(f"⚠️ AI 답글 생성 오류: {e}")
            return "댓글 감사합니다!😊"
    
    def _load_phone_number(self):
        """사용자 설정에서 전화번호 로드"""
        import os
        import json
        
        try:
            possible_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'user_settings.txt'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'user_settings.txt'),
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                        phone = settings.get('phone', '')
                        if phone and phone.strip():
                            return phone.strip()
            return None
        except:
            return None
    
    def _load_custom_reply_instruction(self):
        """사용자 커스텀 답글 지침 로드"""
        import os
        import json
        
        try:
            # 설정 파일 경로 탐색
            possible_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'user_settings.txt'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'user_settings.txt'),
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                        instruction = settings.get('reply_instruction', '')
                        if instruction and instruction.strip():
                            return instruction.strip()
            return None
        except:
            return None

    def _get_next_default_reply(self):
        """사용자 설정에서 기본 답글 문구를 가져와 순차 사용"""
        import os
        import json
        
        # 기본 답글 목록
        default_replies = [
            "감사합니다😊", "좋은 말씀 감사해요💕", "응원 감사합니다🙏", 
            "행복한 하루 되세요✨", "방문 감사합니다🌻"
        ]
        
        try:
            # 설정 파일 경로 탐색
            possible_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'user_settings.txt'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'user_settings.txt'),
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                        custom_replies = settings.get('default_reply', '')
                        if custom_replies and custom_replies.strip():
                            default_replies = [r.strip() for r in custom_replies.split(',') if r.strip()]
                            break
        except:
            pass
        
        # 순차 선택
        if default_replies:
            reply = default_replies[self.default_reply_index % len(default_replies)]
            self.default_reply_index += 1
            return reply
        
        return "감사합니다😊"

    def stop(self):
        """작업 중지"""
        self.stop_flag = True
        print("🛑 중지 요청됨...")

    def process_all_unanswered_comments(self, use_ai=True, limit=10):
        """
        메인 실행 함수
        
        Args:
            use_ai: AI 답글 사용 여부
            limit: 처리할 최대 알림 수 (기본 10)
        """
        self.stop_flag = False  # 시작 시 플래그 초기화
        print(f"🚀 댓글 답글 자동화 시작... (최대 {limit}개)")
        
        links = self.get_unread_comment_notifications(limit=limit)
        
        if not links:
            print("📭 처리할 알림이 없습니다.")
            return 0
            
        print(f"🎯 총 {len(links)}개의 댓글 알림 처리를 시작합니다.")
        
        success_count = 0
        skip_count = 0
        for i, link_info in enumerate(links):
            # 중지 플래그 확인
            if self.stop_flag:
                print("🛑 사용자에 의해 중지됨")
                break
            
            # URL 추출
            url = link_info['url']
            
            print(f"\n[{i+1}/{len(links)}] 작업 중...")
            
            # 🆕 URL에서 내 블로그인지 확인 후 답글 처리
            # (reply_to_comment_in_new_window 내부에서 판단)
            result = self.reply_to_comment_in_new_window(url, use_ai)
            if result:
                success_count += 1
            elif result is False and not self.is_my_blog(url):
                skip_count += 1
            
            time.sleep(random.uniform(2, 4))
            
        print(f"\n✨ 전체 작업 완료: {success_count}건 답글, {skip_count}건 건너뜀")
        return success_count
