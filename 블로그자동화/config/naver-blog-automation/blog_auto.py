import os
from datetime import datetime

# 오늘 날짜로 폴더 이름 만들기
today = datetime.now().strftime("%Y-%m-%d")  # 예: "2025-02-23"
# 🆕 크로스 플랫폼: 스크립트 위치 기준 상대 경로 사용
base_dir = os.path.dirname(os.path.abspath(__file__))
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