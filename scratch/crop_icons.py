
from PIL import Image
import os

# 원본 이미지 경로
img_path = "/Users/gm2hapkido/.gemini/antigravity/brain/58887cdc-7cf0-4ca6-bcef-22478cdcf526/training_icons_set_1778648923716.png"
output_dir = "resources/icons"

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

img = Image.open(img_path)
w, h = img.size # 1024, 1024

# 2행 3열 그리드 (이미지 상의 텍스트 제외하고 아이콘 부분만 자르기 위해 오프셋 조정)
# 각 칸의 크기: 341 x 512
icons = [
    ("unicycle.png", (50, 50, 290, 400)),          # 1행 1열
    ("childrens_day.png", (390, 50, 630, 400)),    # 1행 2열
    ("seollal.png", (730, 50, 970, 400)),          # 1행 3열
    ("chuseok.png", (50, 550, 290, 900)),          # 2행 1열
    ("xmas.png", (390, 550, 630, 900)),             # 2행 2열
    ("election.png", (730, 550, 970, 900))         # 2행 3열
]

for name, (left, top, right, bottom) in icons:
    cropped = img.crop((left, top, right, bottom))
    # 투명 배경화 (흰색 제거)
    cropped = cropped.convert("RGBA")
    data = cropped.getdata()
    new_data = []
    for item in data:
        # 흰색에 가까우면 투명하게 (약간의 오차 허용)
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
    cropped.putdata(new_data)
    cropped.save(os.path.join(output_dir, name))
    print(f"Saved {name}")
