import time
import random
import traceback
import subprocess
import sys

# pyperclip 설치 확인 및 설치
try:
    import pyperclip
except ImportError:
    print("📦 pyperclip 모듈 설치 중...")
    if getattr(sys, 'frozen', False):
        print("[Warning] 빌드된 앱에서는 pip install을 실행할 수 없습니다. pyperclip 기능을 건너뜁니다.")
        pyperclip = None
    else:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyperclip"])
        import pyperclip

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains

class NaverBandCommentReply:
    """
    네이버 밴드 댓글 자동 답글 시스템
    - 게시글의 댓글을 읽고 AI로 답글 작성
    - 운영자/관장 댓글은 스킵
    - 이미 답글 단 댓글은 스킵
    """
    
    def __init__(self, driver, ai_handler=None, base_dir=None, instruction=None, gpt_handler=None):
        self.driver = driver
        self.ai_handler = ai_handler or gpt_handler
        self.base_dir = base_dir
        self.instruction = instruction
        self.stop_flag = False
        
        # 운영자/관장 키워드 (스킵 대상)
        self.MANAGER_KEYWORDS = [
            '관장', '관장님', '사범', '사범님', '매니저', '리더', '공동리더', 
            '운영자', '지도자', '상담사', '선생', '선생님', '이관원', '부평라이온'
        ]
        
        # 스팸 키워드 (🔧 개선: '홍보' 대신 더 구체적인 패턴 사용)
        self.SPAM_KEYWORDS = [
            # '홍보' 단독 제거 → 이름에 포함될 수 있음 (예: 홍보람)
            '홍보글', '홍보합니다', '홍보드립니다', '홍보해요',
            '광고', '판매', '할인', '무료체험', '무료상담', 
            '카톡', '카카오톡', '문의주세요', '연락주세요',
            'http', 'www.', '.com', '.kr', 
            '대출', '투자', '수익', '부업', '알바', '재테크',
            '다이어트', '살빠지는', '무료강좌', '선착순'
        ]
        
        # 스팸이 아닌 문맥 (신청, 등록 등)
        self.NOT_SPAM_CONTEXT = [
            '신청합니다', '등록합니다', '신청해요', '신청이요',
            '참가합니다', '참가신청', '수업신청', '캠프', '둘다'
        ]
        self.SPAM_REPLY = "안녕하세요! 이곳은 광고나 홍보를 위한 공간이 아닙니다. 댓글 삭제 부탁드립니다."
        
        # 기본 답글 (AI 실패 시 사용) - 간단하고 자연스럽게
        self.DEFAULT_REPLIES = [
            "잘 보고 갑니다! 좋은 하루 되세요~"
        ]
        self.default_reply_index = 0

    def _get_next_default_reply(self):
        reply = self.DEFAULT_REPLIES[self.default_reply_index]
        self.default_reply_index = (self.default_reply_index + 1) % len(self.DEFAULT_REPLIES)
        return reply

    def stop(self):
        """작업 중지"""
        self.stop_flag = True
        print("🛑 밴드 댓글 답글 중지 요청됨...")

    def process_band_comments(self, band_url: str, use_ai: bool = True, limit: int = 5):
        """
        밴드 댓글 자동 답글 메인 함수
        """
        self.stop_flag = False
        
        try:
            print(f"🚀 밴드 댓글 답글 자동화 시작... (최근 {limit}개 글)")
            
            # 1. 밴드 피드로 이동
            if band_url not in self.driver.current_url:
                print(f"📍 밴드로 이동: {band_url}")
                self.driver.get(band_url)
                time.sleep(4)
            
            feed_url = self.driver.current_url
            
            # 2. 메인 화면 스크롤
            print("📜 메인 화면 스크롤 중...")
            self._scroll_main_page(limit)
            
            # 3. 게시글 URL 수집
            post_urls = self._collect_post_urls(limit)
            
            if not post_urls:
                print("  ⚠️ 처리할 게시글이 없습니다.")
                return True
            
            print(f"📝 총 {len(post_urls)}개의 게시글 URL 수집 완료")
            
            total_replied = 0
            
            # 4. 각 게시글 처리
            for i, post_url in enumerate(post_urls):
                if self.stop_flag: 
                    break
                
                print(f"\n[{i+1}/{len(post_urls)}] 게시글 처리 중...")
                
                try:
                    # 게시글 상세 페이지로 이동
                    self.driver.get(post_url)
                    time.sleep(3)
                    
                    # 댓글 영역으로 스크롤
                    self._scroll_to_comments()
                    
                    # 댓글에 답글 달기
                    replied = self._process_comments_on_page(use_ai)
                    total_replied += replied
                    
                    if replied > 0:
                        print(f"  ✅ 이 게시글에서 {replied}개 답글 완료")
                    
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"  ❌ 게시글 처리 오류: {e}")
                    continue
            
            # 5. 완료
            print(f"\n✨ 완료! 총 {total_replied}개의 답글을 달았습니다.")
            return True
            
        except Exception as e:
            print(f"❌ 치명적 오류: {e}")
            traceback.print_exc()
            return False

    def _scroll_main_page(self, count):
        """메인 피드 스크롤"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        for _ in range(7):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

    def _collect_post_urls(self, limit):
        """게시글 URL 수집 (댓글이 있는 것만)"""
        post_urls = []
        
        # 게시글 링크 찾기 (a.text 또는 시간 링크)
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, "a.text[href*='/post/']")
            for link in links:
                href = link.get_attribute("href")
                if href and "/post/" in href and href not in post_urls:
                    post_urls.append(href)
                    if len(post_urls) >= limit:
                        break
        except:
            pass
        
        # 대체: 시간 링크로 찾기
        if len(post_urls) < limit:
            try:
                time_links = self.driver.find_elements(By.CSS_SELECTOR, "a.time[href*='/post/']")
                for link in time_links:
                    href = link.get_attribute("href")
                    if href and "/post/" in href and href not in post_urls:
                        post_urls.append(href)
                        if len(post_urls) >= limit:
                            break
            except:
                pass
        
        return post_urls[:limit]

    def _scroll_to_comments(self):
        """댓글 영역으로 스크롤 - 모든 댓글 로드"""
        try:
            # 여러 번 스크롤하여 모든 댓글 로드
            last_height = 0
            for _ in range(5):  # 최대 5회 스크롤
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            # 맨 위로 돌아가서 처음부터 처리
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
        except:
            pass

    def _process_comments_on_page(self, use_ai):
        """현재 페이지에서 댓글 처리 - 답글쓰기 버튼 사용"""
        replied_count = 0
        processed_authors = set()  # 이미 처리한 작성자 추적
        
        try:
            # ★ 핵심: 답글쓰기 버튼들 찾기 ★
            time.sleep(2)  # 페이지 로딩 대기
            reply_btn_selectors = "button._replyBtn, button.reply, button.btn_reply, button.comment_reply"
            reply_buttons = self.driver.find_elements(By.CSS_SELECTOR, reply_btn_selectors)
            
            if not reply_buttons:
                print("  ℹ️ 답글쓰기 버튼을 찾을 수 없습니다. (댓글이 없거나 로딩 실패)")
                return 0
            
            total_buttons = len(reply_buttons)
            print(f"  📋 답글쓰기 버튼 {total_buttons}개 발견")
            
            # 🔧 개선: 인덱스 대신 while 루프로 모든 버튼 처리
            processed_count = 0
            max_iterations = total_buttons + 10  # 무한 루프 방지
            
            while processed_count < max_iterations:
                if self.stop_flag: 
                    break
                
                try:
                    # 버튼 다시 찾기 (DOM 변경 대응)
                    reply_buttons = self.driver.find_elements(By.CSS_SELECTOR, reply_btn_selectors)
                    
                    if not reply_buttons:
                        break
                    
                    # 아직 처리 안 된 버튼 찾기
                    target_btn = None
                    target_info = None
                    
                    for btn in reply_buttons:
                        try:
                            # 버튼을 화면에 보이게 스크롤
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({block: 'center'});", btn
                            )
                            time.sleep(0.3)
                            
                            comment_info = self._get_comment_info(btn)
                            if not comment_info:
                                continue
                            
                            author_name = comment_info['author']
                            
                            # 이미 처리한 작성자인지 확인
                            if author_name in processed_authors:
                                continue
                            
                            # 운영자/관장 댓글 스킵
                            if self._is_manager(author_name):
                                processed_authors.add(author_name)
                                continue
                            
                            # 이미 답글이 달린 댓글 스킵
                            if self._has_my_reply_nearby(btn):
                                processed_authors.add(author_name)
                                continue
                            
                            # 처리할 대상 발견!
                            target_btn = btn
                            target_info = comment_info
                            break
                            
                        except Exception:
                            continue
                    
                    # 처리할 대상이 없으면 종료
                    if not target_btn or not target_info:
                        print("  ℹ️ 처리할 댓글이 더 이상 없습니다.")
                        break
                    
                    author_name = target_info['author']
                    comment_text = target_info['text']
                    
                    # 스팸 체크
                    is_spam = self._is_spam(comment_text)
                    
                    print(f"  💬 [{author_name}] 댓글: {comment_text[:30]}...")
                    
                    # 답글 작성
                    if self._write_reply(target_btn, author_name, comment_text, use_ai, is_spam):
                        replied_count += 1
                        processed_authors.add(author_name)
                        time.sleep(3)  # 전송 후 대기
                    else:
                        # 실패해도 일단 처리됨으로 표시 (무한 루프 방지)
                        processed_authors.add(author_name)
                    
                    processed_count += 1
                    
                except Exception as e:
                    print(f"  ⚠️ 개별 댓글 처리 오류: {e}")
                    processed_count += 1
                    continue
            
            return replied_count
            
        except Exception as e:
            print(f"  ❌ 댓글 처리 오류: {e}")
            return 0

    def _get_comment_info(self, reply_btn):
        """답글쓰기 버튼에서 댓글 정보 추출"""
        try:
            # 버튼의 부모/조상 요소에서 정보 찾기
            parent = reply_btn
            for _ in range(5):  # 최대 5단계 상위로
                parent = parent.find_element(By.XPATH, "..")
                
                # 작성자 이름 찾기
                try:
                    name_el = parent.find_element(By.CSS_SELECTOR, "button.nameWrap strong")
                    author = name_el.text.strip()
                    
                    # 댓글 내용 찾기 - 더 정확한 셀렉터 사용
                    text = ""
                    try:
                        # 우선 순위: 1) commentBody 직접 텍스트, 2) p.txt
                        text_el = parent.find_element(By.CSS_SELECTOR, "p.txt, span.txt")
                        text = text_el.text.strip()
                    except:
                        try:
                            text_el = parent.find_element(By.CSS_SELECTOR, "div.commentBody")
                            text = text_el.text.strip()
                        except:
                            pass
                    
                    # 불필요한 텍스트 제거 (시간, 버튼 텍스트 등)
                    text = self._clean_comment_text(text)
                    
                    if author:
                        return {'author': author, 'text': text}
                except:
                    continue
            
            return None
        except:
            return None

    def _clean_comment_text(self, text):
        """댓글 텍스트에서 불필요한 부분 제거"""
        import re
        
        if not text:
            return ""
        
        # 시간 정보 제거 (예: "4시간 전", "12월 30일 오후 2:39")
        text = re.sub(r'\d+시간 전', '', text)
        text = re.sub(r'\d+분 전', '', text)
        text = re.sub(r'\d+월 \d+일.*', '', text)
        text = re.sub(r'어제|오늘', '', text)
        
        # UI 버튼 텍스트 제거
        remove_words = ['표정짓기', '답글쓰기', '좋아요', '더보기']
        for word in remove_words:
            text = text.replace(word, '')
        
        # 연속 공백/줄바꿈 정리
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def _is_manager(self, name):
        """운영자/관장인지 확인"""
        for keyword in self.MANAGER_KEYWORDS:
            if keyword in name:
                return True
        return False

    def _has_my_reply_nearby(self, reply_btn):
        """
        이미 내(관장/운영자) 답글이 있는지 확인
        
        🔧 개선: 멘션과 관계없이 바로 다음에 운영자 답글이 있으면 스킵
        (닉네임 변경 등으로 멘션 불일치 문제 해결)
        """
        try:
            # 모든 답글쓰기 버튼 찾기
            all_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button._replyBtn, button.reply, button.btn_reply, button.comment_reply")
            
            # 현재 버튼의 인덱스 찾기
            current_index = -1
            for idx, btn in enumerate(all_buttons):
                try:
                    if btn == reply_btn:
                        current_index = idx
                        break
                except:
                    continue
            
            if current_index == -1 or current_index >= len(all_buttons) - 1:
                return False
            
            # 현재 댓글 작성자 확인
            current_author = self._get_comment_info(reply_btn)
            if not current_author:
                return False
            current_name = current_author.get('author', '')
            
            # 🔧 개선: 바로 다음 버튼들만 확인 (최대 3개)
            # 연속된 운영자 답글이 있으면 무조건 스킵 (멘션 확인 완화)
            for next_idx in range(current_index + 1, min(current_index + 4, len(all_buttons))):
                try:
                    next_btn = all_buttons[next_idx]
                    next_info = self._get_comment_info(next_btn)
                    
                    if not next_info:
                        continue
                    
                    next_name = next_info.get('author', '')
                    next_text = next_info.get('text', '')
                    
                    # 🔑 핵심 수정: 운영자 답글이 있으면 멘션 관계없이 스킵
                    if self._is_manager(next_name):
                        # 방법 1: 멘션이 있으면 확실히 스킵
                        if f"@{current_name}" in next_text or current_name in next_text[:30]:
                            print(f"    ⚠️ 이미 운영자 답글 있음 (멘션 일치): {next_name}")
                            return True
                        
                        # 방법 2: 멘션이 없어도 바로 다음이 운영자 답글이면 스킵
                        # (닉네임 변경 등 대응)
                        if next_idx == current_index + 1:
                            print(f"    ⚠️ 이미 운영자 답글 있음 (바로 다음): {next_name}")
                            return True
                    else:
                        # 다른 일반 사용자 댓글을 만나면 연속성 끊김
                        break
                        
                except:
                    continue
            
            return False
            
        except Exception as e:
            return False

    def _is_spam(self, text):
        """스팸인지 확인 (🔧 개선: 신청 문맥이면 스팸 아님)"""
        if not text:
            return False
        
        # 신청/등록 문맥이면 스팸이 아님
        for context in self.NOT_SPAM_CONTEXT:
            if context in text:
                return False
        
        # 스팸 키워드 확인
        for keyword in self.SPAM_KEYWORDS:
            if keyword in text:
                return True
        
        return False

    def _write_reply(self, reply_btn, author_name, comment_text, use_ai, is_spam):
        """답글 작성 - 답글쓰기 버튼 클릭 → 입력 → 전송"""
        try:
            # 1. 답글쓰기 버튼 클릭
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", reply_btn)
            time.sleep(0.5)
            
            try:
                reply_btn.click()
            except:
                self.driver.execute_script("arguments[0].click();", reply_btn)
            
            time.sleep(1.5)
            
            # 2. 입력창 찾기 (textarea._messageTextArea)
            input_box = None
            try:
                input_box = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "textarea._messageTextArea"))
                )
            except:
                print("  ⚠️ 입력창을 찾을 수 없습니다.")
                return False
            
            # 3. 답글 생성
            if is_spam:
                reply = self.SPAM_REPLY
            elif use_ai and self.ai_handler:
                reply = self.ai_handler.generate_platform_content(
                    topic=f"다음 밴드 댓글에 대해 학부모님/관원에게 답변하듯 따뜻하고 긍정적인 답글을 1-2문장으로 작성해주세요: '{comment_text}'",
                    platform='idle'
                ).get('content', self._get_next_default_reply())
            else:
                reply = self._get_next_default_reply()
            
            # 4. 입력창에 답글 입력 (클립보드 사용으로 이모지 에러 방지)
            input_box.click()
            time.sleep(0.3)
            
            # 기존 내용 지우기 (@ 태그 뒤에 바로 추가하려면 필요 없음)
            # 하지만 잔여 텍스트 방지를 위해
            try:
                # 현재 텍스트 확인
                current_text = input_box.get_attribute("value") or ""
                if "@" in current_text:
                    # @ 태그가 있으면 그 뒤에 추가
                    pass
                else:
                    # @ 태그 없으면 추가
                    input_box.send_keys(f"@{author_name} ")
            except:
                pass
            
            # 클립보드 붙여넣기(Cmd+V)는 백그라운드/셀레니움 환경에서 조용히 실패하여 빈 내용이 날아가는 원인이 됨.
            # 이모지를 제거하고 직접 send_keys로 확실하게 입력함.
            clean_reply = self._remove_emoji(reply)
            input_box.send_keys(clean_reply)
            
            time.sleep(1.0)
            
            # 5. 보내기 버튼 클릭 (button._sendMessageButton)
            try:
                send_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button._sendMessageButton"))
                )
                self.driver.execute_script("arguments[0].click();", send_btn)
                print(f"  ✅ [{author_name}]님께 답글 전송 완료!")
                return True
            except:
                # 엔터키 시도
                input_box.send_keys(Keys.ENTER)
                print(f"  ✅ [{author_name}]님께 답글 전송 완료! (Enter)")
                return True
            
        except Exception as e:
            print(f"  ❌ 답글 작성 오류: {e}")
            return False

    def _generate_ai_reply(self, comment_text):
        """AI로 답글 생성"""
        if not self.gpt_handler:
            return self._get_next_default_reply()
        
        # 사용자 설정 지침이 있으면 사용, 없으면 기본 지침 사용
        if self.instruction:
            system_prompt = self.instruction
        else:
            system_prompt = """당신은 친절하고 따뜻한 합기도 체육관 관장님입니다.

[답글 작성 지침]
1. 상대방의 댓글 내용을 읽고 핵심 내용이나 뉘앙스에 맞춰 사람 냄새 나는 자연스러운 답글을 작성하세요.
2. 기계적인 단답형(예: "감사합니다", "좋은 하루 되세요")은 피하고, 댓글 내용에 직접적으로 반응해 주세요.
3. 1~2문장(30~50자 내외)으로 정성스럽게 작성하세요.
4. 존댓말을 사용하세요.
5. 매번 똑같은 이모지(😊 등)를 남발하지 마세요. 이모지는 빼도 좋으며 아주 자연스러울 때만 1개 정도 사용하세요.
6. 호칭이나 이름은 사용하지 마세요.
7. 답글만 출력하세요 (기타 설명 제외).
"""
        
        user_text = f"댓글: {comment_text}\n\n위 댓글에 자연스럽고 간단한 답글을 작성해주세요."
        
        try:
            # generate_reply 메서드 사용 (GPTHandler에 추가됨)
            response = self.gpt_handler.generate_reply(
                system_prompt=system_prompt,
                user_text=user_text,
                max_tokens=150
            )
            return response.strip() if response else self._get_next_default_reply()
        except Exception as e:
            print(f"  ⚠️ AI 생성 오류: {e}")
            return self._get_next_default_reply()

    def _remove_emoji(self, text):
        """이모지 제거"""
        import re
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", 
            flags=re.UNICODE
        )
        return emoji_pattern.sub('', text)
