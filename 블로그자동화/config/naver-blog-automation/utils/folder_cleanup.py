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
        """지정된 일수보다 오래된 날짜 폴더들과 크롬 프로필 폴더들을 삭제합니다."""
        today = datetime.now()
        cutoff_date = today - timedelta(days=self.retention_days)

        try:
            # 베이스 디렉토리의 모든 항목을 확인
            for item in os.listdir(self.base_path):
                item_path = os.path.join(self.base_path, item)
                
                # 디렉토리인 경우만 처리
                if os.path.isdir(item_path):
                    should_delete = False
                    
                                        # 날짜 형식(YYYY-MM-DD) 폴더 확인
                    if self._is_date_folder(item):
                        folder_date = self._parse_folder_date(item)
                        if folder_date and folder_date < cutoff_date:
                            should_delete = True
                    
                    # 크롬 프로필 폴더 확인 (manual_chrome_profile_로 시작)
                    elif item.startswith('manual_chrome_profile_'):
                        folder_age = self._get_folder_age(item_path)
                        if folder_age and folder_age > self.retention_days:
                            should_delete = True
                    
                    # 삭제 실행
                    if should_delete:
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

    def _get_folder_age(self, folder_path):
        """폴더의 생성 시간을 기준으로 나이(일수)를 계산합니다."""
        try:
            # 폴더의 생성 시간 또는 수정 시간 중 더 이른 시간 사용
            stat = os.stat(folder_path)
            creation_time = min(stat.st_ctime, stat.st_mtime)
            folder_date = datetime.fromtimestamp(creation_time)
            
            # 현재 시간과의 차이를 일수로 계산 (시간 단위까지 정확하게)
            age_timedelta = datetime.now() - folder_date
            age_days = age_timedelta.total_seconds() / (24 * 60 * 60)  # 초를 일수로 변환
            return age_days
        except Exception as e:
            print(f"폴더 나이 계산 중 오류: {folder_path} - {str(e)}")
            return None

if __name__ == "__main__":
    cleanup = FolderCleanup()
    cleanup.cleanup_old_folders() 