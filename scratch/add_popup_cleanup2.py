import os

def fix():
    file_path = "/Users/gm2hapkido/Desktop/라이온개발자/naver_blog_post_finisher.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    target = """            # 🧹 남아있는 팝업 오버레이 제거 (이전 단계의 링크 삽입 등으로 인한 간섭 방지)
            try:
                self.driver.execute_script('''
                    document.querySelectorAll('.se-popup-dim, .se-popup-dim-transparent').forEach(function(el) {
                        el.style.display = 'none';
                        el.remove();
                    });
                ''')
            except:
                pass"""
    
    replacement = """            # 🧹 남아있는 팝업 오버레이 제거 (이전 단계의 링크 삽입 등으로 인한 간섭 방지)
            try:
                self.driver.switch_to.default_content()
                self.driver.execute_script('''
                    document.querySelectorAll('.se-popup-dim, .se-popup-dim-transparent').forEach(function(el) {
                        el.style.display = 'none';
                        el.remove();
                    });
                ''')
                self.driver.switch_to.frame("mainFrame")
            except:
                pass"""

    if target in content:
        content = content.replace(target, replacement)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Successfully updated popup cleanup logic to use default_content.")
    else:
        print("Target string not found.")

if __name__ == "__main__":
    fix()
