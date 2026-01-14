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
            dojang_name = self.settings.get('dojang_name', '라이온태권도')
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
                print(f"사용할 카카오 URL: {kakao_url}")
                
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
                    print("❌ 링크 버튼을 찾을 수 없습니다")
                    return False
                
                # 링크 버튼 클릭 후 처리
                if link_button_found:
                    print("🔗 링크 버튼 클릭 후 링크 입력창 확인 중...")
                    
                    # 링크 입력창이 나타날 때까지 대기 (최대 5초)
                    link_input_appeared = False
                    for attempt in range(10):  # 0.5초씩 10번 = 최대 5초
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

            # 장소 검색 및 지도 표시
            try:
                print("\n==== 장소 정보 추가 시작 ====")
                
                # 장소 버튼 클릭
                print("장소 버튼 찾기 및 클릭 시도...")
                location_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.se-map-toolbar-button.se-document-toolbar-basic-button.se-text-icon-toolbar-button"))
                )
                print("장소 버튼 발견, 클릭 시도...")
                location_button.click()
                time.sleep(1)
                print("장소 버튼 클릭 성공, 1초 대기 완료")

                # 장소 검색창에 주소 및 상호 입력
                print("장소 검색창 찾기...")
                location_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input.react-autosuggest__input"))
                )
                # 검색어를 사용자 설정에서 정확히 가져오기
                address = self.settings.get('address', '')
                dojang_name = self.settings.get('dojang_name', '')
                search_text = f"{address} {dojang_name}"
                
                print(f"장소 검색창 발견, 검색어 입력: {search_text}")
                # 기존 입력 내용 삭제 후 새로 입력
                location_input.clear()
                location_input.send_keys(search_text)
                time.sleep(1)  # 0.5초에서 1초로 변경
                print("검색어 입력 완료, 1초 대기")
                
                # Enter 키 입력으로 검색 실행
                print("Enter 키 입력으로 검색 실행...")
                actions = ActionChains(self.driver)
                actions.send_keys(Keys.ENTER).perform()
                time.sleep(2)  # 검색 결과 로드를 위해 대기 시간 (3초에서 2초로 변경)
                print("Enter 키 입력 완료, 2초 대기")

                # 검색 결과 항목 선택자 출력 (디버깅용)
                print("페이지의 검색 결과 UI 정보 수집 중...")
                search_elements_debug = self.driver.execute_script("""
                // 검색 결과와 관련된 모든 요소 검사
                const searchResults = [];
                
                // li 태그 검사
                const liElements = document.querySelectorAll('li');
                for (const li of liElements) {
                    if (li.className && (li.className.includes('result') || li.className.includes('search'))) {
                        searchResults.push({
                            tagName: 'li',
                            className: li.className,
                            isVisible: li.offsetWidth > 0 && li.offsetHeight > 0,
                            text: li.textContent.substring(0, 50) + '...',
                            childCount: li.childNodes.length
                        });
                    }
                }
                
                // div 검색 결과 컨테이너 검사
                const divElements = document.querySelectorAll('div');
                for (const div of divElements) {
                    if (div.className && (div.className.includes('result') || div.className.includes('search'))) {
                        searchResults.push({
                            tagName: 'div',
                            className: div.className,
                            isVisible: div.offsetWidth > 0 && div.offsetHeight > 0,
                            text: div.textContent.substring(0, 50) + '...',
                            childCount: div.childNodes.length
                        });
                    }
                }
                
                return searchResults;
                """)
                print(f"발견된 검색 관련 요소: {len(search_elements_debug)}")
                for idx, element in enumerate(search_elements_debug):
                    print(f"검색 요소 {idx+1}: {element}")

                # 검색 결과 항목 선택자 다양화
                print("다양한 검색 결과 항목 선택자로 시도 중...")
                search_result_selectors = [
                    "li.se-place-map-search-result-item",  # 이미지에서 확인된 클래스명
                    "li[class*='se-place-map-search-result-item']",
                    "li.se-place-map-search-result-item.se-is-highlight",  # 기존 선택자
                    "li.se-map-search-result-item",
                    "li.se-map-search-item",
                    "li[class*='search-result']",
                    "li[class*='result-item']",
                    ".se-map-search-result .se-map-search-item",
                    ".react-autosuggest__suggestions-list li"
                ]
                
                result_item = None
                used_selector = None
                dojang_name = self.settings.get('dojang_name', '')
                
                for selector in search_result_selectors:
                    try:
                        print(f"선택자 시도: {selector}")
                        items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if items:
                            print(f"선택자 {selector}로 {len(items)}개 요소 발견")
                            
                            # 모든 항목을 출력 (디버깅용)
                            for idx, item in enumerate(items):
                                if item.is_displayed():
                                    item_text = item.text[:50] + "..." if len(item.text) > 50 else item.text
                                    print(f"결과 항목 #{idx+1}: {item_text}")
                            
                            # 도장 이름이 포함된 항목을 우선 찾기
                            dojang_found = False
                            for item in items:
                                if item.is_displayed() and dojang_name in item.text:
                                    result_item = item
                                    used_selector = selector
                                    dojang_found = True
                                    print(f"도장 이름({dojang_name})이 포함된 검색 결과 발견!")
                                    break
                            
                            # 도장 이름이 포함된 항목이 없으면 첫 번째 표시 항목 선택
                            if not dojang_found and not result_item:
                                for item in items:
                                    if item.is_displayed():
                                        result_item = item
                                        used_selector = selector
                                        print(f"도장 이름이 포함된 결과는 없어 첫 번째 표시 항목 선택")
                                        break
                            
                            if result_item:
                                break
                    except Exception as e:
                        print(f"선택자 {selector} 시도 중 오류: {str(e)}")
                
                # 선택자로 찾지 못한 경우 JavaScript로 검색
                if not result_item:
                    print("JavaScript로 검색 결과 항목 찾기...")
                    result_item_js = self.driver.execute_script("""
                    // 검색 결과 컨테이너 찾기 (여러 패턴 시도)
                    function findSearchResult() {
                        const dojangName = arguments[0];
                        console.log('찾을 도장 이름:', dojangName);
                        
                        // 1. 도장 이름이 포함된 결과 찾기
                        const allElements = document.querySelectorAll('*');
                        for (const el of allElements) {
                            if (el.innerText && el.innerText.includes(dojangName)) {
                                // 도장 이름을 포함하는 요소 찾기
                                const parent = el.closest('li') || el.closest('div[role="option"]') || el;
                                if (parent.offsetWidth > 0 && parent.offsetHeight > 0) {
                                    console.log('도장 이름이 포함된 검색 결과 발견!');
                                    return {
                                        element: parent,
                                        foundDojang: true
                                    };
                                }
                            }
                        }
                        
                        // 도장 이름이 없을 경우 일반 검색 결과 찾기
                        // 2. 클래스명에 'search-result'가 포함된 모든 요소
                        const resultsByClass = document.querySelectorAll('[class*="search-result"], [class*="result-item"]');
                        for (const item of resultsByClass) {
                            if (item.offsetWidth > 0 && item.offsetHeight > 0) {
                                return {
                                    element: item,
                                    foundDojang: false
                                };
                            }
                        }
                        
                        // 3. 검색 결과 목록 내부의 첫 번째 항목
                        const resultLists = document.querySelectorAll('.react-autosuggest__suggestions-list, [class*="search-list"]');
                        for (const list of resultLists) {
                            if (list.children.length > 0 && list.children[0].offsetWidth > 0) {
                                return {
                                    element: list.children[0],
                                    foundDojang: false
                                };
                            }
                        }
                        
                        // 4. 특정 텍스트 패턴이 있는 요소
                        for (const el of allElements) {
                            if (el.innerText && (el.innerText.includes('도로명') || el.innerText.includes('지번'))) {
                                // 검색 결과는 주로 주소 정보를 포함함
                                const parent = el.closest('li') || el.closest('div[role="option"]') || el;
                                if (parent.offsetWidth > 0 && parent.offsetHeight > 0) {
                                    return {
                                        element: parent,
                                        foundDojang: false
                                    };
                                }
                            }
                        }
                        
                        return null;
                    }
                    
                    const result = findSearchResult(arguments[0]);
                    if (result) {
                        // 결과 요소의 위치로 스크롤
                        result.element.scrollIntoView();
                        
                        // 요소 정보 반환
                        return {
                            found: true,
                            tagName: result.element.tagName,
                            className: result.element.className,
                            text: result.element.innerText.substring(0, 50),
                            foundDojang: result.foundDojang
                        };
                    }
                    return { found: false };
                    """, dojang_name)
                    
                    if result_item_js and result_item_js.get('found'):
                        print(f"JavaScript로 검색 결과 요소 발견: {result_item_js}")
                        if result_item_js.get('foundDojang'):
                            print(f"도장 이름({dojang_name})이 포함된 결과를 JavaScript로 찾았습니다!")
                        else:
                            print("도장 이름이 포함된 결과는 찾지 못했으나, 검색 결과를 선택합니다.")
                        
                        # 요소에 직접 클릭 이벤트 발생시키기
                        self.driver.execute_script("""
                        const resultItem = arguments[0];
                        
                        // 마우스 이벤트 시뮬레이션 (hover -> 우클릭)
                        resultItem.dispatchEvent(new MouseEvent('mouseover', {
                            bubbles: true,
                            cancelable: true,
                            view: window
                        }));
                        
                        setTimeout(() => {
                            resultItem.dispatchEvent(new MouseEvent('contextmenu', {
                                bubbles: true,
                                cancelable: true,
                                view: window,
                                button: 2
                            }));
                        }, 500);
                        """, result_item_js)
                        
                        time.sleep(1)
                        print("JavaScript로 요소에 마우스 오버 및 우클릭 이벤트 발생")
                
                # 선택자로 요소를 찾은 경우 마우스 이벤트 발생
                elif result_item:
                    print(f"검색 결과 항목 발견: {used_selector}")
                    print(f"검색 결과 텍스트: {result_item.text[:50]}...")
                    
                    # 스크린샷 캡처 시도 (디버깅용)
                    try:
                        result_item.screenshot('/tmp/search_result.png')
                        print("검색 결과 요소 스크린샷 저장: /tmp/search_result.png")
                    except:
                        print("스크린샷 저장 실패 (무시)")
                    
                    # 검색 결과에 마우스 이동 (hover)
                    print("검색 결과에 마우스 이동 중...")
                    hover = ActionChains(self.driver)
                    hover.move_to_element(result_item).perform()
                    time.sleep(1)
                    print("검색 결과에 마우스 이동 완료")
                    
                    # 마우스 좌클릭 시도
                    try:
                        print("마우스 좌클릭 시도...")
                        click_action = ActionChains(self.driver)
                        click_action.click(result_item).perform()
                        time.sleep(1)
                        print("마우스 좌클릭 완료, 1초 대기")
                    except Exception as e:
                        print(f"마우스 좌클릭 중 오류: {str(e)}")
                else:
                    raise Exception("검색 결과 항목을 찾을 수 없습니다.")
                
                # (+추가) 버튼 클릭 시도 - 다양한 방법 동원
                try:
                    print("\n(+추가) 버튼 찾기 시도...")
                    
                    # 모든 버튼 정보 수집 (디버깅)
                    buttons_info = self.driver.execute_script("""
                    const buttons = document.querySelectorAll('button');
                    return Array.from(buttons).map(btn => ({
                        text: btn.innerText.trim(),
                        class: btn.className,
                        isVisible: btn.offsetWidth > 0 && btn.offsetHeight > 0,
                        hasPlus: btn.innerText.includes('+') || btn.innerText.includes('추가')
                    })).filter(info => info.isVisible);
                    """)
                    
                    print(f"화면에 표시된 버튼 수: {len(buttons_info)}")
                    for idx, btn in enumerate(buttons_info):
                        if btn.get('hasPlus'):
                            print(f"주목할 버튼 {idx+1}: {btn} - '+' 또는 '추가' 텍스트 포함")
                        elif idx < 5:  # 처음 5개 버튼만 출력
                            print(f"버튼 {idx+1}: {btn}")
                    
                    # JavaScript로 (+추가) 버튼 찾기 및 클릭 시도 - 1초 간격으로 5번 클릭
                    print("JavaScript로 (+추가) 버튼 찾기 및 5번 클릭 시도...")
                    add_button_clicked = self.driver.execute_script("""
                    // 이미지에서 확인된 클래스 사용하여 버튼 찾기
                    const findAddButton = () => {
                        // 정확한 클래스명으로 먼저 시도
                        const addButtonSpan = document.querySelector('span.se-place-map-search-add-button-text');
                        if (addButtonSpan) {
                            const clickableParent = addButtonSpan.closest('button') || addButtonSpan.parentElement;
                            if (clickableParent) return clickableParent;
                            return addButtonSpan;
                        }
                        
                        // 다른 방법으로 시도
                        const buttonsByText = Array.from(document.querySelectorAll('button')).filter(
                            btn => btn.innerText.includes('+') || btn.innerText.includes('추가')
                        );
                        if (buttonsByText.length > 0) return buttonsByText[0];
                        
                        // 클래스명으로 찾기
                        const buttonsByClass = document.querySelectorAll(
                            'button.se-place-add-button, button[class*="add-button"]'
                        );
                        if (buttonsByClass.length > 0) return buttonsByClass[0];
                        
                        return null;
                    };
                    
                    // 버튼 찾기
                    const addButton = findAddButton();
                    
                    if (!addButton) {
                        console.log('추가 버튼을 찾을 수 없습니다.');
                        return false;
                    }
                    
                    console.log('추가 버튼 발견, 5번 클릭 시도 시작...');
                    
                    // 1초 간격으로 5번 클릭
                    for (let i = 0; i < 5; i++) {
                        setTimeout(() => {
                            console.log(`${i+1}번째 클릭 시도...`);
                            addButton.click();
                        }, i * 1000);
                    }
                    
                    return true;
                    """)
                    
                    print(f"JavaScript로 (+추가) 버튼 클릭 시작: {add_button_clicked}")
                    
                    # 5번의 클릭이 완료될 때까지 5초 대기
                    print("5번 클릭 완료 대기 중 (5초)...")
                    time.sleep(5)
                    
                    # 확인 버튼 클릭 (기존 코드 유지)
                    
                except Exception as e:
                    print(f"(+추가) 버튼 찾기 및 클릭 중 오류: {str(e)}")
                
                # 확인 버튼 클릭 - 더 강력한 확인 버튼 클릭 로직으로 업데이트
                try:
                    print("\n확인 버튼 찾기 및 클릭 시도...")
                    # 여러번 시도 (버튼이 나타날 때까지 반복)
                    max_attempts = 3
                    confirm_clicked = False
                    
                    for attempt in range(max_attempts):
                        try:
                            print(f"확인 버튼 클릭 시도 {attempt+1}/{max_attempts}...")
                            
                            confirm_clicked = self.driver.execute_script("""
                            // 확인 버튼 찾는 함수
                            function findConfirmButton() {
                                // 명확한 선택자로 먼저 시도
                                const confirmBtn = document.querySelector('button.se-popup-button-confirm, button[data-log="pog.ok"]');
                                if (confirmBtn) {
                                    console.log('정확한 선택자로 확인 버튼 발견');
                                    confirmBtn.click();
                                    return true;
                                }
                                
                                // 텍스트로 버튼 찾기
                                const buttonsByText = Array.from(document.querySelectorAll('button')).filter(
                                    btn => btn.innerText.trim() === '확인'
                                );
                                if (buttonsByText.length > 0) {
                                    console.log('텍스트로 확인 버튼 발견');
                                    buttonsByText[0].click();
                                    return true;
                                }
                                
                                // 클래스로 버튼 찾기
                                const buttonsByClass = document.querySelectorAll(
                                    'button.confirm, button[class*="confirm"], button.se-popup-button'
                                );
                                for (const btn of buttonsByClass) {
                                    if (btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                                        console.log('클래스로 확인 버튼 발견');
                                        btn.click();
                                        return true;
                                    }
                                }
                                
                                return false;
                            }
                            
                            return findConfirmButton();
                            """)
                            
                            if confirm_clicked:
                                print(f"확인 버튼 클릭 성공 (시도 {attempt+1})")
                                break
                            else:
                                print(f"확인 버튼을 찾을 수 없음 (시도 {attempt+1})")
                                time.sleep(1)  # 다음 시도 전 대기
                        except Exception as e:
                            print(f"확인 버튼 클릭 시도 {attempt+1} 중 오류: {str(e)}")
                            time.sleep(1)
                    
                    print("==== 장소 정보 추가 완료 ====\n" if confirm_clicked else "==== 장소 정보 추가 시도 완료 ====\n")
                except Exception as e:
                    print(f"확인 버튼 클릭 중 오류: {str(e)}")
            except Exception as e:
                print(f"위치 정보 추가 중 오류 발생: {str(e)}")
                traceback.print_exc()
                success = False

            # 🎯 장소 정보 추가 완료 - '찾아 오는 길' 텍스트는 제거됨
            print("✅ 장소 정보 추가 완료 - 추가 텍스트 없이 진행")

            # 발행 버튼 클릭은 예약 모드가 아닐 때만 실행 (add_tags에서 처리)
            # (예약 모드에서는 set_reservation_time 후에 click_final_publish_button 호출)
            
            print("푸터 정보 추가 완료" if success else "푸터 정보 일부 추가 실패")
            return True  # 계속 진행하기 위해 True 반환
            
        except Exception as e:
            print(f"푸터 추가 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return True  # 계속 진행하기 위해 True 반환
            
    def add_tags(self, tags=None, skip_publish=False):
        """태그 추가"""
        try:
            if not tags:
                tags = self.settings.get('blog_tags', [])
            
            if not tags:
                print("태그가 설정되지 않았습니다.")
                return True  # 태그 없어도 계속 진행

            print("태그 입력을 시작합니다...")
            time.sleep(1)
            
            # 기본 프레임으로 전환
            try:
                self.driver.switch_to.default_content()
                print("기본 프레임으로 전환")
                time.sleep(0.5)
            except Exception as e:
                print(f"기본 프레임 전환 중 오류: {str(e)}")

            # mainFrame으로 전환
            try:
                print("mainFrame으로 전환 시도...")
                frame = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "mainFrame"))
                )
                self.driver.switch_to.frame(frame)
                print("mainFrame으로 전환 성공")
                time.sleep(1)
            except Exception as e:
                print(f"mainFrame 전환 중 오류: {str(e)}")
                return False
            
            # 🎯 발행 버튼을 클릭해서 발행 패널 열기
            print("📋 발행 버튼 클릭하여 발행 패널 열기...")
            panel_opened = self.driver.execute_script("""
            console.log('발행 버튼 클릭하여 발행 패널 열기...');
            
            const publishBtnSelectors = [
                'button.publish_btn__m9KHH',
                'button[class*="publish_btn"]',
                'button[data-testid="btn-publish"]',
                '.publish_btn__m9KHH'
            ];
            
            for (const selector of publishBtnSelectors) {
                try {
                    const btn = document.querySelector(selector);
                    if (btn && btn.offsetWidth > 0) {
                        btn.click();
                        console.log('✅ 발행 버튼 클릭 성공: ' + selector);
                        return true;
                    }
                } catch (e) {}
            }
            
            // 텍스트로 찾기
            const allButtons = document.querySelectorAll('button');
            for (const btn of allButtons) {
                if (btn.textContent.includes('발행') && btn.offsetWidth > 0) {
                    btn.click();
                    console.log('✅ 텍스트로 발행 버튼 클릭 성공');
                    return true;
                }
            }
            
            console.log('❌ 발행 버튼을 찾을 수 없습니다.');
            return false;
            """)
            
            if panel_opened:
                print("✅ 발행 패널 열기 성공")
                time.sleep(2)  # 발행 패널 로딩 대기
            else:
                print("⚠️ 발행 패널 열기 실패, 계속 진행...")
            
            # 태그 입력 필드 찾기 (발행 패널 안)
            try:
                print("태그 입력 필드 찾기...")
                tag_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input#tag-input'))
                )
                print("태그 입력 필드를 찾았습니다.")
                
                # 각 태그 입력
                for tag in tags:
                    try:
                        print(f"'{tag}' 태그 입력 시도...")
                        tag_input.send_keys(tag)
                        time.sleep(0.5)
                        tag_input.send_keys(Keys.SPACE)
                        time.sleep(0.5)
                        print(f"태그 입력 완료: {tag}")
                    except Exception as e:
                        print(f"태그 '{tag}' 입력 중 오류: {str(e)}")
                        continue
                
                print("모든 태그 입력이 완료되었습니다.")
                
                # 🎯 예약 모드에서는 발행 버튼 클릭 스킵
                if skip_publish:
                    print("⏰ 예약 모드: 태그 추가 후 발행 버튼 클릭 스킵")
                    return True
                
                # 🎯 앱 설정에서 최종 발행 자동 완료 설정 확인
                auto_final_publish = self._get_auto_final_publish_setting()
                
                if auto_final_publish:
                    # 체크됨: 완전 자동 업로드 (5초 후 발행 버튼 클릭)
                    print("🕐 태그 추가 완료 후 5초 대기...")
                    time.sleep(5)
                    
                    # 🚀 발행 버튼 클릭 (녹색 발행 버튼)
                    print("🚀 최종 발행 버튼 클릭 시도...")
                    publish_success = self.click_final_publish_button()
                    
                    if publish_success:
                        print("✅ 블로그 포스트 발행 완료!")
                        return True
                    else:
                        print("⚠️ 발행 버튼 클릭 실패")
                        return False
                else:
                    # 체크 해제됨: 수동 검토 모드 (발행 버튼 클릭 안함)
                    print("🔍 수동 검토 모드: 태그 추가 완료 후 대기 상태")
                    print("📝 사용자가 직접 내용을 확인하고 발행 버튼을 클릭해주세요.")
                    return True
                
            except Exception as e:
                print(f"태그 입력 필드를 찾을 수 없습니다: {str(e)}")
                traceback.print_exc()
                return False
            
        except Exception as e:
            print(f"태그 입력 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return False
        finally:
            # 기본 프레임으로 복귀
            try:
                self.driver.switch_to.default_content()
                print("기본 프레임으로 복귀")
            except Exception as e:
                print(f"기본 프레임 복귀 중 오류: {str(e)}")
    
    def _get_auto_final_publish_setting(self):
        """앱 설정에서 최종 발행 자동 완료 설정 읽기"""
        try:
            import json
            import os
            
            # 설정 파일 경로
            config_path = os.path.join(os.path.dirname(__file__), 'config', 'app_settings.json')
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # 기본값은 True (체크됨)
                    return settings.get('auto_final_publish', True)
            else:
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
            # 필요 시 프레임 전환
            try:
                self.driver.switch_to.default_content()
                frame = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "mainFrame"))
                )
                self.driver.switch_to.frame(frame)
                time.sleep(1)
            except:
                pass  # 이미 mainFrame에 있을 수 있음
            
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
            print("  📋 발행 옵션 패널 확인...")
            panel_opened = self.driver.execute_script("""
            // 예약 라디오 버튼이 이미 보이는지 확인
            const reserveRadio = document.querySelector('input#radio_time2, label[for="radio_time2"]');
            if (reserveRadio && reserveRadio.offsetWidth > 0) {
                console.log('✅ 발행 패널이 이미 열려있음');
                return true;
            }
            
            console.log('발행 버튼 클릭하여 옵션 패널 열기...');
            
            // 발행 버튼 찾기
            const publishBtnSelectors = [
                'button.publish_btn__m9KHH',
                'button[class*="publish_btn"]',
                'button[data-testid="btn-publish"]',
                '.publish_btn__m9KHH'
            ];
            
            for (const selector of publishBtnSelectors) {
                try {
                    const btn = document.querySelector(selector);
                    if (btn && btn.offsetWidth > 0) {
                        btn.click();
                        console.log('✅ 발행 버튼 클릭 성공: ' + selector);
                        return true;
                    }
                } catch (e) {}
            }
            
            console.log('❌ 발행 버튼을 찾을 수 없습니다.');
            return false;
            """)
            
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

    
    def click_final_publish_button(self):
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
            
    def click_publish_button(self):
        """발행 버튼 클릭"""
        try:
            print("발행 버튼 클릭 시도...")
            
            # 기본 프레임으로 복귀
            try:
                self.driver.switch_to.default_content()
                print("기본 프레임으로 복귀")
                time.sleep(1)
            except Exception as e:
                print(f"기본 프레임 복귀 중 오류: {str(e)}")
            
            # mainFrame으로 전환
            try:
                print("mainFrame으로 전환 시도...")
                frame = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "mainFrame"))
                )
                self.driver.switch_to.frame(frame)
                print("mainFrame으로 전환 성공")
                time.sleep(2)
            except Exception as e:
                print(f"mainFrame 전환 중 오류: {str(e)}")
                return False
            
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
            
            # 2. 검색 입력 필드 찾기
            search_input_found = False
            search_input_selectors = [
                "input.se-map-search-input",
                "input.place_search_input",
                "input[placeholder*='검색']",
                "input[placeholder*='장소']",
                ".se-map-search input",
                "input[type='text'][class*='search']"
            ]
            
            # 주소와 상호를 조합한 검색어 생성
            search_query = f"{address} {dojang_name}".strip()
            print(f"검색할 쿼리: {search_query}")
            
            for selector in search_input_selectors:
                try:
                    print(f"검색 입력 필드 선택자 시도: {selector}")
                    search_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    
                    search_input.clear()
                    time.sleep(0.5)
                    search_input.send_keys(search_query)
                    time.sleep(0.5)
                    search_input.send_keys(Keys.ENTER)
                    search_input_found = True
                    print(f"검색어 입력 성공: {search_query}")
                    break
                except Exception as e:
                    print(f"검색 입력 필드 선택자 {selector} 실패: {str(e)}")
                    
            if not search_input_found:
                print("검색 입력 필드를 찾을 수 없습니다. 스크립트로 시도합니다.")
                # 스크립트로 검색 입력 시도
                script = f"""
                function findAndEnterSearchQuery() {{
                    const inputs = document.querySelectorAll('input[type="text"]');
                    for (const input of inputs) {{
                        if ((input.placeholder && (input.placeholder.includes('검색') || input.placeholder.includes('장소'))) ||
                            (input.className && (input.className.includes('search') || input.className.includes('map')))) {{
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
            
            # 4. 첫 번째 검색 결과 선택
            result_selected = False
            result_selectors = [
                ".se-map-search-result-list li:first-child",
                ".se-map-search-result-item:first-child",
                ".place_search_item:first-child",
                ".se-map-search-results-list-view-item:first-child"
            ]
            
            for selector in result_selectors:
                try:
                    print(f"검색 결과 선택자 시도: {selector}")
                    result_item = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    result_item.click()
                    result_selected = True
                    print("첫 번째 검색 결과 선택 성공")
                    break
                except Exception as e:
                    print(f"검색 결과 선택자 {selector} 실패: {str(e)}")
            
            if not result_selected:
                print("검색 결과를 선택할 수 없습니다. 스크립트로 시도합니다.")
                # 스크립트로 첫 번째 결과 선택 시도
                script = """
                function selectFirstSearchResult() {
                    const results = document.querySelectorAll('.se-map-search-result-list li, .se-map-search-result-item, .place_search_item, .se-map-search-results-list-view-item');
                    if (results.length > 0) {
                        results[0].click();
                        return true;
                    }
                    return false;
                }
                return selectFirstSearchResult();
                """
                result_selected = self.driver.execute_script(script)
                print(f"스크립트 실행 결과: {result_selected}")
            
            # 5. 선택 확인/완료 버튼 클릭
            time.sleep(2)
            confirmation_clicked = False
            confirmation_selectors = [
                "button.se-map-save-button",
                "button.place_confirm_btn",
                "button[data-log='map.save']",
                "button.se_map_apply_button",
                "button:contains('등록')",
                "button:contains('확인')",
                "button:contains('적용')"
            ]
            
            for selector in confirmation_selectors:
                try:
                    print(f"확인 버튼 선택자 시도: {selector}")
                    confirm_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    confirm_button.click()
                    confirmation_clicked = True
                    print("위치 등록 확인 버튼 클릭 성공")
                    break
                except Exception as e:
                    print(f"확인 버튼 선택자 {selector} 실패: {str(e)}")
            
            if not confirmation_clicked:
                print("확인 버튼을 찾을 수 없습니다. 스크립트로 시도합니다.")
                # 스크립트로 확인 버튼 클릭 시도
                script = """
                function clickConfirmButton() {
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {
                        const text = btn.textContent.toLowerCase();
                        if (text.includes('등록') || text.includes('확인') || text.includes('적용') ||
                            btn.className.includes('save') || btn.className.includes('confirm') || btn.className.includes('apply')) {
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
                    # 🎯 입력창 완전히 초기화 후 정확한 URL만 입력
                    link_input.click()  # 포커스 확보
                    link_input.clear()  # 기존 내용 삭제
                    time.sleep(0.1)     # 삭제 완료 대기
                    link_input.send_keys(url)  # 정확한 URL만 입력
                    print(f"✅ 링크 입력창에 URL 입력 성공: {url}")
                    
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
                            // 🎯 입력창 완전히 초기화 후 정확한 URL만 입력
                            input.focus();
                            input.value = '';
                            input.value = url;  // arguments로 전달받은 정확한 URL만 입력
                            
                            // 이벤트 발생
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            
                            // 🎯 Enter 키 이벤트 발생
                            const enterEvent = new KeyboardEvent('keydown', {
                                key: 'Enter',
                                code: 'Enter',
                                keyCode: 13,
                                which: 13,
                                bubbles: true
                            });
                            input.dispatchEvent(enterEvent);
                            
                            console.log('✅ JavaScript로 링크 입력 및 Enter 키 완료, 입력된 값:', input.value);
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