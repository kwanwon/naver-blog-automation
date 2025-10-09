import os
from datetime import datetime

# 오늘 날짜로 폴더 이름 만들기
today = datetime.now().strftime("%Y-%m-%d")  # 예: "2025-02-23"
base_dir = "/Users/gm2hapkido/Desktop/블로그자동화"  # 본인 사용자 이름으로 수정
folder_path = os.path.join(base_dir, today)

# 폴더 만들기
if not os.path.exists(folder_path):
    os.makedirs(folder_path)
    print("폴더가 만들어졌어요: " + folder_path)

# 글 파일 만들기
content = "이 글은 테스트 포스트입니다."
file_path = os.path.join(folder_path, "post.txt")
with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("파일이 만들어졌어요: " + file_path)