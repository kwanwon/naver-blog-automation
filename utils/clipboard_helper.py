"""
클립보드 헬퍼 모듈 - 빌드된 앱에서도 안정적으로 동작하는 클립보드 처리

우선순위:
1. pyperclip (표준)
2. subprocess pbcopy/pbpaste (macOS 네이티브)
3. subprocess clip/powershell (Windows 네이티브)
"""

import os
import subprocess
import sys

# pyperclip은 선택적으로 로드
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    print("⚠️ pyperclip 모듈을 찾을 수 없습니다. 네이티브 클립보드 사용.")


def copy_to_clipboard(text: str) -> bool:
    """
    텍스트를 클립보드에 복사합니다.
    여러 가지 방법을 순차적으로 시도하여 하나라도 성공하면 True 반환.
    
    Args:
        text: 복사할 텍스트
    
    Returns:
        성공 여부 (True/False)
    """
    # 방법 1: macOS pbcopy (우선 순위 상향 - 포맷 보존)
    if sys.platform == 'darwin':
        try:
            # pbcopy는 utf-8 인코딩된 바이트를 받음
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.communicate(text.encode('utf-8'))
            if process.returncode == 0:
                print("✅ [Clipboard] macOS pbcopy로 복사 성공")
                return True
            else:
                print(f"⚠️ [Clipboard] pbcopy 실패: returncode={process.returncode}")
        except Exception as e:
            print(f"⚠️ [Clipboard] pbcopy 오류: {e}")

    # 방법 2: pyperclip (Mac이 아니거나 pbcopy 실패 시)
    if PYPERCLIP_AVAILABLE:
        try:
            pyperclip.copy(text)
            # 검증
            result = pyperclip.paste()
            if result and len(result) >= len(text) * 0.9:
                print("✅ [Clipboard] pyperclip으로 복사 성공")
                return True
            else:
                print(f"⚠️ [Clipboard] pyperclip 복사 후 검증 실패 (원본: {len(text)}자, 결과: {len(result) if result else 0}자)")
        except Exception as e:
            print(f"⚠️ [Clipboard] pyperclip 오류: {e}")
    
    # 방법 3: Windows clip 시도
    if sys.platform == 'win32':
        try:
            process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
            process.communicate(text.encode('utf-16'))
            if process.returncode == 0:
                print("✅ [Clipboard] clip으로 복사 성공")
                return True
        except Exception as e:
            print(f"⚠️ [Clipboard] clip 오류: {e}")
        
        # PowerShell 대안
        try:
            # PowerShell을 사용하여 클립보드에 복사
            escaped_text = text.replace("'", "''")
            subprocess.run(
                ['powershell', '-command', f"Set-Clipboard -Value '{escaped_text}'"],
                check=True,
                capture_output=True
            )
            print("✅ [Clipboard] PowerShell로 복사 성공")
            return True
        except Exception as e:
            print(f"⚠️ [Clipboard] PowerShell 오류: {e}")
    
    print("❌ [Clipboard] 모든 클립보드 복사 방법 실패")
    return False


def paste_from_clipboard() -> str:
    """
    클립보드에서 텍스트를 가져옵니다.
    
    Returns:
        클립보드 내용 또는 빈 문자열
    """
    # 방법 1: pyperclip
    if PYPERCLIP_AVAILABLE:
        try:
            return pyperclip.paste()
        except Exception as e:
            print(f"⚠️ [Clipboard] pyperclip paste 오류: {e}")
    
    # 방법 2: macOS pbpaste
    if sys.platform == 'darwin':
        try:
            process = subprocess.Popen(['pbpaste'], stdout=subprocess.PIPE)
            out, err = process.communicate()
            return out.decode('utf-8')
        except Exception as e:
            print(f"⚠️ [Clipboard] pbpaste 오류: {e}")
    
    # 방법 3: Windows PowerShell
    if sys.platform == 'win32':
        try:
            result = subprocess.run(
                ['powershell', '-command', 'Get-Clipboard'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            print(f"⚠️ [Clipboard] PowerShell paste 오류: {e}")
    
    return ""


def insert_text_to_editor(driver, editor_element, content: str, platform: str = "blog") -> bool:
    """
    에디터에 텍스트를 삽입합니다. 여러 가지 방법을 순차적으로 시도합니다.
    
    Args:
        driver: Selenium WebDriver 인스턴스
        editor_element: 에디터 요소 (contenteditable div 등)
        content: 삽입할 텍스트
        platform: 플랫폼 힌트 ("band", "cafe", "blog", "generic")
    
    Returns:
        성공 여부
    """
    import time
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains

    if not content:
        return True
    
    print(f"📝 [Insert] 텍스트 삽입 시도 ({len(content)}자, 플랫폼: {platform})")
    
    # 에디터 클릭 및 포커스
    try:
        editor_element.click()
        time.sleep(0.5)
    except:
        pass
    
    # 방법 1: 클립보드 복사 + 붙여넣기
    if copy_to_clipboard(content):
        try:
            time.sleep(0.3)
            
            if sys.platform == 'darwin':
                ActionChains(driver).key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
            else:
                ActionChains(driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            
            time.sleep(2)  # 붙여넣기 후 렌더링 딜레이를 위해 충분한 대기 (텍스트 순서 꼬임 방지)
            
            # 붙여넣기 후 이벤트 트리거 (에디터 상태 갱신)
            ActionChains(driver).send_keys(Keys.SPACE).send_keys(Keys.BACKSPACE).perform()
            time.sleep(1)
            
            # 검증: 에디터에 내용이 있는지 확인 (Selenium .text의 한계 극복을 위해 JS 사용)
            try:
                editor_text = driver.execute_script("return arguments[0].innerText || arguments[0].textContent || '';", editor_element)
            except:
                editor_text = editor_element.text if editor_element.text else ""
                
            editor_text = editor_text.strip()
            # 텍스트가 매우 길 경우 DOM 반영이 지연될 수 있으므로, 10% 이상만 확인되면 성공으로 간주
            if len(editor_text) >= len(content) * 0.1 or len(editor_text) > 10:
                print(f"✅ [Insert] 클립보드 붙여넣기 성공 ({len(editor_text)}자)")
                return True
            else:
                print(f"⚠️ [Insert] 클립보드 붙여넣기 후 검증 실패 ({len(editor_text)}자만 확인됨)")
        except Exception as e:
            print(f"⚠️ [Insert] 클립보드 붙여넣기 오류: {e}")
    
    # 방법 2: JavaScript로 직접 삽입 (execCommand 사용 추가)
    print("🔄 [Insert] JS 직접 삽입 시도...")
    try:
        # 플랫폼별 JS 스크립트
        js_script = """
            const editor = arguments[0];
            const content = arguments[1];
            
            if (!editor) return false;
            
            // 방법 2a: insertText Command (가장 표준적인 텍스트 삽입)
            try {
                editor.focus();
                const success = document.execCommand('insertText', false, content);
                if (success) {
                    console.log('execCommand insertText 성공');
                    // 이벤트 트리거
                    editor.dispatchEvent(new Event('input', { bubbles: true }));
                    editor.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }
            } catch (e) {
                console.log('execCommand 시도 실패', e);
            }

            // 방법 2b: innerText 직접 설정
            try {
                editor.focus();
                editor.innerText = content;
                
                // 이벤트 트리거
                editor.dispatchEvent(new Event('input', { bubbles: true }));
                editor.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            } catch (e) {
                console.error('JS 삽입 오류:', e);
            }
            
            // 방법 2c: innerHTML (줄바꿈 처리)
            try {
                const lines = content.split('\\n');
                const html = lines.map(line => `<p>${line || '&nbsp;'}</p>`).join('');
                editor.innerHTML = html;
                editor.dispatchEvent(new Event('input', { bubbles: true }));
                return true;
            } catch (e) {
                console.error('HTML 삽입 오류:', e);
            }
            
            return false;
        """
        
        result = driver.execute_script(js_script, editor_element, content)
        
        if result:
            time.sleep(0.5)
            
            # 키 이벤트 추가 발생 (상태 갱신 유도)
            try:
                editor_element.send_keys(Keys.END)
                editor_element.send_keys(Keys.SPACE)
                editor_element.send_keys(Keys.BACKSPACE)
            except:
                pass
            
            # 검증
            editor_text = editor_element.text.strip() if editor_element.text else ""
            if len(editor_text) >= len(content) * 0.3:
                print(f"✅ [Insert] JS 삽입 성공 ({len(editor_text)}자)")
                return True
            else:
                print(f"⚠️ [Insert] JS 삽입 후 검증 실패")
    except Exception as e:
        print(f"⚠️ [Insert] JS 삽입 오류: {e}")
    
    # 방법 3: send_keys (느리지만 확실함)
    print("🔄 [Insert] send_keys 직접 입력 시도...")
    try:
        # 너무 긴 텍스트는 잘라서 처리
        max_sendkeys_length = 2000
        text_to_send = content[:max_sendkeys_length] if len(content) > max_sendkeys_length else content
        
        if len(content) > max_sendkeys_length:
            print(f"⚠️ [Insert] 텍스트가 너무 길어 {max_sendkeys_length}자로 잘라서 입력합니다.")
        editor_element.clear()
        time.sleep(0.2)
        editor_element.send_keys(text_to_send)
        time.sleep(0.5)
        
        # 검증
        editor_text = editor_element.text.strip() if editor_element.text else ""
        if len(editor_text) >= len(text_to_send) * 0.5:
            print(f"✅ [Insert] send_keys 성공 ({len(editor_text)}자)")
            return True
    except Exception as e:
        print(f"⚠️ [Insert] send_keys 오류: {e}")
    
    print("❌ [Insert] 모든 텍스트 삽입 방법 실패")
    return False
