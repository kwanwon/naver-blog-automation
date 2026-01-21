import flet as ft # type: ignore
from modules.gpt_handler import GPTHandler
from modules.serial_auth import BlogSerialAuth
from modules.auto_updater import AutoUpdater  # 자동 업데이트 추가
from config.config import Config
from modules.scheduler_engine import SmartScheduler
from naver_band_auto import NaverBandAutomation
from naver_band_comment_reply import NaverBandCommentReply  # 밴드 댓글 답글
from naver_cafe_auto import NaverCafeAutomation
from modules.idle_activity import IdleActivity

import subprocess
import os
import sys  # sys 모듈 추가
import io

# 🆕 Windows 콘솔 인코딩 문제 해결 (이모지 출력 시 UnicodeEncodeError 방지)
if sys.platform == 'win32':
    try:
        # stdout/stderr를 UTF-8로 설정하고, 인코딩 불가능한 문자는 ?로 대체
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass  # 콘솔이 없는 경우 (noconsole 모드) 무시
import platform  # 플랫폼 감지 추가
from datetime import datetime, timedelta
import json
from utils.folder_cleanup import FolderCleanup  # 추가
import random
import hashlib
import threading
import time
import traceback

class BlogWriterApp:
    def __init__(self):
        # 플랫폼 정보 감지
        self.platform_system = platform.system().lower()  # 'windows', 'darwin', 'linux'
        self.is_windows = self.platform_system == 'windows'
        self.is_macos = self.platform_system == 'darwin'
        self.is_linux = self.platform_system == 'linux'
        
        print(f"🌍 플랫폼 감지: {platform.system()} ({platform.machine()})")
        print(f"💻 운영체제: {platform.platform()}")
        
        # 기본 디렉토리 설정
        self.base_dir = self._get_base_directory()
        
        # 시리얼 인증 초기화
        self.serial_auth = BlogSerialAuth()
        
        print(f"📁 최종 기본 디렉토리: {self.base_dir}")
        print(f"🔄 현재 작업 디렉토리: {os.getcwd()}")
        
        # 자동 업데이트 확인 (백그라운드에서)
        self.check_for_updates()
        
        # 디렉토리 존재 확인 및 생성
        self._ensure_directories()
        
        # 이미지 폴더 생성
        self.create_image_folders()
        
        # 폴더 정리 실행
        cleanup = FolderCleanup(retention_days=2)
        cleanup.cleanup_old_folders()
        
        # 설정 초기화
        self.settings = self.load_settings()
        self.use_dummy = self.settings.get('use_dummy', False)
        
        self.gpt_handler = GPTHandler(use_dummy=self.use_dummy)
        self.current_title = ""
        self.current_content = ""
        self.last_save_content = None
        self.browser_driver = None  # 브라우저 드라이버 인스턴스
        self.temp_driver = None  # 임시 브라우저 드라이버 인스턴스
        
        # 🔒 브라우저 락 - 동시 실행 방지 (스케줄러, 수동 실행 등)
        self.browser_lock = threading.Lock()
        self.is_browser_busy = False  # 현재 브라우저 사용 중인지
        # AI 모델 사용 로그 저장
        self.model_usage_logs = []  # [{time, topic, model, status, reason, target, duration}]
        # 🆕 크로스 플랫폼: 사용자 데이터 폴더 사용
        app_data_dir = self._get_app_data_dir()
        self.model_usage_log_path = os.path.join(app_data_dir, 'config', 'model_usage_logs.json')
        os.makedirs(os.path.dirname(self.model_usage_log_path), exist_ok=True)
        
        self._load_model_usage_logs()
        self.model_usage_cost_text = None  # 비용 요약 텍스트
        self.model_usage_cost_detail = None  # 비용 상세 텍스트
        self.model_usage_full_dialog = None  # 전체 로그 보기 다이얼로그
        
        # 순차적 주제 선택을 위한 인덱스 추적 변수 (플랫폼별)
        self.topic_indices = {'blog': -1, 'band': -1, 'cafe': -1}
        self.load_topic_index()  # 저장된 인덱스 로드
        
        # 타이머 관련 변수들
        self.timer_running = False
        self.timer_thread = None
        self.next_post_time = None
        self.daily_post_count = 0
        self.timer_start_btn = None
        self.timer_stop_btn = None
        
        # UI 참조들 (타이머에서 사용)
        self.page_ref = None
        self.send_message_func = None
        self.last_upload_success = False  # 마지막 업로드 성공 여부 추적
        
        # 시계 관련 변수들
        self.clock_text = None
        self.clock_thread = None
        self.clock_running = False
        
        # 절전 모드 방지 관련 변수들 (macOS 전용)
        self.caffeinate_process = None
        
        # 블로그 댓글 답글 limit (기본값 10)
        self.blog_reply_limit = "10"
        
        # 스마트 스케줄러 초기화
        # 🆕 크로스 플랫폼: 사용자 데이터 폴더 사용
        scheduler_path = os.path.join(app_data_dir, 'config', 'smart_scheduler.json')
        self.scheduler = SmartScheduler(scheduler_path)
        self.scheduler.on_task_executed = self.handle_scheduled_task
        
        self.scheduler.on_task_executed = self.handle_scheduled_task
        
        # 밴드 예약 큐 초기화
        self.band_reservation_queue = []
        
        # 댓글 모니터링 모듈 (백그라운드)
        self.comment_monitor = None
        self.comment_monitor_active = False
        
        # 드라이브 자동 포스팅 시스템
        self.drive_auto_post_system = None
        self._init_drive_auto_post()
        
        # 🔄 세션 유지 시스템 (30분 비활성 시 네이버 홈 방문)
        self.session_keep_alive_active = False
        self.session_keep_alive_thread = None
        self.last_activity_time = time.time()
        self.session_refresh_interval = 30 * 60  # 30분 (초 단위)
        
        if self.is_macos:
            self._start_caffeinate()


    def _get_app_data_dir(self):
        """사용자 데이터 디렉토리 반환 (~/.blog_automation)"""
        try:
            home = os.path.expanduser("~")
            # Windows: AppData/Local/BlogAutomation, Mac: ~/.blog_automation
            if self.is_windows:
                app_data = os.getenv('LOCALAPPDATA', os.path.join(home, 'AppData', 'Local'))
                base = os.path.join(app_data, 'BlogAutomation')
            else:
                base = os.path.join(home, '.blog_automation')
            
            os.makedirs(base, exist_ok=True)
            return base
        except Exception as e:
            print(f"❌ 데이터 디렉토리 생성 실패: {e}")
            return os.path.join(os.getcwd(), 'data')

    def load_settings(self):
        """앱 설정 파일 로드"""
        # 1. 사용자 데이터 폴더에서 먼저 시도
        app_data_dir = self._get_app_data_dir()
        settings_path = os.path.join(app_data_dir, 'config', 'app_settings.json')
        
        # 2. 없으면 기본 설치 경로에서 시도 (초기값)
        if not os.path.exists(settings_path):
            legacy_path = os.path.join(self.base_dir, 'config', 'app_settings.json')
            if os.path.exists(legacy_path):
                settings_path = legacy_path

        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"설정 로드 중 오류: {e}")
        return {}

    def save_settings(self):
        """앱 설정 파일 저장"""
        # 무조건 사용자 데이터 폴더에 저장
        app_data_dir = self._get_app_data_dir()
        settings_path = os.path.join(app_data_dir, 'config', 'app_settings.json')
        
        try:
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"설정 저장 중 오류: {e}")
    
    def _save_setting(self, key: str, value):
        """개별 설정 저장 (UI on_blur 이벤트용)"""
        # 폴더 경로 설정의 경우 따옴표 자동 제거
        if isinstance(value, str) and 'folder' in key.lower():
            value = value.strip("'").strip('"').strip()
        
        self.settings[key] = value
        self.save_settings()
        print(f"✅ 설정 저장됨: {key}")

    
    def _init_drive_auto_post(self):
        """드라이브 자동 포스팅 시스템 초기화"""
        try:
            from modules.drive_auto_post import DriveAutoPostSystem
            
            self.drive_auto_post_system = DriveAutoPostSystem(self.settings)
            
            # 콜백 설정
            self.drive_auto_post_system.generate_content = self._drive_generate_content
            self.drive_auto_post_system.post_to_band = self._drive_post_to_band
            self.drive_auto_post_system.on_post_success = self._drive_on_success
            self.drive_auto_post_system.on_post_fail = self._drive_on_fail
            
            print("✅ 드라이브 자동 포스팅 시스템 초기화 완료")
        except Exception as e:
            print(f"⚠️ 드라이브 자동 포스팅 시스템 초기화 실패: {e}")
            self.drive_auto_post_system = None
    
    def _drive_generate_content(self, topic: str, folder_name: str):
        """드라이브 자동 포스팅용 AI 글 생성"""
        try:
            full_topic = f"[{folder_name}] {topic}"
            # 🟢 드라이브 자동포스팅 전용 지침 사용 (band_instructions와 분리)
            result = self.gpt_handler.generate_platform_content(
                full_topic,
                platform='drive_auto',  # 전용 플랫폼 타입
                task_type='regular'
            )
            return result
        except Exception as e:
            print(f"❌ AI 글 생성 오류: {e}")
            return None
    
    def _drive_post_to_band(self, content: str, image_paths: list):
        """드라이브 자동 포스팅용 밴드 포스팅"""
        try:
            from naver_band_auto import NaverBandAutomation
            
            driver = self.get_or_create_driver()
            band_url = self.settings.get('band_url', '')
            
            if not band_url:
                print("❌ 밴드 URL이 설정되지 않았습니다.")
                return False
            
            band_auto = NaverBandAutomation(driver)
            success = band_auto.post_to_band(
                band_url=band_url,
                content=content,
                image_paths=image_paths if image_paths else None
            )
            return success
        except Exception as e:
            print(f"❌ 밴드 포스팅 오류: {e}")
            return False
    
    def _drive_on_success(self, folder_name: str, file_count: int):
        """드라이브 자동 포스팅 성공 콜백"""
        print(f"🎉 [{folder_name}] {file_count}개 사진 포스팅 성공!")
    
    def _drive_on_fail(self, folder_name: str, error: str):
        """드라이브 자동 포스팅 실패 콜백"""
        print(f"❌ [{folder_name}] 포스팅 실패: {error}")
    
    def _start_drive_auto_post(self, page):
        """드라이브 자동 포스팅 시작"""
        print("🔄 [드라이브 자동 포스팅] 시작 버튼 클릭됨...")
        
        if not self.drive_auto_post_system:
            print("⚙️ 드라이브 자동 포스팅 시스템 초기화 중...")
            self._init_drive_auto_post()
        
        if not self.drive_auto_post_system:
            print("❌ 드라이브 자동 포스팅 시스템 초기화 실패")
            page.snack_bar = ft.SnackBar(content=ft.Text("❌ 드라이브 자동 포스팅 시스템 초기화 실패"))
            page.snack_bar.open = True
            page.update()
            return
        
        # 상위 폴더 경로
        parent_folder = self.settings.get('drive_parent_folder', '')
        print(f"📁 상위 폴더 경로: '{parent_folder}'")
        
        if not parent_folder:
            print("❌ 상위 폴더 경로가 비어 있음")
            page.snack_bar = ft.SnackBar(content=ft.Text("❌ 상위 폴더 경로를 입력해주세요."), bgcolor=ft.Colors.RED)
            page.snack_bar.open = True
            page.update()
            return
        
        # 제외 폴더 파싱
        exclude_str = self.settings.get('drive_exclude_folders', '백업사진, 실패사진')
        exclude_folders = [f.strip() for f in exclude_str.split(',') if f.strip()]
        
        # 상위 폴더 기준으로 백업/실패 폴더 자동 설정
        backup_dir = os.path.join(parent_folder, '백업사진')
        error_dir = os.path.join(parent_folder, '실패사진')
        
        # 폴더 생성 (없으면)
        os.makedirs(backup_dir, exist_ok=True)
        os.makedirs(error_dir, exist_ok=True)
        
        print(f"📁 백업 폴더: {backup_dir}")
        print(f"📁 실패 폴더: {error_dir}")
        
        # 설정 적용
        sheet_url = self.settings.get('google_sheet_url', '')
        print(f"📊 스프레드시트 URL 설정: '{sheet_url[:60]}...' " if sheet_url else "📊 스프레드시트 URL: 없음")
        
        self.drive_auto_post_system.configure({
            "google_sheet_url": sheet_url,
            "backup_dir": backup_dir,
            "error_dir": error_dir
        })
        
        # 상위 폴더에서 하위 폴더들 자동 스캔 및 등록
        scanned = self.drive_auto_post_system.scan_and_add_subfolders(parent_folder, exclude_folders)
        
        if not scanned:
            page.snack_bar = ft.SnackBar(content=ft.Text("❌ 감시할 하위 폴더가 없습니다."), bgcolor=ft.Colors.RED)
            page.snack_bar.open = True
            page.update()
            return
        
        # 시작
        if self.drive_auto_post_system.start():
            folder_names = ', '.join([f['name'] for f in scanned[:5]])
            if len(scanned) > 5:
                folder_names += f" 외 {len(scanned) - 5}개"
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"✅ 자동 감지 시작! {len(scanned)}개 폴더 감시 중: {folder_names}"),
                bgcolor=ft.Colors.GREEN
            )
        else:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("❌ 드라이브 자동 포스팅 시작 실패"),
                bgcolor=ft.Colors.RED
            )
        
        page.snack_bar.open = True
        page.update()
    
    def _on_drive_folder_selected(self, e: ft.FilePickerResultEvent, text_field: ft.TextField):
        if e.path:
            # 선택된 경로를 정규화(NFC)하여 한글 깨짐 방지
            import unicodedata
            normalized_path = unicodedata.normalize('NFC', e.path)
            
            text_field.value = normalized_path
            self._save_setting('drive_parent_folder', normalized_path)
            text_field.update()
            
            # 안내 메시지
            if text_field.page:
                text_field.page.snack_bar = ft.SnackBar(content=ft.Text(f"✅ 폴더가 선택되었습니다: {os.path.basename(normalized_path)}"))
                text_field.page.snack_bar.open = True
                text_field.page.update()

    def _on_global_folder_picker_result(self, e: ft.FilePickerResultEvent):
        """전역 폴더 선택기 결과 처리"""
        if getattr(self, 'current_folder_picker_target', None):
            self._on_drive_folder_selected(e, self.current_folder_picker_target)
            self.current_folder_picker_target = None

    def _open_folder_picker(self, e):
        """폴더 선택기 열기 (macOS: osascript 사용, 크로스 플랫폼 지원)"""
        try:
            print("📂 폴더 선택 버튼 클릭됨")
            
            # 형제 컨트롤(TextField) 찾기
            row = e.control.parent
            text_field = row.controls[0]
            
            import threading
            import subprocess
            import unicodedata
            
            def run_folder_picker():
                try:
                    folder_path = None
                    
                    if sys.platform == 'darwin':  # macOS
                        # AppleScript를 통해 네이티브 폴더 선택 다이얼로그 실행
                        script = '''
                        tell application "System Events"
                            activate
                        end tell
                        set folderPath to POSIX path of (choose folder with prompt "📁 감시할 폴더를 선택하세요")
                        return folderPath
                        '''
                        result = subprocess.run(
                            ['osascript', '-e', script],
                            capture_output=True,
                            text=True,
                            timeout=60
                        )
                        
                        if result.returncode == 0 and result.stdout.strip():
                            folder_path = result.stdout.strip()
                            # 경로 끝의 / 제거
                            if folder_path.endswith('/'):
                                folder_path = folder_path[:-1]
                        else:
                            print("⚠️ 폴더 선택이 취소됨")
                            return
                            
                    else:  # Windows/Linux
                        from tkinter import Tk, filedialog
                        root = Tk()
                        root.withdraw()
                        folder_path = filedialog.askdirectory(title="감시할 폴더를 선택하세요")
                        root.destroy()
                        
                        if not folder_path:
                            print("⚠️ 폴더 선택이 취소됨")
                            return
                    
                    if folder_path:
                        # 한글 경로 정규화 (NFD → NFC)
                        normalized_path = unicodedata.normalize('NFC', folder_path)
                        print(f"✅ 선택된 폴더: {normalized_path}")
                        
                        # UI 업데이트
                        text_field.value = normalized_path
                        self._save_setting('drive_parent_folder', normalized_path)
                        text_field.update()
                        
                        # 안내 메시지
                        if text_field.page:
                            text_field.page.snack_bar = ft.SnackBar(
                                content=ft.Text(f"✅ 폴더가 선택되었습니다: {os.path.basename(normalized_path)}")
                            )
                            text_field.page.snack_bar.open = True
                            text_field.page.update()
                            
                except subprocess.TimeoutExpired:
                    print("⚠️ 폴더 선택 시간 초과")
                except Exception as inner_ex:
                    print(f"❌ 폴더 선택 오류: {inner_ex}")
            
            # 별도 스레드에서 실행 (UI 블로킹 방지)
            threading.Thread(target=run_folder_picker, daemon=True).start()
            
        except Exception as ex:
            print(f"❌ 폴더 선택기 열기 실패: {ex}")

    def _scan_drive_folders(self, page):
        """상위 폴더 스캔하여 하위 폴더 목록 표시"""
        parent_folder = self.settings.get('drive_parent_folder', '')
        
        if not parent_folder:
            page.snack_bar = ft.SnackBar(content=ft.Text("❌ 상위 폴더 경로를 먼저 입력해주세요."), bgcolor=ft.Colors.RED)
            page.snack_bar.open = True
            page.update()
            return
        
        if not os.path.exists(parent_folder):
            page.snack_bar = ft.SnackBar(content=ft.Text(f"❌ 폴더가 존재하지 않습니다: {parent_folder}"), bgcolor=ft.Colors.RED)
            page.snack_bar.open = True
            page.update()
            return
        
        # 제외 폴더 파싱
        exclude_str = self.settings.get('drive_exclude_folders', '백업사진, 실패사진')
        exclude_folders = [f.strip() for f in exclude_str.split(',') if f.strip()]
        
        # 하위 폴더 조회
        if self.drive_auto_post_system:
            folders = self.drive_auto_post_system.get_subfolders(parent_folder, exclude_folders)
        else:
            # 직접 조회
            from pathlib import Path
            default_excludes = {'백업사진', '실패사진', 'Backup', 'Error', '.DS_Store', '@eaDir'}
            exclude_set = default_excludes | set(exclude_folders)
            
            folders = []
            for item in sorted(os.listdir(parent_folder)):
                item_path = os.path.join(parent_folder, item)
                if os.path.isdir(item_path) and item not in exclude_set and not item.startswith('.'):
                    folders.append({"path": item_path, "name": item})
        
        if folders:
            folder_names = [f['name'] for f in folders]
            message = f"✅ {len(folders)}개 폴더 발견: {', '.join(folder_names[:10])}"
            if len(folder_names) > 10:
                message += f" 외 {len(folder_names) - 10}개"
            page.snack_bar = ft.SnackBar(content=ft.Text(message), bgcolor=ft.Colors.GREEN)
        else:
            page.snack_bar = ft.SnackBar(content=ft.Text("⚠️ 하위 폴더가 없거나 모두 제외되었습니다."), bgcolor=ft.Colors.ORANGE)
        
        page.snack_bar.open = True
        page.update()
    
    def _stop_drive_auto_post(self, page):
        """드라이브 자동 포스팅 중지"""
        if self.drive_auto_post_system:
            self.drive_auto_post_system.stop()
            page.snack_bar = ft.SnackBar(content=ft.Text("🛑 드라이브 자동 포스팅 중지됨"))
            page.snack_bar.open = True
            page.update()


    def _debug_log(self, hypothesis_id: str, location: str, message: str, data: dict | None = None, run_id: str = "run1"):
        """Debug NDJSON 로그를 로컬 파일로 남깁니다."""
        try:
            payload = {
                "sessionId": "debug-session",
                "runId": run_id,
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data or {},
                "timestamp": int(time.time() * 1000),
            }
            # #region agent log
            # 🆕 크로스 플랫폼: 사용자 데이터 폴더 사용
            app_data_dir = self._get_app_data_dir()
            debug_log_path = os.path.join(app_data_dir, 'logs', 'debug.log')
            os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)
            with open(debug_log_path, "a", encoding="utf-8") as lf:
                lf.write(json.dumps(payload, ensure_ascii=False) + "\n")
            # #endregion
        except Exception:
            pass

    def _load_model_usage_logs(self):
        """AI 사용 로그를 파일에서 로드"""
        try:
            if os.path.exists(self.model_usage_log_path):
                with open(self.model_usage_log_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        # 최신 500건만 유지
                        self.model_usage_logs = data[-500:]
                        print(f"📂 AI 사용 로그 로드: {len(self.model_usage_logs)}건")
        except Exception as e:
            print(f"AI 사용 로그 로드 실패(무시): {e}")

    def _save_model_usage_logs(self):
        """AI 사용 로그를 파일로 저장"""
        try:
            os.makedirs(os.path.dirname(self.model_usage_log_path), exist_ok=True)
            with open(self.model_usage_log_path, 'w', encoding='utf-8') as f:
                json.dump(self.model_usage_logs[-500:], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"AI 사용 로그 저장 실패(무시): {e}")

    def _compute_usage_costs(self):
        """로그 기반 사용량/비용 집계 (오늘 / 최근 30일)"""
        today = datetime.now().date()
        cutoff = datetime.now() - timedelta(days=30)
        by_model_today = {}
        by_model_month = {}

        def per_post_cost(model_id: str) -> float:
            info = Config.AI_MODELS.get(model_id, {})
            if info.get("free"):
                return 0.0
            ic = info.get("input_cost_per_1k_krw") or 0
            oc = info.get("output_cost_per_1k_krw") or 0
            # 기존 UI 가정과 동일: 입력 1K, 출력 2K 사용
            return ic + 2 * oc

        for log in self.model_usage_logs:
            try:
                ts = datetime.strptime(log.get("time", ""), "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            mid = log.get("model", "")
            if not mid:
                continue
            cost = per_post_cost(mid)
            if ts.date() == today:
                by_model_today[mid] = by_model_today.get(mid, 0) + cost
            if ts >= cutoff:
                by_model_month[mid] = by_model_month.get(mid, 0) + cost

        total_today = sum(by_model_today.values())
        total_month = sum(by_model_month.values())

        def fmt_lines(data: dict):
            lines = []
            for mid, val in sorted(data.items(), key=lambda x: -x[1]):
                name = Config.AI_MODELS.get(mid, {}).get("name", mid)
                lines.append(f"- {name}: ≈₩{int(val):,}")
            return "\n".join(lines) if lines else "-"

        return {
            "today": total_today,
            "month": total_month,
            "today_lines": fmt_lines(by_model_today),
            "month_lines": fmt_lines(by_model_month)
        }

    def _update_usage_cost_ui(self):
        """비용 요약 UI 업데이트"""
        try:
            if not (hasattr(self, "model_usage_cost_text") and hasattr(self, "model_usage_cost_detail")):
                return
            costs = self._compute_usage_costs()
            self.model_usage_cost_text.value = (
                f"오늘 ≈₩{int(costs['today']):,} / 최근 30일 ≈₩{int(costs['month']):,}"
            )
            self.model_usage_cost_detail.value = (
                f"[오늘]\n{costs['today_lines']}\n\n[최근 30일]\n{costs['month_lines']}"
            )
            self.model_usage_cost_text.update()
            self.model_usage_cost_detail.update()
        except Exception as e:
            print(f"비용 요약 업데이트 실패(무시): {e}")
    
    def _start_caffeinate(self):
        """🆕 크로스 플랫폼: 절전 모드 방지 시작"""
        import platform
        system = platform.system()
        
        try:
            if system == 'Darwin':  # macOS
                import subprocess
                # caffeinate 명령어로 절전 모드 방지
                # -d: 디스플레이 절전 방지, -i: 시스템 유휴 절전 방지, -s: 시스템 절전 방지
                self.caffeinate_process = subprocess.Popen(
                    ['caffeinate', '-d', '-i', '-s'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("🔋 macOS 절전 모드 방지 활성화됨 (caffeinate 실행)")
                
            elif system == 'Windows':
                # Windows: SetThreadExecutionState 사용
                import ctypes
                ES_CONTINUOUS = 0x80000000
                ES_SYSTEM_REQUIRED = 0x00000001
                ES_DISPLAY_REQUIRED = 0x00000002
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
                )
                self.caffeinate_process = 'windows_active'  # 플래그로 표시
                print("🔋 Windows 절전 모드 방지 활성화됨")
                
            else:  # Linux
                print("ℹ️ Linux에서는 절전 모드 방지가 지원되지 않습니다.")
                self.caffeinate_process = None
                
        except Exception as e:
            print(f"⚠️ 절전 모드 방지 설정 실패: {str(e)}")
            self.caffeinate_process = None
    
    def _stop_caffeinate(self):
        """🆕 크로스 플랫폼: 절전 모드 방지 중지"""
        import platform
        system = platform.system()
        
        if self.caffeinate_process:
            try:
                if system == 'Darwin' and hasattr(self.caffeinate_process, 'terminate'):
                    # macOS: 프로세스 종료
                    self.caffeinate_process.terminate()
                    self.caffeinate_process.wait(timeout=5)
                    print("🔋 macOS 절전 모드 방지 해제됨 (caffeinate 종료)")
                    
                elif system == 'Windows':
                    # Windows: 절전 모드 허용으로 복원
                    import ctypes
                    ES_CONTINUOUS = 0x80000000
                    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                    print("🔋 Windows 절전 모드 방지 해제됨")
                    
            except Exception as e:
                print(f"⚠️ 절전 모드 방지 해제 중 오류: {str(e)}")
                if system == 'Darwin' and hasattr(self.caffeinate_process, 'kill'):
                    try:
                        self.caffeinate_process.kill()
                    except:
                        pass
            finally:
                self.caffeinate_process = None

    # =============== 세션 유지 시스템 ===============
    
    def start_session_keep_alive(self):
        """세션 유지 시스템 시작 - 30분 비활성 시 네이버 홈 방문"""
        if self.session_keep_alive_active:
            print("ℹ️ 세션 유지 시스템이 이미 실행 중입니다.")
            return
        
        self.session_keep_alive_active = True
        self.last_activity_time = time.time()
        
        def session_worker():
            print("🔄 세션 유지 시스템 시작됨 (30분 비활성 시 갱신)")
            
            while self.session_keep_alive_active:
                try:
                    # 10초마다 확인
                    time.sleep(10)
                    
                    # 브라우저가 사용 중이면 타이머 리셋
                    if self.is_browser_busy:
                        self.last_activity_time = time.time()
                        continue
                    
                    # 비활성 시간 확인
                    idle_time = time.time() - self.last_activity_time
                    
                    # 30분(1800초) 경과 시 세션 갱신
                    if idle_time >= self.session_refresh_interval:
                        print(f"⏰ {int(idle_time/60)}분 비활성 - 세션 갱신 시작...")
                        self._refresh_naver_session()
                        self.last_activity_time = time.time()
                        print("✅ 세션 갱신 완료 - 타이머 리셋")
                        
                except Exception as e:
                    print(f"⚠️ 세션 유지 오류: {e}")
                    time.sleep(60)  # 오류 시 1분 대기
            
            print("🔄 세션 유지 시스템 종료됨")
        
        self.session_keep_alive_thread = threading.Thread(target=session_worker, daemon=True)
        self.session_keep_alive_thread.start()
    
    def stop_session_keep_alive(self):
        """세션 유지 시스템 중지"""
        self.session_keep_alive_active = False
        print("🔄 세션 유지 시스템 중지 요청됨")
    
    def update_activity_time(self):
        """활동 시간 업데이트 (작업 시작/종료 시 호출)"""
        self.last_activity_time = time.time()
    
    def _refresh_naver_session(self):
        """네이버 홈 방문하여 세션 갱신"""
        try:
            # 락이 있으면 건너뛰기 (다른 작업 중)
            if self.is_browser_busy:
                print("ℹ️ 다른 작업 중 - 세션 갱신 건너뛰기")
                return
            
            # 드라이버 확인
            if not self.browser_driver or not self.is_driver_alive(self.browser_driver):
                print("ℹ️ 브라우저가 없음 - 세션 갱신 건너뛰기")
                return
            
            # 락 획득 (짧은 작업이므로 빠르게)
            self.browser_lock.acquire()
            self.is_browser_busy = True
            
            try:
                # 현재 URL 저장
                current_url = self.browser_driver.current_url
                
                # 네이버 홈 방문
                self.browser_driver.get("https://www.naver.com")
                time.sleep(2)
                
                # 로그인 상태 확인 (간단한 체크)
                page_source = self.browser_driver.page_source
                if "로그인" in page_source and "로그아웃" not in page_source:
                    print("⚠️ 로그인 세션 만료됨!")
                else:
                    print("✅ 네이버 세션 유효 확인됨")
                
                # 원래 페이지로 복귀 (블로그 홈으로)
                self.browser_driver.get("https://section.blog.naver.com/")
                time.sleep(1)
                
            finally:
                self.is_browser_busy = False
                self.browser_lock.release()
                
        except Exception as e:
            print(f"⚠️ 세션 갱신 중 오류: {e}")
            self.is_browser_busy = False
            try:
                self.browser_lock.release()
            except:
                pass

    def start_comment_monitoring(self):
        """백그라운드 댓글 모니터링 시작 (다른 작업과 독립적)"""
        if self.comment_monitor_active:
            print("⚠️ 댓글 모니터링이 이미 실행 중입니다.")
            return
        
        try:
            # 브라우저 드라이버 필요
            driver = self.get_or_create_driver()
            if not driver:
                print("❌ 댓글 모니터링을 위한 브라우저를 시작할 수 없습니다.")
                return
            
            idle_module = IdleActivity(driver, self.gpt_handler, self.base_dir)
            use_ai_reply = self.settings.get('idle_use_ai_reply', False)
            check_interval = self.settings.get('idle_comment_check_interval', 300)
            
            idle_module.start_comment_monitoring(check_interval=check_interval, use_ai=use_ai_reply)
            self.comment_monitor = idle_module
            self.comment_monitor_active = True
            
            print(f"👀 백그라운드 댓글 모니터링 시작 (주기: {check_interval}초, AI: {use_ai_reply})")
            
        except Exception as e:
            print(f"❌ 댓글 모니터링 시작 실패: {e}")
            self.comment_monitor_active = False
    
    def stop_comment_monitoring(self):
        """백그라운드 댓글 모니터링 중지"""
        if self.comment_monitor:
            try:
                self.comment_monitor.stop_comment_monitoring()
                print("🛑 백그라운드 댓글 모니터링 중지됨")
            except:
                pass
        self.comment_monitor = None
        self.comment_monitor_active = False


    def _get_base_directory(self):
        """플랫폼별 기본 디렉토리 결정"""
        if getattr(sys, 'frozen', False):
            # 실행 파일로 실행된 경우 (PyInstaller 등으로 빌드된 경우)
            base_dir = os.path.dirname(sys.executable)
            print(f"🔧 Frozen 모드: {base_dir}")
            
            # macOS .app 번들일 경우 처리
            if self.is_macos and "Contents/MacOS" in base_dir:
                print(f"🍎 macOS 앱 번들 감지")
                # .app 번들에서 리소스 디렉토리 찾기
                possible_dirs = [
                    # Resources 디렉토리 (표준 macOS 앱 구조)
                    os.path.join(os.path.dirname(base_dir), "Resources"),
                    # 번들 외부 디렉토리
                    os.path.dirname(os.path.dirname(os.path.dirname(base_dir))),
                    # 현재 작업 디렉토리
                    os.getcwd(),
                    # 실행 파일 디렉토리
                    base_dir
                ]
                
                for dir_path in possible_dirs:
                    print(f"📂 확인 중: {dir_path}")
                    if os.path.exists(dir_path):
                        print(f"  ✅ 디렉토리 존재함")
                        # config 디렉토리 확인
                        config_path = os.path.join(dir_path, 'config')
                        if os.path.exists(config_path):
                            print(f"  📁 config 디렉토리 찾음: {config_path}")
                            return dir_path
                            
                        # 상위 디렉토리의 config 확인
                        parent_config = os.path.join(os.path.dirname(dir_path), 'config')
                        if os.path.exists(parent_config):
                            print(f"  📁 상위 디렉토리에서 config 찾음: {parent_config}")
                            return os.path.dirname(dir_path)
            
            # Windows 실행 파일의 경우
            elif self.is_windows:
                print(f"🪟 Windows 실행 파일 모드")
                # Windows에서는 일반적으로 실행 파일과 같은 디렉토리에 리소스 배치
                
            # 기본 디렉토리에 config가 없는 경우 상위 디렉토리 탐색
            config_dir = os.path.join(base_dir, 'config')
            if not os.path.exists(config_dir):
                print(f"⚠️ 기본 디렉토리에 config 폴더가 없습니다.")
                # 실행 파일 경로에서 상위 디렉토리들 탐색
                test_dir = base_dir
                for i in range(3):  # 최대 3단계 상위까지 확인
                    test_dir = os.path.dirname(test_dir)
                    test_config = os.path.join(test_dir, 'config')
                    print(f"  🔍 상위 {i+1}단계 확인: {test_config}")
                    if os.path.exists(test_config):
                        print(f"  ✅ 상위 디렉토리에서 config 찾음: {test_config}")
                        return test_dir
            
            return base_dir
        else:
            # 스크립트로 실행된 경우
            base_dir = os.path.dirname(os.path.abspath(__file__))
            print(f"📝 스크립트 모드: {base_dir}")
            return base_dir

    def _ensure_directories(self):
        """필요한 디렉토리들을 생성합니다"""
        directories = ['config', 'drafts', 'settings', 'logs']
        
        for directory in directories:
            dir_path = os.path.join(self.base_dir, directory)
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"📁 디렉토리 확인/생성: {dir_path}")
            except Exception as e:
                print(f"❌ 디렉토리 생성 실패 ({directory}): {str(e)}")
        
        # 디렉토리 내용 확인 (디버깅용)
        try:
            contents = os.listdir(self.base_dir)
            print(f"📋 기본 디렉토리 내용: {contents}")
        except Exception as e:
            print(f"❌ 디렉토리 내용 확인 실패: {str(e)}")

    def _terminate_processes_safely(self):
        """플랫폼별로 안전하게 프로세스를 종료합니다"""
        try:
            print(f"🔄 프로세스 정리 시작 (플랫폼: {self.platform_system})")
            
            # macOS 절전 모드 방지 프로세스 종료
            if self.is_macos:
                self._stop_caffeinate()
            
            # 브라우저 드라이버 종료
            if hasattr(self, 'browser_driver') and self.browser_driver:
                try:
                    self.browser_driver.quit()
                    print("✅ 브라우저 드라이버 종료 완료")
                except Exception as e:
                    print(f"⚠️ 브라우저 드라이버 종료 중 오류: {e}")
            
            # 임시 브라우저 드라이버 종료
            if hasattr(self, 'temp_driver') and self.temp_driver:
                try:
                    self.temp_driver.quit()
                    print("✅ 임시 브라우저 드라이버 종료 완료")
                except Exception as e:
                    print(f"⚠️ 임시 브라우저 드라이버 종료 중 오류: {e}")
            
            # 플랫폼별 프로세스 종료
            if self.is_windows:
                # Windows 프로세스 종료
                try:
                    subprocess.run(["taskkill", "/f", "/im", "chromedriver.exe"], 
                                 capture_output=True, timeout=10)
                    subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], 
                                 capture_output=True, timeout=10)
                    print("✅ Windows 프로세스 종료 완료")
                except Exception as e:
                    print(f"⚠️ Windows 프로세스 종료 중 오류: {e}")
                    
            elif self.is_macos or self.is_linux:
                # macOS/Linux 프로세스 종료
                try:
                    subprocess.run(["pkill", "-f", "chromedriver"], 
                                 capture_output=True, timeout=10)
                    subprocess.run(["pkill", "-f", "chrome"], 
                                 capture_output=True, timeout=10)
                    print("✅ macOS/Linux 프로세스 종료 완료")
                except Exception as e:
                    print(f"⚠️ macOS/Linux 프로세스 종료 중 오류: {e}")
            
            # psutil을 사용한 자식 프로세스 종료 (크로스 플랫폼)
            try:
                import psutil # type: ignore
                current_process = psutil.Process()
                children = current_process.children(recursive=True)
                for child in children:
                    try:
                        child.terminate()
                        print(f"🔄 자식 프로세스 종료: {child.pid}")
                    except Exception as e:
                        print(f"⚠️ 자식 프로세스 종료 실패: {e}")
                        
                # 강제 종료가 필요한 경우
                gone, still_alive = psutil.wait_procs(children, timeout=3)
                for p in still_alive:
                    try:
                        p.kill()
                        print(f"💀 강제 종료: {p.pid}")
                    except:
                        pass
                        
            except ImportError:
                print("⚠️ psutil이 설치되지 않아 자식 프로세스 정리를 건너뜁니다.")
            except Exception as e:
                print(f"⚠️ 자식 프로세스 정리 중 오류: {e}")
                
        except Exception as e:
            print(f"❌ 프로세스 정리 중 전체 오류: {str(e)}")

    def _safe_exit(self, exit_code=0):
        """안전한 앱 종료"""
        try:
            print(f"🚪 안전한 앱 종료 시작 (코드: {exit_code})")
            
            # 시계 중지
            self.stop_clock()
            
            # 시리얼 상태 업데이터 중지
            self.stop_serial_status_updater()
            
            # 타이머 중지
            if self.timer_running:
                self.timer_running = False
            
            # 프로세스 정리
            self._terminate_processes_safely()
            
            # 플랫폼별 강제 종료
            pid = os.getpid()
            if self.is_windows:
                try:
                    subprocess.run([f"taskkill", "/F", "/PID", str(pid)], 
                                 capture_output=True, timeout=5)
                except:
                    pass
            else:
                try:
                    os.system(f"kill -9 {pid}")
                except:
                    pass
                    
            # Python 종료
            sys.exit(exit_code)
            
        except Exception as e:
            print(f"❌ 안전 종료 중 오류: {str(e)}")
            sys.exit(1)

    def simple_login(self, page, e):
        """간단한 로그인 프로세스 - 브라우저 열고 내 블로그까지 이동"""
        # 스낵바로 상태 표시
        page.snack_bar = ft.SnackBar(content=ft.Text("🔧 Chrome 클립보드 권한을 설정하고 있습니다..."))
        page.snack_bar.open = True
        page.update()
        
        def open_browser():
            try:
                # 1. 먼저 Chrome 클립보드 권한 설정
                print("🔧 Chrome 클립보드 권한 자동 설정 시작...")
                try:
                    from setup_chrome_permissions import setup_chrome_clipboard_permissions
                    setup_success = setup_chrome_clipboard_permissions()
                    if setup_success:
                        print("✅ Chrome 클립보드 권한 설정 완료")
                        page.snack_bar = ft.SnackBar(content=ft.Text("✅ Chrome 권한 설정 완료! 브라우저를 열고 있습니다..."))
                    else:
                        print("⚠️ Chrome 클립보드 권한 설정 실패, 계속 진행...")
                        page.snack_bar = ft.SnackBar(content=ft.Text("⚠️ 권한 설정 실패했지만 브라우저를 열고 있습니다..."))
                    page.snack_bar.open = True
                    page.update()
                except Exception as perm_error:
                    print(f"권한 설정 중 오류 (무시하고 계속): {perm_error}")
                    page.snack_bar = ft.SnackBar(content=ft.Text("🌐 브라우저를 열고 있습니다..."))
                    page.snack_bar.open = True
                    page.update()
                
                # 2. 브라우저 시작
                from manual_session_helper import ManualSessionHelper
                helper = ManualSessionHelper()
                
                # 브라우저 설정 및 시작
                helper.setup_driver()
                
                # 네이버 로그인 페이지로 이동
                helper.driver.get('https://nid.naver.com/nidlogin.login')
                time.sleep(2)
                
                # 브라우저 인스턴스를 임시 저장
                self.temp_driver = helper.driver
                
                # 로그인 완료 버튼 표시
                self.show_login_complete_button(page)
                
            except Exception as e:
                print(f"브라우저 열기 중 오류: {str(e)}")
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"❌ 브라우저 열기 중 오류가 발생했습니다: {str(e)}"),
                    bgcolor=ft.Colors.RED
                )
                page.snack_bar.open = True
                page.update()
        
        # 별도 스레드에서 브라우저 열기
        thread = threading.Thread(target=open_browser)
        thread.daemon = True
        thread.start()

    def show_login_complete_button(self, page):
        """로그인 완료 버튼 표시"""
        page.snack_bar = ft.SnackBar(content=ft.Text("🔐 브라우저에서 네이버 로그인을 완료한 후 아래 버튼을 클릭해주세요!"))
        page.snack_bar.open = True
        page.update()
        
        # 로그인 완료 확인 버튼
        complete_button = ft.ElevatedButton(
            text="로그인 완료",
            icon=ft.Icons.CHECK_CIRCLE,
            on_click=lambda e: self.complete_login(page),
            bgcolor=ft.Colors.GREEN,
            color=ft.Colors.WHITE,
            width=200,
            height=50
        )
        
        # 기존 로그인 버튼을 완료 버튼으로 교체
        self.update_login_button(page, complete_button)

    def complete_login(self, page):
        """로그인 완료 처리"""
        def complete_thread():
            try:
                # 내 블로그로 이동
                page.snack_bar = ft.SnackBar(content=ft.Text("📝 내 블로그로 이동 중..."))
                page.snack_bar.open = True
                page.update()
                
                self.temp_driver.get('https://blog.naver.com')
                time.sleep(3)
                
                # 로그인 상태 확인
                page_source = self.temp_driver.page_source
                if "로그아웃" in page_source or "님" in page_source:
                    # 세션 정보 저장
                    cookies = self.temp_driver.get_cookies()
                    cookies_file = os.path.join(self.base_dir, 'naver_cookies.json')
                    with open(cookies_file, 'w', encoding='utf-8') as f:
                        json.dump(cookies, f, ensure_ascii=False, indent=2)
                    
                    # 브라우저 인스턴스를 클래스 변수로 저장 (재사용을 위해)
                    self.browser_driver = self.temp_driver
                    self.temp_driver = None
                    
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text("✅ 로그인 완료! 내 블로그에 접속했습니다. 이제 업로드가 가능합니다."),
                        bgcolor=ft.Colors.GREEN
                    )
                    page.snack_bar.open = True
                    page.update()
                    
                    # 원래 로그인 버튼으로 복원
                    original_button = self.create_simple_login_button(page)
                    self.update_login_button(page, original_button.content)
                    
                else:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text("❌ 로그인에 실패했습니다. 다시 시도해주세요."),
                        bgcolor=ft.Colors.RED
                    )
                    page.snack_bar.open = True
                    page.update()
                    if hasattr(self, 'temp_driver') and self.temp_driver:
                        self.temp_driver.quit()
                        self.temp_driver = None
                    
                    # 원래 로그인 버튼으로 복원
                    original_button = self.create_simple_login_button(page)
                    self.update_login_button(page, original_button.content)
                    
            except Exception as e:
                print(f"로그인 완료 처리 중 오류: {str(e)}")
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"❌ 로그인 완료 처리 중 오류가 발생했습니다: {str(e)}"),
                    bgcolor=ft.Colors.RED
                )
                page.snack_bar.open = True
                page.update()
                
                # 원래 로그인 버튼으로 복원
                original_button = self.create_simple_login_button(page)
                self.update_login_button(page, original_button.content)
        
        # 별도 스레드에서 실행
        thread = threading.Thread(target=complete_thread)
        thread.daemon = True
        thread.start()

    def update_login_button(self, page, new_button):
        """로그인 버튼 업데이트"""
        try:
            # 페이지 구조: [0] = header, [1] = tabs
            # 첫 번째 탭(블로그 작성)의 첫 번째 컨트롤(로그인 버튼)을 업데이트
            main_tab = page.controls[1].tabs[0].content  # 두 번째 컨트롤(탭)의 첫 번째 탭
            if isinstance(new_button, ft.Row):
                # 새 버튼이 Row인 경우 (타이머 버튼들과 함께)
                main_tab.controls[0] = ft.Container(
                    content=new_button,
                    alignment=ft.alignment.center,
                    padding=ft.padding.all(10)
                )
            else:
                # 새 버튼이 단일 버튼인 경우
                main_tab.controls[0] = ft.Container(
                    content=new_button,
                    alignment=ft.alignment.center,
                    padding=ft.padding.all(10)
                )
            page.update()
        except Exception as e:
            print(f"버튼 업데이트 중 오류: {str(e)}")
            # 오류 발생 시 상세 정보 출력
            try:
                print(f"페이지 컨트롤 수: {len(page.controls)}")
                if len(page.controls) > 1:
                    print(f"탭 수: {len(page.controls[1].tabs)}")
            except:
                pass

    def check_login_status(self):
        """네이버 로그인 상태 확인"""
        cookies_path = os.path.join(self.base_dir, 'naver_cookies.json')
        return os.path.exists(cookies_path)
    
    def band_login(self, page, e):
        """밴드 로그인 - 밴드 페이지로 이동"""
        page.snack_bar = ft.SnackBar(
            content=ft.Text("🎵 밴드 로그인 페이지를 여는 중..."),
            bgcolor=ft.Colors.GREEN_700
        )
        page.snack_bar.open = True
        page.update()
        
        def open_band():
            try:
                # 브라우저가 이미 있으면 그것을 사용, 없으면 새로 생성
                driver = self.get_or_create_driver()
                
                # 밴드 페이지로 이동
                band_url = self.settings.get('band_url', 'https://band.us')
                driver.get(band_url)
                time.sleep(2)
                
                # 스낵바 업데이트
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("✅ 밴드 페이지가 열렸습니다. 로그인이 필요하면 브라우저에서 진행해주세요."),
                    bgcolor=ft.Colors.GREEN
                )
                page.snack_bar.open = True
                page.update()
                
            except Exception as ex:
                print(f"밴드 로그인 중 오류: {str(ex)}")
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"❌ 밴드 페이지 열기 실패: {str(ex)}"),
                    bgcolor=ft.Colors.RED
                )
                page.snack_bar.open = True
                page.update()
        
        # 별도 스레드에서 실행
        thread = threading.Thread(target=open_band)
        thread.daemon = True
        thread.start()
    
    def get_serial_status(self):
        """시리얼 인증 상태 정보 반환"""
        try:
            # 개발자 모드에서는 시리얼 인증을 건너뜀
            if getattr(self.serial_auth, "developer_mode", False):
                return {
                    "status": "💻 개발자 모드",
                    "message": "시리얼 인증이 비활성화되었습니다",
                    "color": ft.Colors.BLUE,
                    "days_remaining": 999
                }
            
            config = self.serial_auth.load_config()
            
            if not config.get("serial_number"):
                return {
                    "status": "❌ 미인증",
                    "message": "시리얼 번호가 등록되지 않았습니다",
                    "color": ft.Colors.RED,
                    "days_remaining": 0
                }
            
            # 시리얼 번호 검증으로 실제 만료일 확인
            serial_number = config.get("serial_number")
            valid, message, expiry_date = self.serial_auth.check_serial(serial_number)
            
            if not valid:
                return {
                    "status": "❌ 만료/오류",
                    "message": message,
                    "color": ft.Colors.RED,
                    "days_remaining": 0
                }
            
            # 실제 만료일이 있는 경우 사용
            if expiry_date:
                from datetime import datetime
                now = datetime.now()
                
                # 만료일이 datetime 객체가 아닌 경우 변환
                if isinstance(expiry_date, str):
                    try:
                        expiry_date = datetime.fromisoformat(expiry_date)
                    except:
                        try:
                            expiry_date = datetime.strptime(expiry_date, "%Y-%m-%d")
                        except:
                            # 파싱 실패 시 기본 30일 사용
                            from datetime import timedelta
                            last_validation = config.get("last_validation")
                            if last_validation:
                                last_check = datetime.fromisoformat(last_validation)
                                expiry_date = last_check + timedelta(days=30)
                            else:
                                expiry_date = now + timedelta(days=30)
                
                # 남은 일수 계산
                days_remaining = max(0, (expiry_date - now).days)
                
                if days_remaining <= 0:
                    return {
                        "status": "❌ 만료됨",
                        "message": "시리얼 번호가 만료되었습니다",
                        "color": ft.Colors.RED,
                        "days_remaining": 0
                    }
                elif days_remaining <= 7:
                    return {
                        "status": "⚠️ 곧 만료",
                        "message": f"시리얼 번호가 {days_remaining}일 후 만료됩니다",
                        "color": ft.Colors.ORANGE,
                        "days_remaining": days_remaining
                    }
                else:
                    return {
                        "status": "✅ 인증됨",
                        "message": f"시리얼 번호가 정상적으로 인증되었습니다",
                        "color": ft.Colors.GREEN,
                        "days_remaining": days_remaining
                    }
            else:
                # 만료일 정보가 없는 경우 기본 처리
                last_validation = config.get("last_validation")
                if not last_validation:
                    return {
                        "status": "⚠️ 검증 필요",
                        "message": "시리얼 번호 재검증이 필요합니다",
                        "color": ft.Colors.ORANGE,
                        "days_remaining": 0
                    }
                
                from datetime import datetime, timedelta
                try:
                    last_check = datetime.fromisoformat(last_validation)
                    # 기본 30일 사용
                    expiry_date = last_check + timedelta(days=30)
                    now = datetime.now()
                    days_remaining = max(0, (expiry_date - now).days)
                    
                    if days_remaining <= 0:
                        return {
                            "status": "❌ 만료됨",
                            "message": "시리얼 번호가 만료되었습니다",
                            "color": ft.Colors.RED,
                            "days_remaining": 0
                        }
                    elif days_remaining <= 7:
                        return {
                            "status": "⚠️ 곧 만료",
                            "message": f"시리얼 번호가 {days_remaining}일 후 만료됩니다",
                            "color": ft.Colors.ORANGE,
                            "days_remaining": days_remaining
                        }
                    else:
                        return {
                            "status": "✅ 인증됨",
                            "message": f"시리얼 번호가 정상적으로 인증되었습니다",
                            "color": ft.Colors.GREEN,
                            "days_remaining": days_remaining
                        }
                        
                except Exception as date_e:
                    print(f"날짜 파싱 오류: {date_e}")
                    return {
                        "status": "⚠️ 오류",
                        "message": "시리얼 상태 확인 중 오류가 발생했습니다",
                        "color": ft.Colors.ORANGE,
                        "days_remaining": 0
                    }
                
        except Exception as e:
            print(f"시리얼 상태 확인 오류: {e}")
            return {
                "status": "❌ 오류",
                "message": "시리얼 인증 시스템 오류",
                "color": ft.Colors.RED,
                "days_remaining": 0
            }



    def create_simple_login_button(self, page):
        """간단한 로그인 버튼 생성"""
        login_btn = ft.ElevatedButton(
            text="네이버 로그인",
            icon=ft.Icons.LOGIN,
            on_click=lambda e: self.simple_login(page, e),
            bgcolor=ft.Colors.BLUE,
            color=ft.Colors.WHITE,
            width=150,
            height=50
        )
        
        # 밴드 로그인 버튼 추가
        band_login_btn = ft.ElevatedButton(
            text="밴드 로그인",
            icon=ft.Icons.GROUPS,
            on_click=lambda e: self.band_login(page, e),
            bgcolor=ft.Colors.GREEN_700,
            color=ft.Colors.WHITE,
            width=150,
            height=50
        )
        
        # 타이머 제어 버튼들
        self.timer_start_btn = ft.ElevatedButton(
            text="블로그 시작",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=ft.Colors.GREEN_400,
            color=ft.Colors.WHITE,
            disabled=False,  # 기능 활성화
            width=120,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=25)
            ),
            on_click=lambda e: self.start_timer(page)
        )
        
        self.timer_stop_btn = ft.ElevatedButton(
            text="중지",
            icon=ft.Icons.STOP,
            bgcolor=ft.Colors.RED_400,
            color=ft.Colors.WHITE,
            disabled=True,  # 초기에는 비활성화
            width=90,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=25)
            ),
            on_click=lambda e: self.stop_timer(page)
        )
        
        return ft.Container(
            content=ft.Row([
                login_btn,
                band_login_btn,
                self.timer_start_btn,
                self.timer_stop_btn
            ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
            alignment=ft.alignment.center,
            padding=ft.padding.all(10)
        )

    def calculate_image_positions(self, content, mode):
        """본문 분석하여 이미지 삽입 위치 계산"""
        lines = content.split('\n')
        total_lines = len(lines)
        positions = []
        
        # 문단 끝과 문장 끝 위치 찾기
        sentence_end_markers = ['. ', '다. ', '요. ', '죠. ', '!', '?']
        key_points = []
        
        for i, line in enumerate(lines):
            # 빈 줄은 문단의 끝
            if not line.strip():
                if i > 0:  # 첫 줄이 아닌 경우만
                    key_points.append({
                        'line': i-1,
                        'weight': 1.0,
                        'type': 'paragraph_end'
                    })
                continue
            
            # 문장 끝 체크
            if any(line.strip().endswith(marker) for marker in sentence_end_markers):
                key_points.append({
                    'line': i,
                    'weight': 0.8,
                    'type': 'sentence_end'
                })
        
        # 모드별 위치 계산
        if mode == "random":
            num_sections = random.randint(3, 5)
            target_positions = [i * total_lines // num_sections for i in range(1, num_sections)]
        elif mode == "three_parts":
            target_positions = [total_lines // 3, (2 * total_lines) // 3]
        elif mode == "five_parts":
            target_positions = [
                total_lines // 5,
                (2 * total_lines) // 5,
                (3 * total_lines) // 5,
                (4 * total_lines) // 5
            ]
        else:  # "end" 모드
            return []
        
        # 각 목표 위치에 대해 가장 적절한 실제 위치 찾기
        for target in target_positions:
            # 가장 가까운 key_point 찾기
            closest_point = min(key_points, 
                key=lambda x: (abs(x['line'] - target), -x['weight']),
                default={'line': target}
            )
            if closest_point['line'] not in [p['line'] for p in positions]:
                positions.append(closest_point)
        
        # 위치를 라인 번호 순으로 정렬
        positions.sort(key=lambda x: x['line'])
        return positions

    def save_image_positions(self, content, mode):
        """이미지 삽입 위치 정보 저장"""
        try:
            positions = self.calculate_image_positions(content, mode)
            image_data = {
                'content_hash': hashlib.md5(content.encode()).hexdigest(),
                'mode': mode,
                'positions': positions,
                'total_lines': len(content.split('\n')),
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 설정 폴더가 없으면 생성
            os.makedirs(os.path.join(self.base_dir, 'config'), exist_ok=True)
            
            # 위치 정보 저장
            with open(os.path.join(self.base_dir, 'config/image_positions.json'), 'w', encoding='utf-8') as f:
                json.dump(image_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"이미지 위치 저장 중 오류 발생: {str(e)}")
            return False

    def load_image_positions(self, content):
        """저장된 이미지 위치 정보 로드"""
        try:
            if os.path.exists(os.path.join(self.base_dir, 'config/image_positions.json')):
                with open(os.path.join(self.base_dir, 'config/image_positions.json'), 'r', encoding='utf-8') as f:
                    image_data = json.load(f)
                    
                # 현재 컨텐츠의 해시값과 비교
                current_hash = hashlib.md5(content.encode()).hexdigest()
                if current_hash == image_data['content_hash']:
                    return image_data
            return None
        except Exception as e:
            print(f"이미지 위치 로드 중 오류 발생: {str(e)}")
            return None

    def load_topic_index(self):
        """저장된 주제 인덱스 로드 (플랫폼별)"""
        try:
            # 🆕 크로스 플랫폼: 사용자 데이터 폴더 사용
            app_data_dir = self._get_app_data_dir()
            index_path = os.path.join(app_data_dir, 'config', 'topic_index.json')
            
            # 파일이 없으면 레거시 경로 시도
            if not os.path.exists(index_path):
                legacy_path = os.path.join(self.base_dir, 'config', 'topic_index.json')
                if os.path.exists(legacy_path):
                    index_path = legacy_path
            
            if os.path.exists(index_path):
                with open(index_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 하위 호환성 유지: 기존 'current_index'가 있으면 'blog'에 할당
                    if 'current_index' in data:
                        self.topic_indices['blog'] = data.get('current_index', -1)
                    
                    # 플랫폼별 인덱스 업데이트
                    self.topic_indices.update({k: v for k, v in data.items() if k in self.topic_indices})
                    self._debug_log("H1", "blog_writer_app.load_topic_index", "loaded topic indices", self.topic_indices)
        except Exception as e:
            print(f"주제 인덱스 로드 중 오류 발생: {str(e)}")
            self.topic_indices = {'blog': -1, 'band': -1, 'cafe': -1}
            
    def save_topic_index(self):
        """현재 주제 인덱스 저장 (플랫폼별)"""
        try:
            # 🆕 크로스 플랫폼: 사용자 데이터 폴더 사용
            app_data_dir = self._get_app_data_dir()
            index_path = os.path.join(app_data_dir, 'config', 'topic_index.json')
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(self.topic_indices, f)
            self._debug_log("H1", "blog_writer_app.save_topic_index", "saved topic indices", self.topic_indices)
        except Exception as e:
            print(f"주제 인덱스 저장 중 오류 발생: {str(e)}")
    
    def start_timer(self, page):
        """타이머 시작"""
        print("🔘 타이머 시작 버튼이 클릭되었습니다.")
        
        if self.timer_running:
            print("⚠️ 타이머가 이미 실행 중입니다.")
            self.show_dialog(page, "⚠️ 알림", "타이머가 이미 실행 중입니다.", ft.Colors.ORANGE)
            return
            
        try:
            # 타이머 설정 로드
            timer_settings = self.load_timer_settings_data()
            if not timer_settings:
                print("❌ 타이머 설정이 없습니다.")
                self.show_dialog(
                    page, 
                    "❌ 설정 오류", 
                    "시간 설정을 먼저 저장해주세요!\n\n'시간 설정' 탭에서 운영 시간과 포스팅 간격을 설정하고 '설정 저장' 버튼을 클릭하세요.",
                    ft.Colors.RED
                )
                return
            
            print(f"📋 타이머 설정 로드됨: {timer_settings}")
            
            # 현재 시간이 운영 시간인지 확인
            if not self.is_operating_time(timer_settings):
                now = datetime.now()
                start_time = timer_settings.get('start_time', '09:00')
                end_time = timer_settings.get('end_time', '23:00')
                current_time = now.strftime('%H:%M')
                
                print(f"⏰ 운영 시간이 아닙니다. 현재: {current_time}, 운영시간: {start_time}~{end_time}")
                self.show_dialog(
                    page,
                    "⏰ 운영 시간 아님",
                    f"현재는 운영 시간이 아닙니다.\n\n현재 시간: {current_time}\n운영 시간: {start_time} ~ {end_time}\n\n운영 시간 내에 다시 시도하거나 '시간 설정' 탭에서 운영 시간을 조정하세요.",
                    ft.Colors.ORANGE
                )
                return
            
            # 일일 포스팅 제한 확인
            max_posts = int(timer_settings.get('max_posts', 20))
            if self.daily_post_count >= max_posts:
                print(f"📊 일일 포스팅 제한 도달: {self.daily_post_count}/{max_posts}")
                self.show_dialog(
                    page,
                    "📊 일일 제한 도달",
                    f"오늘의 포스팅 제한에 도달했습니다.\n\n오늘 포스팅: {self.daily_post_count}회\n일일 제한: {max_posts}회\n\n내일 다시 시도하거나 '시간 설정' 탭에서 일일 제한을 늘려주세요.",
                    ft.Colors.ORANGE
                )
                return
            
            # 타이머 시작
            print("✅ 모든 조건이 만족되어 타이머를 시작합니다.")
            self.timer_running = True
            self.timer_start_btn.disabled = True
            self.timer_stop_btn.disabled = False
            
            # 첫 포스팅은 즉시 실행 (다음 포스팅 시간을 현재 시간으로 설정)
            self.next_post_time = datetime.now()
            
            # UI에 즉시 포스팅 표시
            if hasattr(self, 'next_post_time_text_ref') and self.next_post_time_text_ref:
                self.next_post_time_text_ref.value = "다음 포스팅 시간: 즉시 실행"
                page.update()
            
            # 타이머 스레드 시작
            self.timer_thread = threading.Thread(target=self.timer_worker, args=(page, timer_settings))
            self.timer_thread.daemon = True
            self.timer_thread.start()
            
            # 성공 다이얼로그 표시
            self.show_dialog(
                page,
                "🚀 타이머 시작",
                "타이머가 성공적으로 시작되었습니다!\n\n첫 번째 포스팅을 즉시 실행하고, 이후 설정된 간격으로 자동 포스팅됩니다.",
                ft.Colors.GREEN
            )
            
            print("🚀 타이머 시작 완료")
            
            # 사용 현황 업데이트
            self.update_usage_display()
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 타이머 시작 중 오류: {error_msg}")
            self.show_dialog(
                page,
                "❌ 오류 발생",
                f"타이머 시작 중 오류가 발생했습니다:\n\n{error_msg}\n\n설정을 확인하고 다시 시도해주세요.",
                ft.Colors.RED
            )
    
    def show_dialog(self, page, title, message, color):
        """사용자에게 다이얼로그로 메시지 표시"""
        try:
            print(f"🔔 다이얼로그 표시 시도: {title}")
            
            def close_dialog(e):
                try:
                    dialog.open = False
                    page.update()
                    print("✅ 다이얼로그 닫기 완료")
                except Exception as close_e:
                    print(f"❌ 다이얼로그 닫기 중 오류: {close_e}")
            
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(title, weight=ft.FontWeight.BOLD, color=color, size=16),
                content=ft.Text(message, size=14, selectable=True),
                actions=[
                    ft.TextButton(
                        "확인", 
                        on_click=close_dialog,
                        style=ft.ButtonStyle(
                            color=ft.Colors.WHITE,
                            bgcolor=color
                        )
                    )
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            # 기존 다이얼로그가 있으면 닫기
            if hasattr(page, 'dialog') and page.dialog:
                try:
                    page.dialog.open = False
                except:
                    pass
            
            page.dialog = dialog
            dialog.open = True
            page.update()
            
            print(f"✅ 다이얼로그 표시 완료: {title}")
            
        except Exception as e:
            print(f"❌ 다이얼로그 표시 중 오류: {str(e)}")
            # 다이얼로그 실패 시 스낵바로 대체
            try:
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"{title}: {message}"),
                    bgcolor=color,
                    duration=5000
                )
                page.snack_bar.open = True
                page.update()
                print("✅ 스낵바로 대체 표시 완료")
            except Exception as snack_e:
                print(f"❌ 스낵바 표시도 실패: {snack_e}")
    
    def stop_timer(self, page):
        """타이머 중지"""
        print("🔘 타이머 중지 버튼이 클릭되었습니다.")
        
        try:
            if not self.timer_running:
                print("⚠️ 타이머가 실행 중이지 않습니다.")
                self.show_dialog(
                    page,
                    "⚠️ 알림",
                    "타이머가 현재 실행 중이지 않습니다.",
                    ft.Colors.ORANGE
                )
                return
            
            self.timer_running = False
            self.timer_start_btn.disabled = False
            self.timer_stop_btn.disabled = True
            self.next_post_time = None
            
            # UI에 타이머 중지 상태 표시
            if hasattr(self, 'next_post_time_text_ref') and self.next_post_time_text_ref:
                self.next_post_time_text_ref.value = "다음 포스팅 시간: --:--:--"
            page.update()
            
            # 성공 다이얼로그 표시
            self.show_dialog(
                page,
                "⏹️ 타이머 중지",
                "타이머가 성공적으로 중지되었습니다.\n\n자동 포스팅이 중단되었습니다.",
                ft.Colors.BLUE
            )
            
            print("⏹️ 타이머 중지 완료")
            
            # 사용 현황 업데이트
            self.update_usage_display()
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 타이머 중지 중 오류: {error_msg}")
            self.show_dialog(
                page,
                "❌ 오류 발생",
                f"타이머 중지 중 오류가 발생했습니다:\n\n{error_msg}",
                ft.Colors.RED
            )
    
    def load_timer_settings_data(self):
        """타이머 설정 데이터 로드"""
        try:
            timer_file = os.path.join(self.base_dir, 'config/timer_settings.json')
            if os.path.exists(timer_file):
                with open(timer_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"타이머 설정 로드 중 오류: {str(e)}")
            return None
    
    def is_operating_time(self, timer_settings):
        """현재 시간이 운영 시간인지 확인"""
        try:
            now = datetime.now()
            start_time_str = timer_settings.get('start_time', '09:00')
            end_time_str = timer_settings.get('end_time', '23:00')
            
            start_hour, start_min = map(int, start_time_str.split(':'))
            end_hour, end_min = map(int, end_time_str.split(':'))
            
            start_time = now.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
            end_time = now.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)
            
            return start_time <= now <= end_time
        except Exception as e:
            print(f"운영 시간 확인 중 오류: {str(e)}")
            return False
    
    def calculate_next_post_time(self, timer_settings):
        """다음 포스팅 시간 계산"""
        try:
            min_interval = int(timer_settings.get('min_interval', 15))
            max_interval = int(timer_settings.get('max_interval', 20))
            
            # 랜덤 간격 계산 (분 단위)
            random_interval = random.randint(min_interval, max_interval)
            
            # 다음 포스팅 시간 설정
            self.next_post_time = datetime.now() + timedelta(minutes=random_interval)
            
            # UI 업데이트
            if hasattr(self, 'next_post_time_text_ref') and self.next_post_time_text_ref and self.page_ref:
                self.next_post_time_text_ref.value = f"다음 포스팅 시간: {self.next_post_time.strftime('%H:%M:%S')}"
                self.page_ref.update()
            
        except Exception as e:
            print(f"다음 포스팅 시간 계산 중 오류: {str(e)}")
            # 기본값으로 15분 후 설정
            self.next_post_time = datetime.now() + timedelta(minutes=15)
            
            # UI 업데이트 (기본값)
            if hasattr(self, 'next_post_time_text_ref') and self.next_post_time_text_ref and self.page_ref:
                self.next_post_time_text_ref.value = f"다음 포스팅 시간: {self.next_post_time.strftime('%H:%M:%S')}"
                self.page_ref.update()
    
    def timer_worker(self, page, timer_settings):
        """타이머 워커 스레드"""
        last_date = datetime.now().date()
        last_settings_check = datetime.now()
        
        while self.timer_running:
            try:
                now = datetime.now()
                current_date = now.date()
                
                # 🔄 30초마다 설정 파일 다시 읽기 (실시간 반영)
                if (now - last_settings_check).total_seconds() >= 30:
                    try:
                        updated_settings = self.load_timer_settings_data()
                        if updated_settings:
                            # 설정이 실제로 변경되었는지 확인
                            settings_changed = False
                            for key in ['min_interval', 'max_interval', 'start_time', 'end_time', 'max_posts']:
                                if str(timer_settings.get(key, '')) != str(updated_settings.get(key, '')):
                                    settings_changed = True
                                    break
                            
                            if settings_changed:
                                timer_settings = updated_settings
                                print("🔄 타이머 설정이 변경되어 업데이트했습니다.")
                                
                                # 다음 포스팅 시간 재계산
                                self.calculate_next_post_time(timer_settings)
                                next_time_str = self.next_post_time.strftime('%H:%M:%S') if self.next_post_time else '계산 중...'
                                print(f"🎯 새로운 다음 포스팅 시간: {next_time_str}")
                                
                                # UI에 다이얼로그 알림 표시 (별도 스레드에서 실행)
                                if self.page_ref:
                                    try:
                                        # UI 스레드에서 안전하게 실행
                                        import threading
                                        def show_update_dialog():
                                            try:
                                                self.show_dialog(
                                                    self.page_ref,
                                                    "🔄 설정 업데이트",
                                                    f"타이머 설정이 변경되어 업데이트되었습니다!\n\n📊 오늘의 포스팅 수: {self.daily_post_count}회\n⏰ 새로운 다음 포스팅 시간: {next_time_str}\n\n새로운 설정으로 타이머가 계속 실행됩니다.",
                                                    ft.Colors.BLUE
                                                )
                                            except Exception as dialog_e:
                                                print(f"❌ 설정 업데이트 다이얼로그 표시 실패: {dialog_e}")
                                        
                                        # 메인 스레드에서 실행
                                        threading.Timer(0.1, show_update_dialog).start()
                                        
                                    except Exception as e:
                                        print(f"❌ 설정 업데이트 알림 처리 중 오류: {e}")
                        
                        last_settings_check = now
                    except Exception as e:
                        print(f"설정 업데이트 중 오류: {str(e)}")
                
                # 날짜가 바뀌면 일일 포스팅 카운트 리셋
                if current_date != last_date:
                    self.daily_post_count = 0
                    last_date = current_date
                    print(f"새로운 날짜: {current_date}, 일일 포스팅 카운트 리셋")
                
                # 운영 시간 확인
                if not self.is_operating_time(timer_settings):
                    current_time = now.strftime('%H:%M')
                    start_time = timer_settings.get('start_time', '09:00')
                    end_time = timer_settings.get('end_time', '23:00')
                    
                    print(f"운영 시간이 아니므로 타이머 대기 중... (현재: {current_time}, 운영시간: {start_time}~{end_time})")
                    
                    # 5분마다 한번씩만 다이얼로그 표시 (너무 자주 표시되지 않도록)
                    if not hasattr(self, '_last_operating_time_alert') or (now - self._last_operating_time_alert).total_seconds() >= 300:
                        self._last_operating_time_alert = now
                        if self.page_ref:
                            try:
                                # UI 스레드에서 안전하게 실행
                                import threading
                                def show_operating_time_dialog():
                                    try:
                                        self.show_dialog(
                                            self.page_ref,
                                            "⏰ 운영 시간 대기 중",
                                            f"현재는 운영 시간이 아닙니다.\n\n현재 시간: {current_time}\n운영 시간: {start_time} ~ {end_time}\n\n운영 시간까지 대기합니다.",
                                            ft.Colors.BLUE
                                        )
                                    except Exception as dialog_e:
                                        print(f"❌ 운영 시간 다이얼로그 표시 실패: {dialog_e}")
                                
                                # 메인 스레드에서 실행
                                threading.Timer(0.1, show_operating_time_dialog).start()
                                
                            except Exception as e:
                                print(f"❌ 운영 시간 알림 처리 중 오류: {e}")
                    
                    time.sleep(60)  # 1분마다 확인
                    continue
                
                # 일일 포스팅 제한 확인
                max_posts = int(timer_settings.get('max_posts', 20))
                if self.daily_post_count >= max_posts:
                    print(f"일일 포스팅 제한 도달, 타이머 대기 중... ({self.daily_post_count}/{max_posts})")
                    
                    # 10분마다 한번씩만 다이얼로그 표시 (너무 자주 표시되지 않도록)
                    if not hasattr(self, '_last_limit_alert') or (now - self._last_limit_alert).total_seconds() >= 600:
                        self._last_limit_alert = now
                        if self.page_ref:
                            try:
                                # UI 스레드에서 안전하게 실행
                                import threading
                                def show_limit_dialog():
                                    try:
                                        self.show_dialog(
                                            self.page_ref,
                                            "📊 일일 제한 도달",
                                            f"오늘의 포스팅 제한에 도달했습니다.\n\n오늘 포스팅: {self.daily_post_count}회\n일일 제한: {max_posts}회\n\n내일까지 대기하거나 설정을 변경하세요.",
                                            ft.Colors.ORANGE
                                        )
                                    except Exception as dialog_e:
                                        print(f"❌ 일일 제한 다이얼로그 표시 실패: {dialog_e}")
                                
                                # 메인 스레드에서 실행
                                threading.Timer(0.1, show_limit_dialog).start()
                                
                            except Exception as e:
                                print(f"❌ 일일 제한 알림 처리 중 오류: {e}")
                    
                    time.sleep(60)  # 1분마다 확인
                    continue
                
                # 포스팅 시간 확인
                if self.next_post_time and now >= self.next_post_time:
                    print(f"포스팅 시간 도달: {now.strftime('%H:%M:%S')}")
                    
                    # 자동 포스팅 실행
                    success = self.auto_post(page)
                    
                    if success:
                        self.daily_post_count += 1
                        success_message = f"✅ 자동 포스팅 완료: 오늘의 포스팅 수: {self.daily_post_count}"
                        print(success_message)
                        
                        # UI 다이얼로그로 성공 알림 (별도 스레드에서 실행)
                        if self.page_ref:
                            try:
                                # 다음 포스팅 시간 계산 후 다이얼로그 표시
                                self.calculate_next_post_time(timer_settings)
                                next_time_str = self.next_post_time.strftime('%H:%M:%S') if self.next_post_time else '계산 중...'
                                
                                # UI 스레드에서 안전하게 실행
                                import threading
                                def show_success_dialog():
                                    try:
                                        self.show_dialog(
                                            self.page_ref,
                                            "🎉 자동 포스팅 성공!",
                                            f"포스팅이 성공적으로 완료되었습니다.\n\n📊 오늘의 포스팅 수: {self.daily_post_count}회\n⏰ 다음 포스팅 시간: {next_time_str}",
                                            ft.Colors.GREEN
                                        )
                                    except Exception as dialog_e:
                                        print(f"❌ 성공 다이얼로그 표시 실패: {dialog_e}")
                                
                                # 메인 스레드에서 실행
                                threading.Timer(0.1, show_success_dialog).start()
                                
                            except Exception as e:
                                print(f"❌ 성공 알림 처리 중 오류: {e}")
                        
                        # 다음 포스팅 시간 계산
                        self.calculate_next_post_time(timer_settings)
                        print(f"다음 포스팅 시간: {self.next_post_time.strftime('%H:%M:%S')}")
                    else:
                        failure_message = "❌ 자동 포스팅 실패 (업로드 실패), 포스팅 수 카운트 안함, 정상 간격으로 다음 포스팅 예약"
                        print(failure_message)
                        
                        # 다음 포스팅 시간을 정상 랜덤 간격으로 계산
                        self.calculate_next_post_time(timer_settings)
                        
                        # UI 다이얼로그로 실패 알림 (별도 스레드에서 실행)
                        if self.page_ref:
                            try:
                                next_time_str = self.next_post_time.strftime('%H:%M:%S') if self.next_post_time else '계산 중...'
                                
                                # UI 스레드에서 안전하게 실행
                                import threading
                                def show_failure_dialog():
                                    try:
                                        self.show_dialog(
                                            self.page_ref,
                                            "⚠️ 자동 포스팅 실패",
                                            f"포스팅 업로드에 실패했습니다.\n\n📊 오늘의 포스팅 수: {self.daily_post_count}회 (변경 없음)\n⏰ 다음 포스팅 시간: {next_time_str}\n\n브라우저 로그인 상태를 확인해주세요.",
                                            ft.Colors.ORANGE
                                        )
                                    except Exception as dialog_e:
                                        print(f"❌ 실패 다이얼로그 표시 실패: {dialog_e}")
                                
                                # 메인 스레드에서 실행
                                threading.Timer(0.1, show_failure_dialog).start()
                                
                            except Exception as e:
                                print(f"❌ 실패 알림 처리 중 오류: {e}")
                        
                        print(f"다음 포스팅 시간: {self.next_post_time.strftime('%H:%M:%S')}")
                
                # 1초마다 확인
                time.sleep(1)
                
            except Exception as e:
                print(f"타이머 워커 중 오류: {str(e)}")
                time.sleep(60)  # 오류 발생 시 1분 대기
    
    def auto_post(self, page):
        """자동 포스팅 실행 - 전송 버튼만 클릭"""
        try:
            print("🔘 타이머 자동 포스팅: 전송 버튼 클릭!")
            
            # UI에서 전송 버튼 클릭 시뮬레이션
            if self.send_message_func:
                # send_message 함수 호출 (전송 버튼과 동일한 동작)
                self.send_message_func(None)
                
                print("✅ 전송 버튼 클릭 완료! 이후 자동 처리됩니다.")
                
                # 스낵바로 알림
                if self.page_ref:
                    self.page_ref.snack_bar = ft.SnackBar(
                        content=ft.Text("✅ 자동 포스팅이 시작되었습니다!"),
                        bgcolor=ft.Colors.GREEN_400
                    )
                    self.page_ref.snack_bar.open = True
                    self.page_ref.update()
                
                return True
            return False
        except Exception as e:
            print(f"❌ 자동 포스팅 실행 중 오류: {str(e)}")
            return False

    def handle_scheduled_task(self, task):
        """스케줄러에 의해 트리거된 작업 처리"""
        print(f"🎯 예약된 작업 실행: {task.platform} - {task.task_type}")
        
        # 🔒 브라우저 락 획득 (다른 작업이 끝날 때까지 대기)
        if self.is_browser_busy:
            print(f"⏳ 다른 작업이 진행 중입니다. 완료까지 대기...")
        
        self.browser_lock.acquire()
        self.is_browser_busy = True
        self.update_activity_time()  # 세션 유지 타이머 리셋
        print(f"🔓 락 획득 완료 - 작업 시작: {task.platform}")
        
        # 기본 상태는 실패로 설정 (성공 시 변경)
        task.last_status = 'failed'
        
        try:
            if task.platform == 'blog' and task.task_type == 'reservation_batch':
                # 블로그 예약 일괄 등록 (새 기능)
                start_time = time.time()
                times = task.data.get('times', [])
                per_post = task.data.get('per_post_minutes', 3)
                
                print(f"📦 [블로그 일괄 예약] 시작: 총 {len(times)}건 ({', '.join(times)})")
                
                if not times:
                    print("⚠️ 예약 시간이 없습니다.")
                    return
                
                success_cnt = 0
                
                for i, res_time in enumerate(times):
                    # 스케줄러 중지 체크
                    if not self.scheduler or not self.scheduler.running:
                        print(f"  ⛔ 스케줄러가 중지되었습니다. 남은 작업 취소.")
                        break
                    
                    # 🆕 일시정지 체크 - 일시정지 상태면 대기
                    while self.scheduler and self.scheduler.paused and self.scheduler.running:
                        print(f"  ⏸️ 일시정지 중... ({i+1}/{len(times)}) 재개를 기다립니다.")
                        time.sleep(3)
                    
                    # 일시정지 해제 후 다시 running 체크
                    if not self.scheduler or not self.scheduler.running:
                        print(f"  ⛔ 스케줄러가 중지되었습니다. 남은 작업 취소.")
                        break
                    
                    print(f"  👉 블로그 예약 {i+1}/{len(times)}: {res_time} 처리 중...")
                    
                    try:
                        # 1. 주제 선택 및 내용 생성
                        topic = self.select_sequential_topic('blog') or "일상 이야기"
                        result = self.gpt_handler.generate_platform_content(topic, platform='blog')
                        
                        if not result or not result.get('content'):
                            print(f"    ❌ 내용 생성 실패 ({res_time})")
                            continue
                        
                        # 2. 기존 브라우저 사용 또는 생성
                        driver = self.get_or_create_driver()
                        
                        # 3. NaverBlogAutomation 사용하여 포스트 작성 (단일 포스팅과 동일하게)
                        from naver_blog_auto import NaverBlogAutomation
                        from naver_blog_post_finisher import NaverBlogPostFinisher
                        
                        # --- 이미지 폴더 선택: 포스트 단위로 한 폴더만 고정 사용 ---
                        custom_images_folder = None
                        images_available = False
                        try:
                            folder_path = self.get_next_image_folder()
                            if folder_path and os.path.exists(folder_path):
                                valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
                                files = [
                                    f for f in os.listdir(folder_path)
                                    if os.path.splitext(f)[1].lower() in valid_exts
                                ]
                                if files:
                                    custom_images_folder = folder_path
                                    images_available = True
                                    print(f"    🖼️ 커스텀 이미지 폴더 사용: {folder_path}")
                        except Exception as img_folder_err:
                            print(f"    ⚠️ 이미지 폴더 선택 오류: {img_folder_err}")
                        
                        # 자동화 인스턴스 생성 (이미지 삽입 활성화)
                        blog_auto = NaverBlogAutomation(
                            auto_mode=images_available,  # 이미지가 있으면 자동 삽입
                            image_insert_mode="random",
                            use_stickers=False,
                            custom_images_folder=custom_images_folder
                        )
                        
                        # 기본 디렉토리 및 설정
                        blog_auto.base_dir = self.base_dir
                        blog_auto.settings = blog_auto.load_settings()
                        blog_auto.driver = driver  # 기존 드라이버 재사용
                        
                        # 이미지 삽입 핸들러 수동 초기화
                        if images_available and blog_auto.driver:
                            print("    🖼️ 이미지 삽입 핸들러 초기화 중...")
                            from naver_blog_auto_image import NaverBlogImageInserter
                            
                            fallback_folder = custom_images_folder if custom_images_folder else getattr(blog_auto, 'default_images_folder', None)
                            blog_auto.image_inserter = NaverBlogImageInserter(
                                driver=blog_auto.driver,
                                images_folder=getattr(blog_auto, 'images_folder', None),
                                insert_mode=blog_auto.image_insert_mode,
                                fallback_folder=fallback_folder
                            )
                            print("    ✅ 이미지 삽입 핸들러 초기화 완료")
                        else:
                            blog_auto.image_inserter = None
                        
                        # 블로그 에디터 URL로 이동
                        naver_id = self.settings.get('naver_id', '')
                        
                        if not naver_id:
                            # 설정에 없으면 현재 블로그에서 추출
                            try:
                                driver.get('https://blog.naver.com/MyBlog.naver')
                                time.sleep(2)
                                current_url = driver.current_url
                                if 'blog.naver.com/' in current_url:
                                    parts = current_url.split('blog.naver.com/')
                                    if len(parts) > 1:
                                        naver_id = parts[1].split('?')[0].split('/')[0]
                                        print(f"    📌 블로그 ID 자동 감지: {naver_id}")
                            except:
                                pass
                        
                        if not naver_id:
                            print(f"    ❌ 네이버 블로그 ID를 찾을 수 없습니다.")
                            continue
                        
                        # 제목, 본문, 태그 준비
                        title = result.get('title', topic)
                        content = result.get('content', '')
                        
                        # 태그: GPT 태그 + 사용자 설정 태그 병합
                        gpt_tags = result.get('tags', [])
                        user_tags = []
                        try:
                            user_tags_str = self.settings.get('blog_tags', '')
                            if user_tags_str:
                                user_tags = [tag.strip() for tag in user_tags_str.split(',') if tag.strip()]
                        except:
                            pass
                        tags = list(set(gpt_tags + user_tags))  # 중복 제거
                        
                        # 글 작성 (이미지 포함) - write_post가 푸터+태그 추가까지 처리
                        # 예약 모드: 최종 발행 버튼 클릭 스킵 (나중에 예약 설정 후 발행)
                        try:
                            blog_auto.skip_final_publish = True  # 예약 모드 플래그 설정
                            success = blog_auto.write_post(title, content, tags)
                            if success:
                                print(f"    ✅ 글 작성 완료")
                            else:
                                print(f"    ❌ 글 작성 실패")
                                continue
                        except Exception as write_err:
                            print(f"    ❌ 글 작성 실패: {write_err}")
                            continue
                        
                        # 예약 모드: write_post()가 이미 푸터+태그+발행 처리했으므로 건너뜀
                        # 발행 옵션 패널에서 예약 시간만 설정
                        finisher = NaverBlogPostFinisher(driver, self.settings)
                        
                        # 6. 예약 발행 설정
                        reservation_success = finisher.set_reservation_time(res_time)
                        publish_success = False  # 초기화
                        
                        if reservation_success:
                            # 7. 발행 버튼 클릭
                            publish_success = finisher.click_final_publish_button()
                            
                            if publish_success:
                                success_cnt += 1
                                print(f"    ✅ 블로그 예약 성공: {res_time}")
                            else:
                                print(f"    ❌ 발행 버튼 클릭 실패: {res_time}")
                        else:
                            print(f"    ❌ 예약 시간 설정 실패: {res_time}")
                        
                        # 로그 기록
                        self.add_model_usage_log(
                            topic=topic,
                            model=result.get('model', 'gpt-4o-mini'),
                            status="성공" if (reservation_success and publish_success) else "실패",
                            reason=f"블로그 예약({res_time})",
                            target="네이버 블로그",
                            duration_sec=0
                        )
                        
                        # 다음 작업 전 대기
                        if i < len(times) - 1:
                            wait_seconds = per_post * 60  # 분을 초로 변환
                            # 표시 형식 (초 또는 분 단위)
                            if wait_seconds < 60:
                                wait_display = f"{int(wait_seconds)}초"
                            elif wait_seconds % 60 == 0:
                                wait_display = f"{int(wait_seconds // 60)}분"
                            else:
                                wait_display = f"{int(wait_seconds // 60)}분 {int(wait_seconds % 60)}초"
                            print(f"    ⏳ 다음 작업까지 {wait_display} 대기...")
                            time.sleep(wait_seconds)
                            
                    except Exception as post_err:
                        print(f"    ❌ 블로그 예약 중 오류: {post_err}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                total_duration = time.time() - start_time
                print(f"🏁 [블로그 일괄 예약] 완료. 성공: {success_cnt}/{len(times)}, 소요: {total_duration:.1f}초")
                
                if success_cnt > 0:
                    task.last_status = 'success'
                else:
                    task.last_status = 'failed'
                
                # 실패 시 UI 알림
                if success_cnt < len(times) and self.page_ref:
                    try:
                        import threading
                        def show_blog_batch_result():
                            try:
                                if success_cnt == 0:
                                    title = "❌ 블로그 일괄 예약 전체 실패"
                                    color = ft.Colors.RED
                                else:
                                    title = "⚠️ 블로그 일괄 예약 일부 실패"
                                    color = ft.Colors.ORANGE
                                
                                msg = f"블로그 일괄 예약 결과\\n\\n📊 성공: {success_cnt}/{len(times)}건\\n⏱️ 소요: {total_duration:.1f}초"
                                self.show_dialog(self.page_ref, title, msg, color)
                            except:
                                pass
                        threading.Timer(0.1, show_blog_batch_result).start()
                    except:
                        pass
                
                self.scheduler.save_tasks()
                self.update_scheduler_ui()
                
            elif task.platform == 'blog':
                # 블로그 포스팅 로직
                # reservation_time이 있으면 예약 발행, 없으면 즉시 발행
                reservation_time = task.data.get('reservation_time') if task.data else None
                
                if reservation_time:
                    # 예약 발행 모드
                    print(f"📝 [블로그 예약 포스팅] 시작: 예약 시간 {reservation_time}")
                    
                    from naver_blog_auto import NaverBlogAutomation
                    from naver_blog_post_finisher import NaverBlogPostFinisher
                    
                    try:
                        # 주제 및 내용 생성
                        topic = self.select_sequential_topic('blog') or "일상 이야기"
                        result = self.gpt_handler.generate_platform_content(topic, platform='blog')
                        
                        if not result or not result.get('content'):
                            print(f"    ❌ 내용 생성 실패")
                            task.last_status = 'failed'
                            return
                        
                        driver = self.get_or_create_driver()
                        
                        # 이미지 폴더 선택
                        custom_images_folder = None
                        images_available = False
                        try:
                            folder_path = self.get_next_image_folder()
                            if folder_path and os.path.exists(folder_path):
                                valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
                                files = [f for f in os.listdir(folder_path) if os.path.splitext(f)[1].lower() in valid_exts]
                                if files:
                                    custom_images_folder = folder_path
                                    images_available = True
                                    print(f"    🖼️ 이미지 폴더: {folder_path}")
                        except Exception as img_err:
                            print(f"    ⚠️ 이미지 폴더 오류: {img_err}")
                        
                        # 블로그 자동화 객체 생성
                        blog_auto = NaverBlogAutomation(
                            auto_mode=images_available,
                            image_insert_mode="random",
                            use_stickers=False,
                            custom_images_folder=custom_images_folder
                        )
                        
                        blog_auto.base_dir = self.base_dir
                        blog_auto.settings = blog_auto.load_settings()
                        blog_auto.driver = driver
                        
                        # 이미지 핸들러 초기화
                        if images_available:
                            from naver_blog_auto_image import NaverBlogImageInserter
                            fallback_folder = custom_images_folder if custom_images_folder else getattr(blog_auto, 'default_images_folder', None)
                            blog_auto.image_inserter = NaverBlogImageInserter(
                                driver=blog_auto.driver,
                                images_folder=getattr(blog_auto, 'images_folder', None),
                                insert_mode=blog_auto.image_insert_mode,
                                fallback_folder=fallback_folder
                            )
                        else:
                            blog_auto.image_inserter = None
                        
                        # 네이버 ID 확인
                        naver_id = self.settings.get('naver_id', '')
                        if not naver_id:
                            try:
                                driver.get('https://blog.naver.com/MyBlog.naver')
                                time.sleep(2)
                                current_url = driver.current_url
                                if 'blog.naver.com/' in current_url:
                                    parts = current_url.split('blog.naver.com/')
                                    if len(parts) > 1:
                                        naver_id = parts[1].split('?')[0].split('/')[0]
                            except:
                                pass
                        
                        if not naver_id:
                            print(f"    ❌ 네이버 블로그 ID를 찾을 수 없습니다.")
                            task.last_status = 'failed'
                            return
                        
                        # 제목, 본문, 태그 준비
                        title = result.get('title', topic)
                        content = result.get('content', '')
                        gpt_tags = result.get('tags', [])
                        user_tags = []
                        try:
                            user_tags_str = self.settings.get('blog_tags', '')
                            if user_tags_str:
                                user_tags = [tag.strip() for tag in user_tags_str.split(',') if tag.strip()]
                        except:
                            pass
                        tags = list(set(gpt_tags + user_tags))
                        
                        # 글 작성 (write_post가 푸터+태그까지 처리)
                        # 예약 모드: 최종 발행 버튼 클릭 스킵 (나중에 예약 설정 후 발행)
                        blog_auto.skip_final_publish = True  # 예약 모드 플래그 설정
                        success = blog_auto.write_post(title, content, tags)
                        if not success:
                            print(f"    ❌ 글 작성 실패")
                            task.last_status = 'failed'
                            return
                        
                        print(f"    ✅ 글 작성 완료")
                        
                        # 예약 모드: write_post()가 이미 푸터+태그 처리함
                        # 발행 옵션 패널에서 예약 시간만 설정
                        finisher = NaverBlogPostFinisher(driver, self.settings)
                        
                        # 예약 시간 설정
                        reservation_success = finisher.set_reservation_time(reservation_time)
                        publish_success = False  # 초기화
                        
                        if reservation_success:
                            publish_success = finisher.click_final_publish_button()
                            
                            if publish_success:
                                print(f"    ✅ 블로그 예약 성공: {reservation_time}")
                                task.last_status = 'success'
                            else:
                                print(f"    ❌ 발행 버튼 클릭 실패")
                                task.last_status = 'failed'
                        else:
                            print(f"    ❌ 예약 시간 설정 실패")
                            task.last_status = 'failed'
                        
                        # 로그 기록
                        self.add_model_usage_log(
                            topic=topic,
                            model=result.get('model', 'gpt-4o-mini'),
                            status="성공" if (reservation_success and publish_success) else "실패",
                            reason=f"블로그 예약({reservation_time})",
                            target="네이버 블로그",
                            duration_sec=0
                        )
                        
                    except Exception as e:
                        print(f"    ❌ 블로그 예약 중 오류: {e}")
                        import traceback
                        traceback.print_exc()
                        task.last_status = 'failed'
                else:
                    # 즉시 발행 모드 (기존 로직)
                    if self.page_ref:
                        if self.auto_post(self.page_ref):
                            task.last_status = 'success'
            
            elif task.platform == 'band' and task.task_type == 'reservation_batch':
                 # 밴드 예약 일괄 등록
                 start_time = time.time()
                 times = task.data.get('times', [])
                 types = task.data.get('types', ['regular'] * len(times))  # 유형 목록 (기본값: regular)
                 band_url = task.data.get('band_url', self.settings.get('band_url', ''))
                 
                 print(f"📦 [밴드 일괄 예약] 시작: 총 {len(times)}건 ({', '.join(times)})")
                 
                 if not times:
                     print("⚠️ 예약 시간이 없습니다.")
                     return
                 
                 band_auto = NaverBandAutomation(self.get_or_create_driver())
                 
                 success_cnt = 0
                 
                 for i, res_time in enumerate(times):
                     # 🆕 스케줄러 중지 체크
                     if not self.scheduler or not self.scheduler.running:
                         print(f"  ⛔ 스케줄러가 중지되었습니다. 남은 작업 취소.")
                         break
                     
                     # 🆕 일시정지 체크 - 일시정지 상태면 대기
                     while self.scheduler and self.scheduler.paused and self.scheduler.running:
                         print(f"  ⏸️ 일시정지 중... ({i+1}/{len(times)}) 재개를 기다립니다.")
                         time.sleep(3)
                     
                     # 일시정지 해제 후 다시 running 체크
                     if not self.scheduler or not self.scheduler.running:
                         print(f"  ⛔ 스케줄러가 중지되었습니다. 남은 작업 취소.")
                         break
                     
                     task_type = types[i] if i < len(types) else 'regular'
                     print(f"  👉 예약 작업 {i+1}/{len(times)}: {res_time} (유형: {task_type}) 처리 중...")
                     
                     # 주제 및 내용 생성 (유형에 따라 다른 스타일)
                     topic = self.select_sequential_topic('band') or "체육관 일상"
                     result = self.gpt_handler.generate_platform_content(topic, platform='band', task_type=task_type)
                     
                     if not result or not result.get('content'):
                         print(f"    ❌ 내용 생성 실패 ({res_time})")
                         continue
                         
                     # 이미지 준비 (설정에 따름)
                     images = []
                     if self.settings.get('band_auto_image', self.settings.get('auto_image', True)):
                        images = self.get_images_to_upload(platform='band')

                     # 예약 포스팅 실행 (reservation_time 전달)
                     res_success = band_auto.post_to_band(
                         band_url, 
                         result.get('content', ''), 
                         image_paths=images, 
                         reservation_time=res_time
                     )
                     
                     if res_success:
                         success_cnt += 1
                         print(f"    ✅ 예약 성공: {res_time}")
                     else:
                         print(f"    ❌ 예약 실패: {res_time}")
                         
                     # 로그 기록
                     self.add_model_usage_log(
                        topic=topic,
                        model=result.get('model', '-'),
                        status="성공" if res_success else "실패",
                        reason=f"밴드 예약({res_time})",
                        target="네이버 밴드",
                        duration_sec=0
                     )
                     
                     # 작업 간 딜레이
                     if i < len(times) - 1:
                         time.sleep(5)
                 
                 total_duration = time.time() - start_time
                 print(f"🏁 [밴드 일괄 예약] 완료. 성공: {success_cnt}/{len(times)}, 소요: {total_duration:.1f}초")
                 
                 if success_cnt > 0:
                     task.last_status = 'success'
                 else:
                     task.last_status = 'failed'
                 
                 # 일부 또는 전체 실패 시 UI 알림
                 failed_cnt = len(times) - success_cnt
                 if failed_cnt > 0 and self.page_ref:
                     try:
                         import threading
                         def show_batch_result_dialog():
                             try:
                                 if success_cnt == 0:
                                     title = "❌ 밴드 일괄 예약 전체 실패"
                                     color = ft.Colors.RED
                                     msg = f"밴드 일괄 예약이 모두 실패했습니다.\n\n📊 결과: 성공 0/{len(times)}건\n⏱️ 소요 시간: {total_duration:.1f}초\n\n다음 스케줄은 정상 진행됩니다."
                                 else:
                                     title = "⚠️ 밴드 일괄 예약 일부 실패"
                                     color = ft.Colors.ORANGE
                                     msg = f"밴드 일괄 예약 중 일부가 실패했습니다.\n\n📊 결과: 성공 {success_cnt}/{len(times)}건\n❌ 실패: {failed_cnt}건\n⏱️ 소요 시간: {total_duration:.1f}초"
                                 
                                 self.show_dialog(self.page_ref, title, msg, color)
                             except Exception as dialog_e:
                                 print(f"❌ 일괄 예약 결과 다이얼로그 표시 실패: {dialog_e}")
                         
                         threading.Timer(0.1, show_batch_result_dialog).start()
                     except Exception as e:
                         print(f"❌ 일괄 예약 결과 알림 처리 중 오류: {e}")
                 
                 self.scheduler.save_tasks()
                 self.update_scheduler_ui()

            elif task.platform == 'band':
                # 밴드 포스팅 (단일)
                start_time = time.time()
                band_auto = NaverBandAutomation(self.get_or_create_driver())
                band_url = task.data.get('band_url', self.settings.get('band_url', ''))
                
                # 예약 시간 확인
                reservation_time = task.data.get('reservation_time')
                
                # 내용 생성
                topic = self.select_sequential_topic('band') or "체육관 소개 및 일상"
                print(f"🤖 [밴드] '{topic}' 주제로 내용 생성 중... (예약: {reservation_time or '즉시'}, 타입: {task.task_type})")
                result = self.gpt_handler.generate_platform_content(topic, platform='band', task_type=task.task_type)
                
                if not result or not result.get('content'):
                    print("❌ [밴드] AI 내용 생성에 실패했습니다.")
                    self.add_model_usage_log(topic=topic, model="-", status="실패", reason="내용 생성 실패", target="밴드")
                    return False
                
                # 이미지 준비
                images = []
                # 밴드 전용 이미지 설정 사용 (없으면 기본값 True)
                if self.settings.get('band_auto_image', self.settings.get('auto_image', True)):
                    images = self.get_images_to_upload(platform='band')
                    
                success = band_auto.post_to_band(
                    band_url, 
                    result.get('content', ''), 
                    image_paths=images,
                    reservation_time=reservation_time
                )
                
                if success:
                    task.last_status = 'success'
                else:
                    task.last_status = 'failed'
                    
                    # UI 다이얼로그로 실패 알림 (예약 실패 포함)
                    if self.page_ref:
                        try:
                            import threading
                            def show_band_failure_dialog():
                                try:
                                    if reservation_time:
                                        failure_msg = f"밴드 예약 설정에 실패했습니다.\n\n⏰ 예약 시간: {reservation_time}\n📝 주제: {topic}\n\n예약이 되지 않아 게시를 중단했습니다.\n다음 스케줄은 정상 진행됩니다."
                                    else:
                                        failure_msg = f"밴드 포스팅에 실패했습니다.\n\n📝 주제: {topic}\n\n다음 스케줄은 정상 진행됩니다."
                                    
                                    self.show_dialog(
                                        self.page_ref,
                                        "❌ 밴드 예약 실패",
                                        failure_msg,
                                        ft.Colors.RED
                                    )
                                except Exception as dialog_e:
                                    print(f"❌ 밴드 실패 다이얼로그 표시 실패: {dialog_e}")
                            
                            threading.Timer(0.1, show_band_failure_dialog).start()
                        except Exception as e:
                            print(f"❌ 밴드 실패 알림 처리 중 오류: {e}")
                
                self.scheduler.save_tasks()
                self.update_scheduler_ui()
                
                # 로그 추가
                duration = time.time() - start_time
                self.add_model_usage_log(
                    topic=topic,
                    model=result.get('model', 'gpt-4o-mini'),
                    status="성공" if success else "실패",
                    reason="밴드 자동 업로드" if success else ("밴드 예약 설정 실패" if reservation_time else "밴드 업로드 실패"),
                    target="네이버 밴드",
                    duration_sec=duration
                )
            
            elif task.platform == 'cafe':
                # 카페 포스팅 (이미지 포함)
                start_time = time.time()
                cafe_auto = NaverCafeAutomation(self.get_or_create_driver())
                cafe_url = task.data.get('cafe_url', self.settings.get('cafe_url', ''))
                menu_id = task.data.get('menu_id', self.settings.get('cafe_menu_id', ''))
                
                # 내용 생성
                topic = self.select_sequential_topic('cafe') or "체육관 소식"
                print(f"🤖 [카페] '{topic}' 주제로 내용 생성 중... (타입: {task.task_type})")
                result = self.gpt_handler.generate_platform_content(topic, platform='cafe', task_type=task.task_type)
                
                if not result or not result.get('content'):
                    print("❌ [카페] AI 내용 생성에 실패했습니다.")
                    self.add_model_usage_log(topic=topic, model="-", status="실패", reason="내용 생성 실패", target="카페")
                    return False

                # 이미지 준비
                images = []
                # 카페 전용 이미지 설정 사용 (없으면 기본값 True)
                if self.settings.get('cafe_auto_image', self.settings.get('auto_image', True)):
                    images = self.get_images_to_upload(platform='cafe')
                    
                success = cafe_auto.post_to_cafe(cafe_url, menu_id, result.get('title', '제목 없음'), result.get('content', ''), image_paths=images)
                
                if success:
                    task.last_status = 'success'
                else:
                    task.last_status = 'failed'
                self.scheduler.save_tasks()
                self.update_scheduler_ui()
                
                # 로그 추가
                duration = time.time() - start_time
                self.add_model_usage_log(
                    topic=topic,
                    model=result.get('model', 'gpt-4o-mini'),
                    status="성공" if success else "실패",
                    reason="카페 자동 업로드" if success else "카페 업로드 실패",
                    target="네이버 카페",
                    duration_sec=duration
                )
            
            elif task.platform == 'idle':
                # 유휴 활동 (방문소통 / 댓글소통 분리)
                idle_module = IdleActivity(self.get_or_create_driver(), self.gpt_handler, self.base_dir)
                
                # 설정값 로드
                do_like = self.settings.get('idle_do_like', True)
                use_ai_comment = self.settings.get('idle_use_ai_comment', False)  # 방문 댓글에 AI 사용
                use_ai_reply = self.settings.get('idle_use_ai_reply', False)  # 답글에 AI 사용
                visit_count = self.settings.get('idle_visit_count', 3)
                min_interval = self.settings.get('idle_min_interval', 300)  # 5분
                max_interval = self.settings.get('idle_max_interval', 600)  # 10분
                
                if task.task_type == 'visit' or task.task_type == 'regular':
                    # 방문소통: 서로이웃 방문 + 좋아요 + 댓글
                    print(f"🤝 방문소통 시작 (횟수: {visit_count}, 간격: {min_interval}~{max_interval}초)")
                    idle_module.visit_and_interact(
                        count=visit_count, 
                        do_like=do_like, 
                        use_ai=use_ai_comment,
                        min_interval=min_interval,
                        max_interval=max_interval
                    )
                    
                elif task.task_type == 'reply':
                    # 블로그 댓글 답글
                    print(f"💬 블로그 댓글 답글 시작 (AI 답글: {use_ai_reply})")
                    try:
                        from naver_blog_comment_reply import NaverBlogCommentReply
                        driver = self.get_or_create_driver()
                        reply_bot = NaverBlogCommentReply(driver=driver, gpt_handler=self.gpt_handler)
                        count = reply_bot.process_all_unanswered_comments(use_ai=use_ai_reply, limit=10)
                        print(f"✅ 블로그 댓글 답글 완료: {count}개")
                        if count > 0:
                            task.last_status = 'completed'
                    except Exception as reply_err:
                        print(f"❌ 블로그 댓글 답글 오류: {reply_err}")
                
                elif task.task_type == 'band_reply':
                    # 밴드 댓글 답글
                    print(f"💬 밴드 댓글 답글 시작")
                    try:
                        from naver_band_comment_reply import NaverBandCommentReply
                        driver = self.get_or_create_driver()
                        band_url = self.settings.get('band_url', '')
                        if not band_url:
                            print("⚠️ 밴드 URL이 설정되지 않았습니다.")
                        else:
                            band_reply = NaverBandCommentReply(
                                driver=driver,
                                gpt_handler=self.gpt_handler,
                                base_dir=self.base_dir
                            )
                            success = band_reply.process_band_comments(band_url=band_url, use_ai=True, limit=5)
                            if success:
                                print("✅ 밴드 댓글 답글 완료")
                                task.last_status = 'completed'
                    except Exception as band_err:
                        print(f"❌ 밴드 댓글 답글 오류: {band_err}")
            
            # 플랫폼이 blog_reply인 경우 (스케줄러에서 플랫폼으로 선택한 경우)
            elif task.platform == 'blog_reply':
                print(f"💬 [스케줄러] 블로그 댓글 답글 시작")
                try:
                    from naver_blog_comment_reply import NaverBlogCommentReply
                    driver = self.get_or_create_driver()
                    reply_bot = NaverBlogCommentReply(driver=driver, gpt_handler=self.gpt_handler)
                    count = reply_bot.process_all_unanswered_comments(use_ai=True, limit=10)
                    print(f"✅ 블로그 댓글 답글 완료: {count}개")
                    if count > 0:
                        task.last_status = 'completed'
                except Exception as reply_err:
                    print(f"❌ 블로그 댓글 답글 오류: {reply_err}")
            
            # 플랫폼이 band_reply인 경우 (스케줄러에서 플랫폼으로 선택한 경우)
            elif task.platform == 'band_reply':
                print(f"💬 [스케줄러] 밴드 댓글 답글 시작")
                try:
                    from naver_band_comment_reply import NaverBandCommentReply
                    driver = self.get_or_create_driver()
                    band_url = self.settings.get('band_url', '')
                    if not band_url:
                        print("⚠️ 밴드 URL이 설정되지 않았습니다.")
                    else:
                        band_reply = NaverBandCommentReply(
                            driver=driver,
                            gpt_handler=self.gpt_handler,
                            base_dir=self.base_dir
                        )
                        success = band_reply.process_band_comments(band_url=band_url, use_ai=True, limit=5)
                        if success:
                            print("✅ 밴드 댓글 답글 완료")
                            task.last_status = 'completed'
                except Exception as band_err:
                    print(f"❌ 밴드 댓글 답글 오류: {band_err}")

            # 🆕 플랫폼이 neighbor_visit인 경우 (이웃방문)
            elif task.platform == 'neighbor_visit':
                print(f"🤝 [스케줄러] 이웃방문 시작")
                try:
                    from modules.idle_activity import IdleActivity
                    driver = self.get_or_create_driver()
                    
                    # 기본 설정값 (task.data에서 가져오거나 기본값 사용)
                    visit_count = task.data.get('visit_count', 10) if task.data else 10
                    do_like = task.data.get('do_like', True) if task.data else True
                    use_ai = task.data.get('use_ai', True) if task.data else True
                    min_interval = task.data.get('min_interval', 10) if task.data else 10
                    max_interval = task.data.get('max_interval', 30) if task.data else 30
                    
                    print(f"📊 이웃방문 설정: 횟수={visit_count}, 좋아요={do_like}, AI={use_ai}")
                    
                    idle_module = IdleActivity(driver, self.gpt_handler, self.base_dir)
                    success = idle_module.visit_and_interact(
                        count=visit_count,
                        do_like=do_like,
                        use_ai=use_ai,
                        min_interval=min_interval,
                        max_interval=max_interval
                    )
                    
                    if success:
                        print(f"✅ 이웃방문 완료: {visit_count}회")
                        task.last_status = 'completed'
                    else:
                        print("⚠️ 이웃방문 중 일부 오류 발생")
                        task.last_status = 'completed'  # 부분 완료도 완료로 처리
                except Exception as visit_err:
                    print(f"❌ 이웃방문 오류: {visit_err}")
                    traceback.print_exc()


        except Exception as e:
            print(f"❌ 작업 처리 중 치명적 오류 발생: {e}")
            traceback.print_exc()
            task.last_status = 'failed'
            # 에러가 발생해도 완료 처리를 위해 예외를 전파하지 않거나, 여기서 저장/UI갱신을 시도
            self.scheduler.save_tasks()
            try:
                self.update_scheduler_ui()
            except:
                pass
        
        finally:
            # 🔓 락 해제 (성공/실패 관계없이)
            self.is_browser_busy = False
            self.browser_lock.release()
            self.update_activity_time()  # 세션 유지 타이머 리셋
            print(f"🔒 락 해제 완료 - 작업 종료: {task.platform}")
            
            # ⏰ 다음 작업 전 1분 대기 (순차 실행 시 여유 확보)
            print(f"⏳ 다음 작업 전 60초 대기...")
            time.sleep(60)

    def get_or_create_driver(self):
        """브라우저 드라이버를 가져오거나 새로 생성"""
        if self.browser_driver and self.is_driver_alive(self.browser_driver):
            return self.browser_driver
        
        # 새 드라이버 설정 (ChromeManager 사용)
        from modules.chrome_manager import ChromeManager
        manager = ChromeManager(self.base_dir)
        self.browser_driver = manager.setup_driver()
        return self.browser_driver

    def is_driver_alive(self, driver):
        try:
            driver.title
            return True
        except:
            return False

    def generate_content(self, topic, platform, task_type='regular', return_title=False):
        """GPT를 사용하여 플랫폼별 스타일의 게시글 생성"""
        result = self.gpt_handler.generate_platform_content(topic, platform=platform, task_type=task_type)
        
        if return_title:
            return result.get('title', '제목 없음'), result.get('content', '')
        return result.get('content', '')

    def auto_post(self, page):
        """자동 포스팅 실행 - 전송 버튼만 클릭"""
        try:
            print("🔘 타이머 자동 포스팅: 전송 버튼 클릭!")
            
            # UI에서 전송 버튼 클릭 시뮬레이션
            if self.send_message_func:
                # send_message 함수 호출 (전송 버튼과 동일한 동작)
                self.send_message_func(None)
                
                print("✅ 전송 버튼 클릭 완료! 이후 자동 처리됩니다.")
                
                # 스낵바로 알림
                if self.page_ref:
                    self.page_ref.snack_bar = ft.SnackBar(
                        content=ft.Text("✅ 자동 포스팅이 시작되었습니다!"),
                        bgcolor=ft.Colors.GREEN_400
                    )
                    self.page_ref.snack_bar.open = True
                    self.page_ref.update()
                
                return True
            else:
                print("❌ 전송 버튼 함수가 설정되지 않았습니다.")
                return False
                
        except Exception as e:
            print(f"❌ 자동 포스팅 실행 중 오류: {str(e)}")
            return False
    
    def update_usage_display(self):
        """사용 현황 디스플레이 업데이트"""
        try:
            if self.page_ref:
                # 타이머 상태 정보를 스낵바로 표시
                if self.timer_running:
                    if self.next_post_time:
                        remaining = self.next_post_time - datetime.now()
                        if remaining.total_seconds() > 0:
                            minutes = int(remaining.total_seconds() // 60)
                            seconds = int(remaining.total_seconds() % 60)
                            status_msg = f"⏰ 타이머 실행 중 | 다음 포스팅까지: {minutes}분 {seconds}초 | 오늘: {self.daily_post_count}회"
                        else:
                            status_msg = f"⏰ 타이머 실행 중 | 포스팅 준비 중... | 오늘: {self.daily_post_count}회"
                    else:
                        status_msg = f"⏰ 타이머 실행 중 | 시간 계산 중... | 오늘: {self.daily_post_count}회"
                else:
                    status_msg = f"⏹️ 타이머 중지됨 | 오늘: {self.daily_post_count}회"
                
                # 상태 메시지는 콘솔에만 출력 (UI 업데이트는 필요시에만)
                print(status_msg)
                
        except Exception as e:
            print(f"사용 현황 업데이트 중 오류: {str(e)}")
    
    def add_model_usage_log(
        self,
        topic: str,
        model: str,
        status: str,
        reason: str = "-",
        target: str = "블로그",
        duration_sec: float | None = None
    ):
        """AI 모델 사용 로그 추가"""
        try:
            # 초기화가 안 되었다면 강제로 활성화(페이지가 이미 구성된 상태라고 가정)
            if not getattr(self, "model_usage_initialized", False):
                self.model_usage_initialized = True
            duration_txt = f"{duration_sec:.1f}s" if duration_sec is not None else "-"
            log_entry = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "topic": topic or "-",
                "model": model or "-",
                "status": status,
                "reason": reason or "-",
                "target": target or "-",
                "duration": duration_txt
            }
            print(f"[AI 로그] {log_entry}")
            self.model_usage_logs.append(log_entry)
            # 로그가 너무 길어지는 것을 방지 (최신 500건만 유지)
            if len(self.model_usage_logs) > 500:
                self.model_usage_logs = self.model_usage_logs[-500:]
            self._save_model_usage_logs()
            # 최신 로그 한 줄 표시
            if hasattr(self, "model_usage_latest_text"):
                self.model_usage_latest_text.value = (
                    f"최근: {log_entry['status']} | {log_entry['target']} | {log_entry['model']} | {log_entry['duration']}"
                )
                self.model_usage_latest_text.color = ft.Colors.BLUE_900
                self.model_usage_latest_text.update()
            # 비용 요약 업데이트
            self._update_usage_cost_ui()
            self.refresh_model_usage_table(force=True)
        except Exception as e:
            print(f"모델 사용 로그 추가 중 오류: {str(e)}")
    
    def refresh_model_usage_table(self, force: bool = False):
        """AI 모델 사용 로그 테이블 갱신"""
        try:
            if not getattr(self, "model_usage_initialized", False) and not force:
                return
            # 비용 갱신
            self._update_usage_cost_ui()
            # 카드형 리스트 뷰 사용 여부 확인
            if hasattr(self, "model_usage_list"):
                def _short(txt: str, limit: int = 28):
                    if not txt:
                        return "-"
                    return txt if len(txt) <= limit else txt[:limit-1] + "…"
                
                def _status_chip(status: str):
                    status = status or "-"
                    color_map = {
                        "성공": ft.Colors.GREEN_200,
                        "실패": ft.Colors.RED_200
                    }
                    text_color_map = {
                        "성공": ft.Colors.GREEN_900,
                        "실패": ft.Colors.RED_900
                    }
                    return ft.Container(
                        content=ft.Text(status, size=11, weight=ft.FontWeight.BOLD, color=text_color_map.get(status, ft.Colors.BLUE_900)),
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border_radius=20,
                        bgcolor=color_map.get(status, ft.Colors.BLUE_100)
                    )

                rows = []
                for log in reversed(self.model_usage_logs[-200:]):  # 최신 순으로 최대 200개 표시
                    rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(log.get("time", "-"))),
                                ft.DataCell(ft.Text(_short(log.get("target", "-"), 10))),
                                ft.DataCell(ft.Text(_short(log.get("topic", "-"), 24))),
                                ft.DataCell(ft.Text(_short(log.get("model", "-"), 18))),
                                ft.DataCell(_status_chip(log.get("status", "-"))),
                                ft.DataCell(ft.Text(log.get("duration", "-"))),
                                ft.DataCell(ft.Text(_short(log.get("reason", "-"), 28)))
                            ]
                        )
                    )

                def _apply_rows():
                    # 카드형 리스트로 표시
                    cards = []
                    for log in reversed(self.model_usage_logs[-50:]):  # 최근 50건 카드 표시
                        status = log.get("status", "-")
                        color_map = {
                            "성공": ft.Colors.GREEN_100,
                            "실패": ft.Colors.RED_100
                        }
                        text_color_map = {
                            "성공": ft.Colors.GREEN_900,
                            "실패": ft.Colors.RED_900
                        }
                        cards.append(
                            ft.Container(
                                content=ft.Row(
                                    controls=[
                                        ft.Column([
                                            ft.Text(f"{log.get('time','-')} · {log.get('target','-')}", size=12, color=ft.Colors.BLUE_800),
                                            ft.Text(_short(log.get('topic','-'), 60), size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                                            ft.Text(log.get("reason","-"), size=12, color=ft.Colors.GREY_700),
                                        ], spacing=2, expand=True),
                                        ft.Column([
                                            ft.Text(log.get("model","-"), size=12, color=ft.Colors.GREY_800),
                                            ft.Text(log.get("duration","-"), size=12, color=ft.Colors.GREY_600),
                                            ft.Container(
                                                content=ft.Text(status, size=11, weight=ft.FontWeight.BOLD, color=text_color_map.get(status, ft.Colors.BLUE_900)),
                                                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                                border_radius=20,
                                                bgcolor=color_map.get(status, ft.Colors.BLUE_100)
                                            )
                                        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.END)
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                ),
                                padding=10,
                                bgcolor=ft.Colors.WHITE,
                                border_radius=8,
                                border=ft.border.all(1, ft.Colors.BLUE_50),
                                shadow=ft.BoxShadow(
                                    spread_radius=0.5,
                                    blur_radius=4,
                                    color=ft.Colors.with_opacity(0.08, ft.Colors.BLUE_400)
                                )
                            )
                        )
                    if hasattr(self, "model_usage_list"):
                        self.model_usage_list.controls = cards
                        self.model_usage_list.update()
                    has_rows = len(cards) > 0
                    self.model_usage_empty.visible = not has_rows
                    self.model_usage_empty.opacity = 0 if has_rows else 1
                    self.model_usage_empty.disabled = has_rows
                    self.model_usage_empty.update()
                    # 카운트 텍스트 업데이트
                    if hasattr(self, "model_usage_count_text"):
                        self.model_usage_count_text.value = f"총 {len(self.model_usage_logs)}건 (최근 200건 표시)"
                        self.model_usage_count_text.color = ft.Colors.BLUE_900
                        self.model_usage_count_text.update()
                    # 최신 한 줄 표시
                    if hasattr(self, "model_usage_latest_text"):
                        if has_rows:
                            last = self.model_usage_logs[-1]
                            self.model_usage_latest_text.value = (
                                f"최근: {last.get('status','-')} | {last.get('target','-')} | "
                                f"{last.get('model','-')} | {last.get('duration','-')}"
                            )
                        else:
                            self.model_usage_latest_text.value = "최근 로그 없음"
                        self.model_usage_latest_text.color = ft.Colors.BLUE_900
                        self.model_usage_latest_text.update()
                    if hasattr(self, "model_usage_stack"):
                        self.model_usage_stack.update()
                    if self.page_ref:
                        self.page_ref.update()

                if self.page_ref and hasattr(self.page_ref, "invoke_later"):
                    self.page_ref.invoke_later(_apply_rows)
                else:
                    _apply_rows()
        except Exception as e:
            print(f"모델 사용 로그 테이블 갱신 중 오류: {str(e)}")

    def _show_full_usage_dialog(self, page=None):
        """AI 사용 로그 전체 보기 다이얼로그"""
        try:
            p = page or self.page_ref
            if not p:
                print("[AI 로그] 전체 보기 실패: page_ref 없음")
                return

            def build_full_list():
                items = []
                if not self.model_usage_logs:
                    items.append(ft.Text("로그가 없습니다.", size=12, color=ft.Colors.GREY_700))
                else:
                    for log in reversed(self.model_usage_logs):
                        txt = (
                            f"{log.get('time','-')} | {log.get('model','-')} | "
                            f"{log.get('status','-')} | {log.get('target','-')} | "
                            f"{log.get('duration','-')}\n{log.get('topic','-')}"
                        )
                        items.append(ft.Text(txt, size=12, color=ft.Colors.BLUE_900))
                return ft.ListView(controls=items, height=520, auto_scroll=False)

            self.model_usage_full_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("AI 사용 내역 전체 보기", size=16, weight=ft.FontWeight.BOLD),
                content=ft.Container(
                    content=build_full_list(),
                    width=760,
                    height=560,
                    padding=10
                ),
                actions=[
                    ft.TextButton("닫기", on_click=lambda e: self._close_full_usage_dialog(p))
                ],
                actions_alignment=ft.MainAxisAlignment.END
            )
            p.dialog = self.model_usage_full_dialog
            self.model_usage_full_dialog.open = True
            p.update()
            print("[AI 로그] 전체 보기 다이얼로그 open")
        except Exception as e:
            print(f"[AI 로그] 전체 로그 다이얼로그 표시 오류: {e}")

    def _show_full_usage_bottomsheet(self, page=None):
        """AI 사용 로그 전체 보기 - BottomSheet (show_bottom_sheet)로 표시, 미지원 시 Dialog로 대체"""
        try:
            p = page or self.page_ref
            if not p:
                print("[AI 로그] BottomSheet 실패: page_ref 없음")
                return

            def build_list():
                items = []
                if not self.model_usage_logs:
                    items.append(ft.Text("로그가 없습니다.", size=12, color=ft.Colors.GREY_700))
                else:
                    for log in reversed(self.model_usage_logs):
                        txt = (
                            f"{log.get('time','-')} | {log.get('model','-')} | "
                            f"{log.get('status','-')} | {log.get('target','-')} | "
                            f"{log.get('duration','-')}\n{log.get('topic','-')}"
                        )
                        items.append(ft.Text(txt, size=12, color=ft.Colors.BLUE_900))
                return ft.ListView(controls=items, height=520, auto_scroll=False)

            content = ft.Container(
                content=build_list(),
                width=760,
                height=560,
                padding=10
            )

            def close_sheet(e=None):
                if hasattr(p, "close_bottom_sheet"):
                    try:
                        p.close_bottom_sheet()
                        p.update()
                        return
                    except Exception:
                        pass
                # fallback: hide sheet by clearing bottom_sheet if present
                try:
                    p.bottom_sheet = None
                    p.update()
                except Exception:
                    pass

            sheet = ft.BottomSheet(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            [
                                ft.Text("AI 사용 내역 전체 보기", size=16, weight=ft.FontWeight.BOLD),
                                ft.IconButton(icon=ft.Icons.CLOSE, on_click=close_sheet)
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        content
                    ],
                    spacing=10
                ),
                show_drag_handle=True
            )

            if hasattr(p, "show_bottom_sheet"):
                p.show_bottom_sheet(sheet)
                p.update()
                print("[AI 로그] BottomSheet open")
            else:
                print("[AI 로그] BottomSheet 미지원 -> Dialog로 대체")
                self._show_full_usage_dialog(p)
        except Exception as e:
            print(f"[AI 로그] BottomSheet 표시 오류: {e}")

    # 인라인 전체 보기 패널 -----------------
    def _build_full_usage_panel(self):
        self.model_usage_full_panel_list = ft.ListView(
            controls=[],
            height=260,
            auto_scroll=False
        )
        self.model_usage_full_panel = ft.Container(
            visible=False,
            bgcolor=ft.Colors.BLUE_50,
            border=ft.border.all(1, ft.Colors.BLUE_100),
            border_radius=10,
            padding=10,
            content=ft.Column(
                controls=[
                    ft.Row(
                        [
                            ft.Text("AI 사용 내역 전체 보기 (인라인)", size=16, weight=ft.FontWeight.BOLD),
                            ft.IconButton(icon=ft.Icons.CLOSE, on_click=lambda e: self._hide_full_usage_panel())
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    self.model_usage_full_panel_list
                ],
                spacing=10,
                height=280
            )
        )
        return self.model_usage_full_panel

    def _refresh_full_usage_panel_list(self):
        if not hasattr(self, "model_usage_full_panel_list"):
            return
        items = []
        if not self.model_usage_logs:
            items.append(ft.Text("로그가 없습니다.", size=12, color=ft.Colors.GREY_700))
        else:
            for log in reversed(self.model_usage_logs):
                txt = (
                    f"{log.get('time','-')} | {log.get('model','-')} | "
                    f"{log.get('status','-')} | {log.get('target','-')} | "
                    f"{log.get('duration','-')}\n{log.get('topic','-')}"
                )
                items.append(ft.Text(txt, size=12, color=ft.Colors.BLUE_900))
        self.model_usage_full_panel_list.controls = items
        try:
            self.model_usage_full_panel_list.update()
        except Exception:
            pass

    def _show_full_usage_panel(self):
        self._refresh_full_usage_panel_list()
        if hasattr(self, "model_usage_full_panel"):
            self.model_usage_full_panel.visible = True
            try:
                self.model_usage_full_panel.update()
            except Exception:
                pass
        if hasattr(self, "model_usage_card_container"):
            self.model_usage_card_container.visible = False
            try:
                self.model_usage_card_container.update()
            except Exception:
                pass

    def _hide_full_usage_panel(self):
        if hasattr(self, "model_usage_full_panel"):
            self.model_usage_full_panel.visible = False
            try:
                self.model_usage_full_panel.update()
            except Exception:
                pass
        if hasattr(self, "model_usage_card_container"):
            self.model_usage_card_container.visible = True
            try:
                self.model_usage_card_container.update()
            except Exception:
                pass

    def _close_full_usage_dialog(self, page):
        try:
            if self.model_usage_full_dialog:
                self.model_usage_full_dialog.open = False
                page.update()
        except Exception as e:
            print(f"전체 로그 다이얼로그 닫기 오류: {e}")
    
    def _clear_model_usage_logs(self):
        """AI 모델 사용 로그 전체 삭제"""
        try:
            self.model_usage_logs = []
            self._save_model_usage_logs()
            self._update_usage_cost_ui()
            self.refresh_model_usage_table()
        except Exception as e:
            print(f"모델 사용 로그 초기화 중 오류: {str(e)}")
    
    def _build_model_usage_card(self):
        """AI 모델 사용 로그 카드 UI"""
        self.model_usage_stack = ft.Stack(
            controls=[
                ft.Container(
                    content=self.model_usage_list,
                    expand=True
                ),
                ft.Container(
                    content=self.model_usage_empty,
                    expand=True,
                    alignment=ft.alignment.center
                )
            ],
            expand=True
        )
        return ft.Container(
            content=self.model_usage_stack,
            height=220,
            padding=12,
            border=ft.border.all(1, ft.Colors.BLUE_100),
            border_radius=10,
            bgcolor=ft.Colors.BLUE_50,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=6,
                color=ft.Colors.with_opacity(0.12, ft.Colors.BLUE_200)
            )
        )
    
    def start_clock(self):
        """실시간 시계 시작"""
        if not self.clock_running:
            self.clock_running = True
            self.clock_thread = threading.Thread(target=self.clock_worker)
            self.clock_thread.daemon = True
            self.clock_thread.start()
    
    def stop_clock(self):
        """실시간 시계 중지"""
        self.clock_running = False
    
    def clock_worker(self):
        """시계 업데이트 워커"""
        while self.clock_running:
            try:
                if self.clock_text and self.page_ref:
                    current_time = datetime.now()
                    time_str = current_time.strftime("📅 %Y-%m-%d %p %I:%M:%S")
                    # 한국어 오전/오후 변환
                    time_str = time_str.replace("AM", "오전").replace("PM", "오후")
                    
                    self.clock_text.value = time_str
                    self.page_ref.update()
                
                time.sleep(1)  # 1초마다 업데이트
                
            except Exception as e:
                print(f"시계 업데이트 중 오류: {str(e)}")
                time.sleep(1)
    
    def start_serial_status_updater(self):
        """시리얼 상태 실시간 업데이트 시작"""
        if not hasattr(self, 'serial_status_running'):
            self.serial_status_running = True
            self.serial_status_thread = threading.Thread(target=self.serial_status_worker)
            self.serial_status_thread.daemon = True
            self.serial_status_thread.start()
    
    def stop_serial_status_updater(self):
        """시리얼 상태 업데이트 중지"""
        if hasattr(self, 'serial_status_running'):
            self.serial_status_running = False
    
    def serial_status_worker(self):
        """시리얼 상태 업데이트 워커"""
        while getattr(self, 'serial_status_running', False):
            try:
                if (hasattr(self, 'serial_status_text_ref') and 
                    hasattr(self, 'days_text_ref') and 
                    self.page_ref):
                    
                    # 시리얼 상태 업데이트
                    serial_status = self.get_serial_status()
                    
                    self.serial_status_text_ref.value = f"🔐 {serial_status['status']} | {serial_status['message']}"
                    self.serial_status_text_ref.color = serial_status['color']
                    
                    if serial_status['days_remaining'] > 0:
                        self.days_text_ref.value = f"📅 유효기간: {serial_status['days_remaining']}일 남음"
                        self.days_text_ref.visible = True
                    else:
                        self.days_text_ref.value = ""
                        self.days_text_ref.visible = False
                    
                    self.page_ref.update()
                
                # 5분마다 업데이트 (시리얼 상태는 자주 변경되지 않으므로)
                time.sleep(300)
                
            except Exception as e:
                print(f"시리얼 상태 업데이트 중 오류: {str(e)}")
                time.sleep(60)  # 오류 발생 시 1분 대기
            
    def create_image_folders(self):
        """10개의 이미지 폴더를 생성합니다."""
        try:
            for i in range(1, 11):
                folder_name = f"default_images_{i}"
                folder_path = os.path.join(self.base_dir, folder_name)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                    print(f"이미지 폴더 생성 완료: {folder_path}")
            return True
        except Exception as e:
            print(f"이미지 폴더 생성 중 오류 발생: {str(e)}")
            return False
            
    def load_folder_index(self, platform='blog'):
        """현재 이미지 폴더 인덱스를 로드합니다."""
        try:
            suffix = "" if platform == 'blog' else f"_{platform}"
            index_file = os.path.join(self.base_dir, f'config/current_folder_index{suffix}.txt')
            if os.path.exists(index_file):
                with open(index_file, 'r') as f:
                    return int(f.read().strip())
            return 0  # 파일이 없으면 0부터 시작
        except Exception as e:
            print(f"폴더 인덱스 로드 중 오류 발생: {str(e)}")
            return 0
            
    def save_folder_index(self, index, platform='blog'):
        """현재 이미지 폴더 인덱스를 저장합니다."""
        try:
            suffix = "" if platform == 'blog' else f"_{platform}"
            index_file = os.path.join(self.base_dir, f'config/current_folder_index{suffix}.txt')
            with open(index_file, 'w') as f:
                f.write(str(index))
        except Exception as e:
            print(f"폴더 인덱스 저장 중 오류 발생: {str(e)}")
            
    def load_used_folders(self, platform='blog'):
        """사용된 이미지 폴더 이력을 로드합니다."""
        try:
            suffix = "" if platform == 'blog' else f"_{platform}"
            used_folders_file = os.path.join(self.base_dir, f'config/used_folders{suffix}.json')
            if os.path.exists(used_folders_file):
                with open(used_folders_file, 'r') as f:
                    return json.load(f)
            return {"used_folders": [], "cycle_count": 0}
        except Exception as e:
            print(f"사용된 폴더 이력 로드 중 오류 발생: {str(e)}")
            return {"used_folders": [], "cycle_count": 0}
            
    def save_used_folders(self, data, platform='blog'):
        """사용된 이미지 폴더 이력을 저장합니다."""
        try:
            suffix = "" if platform == 'blog' else f"_{platform}"
            used_folders_file = os.path.join(self.base_dir, f'config/used_folders{suffix}.json')
            with open(used_folders_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"사용된 폴더 이력 저장 중 오류 발생: {str(e)}")
            return False

    def save_used_folder(self, folder_name):
        """특정 폴더를 사용된 목록에 추가합니다."""
        try:
            used_data = self.load_used_folders()
            if folder_name not in used_data["used_folders"]:
                used_data["used_folders"].append(folder_name)
                self.save_used_folders(used_data)
            return True
        except Exception as e:
            print(f"폴더 추가 중 오류 발생: {str(e)}")
            return False
            
    def get_images_to_upload(self, platform='blog'):
        """현재 상태에서 업로드할 이미지 파일 경로 리스트를 반환합니다."""
        try:
            folder_path = self.get_next_image_folder(platform=platform)
            if not folder_path or not os.path.exists(folder_path):
                print(f"ℹ️ {platform} 업로드용 폴더를 찾을 수 없어 이미지를 생략합니다.")
                return []
            
            valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
            image_paths = [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if os.path.splitext(f)[1].lower() in valid_exts and not f.startswith('.')
            ]
            
            if not image_paths:
                print(f"ℹ️ {folder_path} 폴더에 이미지가 없어 업로드를 생략합니다.")
                return []
            # 폴더 사용 이력 업데이트도 함께 진행 (한 번 가져오면 사용한 것으로 간주)
            folder_name = os.path.basename(folder_path)
            # save_used_folder 가 별도 정의되어 있을 가능성 확인 필요하나, 
            # 여기서는 save_used_folders 인터페이스에 맞게 관리됩니다 (get_next_image_folder 내부에서 처리됨)
            
            return image_paths
        except Exception as e:
            print(f"이미지 목록 가져오기 오류: {e}")
            return []
            
    def get_next_image_folder(self, platform='blog'):
        """다음 이미지 폴더 경로를 반환하고 인덱스를 업데이트합니다.
           이미 사용된 폴더는 건너뛰고 다음 폴더를 선택합니다."""
        # 플랫폼별 폴더 접두사 결정
        prefix = "default_images" if platform == 'blog' else f"{platform}_images"
        
        # 사용된 폴더 이력 로드
        used_data = self.load_used_folders(platform=platform)
        used_folders = used_data["used_folders"]
        cycle_count = used_data["cycle_count"]
        
        # 현재 인덱스 로드
        current_index = self.load_folder_index(platform=platform)
        
        # 모든 폴더 사용 여부 확인
        all_used = True
        for i in range(1, 11):
            folder_name = f"{prefix}_{i}"
            if folder_name not in used_folders:
                # 실제로 폴더가 존재하는지 확인
                if os.path.exists(os.path.join(self.base_dir, folder_name)):
                    all_used = False
                    break
                
        # 모든 폴더가 사용되었으면 초기화
        if all_used:
            used_folders = []
            cycle_count += 1
            print(f"모든 {platform} 이미지 폴더를 사용했습니다. 새로운 사이클({cycle_count}) 시작")
            
        # 사용되지 않은 다음 폴더 찾기
        found = False
        next_index = current_index
        
        for _ in range(10):  # 최대 10번 시도
            next_index = (next_index % 10) + 1  # 1~10 순환
            folder_name = f"{prefix}_{next_index}"
            folder_path = os.path.join(self.base_dir, folder_name)
            
            # 폴더가 존재하고 아직 사용되지 않았으면 선택
            if os.path.exists(folder_path) and folder_name not in used_folders:
                found = True
                break
        
        if not found:
            # 블로그는 기본 폴더로 폴백하지만, 카페/밴드는 폴더가 없으면 생략하도록 처리 (None 반환)
            if platform == 'blog':
                print("사용 가능한 블로그 이미지 폴더를 찾을 수 없습니다. 기본 폴더 사용.")
                return os.path.join(self.base_dir, "default_images")
            else:
                print(f"ℹ️ 사용 가능한 {platform} 전용 이미지 폴더가 없습니다. 이미지 없이 업로드를 진행합니다.")
                return None
        
        # 선택된 폴더를 사용된 목록에 추가
        used_folders.append(f"{prefix}_{next_index}")
        used_data = {"used_folders": used_folders, "cycle_count": cycle_count}
        self.save_used_folders(used_data, platform=platform)
        
        # 인덱스 업데이트 및 저장
        self.save_folder_index(next_index, platform=platform)
        
        folder_path = os.path.join(self.base_dir, f"{prefix}_{next_index}")
        print(f"이미지 폴더 선택: {folder_path} (사이클 {cycle_count}, 플랫폼: {platform})")
        return folder_path

    def select_sequential_topic(self, platform='blog'):
        """저장된 주제 목록에서 순차적으로 주제 선택 (플랫폼별)"""
        try:
            if os.path.exists(os.path.join(self.base_dir, 'config/user_settings.txt')):
                with open(os.path.join(self.base_dir, 'config/user_settings.txt'), 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # 플랫폼별 설정 키 결정
                    key = f"{platform}_topics" if platform in ['band', 'cafe'] else "blog_topics"
                    topics_str = settings.get(key, '')
                    
                    if topics_str:
                        topics = [topic.strip() for topic in topics_str.split(',') if topic.strip()]
                        if topics:
                            # 해당 플랫폼의 인덱스 업데이트
                            idx = self.topic_indices.get(platform, -1)
                            idx = (idx + 1) % len(topics)
                            self.topic_indices[platform] = idx
                            
                            self._debug_log("H2", "blog_writer_app.select_sequential_topic", f"selected {platform} topic", 
                                          {"topics_count": len(topics), "new_index": idx})
                            # 인덱스 저장
                            self.save_topic_index()
                            return topics[idx]
            return None
        except Exception as e:
            print(f"[{platform}] 주제 선택 중 오류 발생: {str(e)}")
            return None

    def auto_reply_comments_click(self, e, use_ai=False):
        """댓글 자동 답글 기능 (알림센터 기반 - NaverBlogCommentReply 모듈 사용)"""
        try:
            # 새로 작성한 모듈 임포트
            from naver_blog_comment_reply import NaverBlogCommentReply
            
            # limit 값 가져오기
            try:
                reply_limit = int(self.blog_reply_limit) if self.blog_reply_limit else 10
                reply_limit = max(1, min(reply_limit, 50))  # 1~50 제한
            except:
                reply_limit = 10
            
            # 스낵바로 시작 알림
            if self.page_ref:
                self.page_ref.snack_bar = ft.SnackBar(
                    content=ft.Text(f"🔔 알림센터에서 댓글 답글 시작 (최대 {reply_limit}개)..."),
                    bgcolor=ft.Colors.BLUE_600
                )
                self.page_ref.snack_bar.open = True
                self.page_ref.update()
            
            # 별도 스레드에서 실행 (UI 프리징 방지)
            def run_reply_task():
                # 🔒 락 획득 (다른 작업이 끝날 때까지 대기)
                if self.is_browser_busy:
                    print("⏳ 다른 작업이 진행 중입니다. 완료까지 대기...")
                    if self.page_ref:
                        self.page_ref.snack_bar = ft.SnackBar(
                            content=ft.Text("⏳ 다른 작업 완료 대기 중..."),
                            bgcolor=ft.Colors.ORANGE_600
                        )
                        self.page_ref.snack_bar.open = True
                        try:
                            self.page_ref.update()
                        except:
                            pass
                
                self.browser_lock.acquire()
                self.is_browser_busy = True
                self.update_activity_time()
                print("🔓 [블로그 답글] 락 획득 완료")
                
                try:
                    # 드라이버 확보
                    driver = self.get_or_create_driver()
                    
                    # 전용 모듈 인스턴스 생성 및 저장 (중지 기능용)
                    reply_bot = NaverBlogCommentReply(
                        driver=driver,
                        gpt_handler=self.gpt_handler
                    )
                    self.comment_reply_instance = reply_bot  # 인스턴스 저장
                    
                    # 실행 (limit 파라미터 추가)
                    count = reply_bot.process_all_unanswered_comments(use_ai=use_ai, limit=reply_limit)
                    
                    # 완료 알림
                    if self.page_ref:
                        if count > 0:
                            msg = f"✅ {count}개 댓글에 답글 작성을 완료했습니다!"
                            color = ft.Colors.GREEN_600
                        else:
                            msg = "📭 처리할 새로운 댓글 알림이 없습니다."
                            color = ft.Colors.ORANGE_600
                            
                        self.page_ref.snack_bar = ft.SnackBar(content=ft.Text(msg), bgcolor=color)
                        self.page_ref.snack_bar.open = True
                        
                except Exception as thread_error:
                    print(f"❌ 댓글 답글 스레드 오류: {thread_error}")
                    traceback.print_exc()
                    if self.page_ref:
                        self.page_ref.snack_bar = ft.SnackBar(
                            content=ft.Text(f"❌ 오류 발생: {str(thread_error)}"),
                            bgcolor=ft.Colors.RED_600
                        )
                        self.page_ref.snack_bar.open = True
                        
                finally:
                    # 🔧 확실한 상태 정리 + 락 해제
                    self.comment_reply_instance = None
                    self.is_browser_busy = False
                    self.browser_lock.release()
                    self.update_activity_time()
                    print("🔒 [블로그 답글] 락 해제 완료")
                    try:
                        if self.page_ref:
                            self.page_ref.update()
                    except:
                        pass
            
            import threading
            threading.Thread(target=run_reply_task, daemon=True).start()
                
        except Exception as e:
            print(f"❌ 댓글 답글 실행 중 오류: {e}")
            traceback.print_exc()
            
            if self.page_ref:
                self.page_ref.snack_bar = ft.SnackBar(
                    content=ft.Text(f"❌ 오류 발생: {str(e)}"),
                    bgcolor=ft.Colors.RED_600
                )
                self.page_ref.snack_bar.open = True
                self.page_ref.update()

    def stop_comment_reply_click(self, e):
        """댓글 자동 답글 중지"""
        if hasattr(self, 'comment_reply_instance') and self.comment_reply_instance:
            self.comment_reply_instance.stop()
            print("🛑 댓글 답글 중지 요청됨")
            
            if self.page_ref:
                self.page_ref.snack_bar = ft.SnackBar(
                    content=ft.Text("🛑 댓글 답글 작업 중지 중..."),
                    bgcolor=ft.Colors.ORANGE_600
                )
                self.page_ref.snack_bar.open = True
                self.page_ref.update()
        else:
            print("⚠️ 실행 중인 댓글 답글 작업이 없습니다.")


    def on_content_change(self, e):
        """본문 내용이 변경될 때마다 호출되는 함수"""
        try:
            if self.current_content:  # 본문이 있는 경우
                # 자동 저장
                self.auto_save()
                
                # 이미지 위치 계산 및 저장
                if auto_image_checkbox.value:  # type: ignore # 자동 이미지 삽입이 활성화된 경우
                    self.save_image_positions(self.current_content, image_insert_mode_value) # type: ignore
        except Exception as e:
            print(f"본문 변경 처리 중 오류 발생: {str(e)}")

    def main(self, page: ft.Page):
        # 페이지 객체 저장 (먼저 설정)
        self.page = page
        
        # 페이지 기본 설정
        page.title = "블로그 글쓰기 도우미"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.padding = 20
        page.window_width = 1200
        page.window_height = 800
        page.window_resizable = True
        
        # Windows 호환성: 초기화 시 명시적 업데이트
        try:
            page.update()
        except Exception as e:
            print(f"⚠️ 초기 페이지 업데이트 실패 (무시됨): {e}")
        
        # 전역 폴더 선택기 초기화
        self.current_folder_picker_target = None
        self.folder_picker = ft.FilePicker(on_result=self._on_global_folder_picker_result)
        page.overlay.append(self.folder_picker)
        
        # 시리얼 인증 확인 (필수) - 앱 내부에서 처리
        if self.serial_auth.is_serial_required():
            print("🔐 시리얼 인증이 필요합니다. 인증 화면을 표시합니다...")
            self._show_serial_auth_dialog(page)
            return  # 인증 다이얼로그만 표시하고 리턴 (메인 UI는 인증 성공 후 로드)
        
        # 시리얼 인증 완료 - 메인 UI 로드
        self._load_main_ui(page)
    
    def _show_serial_auth_dialog(self, page: ft.Page):
        """앱 내부에서 시리얼 인증 다이얼로그 표시"""
        import threading
        import time
        
        # UI 컴포넌트들
        serial_input = ft.TextField(
            label="시리얼 번호",
            hint_text="시리얼 번호를 입력하세요",
            width=350,
            autofocus=True
        )
        
        status_text = ft.Text(
            "",
            size=14,
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.RED
        )
        
        loading_ring = ft.ProgressRing(visible=False, width=30, height=30)
        
        # 기존 시리얼이 유효하지 않은 경우 메시지 표시
        config = self.serial_auth.load_config()
        existing_serial = config.get("serial_number", "")
        if existing_serial:
            status_text.value = "❌ 기존 시리얼이 만료되었거나 유효하지 않습니다.\n🔐 새로운 시리얼 번호를 입력해주세요."
            # 무효한 시리얼 삭제
            config["serial_number"] = ""
            config["last_validation"] = ""
            self.serial_auth.save_config(config)
        
        submit_button = ft.ElevatedButton(
            "인증",
            width=150,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE,
                color=ft.Colors.WHITE
            )
        )
        
        cancel_button = ft.TextButton(
            "취소 (프로그램 종료)",
            width=150
        )
        
        def on_serial_submit(e):
            serial_number = serial_input.value.strip()
            
            if not serial_number:
                status_text.value = "❌ 시리얼 번호를 입력해주세요."
                status_text.color = ft.Colors.RED
                page.update()
                return
            
            # 로딩 표시
            submit_button.disabled = True
            cancel_button.disabled = True
            serial_input.disabled = True
            loading_ring.visible = True
            status_text.value = "🔄 인증 중..."
            status_text.color = ft.Colors.BLUE
            page.update()
            
            def validate_serial():
                try:
                    valid, message, expiry_date = self.serial_auth.check_serial(serial_number)
                    
                    if valid:
                        # 성공 - 시리얼 저장
                        self.serial_auth.save_validation(serial_number, expiry_date)
                        
                        # UI 업데이트
                        loading_ring.visible = False
                        status_text.value = "✅ 인증 성공! 프로그램을 시작합니다..."
                        status_text.color = ft.Colors.GREEN
                        page.update()
                        
                        time.sleep(1)
                        
                        # 인증 다이얼로그 닫고 메인 UI 로드
                        try:
                            page.controls.clear()
                            page.update()
                            self._load_main_ui(page)
                        except Exception as ui_error:
                            print(f"❌ 메인 UI 로드 오류: {ui_error}")
                            import traceback
                            traceback.print_exc()
                            # 오류 발생 시에도 재시도
                            try:
                                time.sleep(0.5)
                                page.update()
                                self._load_main_ui(page)
                            except:
                                pass
                        
                    else:
                        # 실패
                        loading_ring.visible = False
                        status_text.value = f"❌ {message}"
                        status_text.color = ft.Colors.RED
                        submit_button.disabled = False
                        cancel_button.disabled = False
                        serial_input.disabled = False
                        page.update()
                        
                except Exception as ex:
                    loading_ring.visible = False
                    status_text.value = f"❌ 인증 중 오류: {str(ex)}"
                    status_text.color = ft.Colors.RED
                    submit_button.disabled = False
                    cancel_button.disabled = False
                    serial_input.disabled = False
                    page.update()
            
            # 백그라운드에서 검증 실행
            threading.Thread(target=validate_serial, daemon=True).start()
        
        def on_cancel(e):
            print("❌ 사용자가 시리얼 인증을 취소했습니다.")
            page.window_destroy()
        
        # 이벤트 핸들러 연결
        submit_button.on_click = on_serial_submit
        cancel_button.on_click = on_cancel
        serial_input.on_submit = on_serial_submit
        
        # 인증 화면 레이아웃
        auth_content = ft.Column([
            ft.Container(height=50),
            ft.Icon(ft.Icons.LOCK, size=60, color=ft.Colors.BLUE_600),
            ft.Container(height=20),
            ft.Text(
                "🔐 시리얼 번호 인증",
                size=28,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER,
                color=ft.Colors.BLUE_700
            ),
            ft.Container(height=10),
            ft.Text(
                "블로그자동화 프로그램 사용을 위해\n시리얼 번호 인증이 필요합니다.",
                size=16,
                text_align=ft.TextAlign.CENTER,
                color=ft.Colors.GREY_700
            ),
            ft.Container(height=40),
            serial_input,
            ft.Container(height=15),
            ft.Row([loading_ring], alignment=ft.MainAxisAlignment.CENTER),
            status_text,
            ft.Container(height=30),
            ft.Row([
                cancel_button,
                submit_button
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        # 페이지에 인증 화면 추가
        page.add(ft.Container(
            content=auth_content,
            alignment=ft.alignment.center,
            expand=True
        ))
        
        # 포커스 설정
        try:
            serial_input.focus()
        except:
            pass
    
    def _load_main_ui(self, page: ft.Page):
        
        # ========== 시작 안내 다이얼로그 ==========
        def close_startup_guide(e):
            startup_dialog.open = False
            page.update()
        
        startup_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.CHECKLIST, color=ft.Colors.BLUE_600, size=30),
                ft.Text("📋 시작 전 체크리스트", size=20, weight=ft.FontWeight.BOLD)
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("프로그램을 사용하기 전에 아래 단계를 먼저 완료해주세요:", 
                           size=14, color=ft.Colors.GREY_700),
                    ft.Divider(height=10),
                    
                    # 단계 1
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Text("1", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                bgcolor=ft.Colors.BLUE_600,
                                width=30, height=30,
                                border_radius=15,
                                alignment=ft.alignment.center
                            ),
                            ft.Column([
                                ft.Text("네이버 로그인", weight=ft.FontWeight.BOLD, size=14),
                                ft.Text("[네이버 로그인] 버튼 클릭 → 로그인 진행 → [로그인 완료] 클릭", 
                                       size=12, color=ft.Colors.GREY_600)
                            ], spacing=2, expand=True)
                        ], spacing=10),
                        padding=10,
                        bgcolor=ft.Colors.BLUE_50,
                        border_radius=8
                    ),
                    
                    # 단계 2
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Text("2", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                bgcolor=ft.Colors.GREEN_600,
                                width=30, height=30,
                                border_radius=15,
                                alignment=ft.alignment.center
                            ),
                            ft.Column([
                                ft.Text("블로그 글쓰기 창 활성화", weight=ft.FontWeight.BOLD, size=14),
                                ft.Text("[글쓰기] 클릭 → [링크] 클릭 → 글쓰기 창 닫기", 
                                       size=12, color=ft.Colors.GREY_600)
                            ], spacing=2, expand=True)
                        ], spacing=10),
                        padding=10,
                        bgcolor=ft.Colors.GREEN_50,
                        border_radius=8
                    ),
                    
                    # 단계 3
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Text("3", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                bgcolor=ft.Colors.PURPLE_600,
                                width=30, height=30,
                                border_radius=15,
                                alignment=ft.alignment.center
                            ),
                            ft.Column([
                                ft.Text("네이버 밴드 로그인 (선택)", weight=ft.FontWeight.BOLD, size=14),
                                ft.Text("밴드 포스팅 사용 시: 밴드 로그인 진행 후 그대로 유지", 
                                       size=12, color=ft.Colors.GREY_600)
                            ], spacing=2, expand=True)
                        ], spacing=10),
                        padding=10,
                        bgcolor=ft.Colors.PURPLE_50,
                        border_radius=8
                    ),
                    
                    # 단계 4
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Text("4", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                bgcolor=ft.Colors.ORANGE_600,
                                width=30, height=30,
                                border_radius=15,
                                alignment=ft.alignment.center
                            ),
                            ft.Column([
                                ft.Text("자동 포스팅 시작!", weight=ft.FontWeight.BOLD, size=14),
                                ft.Text("위 단계 완료 후 → 이 창에서 자동 포스팅 또는 스케줄러 실행", 
                                       size=12, color=ft.Colors.GREY_600)
                            ], spacing=2, expand=True)
                        ], spacing=10),
                        padding=10,
                        bgcolor=ft.Colors.ORANGE_50,
                        border_radius=8
                    ),
                    
                    ft.Divider(height=10),
                    ft.Text("💡 이 안내는 프로그램 시작 시마다 표시됩니다.", 
                           size=11, color=ft.Colors.GREY_500, italic=True)
                ], spacing=12, scroll=ft.ScrollMode.AUTO),
                width=450,
                height=420
            ),
            actions=[
                ft.ElevatedButton(
                    "✅ 확인했습니다",
                    icon=ft.Icons.CHECK_CIRCLE,
                    bgcolor=ft.Colors.BLUE_600,
                    color=ft.Colors.WHITE,
                    on_click=close_startup_guide
                )
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER
        )
        
        page.overlay.append(startup_dialog)
        startup_dialog.open = True
        # ========== 시작 안내 다이얼로그 끝 ==========

        
        # 실시간 시계 컴포넌트 생성
        self.clock_text = ft.Text(
            value="📅 로딩 중...",
            size=16,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_600,
            text_align=ft.TextAlign.CENTER
        )
        
        # 시계 시작
        self.start_clock()
        
        # 닫기 버튼 이벤트 핸들러 추가
        def on_window_close(e):
            print("🚪 앱 종료 요청 감지됨")
            try:
                # 안전한 종료 실행
                self._safe_exit(0)
                
            except Exception as e:
                print(f"❌ 종료 중 오류 발생: {str(e)}")
                self._safe_exit(1)
            
        # 윈도우 이벤트 핸들러 설정
        page.on_window_event = on_window_close

        # GPT 설정 탭 컴포넌트
        gpt_persona = ft.TextField(
            label="GPT 페르소나",
            hint_text="GPT가 어떤 역할이나 정체성을 가지고 글을 작성할지 정의하세요...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True
        )
        
        persona_help_text = ft.Text(
            "페르소나 예시: '*** 분야 전문가', '*** 관련 블로거' 등 (권장 길이: 100-300자)",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )
        
        gpt_instructions = ft.TextField(
            label="GPT 지침",
            hint_text="글 작성 시 따라야 할 구체적인 지침이나 규칙을 정의하세요...",
            multiline=True,
            min_lines=3,
            max_lines=5,
            expand=True
        )
        
        instructions_help_text = ft.Text(
            "지침 예시: '*** 내용을 자연스럽게 포함', '*** 대상 설득력 있는 내용' 등 (권장 길이: 200-500자)",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )
        
        gpt_style = ft.TextField(
            label="글쓰기 스타일",
            hint_text="원하는 글쓰기 스타일을 설정하세요...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True
        )
        
        style_help_text = ft.Text(
            "스타일 예시: '친근한 대화체', '전문적인 설명식', '*** 스타일' 등 (권장 길이: 100-300자)",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )

        # 홍보/정보 지침 및 비율
        promotional_instructions = ft.TextField(
            label="홍보성 지침",
            hint_text="홍보성 포스팅 시 따라야 할 지침을 입력하세요...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True
        )
        informational_instructions = ft.TextField(
            label="정보성 지침",
            hint_text="정보성 포스팅 시 따라야 할 지침을 입력하세요...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True
        )
        
        band_instructions = ft.TextField(
            label="밴드 전용 지침",
            hint_text="밴드 포스팅 시 적용할 전용 지침을 입력하세요 (예: 친근하게, 해시태그 포함)...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True
        )
        
        cafe_instructions = ft.TextField(
            label="카페 전용 지침",
            hint_text="카페 포스팅 시 적용할 전용 지침을 입력하세요 (예: 정보 공유 중심, 정중하게)...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True
        )
        
        idle_instructions = ft.TextField(
            label="소통(댓글/방문) 지침",
            hint_text="이웃 방문 및 댓글 작성 시 적용할 페르소나와 스타일을 입력하세요...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True
        )
        promotional_ratio = ft.TextField(
            label="홍보성 비율",
            hint_text="예: 3",
            width=120,
            value="3"
        )
        informational_ratio = ft.TextField(
            label="정보성 비율",
            hint_text="예: 7",
            width=120,
            value="7"
        )
        promo_example_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("홍보성 지침 예시"),
            content=ft.Text("예시:\n- 체육관/센터의 강점과 혜택을 강조\n- 문의/연락처/위치 정보를 자연스럽게 포함\n- 이벤트나 할인 안내를 간결히 언급"),
            actions=[ft.TextButton("닫기", on_click=lambda e: setattr(promo_example_dialog, "open", False))],
            actions_alignment=ft.MainAxisAlignment.END
        )
        info_example_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("정보성 지침 예시"),
            content=ft.Text("예시:\n- 운동/건강 팁을 단계별로 설명\n- 근거 또는 사례를 간단히 제시\n- 실천 가능한 체크리스트/팁 포함"),
            actions=[ft.TextButton("닫기", on_click=lambda e: setattr(info_example_dialog, "open", False))],
            actions_alignment=ft.MainAxisAlignment.END
        )
        # 예시 보기 핸들러
        def show_promo_example(e):
            page.dialog = promo_example_dialog
            promo_example_dialog.open = True
            page.update()
        def show_info_example(e):
            page.dialog = info_example_dialog
            info_example_dialog.open = True
            page.update()
        
        use_api_checkbox = ft.Checkbox(
            label="실제 OpenAI API 사용 (체크 해제 시 더미 데이터 사용)",
            value=not self.use_dummy
        )
        
        api_key_field = ft.TextField(
            label="OpenAI API 키",
            hint_text="OpenAI API 키를 입력하세요...",
            password=True,  # 비밀번호 형태로 표시
            can_reveal_password=False,  # 비밀번호 표시 버튼 제거
            visible=not self.use_dummy
        )

        # Gemini API 키 (항상 표시, 미입력 시 경고 메시지)
        gemini_api_key_field = ft.TextField(
            label="Gemini API 키",
            hint_text="Gemini API 키를 입력하세요...",
            password=True,
            can_reveal_password=False,
            visible=True
        )
        
        api_key_help_text = ft.Text(
            "API 키는 보안을 위해 항상 암호화되어 표시됩니다. *** 웹사이트에서 발급받은 키를 입력하세요.",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True,
            visible=not self.use_dummy
        )
        
        # 자동 업로드 설정
        auto_upload_checkbox = ft.Checkbox(
            label="글 생성 후 자동으로 블로그에 업로드",
            value=False
        )
        
        auto_upload_help_text = ft.Text(
            "이 옵션을 선택하면 GPT가 글을 생성한 후 자동으로 블로그에 업로드합니다.",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )
        
        # 자동 주제 선택 설정
        auto_topic_checkbox = ft.Checkbox(
            label="주제 자동 선택",
            value=False
        )
        
        auto_topic_help_text = ft.Text(
            "체크: 사용자 설정에 등록된 주제 중 하나를 자동으로 선택하여 글을 생성합니다. 체크 해제: 수동으로 주제를 입력합니다.",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )
        
        # 이미지 자동 삽입 설정 추가
        auto_image_checkbox = ft.Checkbox(
            label="이미지 자동 삽입 모드",
            value=True
        )
        
        auto_image_help_text = ft.Text(
            "체크: 이미지를 자동으로 삽입합니다. 체크 해제: 수동으로 이미지를 선택합니다.",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )
        
        # 🎯 최종 발행 설정 추가
        auto_final_publish_checkbox = ft.Checkbox(
            label="최종 발행 자동 완료",
            value=True
        )
        
        auto_final_publish_help_text = ft.Text(
            "체크: 태그 추가 후 자동으로 발행 버튼까지 클릭하여 완전 자동 업로드. 체크 해제: 태그 추가 후 대기 상태로 수동 검토 가능.",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )

        # 모델 선택 체크박스
        model_checkboxes = {}
        model_descriptions = {}
        model_info_text = ft.Text(
            "선택된 모델: 0개 (체크된 순서대로 순차 사용)",
            size=12,
            color=ft.Colors.GREY_600
        )
        model_cost_summary = ft.Text(
            "월 예상 비용(10회/일, 300회/월): -",
            size=13,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_800,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS
        )
        model_cost_info = ft.Text(
            "모델별 월 추정 비용: -",
            size=12,
            color=ft.Colors.GREY_600,
            visible=False
        )
        model_desc_text = ft.Text(
            "모델 설명: -",
            size=12,
            color=ft.Colors.GREY_600,
            visible=False
        )

        def update_model_ui():
            selected = [mid for mid, cb in model_checkboxes.items() if cb.value]
            has_gemini = any(mid.startswith("gemini") for mid in selected)
            # Gemini 키 입력칸은 항상 노출 (미입력 시도 대비)
            gemini_api_key_field.visible = True
            model_info_text.value = f"선택된 모델: {len(selected)}개"
            # 비용 계산 (10개/일 → 300개/월 가정, 선택된 모델 라운드로빈 분배)
            cost_lines = []
            total_monthly_posts = 10 * 30
            usage = {}
            if selected:
                for i in range(total_monthly_posts):
                    mid = selected[i % len(selected)]
                    usage[mid] = usage.get(mid, 0) + 1
            total_cost = 0
            for mid in selected:
                info = Config.AI_MODELS.get(mid, {})
                free = info.get("free", False)
                ic = info.get("input_cost_per_1k_krw") or 0
                oc = info.get("output_cost_per_1k_krw") or 0
                count = usage.get(mid, 0)
                per_post = 0 if free else (ic + 2 * oc)  # 입력 1K, 출력 2K 가정
                monthly = per_post * count
                total_cost += monthly
                cost_lines.append(f"{info.get('name', mid)}: {count}회 · 월≈₩{int(monthly):,}" + (" (무료)" if free else ""))
            if cost_lines:
                model_cost_summary.value = f"월 예상 비용(10회/일, 300회/월): ≈₩{int(total_cost):,}"
                cost_lines.append(f"합계: 월≈₩{int(total_cost):,}")
                model_cost_info.value = "\n".join(cost_lines)
                model_cost_info.visible = True
            else:
                model_cost_summary.value = "월 예상 비용(10회/일, 300회/월): -"
                model_cost_info.value = "모델별 월 추정 비용: -"
                model_cost_info.visible = False
            # 모델 설명 출력
            desc_lines = []
            for mid in selected:
                info = Config.AI_MODELS.get(mid, {})
                name = info.get("name", mid)
                provider = info.get("provider", "-")
                context = info.get("context", "")
                free = info.get("free", False)
                ic = info.get("input_cost_per_1k_krw")
                oc = info.get("output_cost_per_1k_krw")
                cost_label = "무료" if free else f"입력≈₩{ic}/1K, 출력≈₩{oc}/1K" if ic is not None and oc is not None else "비용 정보 없음"
                desc_lines.append(f"- {name} ({provider}, {context}) · {cost_label}")
            if desc_lines:
                model_desc_text.value = "모델 설명:\n" + "\n".join(desc_lines)
                model_desc_text.visible = True
            else:
                model_desc_text.value = "모델 설명: -"
                model_desc_text.visible = False
            page.update()

        for model_id, info in Config.AI_MODELS.items():
            label = f"{info.get('name', model_id)}"
            provider = info.get("provider")
            if provider:
                label += f" ({provider})"
            ic = info.get("input_cost_per_1k_krw")
            oc = info.get("output_cost_per_1k_krw")
            if ic is not None and oc is not None:
                label += f" · 입력≈₩{ic}/1K · 출력≈₩{oc}/1K"
            cb = ft.Checkbox(label=label, value=False, on_change=lambda e, mid=model_id: update_model_ui())
            model_checkboxes[model_id] = cb
            model_descriptions[model_id] = info.get("description", "")

        # 이미지 삽입 모드 기본값 설정 (UI 요소 제거)
        image_insert_mode_value = "random"
        
        # API 사용 여부에 따라 API 키 필드 표시/숨김
        def on_api_checkbox_change(e):
            api_key_field.visible = use_api_checkbox.value
            api_key_help_text.visible = use_api_checkbox.value
            page.update()
            
        # 체크박스 변경 시 자동 저장 함수
        def on_checkbox_change(e):
            save_app_settings()  # 체크박스 변경 시 자동으로 설정 저장
            page.update()
            
        use_api_checkbox.on_change = on_api_checkbox_change
        auto_upload_checkbox.on_change = on_checkbox_change
        auto_image_checkbox.on_change = on_checkbox_change
        auto_topic_checkbox.on_change = on_checkbox_change
        auto_final_publish_checkbox.on_change = on_checkbox_change

        def save_app_settings(e=None):
            try:
                app_settings = {
                    "use_dummy": not use_api_checkbox.value,
                    "auto_upload": auto_upload_checkbox.value,
                    "auto_image": auto_image_checkbox.value,
                    "auto_topic": auto_topic_checkbox.value,
                    "auto_final_publish": auto_final_publish_checkbox.value,
                    "image_insert_mode": image_insert_mode_value,
                    "band_url": band_url_input.value if 'band_url_input' in locals() else self.settings.get('band_url', ''),
                    "cafe_url": cafe_url_input.value if 'cafe_url_input' in locals() else self.settings.get('cafe_url', ''),
                    "cafe_menu_id": cafe_menu_input.value if 'cafe_menu_input' in locals() else self.settings.get('cafe_menu_id', ''),
                    "idle_visit_count": idle_visit_count.value if 'idle_visit_count' in locals() else self.settings.get('idle_visit_count', 2),
                    "idle_use_ai_comment": idle_use_ai_comment.value if 'idle_use_ai_comment' in locals() else self.settings.get('idle_use_ai_comment', True),
                    "idle_do_like": idle_do_like.value if 'idle_do_like' in locals() else self.settings.get('idle_do_like', True),
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                self.settings = app_settings
                with open(os.path.join(self.base_dir, 'config/app_settings.json'), 'w', encoding='utf-8') as f:
                    json.dump(app_settings, f, ensure_ascii=False, indent=2)
                
                if e:  # 직접 호출이 아닌 경우에만 메시지 표시
                    page.snack_bar = ft.SnackBar(content=ft.Text("앱 설정이 저장되었습니다."))
                    page.snack_bar.open = True
                    page.update()
            except Exception as e:
                if e:  # 직접 호출이 아닌 경우에만 메시지 표시
                    page.snack_bar = ft.SnackBar(content=ft.Text(f"저장 중 오류 발생: {str(e)}"))
                    page.snack_bar.open = True
                    page.update()

        def load_app_settings():
            try:
                if os.path.exists(os.path.join(self.base_dir, 'config/app_settings.json')):
                    with open(os.path.join(self.base_dir, 'config/app_settings.json'), 'r', encoding='utf-8') as f:
                        app_settings = json.load(f)
                        use_api_checkbox.value = not app_settings.get('use_dummy', False)
                        api_key_field.visible = use_api_checkbox.value
                        api_key_help_text.visible = use_api_checkbox.value
                        auto_upload_checkbox.value = app_settings.get('auto_upload', False)
                        auto_image_checkbox.value = app_settings.get('auto_image', True)
                        auto_topic_checkbox.value = app_settings.get('auto_topic', False)
                        auto_final_publish_checkbox.value = app_settings.get('auto_final_publish', True)
                        image_insert_mode_value = app_settings.get('image_insert_mode', 'random')
                        
                        if 'idle_visit_count' in locals():
                            idle_visit_count.value = app_settings.get('idle_visit_count', 2)
                        if 'idle_use_ai_comment' in locals():
                            idle_use_ai_comment.value = app_settings.get('idle_use_ai_comment', True)
                        if 'idle_do_like' in locals():
                            idle_do_like.value = app_settings.get('idle_do_like', True)
                        page.update()
                        
                    # 자동 주제 모드 상태 표시 업데이트는 함수 정의 후에 호출
                    # on_auto_topic_change(None)  # 임시 주석 처리
            except Exception as e:
                print(f"앱 설정 로드 중 오류 발생: {str(e)}")

        def save_gpt_settings(e):
            try:
                settings = {
                    "persona": gpt_persona.value,
                    "instructions": gpt_instructions.value,
                    "style": gpt_style.value,
                    "promotional_instructions": promotional_instructions.value,
                    "informational_instructions": informational_instructions.value,
                    "band_instructions": band_instructions.value,
                    "cafe_instructions": cafe_instructions.value,
                    "idle_instructions": idle_instructions.value,
                    "promotional_ratio": promotional_ratio.value,
                    "informational_ratio": informational_ratio.value,
                    "selected_models": [mid for mid, cb in model_checkboxes.items() if cb.value],
                    "gemini_api_key": gemini_api_key_field.value,
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                with open(os.path.join(self.base_dir, 'config/gpt_settings.txt'), 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)
                
                # API 키 저장 (환경 변수 파일에)
                if use_api_checkbox.value and api_key_field.value:
                    env_content = f"OPENAI_API_KEY={api_key_field.value}\n"
                    if gemini_api_key_field.value:
                        env_content += f"GEMINI_API_KEY={gemini_api_key_field.value}\n"
                    with open(os.path.join(self.base_dir, '.env'), 'w', encoding='utf-8') as f:
                        f.write(env_content)
                
                # GPT 핸들러 재초기화
                self.use_dummy = not use_api_checkbox.value
                self.gpt_handler = GPTHandler(use_dummy=self.use_dummy)
                
                # 댓글 답글 설정을 user_settings.txt에 저장
                try:
                    user_settings_path = os.path.join(self.base_dir, 'config/user_settings.txt')
                    if os.path.exists(user_settings_path):
                        with open(user_settings_path, 'r', encoding='utf-8') as f:
                            user_settings = json.load(f)
                    else:
                        user_settings = {}
                    
                    user_settings['reply_instruction'] = reply_instruction.value
                    user_settings['default_reply'] = default_reply.value
                    user_settings['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    with open(user_settings_path, 'w', encoding='utf-8') as f:
                        json.dump(user_settings, f, ensure_ascii=False, indent=2)
                    print(f"✅ 댓글 답글 설정 저장 완료")
                except Exception as ue:
                    print(f"⚠️ 댓글 답글 설정 저장 중 오류: {ue}")
                
                # 앱 설정 저장
                save_app_settings()
                
                page.snack_bar = ft.SnackBar(content=ft.Text("GPT 설정이 저장되었습니다."))
                page.snack_bar.open = True
                page.update()
            except Exception as e:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"저장 중 오류 발생: {str(e)}"))
                page.snack_bar.open = True
                page.update()

        def load_gpt_settings():
            try:
                if os.path.exists(os.path.join(self.base_dir, 'config/gpt_settings.txt')):
                    with open(os.path.join(self.base_dir, 'config/gpt_settings.txt'), 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                        gpt_persona.value = settings.get('persona', '')
                        
                        # 고정 검토 지침 제거 (UI에 표시하지 않음)
                        instructions = settings.get('instructions', '')
                        fixed_review_prefix = """글 작성 후 반드시 다음 사항을 검토해주세요:
1. 오타와 맞춤법 오류가 없는지 확인
2. 문장 간 연결이 자연스러운지 확인
3. 논리적 흐름이 일관되는지 확인
4. 불필요한 반복이나 중복 표현이 없는지 확인
5. 전체적인 글의 통일성과 완성도 검토

"""
                        if instructions.startswith(fixed_review_prefix):
                            # 고정 검토 지침을 제외한 사용자 지침만 표시
                            gpt_instructions.value = instructions[len(fixed_review_prefix):]
                        else:
                            gpt_instructions.value = instructions
                            
                        gpt_style.value = settings.get('style', '')
                        promotional_instructions.value = settings.get('promotional_instructions', '')
                        informational_instructions.value = settings.get('informational_instructions', '')
                        band_instructions.value = settings.get('band_instructions', '')
                        cafe_instructions.value = settings.get('cafe_instructions', '')
                        idle_instructions.value = settings.get('idle_instructions', '')
                        promotional_ratio.value = str(settings.get('promotional_ratio', '3'))
                        informational_ratio.value = settings.get('informational_ratio', '7')
                        # 모델 선택 복원
                        selected_models = settings.get('selected_models', [])
                        for mid, cb in model_checkboxes.items():
                            cb.value = mid in selected_models
                        gemini_api_key_field.value = settings.get('gemini_api_key', '')
                
                # API 사용 여부 설정 로드
                if os.path.exists(os.path.join(self.base_dir, 'config/app_settings.json')):
                    with open(os.path.join(self.base_dir, 'config/app_settings.json'), 'r', encoding='utf-8') as f:
                        app_settings = json.load(f)
                        use_api_checkbox.value = not app_settings.get('use_dummy', False)
                        api_key_field.visible = use_api_checkbox.value
                        api_key_help_text.visible = use_api_checkbox.value
                        auto_upload_checkbox.value = app_settings.get('auto_upload', False)
                        auto_image_checkbox.value = app_settings.get('auto_image', True)
                        auto_topic_checkbox.value = app_settings.get('auto_topic', False)
                        auto_final_publish_checkbox.value = app_settings.get('auto_final_publish', True)  # 🎯 최종 발행 설정 로드
                
                # API 키 로드
                if os.path.exists(os.path.join(self.base_dir, '.env')):
                    with open(os.path.join(self.base_dir, '.env'), 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.startswith('OPENAI_API_KEY='):
                                api_key_field.value = line.split('=', 1)[1].strip()
                                break
                
                # 댓글 답글 설정 로드 (user_settings.txt에서)
                try:
                    user_settings_path = os.path.join(self.base_dir, 'config/user_settings.txt')
                    if os.path.exists(user_settings_path):
                        with open(user_settings_path, 'r', encoding='utf-8') as f:
                            user_settings = json.load(f)
                            reply_instruction.value = user_settings.get('reply_instruction', '- 댓글 내용에 공감하며 감사 표현\n- 15~30자 이내로 짧게 작성\n- 이모지 1개만 포함')
                            default_reply.value = user_settings.get('default_reply', '감사합니다😊,좋은 말씀 감사해요💕,응원 감사합니다🙏,행복한 하루 되세요✨,방문 감사합니다🌻')
                except Exception as ue:
                    print(f"⚠️ 댓글 답글 설정 로드 중 오류: {ue}")
                
                update_model_ui()
                page.update()
            except Exception as e:
                print(f"GPT 설정 로드 중 오류 발생: {str(e)}")

        # 사용자 설정 탭 컴포넌트
        dojang_name = ft.TextField(
            label="도장 이름",
            hint_text="도장 이름을 입력하세요..."
        )

        address = ft.TextField(
            label="주소",
            hint_text="도장 주소를 입력하세요..."
        )

        phone = ft.TextField(
            label="연락처",
            hint_text="연락처를 입력하세요..."
        )

        blog_url = ft.TextField(
            label="블로그 URL",
            hint_text="네이버 블로그 URL을 입력하세요..."
        )

        naver_id = ft.TextField(
            label="네이버 아이디",
            hint_text="네이버 아이디를 입력하세요..."
        )

        naver_pw = ft.TextField(
            label="네이버 비밀번호",
            password=True,
            hint_text="네이버 비밀번호를 입력하세요..."
        )

        kakao_url = ft.TextField(
            label="카카오톡 오픈채팅방 주소",
            hint_text="카카오톡 오픈채팅방 URL을 입력하세요..."
        )

        blog_tags = ft.TextField(
            label="블로그 태그",
            hint_text="태그를 쉼표(,)로 구분하여 입력하세요. 예: 태권도,도장,무술",
            multiline=True,
            min_lines=2,
            max_lines=4
        )

        blog_topics = ft.TextField(
            label="블로그 주제 목록",
            hint_text="블로그 자동 작성에 사용될 주제들을 쉼표(,)로 구분하여 입력하세요.",
            multiline=True,
            min_lines=3,
            max_lines=5
        )

        band_topics = ft.TextField(
            label="밴드 주제 목록",
            hint_text="밴드 자동 포스팅에 사용될 주제들을 쉼표(,)로 구분하여 입력하세요.",
            multiline=True,
            min_lines=3,
            max_lines=5
        )

        cafe_topics = ft.TextField(
            label="카페 주제 목록",
            hint_text="카페 자동 포스팅에 사용될 주제들을 쉼표(,)로 구분하여 입력하세요.",
            multiline=True,
            min_lines=3,
            max_lines=5
        )

        blog_slogan = ft.TextField(
            label="블로그 마지막 슬로건",
            hint_text="블로그 글 마지막 슬로건",
            multiline=True, min_lines=2, max_lines=4
        )
        cafe_slogan = ft.TextField(
            label="카페 마지막 슬로건",
            hint_text="카페 글 마지막 슬로건",
            multiline=True, min_lines=2, max_lines=4
        )
        band_slogan = ft.TextField(
            label="밴드 마지막 슬로건",
            hint_text="밴드 글 마지막 슬로건",
            multiline=True, min_lines=2, max_lines=4
        )

        # 본문 첫 문장 설정 필드 추가
        blog_first_sentence = ft.TextField(
            label="블로그 본문 첫 문장",
            hint_text="블로그 포스팅 첫 문장 (예: 안녕하세요...)",
            multiline=True, min_lines=2, max_lines=3
        )
        cafe_first_sentence = ft.TextField(
            label="카페 본문 첫 문장",
            hint_text="카페 포스팅 첫 문장",
            multiline=True, min_lines=2, max_lines=3
        )
        band_first_sentence = ft.TextField(
            label="밴드 본문 첫 문장",
            hint_text="밴드 포스팅 첫 문장",
            multiline=True, min_lines=2, max_lines=3
        )
        
        # 답글 지침 커스터마이징 필드
        reply_instruction = ft.TextField(
            label="💬 댓글 답글 AI 지침",
            hint_text="댓글에 답글할 때 AI가 참고할 지침 (예: 15자 이내, 감사 표현, 이모지 1개)",
            multiline=True,
            min_lines=3,
            max_lines=5,
            value="- 댓글 내용에 공감하며 감사 표현\n- 15~30자 이내로 짧게 작성\n- 이모지 1개만 포함"
        )
        
        # 기본 답글 문구 커스터마이징 필드
        default_reply = ft.TextField(
            label="📝 기본 답글 문구 (콤마로 구분)",
            hint_text="AI 사용 안함 시 순차 사용할 답글 목록",
            multiline=True,
            min_lines=3,
            max_lines=5,
            value="감사합니다😊,좋은 말씀 감사해요💕,응원 감사합니다🙏,행복한 하루 되세요✨,방문 감사합니다🌻"
        )

        # ========================================
        # 방문소통 / 댓글소통 설정
        # ========================================
        idle_section_title = ft.Text(
            "🤝 방문소통 / 댓글소통 설정",
            size=18,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_700
        )
        
        idle_visit_count = ft.TextField(
            label="방문소통 횟수",
            hint_text="스케줄 실행 시 방문할 블로그 수 (예: 3)",
            width=150,
            value=str(self.settings.get('idle_visit_count', 3))
        )
        
        idle_min_interval = ft.TextField(
            label="최소 간격 (초)",
            hint_text="방문 사이 최소 대기 시간 (예: 30초)",
            width=150,
            value=str(self.settings.get('idle_min_interval', 30))
        )
        
        idle_max_interval = ft.TextField(
            label="최대 간격 (초)",
            hint_text="방문 사이 최대 대기 시간 (예: 60초)",
            width=150,
            value=str(self.settings.get('idle_max_interval', 60))
        )
        
        idle_do_like = ft.Checkbox(
            label="좋아요 클릭",
            value=self.settings.get('idle_do_like', True)
        )
        
        idle_use_ai_comment = ft.Checkbox(
            label="방문 댓글에 AI 사용 (체크 해제 시 랜덤 문구)",
            value=self.settings.get('idle_use_ai_comment', False)
        )
        
        idle_use_ai_reply = ft.Checkbox(
            label="내 글 답글에 AI 사용 (체크 해제 시 30개 랜덤 문구 순차 사용)",
            value=self.settings.get('idle_use_ai_reply', False)
        )
        
        idle_comment_check_interval = ft.TextField(
            label="댓글 확인 주기 (초)",
            hint_text="새 댓글 확인 주기 (예: 300 = 5분)",
            width=150,
            value=str(self.settings.get('idle_comment_check_interval', 300))
        )
        
        idle_enable_comment_monitoring = ft.Checkbox(
            label="댓글 자동 답글 모니터링 활성화 (프로그램 실행 중 항상)",
            value=self.settings.get('idle_enable_comment_monitoring', False)
        )
        
        def save_idle_settings(e):
            try:
                self.settings['idle_visit_count'] = int(idle_visit_count.value or 3)
                self.settings['idle_min_interval'] = int(idle_min_interval.value or 300)
                self.settings['idle_max_interval'] = int(idle_max_interval.value or 600)
                self.settings['idle_do_like'] = idle_do_like.value
                self.settings['idle_use_ai_comment'] = idle_use_ai_comment.value
                self.settings['idle_use_ai_reply'] = idle_use_ai_reply.value
                self.settings['idle_comment_check_interval'] = int(idle_comment_check_interval.value or 300)
                self.settings['idle_enable_comment_monitoring'] = idle_enable_comment_monitoring.value
                self.save_settings()
                
                # 댓글 모니터링 활성화/비활성화
                if idle_enable_comment_monitoring.value:
                    if not self.comment_monitor_active:
                        self.start_comment_monitoring()
                        page.snack_bar = ft.SnackBar(content=ft.Text("✅ 설정 저장 및 댓글 모니터링 시작됨!"), bgcolor=ft.Colors.GREEN)
                    else:
                        page.snack_bar = ft.SnackBar(content=ft.Text("✅ 설정이 저장되었습니다. (모니터링 실행 중)"), bgcolor=ft.Colors.GREEN)
                else:
                    if self.comment_monitor_active:
                        self.stop_comment_monitoring()
                        page.snack_bar = ft.SnackBar(content=ft.Text("✅ 설정 저장 및 댓글 모니터링 중지됨"), bgcolor=ft.Colors.ORANGE)
                    else:
                        page.snack_bar = ft.SnackBar(content=ft.Text("✅ 방문소통/댓글소통 설정이 저장되었습니다."), bgcolor=ft.Colors.GREEN)
                
                page.snack_bar.open = True
                page.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"❌ 저장 중 오류: {str(ex)}"), bgcolor=ft.Colors.RED)
                page.snack_bar.open = True
                page.update()

        
        idle_settings_container = ft.Container(
            content=ft.Column([
                idle_section_title,
                ft.Divider(),
                ft.Text("📌 방문소통: 서로이웃 글 방문 → 좋아요 → 댓글", size=14, color=ft.Colors.GREY_700),
                ft.Row([idle_visit_count, idle_min_interval, idle_max_interval], spacing=10),
                ft.Row([idle_do_like, idle_use_ai_comment], spacing=20),
                ft.Divider(),
                ft.Text("💬 댓글소통: 내 글에 달린 댓글에 자동 답글 (중복 방지)", size=14, color=ft.Colors.GREY_700),
                ft.Row([idle_comment_check_interval, idle_enable_comment_monitoring], spacing=20),
                idle_use_ai_reply,
                ft.ElevatedButton("설정 저장", icon=ft.Icons.SAVE, on_click=save_idle_settings, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
            ], spacing=10),
            padding=15,
            bgcolor=ft.Colors.BLUE_50,
            border_radius=10,
            margin=ft.margin.only(top=10, bottom=10)
        )

        # 개발자 정보
        developer_info = ft.Container(
            content=ft.Column([
                ft.Text("개발자 정보", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("라이온 개발팀"),
                ft.Text("이관원 (010-7282-5529)"),
                ft.Text("이예린 (010-3852-5339)")
            ]),
            padding=20,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border_radius=10,
            margin=ft.margin.only(top=20)
        )


        # 시간 설정 탭 컴포넌트
        timer_start_time = ft.TextField(
            label="시작 시간 (HH:MM)",
            hint_text="예: 09:00",
            width=150,
            value="09:00"
        )

        timer_end_time = ft.TextField(
            label="종료 시간 (HH:MM)",
            hint_text="예: 23:00",
            width=150,
            value="23:00"
        )

        timer_min_interval = ft.TextField(
            label="최소 간격 (분)",
            hint_text="예: 15",
            width=150,
            value="15"
        )

        timer_max_interval = ft.TextField(
            label="최대 간격 (분)",
            hint_text="예: 20",
            width=150,
            value="20"
        )

        timer_max_posts = ft.TextField(
            label="일일 최대 포스팅",
            hint_text="예: 20",
            width=150,
            value="20"
        )

        timer_status_text = ft.Text(
            "타이머 중지됨",
            size=16,
            color=ft.Colors.GREY_600,
            weight=ft.FontWeight.BOLD
        )

        timer_next_post_text = ft.Text(
            "",
            size=14,
            color=ft.Colors.BLUE_600
        )

        # 사용 횟수 추적 텍스트
        daily_usage_text = ft.Text(
            "오늘 사용: 0회 / 30회 (기본)",
            size=14,
            color=ft.Colors.GREEN_600,
            weight=ft.FontWeight.BOLD
        )

        total_usage_text = ft.Text(
            "총 사용: 0회",
            size=12,
            color=ft.Colors.GREY_600
        )

        # 다음 포스팅 시간 표시 텍스트
        next_post_time_text = ft.Text(
            "다음 포스팅 시간: --:--:--",
            size=12,
            color=ft.Colors.BLUE_600,
            weight=ft.FontWeight.BOLD
        )

        def save_user_settings(e, base_dir=None):
            try:
                if base_dir is None:
                    base_dir = self.base_dir
                    
                settings = {
                    "dojang_name": dojang_name.value,
                    "address": address.value,
                    "phone": phone.value,
                    "blog_url": blog_url.value,
                    "naver_id": naver_id.value,
                    "naver_pw": naver_pw.value,
                    "kakao_url": kakao_url.value,
                    "blog_tags": blog_tags.value,
                    "blog_topics": blog_topics.value,
                    "band_topics": band_topics.value,
                    "cafe_topics": cafe_topics.value,
                    "blog_slogan": blog_slogan.value,
                    "cafe_slogan": cafe_slogan.value,
                    "band_slogan": band_slogan.value,
                    "slogan": blog_slogan.value, # 하위 호환성 유지 (naver_blog_auto.py용)
                    "blog_first_sentence": blog_first_sentence.value,
                    "cafe_first_sentence": cafe_first_sentence.value,
                    "band_first_sentence": band_first_sentence.value,
                    "reply_instruction": reply_instruction.value,  # 답글 지침
                    "default_reply": default_reply.value,  # 기본 답글 문구
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                with open(os.path.join(base_dir, 'config/user_settings.txt'), 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)
                
                # 환경 변수 설정
                os.environ['NAVER_ID'] = naver_id.value
                os.environ['NAVER_PW'] = naver_pw.value
                
                page.snack_bar = ft.SnackBar(content=ft.Text("사용자 설정이 저장되었습니다."))
                page.snack_bar.open = True
                page.update()
            except Exception as e:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"저장 중 오류 발생: {str(e)}"))
                page.snack_bar.open = True
                page.update()

        def load_user_settings():
            try:
                if os.path.exists(os.path.join(self.base_dir, 'config/user_settings.txt')):
                    with open(os.path.join(self.base_dir, 'config/user_settings.txt'), 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                        dojang_name.value = settings.get('dojang_name', '')
                        address.value = settings.get('address', '')
                        phone.value = settings.get('phone', '')
                        blog_url.value = settings.get('blog_url', '')
                        naver_id.value = settings.get('naver_id', '')
                        naver_pw.value = settings.get('naver_pw', '')
                        kakao_url.value = settings.get('kakao_url', '')
                        blog_tags.value = settings.get('blog_tags', '')
                        blog_topics.value = settings.get('blog_topics', '')
                        band_topics.value = settings.get('band_topics', '')
                        cafe_topics.value = settings.get('cafe_topics', '')
                        blog_slogan.value = settings.get('blog_slogan', settings.get('slogan', ''))
                        cafe_slogan.value = settings.get('cafe_slogan', '')
                        band_slogan.value = settings.get('band_slogan', '')
                        blog_first_sentence.value = settings.get('blog_first_sentence', settings.get('first_sentence', ''))
                        cafe_first_sentence.value = settings.get('cafe_first_sentence', '')
                        band_first_sentence.value = settings.get('band_first_sentence', '')
                        reply_instruction.value = settings.get('reply_instruction', '- 댓글 내용에 공감하며 감사 표현\n- 15~30자 이내로 짧게 작성\n- 이모지 1개만 포함')
                        default_reply.value = settings.get('default_reply', '감사합니다😊,좋은 말씀 감사해요💕,응원 감사합니다🙏,행복한 하루 되세요✨,방문 감사합니다🌻')
                        page.update()
            except Exception as e:
                print(f"사용자 설정 로드 중 오류 발생: {str(e)}")

        def save_timer_settings(e):
            try:
                settings = {
                    "start_time": timer_start_time.value,
                    "end_time": timer_end_time.value,
                    "min_interval": timer_min_interval.value,
                    "max_interval": timer_max_interval.value,
                    "max_posts": timer_max_posts.value,
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                with open(os.path.join(self.base_dir, 'config/timer_settings.json'), 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)
                
                # 🎯 실행 중인 타이머에 새 설정 즉시 적용
                if self.timer_running:
                    print("📝 타이머 설정이 변경되었습니다. 새 설정을 즉시 적용합니다.")
                    
                    # 다음 포스팅 시간을 새로운 설정으로 재계산
                    self.calculate_next_post_time(settings)
                    print(f"🔄 새로운 다음 포스팅 시간: {self.next_post_time.strftime('%H:%M:%S')}")
                
                page.snack_bar = ft.SnackBar(content=ft.Text("⚡ 시간 설정이 저장되고 즉시 적용되었습니다!"))
                page.snack_bar.open = True
                page.update()
            except Exception as e:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"저장 중 오류 발생: {str(e)}"))
                page.snack_bar.open = True
                page.update()

        def load_timer_settings():
            try:
                if os.path.exists(os.path.join(self.base_dir, 'config/timer_settings.json')):
                    with open(os.path.join(self.base_dir, 'config/timer_settings.json'), 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                        timer_start_time.value = settings.get('start_time', '09:00')
                        timer_end_time.value = settings.get('end_time', '23:00')
                        timer_min_interval.value = settings.get('min_interval', '15')
                        timer_max_interval.value = settings.get('max_interval', '20')
                        timer_max_posts.value = settings.get('max_posts', '20')
                        page.update()
            except Exception as e:
                print(f"시간 설정 로드 중 오류 발생: {str(e)}")

        def load_usage_stats():
            """사용 통계 로드"""
            try:
                usage_file = os.path.join(self.base_dir, 'config/usage_stats.json')
                if os.path.exists(usage_file):
                    with open(usage_file, 'r', encoding='utf-8') as f:
                        stats = json.load(f)
                        
                    today = datetime.now().strftime("%Y-%m-%d")
                    daily_count = stats.get('daily', {}).get(today, 0)
                    total_count = stats.get('total', 0)
                    
                    # 사용량에 따른 색상 변경
                    if daily_count >= 30:
                        color = ft.Colors.RED_600
                        status = f"오늘 사용: {daily_count}회 / 30회 (추가비용 발생!)"
                    elif daily_count >= 25:
                        color = ft.Colors.ORANGE_600
                        status = f"오늘 사용: {daily_count}회 / 30회 (주의)"
                    else:
                        color = ft.Colors.GREEN_600
                        status = f"오늘 사용: {daily_count}회 / 30회 (기본)"
                    
                    daily_usage_text.value = status
                    daily_usage_text.color = color
                    total_usage_text.value = f"총 사용: {total_count}회"
                    page.update()
                    
            except Exception as e:
                print(f"사용 통계 로드 중 오류 발생: {str(e)}")

        def save_usage_stats():
            """사용 통계 저장"""
            try:
                usage_file = os.path.join(self.base_dir, 'config/usage_stats.json')
                
                # 기존 통계 로드
                if os.path.exists(usage_file):
                    with open(usage_file, 'r', encoding='utf-8') as f:
                        stats = json.load(f)
                else:
                    stats = {'daily': {}, 'total': 0}
                
                # 오늘 날짜
                today = datetime.now().strftime("%Y-%m-%d")
                
                # 일일 카운트 증가
                if today not in stats['daily']:
                    stats['daily'][today] = 0
                stats['daily'][today] += 1
                
                # 총 카운트 증가
                stats['total'] += 1
                
                # 30일 이전 데이터 정리 (용량 절약)
                from datetime import timedelta
                cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                stats['daily'] = {k: v for k, v in stats['daily'].items() if k >= cutoff_date}
                
                # 저장
                with open(usage_file, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, ensure_ascii=False, indent=2)
                
                # UI 업데이트
                load_usage_stats()
                
            except Exception as e:
                print(f"사용 통계 저장 중 오류 발생: {str(e)}")

        def increment_usage_count():
            """사용 횟수 증가 (포스팅할 때마다 호출)"""
            save_usage_stats()

        # 자동 저장 함수
        def auto_save(e=None):
            try:
                if title_input.value or content_input.value:
                    save_data = {
                        "title": title_input.value,
                        "content": content_input.value,
                        "last_saved": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    with open(os.path.join(self.base_dir, 'drafts/auto_save.json'), 'w', encoding='utf-8') as f:
                        json.dump(save_data, f, ensure_ascii=False, indent=2)
                    
                    status_text.value = f"마지막 저장: {save_data['last_saved']}"
                    page.update()
            except Exception as e:
                print(f"자동 저장 중 오류 발생: {str(e)}")

        def load_draft():
            try:
                if os.path.exists(os.path.join(self.base_dir, 'drafts/auto_save.json')):
                    with open(os.path.join(self.base_dir, 'drafts/auto_save.json'), 'r', encoding='utf-8') as f:
                        save_data = json.load(f)
                        title_input.value = save_data.get('title', '')
                        content_input.value = save_data.get('content', '')
                        if save_data.get('last_saved'):
                            status_text.value = f"마지막 저장: {save_data['last_saved']}"
                        page.update()
            except Exception as e:
                print(f"임시 저장 로드 중 오류 발생: {str(e)}")

        # 제목과 내용이 변경될 때마다 자동 저장
        def on_title_changed(e):
            auto_save()

        def on_content_changed(e):
            auto_save()

        # 상태 표시 텍스트
        status_text = ft.Text(
            value="",
            color=ft.Colors.GREY_700,
            size=12,
            italic=True
        )

        # UI 컴포넌트
        topic_input = ft.TextField(
            label="주제 입력",
            hint_text="블로그 포스트 주제를 입력하세요...",
            multiline=True,
            min_lines=2,
            max_lines=3,
            expand=True
        )

        chat_messages = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=10
        )

        title_input = ft.TextField(
            label="제목",
            hint_text="블로그 포스트 제목을 입력하세요...",
            multiline=True,
            min_lines=1,
            max_lines=2,
            expand=True,
            on_change=on_title_changed
        )

        content_input = ft.TextField(
            label="본문",
            hint_text="블로그 포스트 내용을 입력하세요...",
            multiline=True,
            min_lines=15,
            max_lines=30,
            expand=True,
            on_change=self.on_content_change
        )

        # 메시지 전송 처리
        def send_message(e):
            start_time = time.time()
            self._debug_log("H4", "blog_writer_app.send_message", "send_message start", {"auto_topic": bool(auto_topic_checkbox.value)}, run_id="run2")
            # 자동 주제 모드 체크
            if auto_topic_checkbox.value:
                # 순차적 주제 선택
                selected_topic = self.select_sequential_topic('blog')
                self._debug_log("H4", "blog_writer_app.send_message", "auto topic selected", {"selected_topic": selected_topic, "current_topic_index": self.topic_indices['blog']}, run_id="run2")
                if not selected_topic:
                    page.snack_bar = ft.SnackBar(content=ft.Text("자동 주제 선택 실패: 주제 목록이 비어 있습니다. 사용자 설정에서 주제를 추가해주세요."))
                    page.snack_bar.open = True
                    page.update()
                    return
                # 선택된 주제를 입력 필드에 설정
                topic_input.value = selected_topic
                page.update()
                
            # 수동 모드 체크
            if not topic_input.value:
                return

            # 입력값 처리
            chat_messages.controls.append(ft.Container(
                content=ft.Text(f"입력: {topic_input.value}"),
                bgcolor=ft.Colors.BLUE_100,
                padding=10,
                border_radius=10,
                margin=ft.margin.only(bottom=10)
            ))
            
            # 처리 중 표시
            progress_dlg = ft.AlertDialog(
                title=ft.Text("처리 중..."),
                content=ft.Column([
                    ft.Text("GPT가 글을 생성하고 있습니다. 잠시만 기다려주세요."),
                    ft.ProgressBar(width=400)
                ], tight=True),
            )
            page.dialog = progress_dlg
            progress_dlg.open = True
            model_spinner.visible = True
            current_model_text.value = "현재 모델: 생성 중..."
            page.update()
            
            try:
                # GPT 응답 생성
                # 포스팅 타입 결정 (비율 기반)
                try:
                    promo_num = int(promotional_ratio.value or "0")
                    info_num = int(informational_ratio.value or "0")
                except:
                    promo_num, info_num = 0, 0
                total_cycle = promo_num + info_num if (promo_num + info_num) > 0 else 0
                is_promotional = False
                if total_cycle > 0:
                    idx = (self.daily_post_count % total_cycle)
                    is_promotional = idx < promo_num
                post_type_config = {
                    "is_promotional": is_promotional,
                    "promotional_instructions": promotional_instructions.value,
                    "informational_instructions": informational_instructions.value,
                    "selected_models": [mid for mid, cb in model_checkboxes.items() if cb.value],
                    "gemini_api_key": gemini_api_key_field.value
                }
                result = self.gpt_handler.generate_content(
                    topic_input.value,
                    post_order=self.daily_post_count + 1,
                    post_type_config=post_type_config
                )
                duration = time.time() - start_time
                self.current_title = result["title"]
                self.current_content = result["content"]
                current_model_text.value = f"현재 모델: {result.get('model','-')}"
                # AI 사용 로그 기록 (성공)
                self.add_model_usage_log(
                    topic=topic_input.value,
                    model=result.get("model", "-"),
                    status="성공",
                    reason="-",
                    target="블로그",
                    duration_sec=duration
                )

                # 제목과 내용 업데이트
                title_input.value = self.current_title
                content_input.value = self.current_content

                # GPT 응답 표시
                chat_messages.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Text("제목: " + result["title"], size=16, weight=ft.FontWeight.BOLD),
                        ft.Text(result["content"])
                    ]),
                    bgcolor=ft.Colors.GREY_100,
                    padding=10,
                    border_radius=10,
                    margin=ft.margin.only(bottom=10)
                ))
                
                # 진행 대화상자 닫기
                progress_dlg.open = False
                model_spinner.visible = False
                page.update()
                
                # 자동 업로드가 설정된 경우
                if auto_upload_checkbox.value:
                    upload_result = upload_to_blog(None)
                    # 업로드 결과를 저장 (자동 포스팅에서 사용)
                    if hasattr(self, 'last_upload_success'):
                        self.last_upload_success = upload_result if upload_result is not None else False
                
            except Exception as e:
                duration = time.time() - start_time
                # 진행 대화상자 닫기
                progress_dlg.open = False
                model_spinner.visible = False
                current_model_text.value = "현재 모델: 오류 발생"
                page.update()
                # AI 사용 로그 기록 (실패)
                self.add_model_usage_log(
                    topic=topic_input.value,
                    model="-",
                    status="실패",
                    reason=str(e),
                    target="블로그",
                    duration_sec=duration
                )

                chat_messages.controls.append(ft.Container(
                    content=ft.Text(f"오류 발생: {str(e)}", color=ft.Colors.RED),
                    padding=10,
                    margin=ft.margin.only(bottom=10)
                ))
            
            # 자동 주제 모드이고 입력 필드를 지우는 경우에만 - 다음 자동 선택을 위해
            if auto_topic_checkbox.value:
                topic_input.value = ""
            else:
                topic_input.value = ""  # 수동 모드에서도 입력 필드 초기화
            model_spinner.visible = False
            page.update()
            page.update()

        # 블로그 업로드 처리
        def upload_to_blog(e=None, is_retry: bool = False):
            start_time = time.time()
            print("🚀 업로드 버튼 클릭됨")
            
            if not title_input.value or not content_input.value:
                page.snack_bar = ft.SnackBar(content=ft.Text("제목과 내용을 모두 입력해주세요."))
                page.snack_bar.open = True
                page.update()
                return

            # 로그인 상태 확인 (브라우저 인스턴스 확인) - 디버깅 정보 추가
            print(f"🔍 브라우저 상태 확인:")
            print(f"  - hasattr(self, 'browser_driver'): {hasattr(self, 'browser_driver')}")
            if hasattr(self, 'browser_driver'):
                print(f"  - self.browser_driver is not None: {self.browser_driver is not None}")
                if self.browser_driver:
                    try:
                        current_url = self.browser_driver.current_url
                        print(f"  - 현재 브라우저 URL: {current_url}")
                    except Exception as browser_e:
                        print(f"  - 브라우저 상태 확인 중 오류: {browser_e}")
                        self.browser_driver = None
            
            if not hasattr(self, 'browser_driver') or not self.browser_driver:
                # 저장된 쿠키가 있는지 확인
                cookies_file = os.path.join(self.base_dir, 'naver_cookies.json')
                if os.path.exists(cookies_file):
                    print("💾 저장된 쿠키 발견, 새 브라우저 세션 생성 시도...")
                    try:
                        # 새 브라우저 생성 및 쿠키 로드
                        from manual_session_helper import ManualSessionHelper
                        helper = ManualSessionHelper()
                        helper.setup_driver()
                        
                        # 네이버 메인 페이지로 이동
                        helper.driver.get('https://www.naver.com')
                        time.sleep(2)
                        
                        # 쿠키 로드
                        with open(cookies_file, 'r', encoding='utf-8') as f:
                            cookies = json.load(f)
                        
                        for cookie in cookies:
                            try:
                                helper.driver.add_cookie(cookie)
                            except Exception as cookie_e:
                                print(f"쿠키 추가 실패: {cookie.get('name', 'unknown')} - {cookie_e}")
                        
                        # 페이지 새로고침하여 로그인 상태 적용
                        helper.driver.refresh()
                        time.sleep(3)
                        
                        # 내 블로그로 이동
                        helper.driver.get('https://blog.naver.com')
                        time.sleep(3)
                        
                        # 로그인 상태 확인
                        page_source = helper.driver.page_source
                        if "로그아웃" in page_source or "님" in page_source:
                            self.browser_driver = helper.driver
                            print("✅ 저장된 쿠키로 브라우저 세션 복원 성공!")
                            page.snack_bar = ft.SnackBar(
                                content=ft.Text("✅ 저장된 로그인 정보로 브라우저 세션을 복원했습니다!"),
                                bgcolor=ft.Colors.GREEN
                            )
                            page.snack_bar.open = True
                            page.update()
                        else:
                            helper.driver.quit()
                            raise Exception("쿠키로 로그인 복원 실패")
                            
                    except Exception as restore_e:
                        print(f"❌ 브라우저 세션 복원 실패: {restore_e}")
                        page.snack_bar = ft.SnackBar(
                            content=ft.Text("❌ 브라우저 세션이 없습니다.\n\n1. '네이버 로그인' 버튼 클릭\n2. 브라우저에서 로그인 완료\n3. '로그인 완료' 버튼 클릭\n\n위 단계를 완료한 후 다시 시도해주세요."),
                            bgcolor=ft.Colors.ORANGE
                        )
                        page.snack_bar.open = True
                        page.update()
                        return
                else:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text("❌ 브라우저 세션이 없습니다.\n\n1. '네이버 로그인' 버튼 클릭\n2. 브라우저에서 로그인 완료\n3. '로그인 완료' 버튼 클릭\n\n위 단계를 완료한 후 다시 시도해주세요."),
                        bgcolor=ft.Colors.ORANGE
                    )
                    page.snack_bar.open = True
                    page.update()
                    return

            try:
                # 업로드 진행 상태 표시
                progress = ft.ProgressBar(width=400)
                dlg = ft.AlertDialog(
                    title=ft.Text("업로드 중..."),
                    content=ft.Column([
                        ft.Text("네이버 블로그에 포스팅을 업로드하고 있습니다."),
                        progress
                    ], tight=True),
                )
                page.dialog = dlg
                dlg.open = True
                page.update()

                # 줄바꿈 처리 (한 줄이 25자를 넘지 않도록, 단어가 잘리지 않게)
                def format_content_for_mobile(content, max_chars=25):
                    formatted_content = ""
                    paragraphs = content.split('\n')
                    
                    for paragraph in paragraphs:
                        if not paragraph.strip():
                            formatted_content += "\n"
                            continue
                            
                        words = paragraph.split()
                        current_line = ""
                        
                        for word in words:
                            # 단어 자체가 max_chars보다 길면 그대로 사용
                            if len(word) > max_chars:
                                if current_line:
                                    formatted_content += current_line + "\n"
                                    current_line = ""
                                formatted_content += word + "\n"
                                continue
                                
                            # 현재 줄에 단어를 추가했을 때 max_chars를 초과하는지 확인
                            if len(current_line) + len(word) + (1 if current_line else 0) > max_chars:
                                formatted_content += current_line + "\n"
                                current_line = word
                            else:
                                if current_line:
                                    current_line += " " + word
                                else:
                                    current_line = word
                        
                        # 마지막 줄 추가
                        if current_line:
                            formatted_content += current_line + "\n"
                        
                        # 문단 사이에 빈 줄 추가
                        formatted_content += "\n"
                    
                    return formatted_content.strip()
                
                # 원본 내용을 모바일 친화적으로 포맷팅
                formatted_content = format_content_for_mobile(content_input.value)
                
                # 임시 파일에 내용 저장
                today = datetime.now().strftime("%Y-%m-%d")
                os.makedirs(os.path.join(self.base_dir, today), exist_ok=True)
                
                file_path = os.path.join(os.path.join(self.base_dir, today), f"{title_input.value}.txt")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"제목: {title_input.value}\n\n{formatted_content}")

                try:
                    # 기존 naver_blog_auto.py 시스템 활용
                    dlg.content.controls[0].value = "네이버 블로그 자동화 시스템 초기화 중..."
                    page.update()
                    
                    # naver_blog_auto.py import
                    from naver_blog_auto import NaverBlogAutomation
                    
                    # --- 이미지 폴더 선택: 포스트 단위로 한 폴더만 고정 사용 ---
                    custom_images_folder = None
                    images_available = False
                    try:
                        folder_path = self.get_next_image_folder()
                        if folder_path and os.path.exists(folder_path):
                            valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
                            files = [
                                f for f in os.listdir(folder_path)
                                if os.path.splitext(f)[1].lower() in valid_exts
                            ]
                            if files:
                                custom_images_folder = folder_path
                                images_available = True
                                print(f"커스텀 이미지 폴더 사용(포스트 단위 고정): {folder_path}")
                            else:
                                print(f"선택된 폴더에 이미지가 없습니다. 이번 포스팅은 이미지 없이 진행: {folder_path}")
                        else:
                            print("사용 가능한 이미지 폴더를 찾지 못했습니다. 이미지 없이 진행합니다.")
                    except Exception as img_folder_err:
                        print(f"이미지 폴더 선택 오류: {img_folder_err}")
                    
                    # 이번 포스팅에 이미지 삽입 여부 결정 (체크박스 ON + 실제 이미지 존재)
                    auto_image_enabled = auto_image_checkbox.value and images_available
                    
                    # 자동화 인스턴스 생성 (기존 브라우저 세션 활용)
                    blog_auto = NaverBlogAutomation(
                        auto_mode=auto_image_enabled,  # 포스트 단위 이미지 사용 여부
                        image_insert_mode="random",
                        use_stickers=False,
                        custom_images_folder=custom_images_folder  # 포스트별 단일 폴더 고정
                    )
                    
                    # 기본 디렉토리를 현재 작업 디렉토리로 설정하여 설정 파일 경로 보정
                    blog_auto.base_dir = self.base_dir
                    
                    # 설정을 다시 로드하여 슬로건 등 최신 설정 반영
                    blog_auto.settings = blog_auto.load_settings()
                    
                    # 기존 브라우저 세션을 naver_blog_auto에 전달
                    blog_auto.driver = self.browser_driver
                    
                    # 이미지 삽입 핸들러 수동 초기화 (기존 브라우저 세션 사용 시)
                    if auto_image_checkbox.value and blog_auto.driver:
                        print("🖼️ 이미지 삽입 핸들러 수동 초기화 중...")
                        from naver_blog_auto_image import NaverBlogImageInserter
                        
                        fallback_folder = blog_auto.custom_images_folder if blog_auto.custom_images_folder else blog_auto.default_images_folder
                        print(f"사용할 이미지 폴더: {fallback_folder}")
                        
                        blog_auto.image_inserter = NaverBlogImageInserter(
                            driver=blog_auto.driver,
                            images_folder=blog_auto.images_folder,
                            insert_mode=blog_auto.image_insert_mode,
                            fallback_folder=fallback_folder
                        )
                        print("✅ 이미지 삽입 핸들러 수동 초기화 완료")
                    else:
                        print("ℹ️ 이미지 자동 삽입이 비활성화되어 있습니다.")
                        blog_auto.image_inserter = None
                    
                    dlg.content.controls[0].value = "블로그 포스팅 작성 중..."
                    page.update()
                    
                    # 태그 로드
                    tags = []
                    if os.path.exists(os.path.join(self.base_dir, 'config/user_settings.txt')):
                        with open(os.path.join(self.base_dir, 'config/user_settings.txt'), 'r', encoding='utf-8') as f:
                            settings = json.load(f)
                            tags = [tag.strip() for tag in settings.get('blog_tags', '').split(',') if tag.strip()]
                    
                    # 블로그 포스팅 작성 (1차 시도, 실패 시 1회 재시도)
                    last_err = None
                    for attempt in range(2):
                        try:
                            success = blog_auto.write_post(
                                title=title_input.value,
                                content=formatted_content,
                                tags=tags
                            )
                            if success:
                                last_err = None
                                break
                            else:
                                raise Exception("블로그 포스팅 작성에 실패했습니다")
                        except Exception as attempt_err:
                            last_err = attempt_err
                            print(f"업로드 시도 {attempt + 1} 실패: {attempt_err}")
                            if attempt == 0:
                                print("➡️ 업로드를 한 번 더 재시도합니다.")
                                time.sleep(1)
                                continue
                            else:
                                raise attempt_err
                    
                    if last_err:
                        raise last_err
                    
                    # 사용 횟수 증가
                    increment_usage_count()
                    
                    # 업로드 성공 로그
                    duration = time.time() - start_time
                    self.add_model_usage_log(
                        topic=title_input.value,
                        model=current_model_text.value.replace("현재 모델: ", ""),
                        status="업로드 성공",
                        reason="네이버 블로그",
                        target="블로그 업로드",
                        duration_sec=duration
                    )
                    
                    dlg.open = False
                    page.update()
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text("✅ 블로그에 성공적으로 업로드되었습니다! 브라우저는 다음 업로드를 위해 유지됩니다."),
                        bgcolor=ft.Colors.GREEN
                    )
                    page.snack_bar.open = True
                    page.update()
                    
                    # 성공 상태 저장
                    if hasattr(self, 'last_upload_success'):
                        self.last_upload_success = True
                    
                    return True  # 성공 반환
                        
                except Exception as e:
                    print(f"naver_blog_auto 업로드 중 오류 발생: {str(e)}")
                    raise e
                    
            except Exception as e:
                print(f"업로드 중 오류 발생: {str(e)}")
                dlg.open = False
                page.update()
                page.snack_bar = ft.SnackBar(content=ft.Text(f"업로드 중 오류가 발생했습니다: {str(e)}"))
                page.snack_bar.open = True
                page.update()
                
                # 업로드 실패 로그
                duration = time.time() - start_time
                self.add_model_usage_log(
                    topic=title_input.value,
                    model=current_model_text.value.replace("현재 모델: ", ""),
                    status="업로드 실패",
                    reason=str(e),
                    target="블로그 업로드",
                    duration_sec=duration
                )
                
                # 실패 상태 저장
                if hasattr(self, 'last_upload_success'):
                    self.last_upload_success = False
                
                # 5초 후 1회 자동 재시도 (재귀 방지)
                if not is_retry:
                    print("⚠️ 업로드 실패, 5초 후 한 번 더 재시도합니다.")
                    def _retry():
                        try:
                            if hasattr(page, "invoke_later"):
                                page.invoke_later(lambda: upload_to_blog(None, True))
                            else:
                                upload_to_blog(None, True)
                        except Exception as retry_err:
                            print(f"재시도 예약 중 오류: {retry_err}")
                    threading.Timer(5, _retry).start()
                
                return False  # 실패 반환

        # 버튼 컴포넌트
        send_button = ft.ElevatedButton(
            text="전송",
            icon=ft.Icons.SEND,
            on_click=send_message
        )

        upload_button = ft.ElevatedButton(
            text="블로그에 업로드",
            icon=ft.Icons.UPLOAD,
            on_click=lambda e: upload_to_blog(e, False)
        )

        # GPT 설정 저장 버튼
        save_gpt_button = ft.ElevatedButton(
            text="GPT 설정 저장",
            icon=ft.Icons.SAVE,
            on_click=save_gpt_settings
        )

        # 사용자 설정 저장 버튼
        save_user_button = ft.ElevatedButton(
            text="사용자 설정 저장",
            icon=ft.Icons.SAVE,
            on_click=lambda e: save_user_settings(e, self.base_dir)
        )

        # 왼쪽 패널
        auto_topic_status = ft.Text(
            value="자동 주제 모드: " + ("활성화" if auto_topic_checkbox.value else "비활성화"),
            color=ft.Colors.GREEN if auto_topic_checkbox.value else ft.Colors.GREY_600,
            size=12,
            italic=True,
            visible=True
        )
        # 현재 사용 모델 표시
        current_model_text = ft.Text(
            value="현재 모델: -",
            size=12,
            color=ft.Colors.BLUE_800
        )
        model_spinner = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)
        
        left_panel = ft.Column(
            controls=[
                topic_input,
                ft.Row(
                    controls=[
                        send_button,
                        auto_topic_status
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                # 사용 현황
                ft.Container(
                    content=ft.Column([
                        ft.Text("📊 사용 현황", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_700),
                        daily_usage_text,
                        total_usage_text,
                        next_post_time_text,
                        ft.Row([model_spinner, current_model_text], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=10,
                    margin=ft.margin.only(top=10, bottom=10),
                    bgcolor=ft.Colors.PURPLE_50,
                    border_radius=8,
                    border=ft.border.all(1, ft.Colors.PURPLE_200)
                ),
                chat_messages
            ],
            spacing=10,
            expand=True
        )

        # 오른쪽 패널
        right_panel = ft.Column(
            controls=[
                title_input,
                content_input,
                auto_image_checkbox,
                auto_image_help_text,
                auto_final_publish_checkbox,
                auto_final_publish_help_text,
                upload_button,
                status_text
            ],
            spacing=10,
            expand=True
        )

        # GPT 설정 탭
        gpt_settings_tab = ft.Container(
            content=ft.Column(
                controls=[
                    gpt_persona,
                    persona_help_text,
                    gpt_instructions,
                    instructions_help_text,
                    gpt_style,
                    style_help_text,
                    ft.Divider(),
                    ft.Text("모델 선택 및 비용 안내", size=16, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Column([
                            ft.Container(  # 상단 월 비용 요약 셀
                                content=model_cost_summary,
                                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                                bgcolor=ft.Colors.WHITE,
                                border_radius=6,
                                border=ft.border.all(1, ft.Colors.BLUE_100),
                                height=36,
                                alignment=ft.alignment.center_left
                            ),
                            ft.Container(  # 선택된 모델 개수 셀
                                content=model_info_text,
                                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                                bgcolor=ft.Colors.WHITE,
                                border_radius=6,
                                border=ft.border.all(1, ft.Colors.BLUE_100),
                                alignment=ft.alignment.center_left
                            ),
                            ft.Container(  # 모델별 월 비용 셀
                                content=ft.Column(
                                    controls=[model_cost_info],
                                    scroll=ft.ScrollMode.ALWAYS,
                                    expand=True,
                                    spacing=0
                                ),
                                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                                bgcolor=ft.Colors.WHITE,
                                border_radius=6,
                                border=ft.border.all(1, ft.Colors.BLUE_100),
                                alignment=ft.alignment.center_left,
                                height=110,
                            ),
                            ft.Container(  # 체크박스 리스트 셀
                                content=ft.ListView(
                                    controls=list(model_checkboxes.values()),
                                    spacing=4,
                                    expand=True,
                                    auto_scroll=False
                                ),
                                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                                bgcolor=ft.Colors.WHITE,
                                border_radius=6,
                                border=ft.border.all(1, ft.Colors.BLUE_100),
                                height=220,
                            ),
                            ft.Container(  # 모델 설명 셀
                                content=ft.Column(
                                    controls=[model_desc_text],
                                    scroll=ft.ScrollMode.ALWAYS,
                                    expand=True,
                                    spacing=0
                                ),
                                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                                bgcolor=ft.Colors.WHITE,
                                border_radius=6,
                                border=ft.border.all(1, ft.Colors.BLUE_100),
                                alignment=ft.alignment.center_left,
                                height=120,
                            ),
                        ], spacing=8),
                        padding=12,
                        bgcolor=ft.Colors.BLUE_50,
                        border_radius=8,
                        border=ft.border.all(1, ft.Colors.BLUE_100)
                    ),
                    ft.Divider(),
                    ft.Text("홍보/정보 지침과 비율", size=16, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                promotional_ratio,
                                informational_ratio
                            ], spacing=10),
                            ft.Row([
                                ft.TextButton("홍보성 예시 보기", on_click=show_promo_example),
                                ft.TextButton("정보성 예시 보기", on_click=show_info_example)
                            ], spacing=10),
                            promotional_instructions,
                            informational_instructions,
                        ], spacing=8),
                        padding=12,
                        bgcolor=ft.Colors.GREY_50,
                        border_radius=8,
                        border=ft.border.all(1, ft.Colors.GREY_200)
                    ),
                    ft.Divider(),
                    ft.Text("플랫폼별 전용 지침 (밴드/카페/소통)", size=16, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Column([
                            band_instructions,
                            cafe_instructions,
                            idle_instructions
                        ], spacing=10),
                        padding=12,
                        bgcolor=ft.Colors.GREEN_50,
                        border_radius=8,
                        border=ft.border.all(1, ft.Colors.GREEN_100)
                    ),
                    ft.Divider(),
                    ft.Text("API 및 자동화 옵션", size=16, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Column([
                            use_api_checkbox,
                            api_key_field,
                            gemini_api_key_field,
                            api_key_help_text,
                            auto_upload_checkbox,
                            auto_upload_help_text,
                            auto_topic_checkbox,
                            auto_topic_help_text,
                            auto_final_publish_checkbox,
                            auto_final_publish_help_text
                        ], spacing=6),
                        padding=12,
                        bgcolor=ft.Colors.AMBER_50,
                        border_radius=8,
                        border=ft.border.all(1, ft.Colors.AMBER_100)
                    ),
                    ft.Divider(),
                    ft.Text("💬 댓글 답글 설정", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_700),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("댓글에 자동 답글할 때 사용되는 지침입니다.", size=12, color=ft.Colors.GREY_600),
                            reply_instruction,
                            default_reply,
                            ft.Text("ℹ️ AI 답글: 위 지침 참고 | 기본 답글: 아래 문구 순차 사용", size=11, color=ft.Colors.GREY_500, italic=True)
                        ], spacing=8),
                        padding=12,
                        bgcolor=ft.Colors.PURPLE_50,
                        border_radius=8,
                        border=ft.border.all(1, ft.Colors.PURPLE_100)
                    ),
                    save_gpt_button
                ],
                spacing=20,
                scroll=ft.ScrollMode.AUTO
            ),
            padding=20,
            expand=True
        )

        # 시간 설정 탭
        timer_settings_tab = ft.Container(
            content=ft.Column(
                controls=[
                    # 시간 설정 설명
                    ft.Container(
                        content=ft.Column([
                            ft.Text("⏰ 자동 시간 설정", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                            ft.Text("설정된 시간에 자동으로 블로그 포스팅을 진행합니다.", size=14, color=ft.Colors.GREY_700),
                            ft.Text("🎯 네이버 자동화 감지를 피하기 위한 랜덤 간격 설정", 
                                   size=12, color=ft.Colors.GREEN_600, weight=ft.FontWeight.BOLD)
                        ]),
                        padding=20,
                        border=ft.border.all(2, ft.Colors.BLUE_300),
                        border_radius=10,
                        margin=10,
                        bgcolor=ft.Colors.BLUE_50
                    ),
                    
                    # 운영 시간 설정
                    ft.Container(
                        content=ft.Column([
                            ft.Text("🕐 운영 시간 설정", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_700),
                            ft.Text("매일 자동으로 시작/종료되는 시간을 설정하세요", size=14, color=ft.Colors.GREY_600),
                            ft.Row([
                                timer_start_time,
                                ft.Text("부터", size=16, color=ft.Colors.GREY_700),
                                timer_end_time,
                                ft.Text("까지", size=16, color=ft.Colors.GREY_700)
                            ], alignment=ft.MainAxisAlignment.START),
                            ft.Text("💡 권장: 오전 9시부터 오후 11시까지 (14시간 운영)", 
                                   size=12, color=ft.Colors.GREY_500, italic=True)
                        ]),
                        padding=20,
                        border=ft.border.all(1, ft.Colors.PURPLE_200),
                        border_radius=10,
                        margin=10,
                        bgcolor=ft.Colors.PURPLE_50
                    ),
                    
                    # 포스팅 간격 설정
                    ft.Container(
                        content=ft.Column([
                            ft.Text("🎲 포스팅 간격 설정", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700),
                            ft.Text("랜덤 간격으로 포스팅하여 자동화 감지를 방지합니다", size=14, color=ft.Colors.GREY_600),
                            ft.Row([
                                timer_min_interval,
                                ft.Text("분 ~", size=16, color=ft.Colors.GREY_700),
                                timer_max_interval,
                                ft.Text("분 랜덤 간격", size=16, color=ft.Colors.GREY_700)
                            ], alignment=ft.MainAxisAlignment.START),
                            ft.Text("⚠️ 포스팅 시간(약 5분) 포함하여 계산됩니다", 
                                   size=12, color=ft.Colors.ORANGE_600, italic=True)
                        ]),
                        padding=20,
                        border=ft.border.all(1, ft.Colors.GREEN_200),
                        border_radius=10,
                        margin=10,
                        bgcolor=ft.Colors.GREEN_50
                    ),
                    
                    # 일일 제한 설정
                    ft.Container(
                        content=ft.Column([
                            ft.Text("📊 일일 포스팅 제한", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_700),
                            ft.Text("하루 최대 포스팅 수를 설정하여 과도한 사용을 방지합니다", size=14, color=ft.Colors.GREY_600),
                            ft.Row([
                                ft.Text("하루 최대", size=16, color=ft.Colors.GREY_700),
                                timer_max_posts,
                                ft.Text("개 포스팅", size=16, color=ft.Colors.GREY_700)
                            ], alignment=ft.MainAxisAlignment.START),
                            ft.Text("💰 하루 기본 포스팅 30개이며, 추가 포스팅시 추가비용 발생합니다", 
                                   size=12, color=ft.Colors.RED_600, weight=ft.FontWeight.BOLD)
                        ]),
                        padding=20,
                        border=ft.border.all(1, ft.Colors.ORANGE_200),
                        border_radius=10,
                        margin=10,
                        bgcolor=ft.Colors.ORANGE_50
                    ),
                    
                    # 설정 저장
                    ft.Container(
                        content=ft.Column([
                            ft.Text("💾 설정 저장", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                            ft.Text("변경된 시간 설정을 저장합니다", size=14, color=ft.Colors.GREY_600),
                            ft.ElevatedButton(
                                "설정 저장",
                                on_click=save_timer_settings,
                                bgcolor=ft.Colors.BLUE,
                                color=ft.Colors.WHITE,
                                icon=ft.Icons.SAVE,
                                width=200
                            )
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=20,
                        border=ft.border.all(1, ft.Colors.BLUE_300),
                        border_radius=10,
                        margin=10,
                        bgcolor=ft.Colors.BLUE_50
                    )
                ],
                spacing=20,
                scroll=ft.ScrollMode.AUTO
            ),
            padding=20,
            expand=True
        )

        # 사용자 설정 탭
        user_settings_tab = ft.Container(
            content=ft.Column(
                controls=[
                    dojang_name,
                    address,
                    phone,
                    blog_url,
                    naver_id,
                    naver_pw,
                    kakao_url,
                    blog_tags,
                    blog_topics,
                    band_topics,
                    cafe_topics,

                    ft.Text("슬로건 설정", size=16, weight=ft.FontWeight.BOLD),
                    blog_slogan,
                    cafe_slogan,
                    band_slogan,
                    ft.Text("첫 문장 설정", size=16, weight=ft.FontWeight.BOLD),
                    blog_first_sentence,
                    cafe_first_sentence,
                    band_first_sentence,
                    save_user_button,
                    developer_info
                ],
                spacing=20,
                scroll=ft.ScrollMode.AUTO
            ),
            padding=20,
            expand=True
        )




        # 로그인 버튼 생성
        login_button = self.create_simple_login_button(page)

        # 메인 컨텐츠 탭
        main_content_tab = ft.Column(
            controls=[
                login_button,  # 로그인 버튼을 원래 위치로 복원
                ft.Row(
                    controls=[
                        ft.Container(
                            content=left_panel,
                            padding=10,
                            border=ft.border.all(1, ft.Colors.GREY_400),
                            border_radius=10,
                            expand=True
                        ),
                        ft.Container(
                            content=right_panel,
                            padding=10,
                            border=ft.border.all(1, ft.Colors.GREY_400),
                            border_radius=10,
                            expand=True
                        )
                    ],
                    spacing=20,
                    expand=True
                )
            ],
            spacing=10,
            expand=True
        )

        # AI 사용 로그 탭 UI 구성
        # 카드형 리스트 뷰(테이블 대체용)
        # 스크롤바가 보이도록 ListView에 높이 지정
        self.model_usage_list = ft.ListView(
            spacing=8,
            expand=True,
            height=420,
            auto_scroll=False
        )
        self.model_usage_count_text = ft.Text("총 0건 (최근 200건 표시)", size=12, color=ft.Colors.BLUE_900)
        self.model_usage_latest_text = ft.Text("최근 로그 없음", size=12, color=ft.Colors.BLUE_900)
        self.model_usage_empty = ft.Column(
            controls=[
                ft.Icon(ft.Icons.INSIGHTS_OUTLINED, size=42, color=ft.Colors.BLUE_400),
                ft.Text("아직 기록이 없습니다", size=14, color=ft.Colors.BLUE_800),
                ft.Text("포스팅 생성 또는 업로드 시 자동으로 기록됩니다.", size=12, color=ft.Colors.BLUE_700, italic=True)
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=6,
            visible=True,
            opacity=1.0
        )
        # 초기 데이터 반영은 페이지가 구성된 후 수행
        self.model_usage_initialized = False

        clear_usage_btn = ft.ElevatedButton(
            text="로그 초기화",
            icon=ft.Icons.CLEAR_ALL,
            on_click=lambda _: self._clear_model_usage_logs()
        )
        more_usage_btn = ft.TextButton(
            "더보기",
            on_click=lambda e: self._show_full_usage_panel(),
            icon=ft.Icons.OPEN_IN_NEW
        )
        # 비용 요약 텍스트
        self.model_usage_cost_text = ft.Text("비용: -", size=12, color=ft.Colors.BLUE_900)
        self.model_usage_cost_detail = ft.Text("모델별 비용: -", size=12, color=ft.Colors.GREY_700, selectable=True)

        # 메인 카드 영역과 인라인 전체보기 패널을 교대로 표시하기 위해 참조 보관
        self.model_usage_card_container = self._build_model_usage_card()
        full_panel = self._build_full_usage_panel()
        
        # 스마트 스케줄러 탭 컴포넌트
        self.scheduler_task_list = ft.ListView(expand=True, spacing=10, padding=10)
        
        def edit_task(task):
            # 작업 수정 팝업 (add_new_task와 유사)
            reservation_field = ft.TextField(label="예약 시간 (HH:MM)", value=task.data.get('reservation_time', ''), visible=(task.platform in ['band', 'blog']), hint_text="예: 14:00")
            
            def on_platform_change(e):
                is_reservable = (platform_dropdown.value in ["band", "blog"])
                reservation_field.visible = is_reservable
                page.update()
            
            def save_edit_task(e):
                # 데이터 업데이트
                task.platform = platform_dropdown.value
                task.task_type = type_dropdown.value
                task.start_time_str = start_field.value
                task.end_time_str = end_field.value
                
                # 데이터(예약시간) 처리
                if task.platform in ['band', 'blog'] and reservation_field.value:
                    import re
                    if not re.match(r"^\d{1,2}:\d{2}$", reservation_field.value.strip()):
                         page.snack_bar = ft.SnackBar(content=ft.Text("예약 시간 형식이 올바르지 않습니다 (HH:MM)"))
                         page.snack_bar.open = True
                         page.update()
                         return
                    task.data['reservation_time'] = reservation_field.value.strip()
                elif 'reservation_time' in task.data:
                    del task.data['reservation_time']
                
                # 수정 후 상태 리셋 및 저장
                task.last_status = 'ready'
                task.is_completed = False
                self.scheduler.save_tasks()
                dialog.open = False
                update_scheduler_ui()
                page.update()

            platform_dropdown = ft.Dropdown(
                label="플랫폼",
                options=[ft.dropdown.Option(p) for p in ["blog", "band", "cafe", "idle"]],
                value=task.platform,
                on_change=on_platform_change
            )
            
            # 유형 옵션 다시 정의 (add_new_task와 동일)
            type_options = [
                ft.dropdown.Option(key="morning", text="오전 포스팅 (08:00~11:00)"), 
                ft.dropdown.Option(key="regular", text="일반 포스팅 (11:00~17:00)"), 
                ft.dropdown.Option(key="closing", text="마감 포스팅 (17:00~21:00)"),
                ft.dropdown.Option(key="visit", text="방문소통 활동"),
                ft.dropdown.Option(key="reply", text="댓글소통 활동"),
                ft.dropdown.Option(key="reservation_batch", text="예약 일괄 실행")
            ]
            
            type_dropdown = ft.Dropdown(
                label="유형",
                options=type_options,
                value=task.task_type
            )
            
            # 현재 시간 + 5분으로 자동 설정
            from datetime import datetime, timedelta
            now = datetime.now()
            auto_start = now + timedelta(minutes=5)
            auto_start_str = auto_start.strftime("%H:%M")
            
            # 작업에서 예약 시간 개수 확인하여 종료 시간 계산
            times_count = len(task.data.get('times', [])) if task.data.get('times') else 1
            per_post = task.data.get('per_post_minutes', 1) if task.data.get('per_post_minutes') else 1
            total_minutes = int(times_count * (per_post + 3)) + 10  # 포스팅 3분 + 여유 10분
            auto_end = auto_start + timedelta(minutes=total_minutes)
            auto_end_str = auto_end.strftime("%H:%M")
            
            # 기존 설정값 확인 (우선 사용)
            default_start = task.start_time_str if task.start_time_str else auto_start_str
            default_end = task.end_time_str if task.end_time_str else auto_end_str
            
            start_field = ft.TextField(label="시작 시간", value=default_start)
            end_field = ft.TextField(label="종료 시간", value=default_end)

            dialog = ft.AlertDialog(
                title=ft.Text("작업 수정"),
                content=ft.Column([
                    platform_dropdown, 
                    type_dropdown, 
                    reservation_field,
                    start_field, 
                    end_field
                ], tight=True),
                actions=[
                    ft.TextButton("취소", on_click=lambda _: setattr(dialog, "open", False)),
                    ft.ElevatedButton("저장", on_click=save_edit_task)
                ]
            )
            page.overlay.append(dialog)
            dialog.open = True
            page.update()

        def delete_task(task):
            if task in self.scheduler.tasks:
                self.scheduler.tasks.remove(task)
                self.scheduler.save_tasks()
                update_scheduler_ui()
        
        # 🆕 순서 이동 함수
        def move_task_up(task):
            """작업 순서 위로 이동"""
            self.scheduler.move_task_up(task)
            update_scheduler_ui()
        
        def move_task_down(task):
            """작업 순서 아래로 이동"""
            self.scheduler.move_task_down(task)
            update_scheduler_ui()

        def update_scheduler_ui():
            items = []
            
            type_map = {
                "morning": "오전 포스팅",
                "regular": "일반 포스팅",
                "closing": "마감 포스팅",
                "visit": "방문 소통",
                "reply": "댓글 소통",
                "reservation_batch": "예약 일괄 실행",
                "neighbor": "이웃방문"  # 🆕 추가
            }
            # 🆕 플랫폼 이름 매핑 (더 읽기 좋게 표시)
            platform_map = {
                "blog": "블로그",
                "band": "밴드",
                "cafe": "카페",
                "blog_reply": "블로그 답글",
                "band_reply": "밴드 답글",
                "neighbor_visit": "이웃방문",
                "idle": "대기"
            }
            
            # 🆕 작업별 예상 소요 시간 (분)
            task_duration_map = {
                "morning": 3,
                "regular": 3,
                "closing": 3,
                "visit": 1,
                "reply": 1,
                "reservation_batch": 5,  # 기본값, 실제는 data에서 계산
                "neighbor": 1,
                "댓글답글": 5
            }
            
            # 현재 시간 기준 누적 예상 시간 계산
            from datetime import datetime, timedelta
            current_time = datetime.now()
            cumulative_minutes = 0
            
            for idx, task in enumerate(self.scheduler.tasks):
                order_num = idx + 1  # 순서 번호
                type_text = type_map.get(task.task_type, task.task_type)
                platform_text = platform_map.get(task.platform, task.platform.upper())
                
                # 🎵 플레이리스트 스타일: 순서와 상태만 표시
                is_current = (idx == self.scheduler.current_index and self.scheduler.running)
                
                # 🆕 예상 소요 시간 계산
                estimated_minutes = task_duration_map.get(task.task_type, 3)
                
                # 예약 일괄 실행은 건수에 따라 계산
                if task.data and 'times' in task.data:
                    post_count = len(task.data['times'])
                    per_post_minutes = task.data.get('per_post_minutes', 1)
                    estimated_minutes = int(post_count * (3 + per_post_minutes))  # 포스팅 3분 + 대기
                
                # 방문/답글은 횟수에 따라 계산
                if task.data and 'visit_count' in task.data:
                    estimated_minutes = max(1, task.data['visit_count'] // 2)  # 2회당 1분
                if task.data and 'limit' in task.data:
                    estimated_minutes = max(1, task.data['limit'] // 3)  # 3개당 1분
                
                # 🆕 예상 실행 시간 계산 (앞 작업들의 누적)
                if idx < self.scheduler.current_index or task.is_completed:
                    estimated_time_str = ""  # 이미 완료된 작업
                else:
                    estimated_time = current_time + timedelta(minutes=cumulative_minutes)
                    estimated_time_str = f"⏰ ~{estimated_time.strftime('%H:%M')}"
                    cumulative_minutes += estimated_minutes + 1  # 1분 여유
                
                # 상세 정보 구성
                detail_text = ""
                if task.data and 'times' in task.data:
                    detail_text = f"📦 {len(task.data['times'])}건 예약 포스팅"
                elif task.data and 'reservation_time' in task.data:
                    detail_text = f"📅 예약: {task.data['reservation_time']}"
                # 🆕 횟수 정보 표시
                elif task.data and 'visit_count' in task.data:
                    detail_text = f"🚶 {task.data['visit_count']}회 방문"
                elif task.data and 'limit' in task.data:
                    detail_text = f"💬 {task.data['limit']}개 답글"
                
                # 상태에 따른 색상 및 아이콘 설정
                if is_current:
                    status_color = ft.Colors.BLUE
                    bg_color = ft.Colors.BLUE_100
                    border_color = ft.Colors.BLUE
                    status_icon = ft.Icons.PLAY_ARROW
                    status_text = "▶️ 실행 중"
                elif task.is_completed or task.last_status == 'completed':
                    status_color = ft.Colors.GREEN
                    bg_color = ft.Colors.GREEN_50
                    border_color = ft.Colors.GREEN
                    status_icon = ft.Icons.CHECK_CIRCLE
                    status_text = "✅ 완료"
                elif task.last_status == 'failed':
                    status_color = ft.Colors.RED
                    bg_color = ft.Colors.RED_50
                    border_color = ft.Colors.RED
                    status_icon = ft.Icons.ERROR_OUTLINE
                    status_text = "❌ 실패"
                elif task.last_status == 'paused':
                    status_color = ft.Colors.ORANGE
                    bg_color = ft.Colors.ORANGE_50
                    border_color = ft.Colors.ORANGE
                    status_icon = ft.Icons.PAUSE
                    status_text = "⏸️ 일시정지"
                else:
                    status_color = ft.Colors.GREY
                    bg_color = ft.Colors.GREY_100
                    border_color = ft.Colors.GREY_300
                    status_icon = ft.Icons.CIRCLE_OUTLINED
                    status_text = f"대기 {estimated_time_str}"  # 🆕 예상 시간 표시
                
                items.append(
                    ft.Container(
                        content=ft.Row([
                            # 순서 번호
                            ft.Container(
                                content=ft.Text(f"{order_num}", weight=ft.FontWeight.BOLD, size=16, color=ft.Colors.WHITE),
                                bgcolor=status_color,
                                width=35,
                                height=35,
                                border_radius=17,
                                alignment=ft.alignment.center
                            ),
                            # 작업 정보
                            ft.Column([
                                ft.Text(f"[{platform_text}] {type_text}", weight=ft.FontWeight.BOLD),
                                ft.Text(f"{status_text} {detail_text}", size=11, color=ft.Colors.GREY_600)
                            ], expand=True, spacing=2),
                            # 버튼들
                            ft.Row([
                                # 순서 이동 버튼
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_UPWARD,
                                    icon_color=ft.Colors.GREY_500,
                                    tooltip="위로 이동",
                                    icon_size=18,
                                    on_click=lambda e, t=task: move_task_up(t)
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_DOWNWARD,
                                    icon_color=ft.Colors.GREY_500,
                                    tooltip="아래로 이동",
                                    icon_size=18,
                                    on_click=lambda e, t=task: move_task_down(t)
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_color=ft.Colors.RED_400,
                                    tooltip="삭제",
                                    icon_size=18,
                                    on_click=lambda e, t=task: delete_task(t)
                                )
                            ], spacing=0)
                        ], spacing=10),
                        padding=10,
                        bgcolor=bg_color,
                        border=ft.border.all(2 if is_current else 1, border_color),
                        border_radius=8
                    )
                )
            self.scheduler_task_list.controls = items
            if self.page_ref:
                self.page_ref.update()

        # 인스턴스 메소드로 바인딩 (handle_scheduled_task에서 호출할 수 있도록)
        self.update_scheduler_ui = update_scheduler_ui

        def add_new_task(e):
            # 간단한 작업 추가 팝업
            reservation_field = ft.TextField(label="예약 시간 (HH:MM)", visible=False, hint_text="예: 14:00")
            count_field = ft.TextField(label="횟수", value="10", width=80, visible=False, hint_text="횟수")
            
            def on_platform_change(e):
                # 블로그 또는 밴드 선택 시 예약 시간 필드 노출
                is_reservable = (platform_dropdown.value in ["band", "blog"])
                reservation_field.visible = is_reservable
                
                # 이웃방문/댓글답글 플랫폼 선택 시 횟수 필드 표시
                is_count_platform = platform_dropdown.value in ["neighbor_visit", "blog_reply", "band_reply"]
                count_field.visible = is_count_platform
                
                # 횟수 기본값 설정
                if platform_dropdown.value == "neighbor_visit":
                    count_field.value = "10"
                    count_field.label = "방문 횟수"
                elif platform_dropdown.value in ["blog_reply", "band_reply"]:
                    count_field.value = "5"
                    count_field.label = "답글 횟수"
                
                # 포스팅 플랫폼만 유형 표시 (카페, 블로그, 밴드)
                is_posting_platform = (platform_dropdown.value in ["blog", "band", "cafe"])
                type_dropdown.visible = is_posting_platform
                
                page.update()
            
            def save_new_task(e):
                data = {}
                # 블로그나 밴드이고 예약 시간이 있으면 데이터에 추가
                if platform_dropdown.value in ["band", "blog"] and reservation_field.value:
                    time_val = reservation_field.value.strip()
                    import re
                    if not re.match(r"^\d{1,2}:\d{2}$", time_val):
                        page.snack_bar = ft.SnackBar(content=ft.Text("예약 시간 형식이 올바르지 않습니다 (HH:MM)"))
                        page.snack_bar.open = True
                        page.update()
                        return
                    data['reservation_time'] = time_val
                
                # 댓글 답글 플랫폼이면 task_type을 "댓글답글"로, 횟수 설정
                if platform_dropdown.value in ["blog_reply", "band_reply"]:
                    task_type = "댓글답글"
                    data['immediate'] = True
                    data['limit'] = int(count_field.value) if count_field.value.isdigit() else 5
                # 이웃방문 플랫폼이면 task_type을 "neighbor"로 설정
                elif platform_dropdown.value == "neighbor_visit":
                    task_type = "neighbor"
                    data['immediate'] = True
                    data['visit_count'] = int(count_field.value) if count_field.value.isdigit() else 10
                    data['do_like'] = True
                    data['use_ai'] = True
                else:
                    task_type = type_dropdown.value
                    
                self.scheduler.add_task(
                    platform_dropdown.value,
                    task_type,
                    start_field.value,
                    end_field.value,
                    data=data
                )
                dialog.open = False
                update_scheduler_ui()
            
            platform_dropdown = ft.Dropdown(
                label="플랫폼",
                options=[
                    ft.dropdown.Option(key="blog", text="블로그"), 
                    ft.dropdown.Option(key="band", text="밴드"), 
                    ft.dropdown.Option(key="cafe", text="카페"),
                    ft.dropdown.Option(key="blog_reply", text="블로그 댓글 답글"),
                    ft.dropdown.Option(key="band_reply", text="밴드 댓글 답글"),
                    ft.dropdown.Option(key="neighbor_visit", text="이웃방문")
                    # 대기(idle) 제거됨
                ],
                value="blog",
                on_change=on_platform_change
            )
            type_dropdown = ft.Dropdown(
                label="유형",
                options=[
                    ft.dropdown.Option(key="regular", text="일반"), 
                    ft.dropdown.Option(key="morning", text="오전형 (인사 포함)"), 
                    ft.dropdown.Option(key="closing", text="저녁형 (인사 포함)")
                ],
                value="regular"
            )
            # 🎵 플레이리스트 모드에서는 시간 필드 불필요
            start_field = ft.TextField(label="시작 시간", value="00:00", visible=False)
            end_field = ft.TextField(label="종료 시간", value="23:59", visible=False)
            
            dialog = ft.AlertDialog(
                title=ft.Text("🎵 플레이리스트에 작업 추가"),
                content=ft.Column([
                    ft.Text("등록한 순서대로 실행됩니다.", size=12, color=ft.Colors.GREY_600),
                    platform_dropdown, 
                    type_dropdown, 
                    ft.Row([count_field, reservation_field], spacing=10)  # 횟수와 예약시간 같은 줄
                ], tight=True, spacing=10),
                actions=[ft.TextButton("취소", on_click=lambda _: setattr(dialog, "open", False)),
                         ft.ElevatedButton("추가", on_click=save_new_task, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)]
            )
            page.overlay.append(dialog)
            dialog.open = True
            page.update()

        scheduler_status_bar = ft.ProgressBar(width=None, color=ft.Colors.GREEN, bgcolor=ft.Colors.GREEN_100, visible=False)
        scheduler_status_text = ft.Text("🛑 스케줄러 중지됨", color=ft.Colors.RED, size=16, weight=ft.FontWeight.BOLD)

        # 🎵 플레이리스트 컨트롤 버튼 (먼저 정의)
        btn_start = ft.ElevatedButton(
            "▶️ 시작",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=ft.Colors.GREEN_700,
            color=ft.Colors.WHITE,
            disabled=False
        )
        btn_pause = ft.ElevatedButton(
            "⏸️ 일시정지",
            icon=ft.Icons.PAUSE,
            bgcolor=ft.Colors.ORANGE_700,
            color=ft.Colors.WHITE,
            disabled=True
        )
        # 🆕 중지 버튼은 항상 활성화 (클릭 시 상태 확인)
        btn_stop = ft.ElevatedButton(
            "⏹️ 중지",
            icon=ft.Icons.STOP,
            bgcolor=ft.Colors.RED_700,
            color=ft.Colors.WHITE,
            disabled=False  # 🆕 항상 활성화
        )

        # 🎵 플레이리스트 스타일 스케줄러 버튼 함수
        def start_scheduler_click(e):
            """▶️ 플레이리스트 시작 (처음부터)"""
            self.scheduler.start()
            
            # 🔄 세션 유지 시스템도 함께 시작
            self.start_session_keep_alive()
            
            # UI 상태 업데이트
            scheduler_status_text.value = "🎵 플레이리스트 실행 중..."
            scheduler_status_text.color = ft.Colors.GREEN
            scheduler_status_bar.visible = True
            scheduler_status_bar.value = None  # 애니메이션 프로그레스 바
            
            # 버튼 상태 및 색상 업데이트
            btn_start.disabled = True
            btn_start.bgcolor = ft.Colors.GREY_400  # 비활성화 색상
            btn_pause.disabled = False
            btn_pause.bgcolor = ft.Colors.ORANGE_700  # 활성화 색상
            # btn_stop은 항상 활성화 유지
            btn_stop.bgcolor = ft.Colors.RED_700  # 활성화 색상
            
            update_scheduler_ui()
            
            page.snack_bar = ft.SnackBar(
                content=ft.Text("▶️ 플레이리스트 시작! 등록된 순서대로 작업을 실행합니다."),
                bgcolor=ft.Colors.GREEN_700
            )
            page.snack_bar.open = True
            page.update()
        
        def pause_scheduler_click(e):
            """⏸️ 일시정지 / ▶️ 재개"""
            if self.scheduler.paused:
                # 재개
                self.scheduler.resume()
                scheduler_status_text.value = "🎵 플레이리스트 실행 중..."
                scheduler_status_text.color = ft.Colors.GREEN
                btn_pause.text = "⏸️ 일시정지"
                btn_pause.bgcolor = ft.Colors.ORANGE_700
                page.snack_bar = ft.SnackBar(content=ft.Text("▶️ 플레이리스트 재개됨"))
            else:
                # 일시정지
                self.scheduler.pause()
                scheduler_status_text.value = "⏸️ 일시정지됨 (현재 작업 완료 후 대기)"
                scheduler_status_text.color = ft.Colors.ORANGE
                btn_pause.text = "▶️ 재개"
                btn_pause.bgcolor = ft.Colors.GREEN_700
                page.snack_bar = ft.SnackBar(content=ft.Text("⏸️ 일시정지됨 - 재개 버튼을 눌러 계속 진행"))
            
            page.snack_bar.open = True
            page.update()

        def stop_scheduler_click(e):
            """⏹️ 중지 (처음으로 초기화)"""
            print("🛑 중지 버튼 클릭됨!")
            
            # 스케줄러 중지 (이미 중지 상태라도 초기화)
            if self.scheduler.running:
                self.scheduler.stop()
                print("  ✅ 스케줄러 중지됨")
            else:
                # 이미 중지된 상태라도 초기화
                self.scheduler.current_index = 0
                for task in self.scheduler.tasks:
                    task.is_completed = False
                    task.last_status = None
                self.scheduler.save_tasks()
                print("  ✅ 스케줄러 상태 초기화됨")
            
            self.stop_session_keep_alive()
            
            # 🎯 UI 상태 즉시 업데이트
            scheduler_status_text.value = "⏹️ 스케줄러 중지됨 (처음으로 초기화)"
            scheduler_status_text.color = ft.Colors.RED
            scheduler_status_bar.visible = False
            scheduler_status_bar.value = 0  # 프로그레스 바 초기화
            
            # 버튼 상태 변경 - 🆕 중지 버튼은 항상 활성화 유지
            btn_start.disabled = False
            btn_start.bgcolor = ft.Colors.GREEN_700  # 시작 버튼 활성화 표시
            btn_pause.disabled = True
            btn_pause.text = "⏸️ 일시정지"
            btn_pause.bgcolor = ft.Colors.GREY_400  # 비활성화 색상
            # btn_stop은 항상 활성화 유지 (disabled 변경 안 함)
            btn_stop.bgcolor = ft.Colors.RED_700  # 활성화 색상 유지
            
            # 먼저 page.update() 호출하여 버튼 상태 반영
            page.update()
            
            # 🎯 작업 목록 UI 업데이트 (모든 작업 "대기" 상태로)
            update_scheduler_ui()
            
            # 스낵바 표시
            page.snack_bar = ft.SnackBar(
                content=ft.Text("⏹️ 스케줄러 중지됨 - 다시 시작하면 처음부터 실행됩니다."),
                bgcolor=ft.Colors.RED_700
            )
            page.snack_bar.open = True
            page.update()
            
            print("✅ 중지 UI 업데이트 완료")
        
        # 버튼에 클릭 핸들러 연결
        btn_start.on_click = start_scheduler_click
        btn_pause.on_click = pause_scheduler_click
        btn_stop.on_click = stop_scheduler_click

        # ========== 블로그 예약 프리셋 UI ==========
        blog_preset_start = ft.TextField(label="예약 시작", value="07:00", width=100)
        blog_preset_end = ft.TextField(label="예약 종료", value="23:00", width=100)
        blog_preset_interval = ft.Dropdown(
            label="간격 (고정)",
            options=[ft.dropdown.Option(str(i), f"{i}시간") for i in range(1, 13)],  # 🆕 1~12시간
            value="2",
            width=120
        )
        # 1건당 소요시간: 30초, 1분, 1분30초, 2분 (초 단위로 저장)
        blog_preset_per_post_time = ft.Dropdown(
            label="1건당 소요",
            options=[
                ft.dropdown.Option("30", "30초"),
                ft.dropdown.Option("60", "1분"),
                ft.dropdown.Option("90", "1분30초"),
                ft.dropdown.Option("120", "2분"),
            ],
            value="60",  # 기본값 1분
            width=120
        )
        
        # 스케줄러 작동 시간 설정 필드 추가
        # 현재 시간 + 5분으로 자동 설정
        from datetime import datetime, timedelta
        now = datetime.now()
        start_auto = now + timedelta(minutes=5)
        start_auto_str = start_auto.strftime("%H:%M")
        end_auto_str = (start_auto + timedelta(minutes=60)).strftime("%H:%M")  # 기본 1시간 후
        
        blog_scheduler_start = ft.TextField(label="작동 시작", value=start_auto_str, width=100, hint_text="스케줄러")
        blog_scheduler_end = ft.TextField(label="작동 종료", value=end_auto_str, width=100, hint_text="스케줄러")
        
        # 자동 계산 체크박스 (기본 체크됨)
        def on_auto_calc_change(e):
            self._blog_auto_calc_scheduler = e.control.value
            # 체크 시 즉시 시간 계산
            if e.control.value:
                calculate_blog_preset()
        
        blog_auto_calc_checkbox = ft.Checkbox(
            label="자동 계산",
            value=True,  # 기본 체크됨
            on_change=on_auto_calc_change,
            tooltip="체크 시 작동 시간을 자동으로 설정합니다"
        )
        self._blog_auto_calc_scheduler = True  # 기본 True
        
        # 수동 시간 변경 시 자동 계산 해제
        def on_manual_time_change(e):
            if blog_auto_calc_checkbox.value:
                blog_auto_calc_checkbox.value = False
                self._blog_auto_calc_scheduler = False
                page.update()
        
        blog_scheduler_start.on_change = on_manual_time_change
        blog_scheduler_end.on_change = on_manual_time_change
        
        blog_preset_result = ft.Text("📊 예상 결과를 보려면 [미리보기]를 클릭하세요", size=12, color=ft.Colors.GREY_600)
        blog_preset_times_list = ft.Text("", size=11, color=ft.Colors.BLUE_700)
        
        def calculate_blog_preset(e=None):
            """블로그 예약 프리셋 계산"""
            try:
                start_h, start_m = map(int, blog_preset_start.value.split(':'))
                end_h, end_m = map(int, blog_preset_end.value.split(':'))
                interval = int(blog_preset_interval.value) * 60  # 분으로 변환 (고정 간격)
                per_post_seconds = int(blog_preset_per_post_time.value)  # 초 단위
                per_post_minutes = per_post_seconds / 60  # 분으로 변환 (계산용)
                
                # 시간 계산
                start_minutes = start_h * 60 + start_m
                end_minutes = end_h * 60 + end_m
                if end_minutes <= start_minutes:
                    end_minutes += 24 * 60  # 다음 날
                
                # 고정 간격으로 시간 생성
                times = []
                current = start_minutes
                while current <= end_minutes:
                    h = (current // 60) % 24
                    m = current % 60
                    # 10분 단위로 맞춤
                    m = (m // 10) * 10
                    times.append(f"{h:02d}:{m:02d}")
                    current += interval
                
                # 총 소요 시간 계산 (초 → 분 변환)
                total_time_seconds = len(times) * (per_post_seconds + 180)  # 포스팅 3분(180초) + 대기 시간
                total_time_minutes = total_time_seconds // 60 + 1  # 분으로 올림
                
                # 스케줄러 작동 시간: 현재 시간 + 5분부터
                from datetime import datetime, timedelta
                now = datetime.now()
                
                # 자동 계산 체크박스가 켜져 있을 때 (수동으로 시간을 바꿨으면 덮어쓰지 않음)
                if hasattr(self, '_blog_auto_calc_scheduler') and self._blog_auto_calc_scheduler:
                    # 시작: 현재 시간 + 5분
                    auto_start = now + timedelta(minutes=5)
                    auto_start_str = auto_start.strftime("%H:%M")
                    
                    # 종료: 시작 + 총 소요 시간 + 10분 여유
                    auto_end = auto_start + timedelta(minutes=total_time_minutes + 10)
                    auto_end_str = auto_end.strftime("%H:%M")
                    
                    blog_scheduler_start.value = auto_start_str
                    blog_scheduler_end.value = auto_end_str
                    recommended_start = auto_start_str
                    recommended_end = auto_end_str
                else:
                    recommended_start = blog_scheduler_start.value
                    recommended_end = blog_scheduler_end.value
                
                # 권장 시간 표시
                recommend_text = f" | 작동: {recommended_start}~{recommended_end}" if recommended_start else ""
                per_post_display = f"{per_post_seconds}초" if per_post_seconds < 60 else f"{per_post_seconds//60}분{per_post_seconds%60}초" if per_post_seconds % 60 else f"{per_post_seconds//60}분"
                blog_preset_result.value = f"📊 총 {len(times)}건 | 간격 {per_post_display} | 소요 ~{total_time_minutes}분{recommend_text}"
                blog_preset_times_list.value = f"⏰ 예약: {', '.join(times)}"
                
                # 계산된 시간 목록 저장
                self._blog_preset_times = times
                
                page.update()
            except Exception as ex:
                blog_preset_result.value = f"❌ 계산 오류: {ex}"
                page.update()
        
        # 드롭다운 변경 시 자동 계산
        def on_preset_change(e):
            # 체크박스가 켜져있거나 끄더라도 시간 목록 갱신을 위해 계산은 하되, 시간 필드 덮어쓰기는 위 calculate 함수에서 제어됨
            calculate_blog_preset()
        
        blog_preset_interval.on_change = on_preset_change
        blog_preset_per_post_time.on_change = on_preset_change
        
        # 초기 계산 실행
        calculate_blog_preset()
        
        def register_blog_preset(e):
            """블로그 예약 프리셋 일괄 등록"""
            # 체크박스가 꺼져있으면 시간 덮어쓰지 않고 계산만 수행
            calculate_blog_preset()
            
            if not hasattr(self, '_blog_preset_times') or not self._blog_preset_times:
                page.snack_bar = ft.SnackBar(content=ft.Text("예약 시간을 계산할 수 없습니다"), bgcolor=ft.Colors.ORANGE)
                page.snack_bar.open = True
                page.update()
                return
            
            # 스케줄러에 블로그 예약 일괄 작업 추가
            times = self._blog_preset_times
            per_post_seconds = int(blog_preset_per_post_time.value)  # 초 단위
            per_post_minutes = per_post_seconds / 60  # 분으로 변환
            
            # 🎵 플레이리스트 모드: 작동 시간은 무시됨 (순서대로 실행)
            # 기본값으로 설정 (호환성 유지)
            start_time = "00:00"
            end_time = "23:59"
            
            self.scheduler.add_task(
                platform='blog',
                task_type='reservation_batch',
                start_time=start_time,
                end_time=end_time,
                data={'times': times, 'per_post_minutes': per_post_minutes}
            )
            
            update_scheduler_ui()
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"✅ 블로그 예약 {len(times)}건 등록! (플레이리스트에 추가됨)"),
                bgcolor=ft.Colors.GREEN
            )
            page.snack_bar.open = True
            page.update()
        
        blog_preset_section = ft.Container(
            content=ft.Column([
                ft.Text("📝 블로그 예약 프리셋", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("🎵 플레이리스트에 추가되면 순서대로 실행됩니다", size=11, color=ft.Colors.GREY_600),
                ft.Row([
                    ft.Text("예약 범위:", width=70),
                    blog_preset_start, blog_preset_end, blog_preset_interval, blog_preset_per_post_time
                ], spacing=10),
                # 🎵 작동 시간은 플레이리스트 모드에서 불필요하므로 숨김
                blog_preset_result,
                blog_preset_times_list,
                ft.Row([
                    ft.ElevatedButton("🎵 플레이리스트에 추가", icon=ft.Icons.PLAYLIST_ADD, bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE, on_click=register_blog_preset)
                ], spacing=10)
            ], spacing=8),
            padding=15,
            bgcolor=ft.Colors.BLUE_50,
            border_radius=10
        )
        
        # ========== 밴드 예약 프리셋 UI ==========
        # 🆕 각 시간대 활성화 체크박스
        band_preset_morning_enabled = ft.Checkbox(label="", value=True, width=30)
        band_preset_morning_time = ft.TextField(label="오전 시간", value="07:00", width=100)
        band_preset_morning_type = ft.Dropdown(
            label="유형",
            options=[
                ft.dropdown.Option("morning", "아침"),
                ft.dropdown.Option("regular", "일반"),
                ft.dropdown.Option("closing", "마감")
            ],
            value="morning",
            width=100
        )
        band_preset_afternoon_enabled = ft.Checkbox(label="", value=True, width=30)
        band_preset_afternoon_time = ft.TextField(label="오후 시간", value="14:30", width=100)
        band_preset_afternoon_type = ft.Dropdown(
            label="유형",
            options=[
                ft.dropdown.Option("morning", "아침"),
                ft.dropdown.Option("regular", "일반"),
                ft.dropdown.Option("closing", "마감")
            ],
            value="regular",
            width=100
        )
        band_preset_closing_enabled = ft.Checkbox(label="", value=True, width=30)
        band_preset_closing_time = ft.TextField(label="마감 시간", value="20:00", width=100)
        band_preset_closing_type = ft.Dropdown(
            label="유형",
            options=[
                ft.dropdown.Option("morning", "아침"),
                ft.dropdown.Option("regular", "일반"),
                ft.dropdown.Option("closing", "마감")
            ],
            value="closing",
            width=100
        )
        # 1건당 소요시간: 30초, 1분, 1분30초, 2분 (초 단위로 저장)
        band_preset_per_post = ft.Dropdown(
            label="1건당 소요",
            options=[
                ft.dropdown.Option("30", "30초"),
                ft.dropdown.Option("60", "1분"),
                ft.dropdown.Option("90", "1분30초"),
                ft.dropdown.Option("120", "2분"),
            ],
            value="60",  # 기본값 1분
            width=100
        )
        
        # 스케줄러 작동 시간 설정 필드 - 현재 시간 + 5분으로 자동 설정
        from datetime import datetime, timedelta
        now_band = datetime.now()
        band_start_auto = now_band + timedelta(minutes=5)
        band_start_auto_str = band_start_auto.strftime("%H:%M")
        band_end_auto_str = (band_start_auto + timedelta(minutes=30)).strftime("%H:%M")  # 기본 30분
        
        band_scheduler_start = ft.TextField(label="작동 시작", value=band_start_auto_str, width=100, hint_text="스케줄러")
        band_scheduler_end = ft.TextField(label="작동 종료", value=band_end_auto_str, width=100, hint_text="스케줄러")
        
        # 자동 계산 체크박스 (기본 체크됨)
        def on_band_auto_calc_change(e):
            self._band_auto_calc_scheduler = e.control.value
            if e.control.value:
                calculate_band_preset()
        
        band_auto_calc_checkbox = ft.Checkbox(
            label="자동 계산",
            value=True,
            on_change=on_band_auto_calc_change,
            tooltip="체크 시 작동 시간을 자동으로 설정합니다"
        )
        self._band_auto_calc_scheduler = True
        
        # 밴드 수동 시간 변경 시 자동 계산 해제
        def on_band_manual_time_change(e):
            if band_auto_calc_checkbox.value:
                band_auto_calc_checkbox.value = False
                self._band_auto_calc_scheduler = False
                page.update()
        
        band_scheduler_start.on_change = on_band_manual_time_change
        band_scheduler_end.on_change = on_band_manual_time_change
        
        band_preset_result = ft.Text("📊 일괄 등록하면 자동 계산됩니다", size=12, color=ft.Colors.GREY_600)
        
        def calculate_band_preset(e=None):
            """밴드 예약 프리셋 계산"""
            per_post_seconds = int(band_preset_per_post.value)  # 초 단위
            per_post_minutes = per_post_seconds / 60  # 분으로 변환
            
            # 총 소요 시간 계산 (3건 * (대기시간 + 포스팅 3분))
            total_time_seconds = 3 * (per_post_seconds + 180)  # 포스팅 3분(180초)
            total_time_minutes = total_time_seconds // 60 + 1
            
            # 자동 계산 체크 시 현재 시간 + 5분으로 설정
            if hasattr(self, '_band_auto_calc_scheduler') and self._band_auto_calc_scheduler:
                from datetime import datetime, timedelta
                now = datetime.now()
                auto_start = now + timedelta(minutes=5)
                auto_start_str = auto_start.strftime("%H:%M")
                auto_end = auto_start + timedelta(minutes=total_time_minutes + 10)
                auto_end_str = auto_end.strftime("%H:%M")
                
                band_scheduler_start.value = auto_start_str
                band_scheduler_end.value = auto_end_str
            
            # 표시 형식
            per_post_display = f"{per_post_seconds}초" if per_post_seconds < 60 else f"{per_post_seconds//60}분{per_post_seconds%60}초" if per_post_seconds % 60 else f"{per_post_seconds//60}분"
            times_list = f"{band_preset_morning_time.value}, {band_preset_afternoon_time.value}, {band_preset_closing_time.value}"
            band_preset_result.value = f"📊 총 3건 | 간격 {per_post_display} | 소요 ~{total_time_minutes}분 | 작동: {band_scheduler_start.value}~{band_scheduler_end.value}"
            page.update()
        
        def register_band_preset(e):
            """밴드 예약 프리셋 일괄 등록 (체크된 시간대만)"""
            # 먼저 계산 실행 (시간 덮어쓰기 방지는 내부에서 처리)
            calculate_band_preset()
            
            per_post_seconds = int(band_preset_per_post.value)  # 초 단위
            per_post_minutes = per_post_seconds / 60  # 분으로 변환
            
            # 🎵 플레이리스트 모드: 작동 시간은 무시됨 (순서대로 실행)
            start_time = "00:00"
            end_time = "23:59"
            
            band_url = self.settings.get('band_url', '')
            
            # 🆕 체크된 시간대만 등록
            times_data = []
            if band_preset_morning_enabled.value:
                times_data.append({'time': band_preset_morning_time.value, 'type': band_preset_morning_type.value})
            if band_preset_afternoon_enabled.value:
                times_data.append({'time': band_preset_afternoon_time.value, 'type': band_preset_afternoon_type.value})
            if band_preset_closing_enabled.value:
                times_data.append({'time': band_preset_closing_time.value, 'type': band_preset_closing_type.value})
            
            if not times_data:
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("⚠️ 최소 1개 시간대를 선택해주세요"),
                    bgcolor=ft.Colors.ORANGE
                )
                page.snack_bar.open = True
                page.update()
                return
            
            self.scheduler.add_task(
                platform='band',
                task_type='reservation_batch',
                start_time=start_time,
                end_time=end_time,
                data={
                    'times': [t['time'] for t in times_data],
                    'types': [t['type'] for t in times_data],
                    'band_url': band_url,
                    'per_post_minutes': per_post_minutes  # 분 단위로 저장
                }
            )
            
            update_scheduler_ui()
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"✅ 밴드 예약 {len(times_data)}건 등록! (플레이리스트에 추가됨)"),
                bgcolor=ft.Colors.GREEN
            )
            page.snack_bar.open = True
            page.update()
        
        # 드롭다운 변경 시 자동 계산
        def on_band_preset_change(e):
            # 체크 여부에 상관없이 리스트 갱신 호출 (시간 필드 덮어쓰기는 내부 제어)
            calculate_band_preset()
        
        band_preset_per_post.on_change = on_band_preset_change
        
        # 초기 계산 실행
        calculate_band_preset()
        
        # 🆕 체크박스 변경 시 예약 건수 재계산
        def update_band_count(e=None):
            enabled_count = sum([
                band_preset_morning_enabled.value,
                band_preset_afternoon_enabled.value,
                band_preset_closing_enabled.value
            ])
            per_post_seconds = int(band_preset_per_post.value)
            total_time_seconds = enabled_count * (per_post_seconds + 180)
            total_time_minutes = total_time_seconds // 60 + 1 if enabled_count > 0 else 0
            
            times_list = []
            if band_preset_morning_enabled.value:
                times_list.append(band_preset_morning_time.value)
            if band_preset_afternoon_enabled.value:
                times_list.append(band_preset_afternoon_time.value)
            if band_preset_closing_enabled.value:
                times_list.append(band_preset_closing_time.value)
            
            band_preset_result.value = f"📊 총 {enabled_count}건 | 소요 ~{total_time_minutes}분 | 시간: {', '.join(times_list) if times_list else '(선택 없음)'}"
            page.update()
        
        band_preset_morning_enabled.on_change = update_band_count
        band_preset_afternoon_enabled.on_change = update_band_count
        band_preset_closing_enabled.on_change = update_band_count
        
        # 초기 표시 업데이트
        update_band_count()
        
        band_preset_section = ft.Container(
            content=ft.Column([
                ft.Text("🎵 밴드 예약 프리셋", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("🎵 체크된 시간대만 플레이리스트에 추가됩니다", size=11, color=ft.Colors.GREY_600),
                ft.Row([band_preset_morning_enabled, ft.Text("오전:", width=40), band_preset_morning_time, band_preset_morning_type], spacing=5),
                ft.Row([band_preset_afternoon_enabled, ft.Text("오후:", width=40), band_preset_afternoon_time, band_preset_afternoon_type], spacing=5),
                ft.Row([band_preset_closing_enabled, ft.Text("마감:", width=40), band_preset_closing_time, band_preset_closing_type], spacing=5),
                ft.Row([ft.Text("1건당:", width=50), band_preset_per_post], spacing=10),
                # 🎵 작동 시간은 플레이리스트 모드에서 불필요하므로 숨김
                band_preset_result,
                ft.Row([
                    ft.ElevatedButton("🎵 플레이리스트에 추가", icon=ft.Icons.PLAYLIST_ADD, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, on_click=register_band_preset)
                ], spacing=10)
            ], spacing=8),
            padding=15,
            bgcolor=ft.Colors.GREEN_50,
            border_radius=10
        )

        # ========== 🆕 매일 자동 시작 설정 UI ==========
        daily_start_time = ft.TextField(label="시작 시간", value="07:00", width=100, hint_text="HH:MM")
        daily_random_range = ft.Dropdown(
            label="랜덤 범위",
            options=[
                ft.dropdown.Option("0", "정각"),
                ft.dropdown.Option("5", "±5분"),
                ft.dropdown.Option("10", "±10분"),
                ft.dropdown.Option("15", "±15분"),
                ft.dropdown.Option("30", "±30분"),
            ],
            value="15",
            width=100
        )
        daily_auto_enabled_checkbox = ft.Checkbox(label="매일 자동 시작", value=False)
        daily_status_text = ft.Text("🔴 비활성화됨", color=ft.Colors.RED, size=12)
        
        def toggle_daily_auto_start(e):
            """매일 자동 시작 활성화/비활성화"""
            enabled = daily_auto_enabled_checkbox.value
            start_time = daily_start_time.value
            random_range_val = int(daily_random_range.value)
            
            # 시간 형식 검증
            import re
            if not re.match(r"^\d{1,2}:\d{2}$", start_time):
                page.snack_bar = ft.SnackBar(content=ft.Text("시간 형식이 올바르지 않습니다 (HH:MM)"))
                page.snack_bar.open = True
                daily_auto_enabled_checkbox.value = False
                page.update()
                return
            
            # 스케줄러에 설정 적용
            self.scheduler.set_daily_auto_start(enabled, start_time, random_range_val)
            
            if enabled:
                self.scheduler.start_daily_auto_monitor()
                daily_status_text.value = f"🟢 활성화됨 (매일 {start_time} ±{random_range_val}분)"
                daily_status_text.color = ft.Colors.GREEN
                page.snack_bar = ft.SnackBar(content=ft.Text(f"✅ 매일 자동 시작 활성화: {start_time} ±{random_range_val}분"))
            else:
                self.scheduler.stop_daily_auto_monitor()
                daily_status_text.value = "🔴 비활성화됨"
                daily_status_text.color = ft.Colors.RED
                page.snack_bar = ft.SnackBar(content=ft.Text("⏹️ 매일 자동 시작 비활성화됨"))
            
            page.snack_bar.open = True
            page.update()
        
        daily_auto_enabled_checkbox.on_change = toggle_daily_auto_start
        
        daily_auto_section = ft.Container(
            content=ft.Column([
                ft.Text("🔄 매일 자동 시작", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("🎵 매일 설정된 시간에 플레이리스트를 자동으로 초기화하고 시작합니다.", size=11, color=ft.Colors.GREY_600),
                ft.Row([
                    ft.Text("시작 시간:", width=80),
                    daily_start_time,
                    daily_random_range
                ], spacing=10),
                ft.Row([
                    daily_auto_enabled_checkbox,
                    daily_status_text
                ], spacing=10),
                ft.Text("📋 동작 방식:", size=11, color=ft.Colors.BLUE, weight=ft.FontWeight.BOLD),
                ft.Text("   1. 자정(0시): 모든 작업 초기화 (완료 → 대기)", size=11, color=ft.Colors.GREY_600),
                ft.Text("   2. 설정 시간 ± 랜덤: 플레이리스트 자동 시작", size=11, color=ft.Colors.GREY_600),
                ft.Text("   3. 24시간 연속 운영 가능 (중지 없이 매일 반복)", size=11, color=ft.Colors.GREY_600),
            ], spacing=8),
            padding=15,
            bgcolor=ft.Colors.AMBER_50,
            border_radius=10
        )

        # ========== 🆕 특별 예약 (폴더 감지) 설정 UI ==========
        special_start_time = ft.TextField(label="시작 시간", value="09:00", width=100, hint_text="HH:MM")
        special_end_time = ft.TextField(label="종료 시간", value="10:00", width=100, hint_text="HH:MM")
        special_enabled_checkbox = ft.Checkbox(label="특별 예약 활성화", value=False)
        special_status_text = ft.Text("🔴 비활성화됨", color=ft.Colors.RED, size=12)
        
        def toggle_special_reservation(e):
            """특별 예약 활성화/비활성화"""
            enabled = special_enabled_checkbox.value
            start_time = special_start_time.value
            end_time = special_end_time.value
            
            # 시간 형식 검증
            import re
            if not re.match(r"^\d{1,2}:\d{2}$", start_time) or not re.match(r"^\d{1,2}:\d{2}$", end_time):
                page.snack_bar = ft.SnackBar(content=ft.Text("시간 형식이 올바르지 않습니다 (HH:MM)"))
                page.snack_bar.open = True
                special_enabled_checkbox.value = False
                page.update()
                return
            
            # 스케줄러에 설정 적용
            self.scheduler.set_special_reservation(enabled, start_time, end_time)
            
            # 콜백 함수 설정 (드라이브 폴더 감지 실행)
            if enabled:
                # drive_auto_post_system이 있을 경우에만 콜백 설정
                if self.drive_auto_post_system:
                    # 🆕 시작 콜백: 폴더 감지 시작
                    self.scheduler.on_special_reservation = lambda: self._start_drive_auto_post(page)
                    # 🆕 종료 콜백: 폴더 감지 중지
                    self.scheduler.on_special_reservation_end = lambda: self._stop_drive_auto_post(page)
                self.scheduler.start_special_reservation_monitor()
                special_status_text.value = f"🟢 활성화됨 ({start_time} ~ {end_time})"
                special_status_text.color = ft.Colors.GREEN
                page.snack_bar = ft.SnackBar(content=ft.Text(f"✅ 특별 예약 활성화: {start_time} ~ {end_time}"))
            else:
                self.scheduler.stop_special_reservation_monitor()
                special_status_text.value = "🔴 비활성화됨"
                special_status_text.color = ft.Colors.RED
                page.snack_bar = ft.SnackBar(content=ft.Text("⏹️ 특별 예약 비활성화됨"))
            
            page.snack_bar.open = True
            page.update()
        
        special_enabled_checkbox.on_change = toggle_special_reservation
        
        special_reservation_section = ft.Container(
            content=ft.Column([
                ft.Text("📂 특별 예약 (폴더 감지)", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("🎵 설정한 시간에 플레이리스트를 일시정지하고 폴더 감지 작업을 실행합니다.", size=11, color=ft.Colors.GREY_600),
                ft.Row([
                    ft.Text("예약 시간:", width=80),
                    special_start_time,
                    ft.Text("~", size=14),
                    special_end_time
                ], spacing=10),
                ft.Row([
                    special_enabled_checkbox,
                    special_status_text
                ], spacing=10),
                ft.Text("⚠️ 플레이리스트 실행 중 위 시간에 도달하면:", size=11, color=ft.Colors.ORANGE),
                ft.Text("   1. 현재 작업 완료 후 일시정지", size=11, color=ft.Colors.GREY_600),
                ft.Text("   2. 폴더 감지 작업 실행 (Google Drive 수동업로드)", size=11, color=ft.Colors.GREY_600),
                ft.Text("   3. 종료 시간 후 플레이리스트 자동 재개", size=11, color=ft.Colors.GREY_600),
            ], spacing=8),
            padding=15,
            bgcolor=ft.Colors.PURPLE_50,
            border_radius=10
        )

        scheduler_tab_content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("📅 스마트 스케줄러 설정", size=20, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("작업 추가", icon=ft.Icons.ADD, on_click=add_new_task)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(
                    content=ft.Column([
                        scheduler_status_text,
                        scheduler_status_bar
                    ]),
                    padding=10,
                    bgcolor=ft.Colors.GREY_50,
                    border_radius=8
                ),
                ft.Divider(),
                # 🆕 예약 프리셋 섹션 추가
                ft.ExpansionTile(
                    title=ft.Text("📝 블로그 예약 프리셋 (클릭하여 펼치기)", size=14, weight=ft.FontWeight.BOLD),
                    controls=[blog_preset_section],
                    initially_expanded=False
                ),
                ft.ExpansionTile(
                    title=ft.Text("🎵 밴드 예약 프리셋 (클릭하여 펼치기)", size=14, weight=ft.FontWeight.BOLD),
                    controls=[band_preset_section],
                    initially_expanded=False
                ),
                # 🆕 매일 자동 시작 설정
                ft.ExpansionTile(
                    title=ft.Text("🔄 매일 자동 시작 (클릭하여 펼치기)", size=14, weight=ft.FontWeight.BOLD),
                    controls=[daily_auto_section],
                    initially_expanded=False
                ),
                # 🆕 특별 예약 (폴더 감지) 설정
                ft.ExpansionTile(
                    title=ft.Text("📂 특별 예약 - 폴더 감지 (클릭하여 펼치기)", size=14, weight=ft.FontWeight.BOLD),
                    controls=[special_reservation_section],
                    initially_expanded=False
                ),
                ft.Divider(),
                self.scheduler_task_list,
                # 🎵 플레이리스트 컨트롤
                ft.Row([
                    btn_start,
                    btn_pause,
                    btn_stop
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)
            ], scroll=ft.ScrollMode.AUTO),
            padding=20,
            expand=True
        )

        # 밴드 포스팅 탭 구성
        def on_band_url_change(e):
            # URL 변경 시 설정에 저장
            self.settings['band_url'] = band_url_input.value
            self.save_settings()
            print(f"✅ 밴드 URL 저장됨: {band_url_input.value}")
        
        band_url_input = ft.TextField(
            label="밴드 URL", 
            value=self.settings.get('band_url', 'https://www.band.us/band/6194797/post'), 
            expand=True,
            on_blur=on_band_url_change  # 포커스 벗어날 때 저장
        )
        band_title_input = ft.TextField(label="제목 (옵션)", expand=True)
        band_content_input = ft.TextField(label="내용", multiline=True, min_lines=10, expand=True)
        band_single_reserve_time = ft.TextField(label="예약 시간 (선택, HH:MM)", hint_text="예: 14:30 (비워두면 즉시 발행)", expand=True)
        
        # 🟢 시간대 선택 드롭다운 추가
        band_time_type_dropdown = ft.Dropdown(
            label="시간대 유형",
            hint_text="AI 글 생성 시 적용",
            options=[
                ft.dropdown.Option("morning", "☀️ 아침형"),
                ft.dropdown.Option("regular", "🌤️ 오후형"),
                ft.dropdown.Option("closing", "🌙 저녁형"),
            ],
            value="regular",  # 기본값: 오후형
            width=180
        )
        
        def on_band_image_change(e):
            self.settings['band_auto_image'] = band_image_checkbox.value
            self.save_settings()
            
        band_image_checkbox = ft.Checkbox(
            label="이미지 자동 포함", 
            value=self.settings.get('band_auto_image', self.settings.get('auto_image', True)),
            on_change=on_band_image_change
        )
        
        def post_to_band_click(e):
            if not band_url_input.value or not band_content_input.value:
                page.snack_bar = ft.SnackBar(content=ft.Text("밴드 URL과 내용을 입력해주세요."))
                page.snack_bar.open = True
                page.update()
                return
            
            # 이미지 준비 (자동 이미지 설정 시)
            images = []
            if band_image_checkbox.value:
                images = self.get_images_to_upload(platform='band')
                if images:
                    print(f"📸 밴드 업로드용 이미지 {len(images)}개 확보")
            
            # 독립된 밴드 자동화 모듈 호출
            start_time = time.time()
            band_auto = NaverBandAutomation(self.get_or_create_driver())
            
            # 예약 시간 확인 (수동 설정된 값)
            reservation_time = None
            if band_single_reserve_time.value:
                # 간단 검증
                import re
                if re.match(r"^\d{1,2}:\d{2}$", band_single_reserve_time.value.strip()):
                     reservation_time = band_single_reserve_time.value.strip()
                     print(f"🕒 수동 포스팅 예약 설정: {reservation_time}")
                else:
                    page.snack_bar = ft.SnackBar(content=ft.Text("예약 시간 형식이 올바르지 않습니다 (HH:MM)"), bgcolor=ft.Colors.RED)
                    page.snack_bar.open = True
                    page.update()
                    return
            
            success = band_auto.post_to_band(
                band_url_input.value, 
                band_content_input.value, 
                image_paths=images,
                reservation_time=reservation_time
            )
            
            duration = time.time() - start_time
            self.add_model_usage_log(
                topic=band_title_input.value or band_content_input.value[:30],
                model="-",  # 수동 포스팅은 모델 정보 없음
                status="업로드 성공" if success else "실패",
                reason=f"네이버 밴드{' (예약)' if reservation_time else ''}",
                target="밴드 업로드",
                duration_sec=duration
            )

            if success:
                msg = f"✅ 밴드에 성공적으로 {'예약' if reservation_time else '게시'}되었습니다!"
                page.snack_bar = ft.SnackBar(content=ft.Text(msg), bgcolor=ft.Colors.GREEN)
            else:
                page.snack_bar = ft.SnackBar(content=ft.Text("❌ 밴드 게시 실패. 로그를 확인하세요."), bgcolor=ft.Colors.RED)
            page.snack_bar.open = True
            page.update()

        def generate_band_content_click(e):
            selected_topic = self.select_sequential_topic('band')
            if not selected_topic:
                page.snack_bar = ft.SnackBar(content=ft.Text("대기 중인 주제가 없습니다. [사용자 설정]에서 [밴드 주제 목록]을 입력해 주세요."))
                page.snack_bar.open = True
                page.update()
                return
            
            # 🟢 선택된 시간대 유형 가져오기
            selected_time_type = band_time_type_dropdown.value or 'regular'
            time_type_labels = {'morning': '아침형', 'regular': '오후형', 'closing': '저녁형'}
            
            # 진행 표시 시작
            page.snack_bar = ft.SnackBar(content=ft.Text(f"🤖 [{time_type_labels.get(selected_time_type, '오후형')}] '{selected_topic}' 주제로 밴드 글을 생성 중..."), duration=3000)
            page.snack_bar.open = True
            page.update()
            
            try:
                start_time = time.time()
                # 🟢 선택된 시간대 유형을 AI에 전달
                result = self.gpt_handler.generate_platform_content(selected_topic, platform='band', task_type=selected_time_type)
                band_title_input.value = result.get('title', '')
                band_content_input.value = result.get('content', '')
                
                duration = time.time() - start_time
                self.add_model_usage_log(
                    topic=selected_topic,
                    model=result.get('model', 'gpt-4o-mini'),
                    status="성공",
                    target=f"밴드({time_type_labels.get(selected_time_type, '오후형')})",
                    duration_sec=duration
                )
                
                page.snack_bar = ft.SnackBar(content=ft.Text(f"✅ 밴드 내용 생성 완료! ({time_type_labels.get(selected_time_type, '오후형')})"), bgcolor=ft.Colors.GREEN)
                page.snack_bar.open = True
                page.update()
            except Exception as ge:
                print(f"❌ 밴드 내용 생성 중 오류: {ge}")
                self.add_model_usage_log(topic=selected_topic, model="-", status="실패", reason=str(ge), target="밴드")
                page.snack_bar = ft.SnackBar(content=ft.Text(f"❌ 생성 실패: {str(ge)}"), bgcolor=ft.Colors.RED)
                page.snack_bar.open = True
                page.update()

        def auto_post_band_click(e):
            try:
                generate_band_content_click(None)
                if not band_content_input.value: 
                    return
                post_to_band_click(None)
            except Exception as ae:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"❌ 밴드 자동 포스팅 실패: {str(ae)}"), bgcolor=ft.Colors.RED)
                page.snack_bar.open = True
                page.update()

        # 밴드 댓글 자동 답글
        self.band_comment_reply_instance = None  # 중지를 위한 인스턴스 저장
        
        # 게시글 수 입력 필드
        band_reply_limit_input = ft.TextField(
            label="최근 게시글 수",
            value="5",
            hint_text="답글 달 게시글 수",
            width=120,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        def band_comment_reply_click(e):
            band_url = band_url_input.value
            if not band_url:
                page.snack_bar = ft.SnackBar(content=ft.Text("밴드 URL을 입력해주세요."))
                page.snack_bar.open = True
                page.update()
                return
            
            # 게시글 수 가져오기
            try:
                reply_limit = int(band_reply_limit_input.value) if band_reply_limit_input.value else 5
                reply_limit = max(1, min(reply_limit, 50))  # 1~50 사이로 제한
            except:
                reply_limit = 5
            
            page.snack_bar = ft.SnackBar(content=ft.Text(f"🚀 밴드 댓글 자동 답글 시작 (최근 {reply_limit}개 게시글)..."), duration=3000)
            page.snack_bar.open = True
            page.update()
            
            def run_band_reply():
                # 🔒 락 획득 (다른 작업이 끝날 때까지 대기)
                if self.is_browser_busy:
                    print("⏳ 다른 작업이 진행 중입니다. 완료까지 대기...")
                    page.snack_bar = ft.SnackBar(content=ft.Text("⏳ 다른 작업 완료 대기 중..."), bgcolor=ft.Colors.ORANGE)
                    page.snack_bar.open = True
                    try:
                        page.update()
                    except:
                        pass
                
                self.browser_lock.acquire()
                self.is_browser_busy = True
                self.update_activity_time()
                print("🔓 [밴드 답글] 락 획득 완료")
                
                try:
                    self.band_comment_reply_instance = NaverBandCommentReply(
                        driver=self.get_or_create_driver(),
                        gpt_handler=self.gpt_handler,
                        base_dir=self.base_dir
                    )
                    success = self.band_comment_reply_instance.process_band_comments(
                        band_url=band_url,
                        use_ai=True,
                        limit=reply_limit  # 사용자 입력 값 사용
                    )
                    if success:
                        page.snack_bar = ft.SnackBar(content=ft.Text("✅ 밴드 댓글 답글 완료!"), bgcolor=ft.Colors.GREEN)
                    else:
                        page.snack_bar = ft.SnackBar(content=ft.Text("⚠️ 밴드 댓글 답글 중 일부 오류 발생"), bgcolor=ft.Colors.ORANGE)
                    page.snack_bar.open = True
                    page.update()
                except Exception as ex:
                    print(f"❌ 밴드 댓글 답글 오류: {ex}")
                    page.snack_bar = ft.SnackBar(content=ft.Text(f"❌ 오류: {str(ex)[:50]}"), bgcolor=ft.Colors.RED)
                    page.snack_bar.open = True
                    page.update()
                finally:
                    # 🔧 확실한 상태 정리 + 락 해제
                    self.band_comment_reply_instance = None
                    self.is_browser_busy = False
                    self.browser_lock.release()
                    self.update_activity_time()
                    print("🔒 [밴드 답글] 락 해제 완료")
                    try:
                        page.update()
                    except:
                        pass
            
            import threading
            threading.Thread(target=run_band_reply, daemon=True).start()

        def band_comment_reply_stop_click(e):
            if self.band_comment_reply_instance:
                self.band_comment_reply_instance.stop()
                page.snack_bar = ft.SnackBar(content=ft.Text("🛑 밴드 댓글 답글 중지 요청됨"), bgcolor=ft.Colors.ORANGE)
                page.snack_bar.open = True
                page.update()
            else:
                page.snack_bar = ft.SnackBar(content=ft.Text("ℹ️ 실행 중인 작업이 없습니다."))
                page.snack_bar.open = True
                page.update()

        # --- 밴드 예약 발행 기능 시작 ---
        # 수동 포스팅에서도 참조할 수 있도록 상위 스코프/self로 변경
        self.band_reserve_time = ft.TextField(label="예약 시간 (HH:MM)", hint_text="예: 14:30", width=150)
        # ListView 대신 Column 사용 (렌더링 안정성)
        band_reserve_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10, expand=True)
        
        def update_reserve_list_ui():
            print(f"DEBUG: 예약 목록 업데이트 시작 (현재 {len(self.band_reservation_queue)}개)")
            band_reserve_list.controls.clear()
            for i, task in enumerate(self.band_reservation_queue):
                delete_btn = ft.IconButton(
                    icon=ft.Icons.DELETE, 
                    icon_color=ft.Colors.RED,
                    on_click=lambda e, idx=i: remove_reserve_task(idx)
                )
                
                band_reserve_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"⏰ {task['time']}", weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                            ft.Text(f"| {task['title'][:10]}...", size=12, color=ft.Colors.GREY_700),
                            delete_btn
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        bgcolor=ft.Colors.GREY_100,
                        padding=5,
                        border_radius=5
                    )
                )
            
            try:
                band_reserve_list.update()
                # 컨테이너가 속한 부모나 페이지 업데이트가 필요할 수 있음
                # page.update() 
            except Exception as uc_e:
                print(f"UI Update Error: {uc_e}")

        def remove_reserve_task(index):
            if 0 <= index < len(self.band_reservation_queue):
                removed = self.band_reservation_queue.pop(index)
                print(f"🗑️ 예약 작업 삭제: {removed['time']}")
                update_reserve_list_ui()

        def add_reserve_task_click(e):
            print("▶️ 작업 추가 버튼 클릭됨")
            time_str = self.band_reserve_time.value
            print(f"DEBUG: 입력된 시간: {time_str}")
            if not time_str:
                page.snack_bar = ft.SnackBar(content=ft.Text("예약 시간을 입력해주세요."), bgcolor=ft.Colors.ORANGE)
                page.snack_bar.open = True
                page.update()
                return
            
            # 시간 형식 검증 (간단히)
            import re
            if not re.match(r"^\d{1,2}:\d{2}$", time_str):
                page.snack_bar = ft.SnackBar(content=ft.Text("올바른 시간 형식(HH:MM)을 입력해주세요. 예: 14:30"), bgcolor=ft.Colors.RED)
                page.snack_bar.open = True
                page.update()
                return

            # 현재 입력된 내용 가져오기
            content = band_content_input.value
            title = band_title_input.value
            print(f"DEBUG: 내용 존재 여부: {bool(content)}, 제목: {title[:20] if title else '없음'}...")
            
            if not content:
                page.snack_bar = ft.SnackBar(content=ft.Text("⚠️ 예약할 내용을 입력하거나 [내용 생성] 버튼을 먼저 눌러주세요."), bgcolor=ft.Colors.ORANGE)
                page.snack_bar.open = True
                page.update()
                print("DEBUG: 내용이 비어있어 작업 추가 중단")
                return
                
            # 이미지 경로 확보
            images = []
            if band_image_checkbox.value:
                pass 
            
            task = {
                "time": time_str,
                "content": content,
                "title": title or "제목 없음", # UI 표시용
                "images": [] # 실행 시점에 채움
            }
            
            self.band_reservation_queue.append(task)
            print(f"DEBUG: 예약 큐에 추가됨. 현재 큐 크기: {len(self.band_reservation_queue)}")
            
            # 시간을 기준으로 정렬
            self.band_reservation_queue.sort(key=lambda x: x['time'])
            
            # UI 업데이트
            update_reserve_list_ui()
            
            page.snack_bar = ft.SnackBar(content=ft.Text(f"✅ 예약 대기열에 추가됨: {time_str}"), bgcolor=ft.Colors.GREEN)
            page.snack_bar.open = True
            page.update()

        def add_batch_to_scheduler_click(e):
            print("▶️ 스케줄러 등록 버튼 클릭됨")
            if not self.band_reservation_queue:
                page.snack_bar = ft.SnackBar(content=ft.Text("대기 중인 예약 작업이 없습니다."))
                page.snack_bar.open = True
                page.update()
                print("⚠️ 대기열 비어있음")
                return

            # 시간만 추출해서 데이터로 저장
            reservation_times = [task['time'] for task in self.band_reservation_queue]
            print(f"📋 등록할 시간 목록: {reservation_times}")
            
            # 시작 시간 입력 다이얼로그
            start_time_field = ft.TextField(label="작업 시작 시간 (HH:MM)", value="08:00")
            
            def confirm_add_scheduler(e):
                print("▶️ 등록 확인 버튼 클릭됨")
                try:
                    start_str = start_time_field.value
                    # 간단 검증
                    import re
                    if not re.match(r"^\d{1,2}:\d{2}$", start_str):
                        page.snack_bar = ft.SnackBar(content=ft.Text("올바른 시작 시간을 입력해주세요 (HH:MM)"))
                        page.snack_bar.open = True
                        page.update()
                        return
                        
                    print(f"🚀 스케줄러 등록 시도: 시작 {start_str}, 시간 {reservation_times}")
                    
                    # 스케줄러에 작업 등록
                    self.scheduler.add_task(
                        platform='band',
                        task_type='reservation_batch',
                        start_time=start_str,
                        end_time=start_str, 
                        data={
                            'times': reservation_times,
                            'band_url': band_url_input.value
                        }
                    )
                    
                    print("✅ 스케줄러 등록 메서드 호출 완료")
                    
                    dialog.open = False
                    page.snack_bar = ft.SnackBar(content=ft.Text(f"✅ 스케줄러에 예약 작업 {len(reservation_times)}건 등록 완료!"), bgcolor=ft.Colors.GREEN)
                    page.snack_bar.open = True
                    
                    # 큐 비우기
                    self.band_reservation_queue.clear()
                    update_reserve_list_ui()
                    
                    # 스케줄러 상태 갱신
                    self.update_scheduler_status(page)
                    
                    page.update()
                    print("✅ UI 업데이트 완료")

                except Exception as ex:
                    print(f"❌ 스케줄러 등록 중 오류 발생: {ex}")
                    import traceback
                    traceback.print_exc()
                    page.snack_bar = ft.SnackBar(content=ft.Text(f"등록 실패: {ex}"), bgcolor=ft.Colors.RED)
                    page.snack_bar.open = True
                    page.update()

            dialog = ft.AlertDialog(
                title=ft.Text("스케줄러에 일괄 예약 작업 등록"),
                content=ft.Column([
                    ft.Text("지정된 시간에 봇이 깨어나서 예약된 글들을 자동으로 작성합니다."),
                    start_time_field,
                    ft.Text(f"등록될 예약 시간: {', '.join(reservation_times)}", size=12, color=ft.Colors.GREY)
                ], tight=True),
                actions=[
                    ft.TextButton("취소", on_click=lambda _: setattr(dialog, "open", False)),
                    ft.ElevatedButton("등록", on_click=confirm_add_scheduler)
                ]
            )
            page.overlay.append(dialog)
            dialog.open = True
            page.update()
            print("✅ 다이얼로그 표시됨")
        # --- 밴드 예약 발행 기능 끝 ---

        # ========== 밴드 수동 주제 포스팅 섹션 ==========
        # 카테고리 기본값 (사용자 커스텀 가능)
        default_band_categories = [
            "아침형", "오후형", "마무리", "오전반", 
            "1시부", "2시부", "3시부", "4시부", "5시부", 
            "6시부", "7시부", "8시부", "9시부", "10시부", 
            "선수부", "시범부", "특별반", "체험학습"
        ]
        
        # 🟢 Google Drive 폴더에서 카테고리 자동 로드 시도
        drive_folder_path = self.settings.get('drive_folder_path', '')
        if drive_folder_path and os.path.exists(drive_folder_path):
            try:
                import unicodedata
                exclude_folders = {'백업사진', '실패사진', 'Backup', 'Error', '.DS_Store', '@eaDir'}
                drive_categories = []
                for item in sorted(os.listdir(drive_folder_path)):
                    item_path = os.path.join(drive_folder_path, item)
                    if os.path.isdir(item_path) and not item.startswith('.'):
                        item_norm = unicodedata.normalize('NFC', item)
                        if item_norm not in exclude_folders:
                            drive_categories.append(item_norm)
                if drive_categories:
                    default_band_categories = drive_categories
                    print(f"📂 Google Drive 폴더에서 카테고리 {len(drive_categories)}개 로드됨")
            except Exception as e:
                print(f"⚠️ Drive 폴더 스캔 실패: {e}")
        
        # 저장된 카테고리 로드 (없으면 Drive 폴더 또는 기본값 사용)
        saved_categories = self.settings.get('band_categories', default_band_categories)
        
        # 카테고리 드롭다운
        band_category_dropdown = ft.Dropdown(
            label="카테고리 선택",
            options=[ft.dropdown.Option(cat) for cat in saved_categories],
            value=saved_categories[0] if saved_categories else "",
            width=200
        )
        
        # 카테고리 편집 버튼
        def edit_categories_click(e):
            categories_text = ft.TextField(
                label="카테고리 목록 (한 줄에 하나씩)",
                value="\n".join(saved_categories),
                multiline=True,
                min_lines=10,
                max_lines=15,
                expand=True
            )
            
            def save_categories(e):
                new_cats = [c.strip() for c in categories_text.value.split("\n") if c.strip()]
                self.settings['band_categories'] = new_cats
                self.save_settings()
                
                # 드롭다운 업데이트
                band_category_dropdown.options = [ft.dropdown.Option(cat) for cat in new_cats]
                if new_cats:
                    band_category_dropdown.value = new_cats[0]
                
                cat_dialog.open = False
                page.snack_bar = ft.SnackBar(content=ft.Text(f"✅ 카테고리 {len(new_cats)}개 저장됨"))
                page.snack_bar.open = True
                page.update()
            
            cat_dialog = ft.AlertDialog(
                title=ft.Text("카테고리 편집"),
                content=ft.Container(content=categories_text, width=400, height=300),
                actions=[
                    ft.TextButton("취소", on_click=lambda _: setattr(cat_dialog, "open", False)),
                    ft.ElevatedButton("저장", on_click=save_categories)
                ]
            )
            page.overlay.append(cat_dialog)
            cat_dialog.open = True
            page.update()
        
        # 수동 주제 입력 필드
        band_manual_topic_input = ft.TextField(
            label="수동 주제 입력",
            hint_text="예: 한국체대 라이온짐 3시부 수련\n수련내용: 성장 스트레칭, 스텝 박스...",
            multiline=True,
            min_lines=3,
            max_lines=6,
            expand=True
        )
        
        # ===== 수동 주제 포스팅 전용 폴더 시스템 =====
        # 수동 업로드 전용 폴더 (자동 감지 폴더와 완전 분리)
        def get_manual_upload_folder():
            """수동 업로드 전용 폴더 경로 반환"""
            # 기본값: 앱 폴더 내 '수동업로드'
            default_path = os.path.join(self.base_dir, '수동업로드')
            folder_path = self.settings.get('manual_upload_folder', default_path)
            
            # 폴더 자동 생성
            if not os.path.exists(folder_path):
                os.makedirs(folder_path, exist_ok=True)
                print(f"📁 수동 업로드 폴더 생성: {folder_path}")
            
            return folder_path
        
        def get_manual_backup_folder():
            """수동 포스팅 백업 폴더 경로 반환"""
            base_folder = get_manual_upload_folder()
            backup_folder = os.path.join(os.path.dirname(base_folder), '수동업로드_백업')
            os.makedirs(backup_folder, exist_ok=True)
            return backup_folder
        
        def get_manual_fail_folder():
            """수동 포스팅 실패 폴더 경로 반환"""
            base_folder = get_manual_upload_folder()
            fail_folder = os.path.join(os.path.dirname(base_folder), '수동업로드_실패')
            os.makedirs(fail_folder, exist_ok=True)
            return fail_folder
        
        def move_images_to_folder(image_paths, target_folder):
            """이미지들을 대상 폴더로 이동"""
            import shutil
            moved_count = 0
            for img_path in image_paths:
                if os.path.exists(img_path):
                    try:
                        filename = os.path.basename(img_path)
                        target_path = os.path.join(target_folder, filename)
                        # 중복 파일명 처리
                        if os.path.exists(target_path):
                            name, ext = os.path.splitext(filename)
                            target_path = os.path.join(target_folder, f"{name}_{int(time.time())}{ext}")
                        shutil.move(img_path, target_path)
                        moved_count += 1
                    except Exception as e:
                        print(f"⚠️ 이미지 이동 실패: {img_path} -> {e}")
            return moved_count
        
        def count_images_in_folder(folder_path):
            """폴더 내 이미지/영상 수 계산"""
            valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov", ".avi"}
            count = 0
            if os.path.exists(folder_path):
                for f in os.listdir(folder_path):
                    if os.path.splitext(f)[1].lower() in valid_exts:
                        count += 1
            return count
        
        # 수동 업로드 폴더 경로 표시 필드 (읽기 전용)
        manual_upload_folder_display = ft.TextField(
            label="📁 수동 업로드 폴더",
            value=get_manual_upload_folder(),
            expand=True,
            read_only=True,
            bgcolor=ft.Colors.GREY_100
        )
        
        # 폴더 내 이미지 수 표시
        manual_image_count_text = ft.Text(
            f"📷 대기 중: {count_images_in_folder(get_manual_upload_folder())}개", 
            size=14, 
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.ORANGE_700
        )
        
        def refresh_manual_folder_display():
            """수동 업로드 폴더 정보 새로고침"""
            folder_path = get_manual_upload_folder()
            manual_upload_folder_display.value = folder_path
            count = count_images_in_folder(folder_path)
            manual_image_count_text.value = f"📷 대기 중: {count}개"
            manual_image_count_text.color = ft.Colors.GREEN_700 if count > 0 else ft.Colors.GREY_500
            page.update()
        
        def open_manual_upload_folder(e):
            """수동 업로드 폴더를 Finder에서 열기"""
            folder_path = get_manual_upload_folder()
            import subprocess
            try:
                subprocess.run(['open', folder_path])  # macOS
            except:
                try:
                    subprocess.run(['explorer', folder_path])  # Windows
                except:
                    page.snack_bar = ft.SnackBar(content=ft.Text(f"폴더 경로: {folder_path}"))
                    page.snack_bar.open = True
                    page.update()
        
        def refresh_manual_image_count(e):
            """이미지 수 새로고침"""
            refresh_manual_folder_display()
            page.snack_bar = ft.SnackBar(content=ft.Text("🔄 이미지 수 새로고침 완료"))
            page.snack_bar.open = True
            page.update()
        
        def change_manual_upload_folder(e):
            """수동 업로드 폴더 경로 변경"""
            folder_input = ft.TextField(
                label="수동 업로드 폴더 경로",
                value=get_manual_upload_folder(),
                hint_text="사진을 수동으로 업로드할 폴더",
                expand=True
            )
            
            def save_folder_path(e):
                new_path = folder_input.value.strip()
                if new_path:
                    os.makedirs(new_path, exist_ok=True)
                    self.settings['manual_upload_folder'] = new_path
                    self.save_settings()
                    refresh_manual_folder_display()
                    
                folder_dialog.open = False
                page.snack_bar = ft.SnackBar(content=ft.Text(f"✅ 폴더 설정됨: {new_path}"), bgcolor=ft.Colors.GREEN)
                page.snack_bar.open = True
                page.update()
            
            folder_dialog = ft.AlertDialog(
                title=ft.Text("📁 수동 업로드 폴더 설정"),
                content=ft.Column([
                    ft.Text("수동 주제 포스팅에 사용할 이미지 폴더를 설정합니다.", size=12, color=ft.Colors.GREY_700),
                    folder_input,
                    ft.Text("💡 이 폴더에 사진을 넣고 '수동 주제로 포스팅' 버튼을 누르세요.", size=11, color=ft.Colors.GREY_600),
                ], spacing=10, tight=True),
                actions=[
                    ft.TextButton("취소", on_click=lambda _: setattr(folder_dialog, "open", False)),
                    ft.ElevatedButton("저장", on_click=save_folder_path)
                ]
            )
            page.overlay.append(folder_dialog)
            folder_dialog.open = True
            page.update()
        
        # 수동 주제 포스팅 버튼 클릭
        def band_manual_post_click(e):
            category = band_category_dropdown.value or ""
            topic = band_manual_topic_input.value or ""
            
            if not topic:
                page.snack_bar = ft.SnackBar(content=ft.Text("❌ 주제를 입력해주세요."), bgcolor=ft.Colors.RED)
                page.snack_bar.open = True
                page.update()
                return
            
            # 수동 업로드 폴더 경로 가져오기
            folder_path = get_manual_upload_folder()
            
            page.snack_bar = ft.SnackBar(content=ft.Text(f"🚀 밴드 수동 주제 포스팅 시작: [{category}] {topic[:30]}..."))
            page.snack_bar.open = True
            page.update()
            
            def run_manual_post():
                try:
                    driver = self.get_or_create_driver()
                    band_url = self.settings.get('band_url', '')
                    
                    if not band_url:
                        print("❌ 밴드 URL이 설정되지 않았습니다.")
                        return
                    
                    # 이미지 수집 (수동 업로드 폴더에서)
                    image_paths = []
                    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
                    video_exts = {".mp4", ".mov", ".avi", ".mkv"}
                    
                    if folder_path and os.path.exists(folder_path):
                        for f in sorted(os.listdir(folder_path)):
                            ext = os.path.splitext(f)[1].lower()
                            if ext in valid_exts or ext in video_exts:
                                image_paths.append(os.path.join(folder_path, f))
                        print(f"🖼️ 수동 업로드 폴더에서 이미지/영상 {len(image_paths)}개 발견")
                    
                    if not image_paths:
                        print(f"⚠️ 수동 업로드 폴더에 이미지가 없습니다.")
                        if page:
                            page.snack_bar = ft.SnackBar(
                                content=ft.Text(f"⚠️ 수동 업로드 폴더에 이미지가 없습니다. 사진을 먼저 추가해주세요."), 
                                bgcolor=ft.Colors.ORANGE
                            )
                            page.snack_bar.open = True
                            page.update()
                        return
                    
                    # AI로 내용 생성
                    full_topic = f"[{category}] {topic}" if category else topic
                    print(f"📝 AI로 포스팅 내용 생성 중: {full_topic}")
                    
                    # 🟢 수동주제포스팅 전용 지침 사용 (사용자 입력 주제 기반)
                    result = self.gpt_handler.generate_platform_content(
                        full_topic,
                        platform='manual_topic',  # 수동 주제 전용 플랫폼 사용
                        task_type='regular'
                    )
                    
                    if not result or not result.get('content'):
                        print("❌ 내용 생성 실패")
                        # 실패 시 이미지 이동
                        fail_folder = get_manual_fail_folder()
                        moved = move_images_to_folder(image_paths, fail_folder)
                        print(f"📦 실패 폴더로 이미지 {moved}개 이동")
                        return
                    
                    content = result.get('content', '')
                    
                    # 밴드에 포스팅
                    from naver_band_auto import NaverBandAutomation
                    band_auto = NaverBandAutomation(driver)
                    success = band_auto.post_to_band(
                        band_url=band_url,
                        content=content,
                        image_paths=image_paths if image_paths else None
                    )
                    
                    if success:
                        print("✅ 밴드 수동 주제 포스팅 완료!")
                        # 성공 시 백업 폴더로 이미지 이동
                        backup_folder = get_manual_backup_folder()
                        moved = move_images_to_folder(image_paths, backup_folder)
                        print(f"📦 백업 폴더로 이미지 {moved}개 이동")
                        
                        if page:
                            page.snack_bar = ft.SnackBar(
                                content=ft.Text(f"✅ 밴드 포스팅 완료! (이미지 {moved}개 백업됨)"), 
                                bgcolor=ft.Colors.GREEN
                            )
                            page.snack_bar.open = True
                            # 이미지 수 업데이트
                            refresh_manual_folder_display()
                            page.update()
                    else:
                        print("❌ 밴드 포스팅 실패")
                        # 실패 시 실패 폴더로 이미지 이동
                        fail_folder = get_manual_fail_folder()
                        moved = move_images_to_folder(image_paths, fail_folder)
                        print(f"📦 실패 폴더로 이미지 {moved}개 이동")
                        
                        if page:
                            page.snack_bar = ft.SnackBar(
                                content=ft.Text(f"❌ 포스팅 실패 (이미지 {moved}개 실패 폴더로 이동)"), 
                                bgcolor=ft.Colors.RED
                            )
                            page.snack_bar.open = True
                            refresh_manual_folder_display()
                            page.update()
                        
                except Exception as ex:
                    print(f"❌ 수동 포스팅 오류: {ex}")
                    import traceback
                    traceback.print_exc()
                    
                    # 예외 발생 시에도 실패 폴더로 이동 시도
                    if image_paths:
                        fail_folder = get_manual_fail_folder()
                        move_images_to_folder(image_paths, fail_folder)
            
            import threading
            threading.Thread(target=run_manual_post, daemon=True).start()
        
        band_settings_tab = ft.Container(
            content=ft.Column([
                ft.Text("💚 네이버 밴드 포스팅", size=20, weight=ft.FontWeight.BOLD),
                band_url_input,
                band_title_input,
                band_content_input,
                ft.Row([
                    band_time_type_dropdown,  # 🟢 시간대 선택 드롭다운
                    band_single_reserve_time,
                ], spacing=10),
                band_image_checkbox,
                ft.Row([
                    ft.ElevatedButton("내용 생성", icon=ft.Icons.AUTO_AWESOME, on_click=generate_band_content_click),
                    ft.ElevatedButton("수동 포스팅", icon=ft.Icons.UPLOAD, on_click=post_to_band_click, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
                    ft.ElevatedButton("AI 자동 포스팅", icon=ft.Icons.BOLT, on_click=auto_post_band_click, bgcolor=ft.Colors.AMBER_700, color=ft.Colors.WHITE),
                ], spacing=10, wrap=True),
                
                ft.Divider(height=20),
                
                # ========== 수동 주제 포스팅 섹션 ==========
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.EDIT_NOTE, color=ft.Colors.ORANGE_700),
                            ft.Text("📝 수동 주제 포스팅", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_700),
                            manual_image_count_text,  # 대기 중인 이미지 수
                        ]),
                        ft.Text("수동 업로드 폴더에 사진 추가 → 카테고리/주제 입력 → AI가 내용 생성 후 포스팅", size=12, color=ft.Colors.GREY_700),
                        
                        # 수동 업로드 폴더 표시
                        ft.Row([
                            manual_upload_folder_display,
                        ]),
                        
                        # 폴더 관리 버튼들
                        ft.Row([
                            ft.ElevatedButton(
                                "📂 폴더 열기", 
                                icon=ft.Icons.FOLDER_OPEN, 
                                on_click=open_manual_upload_folder,
                                tooltip="수동 업로드 폴더를 Finder에서 열기 (여기에 사진 추가)"
                            ),
                            ft.ElevatedButton(
                                "🔄 새로고침", 
                                icon=ft.Icons.REFRESH, 
                                on_click=refresh_manual_image_count,
                                tooltip="이미지 수 새로고침"
                            ),
                            ft.ElevatedButton(
                                "⚙️ 폴더 변경", 
                                icon=ft.Icons.SETTINGS, 
                                on_click=change_manual_upload_folder,
                                tooltip="수동 업로드 폴더 경로 변경"
                            ),
                        ], spacing=10, wrap=True),
                        
                        ft.Divider(height=10),
                        
                        # 카테고리 선택 (선택사항)
                        ft.Row([
                            band_category_dropdown,
                            ft.IconButton(ft.Icons.EDIT, tooltip="카테고리 편집", on_click=edit_categories_click),
                            ft.Text("(선택사항)", size=11, color=ft.Colors.GREY_500),
                        ]),
                        
                        # 주제 입력
                        band_manual_topic_input,
                        
                        ft.Text("💡 수동 업로드 폴더에 사진을 넣고 포스팅 버튼을 누르세요.", size=11, color=ft.Colors.GREY_600),
                        ft.Text("✅ 성공 → 수동업로드_백업/ | ❌ 실패 → 수동업로드_실패/", size=11, color=ft.Colors.TEAL_600),
                        
                        ft.ElevatedButton(
                            "🚀 수동 주제로 포스팅",
                            icon=ft.Icons.SEND,
                            on_click=band_manual_post_click,
                            bgcolor=ft.Colors.ORANGE_700,
                            color=ft.Colors.WHITE,
                            height=45
                        )
                    ], spacing=10),
                    padding=15,
                    bgcolor=ft.Colors.ORANGE_50,
                    border_radius=10,
                    border=ft.border.all(1, ft.Colors.ORANGE_200)
                ),
                # ========== 수동 주제 포스팅 섹션 끝 ==========
                
                ft.Divider(height=20),
                
                # ========== 드라이브 자동 포스팅 섹션 시작 ==========
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.CLOUD_SYNC, color=ft.Colors.TEAL_700),
                            ft.Text("☁️ 드라이브 자동 포스팅", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_700)
                        ]),
                        ft.Text("구글 드라이브 폴더에 사진이 들어오면 자동으로 포스팅합니다.", size=12, color=ft.Colors.GREY_700),
                        
                        # 수련계획표 URL
                        ft.TextField(
                            ref=ft.Ref[ft.TextField](),
                            label="📅 수련계획표 주소 (구글 스프레드시트 공유 링크)",
                            hint_text="https://docs.google.com/spreadsheets/d/.../edit?usp=sharing",
                            value=self.settings.get('google_sheet_url', ''),
                            on_blur=lambda e: self._save_setting('google_sheet_url', e.control.value)
                        ),
                        ft.Text("💡 선택사항: 오늘 날짜의 수련내용을 자동으로 가져와 AI 글 주제로 사용합니다. 없으면 기본 주제 사용.", size=11, color=ft.Colors.GREY_600),
                        
                        # 상위 감시 폴더 (하위 폴더 자동 스캔)
                        ft.Text("📁 감시 폴더 설정:", size=14, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.TextField(
                                label="상위 폴더 경로 (하위 폴더들을 자동 감지)",
                                hint_text="/Users/.../Google Drive/수련사진및영상",
                                value=self.settings.get('drive_parent_folder', ''),
                                on_blur=lambda e: self._save_setting('drive_parent_folder', e.control.value),
                                expand=True
                            ),
                            ft.IconButton(
                                icon=ft.Icons.FOLDER_OPEN,
                                tooltip="폴더 선택",
                                icon_size=30,
                                icon_color=ft.Colors.BLUE_400,
                                on_click=lambda e: self._open_folder_picker(e)
                            )
                        ]),
                        ft.Text("💡 상위 폴더를 입력하면 그 안의 모든 하위 폴더(1시부, 2시부, 선수부 등)를 자동으로 감시합니다.", size=11, color=ft.Colors.GREY_600),
                        
                        # 스캔된 폴더 목록 표시
                        ft.Row([
                            ft.ElevatedButton(
                                "🔍 폴더 스캔",
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=lambda e: self._scan_drive_folders(page),
                                bgcolor=ft.Colors.GREY_700,
                                color=ft.Colors.WHITE
                            ),
                            ft.Text("", size=12, color=ft.Colors.GREY_700, ref=ft.Ref[ft.Text]())
                        ], spacing=10),
                        
                        # 스캔된 폴더 목록 컨테이너
                        ft.Container(
                            content=ft.Column([
                                ft.Text("스캔된 폴더: (폴더 스캔 버튼을 눌러주세요)", size=12, color=ft.Colors.GREY_500)
                            ], spacing=2),
                            ref=ft.Ref[ft.Container](),
                            padding=10,
                            bgcolor=ft.Colors.GREY_100,
                            border_radius=5,
                            visible=True
                        ),
                        
                        # 제외 폴더 설정
                        ft.TextField(
                            label="제외할 폴더 (콤마로 구분)",
                            hint_text="백업사진, 실패사진, 무제 폴더",
                            value=self.settings.get('drive_exclude_folders', '백업사진, 실패사진'),
                            on_blur=lambda e: self._save_setting('drive_exclude_folders', e.control.value)
                        ),
                        
                        ft.Divider(height=15),
                        
                        # 종목 설정
                        ft.Text("🥋 체육관 종목 설정:", size=14, weight=ft.FontWeight.BOLD),
                        ft.TextField(
                            label="체육관 주 종목 (AI 글 생성 시 사용)",
                            hint_text="예: 합기도, 태권도, 유도, 검도",
                            value=self.settings.get('gym_sport', '합기도'),
                            on_blur=lambda e: self._save_setting('gym_sport', e.control.value)
                        ),
                        ft.Text("💡 AI가 이 종목에 맞는 용어로 글을 작성합니다. (예: 합기도 → 낙법, 호신술 / 태권도 → 품새, 격파)", size=11, color=ft.Colors.GREY_600),
                        
                        ft.Divider(height=15),
                        
                        # 안내문 설정
                        ft.Text("📝 포스팅 하단 안내문:", size=14, weight=ft.FontWeight.BOLD),
                        ft.TextField(
                            label="하단 안내문 (글 마지막에 자동 추가)",
                            hint_text="수련의 생생한 현장을 담았습니다...",
                            value=self.settings.get('band_footer_notice', '수련의 생생한 현장을 담았습니다. 사진 및 영상 화질이 다소 아쉬울 수 있으나, 열심히 수련하는 모습을 함께 나눕니다! 🙏'),
                            multiline=True,
                            min_lines=2,
                            max_lines=4,
                            on_blur=lambda e: self._save_setting('band_footer_notice', e.control.value)
                        ),
                        
                        # 해시태그 설정
                        ft.TextField(
                            label="🏷️ 해시태그 (글 마지막에 추가, 8개씩 순환)",
                            hint_text="#태권도 #한국체대 #라이온짐 #수련",
                            value=self.settings.get('band_hashtags', '#한국체대 #라이온체육관 #합기도 #태권도 #줄넘기 #전문체육 #생활체육 #어린이건강 #청소년건강 #성인건강 #어린이운동 #청소년운동 #성인운동 #건강다이어트 #체력단련 #무도교육 #인성교육 #자기방어 #호신술 #운동습관'),
                            multiline=True,
                            min_lines=2,
                            max_lines=3,
                            on_blur=lambda e: self._save_setting('band_hashtags', e.control.value)
                        ),
                        ft.Text("💡 해시태그는 8개씩 순환됩니다. 많이 입력하면 포스팅마다 다른 조합이 사용됩니다.", size=11, color=ft.Colors.GREY_600),
                        
                        ft.Divider(height=10),
                        
                        # 백업/실패 폴더 자동 설정 안내
                        ft.Text("📂 백업/실패 폴더는 상위 폴더 안에 자동 생성됩니다: 백업사진/, 실패사진/", size=11, color=ft.Colors.TEAL_600),
                        
                        # 시작/중지 버튼
                        ft.Row([
                            ft.ElevatedButton(
                                "🚀 자동 감지 시작",
                                icon=ft.Icons.PLAY_ARROW,
                                on_click=lambda e: self._start_drive_auto_post(page),
                                bgcolor=ft.Colors.TEAL_700,
                                color=ft.Colors.WHITE
                            ),
                            ft.ElevatedButton(
                                "⏹️ 중지",
                                icon=ft.Icons.STOP,
                                on_click=lambda e: self._stop_drive_auto_post(page),
                                bgcolor=ft.Colors.RED_700,
                                color=ft.Colors.WHITE
                            ),
                            ft.Text("", ref=ft.Ref[ft.Text](), size=12, color=ft.Colors.GREY_700)
                        ], spacing=10),
                        
                        ft.Text("💡 사진/동영상 감지 후 60초 대기 → AI 글 생성 → 밴드 포스팅 → 백업사진/ 폴더로 이동", size=11, color=ft.Colors.GREY_500)
                    ], spacing=10),
                    padding=15,
                    bgcolor=ft.Colors.TEAL_50,
                    border_radius=10,
                    border=ft.border.all(1, ft.Colors.TEAL_200)
                ),
                # ========== 드라이브 자동 포스팅 섹션 끝 ==========
                
                ft.Divider(height=10),
                ft.Row([
                    band_reply_limit_input,
                    ft.ElevatedButton("댓글 자동 답글", icon=ft.Icons.CHAT, on_click=band_comment_reply_click, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
                    ft.ElevatedButton("중지", icon=ft.Icons.STOP, on_click=band_comment_reply_stop_click, bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)
                ], spacing=10, alignment=ft.MainAxisAlignment.START)
            ], scroll=ft.ScrollMode.AUTO),
            padding=20,
            expand=True
        )

        # 카페 포스팅 탭 구성
        def on_cafe_url_change(e):
            self.settings['cafe_url'] = cafe_url_input.value
            self.save_settings()
            print(f"✅ 카페 URL 저장됨: {cafe_url_input.value}")
        
        def on_cafe_menu_change(e):
            self.settings['cafe_menu_id'] = cafe_menu_input.value
            self.save_settings()
            print(f"✅ 카페 메뉴 ID 저장됨: {cafe_menu_input.value}")
        
        cafe_url_input = ft.TextField(
            label="카페 URL", 
            value=self.settings.get('cafe_url', 'https://cafe.naver.com/lionjiujitsu'), 
            hint_text="예: https://cafe.naver.com/지점이름",
            expand=True,
            on_blur=on_cafe_url_change
        )
        cafe_menu_input = ft.TextField(
            label="메뉴 ID (menuid)", 
            value=self.settings.get('cafe_menu_id', ''), 
            hint_text="카페 게시판 클릭 시 주소창의 menuId=숫자 부분 입력",
            expand=True,
            on_blur=on_cafe_menu_change
        )
        cafe_title_input = ft.TextField(label="제목", expand=True)
        cafe_content_input = ft.TextField(label="내용", multiline=True, min_lines=10, expand=True)
        
        def on_cafe_image_change(e):
            self.settings['cafe_auto_image'] = cafe_image_checkbox.value
            self.save_settings()
            
        cafe_image_checkbox = ft.Checkbox(
            label="이미지 자동 포함", 
            value=self.settings.get('cafe_auto_image', self.settings.get('auto_image', True)),
            on_change=on_cafe_image_change
        )
        
        def post_to_cafe_click(e):
            if not cafe_url_input.value or not cafe_menu_input.value or not cafe_content_input.value:
                page.snack_bar = ft.SnackBar(content=ft.Text("카페 URL, 메뉴 ID, 내용을 모두 입력해주세요."))
                page.snack_bar.open = True
                page.update()
                return
            
            # 이미지 준비 (자동 이미지 설정 시)
            images = []
            if cafe_image_checkbox.value:
                images = self.get_images_to_upload(platform='cafe')
                if images:
                    print(f"📸 카페 업로드용 이미지 {len(images)}개 확보")

            # 독립된 카페 자동화 모듈 호출
            start_time = time.time()
            cafe_auto = NaverCafeAutomation(self.get_or_create_driver())
            success = cafe_auto.post_to_cafe(
                cafe_url_input.value, 
                cafe_menu_input.value, 
                cafe_title_input.value, 
                cafe_content_input.value,
                image_paths=images
            )
            
            duration = time.time() - start_time
            self.add_model_usage_log(
                topic=cafe_title_input.value or cafe_content_input.value[:30],
                model="-",
                status="업로드 성공" if success else "실패",
                reason="네이버 카페",
                target="카페 업로드",
                duration_sec=duration
            )

            if success:
                page.snack_bar = ft.SnackBar(content=ft.Text("✅ 카페에 성공적으로 게시되었습니다!"), bgcolor=ft.Colors.GREEN)
            else:
                page.snack_bar = ft.SnackBar(content=ft.Text("❌ 카페 게시 실패. 로그를 확인하세요."), bgcolor=ft.Colors.RED)
            page.snack_bar.open = True
            page.update()

        def generate_cafe_content_click(e):
            selected_topic = self.select_sequential_topic('cafe')
            if not selected_topic:
                page.snack_bar = ft.SnackBar(content=ft.Text("대기 중인 주제가 없습니다. [사용자 설정]에서 [카페 주제 목록]을 입력해 주세요."))
                page.snack_bar.open = True
                page.update()
                return
            
            # 진행 표시 시작
            page.snack_bar = ft.SnackBar(content=ft.Text(f"🤖 '{selected_topic}' 주제로 카페 글을 생성 중..."), duration=3000)
            page.snack_bar.open = True
            page.update()
            
            try:
                start_time = time.time()
                result = self.gpt_handler.generate_platform_content(selected_topic, platform='cafe')
                cafe_title_input.value = result.get('title', '')
                cafe_content_input.value = result.get('content', '')
                
                duration = time.time() - start_time
                self.add_model_usage_log(
                    topic=selected_topic,
                    model=result.get('model', 'gpt-4o-mini'),
                    status="성공",
                    target="카페",
                    duration_sec=duration
                )
                
                page.snack_bar = ft.SnackBar(content=ft.Text("✅ 카페 내용 생성 완료!"), bgcolor=ft.Colors.GREEN)
                page.snack_bar.open = True
                page.update()
            except Exception as ge:
                print(f"❌ 카페 내용 생성 중 오류: {ge}")
                self.add_model_usage_log(topic=selected_topic, model="-", status="실패", reason=str(ge), target="카페")
                page.snack_bar = ft.SnackBar(content=ft.Text(f"❌ 생성 실패: {str(ge)}"), bgcolor=ft.Colors.RED)
                page.snack_bar.open = True
                page.update()

        def auto_post_cafe_click(e):
            try:
                generate_cafe_content_click(None)
                if not cafe_content_input.value: 
                    return
                post_to_cafe_click(None)
            except Exception as ae:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"❌ 카페 자동 포스팅 실패: {str(ae)}"), bgcolor=ft.Colors.RED)
                page.snack_bar.open = True
                page.update()

        cafe_settings_tab = ft.Container(
            content=ft.Column([
                ft.Text("☕ 네이버 카페 포스팅", size=20, weight=ft.FontWeight.BOLD),
                cafe_url_input,
                cafe_menu_input,
                cafe_title_input,
                cafe_content_input,
                cafe_image_checkbox,
                ft.Row([
                    ft.ElevatedButton("내용 생성", icon=ft.Icons.AUTO_AWESOME, on_click=generate_cafe_content_click),
                    ft.ElevatedButton("수동 포스팅", icon=ft.Icons.UPLOAD, on_click=post_to_cafe_click, bgcolor=ft.Colors.BROWN_400, color=ft.Colors.WHITE),
                    ft.ElevatedButton("AI 자동 포스팅", icon=ft.Icons.BOLT, on_click=auto_post_cafe_click, bgcolor=ft.Colors.AMBER_700, color=ft.Colors.WHITE)
                ], spacing=10)
            ], scroll=ft.ScrollMode.AUTO),
            padding=20,
            expand=True
        )

        # 유휴 활동 탭 구성
        idle_visit_count = ft.Slider(min=0, max=20, divisions=20, label="{value}회", value=2)
        idle_use_ai_comment = ft.Checkbox(label="AI 기반 자연스러운 댓글 남기기", value=True)
        idle_do_like = ft.Checkbox(label="공감(❤️) 클릭 포함", value=True)
        idle_status_text = ft.Text("상태: 대기 중", color=ft.Colors.GREY_700)
        
        def start_idle_activity_click(e):
            if hasattr(self, 'idle_running') and self.idle_running:
                # 이미 실행 중이면 중단 요청 (UI는 정지 버튼이 처리)
                return

            self.idle_running = True
            btn_start.disabled = True
            btn_stop.disabled = False
            idle_status_text.value = "상태: 소통 활동 진행 중..."
            page.update()
            
            # 설정값 가져오기 (초 단위)
            try:
                min_int = int(idle_min_interval.value or 30)
                max_int = int(idle_max_interval.value or 60)
            except:
                min_int = 30
                max_int = 60
            
            print(f"📊 소통 설정: 횟수={int(idle_visit_count.value)}, 간격={min_int}~{max_int}초, 좋아요={idle_do_like.value}, AI={idle_use_ai_comment.value}")
            
            # 별도 스레드에서 실행하여 UI 프리징 방지
            def run_idle_task():
                # 🔒 락 획득 (다른 작업이 끝날 때까지 대기)
                if self.is_browser_busy:
                    print("⏳ 다른 작업이 진행 중입니다. 완료까지 대기...")
                    idle_status_text.value = "상태: 다른 작업 완료 대기 중..."
                    try:
                        page.update()
                    except:
                        pass
                
                self.browser_lock.acquire()
                self.is_browser_busy = True
                self.update_activity_time()
                print("🔓 [이웃 방문] 락 획득 완료")
                
                try:
                    idle_module = IdleActivity(self.get_or_create_driver(), self.gpt_handler, self.base_dir)
                    
                    # 실행 상태 전달을 위해 idle_module에 플래그 설정
                    idle_module.is_running = True
                    self.current_idle_module = idle_module # 중단을 위해 참조 저장
                    
                    # 이웃 방문 및 소통 실행
                    success = idle_module.visit_and_interact(
                        count=int(idle_visit_count.value),
                        do_like=idle_do_like.value,
                        use_ai=idle_use_ai_comment.value,
                        min_interval=min_int,
                        max_interval=max_int
                    )
                    
                    if success:
                        idle_status_text.value = "상태: 소통 활동 완료"
                        page.snack_bar = ft.SnackBar(content=ft.Text("✅ 소통 활동을 성공적으로 마쳤습니다!"), bgcolor=ft.Colors.GREEN)
                    else:
                        if not idle_module.is_running: # 사용자가 중단한 경우
                             idle_status_text.value = "상태: 사용자에 의해 중단됨"
                        else:
                            idle_status_text.value = "상태: 활동 중 일부 오류 또는 중단"
                            page.snack_bar = ft.SnackBar(content=ft.Text("⚠️ 소통 활동이 완료되지 않았습니다."), bgcolor=ft.Colors.ORANGE)
                    
                    page.snack_bar.open = True
                    
                except Exception as e:
                    print(f"❌ 이웃 소통 오류: {e}")
                    idle_status_text.value = f"상태: 오류 발생 - {str(e)[:30]}"
                    
                finally:
                    # 🔧 확실한 상태 정리 + 락 해제
                    self.idle_running = False
                    self.current_idle_module = None
                    self.is_browser_busy = False
                    self.browser_lock.release()
                    self.update_activity_time()
                    print("🔒 [이웃 방문] 락 해제 완료")
                    btn_start.disabled = False
                    btn_stop.disabled = True
                    try:
                        page.update()
                    except:
                        pass

            import threading
            threading.Thread(target=run_idle_task, daemon=True).start()

        def stop_idle_activity_click(e):
            if hasattr(self, 'current_idle_module') and self.current_idle_module:
                self.current_idle_module.is_running = False
                print("🛑 소통 활동 중단 요청됨")
            
            self.idle_running = False
            idle_status_text.value = "상태: 중단 중..."
            btn_stop.disabled = True
            page.update()

        # 버튼 정의
        btn_start = ft.ElevatedButton("▶ 이웃 블로그 방문 시작", icon=ft.Icons.PLAY_ARROW, on_click=start_idle_activity_click, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
        btn_stop = ft.ElevatedButton("중단", icon=ft.Icons.STOP, on_click=stop_idle_activity_click, bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE, disabled=True)

        idle_settings_tab = ft.Container(
            content=ft.Column([
                ft.Text("🤝 블로그 소통 활동", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                ft.Text("이웃 블로그를 방문하여 공감과 댓글을 남기고, 내 블로그의 댓글에 답글을 답니다.", size=14),
                ft.Divider(),
                
                # 방문소통 설정
                ft.Container(
                    content=ft.Column([
                        ft.Text("📌 이웃 블로그 방문 (좋아요 + 댓글)", size=16, weight=ft.FontWeight.BOLD),
                        ft.Text("서로이웃 글 목록에서 다른 사람의 글에 좋아요와 댓글을 남깁니다.", size=12, color=ft.Colors.GREY_600),
                        ft.Row([
                            ft.Text("1회 방문 횟수:"), 
                            idle_visit_count,
                            idle_min_interval,
                            idle_max_interval
                        ], alignment=ft.MainAxisAlignment.START, spacing=10),
                        ft.Row([
                            idle_do_like,
                            idle_use_ai_comment
                        ], spacing=20),
                    ]),
                    padding=10,
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=8
                ),
                
                ft.Divider(),
                ft.Row([
                    ft.ElevatedButton("설정 저장", icon=ft.Icons.SAVE, on_click=save_idle_settings, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
                    btn_start,
                    btn_stop
                ], spacing=10),
                idle_status_text,
                
                ft.Divider(height=30),
                
                # ========== 댓글 자동 답글 섹션 ==========
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.AUTO_FIX_HIGH, color=ft.Colors.PURPLE_600, size=24),
                            ft.Text("💬 댓글 자동 답글 (신기능!)", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_700)
                        ], spacing=10),
                        
                        ft.Text(
                            "알림에 있는 모든 댓글을 자동으로 확인하고 답글을 작성합니다.",
                            size=13,
                            color=ft.Colors.GREY_700
                        ),
                        
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_600, size=16),
                                    ft.Text("알림창(종 모양) 댓글 자동 확인", size=12)
                                ]),
                                ft.Row([
                                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_600, size=16),
                                    ft.Text("각 게시글로 이동하여 답글 작성", size=12)
                                ]),
                                ft.Row([
                                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_600, size=16),
                                    ft.Text("GPT로 맞춤형 답글 생성 (선택)", size=12)
                                ]),
                            ], spacing=8),
                            padding=10,
                            bgcolor=ft.Colors.PURPLE_50,
                            border_radius=8,
                            border=ft.border.all(1, ft.Colors.PURPLE_200)
                        ),
                        
                        ft.Row([
                            ft.TextField(
                                label="처리할 댓글 수",
                                value="10",
                                width=120,
                                keyboard_type=ft.KeyboardType.NUMBER,
                                on_change=lambda e: setattr(self, 'blog_reply_limit', e.control.value)
                            ),
                            ft.ElevatedButton(
                                "🤖 댓글 자동 답글 시작",
                                icon=ft.Icons.CHAT_BUBBLE,
                                on_click=lambda e: self.auto_reply_comments_click(e, use_ai=True),
                                bgcolor=ft.Colors.PURPLE_600,
                                color=ft.Colors.WHITE,
                                height=45
                            ),
                            ft.ElevatedButton(
                                "기본 답글 사용",
                                icon=ft.Icons.MESSAGE,
                                on_click=lambda e: self.auto_reply_comments_click(e, use_ai=False),
                                bgcolor=ft.Colors.PURPLE_400,
                                color=ft.Colors.WHITE,
                                height=45
                            ),
                            ft.ElevatedButton(
                                "중지",
                                icon=ft.Icons.STOP,
                                on_click=lambda e: self.stop_comment_reply_click(e),
                                bgcolor=ft.Colors.RED_600,
                                color=ft.Colors.WHITE,
                                height=45
                            ),
                        ], spacing=10, wrap=True),
                        
                        ft.Text(
                            "💡 Tip: AI 답글은 댓글 내용을 분석하여 자연스러운 답변을 생성합니다.",
                            size=11,
                            color=ft.Colors.GREY_500,
                            italic=True
                        )
                    ], spacing=12),
                    padding=15,
                    bgcolor=ft.Colors.PURPLE_50,
                    border_radius=12,
                    border=ft.border.all(2, ft.Colors.PURPLE_300)
                ),
                # ========== 댓글 자동 답글 섹션 끝 ==========
                
                ft.Text("※ AI 지침은 [GPT 설정] 탭의 '소통 지침' 필드에서 수정 가능합니다.", size=12, color=ft.Colors.GREY_600, italic=True),
            ], scroll=ft.ScrollMode.AUTO, spacing=15),
            padding=20,
            expand=True
        )


        ai_usage_tab = ft.Column(
            controls=[
                ft.Text("AI 모델 사용 내역", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("성공/실패 및 원인을 한국어로 확인하세요.", size=12, color=ft.Colors.GREY_700),
                ft.Row(
                    controls=[
                        self.model_usage_count_text,
                        clear_usage_btn,
                        more_usage_btn,
                        self.model_usage_latest_text
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("실사용 추정 비용 (로그 기반)", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800),
                        self.model_usage_cost_text,
                        ft.Container(
                            content=ft.Column([self.model_usage_cost_detail], scroll=ft.ScrollMode.ALWAYS),
                            padding=ft.padding.symmetric(horizontal=8, vertical=6),
                            bgcolor=ft.Colors.WHITE,
                            border=ft.border.all(1, ft.Colors.BLUE_100),
                            border_radius=6,
                            height=110,
                            alignment=ft.alignment.top_left,
                        )
                    ], spacing=6),
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=8,
                    border=ft.border.all(1, ft.Colors.BLUE_100)
                ),
                self.model_usage_card_container,
                # 인라인 전체 보기 패널 (모달 대체, 기본 숨김)
                full_panel
            ],
            spacing=10,
            expand=True
        )

        # 탭 컨트롤
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="블로그 시작",
                    icon=ft.Icons.EDIT_NOTE,
                    content=main_content_tab
                ),
                ft.Tab(
                    text="밴드 포스팅",
                    icon=ft.Icons.GROUPS,
                    content=band_settings_tab
                ),
                ft.Tab(
                    text="카페 포스팅",
                    icon=ft.Icons.LOCAL_CAFE,
                    content=cafe_settings_tab
                ),
                ft.Tab(
                    text="소통 활동",
                    icon=ft.Icons.PEOPLE,
                    content=idle_settings_tab
                ),
                ft.Tab(
                    text="스마트 스케줄러",
                    icon=ft.Icons.SCHEDULE,
                    content=scheduler_tab_content
                ),
                ft.Tab(
                    text="블로그 타이머",
                    icon=ft.Icons.TIMER,
                    content=timer_settings_tab
                ),
                ft.Tab(
                    text="GPT 설정",
                    icon=ft.Icons.SETTINGS_APPLICATIONS,
                    content=gpt_settings_tab
                ),
                ft.Tab(
                    text="사용자 설정",
                    icon=ft.Icons.PERSON,
                    content=user_settings_tab
                ),
                ft.Tab(
                    text="AI 사용 로그",
                    icon=ft.Icons.LIST_ALT,
                    content=ai_usage_tab
                )
            ],
            expand=True
        )

        # 시리얼 인증 상태 정보 가져오기
        serial_status = self.get_serial_status()
        
        # 시리얼 상태 표시 컴포넌트
        serial_status_text = ft.Text(
            value=f"🔐 {serial_status['status']} | {serial_status['message']}",
            size=14,
            weight=ft.FontWeight.BOLD,
            color=serial_status['color']
        )
        
        # 유효기간 표시 (인증된 경우에만)
        days_text = ft.Text(
            value=f"📅 유효기간: {serial_status['days_remaining']}일 남음" if serial_status['days_remaining'] > 0 else "",
            size=12,
            color=ft.Colors.GREY_600
        )
        
        # 업데이트 버튼 생성
        update_button = ft.ElevatedButton(
            text="🔄 업데이트 확인",
            icon=ft.Icons.SYSTEM_UPDATE,
            on_click=lambda _: self.handle_update_click(page),
            bgcolor=ft.Colors.GREEN_600,
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8)
            ),
            tooltip="최신 버전으로 업데이트합니다"
        )
        
        # 상단 헤더 (시계 + 시리얼 상태 + 업데이트 버튼)
        header = ft.Container(
            content=ft.Row([
                # 왼쪽: 시리얼 상태
                ft.Column([
                    serial_status_text,
                    days_text
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.START),
                
                # 중앙: 시계
                self.clock_text,
                
                # 오른쪽: 업데이트 버튼
                update_button
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.symmetric(vertical=15, horizontal=20),
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
            border_radius=10,
            margin=ft.margin.only(bottom=10)
        )
        
        # 페이지에 헤더와 탭 추가
        page.add(header, tabs)
        # 이제 테이블이 페이지에 추가되었으므로 초기화 후 갱신
        self.model_usage_initialized = True
        self.refresh_model_usage_table(force=True)
        
        # 설정 로드
        load_gpt_settings()
        load_user_settings()
        load_app_settings()
        load_timer_settings()
        load_usage_stats()  # 사용 통계 로드 추가
        load_draft()

        # auto_topic_checkbox 변경 이벤트 처리
        def on_auto_topic_change(e):
            topic_count = 0  # 함수 시작 시 초기화
            if auto_topic_checkbox.value:
                # 주제 목록 수와 현재 인덱스 가져오기
                try:
                    if os.path.exists(os.path.join(self.base_dir, 'config/user_settings.txt')):
                        with open(os.path.join(self.base_dir, 'config/user_settings.txt'), 'r', encoding='utf-8') as f:
                            settings = json.load(f)
                            topics_str = settings.get('blog_topics', '')
                            if topics_str:
                                topics = [topic.strip() for topic in topics_str.split(',') if topic.strip()]
                                topic_count = len(topics)
                except Exception:
                    pass
                
                auto_topic_status.value = f"자동 주제 모드: 활성화 (다음: {self.topic_indices['blog'] + 2}/{topic_count})"
            else:
                auto_topic_status.value = "자동 주제 모드: 비활성화"
                
            auto_topic_status.color = ft.Colors.GREEN if auto_topic_checkbox.value else ft.Colors.GREY_600
            self._debug_log("H3", "blog_writer_app.on_auto_topic_change", "auto topic toggle", {"enabled": auto_topic_checkbox.value, "topic_count": topic_count, "current_topic_index": self.topic_indices['blog']})
            page.update()
            
        auto_topic_checkbox.on_change = on_auto_topic_change
        
        # 초기 상태 설정
        on_auto_topic_change(None)
        
        # 타이머에서 사용할 참조들 저장
        self.page_ref = page
        self.send_message_func = send_message
        self.next_post_time_text_ref = next_post_time_text  # 다음 포스팅 시간 텍스트 참조 추가
        
        # 시리얼 상태 UI 참조 저장
        self.serial_status_text_ref = serial_status_text
        self.days_text_ref = days_text
        
        update_scheduler_ui()
        self.start_serial_status_updater()
        
    def check_for_updates(self):
        """백그라운드에서 업데이트 확인"""
        def update_check():
            try:
                print("🔄 업데이트 확인 중...")
                
                # 현재 버전 로드
                current_version = self.get_current_version()
                updater = AutoUpdater(current_version)
                
                # 원격 버전 확인
                remote_version, changelog = updater.get_remote_version()
                
                if remote_version and updater.compare_versions(remote_version):
                    print(f"🎉 새 버전 발견: v{remote_version}")
                    print("📋 변경사항:")
                    for change in changelog:
                        print(f"  - {change}")
                    print("\n💡 프로그램 재시작 시 자동으로 업데이트됩니다.")
                else:
                    print("✅ 현재 버전이 최신입니다.")
                    
            except Exception as e:
                print(f"⚠️ 업데이트 확인 실패: {e}")
                
        # 백그라운드 스레드에서 실행
        threading.Thread(target=update_check, daemon=True).start()
        
    def get_current_version(self):
        """현재 버전 가져오기"""
        try:
            # 여러 경로에서 version.json 찾기
            possible_paths = [
                os.path.join(self.base_dir, 'version.json'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'version.json'),
            ]
            
            # PyInstaller frozen 모드에서 추가 경로
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(sys.executable)
                possible_paths.extend([
                    os.path.join(exe_dir, 'version.json'),
                    os.path.join(exe_dir, '..', 'Frameworks', 'version.json'),  # macOS app bundle
                    os.path.join(exe_dir, '..', 'Resources', 'version.json'),
                ])
            
            for version_file in possible_paths:
                if os.path.exists(version_file):
                    with open(version_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        version = data.get('version', '1.0.0')
                        if version != '1.0.0':  # 실제 버전 찾음
                            return version
            return '1.0.0'
        except:
            return '1.0.0'
            
    def perform_update(self):
        """업데이트 실행"""
        try:
            print("🔄 업데이트 시작...")
            
            current_version = self.get_current_version()
            updater = AutoUpdater(current_version)
            
            success, message = updater.check_and_update()
            
            if success:
                print(f"✅ {message}")
                print("🔄 프로그램을 재시작해주세요.")
                return True
            else:
                print(f"ℹ️ {message}")
                return False
                
        except Exception as e:
            print(f"❌ 업데이트 실패: {e}")
            return False
            
    def handle_update_click(self, page):
        """업데이트 버튼 클릭 핸들러"""
        def update_process():
            try:
                # 로딩 다이얼로그 표시
                loading_dialog = ft.AlertDialog(
                    title=ft.Text("🔄 업데이트 확인 중...", text_align=ft.TextAlign.CENTER),
                    content=ft.Container(
                        content=ft.Column([
                            ft.ProgressRing(),
                            ft.Text("잠시만 기다려주세요...", text_align=ft.TextAlign.CENTER)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        height=100
                    ),
                    modal=True
                )
                
                page.overlay.append(loading_dialog)
                loading_dialog.open = True
                page.update()
                
                # 업데이트 확인
                current_version = self.get_current_version()
                updater = AutoUpdater(current_version)
                
                # 원격 버전 확인
                remote_version, changelog = updater.get_remote_version()
                
                # 로딩 다이얼로그 닫기
                loading_dialog.open = False
                page.update()
                
                if not remote_version:
                    # 네트워크 오류
                    error_dialog = ft.AlertDialog(
                        title=ft.Text("❌ 업데이트 확인 실패"),
                        content=ft.Text("인터넷 연결을 확인해주세요.\n원격 저장소에 접근할 수 없습니다."),
                        actions=[ft.TextButton("확인", on_click=lambda _: self.close_dialog(page, error_dialog))]
                    )
                    page.overlay.append(error_dialog)
                    error_dialog.open = True
                    page.update()
                    return
                
                if not updater.compare_versions(remote_version):
                    # 최신 버전
                    info_dialog = ft.AlertDialog(
                        title=ft.Text("✅ 최신 버전"),
                        content=ft.Text(f"현재 버전 v{current_version}이 최신입니다!"),
                        actions=[ft.TextButton("확인", on_click=lambda _: self.close_dialog(page, info_dialog))]
                    )
                    page.overlay.append(info_dialog)
                    info_dialog.open = True
                    page.update()
                    return
                
                # 업데이트 확인 다이얼로그
                changelog_text = "\n".join([f"• {change}" for change in changelog])
                
                def perform_update_action(_):
                    confirm_dialog.open = False
                    page.update()
                    
                    # 업데이트 진행 다이얼로그
                    progress_dialog = ft.AlertDialog(
                        title=ft.Text("🚀 업데이트 진행 중", text_align=ft.TextAlign.CENTER),
                        content=ft.Container(
                            content=ft.Column([
                                ft.ProgressRing(),
                                ft.Text("업데이트를 적용하고 있습니다...", text_align=ft.TextAlign.CENTER),
                                ft.Text("잠시만 기다려주세요.", text_align=ft.TextAlign.CENTER, color=ft.Colors.GREY_600)
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            height=120
                        ),
                        modal=True
                    )
                    
                    page.overlay.append(progress_dialog)
                    progress_dialog.open = True
                    page.update()
                    
                    # 업데이트 실행
                    success, message = updater.check_and_update()
                    
                    progress_dialog.open = False
                    page.update()
                    
                    if success:
                        # 빌드된 앱인지 확인
                        is_built_app = getattr(sys, 'frozen', False)
                        
                        # 성공 다이얼로그
                        dialog_content = [
                            ft.Text(message),
                            ft.Text("모든 설정과 시리얼 정보는 안전하게 보존되었습니다.", color=ft.Colors.GREEN_600),
                        ]
                        
                        if is_built_app:
                            # 빌드된 앱은 새 버전 다운로드 필요
                            dialog_content.extend([
                                ft.Divider(),
                                ft.Text("⚠️ 빌드된 앱을 사용 중입니다.", weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_600),
                                ft.Text("완전한 업데이트를 위해 새 버전을 다운로드해주세요:", size=12),
                                ft.TextButton(
                                    "📥 다운로드 페이지 열기",
                                    url="https://github.com/kwanwon/naver-blog-automation/releases"
                                ),
                                ft.Text("다운로드 후 현재 앱을 종료하고 새 앱을 실행하세요.", size=12, color=ft.Colors.GREY_600)
                            ])
                        else:
                            dialog_content.append(ft.Text("프로그램을 재시작해주세요.", weight=ft.FontWeight.BOLD))
                        
                        success_dialog = ft.AlertDialog(
                            title=ft.Text("🎉 업데이트 완료!"),
                            content=ft.Column(dialog_content),
                            actions=[
                                ft.TextButton("재시작", on_click=lambda _: self.restart_application()),
                                ft.TextButton("나중에", on_click=lambda _: self.close_dialog(page, success_dialog))
                            ]
                        )
                        page.overlay.append(success_dialog)
                        success_dialog.open = True
                        page.update()
                    else:
                        # 실패 다이얼로그
                        error_dialog = ft.AlertDialog(
                            title=ft.Text("❌ 업데이트 실패"),
                            content=ft.Text(f"업데이트 중 오류가 발생했습니다:\n{message}"),
                            actions=[ft.TextButton("확인", on_click=lambda _: self.close_dialog(page, error_dialog))]
                        )
                        page.overlay.append(error_dialog)
                        error_dialog.open = True
                        page.update()
                
                confirm_dialog = ft.AlertDialog(
                    title=ft.Text(f"🆕 새 버전 발견: v{remote_version}"),
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(f"현재 버전: v{current_version}", weight=ft.FontWeight.BOLD),
                            ft.Text(f"최신 버전: v{remote_version}", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_600),
                            ft.Divider(),
                            ft.Text("📋 변경사항:", weight=ft.FontWeight.BOLD),
                            ft.Text(changelog_text, color=ft.Colors.GREY_700),
                            ft.Divider(),
                            ft.Text("⚠️ 업데이트 중에는 프로그램을 종료하지 마세요!", color=ft.Colors.ORANGE_600, size=12)
                        ]),
                        height=300,
                        width=500
                    ),
                    actions=[
                        ft.TextButton("취소", on_click=lambda _: self.close_dialog(page, confirm_dialog)),
                        ft.ElevatedButton(
                            "업데이트",
                            on_click=perform_update_action,
                            bgcolor=ft.Colors.GREEN_600,
                            color=ft.Colors.WHITE
                        )
                    ]
                )
                
                page.overlay.append(confirm_dialog)
                confirm_dialog.open = True
                page.update()
                
            except Exception as e:
                # 예외 처리
                if 'loading_dialog' in locals() and loading_dialog.open:
                    loading_dialog.open = False
                    page.update()
                    
                error_dialog = ft.AlertDialog(
                    title=ft.Text("❌ 오류 발생"),
                    content=ft.Text(f"업데이트 확인 중 오류가 발생했습니다:\n{str(e)}"),
                    actions=[ft.TextButton("확인", on_click=lambda _: self.close_dialog(page, error_dialog))]
                )
                page.overlay.append(error_dialog)
                error_dialog.open = True
                page.update()
        
        # 백그라운드에서 실행
        threading.Thread(target=update_process, daemon=True).start()
        
    def close_dialog(self, page, dialog):
        """다이얼로그 닫기"""
        dialog.open = False
        page.update()
        
    def restart_application(self):
        """애플리케이션 재시작"""
        try:
            print("🔄 프로그램을 재시작합니다...")
            
            # 1. 현재 창 닫기 시도
            if hasattr(self, 'page') and self.page:
                try:
                    self.page.window_close()
                except:
                    pass
            
            # 2. 운영체제별 재시작
            if sys.platform == 'win32':
                # Windows: 새 프로세스 시작 후 현재 프로세스 종료
                import subprocess
                python = sys.executable
                subprocess.Popen([python] + sys.argv, 
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
                sys.exit(0)
            else:
                # macOS/Linux: execl 사용
                python = sys.executable
                os.execl(python, python, *sys.argv)
                
        except Exception as e:
            print(f"❌ 재시작 실패: {e}")
            print("수동으로 프로그램을 재시작해주세요.")

if __name__ == "__main__":
    # Windows PyInstaller 빌드 필수! (무한 재귀 방지)
    import multiprocessing
    multiprocessing.freeze_support()
    
    # 프로그램 시작 전 업데이트 확인 (안전 모드: 확인만 하고 자동설치 안 함)
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        version_file = os.path.join(current_dir, 'version.json')
        
        current_version = '1.0.0'
        if os.path.exists(version_file):
            with open(version_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                current_version = data.get('version', '1.0.0')
                
        updater = AutoUpdater(current_version)
        
        # 업데이트 가능 여부만 확인
        is_available, new_ver = updater.check_update_available()
        
        if is_available:
            print(f"✨ 새 버전(v{new_ver})이 있습니다!")
            print("   (설정 탭에서 업데이트를 진행해주세요)")
        else:
            print(f"✅ 현재 최신 버전(v{current_version})입니다.")
            
    except Exception as e:
        print(f"⚠️ 업데이트 확인 중 오류 (무시됨): {e}")
            
    
    # 메인 앱 실행
    app = BlogWriterApp()
    ft.app(target=app.main) 