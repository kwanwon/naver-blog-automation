#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
실제 키보드 입력을 사용한 로그인 테스트
pyautogui를 사용하여 진짜 키보드 타이핑을 시뮬레이션
"""

import os
import time
import random
import pyautogui
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def real_keyboard_login_test():
    print("⌨️ 실제 키보드 입력 테스트 시작")
    
    # pyautogui 설정
    pyautogui.FAILSAFE = True  # 마우스를 화면 모서리로 이동하면 중단
    pyautogui.PAUSE = 0.1  # 각 pyautogui 호출 사이의 기본 지연
    
    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 사용자 에이전트 설정
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 드라이버 설정
    driver_path = ChromeDriverManager().install()
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 자동화 감지 방지
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
    driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});")
    driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko']});")
    
    try:
        print("🌐 네이버 로그인 페이지로 이동...")
        driver.get('https://nid.naver.com/nidlogin.login')
        time.sleep(3)
        
        # ID 필드 찾기 및 위치 확인
        id_field = driver.find_element(By.ID, "id")
        pw_field = driver.find_element(By.ID, "pw")
        
        print("📍 ID 필드 위치 확인 및 클릭...")
        # Selenium으로 필드 클릭하여 포커스
        id_field.click()
        time.sleep(1)
        
        # 기존 내용 지우기 (실제 키보드 단축키 사용)
        print("🗑️ 기존 내용 지우기...")
        pyautogui.hotkey('cmd', 'a')  # 전체 선택 (macOS)
        time.sleep(0.3)
        pyautogui.press('delete')
        time.sleep(0.5)
        
        # ID 입력 (실제 키보드 타이핑)
        print("⌨️ ID 입력 중...")
        test_id = "gm2hapkido"
        for char in test_id:
            pyautogui.write(char)
            time.sleep(random.uniform(0.1, 0.3))  # 자연스러운 타이핑 속도
        
        print("✅ ID 입력 완료")
        
        # 비밀번호 필드로 이동
        print("🔐 비밀번호 필드로 이동...")
        pw_field.click()
        time.sleep(1)
        
        # 기존 내용 지우기
        pyautogui.hotkey('cmd', 'a')
        time.sleep(0.3)
        pyautogui.press('delete')
        time.sleep(0.5)
        
        # 비밀번호 입력
        print("🔒 비밀번호 입력 중...")
        test_pw = "km909090##"
        for char in test_pw:
            pyautogui.write(char)
            time.sleep(random.uniform(0.1, 0.3))
        
        print("✅ 비밀번호 입력 완료")
        
        # 입력 결과 확인
        print("\n📋 입력 결과 확인:")
        try:
            id_value = driver.execute_script("return document.getElementById('id').value;")
            pw_value = driver.execute_script("return document.getElementById('pw').value;")
            print(f"ID 필드 값: '{id_value}'")
            print(f"PW 필드 값 길이: {len(pw_value)} 글자")
        except Exception as e:
            print(f"값 확인 실패: {e}")
        
        # 로그인 버튼 클릭
        print("\n🖱️ 로그인 버튼 클릭...")
        try:
            login_button = driver.find_element(By.ID, 'log.login')
            
            # 사람처럼 잠시 대기
            time.sleep(random.uniform(1, 2))
            
            # 실제 마우스 클릭 사용
            button_location = login_button.location_once_scrolled_into_view
            button_size = login_button.size
            
            # 버튼 중앙 계산
            click_x = button_location['x'] + button_size['width'] // 2
            click_y = button_location['y'] + button_size['height'] // 2
            
            # 실제 마우스 클릭
            pyautogui.click(click_x, click_y)
            
            print("✅ 로그인 버튼 클릭 완료")
            
        except Exception as e:
            print(f"❌ 로그인 버튼 클릭 실패: {e}")
            # 대안: Selenium 클릭
            try:
                login_button = driver.find_element(By.ID, 'log.login')
                login_button.click()
                print("✅ Selenium으로 로그인 버튼 클릭 완료")
            except Exception as e2:
                print(f"❌ Selenium 클릭도 실패: {e2}")
        
        # 로그인 결과 대기 및 확인
        print("\n⏳ 로그인 결과 대기 중...")
        time.sleep(5)
        
        current_url = driver.current_url
        print(f"현재 URL: {current_url}")
        
        # 로그인 성공 여부 확인
        if "naver.com" in current_url and "nidlogin" not in current_url:
            print("🎉 로그인 성공!")
            
            # 네이버 블로그로 이동 테스트
            print("📝 네이버 블로그로 이동 테스트...")
            driver.get('https://blog.naver.com')
            time.sleep(3)
            
            blog_url = driver.current_url
            print(f"블로그 URL: {blog_url}")
            
            # 로그인 상태 확인
            page_source = driver.page_source
            if "로그아웃" in page_source or "님" in page_source:
                print("✅ 블로그에서도 로그인 상태 확인됨!")
            else:
                print("❌ 블로그에서 로그인 상태 확인 안됨")
                
        else:
            print("❌ 로그인 실패")
            
            # 오류 메시지 확인
            page_source = driver.page_source
            if "자동입력 방지" in page_source:
                print("🤖 자동입력 방지 문구 감지")
            elif "아이디" in page_source and "비밀번호" in page_source:
                print("🔒 로그인 정보 오류 또는 추가 인증 필요")
            elif "보안" in page_source:
                print("🛡️ 보안 검증 필요")
        
        # 결과 확인을 위한 대기
        print("\n⏳ 15초 대기 중... (수동으로 결과 확인 가능)")
        time.sleep(15)
        
    except Exception as e:
        print(f"❌ 전체 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("🔚 테스트 완료, 브라우저 종료")
        driver.quit()

if __name__ == "__main__":
    print("⚠️ 주의: 이 테스트는 실제 키보드와 마우스를 제어합니다.")
    print("테스트 중에는 다른 작업을 하지 마세요.")
    print("5초 후 시작됩니다...")
    
    for i in range(5, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    
    real_keyboard_login_test() 