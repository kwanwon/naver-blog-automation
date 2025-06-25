#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def test_image_insertion():
    """네이버 블로그 에디터에서 이미지 삽입 테스트"""
    
    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # ChromeDriver 자동 설정
    driver_path = ChromeDriverManager().install()
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        print("1. 네이버 블로그 글쓰기 페이지로 이동...")
        driver.get('https://blog.naver.com/gm2hapkido?Redirect=Write&')
        time.sleep(5)
        
        print("2. iframe 전환...")
        try:
            iframe = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "mainFrame"))
            )
            driver.switch_to.frame(iframe)
            print("✅ iframe 전환 성공")
        except Exception as e:
            print(f"❌ iframe 전환 실패: {e}")
            return
        
        print("3. 본문 영역 클릭...")
        try:
            body_area = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.se-component.se-text.se-l-default"))
            )
            body_area.click()
            print("✅ 본문 영역 클릭 성공")
            time.sleep(1)
        except Exception as e:
            print(f"❌ 본문 영역 클릭 실패: {e}")
        
        print("4. 현재 페이지의 이미지 관련 요소들 확인...")
        
        # 이미지 버튼 찾기
        image_buttons = driver.find_elements(By.CSS_SELECTOR, "button[class*='image']")
        print(f"이미지 관련 버튼 수: {len(image_buttons)}")
        
        for i, btn in enumerate(image_buttons):
            try:
                print(f"  버튼 {i+1}: class='{btn.get_attribute('class')}', text='{btn.text}', title='{btn.get_attribute('title')}'")
            except:
                pass
        
        # 파일 입력 요소 확인
        file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        print(f"파일 입력 요소 수: {len(file_inputs)}")
        
        print("5. 이미지 버튼 클릭 테스트...")
        try:
            # 가장 가능성 높은 이미지 버튼 클릭
            image_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.se-image-toolbar-button"))
            )
            print(f"이미지 버튼 발견: {image_btn.get_attribute('class')}")
            image_btn.click()
            print("✅ 이미지 버튼 클릭 성공")
            time.sleep(2)
            
            # 클릭 후 파일 입력 요소 다시 확인
            file_inputs_after = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            print(f"이미지 버튼 클릭 후 파일 입력 요소 수: {len(file_inputs_after)}")
            
            if file_inputs_after:
                for i, inp in enumerate(file_inputs_after):
                    try:
                        print(f"  파일 입력 {i+1}: class='{inp.get_attribute('class')}', style='{inp.get_attribute('style')}', visible={inp.is_displayed()}")
                    except:
                        pass
            
            # 이미지 업로드 대화상자 확인
            dialogs = driver.find_elements(By.CSS_SELECTOR, "div[class*='dialog'], div[class*='popup'], div[class*='modal']")
            print(f"대화상자/팝업 수: {len(dialogs)}")
            
            for i, dialog in enumerate(dialogs):
                try:
                    if dialog.is_displayed():
                        print(f"  표시된 대화상자 {i+1}: class='{dialog.get_attribute('class')}'")
                except:
                    pass
                    
        except Exception as e:
            print(f"❌ 이미지 버튼 클릭 실패: {e}")
        
        print("6. 현재 페이지 HTML 구조 일부 출력...")
        try:
            # 툴바 영역 HTML 확인
            toolbar = driver.find_element(By.CSS_SELECTOR, "div.se-toolbar")
            print("툴바 HTML (일부):")
            print(toolbar.get_attribute('outerHTML')[:500] + "...")
        except:
            print("툴바 HTML 확인 실패")
        
        print("\n7. 30초 대기 (수동 확인용)...")
        time.sleep(30)
        
    except Exception as e:
        print(f"전체 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("브라우저 종료...")
        driver.quit()

if __name__ == "__main__":
    test_image_insertion() 