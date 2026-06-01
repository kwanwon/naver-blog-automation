import os
import re

APP_PATH = "/Users/gm2hapkido/Desktop/라이온개발자/blog_writer_app.py"

with open(APP_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 통합 파이프라인 함수 코드 정의
UNIFIED_PIPELINE_CODE = """
    def _execute_unified_blog_posting(self, page, topic, content_str, target_folder=None, reservation_time=None, ai_tags=None, title=None):
        \"\"\"
        [핵심 통합 파이프라인]
        타이머, 일반, 스케줄 예약, 폴더 감지 4가지 모드가 모두 이 단일 함수를 통해 블로그에 포스팅합니다.
        \"\"\"
        try:
            print(f"🚀 통합 파이프라인 시작 (주제: {topic[:15]}...)")
            from naver_blog_auto import NaverBlogAutomation
            from naver_blog_post_finisher import NaverBlogPostFinisher
            import os
            
            # --- 1. 모바일 가독성 포맷팅 (23자/문단 보호 룰) ---
            def format_content_for_mobile(text, max_chars=25):
                formatted = ""
                for paragraph in text.split('\\n'):
                    if not paragraph.strip():
                        formatted += "\\n"
                        continue
                    current_line = ""
                    for word in paragraph.split():
                        if len(word) > max_chars:
                            if current_line: formatted += current_line + "\\n"
                            formatted += word + "\\n"
                            current_line = ""
                            continue
                        if len(current_line) + len(word) + (1 if current_line else 0) > max_chars:
                            formatted += current_line + "\\n"
                            current_line = word
                        else:
                            current_line += (" " + word) if current_line else word
                    if current_line: formatted += current_line + "\\n"
                    formatted += "\\n"
                return formatted.strip()

            content_str = format_content_for_mobile(content_str)
            
            # --- 2. 첫 문장 및 슬로건 강제 삽입 (모든 모드 공통 적용) ---
            f_sent = self.settings.get('blog_first_sentence', self.settings.get('first_sentence', '')).strip()
            s_sent = self.settings.get('blog_slogan', self.settings.get('slogan', '')).strip()
            if f_sent and f_sent not in content_str:
                content_str = f"{f_sent}\\n\\n{content_str}"
            if s_sent and s_sent not in content_str:
                content_str = f"{content_str}\\n\\n{s_sent}"
                
            final_title = title if title else topic

            # --- 3. 브라우저 및 드라이버 준비 ---
            driver = self.get_or_create_driver()
            if not driver:
                print("❌ 유효한 브라우저 세션을 얻지 못했습니다.")
                return False

            # --- 4. 이미지 폴더 및 삽입 모드 결정 ---
            image_mode = getattr(self, 'blog_image_mode_dropdown', None)
            image_mode_val = image_mode.value if image_mode else "auto"
            custom_images_folder = None
            images_available = False
            
            if target_folder and os.path.exists(target_folder):
                # 1순위: 폴더 감지 모드 등에서 명시적으로 넘긴 폴더
                custom_images_folder = target_folder
                images_available = True
            elif image_mode_val == "manual":
                # 2순위: 수동 지정 폴더
                manual_path = getattr(self, 'blog_manual_folder_path', None)
                if manual_path and manual_path.value and os.path.exists(manual_path.value):
                    custom_images_folder = manual_path.value
                    images_available = True
            elif image_mode_val == "auto":
                # 3순위: 스마트 매칭
                try:
                    matched = self.get_smart_image_folder(final_title)
                    if matched and os.path.exists(matched):
                        custom_images_folder = matched
                        images_available = True
                except: pass

            auto_img_cb = getattr(self, 'auto_image_checkbox', None)
            auto_image_enabled = (auto_img_cb.value if auto_img_cb else True) and images_available

            # --- 5. 블로그 자동화 인스턴스 초기화 ---
            naver_id = self.settings.get('naver_id', '')
            media_pos = getattr(self, 'blog_media_position_dropdown', None)
            media_ord = getattr(self, 'blog_media_order_dropdown', None)
            
            blog_auto = NaverBlogAutomation(
                auto_mode=auto_image_enabled,
                image_insert_mode=media_pos.value if media_pos else 'random',
                use_stickers=False,
                custom_images_folder=custom_images_folder,
                naver_id=naver_id,
                media_position=media_pos.value if media_pos else 'middle',
                media_order=media_ord.value if media_ord else 'image_first'
            )
            blog_auto.base_dir = self.base_dir
            blog_auto.settings = blog_auto.load_settings()
            blog_auto.driver = driver
            
            if auto_image_enabled:
                from naver_blog_auto_image import NaverBlogImageInserter
                fallback = blog_auto.custom_images_folder if blog_auto.custom_images_folder else blog_auto.default_images_folder
                blog_auto.image_inserter = NaverBlogImageInserter(
                    driver=blog_auto.driver,
                    images_folder=blog_auto.images_folder,
                    insert_mode=blog_auto.image_insert_mode,
                    fallback_folder=fallback
                )
                blog_auto.image_inserter.media_position = blog_auto.media_position
                blog_auto.image_inserter.media_order = blog_auto.media_order

            # --- 6. 태그 병합 (고정 + AI = 최대 30개) ---
            user_tags_str = self.settings.get('blog_tags', '')
            user_tags = [t.strip() for t in user_tags_str.split(',') if t.strip()]
            ai_tags_list = ai_tags if ai_tags else []
            if isinstance(ai_tags_list, str):
                ai_tags_list = [t.strip() for t in ai_tags_list.split(',') if t.strip()]
                
            merged_tags = []
            seen = set()
            for t in (user_tags[:15] + ai_tags_list[:15]):
                if t and t not in seen:
                    seen.add(t)
                    merged_tags.append(t)
            
            # --- 7. 블로그 포스팅 엔진 실행 (제목/본문/이미지/푸터/장소/태그) ---
            auto_final_cb = getattr(self, 'auto_final_publish_checkbox', None)
            blog_auto.skip_final_publish = not auto_final_cb.value if auto_final_cb else False
            
            success = blog_auto.write_post(title=final_title, content=content_str, tags=merged_tags)
            if not success:
                print("❌ 통합 파이프라인: 본문/태그 작성 중 오류 발생")
                return False

            # --- 8. 스케줄 예약 모드일 경우 예약 시간 주입 및 발행 ---
            finisher = NaverBlogPostFinisher(blog_auto.driver, self.settings)
            
            if reservation_time:
                # write_post가 skip_publish 처리했으므로, 여기서 예약 시간 세팅 후 예약발행
                res_ok = finisher.set_reservation_time(reservation_time)
                if res_ok:
                    return finisher.click_final_publish_button(is_reservation=True)
                else:
                    print("❌ 예약 시간 설정 실패로 발행 보류")
                    return False
            else:
                # 일반 모드 - 설정에 따라 이미 발행되었거나 대기 중임
                if not blog_auto.skip_final_publish:
                    return True # write_post에서 이미 처리 완료됨
                else:
                    print("⏸️ '자동 발행'이 꺼져 있어 1차 발행 패널 상태에서 멈춥니다.")
                    return True

        except Exception as e:
            print(f"❌ 통합 파이프라인 치명적 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

"""

# _execute_unified_blog_posting 이 없으면 main 함수 바로 위에 삽입
if "def _execute_unified_blog_posting" not in content:
    content = content.replace("    def main(self, page: ft.Page):", UNIFIED_PIPELINE_CODE + "\\n    def main(self, page: ft.Page):")
    print("✅ 통합 파이프라인 함수 삽입 완료")

with open(APP_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("작업 완료!")
