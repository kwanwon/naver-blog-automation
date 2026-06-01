import os

def fix():
    file_path = "/Users/gm2hapkido/Desktop/라이온개발자/naver_blog_post_finisher.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    target = """            # 위치 정보 준비"""
    
    replacement = """            # 🧹 남아있는 팝업 오버레이 제거 (이전 단계의 링크 삽입 등으로 인한 간섭 방지)
            try:
                self.driver.execute_script('''
                    document.querySelectorAll('.se-popup-dim, .se-popup-dim-transparent').forEach(function(el) {
                        el.style.display = 'none';
                        el.remove();
                    });
                ''')
            except:
                pass
                
            # 위치 정보 준비"""

    if target in content:
        content = content.replace(target, replacement)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Successfully added popup cleanup to add_location.")
    else:
        print("Target string not found.")

if __name__ == "__main__":
    fix()
