import re

with open("blog_writer_app.py", "r", encoding="utf-8") as f:
    text = f.read()

# Remove from current location
text = text.replace("""        # 구버전 데이터 마이그레이션
        self._migrate_old_user_data()
        
        # 디렉토리 존재 확인 및 생성
        self._ensure_directories()""", "")

# Add after self.user_data_dir = self._get_app_data_dir()
new_code = """        self.user_data_dir = self._get_app_data_dir()
        
        # 구버전 데이터 마이그레이션 (제일 먼저 실행되어야 설정 파일들을 불러올 수 있음)
        self._migrate_old_user_data()
        
        # 디렉토리 존재 확인 및 생성
        self._ensure_directories()"""

text = text.replace("        self.user_data_dir = self._get_app_data_dir()", new_code)

with open("blog_writer_app.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Init order patched!")
