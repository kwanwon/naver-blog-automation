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
        # 디버깅 정보 추가
        print("\n===== NaverBlogPostFinisher 초기화 =====")
        print(f"설정 객체 종류: {type(settings)}")
        print(f"설정 객체 키: {list(settings.keys() if isinstance(settings, dict) else [])}")
        if isinstance(settings, dict) and 'footer_message' in settings:
            print(f"푸터 메시지(초기화): '{settings.get('footer_message', '없음')}'")
            print(f"푸터 메시지 길이: {len(settings.get('footer_message', ''))}")
        else:
            print("설정 객체에 'footer_message' 키가 없거나 설정 객체가 딕셔너리가 아닙니다.")
        print("=====================================\n")
        
    def add_footer(self):
        """
        블로그 포스트에 푸터를 추가합니다:
        1. 줄바꿈으로 공간 확보
        2. 카카오톡 오픈채팅 링크 추가
        3. 도장 위치 추가
        """
        try:
            print("\n===== 푸터 추가 시작 (상세 로그) =====")
            print(f"설정 객체 종류: {type(self.settings)}")
            print(f"설정 객체 키: {list(self.settings.keys() if isinstance(self.settings, dict) else [])}")
            if isinstance(self.settings, dict):
                for key in ['dojang_name', 'footer_message', 'address']:
                    if key in self.settings:
                        print(f"{key}: '{self.settings.get(key, '없음')}'")
                    else:
                        print(f"{key}: 설정에 없음")
            print("=====================================\n")
            
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
            
            # 도장 상호 확인 - 설정에 없을 경우 기본값 사용
            dojang_business_name = self.settings.get('dojang_business_name', '')
            if not dojang_business_name:  # 도장 상호가 없으면 도장 이름을 대신 사용
                dojang_business_name = dojang_name
            print(f"푸터에 사용할 도장 상호: {dojang_business_name}")
            
            # 푸터 메시지 확인 - 설정에 직접 접근
            footer_message = ""
            if isinstance(self.settings, dict) and 'footer_message' in self.settings:
                footer_message = self.settings['footer_message']
                if footer_message is None:
                    footer_message = ""
            
            print(f"푸터에 사용할 메시지 (원본): '{footer_message}'")
            print(f"footer_message 타입: {type(footer_message)}")
            print(f"footer_message 길이: {len(footer_message)}")
            print(f"footer_message.strip() 길이: {len(footer_message.strip())}")
            print(f"is empty after strip: {not footer_message.strip()}")
            
            # 디버깅: settings 객체에서 footer_message 직접 확인
            print(f"settings에서 직접 확인: '{self.settings.get('footer_message', '<없음>')}'")
            
            # 기본 텍스트 추가
            if footer_message and footer_message.strip():
                # 푸터 메시지가 길 경우 줄바꿈 처리
                footer_message_lines = footer_message.strip().split('\n')
                
                # 푸터 텍스트 구성 - 각 줄을 별도로 처리
                footer_text = "이상"
                for line in footer_message_lines:
                    if line.strip():  # 빈 줄은 건너뛰기
                        footer_text += f"\n{line.strip()}"
                
                # 마지막에 도장 상호와 '이었습니다' 추가
                footer_text += f"\n{dojang_business_name}\n이었습니다"
                
                print(f"사용할 푸터 텍스트 (메시지 있음): '{footer_text}'")
            else:
                footer_text = f"이상\n이었습니다"
                print(f"사용할 푸터 텍스트 (메시지 없음): '{footer_text}'")
                
            print("푸터 텍스트 삽입 시작...")
            
            for line in footer_text.split('\n'):
                actions.send_keys(line).perform()
                time.sleep(0.2)
                actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
                time.sleep(0.2)
            
            # 줄바꿈 2번
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
                
                # 1. 링크 버튼 찾기 및 클릭
                link_button_found = False
                link_button_selectors = [
                    "button.se-oglink-toolbar-button",
                    "button[title*='링크']",
                    "button.se-document-toolbar-basic-button[data-type='oglink']",
                    "button[data-type='oglink']",
                    "button[data-group='documentToolbar'][data-type='basic'][data-log='dot.link']"
                ]
                
                # 각 선택자 시도
                for selector in link_button_selectors:
                    try:
                        print(f"링크 버튼 선택자 시도: {selector}")
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        print(f"발견된 요소 수: {len(elements)}")
                        
                        for element in elements:
                            try:
                                element_class = element.get_attribute("class")
                                element_type = element.get_attribute("data-type")
                                element_title = element.get_attribute("title")
                                print(f"발견된 요소 정보: class={element_class}, data-type={element_type}, title={element_title}")
                                
                                element.click()
                                print(f"링크 버튼 클릭 성공: {selector}")
                                link_button_found = True
                                break
                            except Exception as e:
                                print(f"개별 요소 클릭 시도 중 오류: {str(e)}")
                        
                        if link_button_found:
                            break
                    except Exception as e:
                        print(f"선택자 {selector} 시도 중 오류: {str(e)}")
                
                # JavaScript를 사용하여 시도
                if not link_button_found:
                    print("JavaScript로 링크 버튼 찾기 시도...")
                    script = """
                    function findLinkButton() {
                        console.log('링크 버튼 찾기 시작...');
                        
                        const buttons = document.querySelectorAll('button');
                        for (const btn of buttons) {
                            console.log('버튼 검사:', btn.className, btn.getAttribute('data-type'), btn.title);
                            if ((btn.title && btn.title.includes('링크')) || 
                                (btn.getAttribute('data-type') === 'oglink') ||
                                (btn.className && btn.className.includes('oglink')) ||
                                (btn.getAttribute('data-log') === 'dot.link')) {
                                console.log('링크 버튼 발견!');
                                btn.click();
                                return true;
                            }
                        }
                        
                        // 다른 요소들도 확인
                        const allElements = document.querySelectorAll('*');
                        for (const el of allElements) {
                            if ((el.title && el.title.includes('링크')) || 
                               (el.getAttribute('data-type') === 'oglink') ||
                               (el.className && el.className.includes('oglink'))) {
                                
                                if (el.tagName === 'BUTTON' || el.tagName === 'DIV' || el.tagName === 'SPAN' || 
                                    el.onclick || el.getAttribute('role') === 'button') {
                                    console.log('링크 요소 발견:', el.tagName);
                                    el.click();
                                    return true;
                                }
                            }
                        }
                        console.log('링크 버튼을 찾을 수 없습니다.');
                        return false;
                    }
                    return findLinkButton();
                    """
                    link_button_found = self.driver.execute_script(script)
                    print(f"JavaScript로 링크 버튼 찾기 결과: {link_button_found}")
                
                if not link_button_found:
                    print("링크 버튼을 찾을 수 없습니다.")
                    # 대체 방법: 키보드 단축키 사용
                    try:
                        print("키보드 단축키 시도 (Ctrl+K)...")
                        actions = ActionChains(self.driver)
                        actions.key_down(Keys.CONTROL).send_keys('k').key_up(Keys.CONTROL).perform()
                        link_button_found = True
                        print("키보드 단축키 성공")
                    except Exception as e:
                        print(f"키보드 단축키 오류: {str(e)}")
                
                # 링크 버튼 클릭 후 3초 대기
                time.sleep(3)
                print("링크 버튼 클릭 후 3초 대기 완료")
                
                # 2. 링크 입력창 찾기 및 URL 입력
                link_input_found = False
                link_input_selectors = [
                    "input.se-popup-oglink-input",
                    "input[placeholder*='URL']",
                    "input.se-url-input-text",
                    ".se-popup-oglink input"
                ]
                
                # 여러 선택자 시도
                for selector in link_input_selectors:
                    try:
                        print(f"링크 입력창 선택자 시도: {selector}")
                        link_input = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        link_input.clear()
                        link_input.send_keys(kakao_url)
                        print(f"링크 입력창에 URL 입력 성공: {kakao_url}")
                        link_input_found = True
                        break
                    except Exception as e:
                        print(f"선택자 {selector} 시도 중 오류: {str(e)}")
                
                # JavaScript로 시도
                if not link_input_found:
                    print("JavaScript로 링크 입력창 찾기 시도...")
                    script = f"""
                    function findAndFillLinkInput() {{
                        console.log('링크 입력창 찾기 시작...');
                        
                        // URL 입력 필드 찾기
                        const inputs = document.querySelectorAll('input');
                        for (const input of inputs) {{
                            console.log('입력 필드 검사:', input.className, input.placeholder);
                            if ((input.placeholder && (input.placeholder.includes('URL') || input.placeholder.includes('주소'))) || 
                                (input.className && (input.className.includes('oglink') || input.className.includes('url')))) {{
                                console.log('링크 입력창 발견!');
                                input.value = '';
                                input.value = '{kakao_url}';
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                return true;
                            }}
                        }}
                        console.log('링크 입력창을 찾을 수 없습니다.');
                        return false;
                    }}
                    return findAndFillLinkInput();
                    """
                    link_input_found = self.driver.execute_script(script)
                    print(f"JavaScript로 링크 입력창 찾기 결과: {link_input_found}")
                
                if not link_input_found:
                    print("링크 입력창을 찾을 수 없습니다.")
                    return False
                
                time.sleep(1)
                print("링크 입력 후 1초 대기 완료")
                
                # 3. 검색 버튼 클릭
                search_button_found = False
                
                # 먼저 엔터 키를 눌러 검색 시도
                try:
                    print("Enter 키로 검색 시도...")
                    actions = ActionChains(self.driver)
                    actions.send_keys(Keys.ENTER).perform()
                    time.sleep(1)
                    print("Enter 키 입력 성공")
                    search_button_found = True
                except Exception as e:
                    print(f"Enter 키 입력 오류: {str(e)}")
                
                # Enter 키 실패 시 버튼 찾기 시도
                if not search_button_found:
                    search_button_selectors = [
                        "button.se-popup-button-search",
                        "button[title*='검색']",
                        "button.se-popup-oglink-button-search",
                        ".se-popup-button",
                        "button.search"
                    ]
                    
                    # 여러 선택자 시도
                    for selector in search_button_selectors:
                        try:
                            print(f"검색 버튼 선택자 시도: {selector}")
                            search_button = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                            search_button.click()
                            print(f"검색 버튼 클릭 성공: {selector}")
                            search_button_found = True
                            break
                        except Exception as e:
                            print(f"선택자 {selector} 시도 중 오류: {str(e)}")
                
                # JavaScript로 시도
                if not search_button_found:
                    print("JavaScript로 검색 버튼 찾기 시도...")
                    script = """
                    function findAndClickSearchButton() {
                        console.log('검색 버튼 찾기 시작...');
                        
                        // 버튼 텍스트나 클래스로 찾기
                        const buttons = document.querySelectorAll('button');
                        for (const btn of buttons) {
                            console.log('버튼 검사:', btn.className, btn.innerText, btn.title);
                            if ((btn.innerText && btn.innerText.includes('검색')) || 
                                (btn.title && btn.title.includes('검색')) ||
                                (btn.className && btn.className.includes('search'))) {
                                console.log('검색 버튼 발견!');
                                btn.click();
                                return true;
                            }
                        }
                        
                        // 검색 혹은 다음으로 보이는 모든 버튼 시도
                        for (const btn of buttons) {
                            if ((btn.innerText && (btn.innerText.includes('다음') || btn.innerText.includes('계속'))) || 
                                (btn.className && (btn.className.includes('next') || btn.className.includes('continue')))) {
                                console.log('다음 버튼 발견!');
                                btn.click();
                                return true;
                            }
                        }
                        
                        console.log('검색 버튼을 찾을 수 없습니다.');
                        return false;
                    }
                    return findAndClickSearchButton();
                    """
                    search_button_found = self.driver.execute_script(script)
                    print(f"JavaScript로 검색 버튼 찾기 결과: {search_button_found}")
                
                # 검색 결과 로딩 대기 (3초)
                print("검색 결과 로딩 대기 (3초)...")
                time.sleep(3)
                
                # 4. 확인 버튼 클릭
                confirm_button_found = False
                
                # 먼저 엔터 키 시도
                try:
                    print("Enter 키로 확인 버튼 시도...")
                    actions = ActionChains(self.driver)
                    actions.send_keys(Keys.ENTER).perform()
                    time.sleep(1)
                    print("Enter 키 입력 성공")
                except Exception as e:
                    print(f"Enter 키 입력 오류: {str(e)}")
                
                # 스크린샷에서 확인된 정확한 선택자들 먼저 시도
                confirm_button_selectors = [
                    "button.se-popup-button.se-popup-button-confirm",  # 스크린샷에서 확인된 정확한 클래스명
                    "button.se-popup-button-confirm",
                    "button[data-log='pog.ok']",  # 스크린샷에서 확인된 data-log 속성
                    "button.se-popup-oglink-button-apply",
                    "button[title='확인']",
                    ".se-popup-button.se-popup-button-primary",
                    "button.se-popup-button-apply",
                    "button.apply",
                    "button.confirm",
                    "button.se-btn-confirm"
                ]
                
                # 여러 선택자 시도
                for selector in confirm_button_selectors:
                    try:
                        print(f"확인 버튼 선택자 시도: {selector}")
                        confirm_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        print(f"확인 버튼 발견: {selector}, 클릭 시도...")
                        
                        # 버튼에 대한 정보 출력
                        button_info = self.driver.execute_script("""
                        var btn = arguments[0];
                        return {
                            text: btn.innerText,
                            class: btn.className,
                            isVisible: btn.offsetWidth > 0 && btn.offsetHeight > 0,
                            attributes: Array.from(btn.attributes).map(attr => attr.name + '=' + attr.value).join(', ')
                        };
                        """, confirm_button)
                        print(f"버튼 정보: {button_info}")
                        
                        # 직접 클릭 시도
                        confirm_button.click()
                        print(f"확인 버튼 클릭 성공: {selector}")
                        confirm_button_found = True
                        time.sleep(2)  # 클릭 후 더 오래 대기
                        break
                    except Exception as e:
                        print(f"선택자 {selector} 시도 중 오류: {str(e)}")
                
                # JavaScript로 시도 - 더 자세한 스크립트로 개선
                if not confirm_button_found:
                    print("JavaScript로 확인 버튼 찾기 시도...")
                    script = """
                    function findAndClickConfirmButton() {
                        console.log('확인 버튼 찾기 시작...');
                        
                        // 스크린샷에서 확인된 정확한 버튼 찾기
                        const confirmBtnExact = document.querySelector('button.se-popup-button.se-popup-button-confirm, button[data-log="pog.ok"]');
                        if (confirmBtnExact) {
                            console.log('정확한 확인 버튼 발견!');
                            confirmBtnExact.click();
                            return true;
                        }
                        
                        // 버튼 텍스트나 클래스로 찾기
                        const buttons = document.querySelectorAll('button');
                        
                        // 모든 버튼 정보 로깅
                        console.log('페이지 내 버튼 정보:');
                        buttons.forEach((btn, idx) => {
                            console.log(`버튼 ${idx}:`, btn.className, btn.innerText, btn.title, 
                                         btn.getAttribute('data-log'), btn.getAttribute('data-classname'));
                        });
                        
                        // '확인' 텍스트가 있는 버튼 찾기
                        for (const btn of buttons) {
                            if (btn.innerText && btn.innerText.trim() === '확인') {
                                console.log('확인 텍스트 버튼 발견!');
                                btn.click();
                                return true;
                            }
                        }
                        
                        // 클래스명에 confirm이 포함된 버튼 찾기
                        for (const btn of buttons) {
                            if (btn.className && (btn.className.includes('confirm') || btn.className.includes('apply'))) {
                                console.log('확인/적용 클래스 버튼 발견!');
                                btn.click();
                                return true;
                            }
                        }
                        
                        // 버튼 스타일 체크 시 녹색 또는 강조 버튼 찾기
                        for (const btn of buttons) {
                            const style = window.getComputedStyle(btn);
                            if (style.backgroundColor.includes('green') || style.backgroundColor.includes('rgb(3, 199, 90)') || 
                                style.color === 'rgb(3, 199, 90)') {
                                console.log('녹색/강조 버튼 발견!');
                                btn.click();
                                return true;
                            }
                        }
                        
                        // '확인' 아이콘이 있는 버튼 찾기 (체크 마크 포함)
                        const confirmIcons = document.querySelectorAll('button svg, button .check-icon, button .confirm-icon');
                        if (confirmIcons.length > 0) {
                            const parentButton = confirmIcons[0].closest('button');
                            if (parentButton) {
                                console.log('확인 아이콘 버튼 발견!');
                                parentButton.click();
                                return true;
                            }
                        }
                        
                        // 팝업 내부의 모든 버튼 시도 (마지막 수단)
                        const popupButtons = document.querySelectorAll('.se-popup button, .se-layer button');
                        if (popupButtons.length > 0) {
                            console.log('팝업 내 마지막 버튼 시도');
                            // 팝업의 마지막 버튼이 주로 확인 버튼임
                            popupButtons[popupButtons.length - 1].click();
                            return true;
                        }
                        
                        console.log('확인 버튼을 찾을 수 없습니다.');
                        return false;
                    }
                    return findAndClickConfirmButton();
                    """
                    confirm_button_found = self.driver.execute_script(script)
                    print(f"JavaScript로 확인 버튼 찾기 결과: {confirm_button_found}")
                
                # 마지막 시도: DOM 구조를 기반으로 가장 특정한 확인 버튼 위치 지정
                if not confirm_button_found:
                    try:
                        print("DOM 구조 분석을 통한 확인 버튼 찾기 시도...")
                        # 스크린샷에서 확인된 구조로 시도
                        script = """
                        const popupContainer = document.querySelector('.se-popup-container');
                        if (popupContainer) {
                            const buttonContainer = popupContainer.querySelector('.se-popup-button-container');
                            if (buttonContainer) {
                                const confirmButton = buttonContainer.querySelector('button');
                                if (confirmButton) {
                                    confirmButton.click();
                                    return true;
                                }
                            }
                            
                            // 직접 자식 버튼 시도
                            const directButtons = popupContainer.querySelectorAll('button');
                            if (directButtons.length > 0) {
                                // 마지막 버튼이 확인 버튼일 가능성이 높음
                                directButtons[directButtons.length - 1].click();
                                return true;
                            }
                        }
                        return false;
                        """
                        confirm_button_found = self.driver.execute_script(script)
                        print(f"DOM 구조 분석을 통한 확인 버튼 찾기 결과: {confirm_button_found}")
                    except Exception as e:
                        print(f"DOM 구조 분석 중 오류: {str(e)}")
                
                # Wait after confirming
                time.sleep(2)  # 확인 버튼 클릭 후 충분한 대기 시간
                
                # 줄바꿈 추가
                actions = ActionChains(self.driver)
                actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
                time.sleep(0.5)
                
                print("==== 카카오톡 링크 추가 완료 ====\n")
                
            except Exception as e:
                print(f"카카오톡 링크 추가 중 오류 발생: {str(e)}")
                traceback.print_exc()
                print("오류 발생 위치:")
                import inspect
                for frame in inspect.trace():
                    print(f"  파일: {frame.filename}, 줄: {frame.lineno}, 함수: {frame.function}")
                success = False
            
            # 카카오톡 링크 추가 후 3초 대기
            time.sleep(3)  # 링크 삽입 후 3초 대기

            # '- 찾아 오는 길 -' 텍스트 추가
            print("\n==== 찾아 오는 길 추가 시작 ====")
            actions = ActionChains(self.driver)
            actions.send_keys("- 찾아 오는 길 -").perform()
            time.sleep(0.2)
            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
            time.sleep(0.2)
            time.sleep(2)  # '찾아 오는 길' 추가 후 2초 대기
            print("'찾아 오는 길' 텍스트 추가 완료")

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

            # 발행 버튼 클릭
            if not self.click_publish_button():
                print("발행 버튼 클릭 실패")
            
            print("푸터 정보 추가 완료" if success else "푸터 정보 일부 추가 실패")
            return True  # 계속 진행하기 위해 True 반환
            
        except Exception as e:
            print(f"푸터 추가 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return True  # 계속 진행하기 위해 True 반환
            
    def add_tags(self, tags=None):
        """태그 추가"""
        try:
            if not tags:
                tags = self.settings.get('blog_tags', [])
            
            if not tags:
                print("태그가 설정되지 않았습니다.")
                return

            print("태그 입력을 시작합니다...")
            time.sleep(3)  # 발행 창이 완전히 로드될 때까지 대기
            
            # 기본 프레임으로 전환
            try:
                self.driver.switch_to.default_content()
                print("기본 프레임으로 전환")
                time.sleep(1)
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
                time.sleep(2)
            except Exception as e:
                print(f"mainFrame 전환 중 오류: {str(e)}")
                return False
            
            # 태그 입력 필드 찾기
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
                
            if not search_input_found:
                print("검색 입력창을 찾을 수 없습니다.")
                return False
            
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
                    print(f"확인 버튼 발견: {selector}, 클릭 시도...")
                    
                    # 버튼에 대한 정보 출력
                    button_info = self.driver.execute_script("""
                    var btn = arguments[0];
                    return {
                        text: btn.innerText,
                        class: btn.className,
                        isVisible: btn.offsetWidth > 0 && btn.offsetHeight > 0,
                        attributes: Array.from(btn.attributes).map(attr => attr.name + '=' + attr.value).join(', ')
                    };
                    """, confirm_button)
                    print(f"버튼 정보: {button_info}")
                    
                    # 직접 클릭 시도
                    confirm_button.click()
                    print(f"확인 버튼 클릭 성공: {selector}")
                    confirm_button_found = True
                    time.sleep(2)  # 클릭 후 더 오래 대기
                    break
                except Exception as e:
                    print(f"선택자 {selector} 시도 중 오류: {str(e)}")
            
            # JavaScript로 시도 - 더 자세한 스크립트로 개선
            if not confirm_button_found:
                print("JavaScript로 확인 버튼 찾기 시도...")
                script = """
                function findAndClickConfirmButton() {
                    console.log('확인 버튼 찾기 시작...');
                    
                    // 스크린샷에서 확인된 정확한 버튼 찾기
                    const confirmBtnExact = document.querySelector('button.se-popup-button.se-popup-button-confirm, button[data-log="pog.ok"]');
                    if (confirmBtnExact) {
                        console.log('정확한 확인 버튼 발견!');
                        confirmBtnExact.click();
                        return true;
                    }
                    
                    // 버튼 텍스트나 클래스로 찾기
                    const buttons = document.querySelectorAll('button');
                    
                    // 모든 버튼 정보 로깅
                    console.log('페이지 내 버튼 정보:');
                    buttons.forEach((btn, idx) => {
                        console.log(`버튼 ${idx}:`, btn.className, btn.innerText, btn.title, 
                                     btn.getAttribute('data-log'), btn.getAttribute('data-classname'));
                    });
                    
                    // '확인' 텍스트가 있는 버튼 찾기
                    for (const btn of buttons) {
                        if (btn.innerText && btn.innerText.trim() === '확인') {
                            console.log('확인 텍스트 버튼 발견!');
                            btn.click();
                            return true;
                        }
                    }
                    
                    // 클래스명에 confirm이 포함된 버튼 찾기
                    for (const btn of buttons) {
                        if (btn.className && (btn.className.includes('confirm') || btn.className.includes('apply'))) {
                            console.log('확인/적용 클래스 버튼 발견!');
                            btn.click();
                            return true;
                        }
                    }
                    
                    // 버튼 스타일 체크 시 녹색 또는 강조 버튼 찾기
                    for (const btn of buttons) {
                        const style = window.getComputedStyle(btn);
                        if (style.backgroundColor.includes('green') || style.backgroundColor.includes('rgb(3, 199, 90)') || 
                            style.color === 'rgb(3, 199, 90)') {
                            console.log('녹색/강조 버튼 발견!');
                            btn.click();
                            return true;
                        }
                    }
                    
                    // '확인' 아이콘이 있는 버튼 찾기 (체크 마크 포함)
                    const confirmIcons = document.querySelectorAll('button svg, button .check-icon, button .confirm-icon');
                    if (confirmIcons.length > 0) {
                        const parentButton = confirmIcons[0].closest('button');
                        if (parentButton) {
                            console.log('확인 아이콘 버튼 발견!');
                            parentButton.click();
                            return true;
                        }
                    }
                    
                    // 팝업 내부의 모든 버튼 시도 (마지막 수단)
                    const popupButtons = document.querySelectorAll('.se-popup button, .se-layer button');
                    if (popupButtons.length > 0) {
                        console.log('팝업 내 마지막 버튼 시도');
                        // 팝업의 마지막 버튼이 주로 확인 버튼임
                        popupButtons[popupButtons.length - 1].click();
                        return true;
                    }
                    
                    console.log('확인 버튼을 찾을 수 없습니다.');
                    return false;
                }
                return findAndClickConfirmButton();
                """
                confirm_button_found = self.driver.execute_script(script)
                print(f"JavaScript로 확인 버튼 찾기 결과: {confirm_button_found}")
            
            # 마지막 시도: DOM 구조를 기반으로 가장 특정한 확인 버튼 위치 지정
            if not confirm_button_found:
                try:
                    print("DOM 구조 분석을 통한 확인 버튼 찾기 시도...")
                    # 스크린샷에서 확인된 구조로 시도
                    script = """
                    const popupContainer = document.querySelector('.se-popup-container');
                    if (popupContainer) {
                        const buttonContainer = popupContainer.querySelector('.se-popup-button-container');
                        if (buttonContainer) {
                            const confirmButton = buttonContainer.querySelector('button');
                            if (confirmButton) {
                                confirmButton.click();
                                return true;
                            }
                        }
                        
                        // 직접 자식 버튼 시도
                        const directButtons = popupContainer.querySelectorAll('button');
                        if (directButtons.length > 0) {
                            // 마지막 버튼이 확인 버튼일 가능성이 높음
                            directButtons[directButtons.length - 1].click();
                            return true;
                        }
                    }
                    return false;
                    """
                    confirm_button_found = self.driver.execute_script(script)
                    print(f"DOM 구조 분석을 통한 확인 버튼 찾기 결과: {confirm_button_found}")
                except Exception as e:
                    print(f"DOM 구조 분석 중 오류: {str(e)}")
                
                # Wait after confirming
                time.sleep(2)  # 확인 버튼 클릭 후 충분한 대기 시간
                
                # 줄바꿈 추가
                actions = ActionChains(self.driver)
                actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
                time.sleep(0.5)
                
                print("==== 장소 정보 추가 완료 ====\n" if confirm_button_found else "==== 장소 정보 추가 시도 완료 ====\n")
            
        except Exception as e:
            print(f"위치 정보 추가 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return False 