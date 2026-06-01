import os

def fix():
    file_path = "/Users/gm2hapkido/Desktop/라이온개발자/naver_blog_post_finisher.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # We will replace the ensureDomestic function
    old_func = "el.innerText && el.innerText.trim() === '해외' &&"
    new_func = "el.innerText && el.innerText.includes('해외') &&"
    
    old_dom = "el.innerText && el.innerText.trim() === '국내'"
    new_dom = "el.innerText && el.innerText.includes('국내') && el.tagName !== 'BUTTON'"

    if old_func in content:
        content = content.replace(old_func, new_func)
        content = content.replace(old_dom, new_dom)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Successfully updated naver_blog_post_finisher.py again for more robust matching.")
    else:
        print("Could not find the target string to update.")

if __name__ == "__main__":
    fix()
