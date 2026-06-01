import os

def fix():
    file_path = "/Users/gm2hapkido/Desktop/라이온개발자/naver_blog_post_finisher.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Fix the result selection fallback script
    target_result_script = """                script = f\"\"\"
                const items = document.querySelectorAll('li, .place_search_item, .se-map-search-result-item');
                for (const item of items) {
                    if (item.innerText && item.innerText.trim().length > 0) {
                        item.click();
                        return true;
                    }
                }
                return false;
                \"\"\""""
                
    replacement_result_script = """                script = f\"\"\"
                // 1. '추가' 버튼 직접 찾기 (호버 시에만 보여도 DOM에는 존재함)
                const buttons = document.querySelectorAll('button, a');
                for (const btn of buttons) {
                    if (btn.innerText && btn.innerText.includes('추가')) {
                        btn.click();
                        return true;
                    }
                }
                
                // 2. 검색어와 일치하는 결과 아이템 클릭
                const items = document.querySelectorAll('li, div[class*="item"], div[class*="result"]');
                for (const item of items) {
                    if (item.innerText && item.innerText.includes('{search_query}')) {
                        item.click();
                        return true;
                    }
                }
                return false;
                \"\"\""""

    if target_result_script in content:
        content = content.replace(target_result_script, replacement_result_script)
        print("Updated result script fallback.")
    else:
        print("Could not find target_result_script")

    # 2. Fix the confirm button selector
    target_confirm = """            confirm_selectors = [
                "button.se-map-save-button",
                "button[data-type='save']",
                ".se-map-button-save",
                "button:contains('적용')",
                "button:contains('확인')"
            ]"""
            
    replacement_confirm = """            confirm_selectors = [
                "button.se-map-save-button",
                "button[data-type='save']",
                ".se-map-button-save",
                "button[class*='confirm']",
                "button[class*='submit']"
            ]"""

    if target_confirm in content:
        content = content.replace(target_confirm, replacement_confirm)
        print("Updated confirm selectors.")
    else:
        print("Could not find target_confirm")

    # 3. Fix the confirm button fallback script
    target_confirm_script = """                script = \"\"\"
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.innerText && (btn.innerText.includes('적용') || btn.innerText.includes('확인'))) {
                        btn.click();
                        return true;
                    }
                }
                return false;
                \"\"\""""

    replacement_confirm_script = """                script = \"\"\"
                const buttons = document.querySelectorAll('button, a');
                for (const btn of buttons) {
                    // 텍스트가 '확인'이거나 '적용'인 버튼 클릭
                    if (btn.innerText && (btn.innerText.trim() === '확인' || btn.innerText.trim() === '적용')) {
                        btn.click();
                        return true;
                    }
                }
                return false;
                \"\"\""""

    if target_confirm_script in content:
        content = content.replace(target_confirm_script, replacement_confirm_script)
        print("Updated confirm script fallback.")
    else:
        print("Could not find target_confirm_script")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Done applying fixes.")

if __name__ == "__main__":
    fix()
