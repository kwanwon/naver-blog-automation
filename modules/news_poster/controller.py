import os
import json
import traceback
from datetime import datetime
from .image_handler import ImageHandler
from .ai_generator import AIGenerator
from .selenium_poster import SeleniumPoster
from utils.path_utils import get_gpt_settings_path

class NewsPosterController:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.gpt_settings_path = get_gpt_settings_path()

    def run_news_posting_pipeline(self, news_title, news_desc, weather_data=None, selected_logo_path=None, status_callback=None, driver=None, naver_id=None, settings=None):
        """
        Executes the complete pipeline of News Auto-Posting:
        1. Parse settings & Pexels Key.
        2. Download 5 high-quality Pexels images.
        3. Combine with transparent gym logo watermark & micro-filters.
        4. Draft highly engaging blog column text with Gemini.
        5. Upload text + images to SmartEditor and publish instantly.
        6. Clean up temporary files.
        """
        def update_status(msg):
            if status_callback:
                status_callback(msg)
            print(f"[NewsPosterController] {msg}")

        update_status("🚀 뉴스 자동 포스팅 파이프라인을 기동합니다...")
        
        # 1. Load Settings
        gpt_settings = {}
        if os.path.exists(self.gpt_settings_path):
            try:
                with open(self.gpt_settings_path, 'r', encoding='utf-8') as f:
                    gpt_settings = json.load(f)
            except Exception as e:
                update_status(f"⚠️ 설정 로드 실패: {e}")

        pexels_key = gpt_settings.get('pexels_key', '').strip()
        gemini_key = gpt_settings.get('gemini_api_key', '').strip()
        tags = gpt_settings.get('tags', ["뉴스", "건강상식", "체육관"])

        if not gemini_key:
            update_status("❌ 에러: Gemini API 키가 설정되어 있지 않습니다. AI 설정 탭을 확인하세요.")
            return False

        # Prepare workspace paths
        image_handler = ImageHandler(pexels_key=pexels_key)
        ai_generator = AIGenerator()
        selenium_poster = SeleniumPoster()

        # Check logo path
        import unicodedata
        logo_path = selected_logo_path
        if logo_path:
            logo_path = unicodedata.normalize('NFC', logo_path)
            
        if logo_path and not os.path.exists(logo_path):
            print(f"[Step] [Controller] Provided selected_logo_path does not exist: {logo_path}, trying fallback")
            logo_path = None
                
        if not logo_path:
            # Try finding any png logo in emblem folder
            desktop_logo_dir = "/Users/gm2hapkido/Desktop/체육관엠블럼"
            desktop_logo_dir = unicodedata.normalize('NFC', desktop_logo_dir)
            if os.path.exists(desktop_logo_dir):
                files = [unicodedata.normalize('NFC', f) for f in os.listdir(desktop_logo_dir) if f.lower().endswith('.png')]
                if files:
                    logo_path = os.path.join(desktop_logo_dir, files[0])

        try:
            # Step 1: Clean up previous runs
            image_handler.cleanup()

            # Step 2: Extract key query & Download Images
            update_status("📷 Pexels API를 활용하여 연관 무료 이미지 5장 수집 중...")
            # We can extract simple keyword from news title to search better
            # Filter stop words or just query Pexels
            query_keyword = news_title.split(' ')[0] # Default to first word of news title
            if len(query_keyword) < 2 and len(news_title.split(' ')) > 1:
                query_keyword = news_title.split(' ')[1]
                
            # Let's clean the keyword to look natural
            query_keyword = ''.join(c for c in query_keyword if c.isalnum() or c.isspace()).strip()
            
            raw_images = image_handler.download_pexels_images(query_keyword, count=5)
            update_status(f"✓ 무료 이미지 {len(raw_images)}장 다운로드 완료.")

            # Step 3: Apply Watermark & Micro-filters
            update_status("🎨 이미지 5장에 체육관 로고 투명 합성 및 미세 필터 가공 중...")
            processed_images = image_handler.process_and_watermark(raw_images, logo_path=logo_path)
            update_status(f"✓ 로고 워터마크 합성 및 유니크 가공 완료 ({len(processed_images)}장)")

            # Step 4: AI Column Drafting with Gemini
            update_status("✍️ Gemini API를 활용하여 뉴스 기반 고품질 포스팅 본문 생성 중...")
            post_title, post_body, image_keyword = ai_generator.generate_news_post(news_title, news_desc, weather_data=weather_data)
            update_status("✓ 블로그 서론-본문-결론 및 슬로건 완성.")

            # Step 4.5: Re-trigger image download based on the AI-recommended keyword for precise contextual matching
            if image_keyword and pexels_key:
                try:
                    update_status(f"📷 AI 추천 이미지 키워드 '{image_keyword}' 기반 정밀 수집 재가동...")
                    image_handler.cleanup()  # Clean general fallback images
                    raw_images = image_handler.download_pexels_images(image_keyword, count=5)
                    update_status(f"✓ AI 추천 이미지 {len(raw_images)}장 맞춤 수집 완료.")
                    processed_images = image_handler.process_and_watermark(raw_images, logo_path=logo_path)
                    update_status("🎨 이미지에 체육관 로고 투명 합성 및 미세 필터 맞춤 가공 완료.")
                except Exception as img_re_err:
                    update_status(f"⚠️ AI 추천 이미지 수집 중 경미한 장애: {img_re_err} (기본 수집 이미지 사용)")

            # Step 5: Selenium Upload & Instantly Publish
            update_status("📝 크롬 세션을 재사용하여 네이버 블로그에 포스팅 및 즉시 발행 중 (수분 소요)...")
            publish_success = selenium_poster.post_to_naver(
                title=post_title,
                content=post_body,
                image_folder=image_handler.processed_dir,
                tags=tags,
                driver=driver,
                naver_id=naver_id,
                status_callback=status_callback,
                settings=settings
            )

            if publish_success:
                update_status("🎉 네이버 블로그에 완전 자동 뉴스 포스팅 즉시 발행 성공!")
                return True
            else:
                update_status("❌ 네이버 블로그 포스팅 실패. 셀레니움 로그를 확인하세요.")
                return False

        except Exception as ex:
            update_status(f"❌ 파이프라인 구동 중 예기치 못한 에러 발생: {ex}")
            traceback.print_exc()
            return False
            
        finally:
            # Step 6: Safe Clean Up of Temporary Images
            update_status("🧹 사용된 임시 이미지 파일들을 안전하게 자동 비우기 처리합니다.")
            try:
                image_handler.cleanup()
            except:
                pass
            update_status("✓ 정리 완료.")
