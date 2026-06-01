import os

def fix():
    file_path = "/Users/gm2hapkido/Desktop/라이온개발자/naver_blog_post_finisher.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    target = """            confirmation_selectors = [
                "button.se-map-save-button",
                "button.place_confirm_btn",
                "button[data-log='map.save']",
                "button.se_map_apply_button",
                "button[class*='confirm']",
                "button[class*='submit']",
                "button[class*='save']"
            ]"""
            
    replacement = """            # 확인 버튼은 텍스트(XPath)로 명확히 찾기
            confirmation_selectors = [
                "button.se-map-save-button",
                "button.place_confirm_btn",
                "//button[contains(text(), '확인')]",
                "//a[contains(text(), '확인')]",
                "//button[contains(text(), '적용')]"
            ]"""

    if target in content:
        content = content.replace(target, replacement)
        
        # Also fix the selection method to handle XPath
        target2 = "EC.element_to_be_clickable((By.CSS_SELECTOR, selector))"
        replacement2 = "EC.element_to_be_clickable((By.XPATH if selector.startswith('//') else By.CSS_SELECTOR, selector))"
        content = content.replace(target2, replacement2)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Successfully updated confirm selectors.")
    else:
        print("Target not found.")

if __name__ == "__main__":
    fix()
