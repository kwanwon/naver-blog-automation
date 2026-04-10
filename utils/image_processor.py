
import os
import random
import uuid
import traceback
from datetime import datetime
from PIL import Image, ImageEnhance, ImageOps

def get_random_filename(extension=".jpg"):
    """
    Generate a random filename with timestamp.
    Example: 20231027_123456_a1b2c3d4.jpg
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_str = str(uuid.uuid4())[:8]
    return f"{timestamp}_{random_str}{extension}"

def process_image(image_path, output_dir):
    """
    Process an image for blog upload:
    1. Remove Exif data (by creating a new image).
    2. Randomly mirror OR rotate (1-2 degrees).
    3. Adjust brightness (±5%).
    4. Save with a random filename in output_dir.
    
    Args:
        image_path (str): Path to the source image.
        output_dir (str): Directory to save the processed image.
        
    Returns:
        str: Path to the processed image, or None if failed.
    """
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        print(f"🖼️ 이미지 처리 시작: {os.path.basename(image_path)}")
        
        # 1. Load Image
        try:
            original_img = Image.open(image_path)
        except Exception as e:
            print(f"❌ 이미지 열기 실패: {e}")
            return None

        # Handle RGBA (convert to RGB for JPEG saving)
        if original_img.mode in ('RGBA', 'P'):
            original_img = original_img.convert('RGB')
            
        # 2. Remove Exif (implicitly done when creating new image/saving, 
        # but we act on pixel data to be sure)
        # Deep copy the image data to a new object to strip metadata
        img = Image.new(original_img.mode, original_img.size)
        img.putdata(list(original_img.getdata()))
        
        # 3. Random Transformation (Only Rotation, Mirror removed per user request)
        # Rotate weak (1~2 degrees, random direction)
        angle = random.uniform(1.0, 2.0)
        if random.choice([True, False]):
            angle = -angle
        
        # fast rotation with expand=False (might crop corners slightly, but safer for upload size)
        img = img.rotate(angle, resample=Image.BICUBIC, expand=False)
        print(f"   👉 회전 적용됨 ({angle:.1f}도)")

        # 4. Brightness Adjustment (±5%)
        enhancer = ImageEnhance.Brightness(img)
        factor = 1.0 + random.uniform(-0.05, 0.05)
        img = enhancer.enhance(factor)
        print(f"   👉 밝기 조정됨 ({factor:.2f}배)")
        
        # 5. Save
        ext = os.path.splitext(image_path)[1].lower()
        if not ext or ext not in ['.jpg', '.jpeg', '.png', '.webp']:
            ext = '.jpg'
            
        new_filename = get_random_filename(ext)
        output_path = os.path.join(output_dir, new_filename)
        
        # Save without metadata (optimize=True usually strips exif too)
        img.save(output_path, quality=95, optimize=True)
        print(f"✅ 이미지 처리 완료: {os.path.basename(output_path)}")
        
        return output_path
        
    except Exception as e:
        print(f"❌ 이미지 처리 중 치명적 오류: {str(e)}")
        traceback.print_exc()
        return None
