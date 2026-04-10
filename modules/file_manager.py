"""
파일 관리 모듈 (백업/삭제/이동)
- 성공 시: Backup/{오늘날짜}/{시간대} 폴더로 이동
- 실패 시: Error_Photos 폴더로 이동
- 48시간(2일) 지난 백업 파일 자동 삭제
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple
import threading


class FileManager:
    """
    파일 백업 및 정리 관리자
    """
    
    def __init__(self, base_backup_dir: str = None, error_dir: str = None):
        """
        Args:
            base_backup_dir: 백업 기본 디렉토리 
            error_dir: 에러 파일 디렉토리
        """
        # 🆕 크로스 플랫폼: OS별 기본 경로 설정
        if base_backup_dir:
            self.base_backup_dir = base_backup_dir
        else:
            self.base_backup_dir = self._get_default_backup_dir()
            
        if error_dir:
            self.error_dir = error_dir
        else:
            self.error_dir = self._get_default_error_dir()
            
        self.retention_hours = 12  # 보관 시간 (12시간 후 자동 삭제)
        
        # 디렉토리 생성
        self._ensure_dirs()
    
    def _get_default_backup_dir(self):
        """🆕 OS별 기본 백업 디렉토리"""
        import platform
        system = platform.system()
        
        if system == 'Darwin':  # macOS
            # 🆕 이메일 주소가 포함된 특수 폴더(내 드라이브(...))를 최우선적으로 탐색
            home = os.path.expanduser("~")
            potential_roots = []
            
            try:
                import glob
                # 1. '내 드라이브'로 시작하는 모든 폴더 (동기화 폴더 최우선)
                potential_roots.extend(glob.glob(os.path.join(home, "내 드라이브*")))
                # 2. 'Google Drive'로 시작하는 모든 폴더
                potential_roots.extend(glob.glob(os.path.join(home, "Google Drive*")))
                # 3. 'GoogleDrive'로 시작하는 모든 폴더
                potential_roots.extend(glob.glob(os.path.join(home, "GoogleDrive*")))
            except:
                pass

            # 동기화 폴더(이메일 포함된 것)를 우선순위로 정렬
            potential_roots.sort(key=lambda x: ("@" in x), reverse=True)
            
            for root in potential_roots:
                if os.path.isdir(root):
                    return os.path.join(root, "Backup")
            
            # 검색 실패 시 기본값 fallback
            return os.path.expanduser("~/Desktop/Backup")
        elif system == 'Windows':
            # Windows: Google Drive 스트림 또는 Desktop
            possible_paths = [
                os.path.expanduser("~/Google Drive/Backup"),
                os.path.expanduser("~/GoogleDrive/Backup"),
                os.path.join(os.environ.get('USERPROFILE', ''), 'Google Drive', 'Backup'),
                os.path.expanduser("~/Desktop/Backup"),
            ]
            for path in possible_paths:
                parent = os.path.dirname(path)
                if os.path.exists(parent):
                    return path
            return os.path.expanduser("~/Desktop/Backup")
        else:  # Linux
            return os.path.expanduser("~/Backup")
    
    def _get_default_error_dir(self):
        """🆕 OS별 기본 에러 디렉토리"""
        import platform
        system = platform.system()
        
        if system == 'Darwin':  # macOS
            # 🆕 이메일 주소가 포함된 특수 폴더를 최우선적으로 탐색
            home = os.path.expanduser("~")
            potential_roots = []
            
            try:
                import glob
                potential_roots.extend(glob.glob(os.path.join(home, "내 드라이브*")))
                potential_roots.extend(glob.glob(os.path.join(home, "Google Drive*")))
                potential_roots.extend(glob.glob(os.path.join(home, "GoogleDrive*")))
            except:
                pass

            potential_roots.sort(key=lambda x: ("@" in x), reverse=True)
            
            for root in potential_roots:
                if os.path.isdir(root):
                    return os.path.join(root, "Error_Photos")
            
            return os.path.expanduser("~/Desktop/Error_Photos")
        elif system == 'Windows':
            possible_paths = [
                os.path.expanduser("~/Google Drive/Error_Photos"),
                os.path.expanduser("~/GoogleDrive/Error_Photos"),
                os.path.join(os.environ.get('USERPROFILE', ''), 'Google Drive', 'Error_Photos'),
                os.path.expanduser("~/Desktop/Error_Photos"),
            ]
            for path in possible_paths:
                parent = os.path.dirname(path)
                if os.path.exists(parent):
                    return path
            return os.path.expanduser("~/Desktop/Error_Photos")
        else:  # Linux
            return os.path.expanduser("~/Error_Photos")
    
    def _ensure_dirs(self):
        """필요한 디렉토리 생성"""
        for dir_path in [self.base_backup_dir, self.error_dir]:
            try:
                os.makedirs(dir_path, exist_ok=True)
            except Exception as e:
                print(f"⚠️ 디렉토리 생성 실패: {dir_path} - {e}")
    
    def set_backup_dir(self, path: str):
        """백업 디렉토리 설정"""
        self.base_backup_dir = os.path.normpath(path)
        self._ensure_dirs()
    
    def set_error_dir(self, path: str):
        """에러 디렉토리 설정"""
        self.error_dir = os.path.normpath(path)
        self._ensure_dirs()
    
    def set_retention_hours(self, hours: int):
        """보관 시간 설정 (시간 단위)"""
        self.retention_hours = hours
    
    def move_to_backup(self, files: List[str], folder_name: str) -> Tuple[int, int]:
        """
        파일들을 백업 폴더로 이동
        
        Args:
            files: 이동할 파일 경로 리스트
            folder_name: 시간대/폴더 이름 (예: "3시부")
        
        Returns:
            (성공 수, 실패 수) 튜플
        """
        today = datetime.now().strftime("%Y-%m-%d")
        backup_dir = os.path.join(self.base_backup_dir, today, folder_name)
        
        try:
            os.makedirs(backup_dir, exist_ok=True)
        except Exception as e:
            print(f"❌ 백업 폴더 생성 실패: {backup_dir} - {e}")
            return (0, len(files))
        
        success_count = 0
        fail_count = 0
        
        for file_path in files:
            try:
                if not os.path.exists(file_path):
                    print(f"⚠️ 파일 없음: {file_path}")
                    fail_count += 1
                    continue
                
                filename = os.path.basename(file_path)
                dest_path = os.path.join(backup_dir, filename)
                
                # 동일 파일명 존재 시 타임스탬프 추가
                if os.path.exists(dest_path):
                    name, ext = os.path.splitext(filename)
                    timestamp = datetime.now().strftime("%H%M%S")
                    dest_path = os.path.join(backup_dir, f"{name}_{timestamp}{ext}")
                
                shutil.move(file_path, dest_path)
                success_count += 1
                print(f"📁 백업: {filename} → {folder_name}/")
                
            except Exception as e:
                print(f"❌ 파일 이동 실패: {file_path} - {e}")
                fail_count += 1
        
        print(f"✅ 백업 완료: {success_count}개 성공, {fail_count}개 실패")
        return (success_count, fail_count)
    
    def move_to_error(self, files: List[str], reason: str = "") -> int:
        """
        파일들을 에러 폴더로 이동
        
        Args:
            files: 이동할 파일 경로 리스트
            reason: 에러 사유 (폴더명에 포함)
        
        Returns:
            성공적으로 이동된 파일 수
        """
        today = datetime.now().strftime("%Y-%m-%d")
        error_subdir = os.path.join(self.error_dir, today)
        if reason:
            error_subdir = os.path.join(error_subdir, reason.replace("/", "_").replace("\\", "_"))
        
        try:
            os.makedirs(error_subdir, exist_ok=True)
        except Exception as e:
            print(f"❌ 에러 폴더 생성 실패: {error_subdir} - {e}")
            return 0
        
        moved_count = 0
        
        for file_path in files:
            try:
                if not os.path.exists(file_path):
                    continue
                
                filename = os.path.basename(file_path)
                dest_path = os.path.join(error_subdir, filename)
                
                if os.path.exists(dest_path):
                    name, ext = os.path.splitext(filename)
                    timestamp = datetime.now().strftime("%H%M%S")
                    dest_path = os.path.join(error_subdir, f"{name}_{timestamp}{ext}")
                
                shutil.move(file_path, dest_path)
                moved_count += 1
                print(f"⚠️ 에러 폴더로 이동: {filename}")
                
            except Exception as e:
                print(f"❌ 파일 이동 실패: {file_path} - {e}")
        
        return moved_count
    
    def cleanup_old_backups(self) -> Tuple[int, int]:
        """
        보관 기간이 지난 백업 파일/폴더 삭제
        
        Returns:
            (삭제된 폴더 수, 삭제된 파일 수) 튜플
        """
        if not os.path.exists(self.base_backup_dir):
            return (0, 0)
        
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        deleted_folders = 0
        deleted_files = 0
        
        print(f"🧹 {self.retention_hours}시간 이상 된 백업 정리 중...")
        print(f"   기준 시간: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            for date_folder in os.listdir(self.base_backup_dir):
                date_path = os.path.join(self.base_backup_dir, date_folder)
                
                if not os.path.isdir(date_path):
                    continue
                
                # 날짜 폴더 형식 확인 (YYYY-MM-DD)
                try:
                    folder_date = datetime.strptime(date_folder, "%Y-%m-%d")
                except ValueError:
                    continue
                
                # 폴더 생성 시간 또는 날짜 기준으로 판단
                folder_time = datetime.fromtimestamp(os.path.getmtime(date_path))
                
                # retention_hours 이상 지났으면 삭제
                if folder_time < cutoff_time:
                    try:
                        # 폴더 내 파일 수 카운트
                        file_count = sum(len(files) for _, _, files in os.walk(date_path))
                        
                        shutil.rmtree(date_path)
                        deleted_folders += 1
                        deleted_files += file_count
                        print(f"🗑️ 삭제됨: {date_folder}/ ({file_count}개 파일)")
                        
                    except Exception as e:
                        print(f"❌ 폴더 삭제 실패: {date_path} - {e}")
        
        except Exception as e:
            print(f"❌ 백업 정리 중 오류: {e}")
        
        if deleted_folders > 0:
            print(f"✅ 정리 완료: {deleted_folders}개 폴더, {deleted_files}개 파일 삭제")
        else:
            print(f"ℹ️ 삭제할 오래된 백업이 없습니다.")
        
        return (deleted_folders, deleted_files)
    
    def cleanup_old_errors(self, retention_days: int = 7) -> int:
        """
        오래된 에러 폴더 정리 (기본 7일)
        
        Args:
            retention_days: 보관 일수
        
        Returns:
            삭제된 폴더 수
        """
        if not os.path.exists(self.error_dir):
            return 0
        
        cutoff_time = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0
        
        try:
            for folder in os.listdir(self.error_dir):
                folder_path = os.path.join(self.error_dir, folder)
                
                if not os.path.isdir(folder_path):
                    continue
                
                folder_time = datetime.fromtimestamp(os.path.getmtime(folder_path))
                
                if folder_time < cutoff_time:
                    try:
                        shutil.rmtree(folder_path)
                        deleted_count += 1
                        print(f"🗑️ 에러 폴더 삭제: {folder}")
                    except Exception as e:
                        print(f"❌ 에러 폴더 삭제 실패: {folder} - {e}")
        
        except Exception as e:
            print(f"❌ 에러 폴더 정리 중 오류: {e}")
        
        return deleted_count
    
    def start_auto_cleanup(self, interval_hours: int = 6):
        """
        자동 정리 스케줄러 시작 (백그라운드 스레드)
        
        Args:
            interval_hours: 정리 주기 (시간)
        """
        def cleanup_loop():
            while True:
                try:
                    self.cleanup_old_backups()
                    self.cleanup_old_errors()
                except Exception as e:
                    print(f"❌ 자동 정리 오류: {e}")
                
                # 다음 정리까지 대기
                import time
                time.sleep(interval_hours * 3600)
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
        print(f"🔄 자동 정리 스케줄러 시작됨 (매 {interval_hours}시간)")
    
    def get_backup_stats(self) -> dict:
        """백업 폴더 통계 반환"""
        stats = {
            "total_folders": 0,
            "total_files": 0,
            "total_size_mb": 0,
            "oldest_backup": None,
            "newest_backup": None
        }
        
        if not os.path.exists(self.base_backup_dir):
            return stats
        
        try:
            total_size = 0
            dates = []
            
            for date_folder in os.listdir(self.base_backup_dir):
                date_path = os.path.join(self.base_backup_dir, date_folder)
                if os.path.isdir(date_path):
                    stats["total_folders"] += 1
                    dates.append(date_folder)
                    
                    for _, _, files in os.walk(date_path):
                        stats["total_files"] += len(files)
                        for f in files:
                            try:
                                total_size += os.path.getsize(
                                    os.path.join(date_path, f)
                                )
                            except:
                                pass
            
            stats["total_size_mb"] = round(total_size / (1024 * 1024), 2)
            
            if dates:
                dates.sort()
                stats["oldest_backup"] = dates[0]
                stats["newest_backup"] = dates[-1]
        
        except Exception as e:
            print(f"⚠️ 통계 수집 오류: {e}")
        
        return stats


# 테스트 코드
if __name__ == "__main__":
    print("파일 관리자 테스트")
    
    # 임시 디렉토리로 테스트
    fm = FileManager(
        base_backup_dir="/tmp/test_backup",
        error_dir="/tmp/test_error"
    )
    
    # 통계 출력
    stats = fm.get_backup_stats()
    print(f"\n📊 백업 통계: {stats}")
    
    # 클린업 테스트
    fm.cleanup_old_backups()
