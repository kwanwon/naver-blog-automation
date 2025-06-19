#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
개선된 타이핑 테스트
- 한글 입력기 문제 해결
- 더 정확한 입력 방법
- 단계별 검증
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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def improved_typing_test():
    print("🔍 개선된 타이핑 테스트 시작")
    
    # Chrome 옵션 설정 (최대한 자연스럽게)
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 더 자연스러운 사용자 에이전트
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 추가 자동화 감지 방지 옵션들
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    
    # 드라이버 설정
    driver_path = ChromeDriverManager().install()
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 자동화 감지 방지 스크립트들
    stealth_scripts = [
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});",
        "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});",
        "Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko', 'en-US', 'en']});",
        "Object.defineProperty(navigator, 'platform', {get: () => 'MacIntel'});",
        "Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});",
        "window.chrome = {runtime: {}};",
        "Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})});",
    ]
    
    for script in stealth_scripts:
        try:
            driver.execute_script(script)
        except:
            pass
    
    try:
        print("🌐 네이버 로그인 페이지로 이동...")
        driver.get('https://nid.naver.com/nidlogin.login')
        
        # 페이지 로딩 대기
        wait = WebDriverWait(driver, 10)
        
        print("⏳ 페이지 로딩 대기...")
        time.sleep(5)
        
        # ID 필드 찾기
        print("🔍 ID 필드 찾기...")
        id_field = wait.until(EC.presence_of_element_located((By.ID, "id")))
        pw_field = driver.find_element(By.ID, "pw")
        
        print("✅ 필드 찾기 완료")
        
        # 방법 1: 매우 느린 자연스러운 타이핑
        print("\n=== 방법 1: 매우 느린 자연스러운 타이핑 ===")
        
        # ID 필드 클릭 및 포커스
        print("📍 ID 필드 클릭...")
        id_field.click()
        time.sleep(2)
        
        # 기존 내용 완전히 지우기
        print("🗑️ 기존 내용 지우기...")
        id_field.clear()
        time.sleep(1)
        
        # 추가로 JavaScript로도 지우기
        driver.execute_script("document.getElementById('id').value = '';")
        time.sleep(1)
        
        # ID 입력 (매우 느리게)
        print("⌨️ ID 입력 중 (매우 느리게)...")
        test_id = "gm2hapkido"
        
        for i, char in enumerate(test_id):
            # 각 글자마다 클릭하여 포커스 유지
            id_field.click()
            time.sleep(0.2)
            
            # 한 글자씩 입력
            id_field.send_keys(char)
            
            # 입력 후 검증
            current_value = driver.execute_script("return document.getElementById('id').value;")
            print(f"  {i+1}글자 입력 후: '{current_value}'")
            
            # 랜덤 지연 (사람처럼)
            time.sleep(random.uniform(0.5, 1.0))
        
        # 최종 ID 값 확인
        final_id = driver.execute_script("return document.getElementById('id').value;")
        print(f"✅ 최종 ID 값: '{final_id}'")
        
        # 비밀번호 필드로 이동
        print("\n🔐 비밀번호 필드로 이동...")
        pw_field.click()
        time.sleep(2)
        
        # 비밀번호 필드 지우기
        pw_field.clear()
        time.sleep(1)
        driver.execute_script("document.getElementById('pw').value = '';")
        time.sleep(1)
        
        # 비밀번호 입력
        print("🔒 비밀번호 입력 중...")
        test_pw = "km909090##"
        
        for i, char in enumerate(test_pw):
            pw_field.click()
            time.sleep(0.2)
            pw_field.send_keys(char)
            time.sleep(random.uniform(0.3, 0.7))
        
        # 최종 비밀번호 길이 확인
        final_pw_length = len(driver.execute_script("return document.getElementById('pw').value;"))
        print(f"✅ 최종 비밀번호 길이: {final_pw_length}글자")
        
        # 잠시 대기 (사람처럼)
        print("\n⏳ 입력 완료 후 대기...")
        time.sleep(3)
        
        # 로그인 버튼 찾기 및 클릭
        print("🖱️ 로그인 버튼 클릭...")
        try:
            login_button = driver.find_element(By.ID, 'log.login')
            
            # 버튼이 클릭 가능할 때까지 대기
            wait.until(EC.element_to_be_clickable((By.ID, 'log.login')))
            
            # 사람처럼 잠시 망설이기
            time.sleep(random.uniform(1, 3))
            
            # 클릭
            login_button.click()
            print("✅ 로그인 버튼 클릭 완료")
            
        except Exception as e:
            print(f"❌ 로그인 버튼 클릭 실패: {e}")
        
        # 로그인 결과 대기
        print("\n⏳ 로그인 결과 대기 중...")
        time.sleep(8)
        
        # 현재 상태 확인
        current_url = driver.current_url
        page_title = driver.title
        
        print(f"현재 URL: {current_url}")
        print(f"페이지 제목: {page_title}")
        
        # 로그인 성공 여부 판단
        if "naver.com" in current_url and "nidlogin" not in current_url:
            print("🎉 로그인 성공!")
            
            # 네이버 메인으로 이동해서 확인
            print("📝 네이버 메인 페이지에서 로그인 상태 확인...")
            driver.get('https://www.naver.com')
            time.sleep(3)
            
            page_source = driver.page_source
            if "로그아웃" in page_source or "님" in page_source:
                print("✅ 네이버 메인에서도 로그인 상태 확인!")
            else:
                print("❌ 네이버 메인에서 로그인 상태 확인 안됨")
                
        else:
            print("❌ 로그인 실패")
            
            # 상세한 오류 분석
            page_source = driver.page_source
            
            if "자동입력 방지" in page_source or "자동화" in page_source:
                print("🤖 자동화 감지됨")
            elif "보안" in page_source:
                print("🛡️ 보안 검증 필요")
            elif "아이디" in page_source and "비밀번호" in page_source:
                print("🔒 로그인 정보 오류")
            elif "captcha" in page_source.lower():
                print("🔤 캡차 인증 필요")
            else:
                print("❓ 알 수 없는 오류")
                
            # 오류 메시지 찾기
            try:
                error_elements = driver.find_elements(By.CSS_SELECTOR, ".error_msg, .alert_msg, .warning")
                for elem in error_elements:
                    if elem.is_displayed():
                        print(f"오류 메시지: {elem.text}")
            except:
                pass
        
        # 스크린샷 저장 (디버깅용)
        try:
            screenshot_path = f"login_result_{int(time.time())}.png"
            driver.save_screenshot(screenshot_path)
            print(f"📸 스크린샷 저장: {screenshot_path}")
        except:
            pass
        
        # 결과 확인을 위한 대기
        print("\n⏳ 20초 대기 중... (수동으로 결과 확인 가능)")
        time.sleep(20)
        
    except Exception as e:
        print(f"❌ 전체 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("🔚 테스트 완료, 브라우저 종료")
        driver.quit()

if __name__ == "__main__":
    improved_typing_test()