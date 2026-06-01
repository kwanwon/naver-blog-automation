import os

def fix():
    file_path = "/Users/gm2hapkido/Desktop/라이온개발자/naver_blog_post_finisher.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    target = """            search_input_selectors = [
                "input.se-map-search-input",
                "input.place_search_input",
                "input[placeholder*='검색']",
                "input[placeholder*='장소']",
                ".se-map-search input",
                "input[type='text'][class*='search']"
            ]"""
    
    replacement = """            # 검색 입력 필드 (정확한 클래스 우선, generic 속성 지양)
            search_input_selectors = [
                "input.se-map-search-input",
                "input.place_search_input",
                ".se-map-search input",
                "input[placeholder*='장소']",
                "input[placeholder*='지역']"
            ]"""

    if target in content:
        content = content.replace(target, replacement)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Successfully updated search_input_selectors.")
    else:
        print("Target string not found.")

if __name__ == "__main__":
    fix()
