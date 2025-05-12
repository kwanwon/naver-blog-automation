import os
import shutil
import sys
from datetime import datetime, timedelta

class FolderCleanup:
    def __init__(self, base_path=None, retention_days=2):
        self.retention_days = retention_days
        self.base_path = base_path or self._get_base_path()

    def _get_base_path(self):
        """실행 환경에 따른 기본 경로를 반환합니다."""
        if getattr(sys, 'frozen', False):
            # PyInstaller로 빌드된 경우
            return os.path.dirname(sys.executable)
        else:
            # 일반 Python 스크립트로 실행된 경우
            return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def cleanup_old_folders(self):
        """지정된 일수보다 오래된 날짜 폴더들을 삭제합니다."""
        today = datetime.now()
        cutoff_date = today - timedelta(days=self.retention_days)

        try:
            # 베이스 디렉토리의 모든 항목을 확인
            for item in os.listdir(self.base_path):
                item_path = os.path.join(self.base_path, item)
                
                # 디렉토리이고 날짜 형식(YYYY-MM-DD)인 경우만 처리
                if os.path.isdir(item_path) and self._is_date_folder(item):
                    folder_date = self._parse_folder_date(item)
                    
                    # 설정된 기간보다 오래된 폴더 삭제
                    if folder_date and folder_date < cutoff_date:
                        print(f"삭제중: {item_path}")
                        shutil.rmtree(item_path)
                        print(f"삭제완료: {item_path}")

        except Exception as e:
            print(f"폴더 정리 중 오류 발생: {str(e)}")

    def _is_date_folder(self, folder_name):
        """폴더 이름이 날짜 형식(YYYY-MM-DD)인지 확인"""
        try:
            datetime.strptime(folder_name, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _parse_folder_date(self, folder_name):
        """폴더 이름에서 날짜를 파싱"""
        try:
            return datetime.strptime(folder_name, "%Y-%m-%d")
        except ValueError:
            return None

if __name__ == "__main__":
    cleanup = FolderCleanup()
    cleanup.cleanup_old_folders() 