import os

def fix():
    file_path = "/Users/gm2hapkido/Desktop/라이온개발자/naver_blog_post_finisher.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_str = "            # 1.5 '국내' 옵션 강제 선택 (해외로 설정되어 있을 경우 대비)"
    end_str = "            # 2. 검색 입력 필드 찾기"
    
    start_idx = content.find(start_str)
    end_idx = content.find(end_str)
    
    if start_idx == -1 or end_idx == -1:
        print("Target block not found.")
        return
        
    replacement = """            # 1.5 '국내' 옵션 강제 선택 (해외로 설정되어 있을 경우 대비)
            print("지도 검색 '국내/해외' 옵션 확인 및 '국내' 강제 선택 시도 (Selenium 활용)")
            try:
                # '해외' 버튼이 활성화되어 있는지 확인
                region_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button")
                overseas_btn = None
                
                for btn in region_buttons:
                    try:
                        text = btn.text.strip()
                        if text == '해외' or '해외' in text:
                            overseas_btn = btn
                            break
                    except:
                        pass
                        
                if overseas_btn:
                    print("⚠️ '해외' 로 설정된 것을 감지했습니다. '국내'로 변경을 시도합니다.")
                    overseas_btn.click()
                    time.sleep(1)
                    
                    # 드롭다운에서 '국내' 옵션 클릭
                    dropdown_items = self.driver.find_elements(By.CSS_SELECTOR, "li, button, a, span")
                    for item in dropdown_items:
                        try:
                            item_text = item.text.strip()
                            # 팝업 리스트의 항목인지 확인
                            if item_text == '국내' and item != overseas_btn:
                                item.click()
                                print("✅ '국내' 옵션으로 변경 완료")
                                time.sleep(1)
                                break
                        except:
                            pass
                else:
                    print("✅ 이미 '국내'로 설정되어 있거나 드롭다운을 찾을 수 없습니다.")
            except Exception as e:
                print(f"⚠️ '국내' 옵션 강제 선택 중 오류 (무시됨): {str(e)}")

"""
    new_content = content[:start_idx] + replacement + content[end_idx:]
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Successfully updated domestic selection to use Selenium.")

if __name__ == "__main__":
    fix()
