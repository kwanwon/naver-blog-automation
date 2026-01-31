"""
구글 드라이브 폴더 감지 모듈 (Watchdog + Debounce)
- 여러 폴더 동시 모니터링
- 60초 디바운스 로직
- 별도 스레드에서 동작
"""

import os
import time
import threading
import unicodedata  # 한글 Unicode 정규화용
from datetime import datetime
from typing import Dict, List, Callable, Optional
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("⚠️ watchdog 라이브러리가 설치되지 않았습니다. pip install watchdog")
    # 더미 클래스 정의 (import 실패 시에도 코드가 동작하도록)
    class FileSystemEventHandler:
        pass
    class Observer:
        pass


class DebouncedFolderHandler(FileSystemEventHandler):
    """디바운스 로직이 적용된 폴더 핸들러"""
    
    def __init__(self, folder_path: str, folder_name: str, callback: Callable, debounce_seconds: int = 60):
        super().__init__()
        self.folder_path = folder_path
        self.folder_name = folder_name  # 예: "3시부", "5시부"
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        
        self.last_event_time: Optional[float] = None
        self.pending_files: List[str] = []
        self.debounce_timer: Optional[threading.Timer] = None
        self.lock = threading.Lock()
        
        # 유효한 이미지/영상 확장자
        self.valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif',
                                  '.mp4', '.mov', '.avi', '.mkv', '.m4v'}
    
    def _is_valid_media(self, filepath: str) -> bool:
        """유효한 미디어 파일인지 확인"""
        ext = Path(filepath).suffix.lower()
        return ext in self.valid_extensions
    
    def on_created(self, event):
        """파일 생성 이벤트 처리"""
        print(f"🔔 [DEBUG] on_created: is_dir={event.is_directory}, path={event.src_path}")
        if event.is_directory:
            return
        
        if self._is_valid_media(event.src_path):
            self._handle_file_event(event.src_path)
        else:
            print(f"   ⏭️ 미디어 파일 아님: {event.src_path}")
    
    def on_modified(self, event):
        """파일 수정 이벤트 처리 (업로드 완료 시)"""
        # 수정 이벤트는 너무 많이 발생할 수 있으므로 미디어 파일만 로깅
        if event.is_directory:
            return
        
        if self._is_valid_media(event.src_path):
            print(f"🔔 [DEBUG] on_modified: {event.src_path}")
            self._handle_file_event(event.src_path)
    
    def _handle_file_event(self, filepath: str):
        """파일 이벤트 처리 (디바운스 적용)"""
        with self.lock:
            # 파일이 이미 목록에 없으면 추가
            if filepath not in self.pending_files:
                self.pending_files.append(filepath)
                print(f"📁 [{self.folder_name}] 파일 감지: {os.path.basename(filepath)} (대기: {len(self.pending_files)}개)")
            
            # 마지막 이벤트 시간 업데이트
            self.last_event_time = time.time()
            
            # 기존 타이머 취소
            if self.debounce_timer:
                self.debounce_timer.cancel()
            
            # 새 타이머 설정 (60초 후 실행)
            self.debounce_timer = threading.Timer(
                self.debounce_seconds,
                self._trigger_callback
            )
            self.debounce_timer.start()
            print(f"⏱️ [{self.folder_name}] {self.debounce_seconds}초 후 처리 예정...")
    
    def _trigger_callback(self):
        """디바운스 시간 경과 후 콜백 실행"""
        with self.lock:
            if not self.pending_files:
                return
            
            files_to_process = self.pending_files.copy()
            self.pending_files.clear()
            self.debounce_timer = None
        
        print(f"🚀 [{self.folder_name}] {len(files_to_process)}개 파일 처리 시작!")
        
        try:
            self.callback(
                folder_path=self.folder_path,
                folder_name=self.folder_name,
                files=files_to_process
            )
        except Exception as e:
            print(f"❌ [{self.folder_name}] 콜백 실행 중 오류: {e}")


class DriveWatcher:
    """
    구글 드라이브 폴더 감시자
    - 여러 폴더 동시 모니터링
    - watchdog + 폴링 하이브리드 방식
    - 별도 스레드에서 동작
    """
    
    def __init__(self, debounce_seconds: int = 60, polling_interval: int = 30):
        self.debounce_seconds = debounce_seconds
        self.polling_interval = polling_interval  # 폴링 간격 (초)
        self.observers: List[Observer] = []
        self.handlers: Dict[str, DebouncedFolderHandler] = {}
        self.is_running = False
        self.callback: Optional[Callable] = None
        
        # 폴링용 변수
        self.polling_thread: Optional[threading.Thread] = None
        self.known_files: Dict[str, set] = {}  # 폴더별 알려진 파일 목록
        
        if not WATCHDOG_AVAILABLE:
            print("❌ DriveWatcher: watchdog 라이브러리가 필요합니다.")
    
    def set_callback(self, callback: Callable):
        """
        파일 감지 시 호출될 콜백 설정
        
        콜백 시그니처:
            callback(folder_path: str, folder_name: str, files: List[str])
        """
        self.callback = callback
    
    def add_folder(self, folder_path: str, folder_name: str) -> bool:
        """
        감시할 폴더 추가
        
        Args:
            folder_path: 폴더 전체 경로 (예: /Users/xxx/Google Drive/수련사진/3시부)
            folder_name: 폴더 별칭 (예: "3시부")
        
        Returns:
            성공 여부
        """
        # watchdog이 없어도 폴링을 위해 등록은 진행함
        if not WATCHDOG_AVAILABLE:
            print("⚠️ watchdog 없음: 폴링 모드로 동작합니다.")
        
        # 경로 정규화 (Windows/macOS 호환)
        folder_path = os.path.normpath(folder_path)
        
        # 🔧 한글 경로 NFC 정규화 (macOS NFD 호환)
        folder_path = unicodedata.normalize('NFC', folder_path)
        folder_name = unicodedata.normalize('NFC', folder_name)
        
        if not os.path.exists(folder_path):
            print(f"⚠️ 폴더가 존재하지 않습니다: {folder_path}")
            # 폴더 생성 시도
            try:
                os.makedirs(folder_path, exist_ok=True)
                print(f"✅ 폴더 생성됨: {folder_path}")
            except Exception as e:
                print(f"❌ 폴더 생성 실패: {e}")
                return False
        
        if folder_path in self.handlers:
            print(f"ℹ️ 이미 감시 중인 폴더: {folder_path}")
            return True
        
        # 핸들러 생성
        handler = DebouncedFolderHandler(
            folder_path=folder_path,
            folder_name=folder_name,
            callback=self._on_files_ready,
            debounce_seconds=self.debounce_seconds
        )
        
        self.handlers[folder_path] = handler
        print(f"✅ 감시 폴더 추가됨: [{folder_name}] {folder_path}")
        return True
    
    def remove_folder(self, folder_path: str):
        """감시 폴더 제거"""
        folder_path = os.path.normpath(folder_path)
        if folder_path in self.handlers:
            del self.handlers[folder_path]
            print(f"✅ 감시 폴더 제거됨: {folder_path}")
    
    def _on_files_ready(self, folder_path: str, folder_name: str, files: List[str]):
        """파일 준비 완료 시 호출"""
        if self.callback:
            try:
                self.callback(folder_path, folder_name, files)
            except Exception as e:
                print(f"❌ 콜백 실행 오류: {e}")
                import traceback
                traceback.print_exc()
    
    def start(self) -> bool:
        """폴더 감시 시작 (별도 스레드)"""
        if not WATCHDOG_AVAILABLE:
            print("⚠️ watchdog 라이브러리가 없습니다. 폴링 모드로 시작합니다.")
            # return False  <- 제거: 폴링을 위해 계속 진행
        
        # 이미 실행 중이면 먼저 중지
        if self.is_running:
            print("🔄 기존 감시 중지 후 재시작...")
            self.stop()
        
        if not self.handlers:
            print("⚠️ 감시할 폴더가 없습니다.")
            return False
        
        # 각 폴더에 대해 Observer 생성 (watchdog이 있을 때만)
        # 각 폴더에 대해 Observer 생성
        for folder_path, handler in self.handlers.items():
            if not WATCHDOG_AVAILABLE:
                continue
            try:
                observer = Observer()
                observer.schedule(handler, folder_path, recursive=False)
                observer.start()
                self.observers.append(observer)
                print(f"  ✅ Observer 등록: [{handler.folder_name}]")
            except Exception as e:
                print(f"  ❌ Observer 등록 실패 [{handler.folder_name}]: {e}")
        
        # 폴링 스레드 시작 (Google Drive 폴더용 백업 감지)
        self._init_known_files()
        
        # 🔧 is_running을 스레드 시작 전에 True로 설정해야 루프가 작동함
        self.is_running = True
        
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        print(f"🔄 폴링 스레드 시작됨 (간격: {self.polling_interval}초)")
        
        print(f"🔍 폴더 감시 시작됨: {len(self.observers)}개 Observer + 폴링")
        return True
    
    def _init_known_files(self):
        """현재 폴더의 파일 목록 초기화"""
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif',
                           '.mp4', '.mov', '.avi', '.mkv', '.m4v'}
        
        for folder_path, handler in self.handlers.items():
            try:
                files = set()
                exists = os.path.exists(folder_path)
                print(f"  🔍 [{handler.folder_name}] 경로 확인: {folder_path}")
                print(f"      폴더 존재: {exists}")
                
                if exists:
                    try:
                        all_files = os.listdir(folder_path)
                        print(f"      전체 파일 수: {len(all_files)}")
                        
                        for f in all_files:
                            # 🔧 한글 파일명 NFC 정규화
                            f_normalized = unicodedata.normalize('NFC', f)
                            ext = os.path.splitext(f_normalized)[1].lower()
                            if ext in valid_extensions:
                                files.add(f_normalized)
                    except Exception as list_err:
                        print(f"      ❌ 파일 목록 조회 실패: {list_err}")
                        
                self.known_files[folder_path] = files
                print(f"  📋 [{handler.folder_name}] 기존 파일 {len(files)}개 등록")
            except Exception as e:
                print(f"  ⚠️ [{handler.folder_name}] 파일 목록 초기화 실패: {e}")
                self.known_files[folder_path] = set()
    
    def _polling_loop(self):
        """폴링 루프 - 주기적으로 폴더 스캔"""
        print(f"🔄 [폴링] 루프 시작됨 - is_running: {self.is_running}, handlers: {len(self.handlers)}")
        
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif',
                           '.mp4', '.mov', '.avi', '.mkv', '.m4v'}
        
        poll_count = 0
        while self.is_running:
            try:
                poll_count += 1
                print(f"🔄 [폴링] 스캔 #{poll_count} - {len(self.handlers)}개 폴더 확인 중...")
                
                for folder_path, handler in self.handlers.items():
                    # 폴더 존재 확인
                    if not os.path.exists(folder_path):
                        continue
                    
                    try:
                        # 현재 파일 목록 가져오기 (NFC 정규화)
                        current_files = set()
                        for f in os.listdir(folder_path):
                            # 🔧 한글 파일명 NFC 정규화
                            f_normalized = unicodedata.normalize('NFC', f)
                            ext = os.path.splitext(f_normalized)[1].lower()
                            if ext in valid_extensions:
                                current_files.add(f_normalized)
                        
                        # 새 파일 감지
                        known = self.known_files.get(folder_path, set())
                        new_files = current_files - known
                        
                        if new_files:
                            print(f"🔔 [폴링] [{handler.folder_name}] 새 파일 {len(new_files)}개 감지!")
                            for f in new_files:
                                # 원본 파일명 찾기 (NFC 또는 NFD)
                                actual_filename = f
                                for orig_f in os.listdir(folder_path):
                                    if unicodedata.normalize('NFC', orig_f) == f:
                                        actual_filename = orig_f
                                        break
                                filepath = os.path.join(folder_path, actual_filename)
                                handler._handle_file_event(filepath)
                            
                            # 알려진 파일 목록 업데이트
                            self.known_files[folder_path] = current_files
                    except Exception as scan_err:
                        print(f"⚠️ [폴링] {handler.folder_name} 스캔 오류: {scan_err}")
            except Exception as e:
                print(f"⚠️ 폴링 중 오류: {e}")
            
            # 폴링 간격 대기
            time.sleep(self.polling_interval)
    
    def stop(self):
        """폴더 감시 중지"""
        self.is_running = False
        
        # 폴링 스레드 중지 대기
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=5)
        
        for observer in self.observers:
            observer.stop()
            observer.join(timeout=2)
        
        self.observers.clear()
        self.known_files.clear()
        print("🛑 폴더 감시 중지됨")
    
    def get_status(self) -> Dict:
        """현재 상태 반환"""
        return {
            "is_running": self.is_running,
            "folders": list(self.handlers.keys()),
            "folder_count": len(self.handlers),
            "debounce_seconds": self.debounce_seconds,
            "polling_interval": self.polling_interval
        }


# 크로스 플랫폼 시스템 알림 함수
def send_system_notification(title: str, message: str, sound: bool = True):
    """
    크로스 플랫폼 시스템 알림 전송

    Args:
        title: 알림 제목
        message: 알림 내용
        sound: 소리 재생 여부
    """
    import platform
    system = platform.system()
    
    try:
        if system == 'Darwin':  # macOS
            import subprocess
            sound_cmd = 'with sound name "default"' if sound else ''
            script = f'''
            display notification "{message}" with title "{title}" {sound_cmd}
            '''
            subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
            print(f"📢 [시스템 알림] {title}: {message}")
            
        elif system == 'Windows':
            # Windows 알림 (win10toast 또는 기본 출력)
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=5, threaded=True)
                print(f"📢 [시스템 알림] {title}: {message}")
            except ImportError:
                # win10toast가 없으면 콘솔 출력
                print(f"📢 [알림] {title}: {message}")
                
        else:  # Linux
            # Linux 알림 (notify-send)
            try:
                import subprocess
                subprocess.run(['notify-send', title, message], check=True, capture_output=True)
                print(f"📢 [시스템 알림] {title}: {message}")
            except:
                print(f"📢 [알림] {title}: {message}")
                
    except Exception as e:
        print(f"⚠️ 시스템 알림 실패: {e}")
        print(f"📢 [알림] {title}: {message}")


# 이전 함수명 호환성 유지
send_macos_notification = send_system_notification


# 테스트 코드
if __name__ == "__main__":
    def test_callback(folder_path, folder_name, files):
        print(f"\n{'='*50}")
        print(f"📦 처리 완료!")
        print(f"  폴더: {folder_name}")
        print(f"  경로: {folder_path}")
        print(f"  파일 수: {len(files)}")
        for f in files[:5]:
            print(f"    - {os.path.basename(f)}")
        if len(files) > 5:
            print(f"    ... 외 {len(files) - 5}개")
        print('='*50)
        
        send_macos_notification(
            title=f"{folder_name} 사진 감지",
            message=f"{len(files)}개 파일 준비 완료"
        )
    
    watcher = DriveWatcher(debounce_seconds=10)  # 테스트용 10초
    watcher.set_callback(test_callback)
    watcher.add_folder("/tmp/test_drive_watcher", "테스트폴더")
    
    if watcher.start():
        print("\n폴더 감시 중... Ctrl+C로 종료")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            watcher.stop()
            print("종료됨")
