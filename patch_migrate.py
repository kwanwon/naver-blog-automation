import re

with open("blog_writer_app.py", "r", encoding="utf-8") as f:
    text = f.read()

migration_method = """    def _migrate_old_user_data(self):
        \"\"\"설치 폴더에 남아있는 구버전 사용자 데이터를 새 문서 폴더로 안전하게 자동 이전\"\"\"
        import shutil
        import os
        folders_to_move = [
            '블로그사진폴더', '밴드사진폴더', '카페사진폴더',
            '수동이미지', '블로그_카페_수동이미지', '밴드_수동이미지',
            '수동업로드', 'default_images', 'config', 'drafts', 'data', 'settings', 'logs'
        ]
        for folder in folders_to_move:
            old_path = os.path.join(self.base_dir, folder)
            new_path = os.path.join(self.user_data_dir, folder)
            
            if os.path.exists(old_path) and os.path.isdir(old_path):
                try:
                    if not os.path.exists(new_path):
                        print(f"📦 [마이그레이션] 데이터 이전 중: {folder}")
                        shutil.copytree(old_path, new_path)
                    else:
                        # 이미 새 폴더가 존재한다면 안의 내용물만 병합 (덮어쓰지 않음)
                        for item in os.listdir(old_path):
                            s = os.path.join(old_path, item)
                            d = os.path.join(new_path, item)
                            if not os.path.exists(d):
                                if os.path.isdir(s):
                                    shutil.copytree(s, d)
                                else:
                                    shutil.copy2(s, d)
                except Exception as e:
                    print(f"❌ [마이그레이션 실패] {folder}: {e}")

        # env 파일 이동
        old_env = os.path.join(self.base_dir, '.env')
        new_env = os.path.join(self.user_data_dir, '.env')
        if os.path.exists(old_env) and not os.path.exists(new_env):
            import shutil
            try:
                shutil.copy2(old_env, new_env)
            except Exception:
                pass

    def _ensure_directories(self):"""

text = text.replace("    def _ensure_directories(self):", migration_method)

init_patch = """        # 자동 업데이트 확인 (백그라운드에서)
        self.check_for_updates()
        
        # 구버전 데이터 마이그레이션
        self._migrate_old_user_data()
        
        # 디렉토리 존재 확인 및 생성
        self._ensure_directories()"""

text = text.replace("""        # 자동 업데이트 확인 (백그라운드에서)
        self.check_for_updates()
        
        # 디렉토리 존재 확인 및 생성
        self._ensure_directories()""", init_patch)

with open("blog_writer_app.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Migration logic added!")
