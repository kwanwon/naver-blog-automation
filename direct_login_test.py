#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
직접적인 로그인 테스트
- 실제 네이버 로그인 페이지 분석
- 정확한 선택자 확인
- 단계별 디버깅
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def direct_login_test():
    print("🔍 직접적인 로그인 테스트 시작")
    
    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 드라이버 설정
    driver_path = ChromeDriverManager().install()
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 자동화 감지 방지
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
    
    try:
        print("🌐 네이버 로그인 페이지로 이동...")
        driver.get('https://nid.naver.com/nidlogin.login')
        time.sleep(5)
        
        print(f"현재 URL: {driver.current_url}")
        print(f"페이지 제목: {driver.title}")
        
        # 페이지의 모든 input 요소 분석
        print("\n📋 페이지의 모든 input 요소 분석:")
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"총 input 요소 개수: {len(all_inputs)}")
        
        for i, inp in enumerate(all_inputs):
            try:
                input_type = inp.get_attribute('type')
                input_name = inp.get_attribute('name')
                input_id = inp.get_attribute('id')
                input_placeholder = inp.get_attribute('placeholder')
                input_class = inp.get_attribute('class')
                
                print(f"Input {i+1}:")
                print(f"  - type: {input_type}")
                print(f"  - name: {input_name}")
                print(f"  - id: {input_id}")
                print(f"  - placeholder: {input_placeholder}")
                print(f"  - class: {input_class}")
                print()
                
            except Exception as e:
                print(f"Input {i+1}: 정보 가져오기 실패 - {e}")
        
        # ID 필드 찾기 시도
        print("🔍 ID 필드 찾기 시도:")
        id_selectors = [
            (By.ID, "id"),
            (By.NAME, "id"),
            (By.CSS_SELECTOR, "input[name='id']"),
            (By.CSS_SELECTOR, "input[placeholder*='아이디']"),
            (By.CSS_SELECTOR, "input[type='text']"),
            (By.XPATH, "//input[@id='id']"),
            (By.XPATH, "//input[@name='id']")
        ]
        
        id_field = None
        for selector_type, selector_value in id_selectors:
            try:
                print(f"시도: {selector_type} = {selector_value}")
                id_field = driver.find_element(selector_type, selector_value)
                if id_field:
                    print(f"✅ ID 필드 발견! {selector_type}: {selector_value}")
                    break
            except Exception as e:
                print(f"실패: {e}")
        
        if id_field:
            print("\n⌨️ ID 입력 테스트:")
            try:
                # 클릭
                id_field.click()
                time.sleep(1)
                
                # 기존 내용 지우기
                id_field.clear()
                time.sleep(1)
                
                # ID 입력
                test_id = "gm2hapkido"
                print(f"입력할 ID: {test_id}")
                
                # 한 글자씩 입력
                for char in test_id:
                    id_field.send_keys(char)
                    time.sleep(0.2)
                
                print("✅ ID 입력 완료!")
                
                # 입력된 값 확인
                entered_value = id_field.get_attribute('value')
                print(f"실제 입력된 값: '{entered_value}'")
                
            except Exception as e:
                print(f"❌ ID 입력 실패: {e}")
        else:
            print("❌ ID 필드를 찾을 수 없습니다!")
        
        # 비밀번호 필드 찾기 시도
        print("\n🔍 비밀번호 필드 찾기 시도:")
        pw_selectors = [
            (By.ID, "pw"),
            (By.NAME, "pw"),
            (By.CSS_SELECTOR, "input[name='pw']"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.XPATH, "//input[@id='pw']"),
            (By.XPATH, "//input[@name='pw']")
        ]
        
        pw_field = None
        for selector_type, selector_value in pw_selectors:
            try:
                print(f"시도: {selector_type} = {selector_value}")
                pw_field = driver.find_element(selector_type, selector_value)
                if pw_field:
                    print(f"✅ 비밀번호 필드 발견! {selector_type}: {selector_value}")
                    break
            except Exception as e:
                print(f"실패: {e}")
        
        if pw_field:
            print("\n🔐 비밀번호 입력 테스트:")
            try:
                # 클릭
                pw_field.click()
                time.sleep(1)
                
                # 기존 내용 지우기
                pw_field.clear()
                time.sleep(1)
                
                # 비밀번호 입력
                test_pw = "km909090##"
                print("비밀번호 입력 중...")
                
                # 한 글자씩 입력
                for char in test_pw:
                    pw_field.send_keys(char)
                    time.sleep(0.2)
                
                print("✅ 비밀번호 입력 완료!")
                
            except Exception as e:
                print(f"❌ 비밀번호 입력 실패: {e}")
        else:
            print("❌ 비밀번호 필드를 찾을 수 없습니다!")
        
        # 로그인 버튼 찾기
        print("\n🔍 로그인 버튼 찾기:")
        login_selectors = [
            (By.ID, 'log.login'),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, ".btn_login"),
            (By.XPATH, "//input[@value='로그인']"),
            (By.XPATH, "//button[contains(text(), '로그인')]")
        ]
        
        login_button = None
        for selector_type, selector_value in login_selectors:
            try:
                print(f"시도: {selector_type} = {selector_value}")
                login_button = driver.find_element(selector_type, selector_value)
                if login_button:
                    print(f"✅ 로그인 버튼 발견! {selector_type}: {selector_value}")
                    break
            except Exception as e:
                print(f"실패: {e}")
        
        if login_button:
            print("\n🖱️ 로그인 버튼 클릭 테스트:")
            try:
                login_button.click()
                print("✅ 로그인 버튼 클릭 완료!")
                
                # 로그인 처리 대기
                print("⏳ 로그인 처리 대기 중...")
                time.sleep(5)
                
                # 결과 확인
                final_url = driver.current_url
                print(f"로그인 후 URL: {final_url}")
                
                if "nid.naver.com" not in final_url:
                    print("🎉 로그인 성공!")
                else:
                    print("❌ 로그인 실패 또는 추가 인증 필요")
                
            except Exception as e:
                print(f"❌ 로그인 버튼 클릭 실패: {e}")
        else:
            print("❌ 로그인 버튼을 찾을 수 없습니다!")
        
        print("\n10초 후 브라우저를 종료합니다...")
        time.sleep(10)
        
    except Exception as e:
        print(f"❌ 전체 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()
        print("✅ 브라우저 종료 완료")

if __name__ == "__main__":
    direct_login_test()