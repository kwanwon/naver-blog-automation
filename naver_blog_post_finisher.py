from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import json
import os
import sys
import traceback

# 리소스 경로 처리 함수 추가
def resource_path(relative_path):
    """앱이 번들되었을 때와 그렇지 않을 때 모두 리소스 경로를 올바르게 가져옵니다."""
    try:
        # PyInstaller가 만든 임시 폴더에서 실행될 때
        base_path = sys._MEIPASS
    except Exception:
        # 일반적인 Python 인터프리터에서 실행될 때
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class NaverBlogPostFinisher:
    def __init__(self, driver, settings):
        self.driver = driver
        self.settings = settings
        
    def handle_browser_popups(self):
        """브라우저 팝업 처리 (권한 요청 등) - 클립보드 권한 팝업 전용"""
        try:
            print("🔍 클립보드 권한 팝업 확인 및 처리 중...")
            
            # 1. 브라우저 알림 창 처리 (JavaScript Alert/Confirm)
            try:
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                print(f"브라우저 알림 창 발견: {alert_text}")
                if "클립보드" in alert_text or "복사" in alert_text or "텍스트" in alert_text or "이미지" in alert_text or "허용" in alert_text:
                    alert.accept()  # 허용 클릭
                    print("✅ 클립보드 권한 알림 창 허용 처리 완료")
                    time.sleep(1)
                    return True
                else:
                    alert.dismiss()  # 취소 클릭
                    print("✅ 기타 알림 창 취소 처리 완료")
                    time.sleep(1)
                    return True
            except:
                pass  # 알림 창이 없으면 무시
            
            # 2. 페이지 내 클립보드 권한 팝업 처리 (강화된 버전)
            popup_handled = self.driver.execute_script("""
            function handleClipboardPopups() {
                console.log('클립보드 팝업 처리 시작...');
                let handled = false;
                
                // 모든 버튼 검사
                const allButtons = document.querySelectorAll('button, input[type="button"], div[role="button"]');
                console.log('총 버튼 수:', allButtons.length);
                
                for (const btn of allButtons) {
                    const text = btn.innerText ? btn.innerText.trim() : '';
                    const title = btn.title || '';
                    const ariaLabel = btn.getAttribute('aria-label') || '';
                    const isVisible = btn.offsetWidth > 0 && btn.offsetHeight > 0;
                    
                    // 클립보드 관련 텍스트 확인
                    const isClipboardButton = text === '허용' || text === '확인' || text === 'Allow' || 
                                            title.includes('허용') || title.includes('확인') ||
                                            ariaLabel.includes('허용') || ariaLabel.includes('확인');
                    
                    if (isVisible && isClipboardButton) {
                        console.log('클립보드 권한 버튼 발견:', {
                            text: text,
                            title: title,
                            ariaLabel: ariaLabel,
                            className: btn.className
                        });
                        
                        try {
                            btn.click();
                            console.log('클립보드 권한 버튼 클릭 성공');
                            handled = true;
                            break;
                        } catch (e) {
                            console.log('버튼 클릭 오류:', e);
                        }
                    }
                }
                
                // 특정 클래스나 ID로 팝업 찾기
                const popupSelectors = [
                    '[class*="popup"]',
                    '[class*="dialog"]',
                    '[class*="modal"]',
                    '[id*="popup"]',
                    '[id*="dialog"]',
                    '[id*="modal"]'
                ];
                
                for (const selector of popupSelectors) {
                    const popups = document.querySelectorAll(selector);
                    for (const popup of popups) {
                        if (popup.offsetWidth > 0 && popup.offsetHeight > 0) {
                            const popupText = popup.innerText || '';
                            if (popupText.includes('클립보드') || popupText.includes('복사') || popupText.includes('허용')) {
                                console.log('클립보드 관련 팝업 발견:', popupText.substring(0, 100));
                                
                                // 팝업 내의 허용 버튼 찾기
                                const allowButtons = popup.querySelectorAll('button, input[type="button"]');
                                for (const allowBtn of allowButtons) {
                                    const btnText = allowBtn.innerText ? allowBtn.innerText.trim() : '';
                                    if (btnText === '허용' || btnText === '확인' || btnText === 'Allow') {
                                        console.log('팝업 내 허용 버튼 클릭:', btnText);
                                        allowBtn.click();
                                        handled = true;
                                        break;
                                    }
                                }
                                if (handled) break;
                            }
                        }
                    }
                    if (handled) break;
                }
                
                console.log('클립보드 팝업 처리 결과:', handled);
                return handled;
            }
            
            return handleClipboardPopups();
            """)
            
            if popup_handled:
                print("✅ 클립보드 권한 페이지 팝업 처리 완료")
                time.sleep(2)
                return True
            
            # 3. 반복 확인 (팝업이 지연되어 나타날 수 있음)
            for attempt in range(3):
                time.sleep(1)
                print(f"클립보드 팝업 재확인 {attempt + 1}/3...")
                
                try:
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    print(f"지연된 알림 창 발견: {alert_text}")
                    if "클립보드" in alert_text or "복사" in alert_text or "허용" in alert_text:
                        alert.accept()
                        print("✅ 지연된 클립보드 권한 알림 처리 완료")
                        return True
                except:
                    pass
                
                # JavaScript로 다시 확인
                delayed_popup = self.driver.execute_script("""
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    const text = btn.innerText ? btn.innerText.trim() : '';
                    const isVisible = btn.offsetWidth > 0 && btn.offsetHeight > 0;
                    if (isVisible && (text === '허용' || text === '확인')) {
                        console.log('지연된 팝업 버튼 클릭:', text);
                        btn.click();
                        return true;
                    }
                }
                return false;
                """)
                
                if delayed_popup:
                    print("✅ 지연된 클립보드 팝업 처리 완료")
                    time.sleep(1)
                    return True
            
            # 4. 여전히 팝업이 나타남 → 두 번째 방법(새로고침) 시도
            print("⚠️ 여전히 팝업이 나타남 → 두 번째 방법(새로고침) 시도")
            try:
                current_url = self.driver.current_url
                print(f"현재 URL: {current_url}")
                
                # 페이지 새로고침
                print("🔄 페이지 새로고침 중...")
                self.driver.refresh()
                time.sleep(3)
                
                # 새로고침 후 팝업 재확인
                print("🔍 새로고침 후 팝업 재확인...")
                for refresh_attempt in range(2):
                    print(f"새로고침 후 팝업 확인 {refresh_attempt + 1}/2...")
                    
                    # 브라우저 알림창 확인
                    try:
                        alert = self.driver.switch_to.alert
                        alert_text = alert.text
                        print(f"🎯 새로고침 후 브라우저 알림창 발견: {alert_text}")
                        if "클립보드" in alert_text or "복사" in alert_text or "허용" in alert_text:
                            alert.accept()
                            print("✅ 새로고침 후 브라우저 알림창 처리 완료")
                            return True
                    except:
                        pass
                    
                    # 페이지 내 팝업 재확인
                    popup_found_after_refresh = self.driver.execute_script("""
                    function handleClipboardPopupsAfterRefresh() {
                        console.log('새로고침 후 클립보드 팝업 재확인...');
                        let handled = false;
                        
                        const allButtons = document.querySelectorAll('button, input[type="button"], div[role="button"]');
                        for (const btn of allButtons) {
                            const text = btn.innerText ? btn.innerText.trim() : '';
                            const isVisible = btn.offsetWidth > 0 && btn.offsetHeight > 0;
                            
                            if (isVisible && (text === '허용' || text === '확인' || text === 'Allow')) {
                                console.log('🎯 새로고침 후 허용 버튼 발견!', text);
                                btn.click();
                                console.log('✅ 새로고침 후 허용 버튼 클릭 완료');
                                handled = true;
                                break;
                            }
                        }
                        
                        console.log('새로고침 후 클립보드 팝업 처리 결과:', handled);
                        return handled;
                    }
                    
                    return handleClipboardPopupsAfterRefresh();
                    """)
                    
                    if popup_found_after_refresh:
                        print("✅ 새로고침 후 클립보드 팝업 처리 완료")
                        return True
                    
                    time.sleep(1)
                
                print("✅ 새로고침 완료 - 팝업 처리됨 또는 팝업 없음")
                return True
                
            except Exception as e:
                print(f"새로고침 중 오류 발생: {str(e)}")
                print("기본 팝업 처리 완료로 간주")
                return False
            
            print("ℹ️ 클립보드 권한 팝업이 발견되지 않았습니다")
            return False
                
        except Exception as e:
            print(f"클립보드 팝업 처리 중 오류: {str(e)}")
            return False

    def add_footer(self):
        """
        블로그 포스트에 푸터를 추가합니다:
        1. 줄바꿈으로 공간 확보
        2. 카카오톡 오픈채팅 링크 추가
        3. 도장 위치 추가
        """
        try:
            print("\n=== 푸터 추가 시작 ====")
            
            success = True
            
            # 줄바꿈 3번
            actions = ActionChains(self.driver)
            for _ in range(3):
                actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
                time.sleep(0.2)
            print("줄바꿈 3번 완료")

            # 카카오톡 링크 추가 전 줄바꿈
            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
            time.sleep(0.2)
            print("카카오톡 링크 추가 전 줄바꿈 완료")
            
            # 도장 이름 확인 - 설정에 없을 경우 기본값 사용
            dojang_name = self.settings.get('dojang_name', '라이온짐')
            print(f"푸터에 사용할 도장 이름: {dojang_name}")
            
            # 슬로건은 GPT 생성 본문에 이미 포함되어 있으므로 여기서는 추가하지 않음
            # 바로 상담&문의 섹션으로 진행
            
            # 줄바꿈 2번
            actions = ActionChains(self.driver)
            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
            time.sleep(0.2)
            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
            time.sleep(0.2)

            # -상담&문의- 텍스트 추가
            actions.send_keys("-상담&문의-").perform()
            time.sleep(0.2)
            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
            time.sleep(0.2)

            # 네이버 전화와 카카오톡 텍스트 추가
            actions.send_keys("네이버 전화와").perform()
            time.sleep(0.2)
            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
            time.sleep(0.2)
            actions.send_keys("카톡 오픈채팅 상담 가능합니다^^").perform()
            time.sleep(0.2)
            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
            time.sleep(0.2)

            # 카카오톡 오픈채팅 링크 추가
            try:
                print("\n==== 카카오톡 링크 추가 시작 ====")
                kakao_url = self.settings.get('kakao_url')
                print(f"사용할 카카오 URL: '{kakao_url}'")
                
                if not kakao_url:
                    print("⚠️ 카카오 URL이 설정되지 않았습니다. 링크 추가를 건너뜁니다.")
                    return False
                
                # URL 형식이 올바른지 간단히 확인
                if not kakao_url.startswith('http'):
                    print(f"⚠️ 카카오 URL 형식이 올바르지 않습니다 (http로 시작해야 함): {kakao_url}")
                    # 계속 진행은 함 (사용자가 의도했을 수 있으므로)
                
                # 먼저 텍스트를 명확히 입력
                actions = ActionChains(self.driver)
                actions.send_keys("카카오톡 오픈채팅 바로가기 👉").perform()
                time.sleep(0.5)
                
                # ESC 키를 눌러 혹시 열려있을 수 있는 팝업/파일 선택창 닫기
                try:
                    actions = ActionChains(self.driver)
                    actions.send_keys(Keys.ESCAPE).perform()
                    time.sleep(0.5)
                except Exception as e:
                    print(f"ESC 키 입력 중 오류: {str(e)}")
                
                # 1. 링크 버튼 찾기 및 클릭 (이미지에서 확인된 정확한 정보 사용)
                link_button_found = False
                
                # 이미지에서 확인된 정확한 선택자들
                link_button_selectors = [
                    "button.se-oglink-toolbar-button",  # 이미지에서 확인된 정확한 클래스
                    "button[data-log='dot.link']",      # 이미지에서 확인된 data-log
                    "button[data-role='button-container'][data-log='dot.link']"  # 더 구체적인 선택자
                ]
                
                print("🔗 링크 버튼 클릭 시도...")
                for selector in link_button_selectors:
                    try:
                        print(f"링크 버튼 선택자 시도: {selector}")
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        if elements:
                            print(f"발견된 요소 수: {len(elements)}")
                            for element in elements:
                                try:
                                    if element.is_displayed() and element.is_enabled():
                                        # 요소 정보 출력
                                        element_info = {
                                            'class': element.get_attribute("class"),
                                            'data-log': element.get_attribute("data-log"),
                                            'data-role': element.get_attribute("data-role"),
                                            'title': element.get_attribute("title")
                                        }
                                        print(f"클릭할 링크 버튼: {element_info}")
                                        
                                        # 클릭 시도
                                        element.click()
                                        print(f"✅ 링크 버튼 클릭 성공: {selector}")
                                        link_button_found = True
                                        break
                                except Exception as e:
                                    print(f"개별 요소 클릭 중 오류: {str(e)}")
                                    continue
                        
                        if link_button_found:
                            break
                            
                    except Exception as e:
                        print(f"선택자 {selector} 시도 중 오류: {str(e)}")
                        continue
                
                if not link_button_found:
                    print("⚠️ CSS 선택자로 링크 버튼을 못 찾음. JavaScript로 재시도...")
                    link_button_found = self.driver.execute_script("""
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {
                        const text = btn.innerText ? btn.innerText.trim() : '';
                        const title = btn.getAttribute('title') || '';
                        const dataLog = btn.getAttribute('data-log') || '';
                        
                        if (text === '링크' || title === '링크' || dataLog === 'dot.link') {
                            console.log('JS로 링크 버튼 발견:', btn);
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                    """)
                    
                if not link_button_found:
                    print("❌ 링크 버튼을 찾을 수 없습니다 (JS 검색 실패)")
                    return False
                
                # 링크 버튼 클릭 후 처리
                if link_button_found:
                    print("🔗 링크 버튼 클릭 후 링크 입력창 확인 중...")
                    
                    # 링크 입력창이 나타날 때까지 대기 (최대 5초)
                    link_input_appeared = False
                    for attempt in range(30):  # 0.5초씩 30번 = 최대 15초
                        try:
                            # 링크 입력창 확인
                            link_input = self.driver.find_element(By.CSS_SELECTOR, 
                                "input.se-popup-oglink-input, input[placeholder*='URL'], input[placeholder*='url'], input[placeholder*='링크']")
                            if link_input.is_displayed():
                                print(f"✅ 링크 입력창 확인됨 ({attempt * 0.5}초 후)")
                                link_input_appeared = True
                                break
                        except:
                            pass
                        time.sleep(0.5)
                    
                    if link_input_appeared:
                        print("🔗 링크 입력창 확인 후 1초 대기...")
                        time.sleep(1)  # 링크 입력창 확인 후 1초 대기
                        
                        # 클립보드 권한 팝업 처리 제거 (불필요함)
                        
                        # 🎯 링크 입력 전 안전성 확보
                        print("🔒 링크 입력 전 안전성 확보 중...")
                        
                        # 모든 키보드 입력 차단 및 포커스 정리
                        self.driver.execute_script("""
                        // 모든 활성 요소에서 포커스 제거
                        if (document.activeElement) {
                            document.activeElement.blur();
                        }
                        
                        // 키보드 이벤트 임시 차단
                        window.tempKeyboardBlocked = true;
                        
                        console.log('키보드 입력 차단 및 포커스 정리 완료');
                        """)
                        time.sleep(0.3)
                        
                        # URL 입력
                        if self.fill_link_input(kakao_url):
                            print("✅ 카카오톡 링크 URL 입력 완료!")
                            
                            # 🎯 URL 입력 후 입력값 재확인
                            actual_url = self.driver.execute_script("""
                            const linkInputs = document.querySelectorAll('input.se-popup-oglink-input, .se-popup input[type="text"]');
                            for (const input of linkInputs) {
                                if (input.offsetWidth > 0 && input.offsetHeight > 0) {
                                    return input.value;
                                }
                            }
                            return null;
                            """)
                            print(f"🔍 URL 입력 후 재확인된 값: {actual_url}")
                            
                            # 만약 잘못된 값이 입력되었다면 다시 정정
                            if actual_url and ("찾아" in actual_url or "길" in actual_url):
                                print("🚨 잘못된 텍스트가 감지됨! URL 재입력 시도...")
                                self.driver.execute_script(f"""
                                const linkInputs = document.querySelectorAll('input.se-popup-oglink-input, .se-popup input[type="text"]');
                                for (const input of linkInputs) {{
                                    if (input.offsetWidth > 0 && input.offsetHeight > 0) {{
                                        input.value = '';
                                        input.value = '{kakao_url}';
                                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        console.log('URL 재입력 완료:', input.value);
                                        break;
                                    }}
                                }}
                                """)
                                time.sleep(0.5)
                            
                            # 🎯 주소 입력 후 4초 대기 후 확인 버튼 클릭 (안정성 향상)
                            print("🕐 주소 입력 후 4초 대기...")
                            time.sleep(4)
                            
                            # 🎯 최강화된 확인 버튼 찾기 및 클릭
                            print("🔍 확인 버튼 찾기 시작...")
                            confirm_clicked = self.driver.execute_script("""
                            function findAndClickConfirmButton() {
                                console.log('=== 최강화된 확인 버튼 찾기 시작 ===');
                                
                                // 0. 먼저 현재 모든 버튼 상황 파악
                                console.log('현재 페이지의 모든 버튼 상황:');
                                const allBtns = document.querySelectorAll('button');
                                allBtns.forEach((btn, i) => {
                                    if (btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                                        console.log(`버튼 ${i}:`, {
                                            text: btn.innerText?.trim(),
                                            className: btn.className,
                                            dataLog: btn.getAttribute('data-log'),
                                            disabled: btn.disabled
                                        });
                                    }
                                });
                                
                                // 1. 가장 정확한 선택자들로 시도 (확장됨)
                                const exactSelectors = [
                                    'button.se-popup-button-confirm',
                                    'button.se-popup-button.se-popup-button-confirm', 
                                    'button[data-log="pog.ok"]',
                                    '.se-popup-button-confirm',
                                    '.se-popup .se-popup-button-confirm',
                                    '.se-popup button[class*="confirm"]',
                                    'button[class*="se-popup"][class*="confirm"]'
                                ];
                                
                                console.log('1단계: 정확한 선택자로 시도...');
                                for (const selector of exactSelectors) {
                                    const btn = document.querySelector(selector);
                                    if (btn && btn.offsetWidth > 0 && btn.offsetHeight > 0 && !btn.disabled) {
                                        console.log('✅ 정확한 선택자로 확인 버튼 클릭:', selector);
                                        btn.click();
                                        return true;
                                    }
                                }
                                
                                // 2. 강제로 모든 보이는 버튼에서 '확인' 찾기 (조건 완화)
                                console.log('2단계: 모든 보이는 확인 버튼 찾기...');
                                const visibleButtons = Array.from(document.querySelectorAll('button')).filter(
                                    btn => btn.offsetWidth > 0 && btn.offsetHeight > 0 && !btn.disabled
                                );
                                
                                for (const btn of visibleButtons) {
                                    const text = btn.innerText?.trim();
                                    if (text === '확인' || text === 'OK' || text === '삽입' || text === 'Insert') {
                                        console.log('✅ 강제 검색으로 확인 버튼 발견 및 클릭:', {
                                            text: text,
                                            className: btn.className,
                                            dataLog: btn.getAttribute('data-log')
                                        });
                                        btn.click();
                                        return true;
                                    }
                                }
                                
                                // 3. 클래스명에 'confirm'이 포함된 모든 버튼 시도
                                console.log('3단계: confirm 클래스명 버튼 찾기...');
                                const confirmButtons = document.querySelectorAll('button[class*="confirm"]');
                                for (const btn of confirmButtons) {
                                    if (btn.offsetWidth > 0 && btn.offsetHeight > 0 && !btn.disabled) {
                                        console.log('✅ confirm 클래스 버튼 클릭:', btn.className);
                                        btn.click();
                                        return true;
                                    }
                                }
                                
                                // 4. data-log 속성에 'ok'가 포함된 버튼 찾기
                                console.log('4단계: data-log ok 버튼 찾기...');
                                const okButtons = document.querySelectorAll('button[data-log*="ok"]');
                                for (const btn of okButtons) {
                                    if (btn.offsetWidth > 0 && btn.offsetHeight > 0 && !btn.disabled) {
                                        console.log('✅ data-log ok 버튼 클릭:', btn.getAttribute('data-log'));
                                        btn.click();
                                        return true;
                                    }
                                }
                                
                                // 5. 마지막 수단: 팝업 영역의 마지막 버튼 클릭
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
                            """)
                            
                            if confirm_clicked:
                                print("✅ 확인 버튼 클릭 성공! (본문에 삽입 완료)")
                                
                                # 🎯 2초 대기 후 다음 단계 진행
                                print("🕐 본문 삽입 후 2초 대기...")
                                time.sleep(2)
                                        
                            else:
                                print("⚠️ 확인 버튼 클릭 실패")
                                # 디버깅을 위해 현재 페이지의 버튼 정보 출력
                                self.driver.execute_script("""
                                console.log('=== 디버깅: 현재 페이지의 모든 버튼 정보 ===');
                                const buttons = document.querySelectorAll('button');
                                buttons.forEach((btn, index) => {
                                    if (btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                                        console.log(`버튼 ${index}:`, {
                                            text: btn.innerText?.trim(),
                                            className: btn.className,
                                            id: btn.id,
                                            dataLog: btn.getAttribute('data-log'),
                                            disabled: btn.disabled
                                        });
                                    }
                                });
                                """)
                                
                        else:
                            print("⚠️ URL 입력 실패")
                    else:
                        print("⚠️ 링크 입력창이 나타나지 않음")
                
                print("==== 카카오톡 링크 추가 완료 ====\n")
                
                # 줄바꿈 추가
                actions = ActionChains(self.driver)
                actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
                time.sleep(0.2)
                
            except Exception as e:
                print(f"카카오톡 링크 추가 중 오류 발생: {str(e)}")
                traceback.print_exc()
                print("오류 발생 위치:")
                import inspect
                for frame in inspect.trace():
                    print(f"  파일: {frame.filename}, 줄: {frame.lineno}, 함수: {frame.function}")
                success = False

            # 🎯 카카오 링크 삽입 완료 후 본문 포커스 재확보 및 키보드 입력 차단 해제
            print("🎯 카카오 링크 삽입 완료 - 본문 포커스 재확보 중...")
            try:
                # 키보드 입력 차단 해제
                self.driver.execute_script("""
                window.tempKeyboardBlocked = false;
                console.log('키보드 입력 차단 해제 완료');
                """)
                
                # 본문 영역 클릭하여 포커스 이동
                body_areas = self.driver.find_elements(By.CSS_SELECTOR, 
                    "div.se-component.se-text.se-l-default")
                if body_areas:
                    self.driver.execute_script("arguments[0].click();", body_areas[-1])
                    print("✅ 본문 영역 포커스 재확보 성공")
                    time.sleep(1)  # 포커스 안정화 대기
                else:
                    print("⚠️ 본문 영역을 찾을 수 없음")
            except Exception as e:
                print(f"본문 포커스 재확보 중 오류: {str(e)}")

            # 장소 정보 추가 로직 부분은 중복이므로 모두 제거됨
            return True
            
        except Exception as e:
            print(f"⚠️ 푸터 추가 중 오류 (계속 진행): {str(e)}")
            return True
            
    def _switch_to_main_frame_robust(self):
        """에디터 버튼들이 보이는 최적의 프레임으로 지능적으로 전환합니다."""
        try:
            # 1. 현재 프레임에서 먼저 버튼 확인 (이미 들어가 있을 수 있음)
            try:
                btns = self.driver.find_elements(By.CSS_SELECTOR, "button")
                visible_btns = [b for b in btns if b.is_displayed()]
                if len(visible_btns) > 10:
                    print(f"  ✅ 현재 프레임에 {len(visible_btns)}개의 버튼이 이미 보입니다. 전환을 생략합니다.")
                    return True
            except:
                pass

            # 2. 기본 컨텍스트로 이동하여 다시 시작
            self.driver.switch_to.default_content()
            time.sleep(0.3)
            
            # 3. 버튼이 밖(default_content)에 있는지 확인
            try:
                btns = self.driver.find_elements(By.CSS_SELECTOR, "button")
                visible_btns = [b for b in btns if b.is_displayed()]
                if len(visible_btns) > 10:
                    print(f"  ✅ 기본 페이지(default)에 {len(visible_btns)}개의 버튼이 보입니다. 그대로 진행합니다.")
                    return True
            except:
                pass
            
            # 4. mainFrame 찾기 및 전환 시도
            frame_selectors = ["#mainFrame", "iframe#mainFrame", "frame#mainFrame"]
            frame_found = False
            
            for selector in frame_selectors:
                try:
                    frames = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if frames:
                        self.driver.switch_to.frame(frames[0])
                        # 전환 후 버튼이 실제로 있는지 검증
                        btns = self.driver.find_elements(By.CSS_SELECTOR, "button")
                        visible_btns = [b for b in btns if b.is_displayed()]
                        if len(visible_btns) > 0:
                            print(f"  ✅ {selector} 프레임 전환 성공 (버튼 {len(visible_btns)}개 발견)")
                            frame_found = True
                            break
                        else:
                            print(f"  ⚠️ {selector} 프레임 내에 버튼이 없습니다. 다시 나갑니다.")
                            self.driver.switch_to.default_content()
                except:
                    continue
            
            if not frame_found:
                # 5. 최후의 수단: 인덱스로 시도
                try:
                    self.driver.switch_to.default_content()
                    self.driver.switch_to.frame(0)
                    btns = self.driver.find_elements(By.CSS_SELECTOR, "button")
                    if len(btns) > 0:
                        print("  ✅ 인덱스(0)로 프레임 전환 성공")
                        frame_found = True
                    else:
                        self.driver.switch_to.default_content()
                except:
                    pass
            
            if not frame_found:
                print("  ⚠️ 발행용 최적 컨텍스트를 찾지 못했습니다. 기본 페이지로 시도합니다.")
                self.driver.switch_to.default_content()
                return False
            
            return True
        except Exception as e:
            print(f"  ❌ 프레임 관리 중 오류: {str(e)}")
            self.driver.switch_to.default_content()
            return False

    def _open_publish_panel_robust(self):
        """발행 옵션 패널을 안전하게 엽니다 (재시도 로직 포함)"""
        try:
            print("  📋 발행 옵션 패널 확인 및 열기 시도 (Robust)...")
            
            # 🎯 프레임 내부로 진입 (에디터 버튼들은 주로 mainFrame 안에 있음)
            if not self._switch_to_main_frame_robust():
                print("  ⚠️ 프레임 진입에 실패했지만 계속 진행을 시도합니다.")
            
            # 🧹 Step 0: 장소/링크 팝업 잔여물 제거
            try:
                actions = ActionChains(self.driver)
                actions.send_keys(Keys.ESCAPE).perform()
                time.sleep(0.3)
                actions.send_keys(Keys.ESCAPE).perform()
                time.sleep(0.3)
                print("  🧹 ESC 키로 잔여 팝업 정리 완료")
            except:
                pass
            
            try:
                self.driver.execute_script("""
                    document.querySelectorAll('.se-popup-dim, .se-popup-dim-transparent, .se-popup-background, .dimmed_layer').forEach(function(el) {
                        el.style.display = 'none';
                        el.remove();
                    });
                    // 장소 팝업이 남아있으면 닫기
                    document.querySelectorAll('.se-popup.se-popup-map, .se-popup.se-popup-place').forEach(function(el) {
                        el.style.display = 'none';
                    });
                """)
                print("  🧹 JS로 오버레이/팝업 잔여물 제거 완료")
            except:
                pass

            # 🛠 [Fix] 절대 switch_to.default_content()를 여기서 함부로 호출하지 않음
            # _switch_to_main_frame_robust에서 이미 최적의 위치를 찾았음
            time.sleep(0.5)
            
            # 패널 감지 선택자
            panel_detect_selectors = '.publish_layer, .se-publish-layer, #tag-input, .layer_popup__i0QOY, [class*="is_show"], [class*="publish_setting"], [class*="publish_layer"], [class*="setting_layer"]'
            
            # Step 1: 이미 열려있는지 확인 (다중 컨텍스트 체크)
            def check_panel_once():
                try:
                    panels = self.driver.find_elements(By.CSS_SELECTOR, panel_detect_selectors)
                    visible_panels = [p for p in panels if p.is_displayed()]
                    if visible_panels:
                        print(f"  ✅ 발행 패널 감지됨 (컨텍스트: {'mainFrame' if 'mainFrame' in str(self.driver.current_url) else 'default'})")
                        return True
                except: pass
                return False

            # 먼저 현재 컨텍스트 체크
            if check_panel_once(): return True
            
            # 다른 컨텍스트 체크 (스왑)
            print("  🔍 다른 컨텍스트에서 패널 검색 중...")
            if "mainFrame" in str(self.driver.current_url):
                self.driver.switch_to.default_content()
                if check_panel_once(): return True
                # 못 찾았으면 다시 돌아와서 작업 준비
                self._switch_to_main_frame_robust()
            else:
                if self._switch_to_main_frame_robust():
                    if check_panel_once(): return True
                # 못 찾았으면 다시 밖으로
                self.driver.switch_to.default_content()

            # Step 2: 발행 버튼 선택자 목록 (확장)
            publish_selectors = [
                'button.publish_btn__m9KHH',
                'button[class*="publish_btn"]',
                'button[class*="publish_btn"][class*="btn_green"]',
                'button.se-help-publish-button',
                'button[data-testid="btn-publish"]',
                'button[data-testid="scOnePublishBtn"]',
            ]
            
            for attempt in range(7):
                # 🛑 [Removed BUG] self.driver.switch_to.default_content() - 여기서 나가면 안 됨
                clicked = False
                
                # CSS 선택자로 시도
                for selector in publish_selectors:
                    try:
                        btns = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for btn in btns:
                            if btn.is_displayed() and btn.is_enabled() and "예약" not in btn.text:
                                print(f"  🔘 발행 버튼 발견 (시도 {attempt+1}): {selector}, 텍스트='{btn.text.strip()}'")
                                try:
                                    btn.click()
                                except:
                                    self.driver.execute_script("arguments[0].click();", btn)
                                clicked = True
                                break
                        if clicked: break
                    except: continue
                
                # XPath 텍스트 매칭으로 시도
                if not clicked:
                    try:
                        btns = self.driver.find_elements(By.XPATH, '//button[contains(text(), "발행")]')
                        for btn in btns:
                            if btn.is_displayed() and btn.is_enabled() and "예약" not in btn.text:
                                print(f"  🔘 발행 버튼 발견 (XPath, 시도 {attempt+1})")
                                self.driver.execute_script("arguments[0].click();", btn)
                                clicked = True
                                break
                    except: pass
                
                # JS 전체 탐색 fallback
                if not clicked and attempt % 2 == 1:
                    try:
                        clicked = self.driver.execute_script("""
                            const buttons = document.querySelectorAll('button');
                            for (const btn of buttons) {
                                const text = (btn.innerText || btn.textContent || '').trim();
                                const isVisible = btn.offsetWidth > 0 && btn.offsetHeight > 0;
                                if (isVisible && !btn.disabled && text === '발행') {
                                    console.log('JS: 발행 버튼 클릭');
                                    btn.click();
                                    return true;
                                }
                            }
                            return false;
                        """)
                        if clicked:
                            print(f"  🔘 JS로 발행 버튼 클릭 성공 (시도 {attempt+1})")
                    except: pass
                
                if clicked:
                    time.sleep(1.5)
                    
                    # 패널 열렸는지 확인 (확장된 선택자)
                    try:
                        panels = self.driver.find_elements(By.CSS_SELECTOR, panel_detect_selectors)
                        if any(l.is_displayed() for l in panels):
                            print("  ✅ 발행 패널 열림 확인됨!")
                            return True
                    except: pass
                    
                    # tag-input을 직접 찾아보기 (패널 감지에 실패해도 실제로 열려있을 수 있음)
                    try:
                        tag_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input#tag-input, input[id="tag-input"], input[placeholder*="태그"], input[placeholder*="tag"]')
                        if any(t.is_displayed() for t in tag_inputs):
                            print("  ✅ 태그 입력창이 직접 확인됨! 패널이 열려있습니다.")
                            return True
                    except: pass
                    
                    # 버튼 텍스트가 바뀌었나 확인 (발행 -> 예약, 등 상태 변화)
                    try:
                        mode_check = self.driver.execute_script("""
                            // 발행 설정 패널의 존재를 다양한 방법으로 확인
                            const checks = [
                                document.querySelector('#tag-input'),
                                document.querySelector('[class*="tag_input"]'),
                                document.querySelector('[class*="publish_setting"]'),
                                document.querySelector('[class*="setting_layer"]'),
                                document.querySelector('[class*="category"]'),
                            ];
                            for (const el of checks) {
                                if (el && el.offsetWidth > 0) return true;
                            }
                            return false;
                        """)
                        if mode_check:
                            print("  ✅ JS로 발행 설정 패널 존재 확인됨!")
                            return True
                    except: pass
                    
                    print(f"  ⏳ 패널이 아직 감지되지 않음 (시도 {attempt+1}/7)")
                else:
                    # 🎯 [New] 버튼을 못 찾은 경우, 다른 컨텍스트(프레임)도 시도
                    print(f"  ⏳ 현재 컨텍스트에서 발행 버튼을 찾지 못함 (시도 {attempt+1}/7). 컨텍스트 전환을 시도합니다.")
                    if "mainFrame" in str(self.driver.current_url): # 단순 체크 (더 정교하게 가능)
                        self.driver.switch_to.default_content()
                        print("    ➡️ 기본 컨텍스트로 전환하여 시도")
                    else:
                        self._switch_to_main_frame_robust()
                        print("    ➡️ mainFrame으로 전환하여 시도")
                
                time.sleep(1)
            
            # 최후의 수단: 모든 버튼 정보 출력
            try:
                btn_info = self.driver.execute_script("""
                    const result = [];
                    document.querySelectorAll('button').forEach(btn => {
                        const text = (btn.innerText || '').trim().substring(0, 30);
                        const cls = btn.className.substring(0, 60);
                        const visible = btn.offsetWidth > 0 && btn.offsetHeight > 0;
                        if (visible && text) result.push({text, cls});
                    });
                    return result.slice(0, 15);
                """)
                print(f"  📊 현재 보이는 버튼들: {btn_info}")
            except: pass
            
            print("  ❌ 발행 패널을 열 수 없습니다 (7회 시도 실패)")
            return False
        except Exception as e:
            print(f"  ❌ 발행 패널 열기 오류: {str(e)}")
            traceback.print_exc()
            return False

    def add_tags(self, tags=None, skip_publish=False):
        """태그 추가 (고정 태그 15개 + AI 태그 15개 = 최대 30개 보장)"""
        try:
            # 🎯 [Fix] 고정 태그 15개 + 전달받은 태그(AI 태그) 최대 15개 = 30개 병합
            # load_settings()에서 'blog_tags'가 리스트 형태의 'tags' 키로 변환되어 저장됨
            fixed_tags_raw = self.settings.get('tags', [])
            if isinstance(fixed_tags_raw, list):
                fixed_tags = [t.strip() for t in fixed_tags_raw if t.strip()]
            elif isinstance(fixed_tags_raw, str):
                fixed_tags = [t.strip() for t in fixed_tags_raw.split(',') if t.strip()]
            else:
                fixed_tags = []
            
            if not tags:
                # 태그가 전혀 없으면 고정 태그만 사용
                tags = fixed_tags
            else:
                # 전달받은 태그가 있으면: 고정 태그(최대15) + AI 태그(최대15) 병합
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(',') if t.strip()]
                seen = set()
                merged = []
                # 고정 태그를 우선 최대 15개
                for t in fixed_tags[:15]:
                    if t and t not in seen:
                        merged.append(t)
                        seen.add(t)
                # 전달받은 태그(AI 태그)에서 중복 제거 후 최대 15개 추가
                ai_count = 0
                for t in tags:
                    if t and t not in seen and ai_count < 15 and len(merged) < 30:
                        merged.append(t)
                        seen.add(t)
                        ai_count += 1
                tags = merged
            
            if not tags: return True
            print(f"태그 입력을 시작합니다... (총 {len(tags)}개: 고정 {min(len(fixed_tags),15)}개 + AI {len(tags)-min(len(fixed_tags),15)}개)")

            
            # 🎯 프레임 내부로 진입 (백업 코드 로직 복구)
            if not self._switch_to_main_frame_robust():
                print("  ❌ 프레임 전환 실패로 태그 입력을 중단합니다.")
                return False
                
            if not self._open_publish_panel_robust(): 
                print("  ❌ 발행 패널을 열지 못해 태그 입력을 중단합니다.")
                return False
            
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # 태그 입력 필드 찾기 (다양한 선택자)
            tag_selectors = [
                'input#tag-input', 
                'input[id="tag-input"]',
                'div[class*="tag_input"] input',
                'input[placeholder*="태그"]',
                '.se-tag-input'
            ]
            
            tag_input = None
            for selector in tag_selectors:
                try:
                    tag_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if tag_input.is_displayed():
                        print(f"  ✅ 태그 입력창 발견: {selector}")
                        # 명시적 클릭으로 포커스
                        try:
                            tag_input.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", tag_input)
                        break
                except: continue
            
            if not tag_input:
                print("  ❌ 태그 입력창을 찾을 수 없습니다. (fallback 시도)")
                # JS로 강제 포커스 시도
                try:
                    self.driver.execute_script("document.querySelector('input#tag-input').focus();")
                    tag_input = self.driver.switch_to.active_element
                except: pass

            if tag_input:
                for tag in tags:
                    tag = tag.strip()
                    if not tag: continue
                    print(f"  ✍️ 태그 입력 중: {tag}")
                    tag_input.send_keys(tag)
                    time.sleep(0.3)
                    # SPACE와 ENTER를 모두 사용하여 태그 등록 보장
                    tag_input.send_keys(Keys.SPACE)
                    time.sleep(0.2)
                    tag_input.send_keys(Keys.ENTER)
                    time.sleep(0.5)
            
            if skip_publish: 
                print("  ⏭️ skip_publish 설정으로 인해 최종 발행을 건너뜁니다.")
                return True
                
            if self._get_auto_final_publish_setting():
                print("  🚀 최종 발행 버튼 클릭 단계로 진입합니다...")
                time.sleep(2)
                return self.click_final_publish_button()
            
            print("  ℹ️ 자동 최종 발행이 설정되어 있지 않습니다.")
            return True
        except Exception as e:
            print(f"태그 입력 오류: {str(e)}")
            return False
        finally:
            self.driver.switch_to.default_content()
    def _get_auto_final_publish_setting(self):
        """앱 설정에서 최종 발행 자동 완료 설정 읽기"""
        try:
            import json
            import os
            import sys
            
            # 1. 사용자 데이터 디렉토리에서 먼저 확인 (path_utils.get_app_data_dir 로직)
            if sys.platform == "win32":
                local_app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
                base_path = os.path.join(local_app_data, 'BlogAutomation')
            else:
                base_path = os.path.join(os.path.expanduser('~'), '.blog_automation')
            
            config_path = os.path.join(base_path, 'config', 'app_settings.json')
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # 기본값은 True (체크됨)
                    return settings.get('auto_final_publish', True)
            
            # 2. 레거시 경로 확인 (현재 디렉토리)
            legacy_path = os.path.join(os.path.dirname(__file__), 'config', 'app_settings.json')
            if os.path.exists(legacy_path):
                with open(legacy_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('auto_final_publish', True)
            
            # 설정 파일이 없으면 기본값 True
            print("⚠️ 앱 설정 파일을 찾을 수 없습니다. 기본값(자동 발행)을 사용합니다.")
            return True
                
        except Exception as e:
            print(f"⚠️ 앱 설정 읽기 중 오류: {str(e)}. 기본값(자동 발행)을 사용합니다.")
            return True
    
    def set_reservation_time(self, reservation_time: str):
        """
        블로그 예약 발행 시간 설정
        
        Args:
            reservation_time: 예약 시간 (문자열, "HH:MM" 24시간 형식)
            
        Returns:
            bool: 예약 설정 성공 여부
        """
        try:
            from datetime import datetime, timedelta
            
            print(f"⏰ 블로그 예약 시간 설정 시작: {reservation_time}")
            
            # 이미 mainFrame에 있어야 함 (add_tags에서 호출되므로)
            # 🎯 지능형 프레임 관리 시도
            if not self._switch_to_main_frame_robust():
                print("  ⚠️ 프레임 진입 실패, 하지만 계속 시도합니다.")
            
            # 시간 파싱
            try:
                h, m = map(int, reservation_time.split(':'))
            except:
                print(f"❌ 예약 시간 형식 오류: {reservation_time} (HH:MM 형식 필요)")
                return False
            
            # 분을 10분 단위로 맞춤 (네이버 블로그는 10분 단위)
            m = (m // 10) * 10
            if m >= 60:
                m = 50
            
            # 날짜 계산: 예약 시간이 현재보다 이전이면 다음 날로 설정
            now = datetime.now()
            target_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
            
            is_tomorrow = False
            if target_dt <= now:
                target_dt += timedelta(days=1)
                is_tomorrow = True
                print(f"  📅 예약 시간이 현재보다 이전이므로 다음 날({target_dt.strftime('%Y-%m-%d')})로 설정합니다.")
            
            print(f"  🎯 설정할 예약 시간: {target_dt.strftime('%Y-%m-%d')} {h:02d}:{m:02d}")
            
            # 0. 먼저 발행 패널이 열려있는지 확인 (add_tags에서 이미 열었을 수 있음)
            # 0. 먼저 발행 패널이 열려있는지 확인 (add_tags에서 이미 열었을 수 있음)
            panel_opened = self._open_publish_panel_robust()
            
            if not panel_opened:
                print("  ⚠️ 발행 옵션 패널 열기 실패, 계속 진행...")
            
            time.sleep(1.5)  # 옵션 패널 로딩 대기
            
            # 1. 예약 라디오 버튼 클릭
            reservation_success = self.driver.execute_script("""
            console.log('=== 블로그 예약 시간 설정 시작 ===');
            
            // 1. 예약 라디오 버튼 찾기 및 클릭
            console.log('1. 예약 라디오 버튼 찾기...');
            
            let reserveClicked = false;
            
            // 방법 1: input#radio_time2 직접 클릭 (가장 확실한 방법)
            const radioInput = document.querySelector('input#radio_time2');
            if (radioInput) {
                radioInput.click();
                console.log('✅ input#radio_time2 직접 클릭 성공');
                reserveClicked = true;
            }
            
            // 방법 2: 정확히 "예약" 텍스트만 있는 label 클릭
            if (!reserveClicked) {
                const allLabels = document.querySelectorAll('label.radio_label__mB6ia');
                for (const label of allLabels) {
                    const labelText = label.textContent.trim();
                    if (labelText === '예약') {
                        label.click();
                        console.log('✅ 예약 label 클릭 성공');
                        reserveClicked = true;
                        break;
                    }
                }
            }
            
            // 방법 3: input[name*="time"][value="pre"] 클릭
            if (!reserveClicked) {
                const preInput = document.querySelector('input[value="pre"]');
                if (preInput) {
                    preInput.click();
                    console.log('✅ input[value="pre"] 클릭 성공');
                    reserveClicked = true;
                }
            }
            
            // 방법 4: 발행 시간 영역에서 두 번째 라디오 버튼 클릭
            if (!reserveClicked) {
                const radioInputs = document.querySelectorAll('input[type="radio"]');
                // radio_time1이 "현재", radio_time2가 "예약"
                for (const input of radioInputs) {
                    if (input.id === 'radio_time2' || input.name === 'radio_time' && input !== radioInputs[0]) {
                        input.click();
                        console.log('✅ 두 번째 라디오 버튼 클릭');
                        reserveClicked = true;
                        break;
                    }
                }
            }
            
            if (!reserveClicked) {
                console.log('❌ 예약 라디오 버튼을 찾을 수 없습니다.');
                return false;
            }
            
            return true;
            """)
            
            if not reservation_success:
                print("  ❌ 예약 라디오 버튼을 찾을 수 없습니다.")
                return False
            
            print("  ✅ 예약 라디오 버튼 클릭 완료")
            time.sleep(1.5)  # 시간 선택 UI 로딩 대기 (더 길게)
            
            # 2. 날짜 선택 (다음 날인 경우에만)
            if is_tomorrow:
                target_day = target_dt.day
                target_month = target_dt.month
                target_year = target_dt.year
                
                # 네이버 형식: "2025. 12. 29"
                date_str = target_dt.strftime('%Y. %m. %d')
                
                print(f"  📅 날짜 변경 시도: {date_str}")
                
                # 1단계: 날짜 입력 필드 클릭하여 달력 열기
                calendar_opened = self.driver.execute_script("""
                console.log('1단계: 날짜 입력 필드 클릭하여 달력 열기...');
                
                const dateInput = document.querySelector('input.input_date__QmA0s');
                if (dateInput && dateInput.offsetWidth > 0) {
                    dateInput.click();
                    console.log('✅ 날짜 입력 필드 클릭 성공');
                    return true;
                }
                
                // 대체 선택자
                const altInput = document.querySelector('input[class*="input_date"]');
                if (altInput && altInput.offsetWidth > 0) {
                    altInput.click();
                    console.log('✅ 대체 날짜 입력 필드 클릭 성공');
                    return true;
                }
                
                console.log('❌ 날짜 입력 필드를 찾을 수 없음');
                return false;
                """)
                
                if not calendar_opened:
                    print("  ⚠️ 달력 열기 실패, 계속 진행...")
                else:
                    time.sleep(1)  # 달력 팝업 열림 대기
                
                # 2단계: 달력에서 다음 날 클릭
                click_next_day = self.driver.execute_script(f"""
                const targetDay = {target_day};
                const today = new Date().getDate();
                console.log('2단계: 달력에서 ' + targetDay + '일 클릭 시도... (오늘: ' + today + '일)');
                
                // 오늘 날짜 (녹색) 찾기
                const todayBtn = document.querySelector('button.ui-state-highlight, a.ui-state-highlight');
                console.log('오늘 날짜 버튼:', todayBtn ? todayBtn.textContent : '없음');
                
                // 오늘이 말일인지 확인하고 다음 달로 이동
                const isLastDayOfMonth = (today === 28 || today === 29 || today === 30 || today === 31);
                const targetIsNextMonth = targetDay < today;
                
                if (targetIsNextMonth || isLastDayOfMonth && targetDay === 1) {{
                    // 다음 달 버튼 클릭
                    const nextBtn = document.querySelector('button.ui-datepicker-next, a.ui-datepicker-next');
                    if (nextBtn) {{
                        nextBtn.click();
                        console.log('✅ 다음 달 버튼 클릭');
                        // 약간 대기 후 날짜 클릭
                        return 'next_month';
                    }}
                }}
                
                // 모든 날짜 버튼에서 target 날짜 찾기
                const allDayBtns = document.querySelectorAll('button.ui-state-default, a.ui-state-default, td[data-handler="selectDay"] a');
                console.log('찾은 날짜 버튼 수:', allDayBtns.length);
                
                for (const btn of allDayBtns) {{
                    const dayText = btn.textContent.trim();
                    if (dayText === String(targetDay)) {{
                        // disabled가 아닌지 확인
                        if (!btn.classList.contains('ui-state-disabled') && 
                            !btn.parentElement.classList.contains('ui-state-disabled')) {{
                            btn.click();
                            console.log('✅ ' + targetDay + '일 클릭 성공');
                            return true;
                        }}
                    }}
                }}
                
                console.log('⚠️ ' + targetDay + '일을 찾지 못함');
                return false;
                """)
                
                # 다음 달로 이동한 경우 날짜 다시 클릭
                if click_next_day == 'next_month':
                    time.sleep(0.5)
                    self.driver.execute_script(f"""
                    const targetDay = {target_day};
                    const allDayBtns = document.querySelectorAll('button.ui-state-default, a.ui-state-default');
                    for (const btn of allDayBtns) {{
                        if (btn.textContent.trim() === String(targetDay)) {{
                            btn.click();
                            console.log('✅ 다음 달 ' + targetDay + '일 클릭 성공');
                            return true;
                        }}
                    }}
                    return false;
                    """)
                    print(f"  ✅ 다음 달 {target_day}일 선택 완료")
                elif click_next_day:
                    print(f"  ✅ 날짜 선택 완료: {target_dt.strftime('%Y-%m-%d')}")
                else:
                    print(f"  ⚠️ 날짜 선택 실패 - 기본값 사용")
                
                time.sleep(0.5)
            
            # 3. 시간 선택
            hour_success = self.driver.execute_script(f"""
            console.log('3. 시간 선택...');
            const hour = '{h:02d}';
            
            // 시간 select 요소 찾기
            const hourSelectors = [
                'select.hour_option__J_heO',
                'select[title*="시간"]',
                'select[class*="hour"]',
                '.hour__ckNMb select'
            ];
            
            for (const selector of hourSelectors) {{
                try {{
                    const select = document.querySelector(selector);
                    if (select) {{
                        select.value = hour;
                        select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        console.log('시간 선택 완료: ' + hour + ' (선택자: ' + selector + ')');
                        return true;
                    }}
                }} catch (e) {{
                    console.log('시간 선택 셀렉터 실패: ' + selector);
                }}
            }}
            
            console.log('❌ 시간 select 요소를 찾을 수 없습니다.');
            return false;
            """)
            
            if not hour_success:
                print("  ❌ 시간 선택에 실패했습니다.")
                return False
            
            print(f"  ✅ 시간 선택 완료: {h:02d}시")
            time.sleep(0.5)
            
            # 4. 분 선택
            minute_success = self.driver.execute_script(f"""
            console.log('4. 분 선택...');
            const minute = '{m:02d}';
            
            // 분 select 요소 찾기
            const minuteSelectors = [
                'select.minute_option__Vb3xB',
                'select[title*="분"]',
                'select[class*="minute"]',
                '.minute__KXXvZ select'
            ];
            
            for (const selector of minuteSelectors) {{
                try {{
                    const select = document.querySelector(selector);
                    if (select) {{
                        select.value = minute;
                        select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        console.log('분 선택 완료: ' + minute + ' (선택자: ' + selector + ')');
                        return true;
                    }}
                }} catch (e) {{
                    console.log('분 선택 셀렉터 실패: ' + selector);
                }}
            }}
            
            console.log('❌ 분 select 요소를 찾을 수 없습니다.');
            return false;
            """)
            
            if not minute_success:
                print("  ❌ 분 선택에 실패했습니다.")
                return False
            
            print(f"  ✅ 분 선택 완료: {m:02d}분")
            
            print(f"✅ 블로그 예약 시간 설정 완료: {target_dt.strftime('%Y-%m-%d')} {h:02d}:{m:02d}")
            return True
            
        except Exception as e:
            print(f"❌ 블로그 예약 시간 설정 중 오류: {e}")
            traceback.print_exc()
            return False

    
    def click_final_publish_button_legacy(self):
        """최종 발행 버튼 클릭 (녹색 발행 버튼)"""
        try:
            print("🚀 최종 발행 버튼 클릭 시도...")
            
            # 이미 mainFrame에 있으므로 프레임 전환 없이 진행
            # 발행 버튼 상태 확인 및 클릭
            publish_success = self.driver.execute_script("""
            console.log('=== 최종 발행 버튼 찾기 시작 ===');
            
            // 🎯 1. 가장 정확한 data-testid 선택자 우선 시도
            console.log('🎯 data-testid로 발행 버튼 찾기...');
            const testIdButton = document.querySelector('button[data-testid="scOnePublishBtn"]');
            if (testIdButton && testIdButton.offsetWidth > 0 && testIdButton.offsetHeight > 0 && !testIdButton.disabled) {
                console.log('✅ data-testid로 발행 버튼 발견!', {
                    testId: testIdButton.getAttribute('data-testid'),
                    className: testIdButton.className,
                    text: testIdButton.innerText || testIdButton.textContent,
                    disabled: testIdButton.disabled
                });
                testIdButton.click();
                console.log('✅ data-testid 발행 버튼 클릭 완료');
                return true;
            }
            
            // 🎯 2. 실제 클래스명 패턴으로 찾기 (confirm_btn)
            console.log('🎯 confirm_btn 클래스로 발행 버튼 찾기...');
            const confirmBtnSelectors = [
                'button[class*="confirm_btn"]',
                'button.confirm_btn_WEaBq',
                'button[class*="confirm"]'
            ];
            
            for (const selector of confirmBtnSelectors) {
                try {
                    const btn = document.querySelector(selector);
                    if (btn && btn.offsetWidth > 0 && btn.offsetHeight > 0 && !btn.disabled) {
                        const text = (btn.innerText || btn.textContent || '').trim();
                        if (text === '발행' || text === 'Publish') {
                            console.log('✅ confirm_btn으로 발행 버튼 발견:', {
                                selector: selector,
                                className: btn.className,
                                text: text
                            });
                            btn.click();
                            console.log('✅ confirm_btn 발행 버튼 클릭 완료');
                            return true;
                        }
                    }
                } catch (e) {
                    console.log('confirm_btn 선택자 시도 중 오류:', selector, e.message);
                }
            }
            
            // 🎯 3. 텍스트로 발행 버튼 찾기 (정확한 매칭)
            console.log('🎯 텍스트로 발행 버튼 찾기...');
            const allButtons = document.querySelectorAll('button');
            for (const btn of allButtons) {
                const text = (btn.innerText || btn.textContent || '').trim();
                const isVisible = btn.offsetWidth > 0 && btn.offsetHeight > 0;
                
                if (isVisible && !btn.disabled && text === '발행') {
                    console.log('✅ 텍스트로 발행 버튼 발견:', {
                        text: text,
                        className: btn.className,
                        testId: btn.getAttribute('data-testid'),
                        disabled: btn.disabled
                    });
                    btn.click();
                    console.log('✅ 텍스트 발행 버튼 클릭 완료');
                    return true;
                }
            }
            
            // 🎯 4. 위치 기반으로 발행 버튼 찾기 (화면 중앙 하단)
            console.log('🎯 위치 기반으로 발행 버튼 찾기...');
            const centerBottomButtons = Array.from(document.querySelectorAll('button')).filter(btn => {
                const rect = btn.getBoundingClientRect();
                const text = (btn.innerText || btn.textContent || '').trim();
                const isCenterArea = rect.left > window.innerWidth * 0.3 && rect.right < window.innerWidth * 0.7;
                const isBottomArea = rect.top > window.innerHeight * 0.5;
                const isVisible = btn.offsetWidth > 0 && btn.offsetHeight > 0;
                return isCenterArea && isBottomArea && isVisible && !btn.disabled && text === '발행';
            });
            
            if (centerBottomButtons.length > 0) {
                console.log('✅ 위치 기반으로 발행 버튼 발견:', centerBottomButtons.length + '개');
                centerBottomButtons[0].click();
                console.log('✅ 위치 기반 발행 버튼 클릭 완료');
                return true;
            }
            
            // 🎯 5. 마지막 수단: 모든 버튼 상세 분석
            console.log('🎯 모든 버튼 상세 분석...');
            const publishButtons = Array.from(document.querySelectorAll('button')).filter(btn => {
                const text = (btn.innerText || btn.textContent || '').trim();
                const isVisible = btn.offsetWidth > 0 && btn.offsetHeight > 0;
                return isVisible && !btn.disabled && 
                       (text === '발행' || 
                        btn.getAttribute('data-testid') === 'scOnePublishBtn' ||
                        btn.className.includes('confirm_btn'));
            });
            
            if (publishButtons.length > 0) {
                console.log('✅ 필터링된 발행 버튼 발견:', publishButtons.length + '개');
                publishButtons[0].click();
                console.log('✅ 필터링된 발행 버튼 클릭 완료');
                return true;
            }
            
            console.log('❌ 발행 버튼을 찾을 수 없음');
            return false;
            """)
            
            if publish_success:
                print("✅ 최종 발행 버튼 클릭 성공!")
                time.sleep(3)  # 발행 완료 대기
                return True
            else:
                print("❌ 최종 발행 버튼을 찾을 수 없습니다.")
                
                # 디버깅: 현재 페이지의 모든 버튼 정보 출력
                self.driver.execute_script("""
                console.log('=== 디버깅: 현재 페이지의 모든 버튼 정보 ===');
                const buttons = document.querySelectorAll('button');
                buttons.forEach((btn, index) => {
                    if (btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                        console.log(`버튼 ${index}:`, {
                            text: (btn.innerText || btn.textContent || '').trim(),
                            className: btn.className,
                            id: btn.id,
                            disabled: btn.disabled,
                            rect: btn.getBoundingClientRect()
                        });
                    }
                });
                """)
                
                return False
                
        except Exception as e:
            print(f"최종 발행 버튼 클릭 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return False
            

    def click_final_publish_button(self, is_reservation=False):
        """최종 발행 버튼 클릭 (녹색 발행 버튼) - 예약 포함 (Robust Version)"""
        try:
            print("🚀 최종 발행(또는 예약) 버튼 클릭 시도 (Robust)...")
            
            # 🎯 프레임 내부 유지 (또는 재진입)
            if not self._switch_to_main_frame_robust():
                print("  ⚠️ 프레임 진입 실패, 하지만 계속 시도합니다.")
            
            # 버튼 활성화 대기 및 클릭 시도 (최대 30초)
            publish_success = False
            max_retries = 30
            
            # 확장된 선택자 목록 (패널 내부 버튼 1순위 배치, 상단 토글 버튼 제거)
            publish_selectors = [
                'button.confirm_btn__WEaBq',  # 🎯 스크린샷에서 확인된 패널 내부 완료 버튼
                'button.confirm_btn_WEaBq',
                'button[class*="confirm_btn__"]', 
                'button[class*="confirm_btn"]',
                'button[data-testid="scOnePublishBtn"]',
                '.publish_setting_layer button[class*="publish_btn"]', 
                '//button[text()="발행"]' # 정확히 "발행" 텍스트만 있는 버튼
            ]
            
            # --- 지능형 클릭 및 결과 검증 루프 시작 ---
            for j in range(max_retries):
                found_and_clicked = False
                
                # 1. 버튼 찾기 및 클릭
                for selector in publish_selectors:
                    try:
                        if selector.startswith("//"):
                            btns = self.driver.find_elements(By.XPATH, selector)
                        else:
                            btns = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            
                        for btn in btns:
                            btn_text = (btn.text or '').strip()
                            if btn.is_displayed() and btn.is_enabled() and btn_text == '발행':
                                # 발견 시 즉시 클릭 (JS 최우선)
                                try:
                                    self.driver.execute_script("arguments[0].style.border = '3px solid red'; arguments[0].click();", btn)
                                except:
                                    btn.click()
                                
                                found_and_clicked = True
                                print(f"  🔘 최종 발행 버튼 클릭 시도 ({j+1}/{max_retries}): {selector} (텍스트: {btn_text})")
                                break
                    except:
                        continue
                    if found_and_clicked: break
                
                # 2. JS Fallback (텍스트 기반)
                if not found_and_clicked:
                    try:
                        found_and_clicked = self.driver.execute_script("""
                            const buttons = document.querySelectorAll('button');
                            for (const btn of buttons) {
                                const text = (btn.innerText || btn.textContent || '').trim();
                                const isVisible = btn.offsetWidth > 0 && btn.offsetHeight > 0;
                                if (isVisible && !btn.disabled && !btn.className.includes('publish_btn__m9KHH') && text === '발행') {
                                    btn.style.border = '3px solid blue';
                                    btn.click();
                                    return true;
                                }
                            }
                            return false;
                        """)
                        if found_and_clicked:
                            print(f"  🔘 JS를 통해 최종 발행 버튼 클릭 시도 ({j+1}/{max_retries})")
                    except: pass

                # 3. 효과 검증 (버튼이 사라졌는지 확인)
                time.sleep(1.5)
                
                # 버튼이 여전히 있는지 다시 확인
                still_visible = False
                try:
                    for selector in publish_selectors:
                        if selector.startswith("//"):
                            btns = self.driver.find_elements(By.XPATH, selector)
                        else:
                            btns = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for btn in btns:
                            if btn.is_displayed() and (btn.text or '').strip() == '발행':
                                still_visible = True
                                break
                        if still_visible: break
                except:
                    still_visible = False # Exception 발생 시 버튼이 사라진 것(Stale)으로 간주

                if not still_visible:
                    # ✅ 성공: 버튼이 사라짐 (발행 완료 또는 로딩중)
                    print("  ✅ 최종 발행 버튼이 화면에서 사라졌습니다. (발행 성공)")
                    publish_success = True
                    break
                else:
                    print("  ⏳ 버튼이 여전히 보입니다. 재시도합니다...")
                    # 🎯 컨텍스트 매번 교체하여 시도 (프레임 꼬임 방지)
                    if j % 2 == 0:
                        self.driver.switch_to.default_content()
                        time.sleep(0.5)
                        self._switch_to_main_frame_robust()

            if not publish_success:
                print("  ❌ 30회 시도 후에도 최종 발행 버튼 클릭에 실패했습니다.")
                return False
            
            print("  🚀 발행 절차가 성공적으로 시작되었습니다. 완료 대기 중...")
            time.sleep(5)  
            return True
            
        except Exception as e:
            print(f"최종 발행 버튼 클릭 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return False

    def click_publish_button(self):
        """발행 버튼 클릭"""
        try:
            print("발행 버튼 클릭 시도...")
            
            # 🎯 지능형 프레임 관리 시도
            if not self._switch_to_main_frame_robust():
                print("  ⚠️ 프레임 진입 실패, 하지만 계속 시도합니다.")
            
            # JavaScript로 발행 버튼 상태 확인
            button_info = self.driver.execute_script("""
                const publishBtns = document.querySelectorAll('button.publish_btn__m9KHH, button[class*="publish_btn"], button[class*="PublishButton"]');
                if (publishBtns.length === 0) return { found: false };
                const btn = publishBtns[0];
                return {
                    found: true,
                    disabled: btn.disabled,
                    className: btn.className,
                    visible: btn.offsetWidth > 0 && btn.offsetHeight > 0,
                    text: btn.innerText
                };
            """)
            print(f"발행 버튼 정보: {button_info}")
            
            if not button_info.get('found', False):
                print("발행 버튼을 찾을 수 없습니다")
                return False
            
            # 발행 버튼이 비활성화된 경우 대기
            if button_info.get('disabled', True):
                print("발행 버튼이 비활성화 상태입니다. 5초 대기...")
                time.sleep(5)
            
            # 여러 선택자로 버튼 찾기 시도
            publish_button = None
            selectors = [
                "button.publish_btn__m9KHH",
                "button[class*='publish_btn']",
                "button[class*='PublishButton']",
                "button.btn_publish",
                "button[class*='btn_publish']"
            ]
            
            for selector in selectors:
                try:
                    print(f"선택자 시도: {selector}")
                    publish_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if publish_button:
                        print(f"발행 버튼 발견: {selector}")
                        break
                except:
                    continue
            
            if not publish_button:
                print("발행 버튼을 찾을 수 없습니다")
                return False
            
            # JavaScript로 클릭 시도
            try:
                print("JavaScript로 발행 버튼 클릭 시도...")
                self.driver.execute_script("arguments[0].click();", publish_button)
                print("JavaScript로 발행 버튼 클릭 성공")
            except Exception as e:
                print(f"JavaScript 클릭 실패: {str(e)}")
                try:
                    print("Selenium으로 발행 버튼 클릭 시도...")
                    publish_button.click()
                    print("Selenium으로 발행 버튼 클릭 성공")
                except Exception as e:
                    print(f"Selenium 클릭 실패: {str(e)}")
                    return False
            
            # 클릭 후 대기
            time.sleep(3)
            
            # 기본 프레임으로 복귀
            try:
                self.driver.switch_to.default_content()
                print("기본 프레임으로 복귀")
            except Exception as e:
                print(f"기본 프레임 복귀 중 오류: {str(e)}")
            
            return True
            
        except Exception as e:
            print(f"발행 버튼 클릭 중 오류 발생: {str(e)}")
            traceback.print_exc()
            # 에러 발생 시 기본 프레임으로 복귀 시도
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False 

    def add_location(self):
        """위치 정보 추가 (지도/장소)"""
        try:
            print("\n=== 위치 정보 추가 시작 ====")
            
            # 🎯 지능형 프레임 관리 시도 (에디터 내부에 위치 버튼이 있음)
            if not self._switch_to_main_frame_robust():
                print("  ⚠️ 프레임 진입 실패, 하지만 계속 시도합니다.")
            
            # 위치 정보 준비
            address = self.settings.get('address', '')
            dojang_name = self.settings.get('dojang_name', '')
            
            if not address or not dojang_name:
                print(f"주소 또는 도장 이름이 설정되지 않았습니다. 주소: '{address}', 도장명: '{dojang_name}'")
                # 기본값 사용
                if not address:
                    address = "부평동 18-16"
                    print(f"주소 기본값 사용: {address}")
                if not dojang_name:
                    dojang_name = "라이온태권도"
                    print(f"도장명 기본값 사용: {dojang_name}")
            
            print(f"사용할 주소: {address}, 도장명: {dojang_name}")
            
            # 1. 위치 버튼 찾기
            location_button_found = False
            location_button_selectors = [
                "button.se-map-toolbar-button",
                "button[data-type='map']",
                "button[title*='지도'] img",
                "button[title*='장소'] img",
                "button[data-group='block'] img[aria-label*='지도']",
                "button[data-log='map']"
            ]
            
            for selector in location_button_selectors:
                try:
                    print(f"위치 버튼 선택자 시도: {selector}")
                    location_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for button in location_buttons:
                        try:
                            print(f"위치 버튼 클릭 시도")
                            button.click()
                            time.sleep(2)
                            location_button_found = True
                            break
                        except Exception as e:
                            print(f"버튼 클릭 실패: {str(e)}")
                            continue
                    
                    if location_button_found:
                        break
                except Exception as e:
                    print(f"위치 버튼 선택자 {selector} 실패: {str(e)}")
            
            if not location_button_found:
                print("위치 버튼을 찾을 수 없습니다. 스크립트로 시도합니다.")
                # 스크립트로 위치 버튼 클릭 시도
                script = """
                function findLocationButton() {
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {
                        if ((btn.title && (btn.title.includes('지도') || btn.title.includes('장소'))) ||
                            (btn.getAttribute('data-type') === 'map') ||
                            (btn.getAttribute('data-log') === 'map')) {
                            btn.click();
                            return true;
                        }
                        
                        const img = btn.querySelector('img');
                        if (img && img.getAttribute('aria-label') && 
                            (img.getAttribute('aria-label').includes('지도') || 
                             img.getAttribute('aria-label').includes('장소'))) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }
                return findLocationButton();
                """
                location_button_found = self.driver.execute_script(script)
                print(f"스크립트 실행 결과: {location_button_found}")
                
                if not location_button_found:
                    print("위치 버튼을 찾을 수 없습니다. 위치 추가를 건너뜁니다.")
                    return False
            
            time.sleep(2)
            print("위치 버튼 클릭 성공, 지도 검색 모달 열림 대기")
            
            # 🎯 [Fix] 검색어: 상호명 우선, 없으면 주소만 사용 (둘 다 넣으면 검색 실패)
            if dojang_name:
                search_query = dojang_name.strip()
                print(f"검색할 쿼리: '{search_query}' (상호명 우선)")
            else:
                search_query = address.strip()
                print(f"검색할 쿼리: '{search_query}' (상호 없음 → 주소 사용)")
            
            # 🎯 [Fix] 장소 팝업 오버레이 제거 (se-popup-dim-transparent가 클릭 차단)
            try:
                self.driver.execute_script("""
                    const overlays = document.querySelectorAll('.se-popup-dim, .se-popup-dim-transparent');
                    overlays.forEach(el => { el.style.display = 'none'; el.style.pointerEvents = 'none'; });
                    console.log('장소 팝업 오버레이 제거 완료:', overlays.length, '개');
                """)
                time.sleep(0.3)
                print("  -> 장소 팝업 오버레이 제거 완료")
            except Exception as e:
                print(f"  -> 오버레이 제거 시도 중 오류 (무시): {e}")
            
            # 🎯 [Fix] 국내/해외 드롭다운 처리 (해외로 되어 있을 때만 클릭해서 국내로 변경)
            try:
                # 1. '해외'로 설정되어 있는지 확인하고 드롭다운 열기
                needs_change = self.driver.execute_script("""
                    const buttons = Array.from(document.querySelectorAll('button, a, div[role="button"], span[role="button"]'))
                        .filter(el => el.offsetWidth > 0 && el.offsetHeight > 0);
                    
                    for (const btn of buttons) {
                        const text = (btn.innerText || '').trim();
                        if (text === '해외' && !btn.closest('li') && !btn.closest('ul')) {
                            btn.click(); // 드롭다운 열기
                            return true;
                        }
                    }
                    return false;
                """)
                
                if needs_change:
                    print("  -> 현재 '해외'로 설정됨. 드롭다운을 열었습니다. 1초 대기 후 '국내' 선택 시도...")
                    time.sleep(1) # 드롭다운 애니메이션 대기
                    
                    # 2. 드롭다운 목록에서 '국내' 찾아서 클릭
                    domestic_clicked = self.driver.execute_script("""
                        const options = document.querySelectorAll('li, button, a, span, div[role="button"], div[role="option"]');
                        for (const opt of options) {
                            if ((opt.innerText || '').trim() === '국내' && opt.offsetWidth > 0) {
                                opt.click();
                                return true;
                            }
                        }
                        return false;
                    """)
                    print(f"  -> '국내'로 변경 결과: {domestic_clicked}")
                    time.sleep(1) # 모드 변경 후 리렌더링 대기
                else:
                    print("  -> 이미 '국내'로 설정되어 있거나 '해외' 드롭다운을 찾을 수 없습니다.")
                    
            except Exception as e:
                print(f"  -> 국내/해외 드롭다운 처리 오류 (무시): {e}")
            
            # 2. 검색 입력 필드 찾기 (react-autosuggest__input 선택자 최우선 추가)
            search_input_found = False
            search_input_selectors = [
                "input.react-autosuggest__input",   # 🎯 [Fix] 장소 팝업 실제 입력창
                "input[placeholder*='장소명']",
                "input.se-map-search-input",
                "input.place_search_input",
                "input[placeholder*='검색']",
                "input[placeholder*='장소']",
                ".se-map-search input",
                "input[type='text'][class*='search']"
            ]

            for selector in search_input_selectors:
                try:
                    print(f"검색 입력 필드 선택자 시도: {selector}")
                    search_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    
                    # JS로 React value setter 사용하여 안전하게 입력
                    self.driver.execute_script("""
                        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value'
                        ).set;
                        nativeInputValueSetter.call(arguments[0], arguments[1]);
                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    """, search_input, search_query)
                    time.sleep(0.5)
                    search_input.send_keys(Keys.ENTER)
                    search_input_found = True
                    print(f"검색어 입력 성공: {search_query} (선택자: {selector})")
                    break
                except Exception as e:
                    print(f"검색 입력 필드 선택자 {selector} 실패: {str(e)}")
                    
            if not search_input_found:
                print("검색 입력 필드를 찾을 수 없습니다. 스크립트로 시도합니다.")
                # 스크립트로 검색 입력 시도
                script = f"""
                function findAndEnterSearchQuery() {{
                    const inputs = document.querySelectorAll('input');
                    for (const input of inputs) {{
                        const type = (input.type || '').toLowerCase();
                        if (type === 'hidden' || type === 'button' || type === 'submit') continue;
                        
                        const placeholder = (input.placeholder || '');
                        const className = (input.className || '');
                        
                        // Check visibility
                        if (!(input.offsetWidth > 0 && input.offsetHeight > 0)) continue;

                        if ((placeholder && (placeholder.includes('검색') || placeholder.includes('장소'))) ||
                            (className && (className.includes('search') || className.includes('map')))) {{
                            
                            input.focus();
                            input.value = '';
                            input.value = '{search_query}';
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            input.dispatchEvent(new KeyboardEvent('keydown', {{ 'key': 'Enter', 'keyCode': 13, 'which': 13, bubbles: true }}));
                            return true;
                        }}
                    }}
                    return false;
                }}
                return findAndEnterSearchQuery();
                """
                search_input_found = self.driver.execute_script(script)
                print(f"스크립트 실행 결과: {search_input_found}")
            
            # 3. 검색 결과 대기
            time.sleep(3)
            print("검색 완료, 결과 선택 대기")
            
            # 4. 첫 번째 검색 결과 선택 (마우스 오버 -> 추가 버튼 클릭)
            result_selected = False
            result_selectors = [
                ".se-map-search-result-list li:first-child",
                ".se-map-search-result-item:first-child",
                ".place_search_item:first-child",
                ".se-map-search-results-list-view-item:first-child",
                "ul[class*='list'] li:first-child"
            ]
            
            for selector in result_selectors:
                try:
                    print(f"검색 결과 선택자 시도: {selector}")
                    result_item = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    
                    # 1. 항목 직접 클릭 (호버가 안 먹힐 경우를 대비해 확실히 활성화)
                    try:
                        print("  -> 크롬 최상단으로 가져오기 및 항목 클릭 시도")
                        import os
                        os.system('''osascript -e 'tell application "Google Chrome" to activate' ''')
                        time.sleep(0.5)
                        
                        result_item.click()
                        time.sleep(0.5)
                    except Exception as e:
                        pass
                        
                    # 2. ActionChains를 통한 마우스 오버 시뮬레이션
                    try:
                        from selenium.webdriver.common.action_chains import ActionChains
                        ActionChains(self.driver).move_to_element(result_item).perform()
                        time.sleep(0.5)
                    except Exception as e:
                        pass
                    
                    # 3. Selenium 네이티브 방식(Trusted Event)으로 '추가' 버튼 탐색 및 클릭
                    add_btn_found = False
                    for attempt in range(15):
                        try:
                            # 팝업 내에서 '추가' 텍스트를 가진 요소를 모두 찾음
                            elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'se-popup-map')]//*[contains(text(), '추가')]")
                            for el in elements:
                                # 요소가 화면에 보이고, 배경 전체가 아닌 실제 버튼(크기가 작음)인지 확인
                                if el.is_displayed() and 0 < el.size['width'] < 200:
                                    print(f"  -> 네이티브 추가 버튼 발견! 텍스트: {el.text}")
                                    # Selenium 물리 클릭
                                    ActionChains(self.driver).move_to_element(el).click().perform()
                                    add_btn_found = True
                                    break
                        except Exception as e:
                            pass
                            
                        if add_btn_found:
                            break
                        time.sleep(0.2)
                        
                    # 4. Selenium 실패 시 과거에 성공했던 JS 직접 탐색/클릭 (Fallback)
                    if not add_btn_found:
                        print("  -> Selenium 네이티브 탐색 실패, JS 탐색으로 전환")
                        js_result = self.driver.execute_script("""
                            const clickables = document.querySelectorAll('.se-popup-map button, .se-popup-map a, .se-popup-map span, .se-popup-map div[role="button"], button, a, span');
                            for (const el of clickables) {
                                const text = (el.innerText || el.textContent || '').trim();
                                const className = (el.className || '').toLowerCase();
                                if (text === '✓ 추가' || text === '+ 추가' || text === '추가' || className.includes('se-place-add-button')) {
                                    if (el.offsetWidth > 250) continue; 
                                    el.click();
                                    return true;
                                }
                            }
                            return false;
                        """)
                        if js_result:
                            print("  -> JS 탐색으로 추가 버튼 클릭 성공!")
                            add_btn_found = True
                        else:
                            print("  -> 추가 버튼을 찾지 못하여 최후의 수단으로 항목 재클릭 시도")
                            try:
                                result_item.click()
                            except:
                                pass
                    
                    print(f"  -> 추가 버튼 클릭 성공 여부: {add_btn_found}")
                    if add_btn_found or result_item:
                        result_selected = True
                        print(f"첫 번째 검색 결과 선택 및 추가 성공: {selector}")
                        break
                        
                except Exception as e:
                    print(f"검색 결과 선택자 {selector} 실패: {str(e)}")
            
            if not result_selected:
                print("검색 결과를 선택할 수 없습니다. 전체 문서를 대상으로 다시 스크립트 탐색합니다.")
                script = """
                const results = document.querySelectorAll('.se-map-search-result-list li, .se-map-search-result-item');
                if(results.length > 0) {
                    const li = results[0];
                    const addBtn = li.querySelector('button[class*="add"], button.se-place-add-button');
                    if(addBtn) {
                        addBtn.click();
                        return true;
                    } else {
                        li.click();
                        return true;
                    }
                }
                return false;
                """
                if self.driver.execute_script(script):
                    result_selected = True
                    print("  -> 전역 탐색 스크립트로 클릭 성공")
            
            # 5. 선택 확인/완료 버튼 클릭 (우측 하단 확인 버튼)
            # 장소가 '선택된 장소' 목록에 추가될 때까지 넉넉히 대기
            time.sleep(2)
            confirmation_clicked = False
            
            print("확인 버튼(모달 우측 하단) 스크립트로 탐색 시작...")
            script = """
            function clickConfirmButton() {
                // 1순위: '확인' 텍스트를 가진 팝업 내 버튼 찾기
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.offsetWidth === 0 || btn.offsetHeight === 0 || btn.disabled) continue;
                    
                    const text = (btn.textContent || '').trim();
                    if (text === '확인' || text === '적용') {
                        // se-place-add-button(리스트 항목 내부 추가버튼)은 제외
                        if(btn.className.includes('se-place-add-button')) continue;
                        
                        btn.click();
                        return true;
                    }
                }
                
                // 2순위: map 관련 클래스를 가진 버튼
                for (const btn of buttons) {
                    if (btn.offsetWidth === 0 || btn.offsetHeight === 0 || btn.disabled) continue;
                    const className = (btn.className || '').toLowerCase();
                    if (className.includes('map-save') || className.includes('place_confirm') || className.includes('map_apply')) {
                        btn.click();
                        return true;
                    }
                }
                
                return false;
            }
            return clickConfirmButton();
            """
            confirmation_clicked = self.driver.execute_script(script)
            print(f"스크립트 실행 결과: {confirmation_clicked}")
            
            # 위치 추가 완료 확인
            time.sleep(3)
            print("위치 정보 추가 완료")
            return confirmation_clicked
            
        except Exception as e:
            print(f"위치 정보 추가 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return False 
    
    def handle_clipboard_popup(self):
        """클립보드 권한 팝업 처리"""
        print("🔍 클립보드 권한 팝업 처리 중...")
        
        for attempt in range(3):
            print(f"팝업 확인 시도 {attempt + 1}/3...")
            
            # 1. 브라우저 알림창 확인
            try:
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                print(f"🎯 브라우저 알림창 발견: {alert_text}")
                alert.accept()  # 허용 클릭
                print("✅ 브라우저 알림창 허용 처리 완료")
                time.sleep(1)
                return True
            except:
                pass
            
            # 2. 페이지 내 팝업 확인 및 처리
            popup_found = self.driver.execute_script("""
            console.log('클립보드 팝업 확인 시작...');
            
            // 모든 버튼 검사
            const buttons = document.querySelectorAll('button, input[type="button"], div[role="button"]');
            
            for (const btn of buttons) {
                const text = (btn.innerText || '').trim();
                const isVisible = btn.offsetWidth > 0 && btn.offsetHeight > 0;
                
                if (isVisible && (text === '허용' || text === 'Allow' || text === '확인')) {
                    console.log('🎯 허용 버튼 발견!', text);
                    btn.click();
                    console.log('✅ 허용 버튼 클릭 완료');
                    return true;
                }
            }
            
            // 팝업 다이얼로그 내부 검사
            const dialogs = document.querySelectorAll('[role="dialog"], .popup, .modal, [class*="popup"], [class*="dialog"]');
            for (const dialog of dialogs) {
                if (dialog.offsetWidth > 0 && dialog.offsetHeight > 0) {
                    const dialogText = dialog.innerText || '';
                    if (dialogText.indexOf('클립보드') !== -1 || dialogText.indexOf('clipboard') !== -1) {
                        console.log('🎯 클립보드 관련 다이얼로그 발견');
                        const allowBtns = dialog.querySelectorAll('button');
                        for (const allowBtn of allowBtns) {
                            const btnText = (allowBtn.innerText || '').trim();
                            if (btnText === '허용' || btnText === 'Allow' || btnText === '확인') {
                                console.log('✅ 다이얼로그 내 허용 버튼 클릭:', btnText);
                                allowBtn.click();
                                return true;
                            }
                        }
                    }
                }
            }
            
            console.log('클립보드 팝업을 찾지 못했습니다.');
            return false;
            """)
            
            if popup_found:
                print("✅ 클립보드 팝업 처리 완료")
                time.sleep(1)
                return True
            
            time.sleep(0.5)  # 다음 시도 전 잠시 대기
        
        print("ℹ️ 클립보드 권한 팝업 처리 완료")
        
        print("클립보드 팝업 처리 완료 (팝업 없음)")
        return False
    
    def fill_link_input(self, url):
        """링크 입력창에 URL 입력 (확인 버튼 클릭은 별도 처리)"""
        print(f"🔗 링크 입력창에 URL 입력 시도: {url}")
        
        # 링크 입력창 선택자들 (간소화)
        link_input_selectors = [
            "input.se-popup-oglink-input",
            ".se-popup input[type='text']"
        ]
        
        # 각 선택자로 시도
        for selector in link_input_selectors:
            try:
                print(f"링크 입력창 선택자 시도: {selector}")
                link_input = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                
                if link_input.is_displayed() and link_input.is_enabled():
                    # 🎯 Native value setter를 사용해 확실하게 React 업데이트 보장
                    link_input.click()  # 포커스 확보
                    time.sleep(0.1)
                    
                    self.driver.execute_script("""
                        const input = arguments[0];
                        const url = arguments[1];
                        
                        input.value = '';
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        
                        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value'
                        ).set;
                        nativeInputValueSetter.call(input, url);
                        
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    """, link_input, url)
                    
                    print(f"✅ 링크 입력창에 Native setter로 URL 입력 완료: {url}")
                    
                    # 🎯 입력 값 확인 (디버깅용)
                    actual_value = link_input.get_attribute('value')
                    print(f"🔍 실제 입력된 값: {actual_value}")
                    
                    # 🎯 URL 입력 후 Enter 키 클릭
                    from selenium.webdriver.common.keys import Keys
                    link_input.send_keys(Keys.ENTER)
                    print("✅ Enter 키 클릭 완료")
                    time.sleep(0.5)
                    return True
                    
            except Exception as e:
                print(f"선택자 {selector} 시도 중 오류: {str(e)}")
                continue
        
        # JavaScript로 링크 입력창 찾기 및 입력
        print("JavaScript로 링크 입력창 찾기 시도...")
        try:
            # 🎯 URL을 arguments로 안전하게 전달 (문자열 보간 문제 해결)
            js_result = self.driver.execute_script("""
            function findAndFillLinkInput(url) {
                console.log('JavaScript로 링크 입력창 찾기 시작...');
                console.log('입력할 URL:', url);
                
                // 모든 input 요소 검사
                const inputs = document.querySelectorAll('input');
                for (const input of inputs) {
                    const placeholder = input.placeholder || '';
                    const type = input.type || '';
                    const name = input.name || '';
                    const id = input.id || '';
                    const className = input.className || '';
                    const isVisible = input.offsetWidth > 0 && input.offsetHeight > 0;
                    
                    if (isVisible && (
                        placeholder.indexOf('URL') !== -1 ||
                        placeholder.indexOf('url') !== -1 ||
                        placeholder.indexOf('링크') !== -1 ||
                        type === 'url' ||
                        name.indexOf('url') !== -1 ||
                        id.indexOf('url') !== -1 ||
                        className.indexOf('url') !== -1 ||
                        className.indexOf('oglink') !== -1 ||
                        className.indexOf('link') !== -1
                    )) {
                        console.log('🎯 링크 입력창 발견!', {
                            placeholder: placeholder,
                            type: type,
                            name: name,
                            id: id,
                            className: className
                        });
                        
                        try {
                            // 🎯 [Fix] React controlled input 강제 업데이트
                            // 단순 input.value 할당은 React 내부 state를 갱신하지 않으므로
                            // HTMLInputElement.prototype의 nativeInputValueSetter를 사용해야 한다.
                            input.focus();
                            
                            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                                window.HTMLInputElement.prototype, 'value'
                            ).set;
                            nativeInputValueSetter.call(input, url);
                            
                            // React synthetic event 발생 (React 내부 상태 업데이트 트리거)
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            
                            console.log('✅ React 강제 업데이트 후 값:', input.value);
                            
                            // 🎯 Enter 키 이벤트 발생 (확인 버튼 트리거)
                            const enterEvent = new KeyboardEvent('keydown', {
                                key: 'Enter',
                                code: 'Enter',
                                keyCode: 13,
                                which: 13,
                                bubbles: true
                            });
                            input.dispatchEvent(enterEvent);
                            
                            console.log('✅ JavaScript로 React 링크 입력 완료, 최종 값:', input.value);
                            return true;
                        } catch (e) {
                            console.log('링크 입력 중 오류:', e.message);
                        }
                    }
                }
                
                console.log('❌ 링크 입력창을 찾을 수 없음');
                return false;
            }
            return findAndFillLinkInput(arguments[0]);
            """, url)  # 🎯 URL을 arguments로 안전하게 전달
            
            if js_result:
                print("✅ JavaScript로 링크 입력 성공!")
                time.sleep(1)
                return True
            else:
                print("❌ JavaScript로 링크 입력창을 찾을 수 없음")
                
        except Exception as e:
            print(f"JavaScript 링크 입력 중 오류: {str(e)}")
        
        return False