from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size):
    # 새 이미지 생성 (투명 배경)
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # 원 그리기 (테두리 추가)
    margin = size // 10
    # 외부 테두리 (검정)
    draw.ellipse([margin, margin, size-margin, size-margin], 
                 fill=(40, 40, 40, 255))
    
    # 내부 원 (진한 빨강 - 관리자용)
    inner_margin = margin + (size // 20)
    draw.ellipse([inner_margin, inner_margin, size-inner_margin, size-inner_margin], 
                 fill=(180, 20, 20, 255))
    
    # 'M' 문자 그리기 (Manager / Master)
    try:
        font_size = size // 2
        # 맥OS 기본 폰트 사용 시도
        font_path = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
        if not os.path.exists(font_path):
             font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
        
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()
    
    # 텍스트 중앙 정렬
    text = "M"
    # PIL 버전에 따라 textbbox 또는 textsize 사용
    if hasattr(draw, 'textbbox'):
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
    else:
         text_width, text_height = draw.textsize(text, font=font)
    
    x = (size - text_width) // 2
    # 폰트 베이스라인 조정
    y = (size - text_height) // 2 - (text_height * 0.1)
    
    draw.text((x, y), text, fill=(255, 215, 0, 255), font=font) # 골드 색상 텍스트
    
    return image

# 다양한 크기의 아이콘 생성 (iconutil 요구사항)
sizes = [16, 32, 64, 128, 256, 512, 1024]
iconset_path = "admin_icon.iconset"

if not os.path.exists(iconset_path):
    os.makedirs(iconset_path)

for size in sizes:
    icon = create_icon(size)
    icon.save(f"{iconset_path}/icon_{size}x{size}.png")
    if size <= 512:  # 2x 버전도 생성
        icon = create_icon(size * 2)
        icon.save(f"{iconset_path}/icon_{size}x{size}@2x.png")

print("관리자 아이콘 이미지가 생성되었습니다.")
