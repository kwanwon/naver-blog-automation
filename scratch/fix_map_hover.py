import os

def fix():
    file_path = "/Users/gm2hapkido/Desktop/라이온개발자/naver_blog_post_finisher.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the result selection block
    target = """            for selector in result_selectors:
                try:
                    print(f"검색 결과 선택자 시도: {selector}")
                    result_item = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    result_item.click()
                    result_selected = True
                    print("첫 번째 검색 결과 선택 성공")
                    break
                except Exception as e:
                    print(f"검색 결과 선택자 {selector} 실패: {str(e)}")"""

    replacement = """            # 텍스트 기반으로 검색 결과 항목 찾기 (CSS 클래스가 동적으로 변할 수 있음)
            try:
                print("검색 결과 항목 텍스트로 찾기 시도...")
                # 쿼리의 첫 3글자 이상으로 검색 (띄어쓰기 문제 방지)
                query_prefix = search_query[:4] if len(search_query) >= 4 else search_query
                
                # XPath로 텍스트가 포함된 모든 요소 찾기
                elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{query_prefix}')]")
                
                # 가장 적합한 목록 아이템(div, li 등) 찾기
                target_item = None
                for el in elements:
                    try:
                        if el.is_displayed() and el.tag_name.lower() in ['div', 'li', 'a']:
                            # 내용이 길면 부모 컨테이너일 확률이 높으므로 텍스트 길이 제한
                            if 0 < len(el.text) < 100: 
                                target_item = el
                                break
                    except:
                        pass
                
                if target_item:
                    print(f"검색 결과 항목 발견: {target_item.text[:20]}")
                    
                    # 1. ActionChains로 마우스를 올려서 호버 이벤트 발생 (+추가 버튼 나타나게 함)
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(self.driver)
                    actions.move_to_element(target_item).perform()
                    time.sleep(1)
                    
                    # 2. 호버 후 '추가' 버튼이 나타났는지 확인하고 클릭
                    add_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), '추가') or contains(., '추가')]")
                    visible_add_btn = None
                    for btn in add_buttons:
                        if btn.is_displayed():
                            visible_add_btn = btn
                            break
                            
                    if visible_add_btn:
                        print("'추가' 버튼을 발견하여 클릭합니다.")
                        visible_add_btn.click()
                        result_selected = True
                    else:
                        print("'추가' 버튼이 보이지 않아 항목 자체를 클릭합니다.")
                        target_item.click()
                        result_selected = True
            except Exception as e:
                print(f"텍스트 기반 검색 결과 선택 실패: {str(e)}")
                
            if not result_selected:
                # 기존 CSS 선택자 방식 (백업)"""

    if target in content:
        content = content.replace(target, replacement)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Successfully updated hover logic.")
    else:
        print("Target not found.")

if __name__ == "__main__":
    fix()
