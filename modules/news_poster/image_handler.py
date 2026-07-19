import os
import requests
import random
from PIL import Image, ImageEnhance
import urllib.parse

class ImageHandler:
    def __init__(self, pexels_key=None):
        self.pexels_key = pexels_key
        # Default directories
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.temp_dir = os.path.join(self.base_dir, "modules", "news_poster", "temp_images")
        self.processed_dir = os.path.join(self.base_dir, "modules", "news_poster", "processed_images")

        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)

    def _translate_to_english_fallback(self, keyword):
        """
        Simple translation mapping for gym-related keywords in case of no heavy translator.
        This provides a basic mapping to ensure clean Pexels search queries.
        """
        translation_map = {
            "소아비만": "childhood obesity children",
            "비만": "obesity weight health",
            "어린이 건강": "children fitness kids health",
            "태권도": "taekwondo martial arts",
            "합기도": "hapkido martial arts self defense",
            "체력 단련": "fitness workout children",
            "다이어트": "diet healthy food exercise",
            "자신감": "children confidence self esteem",
            "성장판": "children growth stretching exercise",
            "인성 교육": "children discipline character education",
            "학교 폭력": "self defense confidence children",
            "집중력": "children studying focus coordination",
            "호신술": "self defense self protection self-defense",
            "스트레칭": "stretching exercise flexibility",
            "유아 체육": "toddler gymnastics physical education kids",
        }
        
        # Fallback simple search if not found in dict
        cleaned = keyword.strip()
        for kor, eng in translation_map.items():
            if kor in cleaned:
                return eng
        
        # Simple character replacements or default search terms
        return "children fitness healthy happy"

    def download_pexels_images(self, keyword, count=5):
        """
        Downloads up to `count` images from Pexels based on the given keyword.
        """
        print(f"[Step] [ImageHandler] Starting image retrieval for keyword: '{keyword}' (Pexels key set: {bool(self.pexels_key)})")
        
        if not self.pexels_key:
            print("[Warning] [ImageHandler] Pexels API Key is missing. Falling back to default library images.")
            return self._get_fallback_images(count)
            
        eng_keyword = self._translate_to_english_fallback(keyword)
        # Force Asian / Korean suffix to fetch localized natural images matching the Korean context
        eng_keyword = f"{eng_keyword} korean"
        print(f"[Step] [ImageHandler] Query translated and targeted to: '{eng_keyword}'")
        
        url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(eng_keyword)}&per_page={count * 2}"
        headers = {
            "Authorization": self.pexels_key
        }
        
        downloaded_paths = []
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"[Error] [ImageHandler] Pexels API returned status code {response.status_code}. Response: {response.text}")
                return self._get_fallback_images(count)
                
            data = response.json()
            photos = data.get("photos", [])
            
            if not photos:
                print("[Warning] [ImageHandler] No photos found for this keyword. Trying general fitness fallback.")
                # Fallback search
                fallback_url = f"https://api.pexels.com/v1/search?query=children+sports+fitness&per_page={count}"
                response = requests.get(fallback_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    photos = response.json().get("photos", [])

            # Download actual files
            download_count = 0
            for idx, photo in enumerate(photos):
                if download_count >= count:
                    break
                    
                image_url = photo.get("src", {}).get("large") or photo.get("src", {}).get("medium")
                if not image_url:
                    continue
                    
                try:
                    img_data = requests.get(image_url, timeout=10).content
                    filename = f"pexels_{idx}_{random.randint(1000, 9999)}.jpg"
                    filepath = os.path.join(self.temp_dir, filename)
                    
                    with open(filepath, "wb") as handler:
                        handler.write(img_data)
                        
                    downloaded_paths.append(filepath)
                    download_count += 1
                    print(f"[Step] [ImageHandler] Downloaded: {filename} (Success)")
                except Exception as e:
                    print(f"[Error] [ImageHandler] Failed to download image {image_url}: {e}")
                    
        except Exception as ex:
            print(f"[Error] [ImageHandler] Exception during Pexels API request: {ex}")
            return self._get_fallback_images(count)
            
        if not downloaded_paths:
            return self._get_fallback_images(count)
            
        return downloaded_paths

    def _get_fallback_images(self, count=5):
        """
        Creates basic high quality default background images in case Pexels fails.
        """
        print("[Step] [ImageHandler] Utilizing fallback placeholder system images.")
        fallback_paths = []
        # Generate some simple high-quality gradient color solid images as placeholders
        for idx in range(count):
            img = Image.new("RGB", (800, 600), color=(
                random.randint(220, 255),
                random.randint(235, 255),
                random.randint(220, 255)
            ))
            filename = f"fallback_{idx}_{random.randint(1000, 9999)}.jpg"
            filepath = os.path.join(self.temp_dir, filename)
            img.save(filepath, "JPEG")
            fallback_paths.append(filepath)
        return fallback_paths

    def process_and_watermark(self, image_paths, logo_path=None):
        """
        Applies watermark (logo) at the bottom right corner with transparency,
        performs subtle adjustments (slight rotation, slight contrast enhancement)
        to make each image unique, without mirroring.
        """
        print(f"[Step] [ImageHandler] Starting watermark & processing pipeline (Logo: {logo_path})")
        
        # Ensure image_paths is a list of files
        import shutil
        if isinstance(image_paths, str):
            if os.path.isdir(image_paths):
                print(f"[Step] [ImageHandler] Input is a directory: {image_paths}")
                valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
                files = []
                for f in os.listdir(image_paths):
                    full_path = os.path.join(image_paths, f)
                    if os.path.isfile(full_path):
                        ext = os.path.splitext(f)[1].lower()
                        if ext in valid_exts:
                            files.append(full_path)
                        else:
                            # Copy non-image files (like videos) directly to processed_dir
                            out_path = os.path.join(self.processed_dir, f)
                            try:
                                shutil.copy2(full_path, out_path)
                                print(f"[Step] [ImageHandler] Copied non-image file: {f}")
                            except Exception as e:
                                print(f"[Error] [ImageHandler] Failed to copy {f}: {e}")
                image_paths = files
            elif os.path.isfile(image_paths):
                image_paths = [image_paths]
            else:
                image_paths = []

        # 1. Load user settings to override logo path, get watermark size and GPS
        import json
        import unicodedata
        import subprocess
        import sys
        
        user_settings = {}
        settings_path = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity-ide", "config", "user_settings.txt") # Using standard app data path or checking multiple
        
        # Determine base dir depending on execution context to find user_settings.txt
        try:
            from utils.path_utils import get_app_data_dir
            app_data_dir = get_app_data_dir()
            settings_path = os.path.join(app_data_dir, 'config', 'user_settings.txt')
        except:
            # Fallback path if get_app_data_dir fails
            pass
            
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    user_settings = json.load(f)
            except:
                pass
                
        user_watermark_path = user_settings.get("watermark_path", "")
        if user_watermark_path and os.path.exists(user_watermark_path):
            logo_path = unicodedata.normalize('NFC', user_watermark_path)
        elif logo_path:
            logo_path = unicodedata.normalize('NFC', logo_path)
            
        if not logo_path or not os.path.exists(logo_path):
            # Check Desktop/체육관엠블럼
            desktop_logo_dir = os.path.join(os.path.expanduser("~"), "Desktop", "체육관엠블럼")
            desktop_logo_dir = unicodedata.normalize('NFC', desktop_logo_dir)
            possible_logos = ["엠블럼.png", "라이온체육관(all).png", "사자만.png"]
            possible_logos = [unicodedata.normalize('NFC', p) for p in possible_logos]
            
            resolved_logo = None
            if os.path.exists(desktop_logo_dir):
                for p_logo in possible_logos:
                    check_path = os.path.join(desktop_logo_dir, p_logo)
                    if os.path.exists(check_path):
                        resolved_logo = check_path
                        break
            
            logo_path = resolved_logo
            
        processed_paths = []
        
        logo_im = None
        if logo_path and os.path.exists(logo_path):
            try:
                logo_im = Image.open(logo_path).convert("RGBA")
                print(f"[Step] [ImageHandler] Logo loaded successfully: {os.path.basename(logo_path)}")
            except Exception as e:
                print(f"[Error] [ImageHandler] Failed to load logo {logo_path}: {e}")

        for idx, img_path in enumerate(image_paths):
            try:
                # 1. Open background image
                bg_im = Image.open(img_path).convert("RGBA")
                
                # 2. Make subtle changes (Micro-rotation, slight cropping, contrast boost)
                # Rotate 1 to 3 degrees randomly
                angle = random.choice([-2, -1, 1, 2])
                bg_im = bg_im.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
                
                # Crop slightly to eliminate black background borders from rotation
                w, h = bg_im.size
                border = int(min(w, h) * 0.03) # 3% border crop
                bg_im = bg_im.crop((border, border, w - border, h - border))
                
                # Subtle brightness/contrast enhancement (randomized 1~3%)
                contrast = ImageEnhance.Contrast(bg_im)
                bg_im = contrast.enhance(random.choice([0.98, 1.02, 1.03]))
                
                # 3. Apply Watermark Logo (Bottom Right)
                if logo_im:
                    bg_w, bg_h = bg_im.size
                    logo_w, logo_h = logo_im.size
                    
                    # Compute watermark size dynamically from user_settings (default 10%)
                    try:
                        watermark_percent = float(user_settings.get("watermark_size_percent", "10")) / 100.0
                    except:
                        watermark_percent = 0.10
                        
                    print(f"[Step 3] [ImageHandler] 워터마크 {int(watermark_percent*100)}% 동적 리사이징 (상태: 시도)")
                    
                    target_w = int(bg_w * watermark_percent)
                    
                    # Maintain logo's original aspect ratio
                    aspect_ratio = logo_h / float(logo_w)
                    target_h = int(target_w * aspect_ratio)
                    
                    # Safety check for extremely small backgrounds
                    if target_w < 50:
                        target_w = 50
                        target_h = int(target_w * aspect_ratio)
                    
                    resized_logo = logo_im.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    
                    # Apply transparency (alpha channel override for subtle watermark)
                    alpha = resized_logo.split()[3]
                    alpha = ImageEnhance.Brightness(alpha).enhance(0.65) # 65% opacity
                    resized_logo.putalpha(alpha)
                    
                    # Compute position using 3% dynamic margin based on background size
                    margin_x = int(bg_w * 0.03)
                    margin_y = int(bg_h * 0.03)
                    pos_x = bg_w - target_w - margin_x
                    pos_y = bg_h - target_h - margin_y
                    
                    # Paste logo
                    watermark_layer = Image.new("RGBA", bg_im.size, (0, 0, 0, 0))
                    watermark_layer.paste(resized_logo, (pos_x, pos_y))
                    bg_im = Image.alpha_composite(bg_im, watermark_layer)
                    print(f"[Step 3] [ImageHandler] 워터마크 {int(watermark_percent*100)}% 동적 리사이징 및 3% 동적 여백 합성 적용 (상태: 성공)")
                
                # 4. Save processed image as JPEG to matches blog compatibility
                final_im = bg_im.convert("RGB")
                out_filename = f"processed_{idx}_{random.randint(100,999)}.jpg"
                out_path = os.path.join(self.processed_dir, out_filename)
                
                # 🌟 [GPS 메타데이터(EXIF) 주입 로직 시작] 🌟
                exif_bytes = b""
                gym_gps = user_settings.get("gym_gps_coords", "").strip()
                if gym_gps:
                    try:
                        import piexif
                    except ImportError:
                        print(f"[Warning] [ImageHandler] 'piexif' 패키지가 없습니다. 자동 설치를 시도합니다...")
                        try:
                            import subprocess, sys
                            if getattr(sys, 'frozen', False):
                                print("[Warning] 빌드된 앱에서는 pip install을 실행할 수 없습니다. piexif 기능을 건너뜁니다.")
                                piexif = None
                            else:
                                subprocess.check_call([sys.executable, "-m", "pip", "install", "piexif"])
                                import piexif
                        except Exception as e:
                            print(f"[Warning] [ImageHandler] 'piexif' 자동 설치 실패: {e}")
                            piexif = None
                    
                    if piexif is not None:
                        try:
                            lat_str, lng_str = gym_gps.replace(" ", "").split(",")
                            target_lat = float(lat_str)
                            target_lng = float(lng_str)
                            
                            # 위도/경도를 도/분/초 형태로 변환 (piexif 형식)
                            def to_deg(value, loc):
                                if value < 0:
                                    loc_value = loc[0]
                                    value = -value
                                else:
                                    loc_value = loc[1]
                                d = int(value)
                                m = int((value - d) * 60)
                                s = round((value - d - m/60) * 3600 * 100)
                                return ((d, 1), (m, 1), (s, 100)), loc_value

                            lat_deg, lat_ref = to_deg(target_lat, ["S", "N"])
                            lng_deg, lng_ref = to_deg(target_lng, ["W", "E"])

                            gps_ifd = {
                                piexif.GPSIFD.GPSLatitudeRef: lat_ref,
                                piexif.GPSIFD.GPSLatitude: lat_deg,
                                piexif.GPSIFD.GPSLongitudeRef: lng_ref,
                                piexif.GPSIFD.GPSLongitude: lng_deg,
                                piexif.GPSIFD.GPSAltitudeRef: 0,
                                piexif.GPSIFD.GPSAltitude: (50, 1) # 임의의 고도 50m
                            }
                            
                            exif_dict = {"GPS": gps_ifd}
                            exif_bytes = piexif.dump(exif_dict)
                            print(f"[Step 4] [ImageHandler] 설정된 사용자 GPS 메타데이터({gym_gps}) 생성 성공")
                        except Exception as e:
                            print(f"[Warning] [ImageHandler] GPS EXIF 생성 중 오류 발생: {e}")

                # Safe save with quality 90+ and EXIF data if available
                if exif_bytes:
                    final_im.save(out_path, "JPEG", quality=92, exif=exif_bytes)
                else:
                    final_im.save(out_path, "JPEG", quality=92)
                    
                processed_paths.append(out_path)
                print(f"[Step] [ImageHandler] Processed image saved: {out_filename}")
                
            except Exception as ex:
                print(f"[Error] [ImageHandler] Error processing image {img_path}: {ex}")
                # Fallback to copy original if processing fails
                try:
                    out_filename = f"failed_fallback_{idx}.jpg"
                    out_path = os.path.join(self.processed_dir, out_filename)
                    Image.open(img_path).convert("RGB").save(out_path, "JPEG")
                    processed_paths.append(out_path)
                except:
                    pass
                    
        return self.processed_dir

    def cleanup(self):
        """
        Deletes all files in temp_images and processed_images.
        """
        print("[Step] [ImageHandler] Starting clean-up of temporary image folders.")
        for folder in [self.temp_dir, self.processed_dir]:
            if os.path.exists(folder):
                for filename in os.listdir(folder):
                    file_path = os.path.join(folder, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        print(f"[Error] [ImageHandler] Failed to delete {file_path}: {e}")
        print("[Step] [ImageHandler] Clean-up completed successfully.")
