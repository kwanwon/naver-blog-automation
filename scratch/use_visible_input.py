import os

def fix():
    file_path = "/Users/gm2hapkido/Desktop/라이온개발자/naver_blog_post_finisher.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    target = """                    search_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    
                    search_input.clear()"""
    
    replacement = """                    # 화면에 보이는 요소만 선택
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    search_input = None
                    for el in elements:
                        if el.is_displayed():
                            search_input = el
                            break
                    
                    if not search_input:
                        raise Exception("보이는 검색 입력창이 없음")
                        
                    search_input.clear()"""

    if target in content:
        content = content.replace(target, replacement)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Successfully updated search_input to only use visible element.")
    else:
        print("Target string not found.")

if __name__ == "__main__":
    fix()
