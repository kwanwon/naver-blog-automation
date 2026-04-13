import time
import random
import json
import os
import threading
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

class IdleActivity:
    """
    이웃 소통 및 댓글 답글 자동화 모듈
    
    기능:
    1. 방문소통: 이웃새글 목록에서 직접 공감/댓글 (새창 사용, 중복 방지)
    2. 댓글소통: 우리 글에 달린 댓글 감지 → 자동 답글 (중복 방지)
    """
    
    # 30개 랜덤 답글 문구
    REPLY_PHRASES = [
        "방문해주셔서 감사합니다.^^", "감사합니다 ㅎㅎ 시간될때 구경하러 갈게요~", "감사해요, 행복한 하루 되세요^^",
        "좋은 말씀 감사합니다!", "응원해주셔서 힘이 나요~", "댓글 감사합니다 :)", "좋은 하루 보내세요!",
        "감사합니다~ 자주 놀러오세요 ㅎㅎ", "덕분에 기분이 좋네요^^", "항상 응원해주셔서 감사해요!",
        "댓글 남겨주셔서 감사합니다~", "좋은 인연이 되길 바랍니다^^", "감사해요! 오늘도 화이팅입니다~",
        "방문 감사드려요 ㅎㅎ", "좋은 말씀 남겨주셔서 감사합니다!", "감사합니다~ 행복한 시간 되세요!",
        "응원 감사해요! 자주 뵙겠습니다~", "댓글 정말 감사드립니다^^", "좋은 하루 되세요~ 감사합니다!",
        "항상 응원합니다! 감사해요~", "반갑습니다^^ 좋은 인연이네요!", "감사합니다! 다음에 또 놀러오세요~",
        "댓글 고마워요 ㅎㅎ", "감사합니다~ 건강한 하루 되세요!", "좋은 에너지 감사해요^^",
        "응원 감사합니다! 화이팅!", "반가워요~ 좋은 하루 보내세요!", "감사합니다! 행복 가득하세요~",
        "댓글 감사해요! 자주 소통해요^^", "좋은 말씀 감사합니다~ 힘이 되네요!"
    ]
    
    # 30개 랜덤 댓글 문구
    COMMENT_PHRASES = [
        "좋은 글 잘 봤습니다! 공감해요~", "유익한 정보 감사합니다^^", "글 잘 읽었어요! 응원합니다~",
        "좋은 하루 되세요! 좋은 글이네요 ㅎㅎ", "오늘도 좋은 글 감사합니다!", "잘 보고 갑니다~ 힘내세요!",
        "공감하며 갑니다^^", "글 잘 읽었습니다! 감사해요~", "오늘도 좋은 하루 되세요!",
        "좋은 정보 감사합니다 ㅎㅎ", "응원하며 갑니다! 화이팅!", "잘 보고 공감 누르고 갑니다~",
        "좋은 글 감사해요! 자주 올게요^^", "오늘도 멋진 하루 되세요!", "유익한 글 감사합니다!",
        "잘 읽었습니다~ 공감이요!", "좋은 글 감사해요 ㅎㅎ", "응원합니다! 좋은 하루 되세요~",
        "글 잘 봤어요! 감사합니다^^", "오늘도 좋은 글 잘 읽었어요!", "공감 꾹! 좋은 하루 되세요~",
        "좋은 정보 공유 감사해요!", "잘 보고 갑니다^^", "항상 좋은 글 감사합니다!",
        "유익해요! 응원합니다~", "읽고 갑니다! 감사해요^^", "좋은 글이네요 ㅎㅎ",
        "공감합니다! 좋은 하루 되세요~", "오늘도 화이팅이요!", "잘 봤습니다~ 감사해요!"
    ]
    
    def __init__(self, driver, gpt_handler, base_dir=None):
        self.driver = driver
        self.gpt_handler = gpt_handler
        self.base_url = "https://section.blog.naver.com/BlogHome.naver?directoryNo=0&currentPage=1&groupId=0"
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 답글 완료한 댓글 ID 저장
        self.replied_comments_path = os.path.join(self.base_dir, 'config', 'replied_comments.json')
        self.replied_comments = self._load_replied_comments()
        
        # 처리한 이웃글 (이번 세션 동안만 중복 방지)
        self.processed_posts = set()
        
        # 중단 플래그
        self.is_running = False
        
        # 랜덤 문구 인덱스
        self.phrase_index = random.randint(0, len(self.REPLY_PHRASES)-1)
        self.comment_phrase_index = random.randint(0, len(self.COMMENT_PHRASES)-1)
        
    def _load_replied_comments(self):
        try:
            if os.path.exists(self.replied_comments_path):
                with open(self.replied_comments_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cutoff = datetime.now().timestamp() - (7 * 24 * 60 * 60)
                    return {k: v for k, v in data.items() if v.get('timestamp', 0) > cutoff}
            return {}
        except Exception:
            return {}
    
    def _save_replied_comments(self):
        try:
            os.makedirs(os.path.dirname(self.replied_comments_path), exist_ok=True)
            with open(self.replied_comments_path, 'w', encoding='utf-8') as f:
                json.dump(self.replied_comments, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 저장 실패: {e}")
    
    def _get_next_reply_phrase(self):
        phrase = self.REPLY_PHRASES[self.phrase_index]
        self.phrase_index = (self.phrase_index + 1) % len(self.REPLY_PHRASES)
        return phrase
    
    def _get_next_comment_phrase(self):
        phrase = self.COMMENT_PHRASES[self.comment_phrase_index]
        self.comment_phrase_index = (self.comment_phrase_index + 1) % len(self.COMMENT_PHRASES)
        return phrase
    
    def _generate_ai_comment(self, post_title, post_content_preview):
        """글 내용을 읽고 관련된 댓글 생성 + 블로그 방문 초대"""
        try:
            prompt = f"""다음 블로그 글에 대한 친근하고 따뜻한 댓글을 작성해주세요.

제목: {post_title}
내용: {post_content_preview[:300]}

📋 규칙 (중요):
1. **역할 정의**: 당신은 지금 이웃의 블로그에 놀러 온 **'방문자(이웃)'**입니다. 절대 글의 주인인 것처럼 행동하지 마세요.
2. **절대 금지어**: "문의해 주세요", "상담 가능합니다", "체험 수업", "방문해 주세요" 등 본인의 체육관 홍보나 영업 멘트를 **절대** 하지 마세요. 
3. 글의 내용을 구체적으로 언급하며 공감해주세요. (예: "수련하시는 모습이 멋지네요" X -> "아이들이 뛰는 모습이 정말 활기차 보이네요!" O)
4. "감사합니다", "잘 보고 갑니다" 같은 상투적인 인사로 시작하지 마세요. 바로 본론(감상)부터 말하세요.
5. 마치 친구의 글을 읽은 것처럼 자연스럽게 반응해주세요.
6. 마지막에 "자주 소통해요~" 또는 "좋은 하루 되세요^^" 같은 가벼운 인사를 덧붙여주세요.
7. 전체 50~100자 내외.

📌 절대 금지:
- 상담 유도 ("궁금한 점 있으면 연락주세요" 등 절대 금지)
- 상대방이 나에게 해준 게 없는데 "감사합니다"라고 말하기 (나는 방문자임)

📌 예시:
"오늘 [수련내용/활동] 하시는 모습 보니 정말 열정이 대단하시네요! 저도 같은 지도자로서 많이 배우고 갑니다. 앞으로도 자주 소통하며 지내요~"
"""
            result = self.gpt_handler.generate_platform_content(
                topic=prompt,
                platform='idle'
            )
            comment = result.get('content', '')
            
            # 정리
            if len(comment) > 120: 
                comment = comment[:120]
            if len(comment) < 10 or "작성" in comment or "[" in comment:
                return self._get_next_comment_phrase() + " 제 블로그에도 놀러오세요^^"
            
            # 초대 문구가 없으면 추가
            invite_phrases = ["블로그", "놀러오", "구경오", "방문"]
            if not any(p in comment for p in invite_phrases):
                comment += " 제 블로그에도 놀러오세요^^"
            
            return comment.strip()
        except Exception:
            return self._get_next_comment_phrase() + " 제 블로그에도 놀러오세요^^"
    
    def visit_and_interact(self, count=3, do_like=True, use_ai=False, min_interval=300, max_interval=600):
        print(f"🤝 이웃 소통 활동 시작... (목표: {count}회)")
        self.is_running = True
        interaction_count = 0
        current_page = 1
        max_scroll_attempts = 3
        
        try:
            print(f"📍 페이지 이동: {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(3)
            
            while interaction_count < count and self.is_running:
                try:
                    # 1. 목록 로드 대기
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".list_post_article .item"))
                    )
                    
                    # 2. 아이템 찾기
                    post_items = self.driver.find_elements(By.CSS_SELECTOR, ".list_post_article .item")
                    print(f"  📋 현재 페이지에 {len(post_items)}개 글 발견")
                    
                    # 3. 처리할 아이템 선정 - 🔧 좋아요 버튼이 'off' 상태인 글 찾기
                    target_item = None
                    
                    for i, item in enumerate(post_items):
                        try:
                            # 좋아요 버튼 찾기 - u_likeit_button
                            try:
                                like_btn = item.find_element(By.CSS_SELECTOR, ".u_likeit_button")
                                btn_class = like_btn.get_attribute("class") or ""
                                
                                # 🔧 버그 수정: 'off' 클래스가 없으면 이미 누른 상태
                                # (u_likeit_button에 'on'이란 글자가 포함되어 있어서 이전 로직이 오작동함)
                                if "off" not in btn_class:
                                    continue
                                    
                                # 고유 ID 생성
                                try:
                                    title_elem = item.find_element(By.CSS_SELECTOR, "a.desc_inner, .text")
                                    post_id = str(hash(title_elem.text[:50]))
                                except:
                                    post_id = str(i)
                                
                                if post_id in self.processed_posts:
                                    continue
                                
                                target_item = item
                                self.processed_posts.add(post_id)
                                break
                                
                            except:
                                continue
                                
                        except StaleElementReferenceException:
                            continue
                    
                    # 4. 대상 글이 없으면 페이지네이션
                    if not target_item:
                        print(f"  📄 현재 페이지에 처리할 글 없음. 다음 페이지로...")
                        
                        # 다음 페이지 버튼 찾기
                        next_page_clicked = False
                        try:
                            # 다음 번호 클릭 시도
                            next_num = current_page + 1
                            page_btns = self.driver.find_elements(By.CSS_SELECTOR, ".pagination a, .paginate a")
                            for btn in page_btns:
                                if btn.text.strip() == str(next_num):
                                    self.driver.execute_script("arguments[0].click();", btn)
                                    current_page = next_num
                                    next_page_clicked = True
                                    print(f"  📖 {current_page}페이지로 이동")
                                    time.sleep(2)
                                    break
                        except:
                            pass
                        
                        if not next_page_clicked:
                            print("  ℹ️ 더 이상 페이지가 없거나 모든 글에 이미 공감했습니다.")
                            break
                        continue
                    
                    # 5. 상호작용 수행
                    print(f"\n--- 소통 진행 ({interaction_count+1}/{count}) ---")
                    
                    # 글 요약 추출
                    post_title = "제목 없음"
                    post_content = ""
                    try:
                        text_elem = target_item.find_element(By.CSS_SELECTOR, ".text, a.desc_inner")
                        post_title = text_elem.text[:100]
                        post_content = text_elem.text
                    except:
                        pass
                    print(f"  📄 글: {post_title[:40]}...")
                    
                    # [좋아요]
                    if do_like:
                        try:
                            like_btn = target_item.find_element(By.CSS_SELECTOR, ".u_likeit_button")
                            self.driver.execute_script("arguments[0].click();", like_btn)
                            print("  ❤️ 좋아요 클릭")
                            time.sleep(1)
                        except Exception as e:
                            print(f"  ⚠️ 좋아요 실패: {e}")
                    
                    # [댓글] - 댓글 링크 클릭하여 해당 글로 이동
                    comment_text = ""
                    if use_ai:
                        ai_comment = self._generate_ai_comment(post_title, post_content)
                        comment_text = ai_comment if ai_comment else self._get_next_comment_phrase() + " 제 블로그에도 놀러오세요^^"
                    else:
                        comment_text = self._get_next_comment_phrase() + " 제 블로그에도 놀러오세요^^"
                    
                    # 댓글 링크 찾기 (copen=1 포함)
                    try:
                        comment_link = target_item.find_element(By.CSS_SELECTOR, "a[href*='copen=1']")
                        link_url = comment_link.get_attribute("href")
                        
                        # 새 탭에서 열기
                        self.driver.execute_script(f"window.open('{link_url}', '_blank');")
                        time.sleep(3)
                        
                        # 탭 전환
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        
                        # 댓글 작성
                        if self._write_comment_internal(comment_text):
                            print(f"  💬 댓글 완료: {comment_text[:30]}...")
                        
                        # 탭 닫고 원래 탭으로
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        time.sleep(1)
                        
                    except Exception as e:
                        print(f"  ⚠️ 댓글 링크 없음 또는 실패: {e}")
                    
                    interaction_count += 1
                    
                    # 대기
                    if interaction_count < count and self.is_running:
                        wait_time = random.randint(min_interval, max_interval)
                        print(f"  ⏰ {wait_time}초 대기...")
                        for i in range(wait_time):
                            if not self.is_running:
                                break
                            time.sleep(1)
                    
                except Exception as e:
                    print(f"  ⚠️ 오류 발생: {e}")
                    time.sleep(2)
                    continue
            
            print(f"✅ 방문소통 종료. 총 {interaction_count}회 완료.")
            return interaction_count > 0
            
        except Exception as e:
            print(f"❌ 치명적 오류: {e}")
            return False
        finally:
            self.is_running = False

    def _click_like_in_list(self, item):
        try:
            # 여러 선택자 시도
            selectors = ["span[class*='u_likeit_icon']", "a[class*='like']", "button[class*='like']"]
            for sel in selectors:
                try:
                    btn = item.find_element(By.CSS_SELECTOR, sel)
                    self.driver.execute_script("arguments[0].click();", btn)
                    print("  ❤️ 공감 클릭")
                    return True
                except:
                    continue
            return False
        except:
            return False

    def _open_post_and_comment(self, item, comment_text):
        """새 탭에서 글을 열고 댓글 작성 후 닫기"""
        try:
            # 1. 링크 찾기 - 🔧 올바른 셀렉터 순서
            link_url = None
            
            # 전략 A: a.desc_inner (제목 링크 - 가장 정확)
            try:
                title_link = item.find_element(By.CSS_SELECTOR, "a.desc_inner")
                link_url = title_link.get_attribute("href")
            except:
                pass
            
            # 전략 B: a.text (본문 요약 링크)
            if not link_url:
                try:
                    text_link = item.find_element(By.CSS_SELECTOR, "a.text")
                    link_url = text_link.get_attribute("href")
                except:
                    pass
            
            # 전략 C: 썸네일 링크
            if not link_url:
                try:
                    thumb_link = item.find_element(By.CSS_SELECTOR, "a.thumbnail_inner")
                    link_url = thumb_link.get_attribute("href")
                except:
                    pass
            
            # 전략 D: 아이템 내 모든 블로그 링크 검색
            if not link_url:
                try:
                    all_links = item.find_elements(By.TAG_NAME, "a")
                    for a in all_links:
                        href = a.get_attribute("href")
                        # 새 URL 패턴: /아이디/글번호 (숫자로 끝남)
                        if href and "blog.naver.com" in href:
                            if "/logNo=" in href or href.rstrip('/').split('/')[-1].isdigit():
                                link_url = href
                                break
                except: pass
            
            if not link_url:
                print("  ❌ 링크를 찾을 수 없음")
                # 디버그: 아이템 HTML 일부 출력
                try:
                    print(f"  ℹ️ 아이템 HTML 일부: {item.get_attribute('outerHTML')[:200]}")
                except: pass
                return False

            print(f"  🔗 링크 오픈: {link_url[:40]}...")
            
            # 2. 새 탭 열기
            self.driver.execute_script(f"window.open('{link_url}', '_blank');")
            time.sleep(3) # 페이지 로드 대기
            
            # 3. 탭 전환
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            success = False
            try:
                # 4. 댓글 작성 (iframe 처리 포함)
                success = self._write_comment_internal(comment_text)
            finally:
                # 5. 탭 닫기 및 복귀
                if len(self.driver.window_handles) > 1:
                    self.driver.close() # 현재 탭 닫기
                    self.driver.switch_to.window(self.driver.window_handles[0]) # 메인 탭 복귀
                else:
                    self.driver.switch_to.default_content()
            
            return success

        except Exception as e:
            print(f"  ⚠️ 새 탭 작업 실패: {e}")
            # 안전장치: 탭 복귀
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return False

    def _write_comment_internal(self, text):
        """현재 활성화된 페이지(탭)에서 공감 클릭 + 댓글 작성"""
        try:
            # 로딩 대기
            time.sleep(3)
            
            # iframe 전환 시도 (mainFrame)
            try:
                if self.driver.find_elements(By.ID, "mainFrame"):
                    WebDriverWait(self.driver, 5).until(
                        EC.frame_to_be_available_and_switch_to_it("mainFrame")
                    )
                    print("  📍 mainFrame 전환됨")
            except:
                pass
            
            # 1️⃣ 공감(좋아요) 클릭 - 'off' 상태면 클릭
            try:
                like_btn = self.driver.find_element(By.CSS_SELECTOR, ".u_likeit_button")
                btn_class = like_btn.get_attribute("class") or ""
                if "off" in btn_class:
                    # 🔧 더 안정적인 클릭: dispatchEvent로 마우스 이벤트 시뮬레이션
                    self.driver.execute_script("""
                        var btn = arguments[0];
                        ['mousedown', 'mouseup', 'click'].forEach(function(evtType) {
                            var event = new MouseEvent(evtType, {
                                view: window,
                                bubbles: true,
                                cancelable: true
                            });
                            btn.dispatchEvent(event);
                        });
                    """, like_btn)
                    print("  ❤️ 글 공감 클릭")
                    time.sleep(1)
                else:
                    print("  ℹ️ 이미 공감한 글")
            except Exception as e:
                print(f"  ⚠️ 공감 버튼 못 찾음: {e}")
            
            # 페이지 끝으로 스크롤 (댓글 영역 보이게)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            
            # 2️⃣ 댓글 입력창 찾기 - contenteditable div 또는 textarea
            comment_input = None
            
            # 우선순위 셀렉터 (contenteditable div 먼저)
            selectors = [
                ".u_cbox_text",  # Naver 댓글 입력 (contenteditable div)
                "div[contenteditable='true']",
                "textarea.u_cbox_text",
                "textarea[placeholder*='댓글']",
                "#cbox_module textarea"
            ]
            
            for sel in selectors:
                try:
                    comment_input = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    print(f"  📝 댓글창 발견: {sel}")
                    break
                except:
                    continue
            
            if not comment_input:
                print("  ⚠️ 댓글 입력창 못 찾음")
                self.driver.switch_to.default_content()
                return False
            
            # 3️⃣ 댓글 입력 (contenteditable div 지원)
            try:
                # 클릭하여 포커스
                self.driver.execute_script("arguments[0].click(); arguments[0].focus();", comment_input)
                time.sleep(0.5)
                
                # 태그 확인
                tag_name = comment_input.tag_name.lower()
                
                if tag_name == "div":
                    # contenteditable div인 경우
                    self.driver.execute_script("""
                        arguments[0].innerText = arguments[1];
                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    """, comment_input, text)
                else:
                    # textarea인 경우
                    self.driver.execute_script("arguments[0].value = '';", comment_input)
                    self.driver.execute_script(
                        "arguments[0].focus(); document.execCommand('insertText', false, arguments[1]);",
                        comment_input, text
                    )
                    self.driver.execute_script("""
                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    """, comment_input)
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  ⚠️ 입력 실패, send_keys 시도: {e}")
                try:
                    comment_input.clear()
                    comment_input.send_keys(text)
                except:
                    pass
            
            time.sleep(0.5)
            
            # 4️⃣ 등록 버튼 클릭
            btn_selectors = [
                ".u_cbox_btn_upload",
                "button.u_cbox_btn_upload",
                "button[class*='upload']",
                ".btn_register"
            ]
            
            submit_btn = None
            for sel in btn_selectors:
                try:
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if submit_btn.is_displayed():
                        break
                except:
                    continue
            
            if submit_btn:
                self.driver.execute_script("arguments[0].click();", submit_btn)
                print(f"  💬 댓글 등록 완료: {text[:30]}...")
                time.sleep(3)
                self.driver.switch_to.default_content()
                return True
            else:
                print("  ⚠️ 등록 버튼 못 찾음")
                self.driver.switch_to.default_content()
                return False
                
        except Exception as e:
            print(f"  ⚠️ 댓글 작성 중 오류: {e}")
            return False
        finally:
            # 기본 컨텐츠로 복귀
            try:
                self.driver.switch_to.default_content()
            except:
                pass

    def reply_to_new_comments(self, use_ai=False):
        """새 댓글에 답글 달기"""
        print("💬 새 댓글 확인 중...")
        
        try:
            # 내 블로그 댓글 관리 페이지로 이동
            self.driver.get("https://blog.naver.com/NVisitorguest498View.naver")
            time.sleep(3)
            
            # 댓글 알림 찾기
            comment_items = self.driver.find_elements(
                By.CSS_SELECTOR, ".comment_item, .list_comment li, .u_cbox_comment"
            )
            
            if not comment_items:
                print("ℹ️ 새 댓글이 없습니다.")
                return 0
            
            reply_count = 0
            
            for item in comment_items[:5]:  # 최근 5개만 처리
                if not self.is_running: break
                try:
                    # 댓글 ID 생성 (중복 방지)
                    comment_text = item.text[:100]
                    comment_hash = str(hash(comment_text))
                    
                    if comment_hash in self.replied_comments:
                        continue
                    
                    # 답글 작성하기 버튼 클릭
                    reply_btn = item.find_element(By.CSS_SELECTOR, ".btn_reply, button[class*='reply']")
                    self.driver.execute_script("arguments[0].click();", reply_btn)
                    time.sleep(1)
                    
                    # 답글 생성
                    if use_ai:
                        reply_text = self._generate_ai_reply(comment_text)
                    else:
                        reply_text = self._get_next_reply_phrase()
                    
                    # 답글 입력
                    reply_textarea = self.driver.find_element(By.CSS_SELECTOR, "textarea")
                    reply_textarea.clear()
                    reply_textarea.send_keys(reply_text)
                    time.sleep(0.5)
                    
                    # 등록
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .btn_register")
                    self.driver.execute_script("arguments[0].click();", submit_btn)
                    
                    # 기록
                    self.replied_comments[comment_hash] = {
                        'timestamp': datetime.now().timestamp(),
                        'comment': comment_text[:50],
                        'reply': reply_text
                    }
                    self._save_replied_comments()
                    reply_count += 1
                    print(f"✅ 답글 완료: {reply_text[:30]}...")
                    
                    time.sleep(2)
                    
                except Exception:
                    continue
            
            print(f"💬 답글 완료: {reply_count}개")
            return reply_count
            
        except Exception as e:
            print(f"❌ 댓글 답글 중 오류: {e}")
            return 0

    def _generate_ai_reply(self, comment_text):
        """AI 기반 답글 생성"""
        try:
            result = self.gpt_handler.generate_platform_content(
                topic=f"다음 댓글에 대한 따뜻하고 친근한 답글을 1-2문장으로 작성해주세요: '{comment_text}'",
                platform='idle'
            )
            reply = result.get('content', '')
            if len(reply) > 100: reply = reply[:100]
            return reply if reply else self._get_next_reply_phrase()
        except Exception:
            return self._get_next_reply_phrase()

    def reply_to_comments(self, use_ai=False):
        return self.reply_to_new_comments(use_ai)

    def reply_via_notification_center(self, use_ai=False, max_count=10, min_interval=30, max_interval=60):
        """
        네이버 알림센터를 통해 댓글에 답글 달기
        
        로직:
        1. 네이버 알림센터 열기
        2. a.link_notice 요소들 수집
        3. "네이버"가 포함된 알림 제외 (네이버, 네이버페이 등 공식 알림)
        4. 이미 읽은(어두운) 알림 제외
        5. 클릭하여 해당 블로그 글로 이동 → 답글 작성
        
        Args:
            use_ai: AI 답글 사용 여부
            max_count: 최대 처리 개수
            min_interval: 최소 대기 시간(초)
            max_interval: 최대 대기 시간(초)
        """
        print(f"🔔 알림센터 기반 댓글 답글 시작... (목표: 최대 {max_count}개)")
        self.is_running = True
        reply_count = 0
        
        try:
            # 1. 네이버 블로그 메인으로 이동 (알림센터 접근을 위해)
            print("📍 네이버 블로그 메인으로 이동...")
            self.driver.get("https://section.blog.naver.com/BlogHome.naver")
            time.sleep(3)
            
            # 2. 알림 버튼 클릭하여 알림센터 열기
            try:
                # 알림 버튼 찾기 (여러 선택자 시도)
                notification_btn_selectors = [
                    "button[class*='notice']",
                    "a[class*='notice']", 
                    ".btn_notice",
                    "button[aria-label*='알림']",
                    "#gnb_notice",
                    ".gnb_notice"
                ]
                
                notification_btn = None
                for sel in notification_btn_selectors:
                    try:
                        notification_btn = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                        )
                        if notification_btn:
                            break
                    except:
                        continue
                
                if notification_btn:
                    self.driver.execute_script("arguments[0].click();", notification_btn)
                    print("🔔 알림 버튼 클릭")
                    time.sleep(2)
                else:
                    # 버튼을 못 찾으면 직접 알림센터 URL로 이동
                    print("⚠️ 알림 버튼 못 찾음, 직접 URL로 이동...")
                    self.driver.get("https://notify.naver.com/list.html")
                    time.sleep(3)
                    
            except Exception as e:
                print(f"⚠️ 알림센터 열기 실패, 직접 URL로 이동: {e}")
                self.driver.get("https://notify.naver.com/list.html")
                time.sleep(3)
            
            # 3. 알림 목록 처리
            processed_notifications = set()  # 이번 세션에서 처리한 알림
            scroll_count = 0
            max_scrolls = 10  # 최대 스크롤 횟수
            
            while reply_count < max_count and self.is_running and scroll_count < max_scrolls:
                try:
                    # 알림 항목 찾기
                    time.sleep(1)
                    
                    # a.link_notice 요소들 찾기
                    notice_items = self.driver.find_elements(By.CSS_SELECTOR, "a.link_notice")
                    
                    if not notice_items:
                        # 대체 선택자 시도
                        notice_items = self.driver.find_elements(By.CSS_SELECTOR, 
                            ".notification_item, .notice_item, [class*='notification']"
                        )
                    
                    if not notice_items:
                        print("⚠️ 알림 항목을 찾을 수 없습니다.")
                        break
                    
                    print(f"📋 발견된 알림: {len(notice_items)}개")
                    
                    # 처리할 알림 찾기
                    target_item = None
                    
                    for item in notice_items:
                        try:
                            # 알림 텍스트 추출
                            item_text = item.text.strip()
                            accessibility_name = item.get_attribute("aria-label") or ""
                            
                            # 고유 ID 생성
                            item_id = str(hash(item_text + accessibility_name))
                            
                            # 이미 처리한 알림 건너뛰기
                            if item_id in processed_notifications:
                                continue
                            if item_id in self.replied_comments:
                                continue
                            
                            # "네이버" 포함 알림 제외 (네이버, 네이버페이 등 공식 알림)
                            full_text = (item_text + " " + accessibility_name).lower()
                            if "네이버" in full_text:
                                print(f"  ⏭️ 네이버 공식 알림 제외: {item_text[:30]}...")
                                processed_notifications.add(item_id)
                                continue
                            
                            # 이미 읽은 알림 확인 (클래스에 'read', 'visited', 'dim' 등이 있는지)
                            item_class = item.get_attribute("class") or ""
                            parent_class = ""
                            try:
                                parent = item.find_element(By.XPATH, "./..")
                                parent_class = parent.get_attribute("class") or ""
                            except:
                                pass
                            
                            combined_class = item_class + " " + parent_class
                            if any(kw in combined_class.lower() for kw in ["read", "visited", "dim", "disabled", "inactive"]):
                                print(f"  ⏭️ 이미 읽은 알림 제외: {item_text[:30]}...")
                                processed_notifications.add(item_id)
                                continue
                            
                            # 투명도 확인 (이미 읽은 알림은 어둡게 표시될 수 있음)
                            try:
                                opacity = self.driver.execute_script(
                                    "return window.getComputedStyle(arguments[0]).opacity;", item
                                )
                                if opacity and float(opacity) < 0.7:
                                    print(f"  ⏭️ 어두운(읽은) 알림 제외: {item_text[:30]}...")
                                    processed_notifications.add(item_id)
                                    continue
                            except:
                                pass
                            
                            # 색상 확인 (회색/연한 색상은 이미 읽은 알림일 수 있음)
                            try:
                                color = self.driver.execute_script(
                                    "return window.getComputedStyle(arguments[0]).color;", item
                                )
                                # 예: rgb(150, 150, 150) 같은 회색이면 이미 읽은 것
                                if color and "rgb" in color:
                                    # 간단한 회색 판단 (R, G, B 값이 비슷하고 밝은 경우)
                                    import re
                                    rgb_match = re.findall(r'\d+', color)
                                    if len(rgb_match) >= 3:
                                        r, g, b = int(rgb_match[0]), int(rgb_match[1]), int(rgb_match[2])
                                        # 회색 계열이고 밝은 경우 (이미 읽은 알림)
                                        if max(abs(r-g), abs(g-b), abs(r-b)) < 30 and r > 130:
                                            print(f"  ⏭️ 회색(읽은) 알림 제외: {item_text[:30]}...")
                                            processed_notifications.add(item_id)
                                            continue
                            except:
                                pass
                            
                            # 유효한 알림 발견!
                            target_item = item
                            processed_notifications.add(item_id)
                            print(f"✅ 처리할 알림 발견: {item_text[:50]}...")
                            break
                            
                        except StaleElementReferenceException:
                            continue
                        except Exception as e:
                            print(f"  ⚠️ 알림 확인 중 오류: {e}")
                            continue
                    
                    if not target_item:
                        # 더 이상 처리할 알림이 없으면 스크롤
                        print("  ⬇️ 더 처리할 알림 없음, 스크롤...")
                        self.driver.execute_script("window.scrollBy(0, 500);")
                        time.sleep(2)
                        scroll_count += 1
                        continue
                    
                    # 4. 알림 클릭하여 해당 페이지로 이동
                    try:
                        # 알림 링크 URL 가져오기
                        notice_href = target_item.get_attribute("href")
                        
                        if notice_href:
                            # 새 탭에서 열기
                            self.driver.execute_script(f"window.open('{notice_href}', '_blank');")
                            time.sleep(3)
                            
                            # 새 탭으로 전환
                            self.driver.switch_to.window(self.driver.window_handles[-1])
                            
                            try:
                                # 답글 작성
                                if self._write_reply_on_page(use_ai):
                                    reply_count += 1
                                    
                                    # 답글 기록 저장
                                    self.replied_comments[str(hash(notice_href))] = {
                                        'timestamp': datetime.now().timestamp(),
                                        'url': notice_href[:100]
                                    }
                                    self._save_replied_comments()
                                    
                                    print(f"✅ 답글 완료! ({reply_count}/{max_count})")
                                else:
                                    print("  ⚠️ 답글 작성 실패")
                                    
                            finally:
                                # 탭 닫고 원래 탭으로 복귀
                                if len(self.driver.window_handles) > 1:
                                    self.driver.close()
                                    self.driver.switch_to.window(self.driver.window_handles[0])
                        else:
                            # href 없으면 직접 클릭
                            self.driver.execute_script("arguments[0].click();", target_item)
                            time.sleep(3)
                            
                            # 답글 작성
                            if self._write_reply_on_page(use_ai):
                                reply_count += 1
                                print(f"✅ 답글 완료! ({reply_count}/{max_count})")
                            
                            # 알림센터로 돌아가기
                            self.driver.back()
                            time.sleep(2)
                            
                    except Exception as e:
                        print(f"  ⚠️ 알림 처리 중 오류: {e}")
                        # 안전하게 원래 탭으로 복귀
                        try:
                            if len(self.driver.window_handles) > 1:
                                self.driver.switch_to.window(self.driver.window_handles[0])
                        except:
                            pass
                    
                    # 대기
                    if reply_count < max_count and self.is_running:
                        wait_time = random.randint(min_interval, max_interval)
                        print(f"⏰ {wait_time}초 대기...")
                        
                        for i in range(0, wait_time, 5):
                            if not self.is_running:
                                break
                            time.sleep(min(5, wait_time - i))
                        
                        if not self.is_running:
                            break
                    
                except Exception as e:
                    print(f"⚠️ 알림 처리 루프 오류: {e}")
                    scroll_count += 1
                    time.sleep(2)
            
            print(f"🎉 알림센터 댓글 답글 완료: {reply_count}개")
            return reply_count
            
        except Exception as e:
            print(f"❌ 알림센터 답글 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return reply_count
        finally:
            self.is_running = False

    def _write_reply_on_page(self, use_ai=False):
        """
        현재 페이지에서 댓글에 답글 작성
        (블로그 글 페이지에서 호출됨)
        """
        try:
            time.sleep(2)
            
            # mainFrame으로 전환 (네이버 블로그 구조)
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.frame_to_be_available_and_switch_to_it("mainFrame")
                )
            except:
                pass  # 프레임이 없는 경우도 있음
            
            # 답글 버튼 찾기 (여러 선택자 시도)
            reply_btn_selectors = [
                ".u_cbox_btn_reply",
                "button[class*='reply']",
                ".btn_reply",
                "a[class*='reply']",
                "[data-action='reply']"
            ]
            
            reply_btn = None
            for sel in reply_btn_selectors:
                try:
                    reply_btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    if reply_btn:
                        break
                except:
                    continue
            
            if not reply_btn:
                # 답글 버튼이 없으면 일반 댓글로 작성
                print("  ℹ️ 답글 버튼 없음, 일반 댓글로 작성...")
                return self._write_comment_as_reply(use_ai)
            
            # 답글 버튼 클릭
            self.driver.execute_script("arguments[0].click();", reply_btn)
            time.sleep(1)
            
            # 답글 텍스트 생성
            if use_ai:
                # 원 댓글 텍스트 가져오기 시도
                try:
                    original_comment = self.driver.find_element(
                        By.CSS_SELECTOR, ".u_cbox_text_wrap, .comment_text"
                    ).text[:200]
                    reply_text = self._generate_ai_reply(original_comment)
                except:
                    reply_text = self._get_next_reply_phrase()
            else:
                reply_text = self._get_next_reply_phrase()
            
            # 답글 입력창 찾기
            reply_textarea_selectors = [
                "textarea.u_cbox_text",
                "textarea[placeholder*='답글']",
                ".u_cbox_write_wrap textarea",
                "textarea"
            ]
            
            reply_textarea = None
            for sel in reply_textarea_selectors:
                try:
                    reply_textarea = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    if reply_textarea:
                        break
                except:
                    continue
            
            if not reply_textarea:
                print("  ⚠️ 답글 입력창 못 찾음")
                self.driver.switch_to.default_content()
                return False
            
            # 답글 입력
            try:
                reply_textarea.click()
            except:
                self.driver.execute_script("arguments[0].click();", reply_textarea)
            
            time.sleep(0.5)
            reply_textarea.clear()
            reply_textarea.send_keys(reply_text)
            time.sleep(0.5)
            
            # 등록 버튼 클릭
            submit_btn_selectors = [
                "button.u_cbox_btn_upload",
                ".btn_register",
                "button[type='submit']",
                "button[class*='upload']"
            ]
            
            submit_btn = None
            for sel in submit_btn_selectors:
                try:
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if submit_btn:
                        break
                except:
                    continue
            
            if submit_btn:
                self.driver.execute_script("arguments[0].click();", submit_btn)
                print(f"  💬 답글 등록: {reply_text[:30]}...")
                time.sleep(2)
                self.driver.switch_to.default_content()
                return True
            else:
                print("  ⚠️ 등록 버튼 못 찾음")
                self.driver.switch_to.default_content()
                return False
                
        except Exception as e:
            print(f"  ⚠️ 답글 작성 중 오류: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False

    def _write_comment_as_reply(self, use_ai=False):
        """
        답글 버튼이 없는 경우 일반 댓글로 답글 작성
        """
        try:
            # 감사 댓글 작성
            if use_ai:
                reply_text = self._get_next_reply_phrase()  # 간단한 감사 문구
            else:
                reply_text = self._get_next_reply_phrase()
            
            return self._write_comment_internal(reply_text)
            
        except Exception as e:
            print(f"  ⚠️ 댓글 작성 중 오류: {e}")
            return False
