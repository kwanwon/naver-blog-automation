import os

def fix_location():
    file_path = "/Users/gm2hapkido/Desktop/라이온개발자/naver_blog_post_finisher.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_str = "            # 🧹 장소 추가 전: 남아있는 팝업 오버레이 제거"
    start_idx = content.find(start_str)
    if start_idx == -1:
        print("Error: Could not find start string.")
        return

    end_str = "    def _switch_to_main_frame_robust(self):"
    end_idx = content.find(end_str)
    if end_idx == -1:
        print("Error: Could not find end string.")
        return

    replacement = """            # 3. Add Location (Maps) using the robust separate method
            print("[Footer] Proceeding to location/map addition...")
            try:
                location_success = self.add_location()
                if location_success:
                    print("✅ [Footer] Location information added successfully")
                else:
                    print("⚠️ [Footer] Location addition returned False (non-blocking)")
            except Exception as loc_err:
                print(f"⚠️ [Footer] Location addition failed with exception (bypassed): {str(loc_err)}")

            return True
            
        except Exception as e:
            print(f"⚠️ 푸터 추가 중 오류 (계속 진행): {str(e)}")
            return True
            
"""
    
    fixed_content = content[:start_idx] + replacement + content[end_idx:]

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(fixed_content)
    print("Success: naver_blog_post_finisher.py location logic replaced successfully!")

if __name__ == "__main__":
    fix_location()
