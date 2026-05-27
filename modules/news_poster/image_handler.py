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
        
        # Resolve default logo path if not specified
        import unicodedata
        if logo_path:
            logo_path = unicodedata.normalize('NFC', logo_path)
            
        if not logo_path or not os.path.exists(logo_path):
            # Check Desktop/체육관엠블럼
            desktop_logo_dir = "/Users/gm2hapkido/Desktop/체육관엠블럼"
            # Normalize target directory
            desktop_logo_dir = unicodedata.normalize('NFC', desktop_logo_dir)
            possible_logos = ["엠블럼.png", "라이온체육관(all).png", "사자만.png"]
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
                    
                    print(f"[Step 3] [ImageHandler] 워터마크 15% 동적 리사이징 (상태: 시도)")
                    
                    # Compute watermark size: Exactly 15% of background width
                    target_w = int(bg_w * 0.15)
                    
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
                    print(f"[Step 3] [ImageHandler] 워터마크 15% 동적 리사이징 및 3% 동적 여백 합성 적용 (상태: 성공)")
                
                # 4. Save processed image as JPEG to matches blog compatibility
                final_im = bg_im.convert("RGB")
                out_filename = f"processed_{idx}_{random.randint(100,999)}.jpg"
                out_path = os.path.join(self.processed_dir, out_filename)
                
                # Safe save with quality 90+
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
                    
        return processed_paths

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
