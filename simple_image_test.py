#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def simple_image_test():
    """간단한 이미지 삽입 테스트"""
    
    # 테스트할 이미지 파일 경로 설정
    test_image_path = None
    
    # 이미지 파일 찾기
    image_folders = ['default_images', 'default_images_1', 'default_images_2']
    for folder in image_folders:
        if os.path.exists(folder):
            for file in os.listdir(folder):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    test_image_path = os.path.abspath(os.path.join(folder, file))
                    print(f"테스트용 이미지 파일 발견: {test_image_path}")
                    break
            if test_image_path:
                break
    
    if not test_image_path:
        print("❌ 테스트할 이미지 파일을 찾을 수 없습니다.")
        return
    
    print(f"✅ 사용할 이미지: {test_image_path}")
    print("\n=== 이미지 삽입 테스트 시작 ===")
    print("1. 먼저 블로그 앱에서 수동 로그인을 완료하세요.")
    print("2. 블로그 글쓰기 페이지로 이동하세요.")
    print("3. 아무 글이나 입력하세요.")
    print("4. 이 스크립트를 실행하면 이미지 삽입을 시도합니다.")
    
    input("\n준비가 되면 Enter를 누르세요...")
    
    # Chrome 브라우저 찾기 (기존 세션 활용)
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    
    # 새 브라우저 인스턴스 생성 (기존 프로필 사용)
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver_path = ChromeDriverManager().install()
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        print("\n1. 네이버 블로그로 이동...")
        driver.get('https://blog.naver.com/gm2hapkido?Redirect=Write&')
        time.sleep(3)
        
        print("2. iframe 전환 시도...")
        try:
            iframe = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "mainFrame"))
            )
            driver.switch_to.frame(iframe)
            print("✅ iframe 전환 성공")
        except Exception as e:
            print(f"❌ iframe 전환 실패: {e}")
            print("수동으로 로그인하고 다시 시도하세요.")
            return
        
        print("3. 본문 영역 찾기...")
        try:
            # 본문 영역 클릭
            body_area = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.se-component.se-text.se-l-default"))
            )
            body_area.click()
            print("✅ 본문 영역 클릭 성공")
            time.sleep(1)
        except Exception as e:
            print(f"❌ 본문 영역 클릭 실패: {e}")
        
        print("4. 이미지 버튼 찾기...")
        try:
            # 이미지 버튼 클릭
            image_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.se-image-toolbar-button"))
            )
            print(f"✅ 이미지 버튼 발견: {image_btn.get_attribute('class')}")
            
            image_btn.click()
            print("✅ 이미지 버튼 클릭 성공")
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ 이미지 버튼 클릭 실패: {e}")
            return
        
        print("5. 파일 입력 요소 찾기...")
        try:
            # 파일 입력 요소 찾기
            file_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            print("✅ 파일 입력 요소 발견")
            
            # 파일 경로 입력
            file_input.send_keys(test_image_path)
            print(f"✅ 파일 경로 입력 완료: {os.path.basename(test_image_path)}")
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ 파일 입력 실패: {e}")
            return
        
        print("6. 이미지 업로드 대기...")
        try:
            # 이미지가 업로드되었는지 확인
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.se-image-container img, img[src*='http']"))
            )
            print("✅ 이미지 업로드 확인됨")
            
        except Exception as e:
            print(f"❌ 이미지 업로드 확인 실패: {e}")
        
        print("7. 레이아웃 선택 및 확인...")
        try:
            # 레이아웃 선택 (기본값 사용)
            time.sleep(1)
            
            # 확인 버튼 찾기 및 클릭
            confirm_selectors = [
                'button.se-image-dialog-btn-submit',
                'button.se-dialog-btn-submit', 
                'button.se-btn-confirm',
                'button[class*="submit"]',
                'button[class*="confirm"]'
            ]
            
            confirm_clicked = False
            for selector in confirm_selectors:
                try:
                    confirm_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if confirm_btn.is_displayed():
                        confirm_btn.click()
                        confirm_clicked = True
                        print(f"✅ 확인 버튼 클릭 성공: {selector}")
                        break
                except:
                    continue
            
            if not confirm_clicked:
                print("❌ 확인 버튼을 찾을 수 없습니다. 수동으로 확인 버튼을 클릭하세요.")
            
            time.sleep(2)
            
        except Exception as e:
            print(f"레이아웃 선택 중 오류: {e}")
        
        print("\n✅ 이미지 삽입 테스트 완료!")
        print("브라우저에서 이미지가 삽입되었는지 확인해보세요.")
        
        print("\n30초 후 브라우저를 닫습니다...")
        time.sleep(30)
        
    except Exception as e:
        print(f"전체 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("브라우저 종료...")
        driver.quit()

if __name__ == "__main__":
    simple_image_test() 