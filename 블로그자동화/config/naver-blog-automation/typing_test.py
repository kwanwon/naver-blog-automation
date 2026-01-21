#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
다양한 타이핑 방법 테스트
1. ActionChains를 사용한 자연스러운 타이핑
2. JavaScript를 통한 직접 입력
3. pyautogui를 사용한 실제 키보드 입력
"""

import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

def test_typing_methods():
    print("🔍 다양한 타이핑 방법 테스트 시작")
    
    # Chrome 옵션 설정 (더 자연스럽게)
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
    
    # 자동화 감지 방지 스크립트들
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
    driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});")
    driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko']});")
    
    try:
        print("🌐 네이버 로그인 페이지로 이동...")
        driver.get('https://nid.naver.com/nidlogin.login')
        time.sleep(3)
        
        # ID 필드 찾기
        id_field = driver.find_element(By.ID, "id")
        pw_field = driver.find_element(By.ID, "pw")
        
        print("\n=== 방법 1: ActionChains를 사용한 자연스러운 타이핑 ===")
        try:
            # ID 필드 클릭 및 포커스
            actions = ActionChains(driver)
            actions.click(id_field).perform()
            time.sleep(1)
            
            # 기존 내용 지우기
            actions.key_down(Keys.COMMAND).send_keys('a').key_up(Keys.COMMAND).perform()
            time.sleep(0.5)
            actions.send_keys(Keys.DELETE).perform()
            time.sleep(0.5)
            
            # ID 입력 (자연스러운 타이핑 속도)
            test_id = "gm2hapkido"
            for char in test_id:
                actions.send_keys(char).perform()
                time.sleep(random.uniform(0.1, 0.3))  # 랜덤 지연
            
            print("✅ ActionChains ID 입력 완료")
            
            # 비밀번호 필드로 이동
            actions.click(pw_field).perform()
            time.sleep(1)
            
            # 비밀번호 입력
            test_pw = "km909090##"
            for char in test_pw:
                actions.send_keys(char).perform()
                time.sleep(random.uniform(0.1, 0.3))
            
            print("✅ ActionChains 비밀번호 입력 완료")
            
        except Exception as e:
            print(f"❌ ActionChains 방법 실패: {e}")
        
        time.sleep(2)
        
        print("\n=== 방법 2: JavaScript를 통한 직접 입력 ===")
        try:
            # JavaScript로 값 설정
            driver.execute_script("document.getElementById('id').value = '';")
            driver.execute_script("document.getElementById('pw').value = '';")
            time.sleep(0.5)
            
            # 한 글자씩 JavaScript로 입력
            test_id = "gm2hapkido"
            for i, char in enumerate(test_id):
                current_value = test_id[:i+1]
                driver.execute_script(f"document.getElementById('id').value = '{current_value}';")
                driver.execute_script("document.getElementById('id').dispatchEvent(new Event('input', {bubbles: true}));")
                time.sleep(random.uniform(0.1, 0.2))
            
            test_pw = "km909090##"
            for i, char in enumerate(test_pw):
                current_value = test_pw[:i+1]
                driver.execute_script(f"document.getElementById('pw').value = '{current_value}';")
                driver.execute_script("document.getElementById('pw').dispatchEvent(new Event('input', {bubbles: true}));")
                time.sleep(random.uniform(0.1, 0.2))
            
            print("✅ JavaScript 입력 완료")
            
        except Exception as e:
            print(f"❌ JavaScript 방법 실패: {e}")
        
        time.sleep(2)
        
        print("\n=== 방법 3: 혼합 방법 (클릭 + 자연스러운 send_keys) ===")
        try:
            # 필드 클릭하여 포커스
            id_field.click()
            time.sleep(0.5)
            
            # 전체 선택 후 삭제
            id_field.send_keys(Keys.COMMAND + 'a')
            time.sleep(0.2)
            id_field.send_keys(Keys.DELETE)
            time.sleep(0.5)
            
            # 자연스러운 타이핑
            test_id = "gm2hapkido"
            for char in test_id:
                id_field.send_keys(char)
                time.sleep(random.uniform(0.15, 0.35))  # 사람처럼 불규칙한 타이핑
            
            # 비밀번호 필드
            pw_field.click()
            time.sleep(0.5)
            pw_field.send_keys(Keys.COMMAND + 'a')
            time.sleep(0.2)
            pw_field.send_keys(Keys.DELETE)
            time.sleep(0.5)
            
            test_pw = "km909090##"
            for char in test_pw:
                pw_field.send_keys(char)
                time.sleep(random.uniform(0.15, 0.35))
            
            print("✅ 혼합 방법 입력 완료")
            
        except Exception as e:
            print(f"❌ 혼합 방법 실패: {e}")
        
        # 입력 결과 확인
        print("\n📋 입력 결과 확인:")
        try:
            id_value = driver.execute_script("return document.getElementById('id').value;")
            pw_value = driver.execute_script("return document.getElementById('pw').value;")
            print(f"ID 필드 값: '{id_value}'")
            print(f"PW 필드 값 길이: {len(pw_value)} 글자")
        except Exception as e:
            print(f"값 확인 실패: {e}")
        
        # 로그인 시도
        print("\n🔐 로그인 시도...")
        try:
            login_button = driver.find_element(By.ID, 'log.login')
            
            # 버튼 클릭 전 잠시 대기 (사람처럼)
            time.sleep(random.uniform(1, 2))
            login_button.click()
            
            print("✅ 로그인 버튼 클릭 완료")
            
            # 로그인 결과 대기
            time.sleep(5)
            
            current_url = driver.current_url
            print(f"로그인 후 URL: {current_url}")
            
            # 로그인 성공 여부 확인
            if "naver.com" in current_url and "nidlogin" not in current_url:
                print("🎉 로그인 성공!")
            else:
                print("❌ 로그인 실패 또는 추가 인증 필요")
                
                # 페이지 소스에서 오류 메시지 확인
                page_source = driver.page_source
                if "자동입력 방지" in page_source:
                    print("🤖 자동입력 방지 감지됨")
                elif "아이디" in page_source and "비밀번호" in page_source:
                    print("🔒 로그인 정보 오류 또는 보안 검증 필요")
                
        except Exception as e:
            print(f"❌ 로그인 시도 실패: {e}")
        
        # 잠시 대기하여 결과 확인
        print("\n⏳ 10초 대기 중... (수동으로 확인 가능)")
        time.sleep(10)
        
    except Exception as e:
        print(f"❌ 전체 테스트 실패: {e}")
    
    finally:
        print("🔚 테스트 완료, 브라우저 종료")
        driver.quit()

if __name__ == "__main__":
    test_typing_methods() 