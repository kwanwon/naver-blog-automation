import os

def fix():
    file_path = "/Users/gm2hapkido/Desktop/라이온개발자/naver_blog_post_finisher.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    target = """            # 2. 검색 입력 필드 찾기"""
    replacement = """            # 1.5 '국내' 옵션 강제 선택 (해외로 설정되어 있을 경우 대비)
            print("지도 검색 '국내/해외' 옵션 확인 및 '국내' 강제 선택 시도")
            try:
                script_domestic = '''
                function ensureDomestic() {
                    const buttons = Array.from(document.querySelectorAll('button, span, div, a'));
                    // 현재 선택된 텍스트가 '해외'인 버튼 또는 요소 찾기
                    const regionBtn = buttons.find(el => 
                        el.innerText && el.innerText.trim() === '해외' && 
                        (el.className.includes('region') || el.className.includes('select') || el.tagName === 'BUTTON')
                    );
                    
                    if (regionBtn) {
                        regionBtn.click(); // 드롭다운 열기
                        return true;
                    }
                    return false;
                }
                return ensureDomestic();
                '''
                needs_change = self.driver.execute_script(script_domestic)
                
                if needs_change:
                    time.sleep(0.5)
                    # '국내' 항목 찾아 클릭
                    self.driver.execute_script('''
                        const items = Array.from(document.querySelectorAll('li, button, span, a'));
                        const domesticItem = items.find(el => el.innerText && el.innerText.trim() === '국내');
                        if (domesticItem) {
                            domesticItem.click();
                        }
                    ''')
                    time.sleep(0.5)
                    print("✅ '국내' 옵션으로 변경 완료")
                else:
                    print("✅ 이미 '국내'로 설정되어 있거나 드롭다운을 찾을 수 없습니다.")
            except Exception as e:
                print(f"⚠️ '국내' 옵션 강제 선택 중 오류 (무시됨): {str(e)}")

            # 2. 검색 입력 필드 찾기"""
            
    if target in content:
        content = content.replace(target, replacement)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Successfully updated naver_blog_post_finisher.py")
    else:
        print("Could not find the target string.")

if __name__ == "__main__":
    fix()
