from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size):
    # 새 이미지 생성 (투명 배경)
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # 원 그리기
    margin = size // 10
    draw.ellipse([margin, margin, size-margin, size-margin], 
                 fill=(65, 105, 225, 255))  # 로얄 블루
    
    # 'S' 문자 그리기
    try:
        font_size = size // 2
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # 텍스트 중앙 정렬
    text = "S"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    
    return image

# 다양한 크기의 아이콘 생성
sizes = [16, 32, 64, 128, 256, 512, 1024]
iconset_path = "icon.iconset"

for size in sizes:
    icon = create_icon(size)
    icon.save(f"{iconset_path}/icon_{size}x{size}.png")
    if size <= 512:  # 2x 버전도 생성
        icon = create_icon(size * 2)
        icon.save(f"{iconset_path}/icon_{size}x{size}@2x.png")

print("아이콘 이미지가 생성되었습니다.") 