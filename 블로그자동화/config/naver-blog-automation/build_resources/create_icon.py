from PIL import Image, ImageDraw, ImageFont
import os

# 아이콘 크기 설정
icon_size = (256, 256)

# 새 이미지 생성 (RGBA 모드로 투명 배경)
img = Image.new('RGBA', icon_size, color=(0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 원형 배경 그리기
center = (icon_size[0] // 2, icon_size[1] // 2)
radius = min(icon_size) // 2 - 10
draw.ellipse(
    (
        center[0] - radius,
        center[1] - radius,
        center[0] + radius,
        center[1] + radius
    ),
    fill=(50, 127, 235, 255)  # 파란색 배경
)

# 텍스트 추가
try:
    # 폰트가 없으면 기본 폰트 사용
    font = ImageFont.truetype("Arial", 75)  # 90에서 75로 폰트 크기 감소
except IOError:
    font = ImageFont.load_default()

# "NBA" (네이버 블로그 자동화) 텍스트 추가
text = "NBA"
text_width, text_height = draw.textsize(text, font=font) if hasattr(draw, 'textsize') else font.getbbox(text)[2:]
text_position = (center[0] - text_width // 2, center[1] - text_height // 2 - 10)
draw.text(text_position, text, fill=(255, 255, 255, 255), font=font)

# 저장 경로
ico_path = os.path.join(os.path.dirname(__file__), 'app_icon.png')
ico_path_icns = os.path.join(os.path.dirname(__file__), 'app_icon.icns')

# PNG로 저장
img.save(ico_path, 'PNG')
print(f"아이콘이 생성되었습니다: {ico_path}")

# MacOS에서는 icns 파일도 필요합니다
try:
    # 이 부분은 MacOS에서만 작동합니다
    if os.path.exists('/usr/bin/sips') and os.path.exists('/usr/bin/iconutil'):
        # 임시 iconset 디렉토리 생성
        iconset_dir = os.path.join(os.path.dirname(__file__), 'app_icon.iconset')
        os.makedirs(iconset_dir, exist_ok=True)
        
        # 다양한 크기의 아이콘 생성
        sizes = [16, 32, 64, 128, 256, 512]
        for size in sizes:
            resized = img.resize((size, size), Image.LANCZOS)
            resized.save(os.path.join(iconset_dir, f'icon_{size}x{size}.png'))
            resized.save(os.path.join(iconset_dir, f'icon_{size}x{size}@2x.png'))
        
        # iconutil을 사용하여 iconset을 icns로 변환
        os.system(f'iconutil -c icns {iconset_dir} -o {ico_path_icns}')
        
        # 임시 디렉토리 삭제
        import shutil
        shutil.rmtree(iconset_dir)
        
        print(f"macOS 아이콘이 생성되었습니다: {ico_path_icns}")
except Exception as e:
    print(f"macOS 아이콘 생성 중 오류 발생: {e}")
    print("PNG 아이콘만 사용됩니다.") 