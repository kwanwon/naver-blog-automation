import time
import os
import sys

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium import webdriver

def main():
    print("Setting up Chrome...")
    options = Options()
    # Use the same profile as the app
    profile_path = "/Users/gm2hapkido/Library/Application Support/Google/Chrome"
    options.add_argument(f"user-data-dir={profile_path}")
    options.add_argument("profile-directory=Default")
    
    driver_path = ChromeDriverManager().install()
    if driver_path.endswith('THIRD_PARTY_NOTICES.chromedriver'):
        driver_path = os.path.dirname(driver_path) + '/chromedriver'
    service = ChromeService(executable_path=driver_path)
    
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print("Navigating to Naver Blog...")
        driver.get("https://blog.naver.com/gm2hapkido?Redirect=Write&categoryNo=13")
        
        print("Waiting for iframe...")
        # Switch to iframe
        frame = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "mainFrame"))
        )
        driver.switch_to.frame(frame)
        
        print("Waiting for video button...")
        # Click video button in toolbar
        video_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.se-toolbar-button-video"))
        )
        video_btn.click()
        
        print("Waiting for popup to appear...")
        time.sleep(2)
        
        driver.switch_to.default_content()
        
        print("Finding elements in popup...")
        # Dump HTML of the popup buttons
        buttons = driver.execute_script("""
            var elements = Array.from(document.querySelectorAll('.se-popup-container *')).filter(function(el) {
                return el.innerText && el.innerText.indexOf('동영상 추가') >= 0;
            });
            var res = [];
            for(var i=0; i<elements.length; i++) {
                res.push({
                    tag: elements[i].tagName,
                    class: elements[i].className,
                    text: elements[i].innerText,
                    html: elements[i].outerHTML
                });
            }
            return res;
        """)
        
        print("FOUND ELEMENTS WITH '동영상 추가':")
        for b in buttons:
            print(f"Tag: {b['tag']}, Class: {b['class']}")
            print(f"HTML: {b['html'][:200]}")
            print("-" * 30)
            
        print("Finding all file inputs...")
        inputs = driver.execute_script("""
            var inputs = document.querySelectorAll('input[type="file"]');
            var res = [];
            for(var i=0; i<inputs.length; i++) {
                res.push({
                    id: inputs[i].id,
                    class: inputs[i].className,
                    html: inputs[i].outerHTML
                });
            }
            return res;
        """)
        
        print("FOUND FILE INPUTS:")
        for inp in inputs:
            print(f"HTML: {inp['html'][:200]}")
            print("-" * 30)
            
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
