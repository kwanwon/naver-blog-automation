import json
import urllib.request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    try:
        # Get active tabs from 9222
        req = urllib.request.Request("http://localhost:9222/json")
        with urllib.request.urlopen(req) as response:
            tabs = json.loads(response.read().decode())
        
        blog_tab = next((t for t in tabs if 'blog.naver.com' in t.get('url', '')), None)
        if not blog_tab:
            print("No naver blog tab found.")
            return

        print(f"Found blog tab: {blog_tab['title']}")
        
        options = Options()
        options.debugger_address = "localhost:9222"
        driver = webdriver.Chrome(options=options)
        
        # We are connected to the active browser.
        # Let's switch to mainFrame if possible
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame("mainFrame")
            print("Switched to mainFrame")
        except Exception as e:
            print(f"Could not switch to mainFrame: {e}")

        # Dump HTML containing '국내' or '해외'
        html = driver.page_source
        
        import re
        # Find snippets around '국내'
        matches = re.finditer(r'.{0,150}국내.{0,150}', html, re.DOTALL)
        print("\n--- DOM Snippets containing '국내' ---")
        for i, m in enumerate(matches):
            if i > 5: break
            print(m.group(0).strip())
            print("-" * 40)
            
        driver.quit()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
