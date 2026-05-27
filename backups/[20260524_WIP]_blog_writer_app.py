# -*- coding: utf-8 -*-
import flet as ft # type: ignore
from modules.ai_handler import AIHandler as GPTHandler
from modules.serial_auth import BlogSerialAuth
from modules.auto_updater import AutoUpdater  # 자동 업데이트 추가
from config.config import Config
from modules.scheduler_engine import SmartScheduler
from naver_band_auto import NaverBandAutomation
from naver_band_comment_reply import NaverBandCommentReply  # 밴드 댓글 답글
from naver_cafe_auto import NaverCafeAutomation
from modules.idle_activity import IdleActivity
from modules.marketing.persona_manager import PersonaManager
from modules.marketing.target_finder import TargetFinder
from modules.marketing.smart_reply import SmartReply
from modules.marketing.history_manager import HistoryManager
from modules.marketing.comment_poster import CommentPoster
from modules.marketing.reply_crawler import ReplyCrawler
from selenium.webdriver.common.by import By

import subprocess
import os
import asyncio
import sys  # sys 모듈 추가
import io
import pyperclip

# 🆕 Windows 콘솔 인코딩 문제 해결 (이모지 출력 시 UnicodeEncodeError 방지)
# 🆕 Windows 콘솔 인코딩 문제 해결 및 Noconsole 모드 지원
if sys.platform == 'win32':
    try:
        # stdout/stderr가 None이 아닐 때만 인코딩 설정 (Noconsole 모드 대응)
        if sys.stdout and hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if sys.stderr and hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        # 콘솔이 없는 경우 (noconsole 모드) 또는 설정 실패 시 무시
        pass

import platform  # 플랫폼 감지 추가
from datetime import datetime, timedelta
import json
from utils.folder_cleanup import FolderCleanup  # 추가
from utils.path_utils import (
    get_app_data_dir, get_config_dir, get_data_dir, get_log_dir,
    get_app_settings_path, get_gpt_settings_path, get_api_key_path,
    get_user_settings_path, get_custom_prompts_path
)
import random
import hashlib
import threading
import time
import traceback

from logger_utils import StreamLogger # 추가

# 모바일 가독성 줄바꿈 헬퍼 함수 (25자 한글/단어 보존 스마트 행갈이)
def format_content_for_mobile(content, max_chars=25):
    if not content:
        return ""
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

class BlogWriterApp:
    def __init__(self):
        # 🚀 로거 초기화 (가장 먼저 실행)
        try:
            # 안전한 로그 디렉토리 확보 (os.getcwd 대신 get_log_dir 사용)
            log_dir = get_log_dir()
            os.makedirs(log_dir, exist_ok=True)
            self.console_log_path = os.path.join(log_dir, 'console.log')
        except:
            self.console_log_path = None

        self.stream_logger = StreamLogger(self.console_log_path)
        sys.stdout = self.stream_logger
        sys.stderr = self.stream_logger
        
        # 🚀 [Fix] 루트 로거의 핸들러를 StreamLogger로 모두 교체하여 Noconsole 충돌 방지
        import logging
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        class CustomStreamHandler(logging.StreamHandler):
            def emit(self, record):
                try:
                    msg = self.format(record)
                    self.stream.write(msg + '\n')
                except Exception:
                    pass
        
        custom_handler = CustomStreamHandler(self.stream_logger)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        custom_handler.setFormatter(formatter)
        root_logger.addHandler(custom_handler)
        
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

        
        # 🚀 [Fix] 앱 시작 시 디바이스 정보 및 사용 횟수 즉시 업데이트
        self._initial_device_info_update()
        
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
        
        # 🟢 종목 기반 주제 자동 수정 (마이그레이션)
        # 기본 주제 목록에 '태권도'가 포함되어 있고, 현재 설정된 종목이 '태권도'가 아닌 경우
        # 자동으로 해당 종목으로 치환하여 사용자 편의성 증대
        try:
            gym_sport = self.settings.get('gym_sport', '합기도')
            primary_sport = gym_sport.split(',')[0].strip()
            
            # 태권도가 아닌 경우에만 치환 로직 실행
            if primary_sport != '태권도' and primary_sport:
                changed = False
                for key in ['blog_topics', 'band_topics', 'cafe_topics']:
                    topics = self.settings.get(key, '')
                    if topics and '태권도' in topics:
                        # 단순 치환
                        new_topics = topics.replace('태권도', primary_sport)
                        self.settings[key] = new_topics
                        changed = True
                        print(f"🔄 [Auto-Fix] {key}의 기본값 '태권도'를 '{primary_sport}'(으)로 일괄 수정함")
                
                if changed:
                    self.save_settings()
        except Exception as e:
            print(f"⚠️ 주제 자동 수정 중 오류: {e}")
        self.use_dummy = self.settings.get('use_dummy', False)
        
        self.gpt_handler = GPTHandler(use_dummy=self.use_dummy)
        self.current_title = ""
        self.current_content = ""
        self.current_tags = []
        self.last_save_content = None
        self.browser_driver = None  # 브라우저 드라이버 인스턴스
        self.temp_driver = None  # 임시 브라우저 드라이버 인스턴스
        
        # 🔒 브라우저 락 - 동시 실행 방지 (스케줄러, 수동 실행 등)
        self.browser_lock = threading.Lock()
        self.is_browser_busy = False  # 현재 브라우저 사용 중인지
        # AI 모델 사용 로그 저장
        self.model_usage_logs = []
        self.model_usage_log_path = os.path.join(get_config_dir(), 'model_usage_logs.json')
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
        # 🆕 크로스 플랫폼: 공식 설정 디렉토리 사용 (path_utils)
        scheduler_path = os.path.join(get_config_dir(), 'smart_scheduler.json')
        self.scheduler = SmartScheduler(scheduler_path)
        self.scheduler.on_task_executed = self.handle_scheduled_task
        
        self.scheduler.on_task_executed = self.handle_scheduled_task
        
        # 밴드 예약 큐 초기화
        self.band_reservation_queue = []
        
        # 댓글 모니터링 모듈 (백그라운드)
        self.comment_monitor = None
        self.comment_monitor_active = False
        
        # 드라이브 자동 포스팅 및 파일 관리 시스템
        from modules.file_manager import FileManager
        self.file_manager = FileManager()
        self.file_manager.start_auto_cleanup(interval_hours=6) # 6시간마다 정리 실행
        
        self.drive_auto_post_system = None
        self._init_drive_auto_post()
        
        # 🔄 세션 유지 시스템 (30분 비활성 시 네이버 홈 방문)
        self.session_keep_alive_active = False
        self.session_keep_alive_thread = None
        self.last_activity_time = time.time()
        self.session_refresh_interval = 30 * 60  # 30분 (초 단위)
        
        if self.is_macos:
            self._start_caffeinate()

        # 지역 마케팅 매니저
        self.persona_manager = PersonaManager(self.base_dir)
        self.target_finder = TargetFinder()
        self.smart_reply = SmartReply(self.gpt_handler, self.persona_manager)
        self.history_manager = HistoryManager(os.path.join(self.base_dir, 'data', 'marketing_history.json'))
        self.comment_poster = None # will be init in main or when driver is ready, but logic uses self.driver directly usually or passthrough
        # Actually CommentPoster needs driver, which changes. We can init it on demand.


    def _initial_device_info_update(self):
        """앱 시작 시 백그라운드에서 디바이스 정보 및 사용 횟수 업데이트"""
        def update_task():
            try:
                # 설정 로드하여 시리얼 번호 확인
                config = self.serial_auth.load_config()
                serial_number = config.get("serial_number")
                
                if serial_number:
                    time.sleep(2) # 앱 초기화 안정화를 위해 잠시 대기
                    print(f"📡 [Startup] 디바이스 정보 업데이트 시도: {serial_number}")
                    success = self.serial_auth.update_device_info_and_usage(serial_number)
                    if success:
                        print("✅ [Startup] 디바이스 정보 서버 업데이트 완료")
                    else:
                        print("⚠️ [Startup] 디바이스 정보 업데이트 실패 (또는 불필요)")
            except Exception as e:
                print(f"❌ [Startup] 디바이스 정보 업데이트 중 오류: {e}")

        # UI 블로킹 방지를 위해 스레드로 실행
        threading.Thread(target=update_task, daemon=True).start()

    def _get_app_data_dir(self):
        """사용자 데이터 디렉토리 반환 (Delegates to utils.path_utils)"""
        return get_app_data_dir()

    def _get_time_based_task_type(self, target_time_str=None):
        """현재 시간(또는 예약 시간) 기반으로 task_type 자동 판별
        
        - morning: ~12시 (오전) → 날씨 중심
        - regular: 12~18시 (오후) → 뉴스/이슈 중심
        - closing: 18시~ (저녁) → 뉴스/이슈 중심
        """
        from datetime import datetime as dt_cls
        try:
            if target_time_str:
                hour = int(target_time_str.split(':')[0])
            else:
                hour = dt_cls.now().hour
            
            if hour < 12:
                return 'morning'
            elif hour < 18:
                return 'regular'
            else:
                return 'closing'
        except Exception:
            return 'regular'

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
        # 폴더 경로 설정의 경우 따옴표 자동 제거
        if isinstance(value, str) and 'folder' in key.lower():
            value = value.strip("'").strip('"').strip()
        
        # 변경사항 없으면 스킵 (on_change 과부하 방지)
        if self.settings.get(key) == value:
            return

        self.settings[key] = value
        self.save_settings()
        print(f"✅ 설정 저장됨 [Key: {key}, Value: {value}] -> app_settings.json")

    
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
    
    def _drive_generate_content(self, topic: str, folder_name: str, platform=None, **kwargs):
        """드라이브 자동 포스팅용 AI 글 생성 (유형 2)"""
        try:
            full_topic = f"[{folder_name}] {topic}"
            result = self.gpt_handler.generate_platform_content(
                full_topic,
                platform='drive_auto',  # 전용 플랫폼 타입
                task_type='regular'
            )
            if result and result.get('content'):
                # 🟢 밴드 파이프라인 관통시켜 유형 2 물리적 조립 수행
                from modules.pipelines.band_pipeline import BandPipeline
                gpt_tags = result.get('tags', [])
                ai_tags_str = ",".join(gpt_tags) if isinstance(gpt_tags, list) else str(gpt_tags)
                
                formatted_content, merged_tags = BandPipeline.process(
                    content=result['content'],
                    ai_tags=ai_tags_str,
                    app_data_dir=self._get_app_data_dir(),
                    mode='drive_auto', # 유형 2 명시
                    fallback_settings=self.settings,
                    folder_name=folder_name # 폴더명 전달
                )
                result['content'] = formatted_content
                result['tags'] = merged_tags
            return result
        except Exception as e:
            print(f"❌ AI 글 생성 오류: {e}")
            return None
    
    def _drive_post_to_band(self, content: str, image_paths: list, tags=None, **kwargs):
        """드라이브 자동 포스팅용 밴드 포스팅"""
        try:
            from naver_band_auto import NaverBandAutomation
            
            # 🔒 브라우저 락 - 동시 실행 방지
            self.browser_lock.acquire()
            self.is_browser_busy = True
            
            print("📤 [나폴라] 밴드 자동 포스팅 시작...")
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
        finally:
            self.is_browser_busy = False
            self.browser_lock.release()
            print("🔓 [나폴라] 밴드 자동 포스팅 대기열 해제")
    
    def _drive_on_success(self, folder_name: str, file_count: int):
        """드라이브 자동 포스팅 성공 콜백"""
        print(f"🎉 [{folder_name}] {file_count}개 사진 포스팅 성공!")
    
    def _drive_on_fail(self, folder_name: str, error: str):
        """드라이브 자동 포스팅 실패 콜백"""
        print(f"❌ [{folder_name}] 포스팅 실패: {error}")
    
    # --------------------------------------------------------------------------
    # 📂 DriveWatcher (구글 드라이브) 실시간 감지 연동 메소드 (Phase 2)
    # --------------------------------------------------------------------------
    
    def _toggle_blog_drive_watcher_ui(self):
        """블로그 드라이브 감시 UI 가시성 조절 (독립 섹션 - 항상 표시)"""
        if hasattr(self, 'blog_drive_settings_row'):
            self.blog_drive_settings_row.visible = True
            if self.blog_drive_settings_row.page:
                self.blog_drive_settings_row.update()

    def _toggle_cafe_drive_watcher_ui(self):
        """카페 드라이브 감시 UI 가시성 조절"""
        is_detect = self.cafe_image_mode_dropdown.value == "detect"
        if hasattr(self, 'cafe_drive_settings_row'):
            self.cafe_drive_settings_row.visible = is_detect
            if self.cafe_drive_settings_row.page:
                self.cafe_drive_settings_row.update()

    def _open_folder_picker_for(self, target_textfield: ft.TextField):
        """특정 텍스트필드를 위한 폴더 선택기 열기"""
        self.current_folder_picker_target = target_textfield
        # 기존 _open_folder_picker 로직을 활용하거나 직접 osascript 호출
        self._open_folder_picker(type('obj', (object,), {'control': type('obj', (object,), {'parent': target_textfield.parent})}))

    def _toggle_blog_drive_watcher(self, e):
        """블로그용 실시간 드라이브 감시 시작/중지"""
        folder_path = self.blog_drive_folder_path.value
        if not folder_path or not os.path.exists(folder_path):
            if self.page_ref:
                self.page_ref.snack_bar = ft.SnackBar(content=ft.Text("❌ 유효한 폴더 경로를 입력해주세요."), bgcolor=ft.Colors.RED)
                self.page_ref.snack_bar.open = True
                self.page_ref.update()
            return

        if not hasattr(self, 'blog_watcher') or not self.blog_watcher:
            from modules.drive_watcher import DriveWatcher
            self.blog_watcher = DriveWatcher(debounce_seconds=60)
            self.blog_watcher.set_callback(self._on_blog_drive_detected)

        if not self.blog_watcher.is_running:
            # 시작
            self.blog_watcher.handlers.clear() # 기존 핸들러 청소
            self.blog_watcher.add_folder(folder_path, "블로그 감시")
            if self.blog_watcher.start():
                self.blog_drive_watcher_status.value = "상태: 감시 중..."
                self.blog_drive_watcher_status.color = ft.Colors.GREEN_700
                self.blog_drive_watcher_btn.text = "감시 중지"
                self.blog_drive_watcher_btn.bgcolor = ft.Colors.RED_700
                self.blog_drive_watcher_btn.icon = ft.Icons.STOP
            else:
                if self.page_ref:
                    self.page_ref.snack_bar = ft.SnackBar(content=ft.Text("❌ 감시 시작 실패"), bgcolor=ft.Colors.RED)
                    self.page_ref.snack_bar.open = True
        else:
            # 중지
            self.blog_watcher.stop()
            self.blog_drive_watcher_status.value = "상태: 정지됨"
            self.blog_drive_watcher_status.color = ft.Colors.GREY_600
            self.blog_drive_watcher_btn.text = "실시간 감시 시작"
            self.blog_drive_watcher_btn.bgcolor = ft.Colors.GREEN_700
            self.blog_drive_watcher_btn.icon = ft.Icons.PLAY_ARROW
        
        if self.page_ref:
            self.page_ref.update()

    def _toggle_cafe_drive_watcher(self, e):
        """카페용 실시간 드라이브 감시 시작/중지"""
        folder_path = self.cafe_drive_folder_path.value
        if not folder_path or not os.path.exists(folder_path):
            if self.page_ref:
                self.page_ref.snack_bar = ft.SnackBar(content=ft.Text("❌ 유효한 폴더 경로를 입력해주세요."), bgcolor=ft.Colors.RED)
                self.page_ref.snack_bar.open = True
                self.page_ref.update()
            return

        if not hasattr(self, 'cafe_watcher') or not self.cafe_watcher:
            from modules.drive_watcher import DriveWatcher
            self.cafe_watcher = DriveWatcher(debounce_seconds=60)
            self.cafe_watcher.set_callback(self._on_cafe_drive_detected)

        if not self.cafe_watcher.is_running:
            # 시작
            self.cafe_watcher.handlers.clear()
            self.cafe_watcher.add_folder(folder_path, "카페 감시")
            if self.cafe_watcher.start():
                self.cafe_drive_watcher_status.value = "상태: 감시 중..."
                self.cafe_drive_watcher_status.color = ft.Colors.GREEN_700
                self.cafe_drive_watcher_btn.text = "감시 중지"
                self.cafe_drive_watcher_btn.bgcolor = ft.Colors.RED_700
                self.cafe_drive_watcher_btn.icon = ft.Icons.STOP
            else:
                if self.page_ref:
                    self.page_ref.snack_bar = ft.SnackBar(content=ft.Text("❌ 감시 시작 실패"), bgcolor=ft.Colors.RED)
                    self.page_ref.snack_bar.open = True
        else:
            # 중지
            self.cafe_watcher.stop()
            self.cafe_drive_watcher_status.value = "상태: 정지됨"
            self.cafe_drive_watcher_status.color = ft.Colors.GREY_600
            self.cafe_drive_watcher_btn.text = "실시간 감시 시작"
            self.cafe_drive_watcher_btn.bgcolor = ft.Colors.GREEN_700
            self.cafe_drive_watcher_btn.icon = ft.Icons.PLAY_ARROW
        
        if self.page_ref:
            self.page_ref.update()

    def _on_blog_drive_detected(self, folder_path, folder_name, files):
        """블로그 드라이브 감지 시 자동 포스팅 실행"""
        print(f"🔔 [DriveWatcher] 블로그 새 이미지 감지: {len(files)}개")
        
        # 1. 구글 시트 참조 및 주제 결합 (블로그 전용 URL 사용)
        sheet_url = self.settings.get('blog_sheet_url', '')
        sheet_content = ""
        if sheet_url:
            try:
                from modules.sheets_reader import GoogleSheetsReader
                reader = GoogleSheetsReader(sheet_url=sheet_url)
                # 블로그 감시 모드: 날짜 무관 가장 마지막 주제 가져오기
                sheet_content = reader.get_latest_content()
            except Exception as e:
                print(f"⚠️ 블로그 구글 시트 연동 오류: {e}")
                
        if sheet_content:
            topic = sheet_content
            print(f"📊 [구글 시트] 블로그 감시 모드 주제 반영: {topic[:30]}...")
        else:
            local_topic = self.select_sequential_topic('blog')
            topic = local_topic if local_topic else "양양 한국체대 라이온 일상"
            print(f"ℹ️ 시트 내용 없음, 로컬 주제 사용: {topic[:30]}...")
            
        # 2. 내용 생성
        print(f"🤖 [DriveWatcher] 주제 '{topic}'으로 내용 생성 중...")
        try:
            result = self.gpt_handler.generate_platform_content(topic, platform='blog')
            title = result.get('title', f"[{folder_name}] 일상 공유")
            content = result.get('content', '')
        except Exception as e:
            print(f"❌ GPT 내용 생성 실패: {e}")
            return
        
        # 3. 업로드 (별도 스레드)
        def auto_upload():
            from naver_blog_auto import NaverBlogAutomation
            try:
                # 🔒 브라우저 락
                self.browser_lock.acquire()
                self.is_browser_busy = True
                
                print(f"🚀 [DriveWatcher] 블로그 자동 업로드 시작: {title}")
                driver = self.get_or_create_driver()
                naver_id = self.settings.get('naver_id', '')
                
                # 인스턴스 생성 (감지된 폴더를 이미지 소스로 사용)
                blog_auto = NaverBlogAutomation(
                    auto_mode=True, 
                    image_insert_mode=self.settings.get('blog_image_position', 'random'),
                    custom_images_folder=folder_path,
                    naver_id=naver_id,
                    media_position=self.settings.get('blog_media_position', 'middle'),
                    media_order=self.settings.get('blog_media_order', 'image_first')
                )
                blog_auto.driver = driver
                
                # 이미지 핸들러 초기화 (감지된 폴더의 이미지들을 로드함)
                blog_auto.setup_image_inserter()
                
                # 🟢 오리지널 단순 결합 복원
                # 💡 [모바일 가독성 줄바꿈 적용]
                raw_content = format_content_for_mobile(content)
                
                # 1. 첫문장(머리말) 결합
                blog_intro = self.settings.get('blog_first_sentence', '').strip()
                if blog_intro:
                    processed_content = f"{blog_intro}\n{raw_content}"
                else:
                    processed_content = raw_content
                
                # 2. 슬로건 결합
                blog_slogan = self.settings.get('blog_slogan', '').strip()
                if blog_slogan and blog_slogan not in processed_content:
                    processed_content = f"{processed_content}\n\n{blog_slogan}"
                
                # 3. 태그 병합 (고정 15개 + AI 15개 = 30개 규칙)
                ai_tags = result.get('tags', [])
                if isinstance(ai_tags, str):
                    ai_tags = [t.strip() for t in ai_tags.split(',') if t.strip()]
                    
                user_tags_str = self.settings.get('blog_tags', '')
                user_tags = [tag.strip() for tag in user_tags_str.split(',') if tag.strip()] if user_tags_str else []
                
                seen_tags = set()
                merged_tags = []
                for t in user_tags[:15]:
                    if t and t not in seen_tags:
                        merged_tags.append(t)
                        seen_tags.add(t)
                for t in ai_tags[:15]:
                    if t and t not in seen_tags and len(merged_tags) < 30:
                        merged_tags.append(t)
                        seen_tags.add(t)
                
                # 포스팅 실행 (write_post 사용)
                success = blog_auto.write_post(
                    title=title,
                    content=processed_content,
                    tags=merged_tags
                )
                
                if success:
                    print(f"✅ [DriveWatcher] 블로그 자동 포스팅 완료!")
                    # 처리된 파일 중앙 백업 폴더로 이동 (FileManager 사용)
                    self.file_manager.move_to_backup(files, folder_name)
                else:
                    print(f"❌ [DriveWatcher] 블로그 자동 포스팅 실패")
            except Exception as e:
                print(f"❌ [DriveWatcher] 자동 업로드 중 치명적 오류: {e}")
                traceback.print_exc()
            finally:
                self.is_browser_busy = False
                self.browser_lock.release()
                
        import threading
        threading.Thread(target=auto_upload, daemon=True).start()

    def _on_cafe_drive_detected(self, folder_path, folder_name, files):
        """카페 드라이브 감지 시 자동 포스팅 실행"""
        print(f"🔔 [DriveWatcher] 카페 새 이미지 감지: {len(files)}개")
        
        # 1. 구글 시트 참조 및 주제 결합 (카페 전용 URL 사용)
        sheet_url = self.settings.get('cafe_sheet_url', '')
        sheet_content = ""
        if sheet_url:
            try:
                from modules.sheets_reader import GoogleSheetsReader
                reader = GoogleSheetsReader(sheet_url=sheet_url)
                # 카페 감시 모드: 날짜 무관 가장 마지막 주제 가져오기 (사용자 요청 반영)
                sheet_content = reader.get_latest_content()
            except Exception as e:
                print(f"⚠️ 카페 구글 시트 연동 오류: {e}")
                
        if sheet_content:
            topic = sheet_content
            print(f"📊 [구글 시트] 카페 감시 모드 주제 반영: {topic[:30]}...")
        else:
            local_topic = self.select_sequential_topic('cafe')
            topic = local_topic if local_topic else "카페 소식"
            print(f"ℹ️ 시트 내용 없음, 로컬 주제 사용: {topic[:30]}...")
        
        # 2. 내용 생성
        print(f"🤖 [DriveWatcher] 카페 주제 '{topic}'으로 내용 생성 중...")
        try:
            result = self.gpt_handler.generate_platform_content(topic, platform='cafe')
            title = result.get('title', f"[{folder_name}] 새로운 소식")
            content = result.get('content', '')
        except Exception as e:
            print(f"❌ 카페 GPT 내용 생성 실패: {e}")
            return
        
        # 3. 업로드 (별도 스레드)
        def auto_upload():
            from naver_cafe_auto import NaverCafeAutomation
            try:
                self.browser_lock.acquire()
                self.is_browser_busy = True
                
                print(f"🚀 [DriveWatcher] 카페 자동 업로드 시작: {title}")
                driver = self.get_or_create_driver()
                cafe_auto = NaverCafeAutomation(driver)
                
                success = cafe_auto.post_to_cafe(
                    cafe_url=self.settings.get('cafe_url', ''),
                    menu_id=self.settings.get('cafe_menu_id', ''),
                    title=title,
                    content=content,
                    image_paths=files
                )
                
                if success:
                    print(f"✅ [DriveWatcher] 카페 자동 포스팅 완료!")
                    # 처리된 파일 중앙 백업 폴더로 이동 (FileManager 사용)
                    self.file_manager.move_to_backup(files, folder_name)
                else:
                    print(f"❌ [DriveWatcher] 카페 자동 포스팅 실패")
            except Exception as e:
                print(f"❌ [DriveWatcher] 카페 자동 업로드 중 오류: {e}")
                traceback.print_exc()
            finally:
                self.is_browser_busy = False
                self.browser_lock.release()
                
        import threading
        threading.Thread(target=auto_upload, daemon=True).start()


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
        sheet_url = self.settings.get('band_sheet_url', '')
        print(f"📊 밴드 스프레드시트 URL 설정: '{sheet_url[:60]}...' " if sheet_url else "📊 밴드 스프레드시트 URL: 없음")
        
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
            
            # --- 탭 간 동기화 로직 ---
            if hasattr(self, 'user_blog_drive_folder') and (text_field == self.user_blog_drive_folder or text_field == self.blog_drive_folder_path):
                self.user_blog_drive_folder.value = normalized_path
                self.blog_drive_folder_path.value = normalized_path
                self.user_blog_drive_folder.update()
                self.blog_drive_folder_path.update()
                self._save_setting('blog_drive_folder', normalized_path)
            elif hasattr(self, 'user_cafe_drive_folder') and (text_field == self.user_cafe_drive_folder or text_field == self.cafe_drive_folder_path):
                self.user_cafe_drive_folder.value = normalized_path
                self.cafe_drive_folder_path.value = normalized_path
                self.user_cafe_drive_folder.update()
                self.cafe_drive_folder_path.update()
                self._save_setting('cafe_drive_folder', normalized_path)
            else:
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
                        
                        # UI 및 탭 간 동기화 실행 (로직 재사용)
                        self._on_drive_folder_selected(type('obj', (object,), {'path': normalized_path}), text_field)
                        
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

    def _on_smart_image_scan_click(self, e):
        """로컬 이미지 폴더를 스캔하고 AI 키워드를 자동 학습시킵니다."""
        try:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("🔄 로컬 이미지 폴더 스캔 및 AI 키워드 스마트 학습 진행 중... (약 10~20초 소요)"),
                bgcolor=ft.Colors.BLUE_700,
                duration=4000
            )
            self.page.snack_bar.open = True
            self.page.update()
            
            def run_scan():
                try:
                    result = self.gpt_handler.scan_and_learn_image_folders(base_dir=self.base_dir, force_rescan=True)
                    count = len(result)
                    
                    def update_ui():
                        self.page.snack_bar = ft.SnackBar(
                            content=ft.Text(f"🎉 성공! 총 {count}개의 이미지 폴더 스캔 및 스마트 AI 학습이 완벽히 완료되었습니다!"),
                            bgcolor=ft.Colors.GREEN_700,
                            duration=5000
                        )
                        self.page.snack_bar.open = True
                        self.page.update()
                        
                    self.page.run_task(update_ui)
                except Exception as err:
                    print(f"❌ 스마트 이미지 폴더 스캔 오류: {err}")
                    def show_error():
                        self.page.snack_bar = ft.SnackBar(
                            content=ft.Text(f"❌ 스마트 폴더 스캔 중 실패: {err}"),
                            bgcolor=ft.Colors.RED,
                            duration=4000
                        )
                        self.page.snack_bar.open = True
                        self.page.update()
                    self.page.run_task(show_error)
            
            threading.Thread(target=run_scan, daemon=True).start()
        except Exception as err:
            print(f"❌ 폴더 스캔 핸들러 오류: {err}")

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
            dir_path = os.path.join(self._get_app_data_dir(), directory)
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"📁 디렉토리 확인/생성: {dir_path}")
            except Exception as e:
                print(f"❌ 디렉토리 생성 실패 ({directory}): {str(e)}")
        
        # 디렉토리 내용 확인 (디버깅용)
        try:
            contents = os.listdir(self._get_app_data_dir())
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
                gone, still_alive = psutil.wait_procs(children, timeout=10)
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
                    cookies_file = os.path.join(get_config_dir(), 'naver_cookies.json')
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
        cookies_path = os.path.join(get_config_dir(), 'naver_cookies.json')
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
                    f"현재 시간: {current_time}\n운영 시간: {start_time} ~ {end_time}\n\n운영 시간 내에 다시 시도하거나 '시간 설정' 탭에서 운영 시간을 조정하세요.",
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
            # 🆕 글로벌 설정 경로 사용
            timer_file = os.path.join(self._get_app_data_dir(), 'config', 'timer_settings.json')
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
                                
                                # UI에 다이얼로그 알림 표시 (안전하게 실행)
                                if self.page_ref:
                                    try:
                                        async def show_update_dialog():
                                            try:
                                                self.show_dialog(
                                                    self.page_ref,
                                                    "🔄 설정 업데이트",
                                                    f"타이머 설정이 변경되어 업데이트되었습니다!\n\n📊 오늘의 포스팅 수: {self.daily_post_count}회\n⏰ 새로운 다음 포스팅 시간: {next_time_str}\n\n새로운 설정으로 타이머가 계속 실행됩니다.",
                                                    ft.Colors.BLUE
                                                )
                                            except Exception as dialog_e:
                                                print(f"❌ 설정 업데이트 다이얼로그 표시 실패: {dialog_e}")
                                        
                                        # Flet UI 스레드에서 실행 (Windows 크래시 방지)
                                        self.page_ref.run_task(show_update_dialog)
                                        
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
                                # UI 스레드에서 안전하게 실행 (Windows 크래시 방지)
                                async def show_operating_time_dialog():
                                    try:
                                        self.show_dialog(
                                            self.page_ref,
                                            "⏰ 운영 시간 대기 중",
                                            f"현재는 운영 시간이 아닙니다.\n\n현재 시간: {current_time}\n운영 시간: {start_time} ~ {end_time}\n\n운영 시간까지 대기합니다.",
                                            ft.Colors.BLUE
                                        )
                                    except Exception as dialog_e:
                                        print(f"❌ 운영 시간 다이얼로그 표시 실패: {dialog_e}")
                                
                                # Flet 태스크로 실행
                                self.page_ref.run_task(show_operating_time_dialog)
                                
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
                                # UI 스레드에서 안전하게 실행 (Windows 크래시 방지)
                                async def show_limit_dialog():
                                    try:
                                        self.show_dialog(
                                            self.page_ref,
                                            "📊 일일 제한 도달",
                                            f"오늘의 포스팅 제한에 도달했습니다.\n\n오늘 포스팅: {self.daily_post_count}회\n일일 제한: {max_posts}회\n\n내일까지 대기하거나 설정을 변경하세요.",
                                            ft.Colors.ORANGE
                                        )
                                    except Exception as dialog_e:
                                        print(f"❌ 일일 제한 다이얼로그 표시 실패: {dialog_e}")
                                
                                # Flet 태스크로 실행
                                self.page_ref.run_task(show_limit_dialog)
                                
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
                        # 🟢 시간대 자동 판별: 예약 시간 기준
                        blog_task_type = self._get_time_based_task_type(res_time)
                        print(f"    📊 시간대 판별: {res_time} → {blog_task_type}")
                        result = self.gpt_handler.generate_platform_content(topic, platform='blog', task_type=blog_task_type, target_time=res_time)
                        
                        if not result or not result.get('content'):
                            print(f"    ❌ 내용 생성 실패 ({res_time})")
                            continue
                        
                        # 2. 기존 브라우저 사용 또는 생성
                        driver = self.get_or_create_driver()
                        
                        # 3. NaverBlogAutomation 사용하여 포스트 작성 (단일 포스팅과 동일하게)
                        from naver_blog_auto import NaverBlogAutomation
                        from naver_blog_post_finisher import NaverBlogPostFinisher
                        
                        # --- Phase 2: 이미지 삽입 모드 처리 (스케줄러 전용 - 드라이브 감지와 독립) ---
                        image_mode = self.blog_image_mode_dropdown.value
                        custom_images_folder = None
                        images_available = False
                        
                        if image_mode == "off":
                            print("    🚫 블로그 예약 이미지 모드: 사용 안함")
                        else: # "auto" or "manual" (예약 작업 시 manual은 auto로 처리)
                            print(f"    🤖 블로그 예약 이미지 모드: {image_mode} (자동 선정)")
                            try:
                                folder_path = self.get_smart_image_folder(topic)
                                if folder_path and os.path.exists(folder_path):
                                    custom_images_folder = folder_path
                                    images_available = True
                            except: pass

                        # 자동화 인스턴스 생성
                        blog_auto = NaverBlogAutomation(
                            auto_mode=images_available,
                            image_insert_mode=self.settings.get('blog_image_position', 'random'),
                            use_stickers=False,
                            custom_images_folder=custom_images_folder,
                            naver_id=self.settings.get('naver_id', ''),
                            media_position=self.settings.get('blog_media_position', 'middle'),
                            media_order=self.settings.get('blog_media_order', 'image_first')
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
                            blog_auto.image_inserter.media_position = self.settings.get('blog_media_position', 'middle')
                            blog_auto.image_inserter.media_order = self.settings.get('blog_media_order', 'image_first')
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
                        
                        # 🟢 오리지널 단순 결합 복원 (파이프라인 제거)
                        # 💡 [모바일 가독성 줄바꿈 적용]
                        raw_content = format_content_for_mobile(result.get('content', ''))
                        
                        # 1. 첫문장(머리말) 결합
                        blog_intro = self.settings.get('blog_first_sentence', '').strip()
                        if blog_intro:
                            processed_content = f"{blog_intro}\n{raw_content}"
                        else:
                            processed_content = raw_content
                        
                        # 2. 슬로건 결합
                        blog_slogan = self.settings.get('blog_slogan', '').strip()
                        if blog_slogan and blog_slogan not in processed_content:
                            processed_content = f"{processed_content}\n\n{blog_slogan}"
                        
                        # 3. 태그 병합 (고정 15개 + AI 15개 = 30개 규칙)
                        ai_tags = result.get('tags', [])
                        if isinstance(ai_tags, str):
                            ai_tags = [t.strip() for t in ai_tags.split(',') if t.strip()]
                            
                        user_tags_str = self.settings.get('blog_tags', '')
                        user_tags = [tag.strip() for tag in user_tags_str.split(',') if tag.strip()] if user_tags_str else []
                        
                        seen_tags = set()
                        merged_tags = []
                        
                        # 고정 태그 최대 15개 추가
                        for tag in user_tags[:15]:
                            if tag not in seen_tags:
                                seen_tags.add(tag)
                                merged_tags.append(tag)
                                
                        # AI 태그 최대 15개 추가
                        for tag in ai_tags:
                            if len(merged_tags) >= 30:
                                break
                            if tag not in seen_tags:
                                seen_tags.add(tag)
                                merged_tags.append(tag)
                                
                        content = processed_content
                        tags = merged_tags
                        
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
                            publish_success = finisher.click_final_publish_button(is_reservation=True)
                            
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
                        # 🟢 시간대 자동 판별: 예약 시간 기준
                        blog_task_type = self._get_time_based_task_type(reservation_time)
                        print(f"    📊 시간대 판별: {reservation_time} → {blog_task_type}")
                        result = self.gpt_handler.generate_platform_content(topic, platform='blog', task_type=blog_task_type, target_time=reservation_time)
                        
                        if not result or not result.get('content'):
                            print(f"    ❌ 내용 생성 실패")
                            task.last_status = 'failed'
                            return
                        
                        driver = self.get_or_create_driver()
                        
                        # 이미지 폴더 선택
                        custom_images_folder = None
                        images_available = False
                        try:
                            folder_path = self.get_smart_image_folder(topic)
                            if folder_path and os.path.exists(folder_path):
                                valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
                                files = [f for f in os.listdir(folder_path) if os.path.splitext(f)[1].lower() in valid_exts]
                                if files:
                                    custom_images_folder = folder_path
                                    images_available = True
                                    print(f"    🖼️ 이미지 폴더: {folder_path}")
                        except Exception as img_err:
                            print(f"    ⚠️ 이미지 폴더 오류: {img_err}")
                        
                        # 🆕 네이버 ID 설정 가져오기
                        naver_id = self.settings.get('naver_id', '')

                        # 블로그 자동화 객체 생성
                        blog_auto = NaverBlogAutomation(
                            auto_mode=images_available,
                            image_insert_mode=self.settings.get('blog_image_position', 'random'),
                            use_stickers=False,
                            custom_images_folder=custom_images_folder,
                            naver_id=naver_id,
                            media_position=self.settings.get('blog_media_position', 'middle'),
                            media_order=self.settings.get('blog_media_order', 'image_first')
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
                            blog_auto.image_inserter.media_position = self.settings.get('blog_media_position', 'middle')
                            blog_auto.image_inserter.media_order = self.settings.get('blog_media_order', 'image_first')
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
                        
                        # 🟢 오리지널 단순 결합 복원 (파이프라인 제거)
                        # 💡 [모바일 가독성 줄바꿈 적용]
                        raw_content = format_content_for_mobile(result.get('content', ''))
                        
                        # 1. 첫문장(머리말) 결합
                        blog_intro = self.settings.get('blog_first_sentence', '').strip()
                        if blog_intro:
                            processed_content = f"{blog_intro}\n{raw_content}"
                        else:
                            processed_content = raw_content
                        
                        # 2. 슬로건 결합
                        blog_slogan = self.settings.get('blog_slogan', '').strip()
                        if blog_slogan and blog_slogan not in processed_content:
                            processed_content = f"{processed_content}\n\n{blog_slogan}"
                        
                        # 3. 태그 병합 (고정 15개 + AI 15개 = 30개 규칙)
                        ai_tags = result.get('tags', [])
                        if isinstance(ai_tags, str):
                            ai_tags = [t.strip() for t in ai_tags.split(',') if t.strip()]
                            
                        user_tags_str = self.settings.get('blog_tags', '')
                        user_tags = [tag.strip() for tag in user_tags_str.split(',') if tag.strip()] if user_tags_str else []
                        
                        seen_tags = set()
                        merged_tags = []
                        
                        # 고정 태그 최대 15개 추가
                        for tag in user_tags[:15]:
                            if tag not in seen_tags:
                                seen_tags.add(tag)
                                merged_tags.append(tag)
                                
                        # AI 태그 최대 15개 추가
                        for tag in ai_tags:
                            if len(merged_tags) >= 30:
                                break
                            if tag not in seen_tags:
                                seen_tags.add(tag)
                                merged_tags.append(tag)
                                
                        content = processed_content
                        tags = merged_tags
                        
                        # 글 작성 (write_post가 푸터+태그 처리)
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
                            publish_success = finisher.click_final_publish_button(is_reservation=True)
                            
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
                 band_url = self.settings.get('band_url', '') or task.data.get('band_url', '')
                 
                 print(f"[Step 1] [BandScheduler] 밴드 예약 일괄 등록 시작 (상태: 시도) - 총 {len(times)}건 ({', '.join(times)})")
                 
                 if not times:
                     print("[Step 1] [BandScheduler] 밴드 예약 일괄 등록 시작 (상태: 실패) - 예약 시간이 없습니다.")
                     return
                 
                 band_auto = NaverBandAutomation(self.get_or_create_driver())
                 print("[Step 2] [BandScheduler] 밴드 자동화 드라이버 및 인스턴스 준비 (상태: 성공)")
                 
                 success_cnt = 0
                 
                 # 🟢 뉴스 중복 방지 (방안 A): 뉴스 6건 사전 검색 후 분배
                 news_type_count = sum(1 for t in times if self._get_time_based_task_type(t) in ('regular', 'closing'))
                 all_news = None
                 news_items = []
                 if news_type_count >= 2:
                     try:
                         all_news = self.gpt_handler._get_trending_topics(count=6)
                         if all_news:
                             news_items = all_news.split('\n')
                             print(f"  📰 뉴스 {len(news_items)}건 사전 검색 완료 (분배 모드)")
                     except Exception as e:
                         print(f"  ⚠️ 뉴스 사전 검색 실패, 개별 검색 모드: {e}")
                 
                 news_distribution_index = 0  # 뉴스 분배 인덱스
                 previous_news_summary = ""   # 이전 포스팅 뉴스 (방안 C)
                 
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
                     
                     user_type = types[i] if i < len(types) else 'regular'
                     # 🟢 예약 시간 기준 자동 판별 (사용자 선택 무시 → 시간 기준 강제)
                     task_type = self._get_time_based_task_type(res_time)
                     if user_type != task_type:
                         print(f"  🔄 유형 자동 보정: '{user_type}' → '{task_type}' (예약 시간 {res_time} 기준)")
                     print(f"  👉 예약 작업 {i+1}/{len(times)}: {res_time} (유형: {task_type}) 처리 중...")
                     
                     # 🟢 뉴스 분배 (방안 A+C): regular/closing 타입에 뉴스 3건씩 분배
                     news_pool = None
                     if task_type in ('regular', 'closing') and news_items:
                         start_idx = news_distribution_index * 3
                         end_idx = start_idx + 3
                         news_subset = news_items[start_idx:end_idx]
                         if news_subset:
                             news_pool = '\n'.join(news_subset)
                             print(f"    📰 뉴스 분배: {start_idx+1}~{end_idx}번 ({len(news_subset)}건)")
                             news_distribution_index += 1
                     
                     # 주제 및 내용 생성 (유형에 따라 다른 스타일)
                     topic = self.select_sequential_topic('band') or "체육관 일상"
                     print(f"[Step 3] [BandScheduler] ({res_time}) AI 글 내용 및 날씨 연동 생성 시작 (상태: 시도) - 주제: {topic}")
                     
                     # 예약 시간에 따른 delta_days 계산
                     delta_days = 0
                     if res_time:
                         try:
                             from datetime import datetime
                             now = datetime.now()
                             h, m = map(int, res_time.split(':'))
                             if (h, m) < (now.hour, now.minute):
                                 delta_days = 1
                             else:
                                 delta_days = 0
                         except Exception as ex:
                             print(f"⚠️ [delta_days 계산 오류]: {ex}")
                             delta_days = 0

                     result = self.gpt_handler.generate_platform_content(
                         topic, platform='band', task_type=task_type, target_time=res_time,
                         news_pool=news_pool, previous_news=previous_news_summary, delta_days=delta_days
                     )
                     
                     # 🟢 방안 C: 이전 뉴스 기록 (다음 포스팅에서 중복 방지)
                     if task_type in ('regular', 'closing') and news_pool:
                         previous_news_summary = news_pool
                     
                     if not result or not result.get('content'):
                         print(f"[Step 3] [BandScheduler] ({res_time}) AI 글 내용 생성 실패 (상태: 실패)")
                         continue
                     print(f"[Step 3] [BandScheduler] ({res_time}) AI 글 내용 생성 완료 (상태: 성공) - 모델: {result.get('model', '-')}")
                         
                     # 🟢 밴드 파이프라인 관통시켜 유형 1 물리적 조립 수행 (모바일 가독성 최적화)
                     print(f"[Step 4] [BandScheduler] ({res_time}) 밴드 파이프라인 관통 조립 시작 (상태: 시도)")
                     from modules.pipelines.band_pipeline import BandPipeline
                     gpt_tags = result.get('tags', [])
                     ai_tags_str = ",".join(gpt_tags) if isinstance(gpt_tags, list) else str(gpt_tags)
                     
                     formatted_content, merged_tags = BandPipeline.process(
                         content=result['content'],
                         ai_tags=ai_tags_str,
                         app_data_dir=self._get_app_data_dir(),
                         mode='band', # 유형 1
                         fallback_settings=self.settings
                     )
                     print(f"[Step 4] [BandScheduler] ({res_time}) 밴드 파이프라인 관통 조립 완료 (상태: 성공)")
                         
                     # 이미지 준비 (설정에 따름)
                     images = []
                     if self.settings.get('band_auto_image', self.settings.get('auto_image', True)):
                        images = self.get_images_to_upload(platform='band')

                     # 예약 포스팅 실행 (reservation_time 전달)
                     print(f"[Step 5] [BandScheduler] ({res_time}) 밴드 예약 등록 업로드 시작 (상태: 시도)")
                     res_success = band_auto.post_to_band(
                         band_url, 
                         formatted_content, 
                         image_paths=images, 
                         reservation_time=res_time
                     )
                     
                     if res_success:
                         success_cnt += 1
                         print(f"[Step 5] [BandScheduler] ({res_time}) 밴드 예약 등록 완료 (상태: 성공)")
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
                print(f"[Step 1] [BandScheduler] 밴드 단일 예약 포스팅 시작 (상태: 시도) - 예약: {task.data.get('reservation_time', '즉시')}")
                band_auto = NaverBandAutomation(self.get_or_create_driver())
                band_url = self.settings.get('band_url', '') or task.data.get('band_url', '')
                print("[Step 2] [BandScheduler] 밴드 자동화 드라이버 및 인스턴스 준비 (상태: 성공)")
                
                # 예약 시간 확인
                reservation_time = task.data.get('reservation_time')
                
                # 예약 시간에 따른 delta_days 계산
                delta_days = 0
                if reservation_time:
                    try:
                        from datetime import datetime
                        now = datetime.now()
                        h, m = map(int, reservation_time.split(':'))
                        if (h, m) < (now.hour, now.minute):
                            delta_days = 1
                        else:
                            delta_days = 0
                    except Exception as ex:
                        print(f"⚠️ [delta_days 계산 오류]: {ex}")
                        delta_days = 0

                # 내용 생성
                topic = self.select_sequential_topic('band') or "체육관 소개 및 일상"
                print(f"[Step 3] [BandScheduler] ({reservation_time or '즉시'}) AI 글 내용 및 날씨 연동 생성 시작 (상태: 시도) - 주제: {topic}")
                result = self.gpt_handler.generate_platform_content(topic, platform='band', task_type=task.task_type, target_time=reservation_time, delta_days=delta_days)
                
                if not result or not result.get('content'):
                    print("[Step 3] [BandScheduler] AI 글 내용 생성 실패 (상태: 실패)")
                    self.add_model_usage_log(topic=topic, model="-", status="실패", reason="내용 생성 실패", target="밴드")
                    return False
                print(f"[Step 3] [BandScheduler] AI 글 내용 생성 완료 (상태: 성공) - 모델: {result.get('model', '-')}")
                
                # 🟢 밴드 파이프라인 관통시켜 유형 1 물리적 조립 수행 (모바일 가독성 최적화)
                print("[Step 4] [BandScheduler] 밴드 파이프라인 관통 조립 시작 (상태: 시도)")
                from modules.pipelines.band_pipeline import BandPipeline
                gpt_tags = result.get('tags', [])
                ai_tags_str = ",".join(gpt_tags) if isinstance(gpt_tags, list) else str(gpt_tags)
                
                formatted_content, merged_tags = BandPipeline.process(
                    content=result['content'],
                    ai_tags=ai_tags_str,
                    app_data_dir=self._get_app_data_dir(),
                    mode='band', # 유형 1
                    fallback_settings=self.settings
                )
                print("[Step 4] [BandScheduler] 밴드 파이프라인 관통 조립 완료 (상태: 성공)")
                
                # 이미지 준비
                images = []
                # 밴드 전용 이미지 설정 사용 (없으면 기본값 True)
                if self.settings.get('band_auto_image', self.settings.get('auto_image', True)):
                    images = self.get_images_to_upload(platform='band')
                    
                print(f"[Step 5] [BandScheduler] 밴드 단일 예약 업로드 시작 (상태: 시도) - 예약: {reservation_time or '즉시'}")
                success = band_auto.post_to_band(
                    band_url, 
                    formatted_content, 
                    image_paths=images,
                    reservation_time=reservation_time
                )
                
                if success:
                    print(f"[Step 5] [BandScheduler] 밴드 단일 예약 업로드 완료 (상태: 성공)")
                else:
                    print(f"[Step 5] [BandScheduler] 밴드 단일 예약 업로드 실패 (상태: 실패)")
                
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
                # 🟢 카페: 현재 시간 기준 시간대 자동 판별 (예약 없음)
                cafe_task_type = self._get_time_based_task_type()
                print(f"🤖 [카페] '{topic}' 주제로 내용 생성 중... (시간대: {cafe_task_type})")
                result = self.gpt_handler.generate_platform_content(topic, platform='cafe', task_type=cafe_task_type)
                
                if not result or not result.get('content'):
                    print("❌ [카페] AI 내용 생성에 실패했습니다.")
                    self.add_model_usage_log(topic=topic, model="-", status="실패", reason="내용 생성 실패", target="카페")
                    return False

                # --- Phase 2: 이미지 삽입 모드 처리 ---
                image_mode = self.cafe_image_mode_dropdown.value
                images = []
                
                if image_mode == "off":
                    print("🚫 카페 예약 이미지 삽입 모드: 사용 안함")
                elif image_mode == "detect":
                    print("🔍 카페 예약 이미지 삽입 모드: 드라이브 감지 경로 사용")
                    folder_path = self.cafe_drive_folder_path.value
                    if folder_path and os.path.exists(folder_path):
                        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
                        images = [
                            os.path.join(folder_path, f)
                            for f in os.listdir(folder_path)
                            if os.path.splitext(f)[1].lower() in valid_exts and not f.startswith('.')
                        ]
                else: # "auto" or "manual"
                    print(f"🤖 카페 예약 이미지 삽입 모드: {image_mode}")
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
                                base_dir=self.base_dir,
                                instruction=self.settings.get('reply_instruction')
                            )
                            limit_count = int(task.data.get('limit', task.data.get('reply_count', 30))) if task.data else 30
                            success = band_reply.process_band_comments(band_url=band_url, use_ai=True, limit=limit_count)
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
                    limit_val = int(task.data.get('limit', 10)) if task.data else 10
                    count = reply_bot.process_all_unanswered_comments(use_ai=True, limit=limit_val)
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
                            base_dir=self.base_dir,
                            instruction=self.settings.get('reply_instruction')
                        )
                        limit_count = int(task.data.get('limit', task.data.get('reply_count', 30))) if task.data else 30
                        success = band_reply.process_band_comments(band_url=band_url, use_ai=True, limit=limit_count)
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
        
        # 새 드라이버 설정 (Standard WebDriverManager)
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.options import Options

        try:
            options = Options()
            if getattr(self, 'is_headless', False):
                options.add_argument('--headless=new')
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            # 🆕 윈도우 세션 유지를 위해 고정된 프로필 사용 (ManualSessionHelper와 동일 경로)
            user_data_dir = os.path.join(get_data_dir(), "naver_blog_automation_profile")
            options.add_argument(f"--user-data-dir={user_data_dir}")
            
            # Use ChromeDriverManager to install/manage driver
            service = Service(ChromeDriverManager().install())
            self.browser_driver = webdriver.Chrome(service=service, options=options)
            return self.browser_driver
        except Exception as e:
            print(f"Driver Creation Failed: {e}")
            return None

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
            
    def get_smart_image_folder(self, title, platform='blog'):
        """주제(title)를 기반으로 스마트 이미지 폴더 매칭을 수행합니다.
           매칭되는 폴더가 없거나 이미지가 없는 경우, get_next_image_folder() 로 폴백합니다."""
        if not title:
            return self.get_next_image_folder(platform)
            
        try:
            from folder_manager import ImageFolderManager
            # folder_manager는 self.base_dir 기준으로 초기화
            folder_manager = ImageFolderManager(base_dir=self.base_dir)
            
            # 1. 스마트 이미지 매칭 수행
            matched_folder_name = folder_manager.find_matching_folder(text=title, title=title)
            
            if matched_folder_name:
                folder_path = folder_manager.get_folder_path(matched_folder_name)
                # 매칭된 폴더가 존재하고 실제 이미지를 가지고 있는지 확인
                if folder_path and os.path.exists(folder_path) and folder_manager._has_images(folder_path):
                    print(f"🎯 [Smart Matching SUCCESS] 주제 '{title}' -> 매칭 폴더: '{matched_folder_name}'")
                    return folder_path
            
            print(f"⚠️ [Smart Matching FAIL] 주제 '{title}' 에 적합한 폴더를 찾지 못했거나 폴더가 비어 있습니다. 순차 폴더 순환으로 전환합니다.")
        except Exception as e:
            print(f"⚠️ 스마트 이미지 매칭 중 오류 발생: {e}")
            
        return self.get_next_image_folder(platform)
            
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
            # 🆕 글로벌 설정 경로 사용
            user_settings_path = os.path.join(self._get_app_data_dir(), 'config', 'user_settings.txt')
            if os.path.exists(user_settings_path):
                with open(user_settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    
                    # --- 로컬 주제 목록 ---
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

    def start_periodic_validation(self):
        """24시간 주기 시리얼 재검증 및 사용 정보 업데이트"""
        def periodic_task():
            while True:
                try:
                    # 24시간 대기 (86400초)
                    time.sleep(86400)
                    
                    print("⏰ 주기적 시리얼 검증 시작 (24시간 경과)")
                    
                    config = self.serial_auth.load_config()
                    serial_number = config.get("serial_number")
                    
                    if serial_number:
                        # 정보 업데이트 및 검증
                        self.serial_auth.update_device_info_and_usage(serial_number)
                        
                        valid, message, _ = self.serial_auth.check_serial(serial_number)
                        if not valid:
                            print(f"🚨 시리얼 검증 실패 (만료/블랙리스트): {message}")
                            print("⛔ 보안 정책에 의해 프로그램을 종료합니다.")
                            
                            # 시리얼 정보 삭제 (재실행 시 재인증 유도)
                            try:
                                config["serial_number"] = ""
                                config["last_validation"] = ""
                                self.serial_auth.save_config(config)
                                print("🗑️ 시리얼 정보가 초기화되었습니다.")
                            except Exception as e:
                                print(f"⚠️ 설정 초기화 중 오류 (무시됨): {e}")
                            
                            # 알림 시도 (UI 스레드가 아닐 수 있어 안전장치 필요)
                            try:
                                if self.page:
                                    self.page.snack_bar = ft.SnackBar(
                                        content=ft.Text(f"⛔ 인증 만료/취소됨: 프로그램을 종료합니다."),
                                        bgcolor=ft.Colors.RED_900,
                                        duration=3000
                                    )
                                    self.page.snack_bar.open = True
                                    self.page.update()
                                    time.sleep(3) # 메시지 볼 시간 제공
                            except:
                                pass
                                
                            # 강제 종료
                            print("👋 프로그램 종료...")
                            os._exit(1)
                        else:
                            print("✅ 주기적 시리얼 검증 성공")
                    
                except Exception as e:
                    print(f"❌ 주기적 검증 오류: {e}")
                    time.sleep(60) # 오류 발생 시 1분 후 재시도
        
        # 데몬 스레드로 실행
        threading.Thread(target=periodic_task, daemon=True).start()

    def _create_reply_manager_tab(self):
        """댓글 답글(상담) 관리 탭 UI 생성"""
        
        # UI Elements
        self.reply_notifications_list = ft.Column(scroll=ft.ScrollMode.AUTO, height=500)
        
        fetch_btn = ft.ElevatedButton(
            "🔔 내 소식(답글) 가져오기",
            icon=ft.Icons.NOTIFICATIONS,
            bgcolor=ft.Colors.INDIGO_600,
            color=ft.Colors.WHITE,
            on_click=self._on_fetch_notifications_click
        )
        
        info_text = ft.Text(
            "💡 내 블로그 '내 소식'에서 '답글' 알림을 가져와, 문의성 댓글을 식별하고 대응합니다.",
            size=12, color=ft.Colors.GREY_700
        )
        
        content = ft.Column([
            ft.Container(
                content=ft.Column([
                    ft.Row([ft.Text("📢 답글/문의 관리", size=20, weight=ft.FontWeight.BOLD)]),
                    ft.Row([fetch_btn]),
                    info_text,
                    ft.Divider(),
                    ft.Text("📋 알림 목록", weight=ft.FontWeight.BOLD),
                    self.reply_notifications_list
                ]),
                padding=20,
                bgcolor=ft.Colors.WHITE,
                border_radius=10,
                border=ft.border.all(1, ft.Colors.GREY_300)
            )
        ], scroll=ft.ScrollMode.AUTO)
        
        return content

    def _on_fetch_notifications_click(self, e):
        """알림 가져오기 클릭 핸들러"""
        self.page.snack_bar = ft.SnackBar(ft.Text("🔔 알림을 가져오는 중..."), bgcolor=ft.Colors.BLUE)
        self.page.snack_bar.open = True
        self.page.update()
        
        def fetch_process():
            try:
                driver = self.get_or_create_driver()
                # Handle case where driver might be returned as a tuple (e.g. driver, process)
                if isinstance(driver, tuple):
                    driver = driver[0]
                    
                crawler = ReplyCrawler(driver)
                notifications = crawler.fetch_notifications()
                
                # Check results
                if not notifications:
                    self.page.snack_bar = ft.SnackBar(ft.Text("❌ 새로운 답글 알림이 없습니다."), bgcolor=ft.Colors.ORANGE)
                else:
                    self._render_reply_notifications(notifications)
                    self.page.snack_bar = ft.SnackBar(ft.Text(f"✅ {len(notifications)}개의 알림을 가져왔습니다."), bgcolor=ft.Colors.GREEN)
            except Exception as e:
                print(f"Fetch Error: {e}")
                self.page.snack_bar = ft.SnackBar(ft.Text(f"❌ 오류 발생: {e}"), bgcolor=ft.Colors.RED)
            
            try:
                self.page.snack_bar.open = True
                self.page.update()
            except:
                pass
            
        threading.Thread(target=fetch_process, daemon=True).start()

    def _render_reply_notifications(self, notifications):
        """알림 목록 렌더링"""
        items = []
        for idx, note in enumerate(notifications):
            text = note.get('text', '')
            link = note.get('link', '')
            context = note.get('context', 'UNKNOWN')
            
            # Handler for AI Reply
            def on_ai_reply_click(e, txt=text, lnk=link, ctx=context):
                self._on_reply_auto_engage_click(txt, lnk, ctx)

            # Simple card
            card = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(text, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.TextButton("이동", on_click=lambda e, l=link: [subprocess.run(f"open {l}", shell=True) if sys.platform=='darwin' else subprocess.run(f"start {l}", shell=True)]),
                            ft.ElevatedButton("🤖 AI 자동 답글 (문의 분석)", on_click=on_ai_reply_click, bgcolor=ft.Colors.PURPLE_600, color=ft.Colors.WHITE) 
                        ])
                    ]),
                    padding=10
                )
            )
            items.append(card)
        
        self.reply_notifications_list.controls = items
        self.reply_notifications_list.update()

    # Handler for AI Reply (Render method uses this)
    def _on_reply_auto_engage_click(self, text, url, context='UNKNOWN'):
        """
        AI 자동 답글 처리 로직 (상담 관리 탭)
        context: 'MY_POST' (내 글에 달린 댓글) or 'REPLY_TO_ME' (내 댓글에 대한 답글)
        """
        # 1. Load Contact Info
        try:
            # 🆕 글로벌 설정 경로 사용
            user_settings_path = os.path.join(self._get_app_data_dir(), 'config', 'user_settings.txt')
            with open(user_settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                phone = settings.get('phone', '')
                kakao = settings.get('kakao_url', '')
        except Exception as e:
            phone = ""
            kakao = ""
            print(f"Error loading user settings: {e}")

        contact_info = {'phone': phone, 'kakao': kakao}

        if not phone and not kakao:
            self.page.snack_bar = ft.SnackBar(ft.Text("⚠️ 연락처/카톡 설정이 없습니다. 사용자 설정 탭에서 입력해주세요."), bgcolor=ft.Colors.ORANGE)
            self.page.snack_bar.open = True
            self.page.update()
            # Continue anyway but with empty info (AI might handle it or fallback)

        self.page.snack_bar = ft.SnackBar(ft.Text(f"🤖 [{context}] 답글 분석 및 대응 중..."), bgcolor=ft.Colors.BLUE)
        self.page.snack_bar.open = True
        self.page.update()

        def process_reply():
            try:
                # 1. Analyze Intent
                intent = self.smart_reply.analyze_reply_intent(text)
                print(f"답글 의도: {intent}, 문맥: {context}")
                
                # Logic Branch based on Context
                should_reply = False
                reply_type = None # 'GREETING' or 'INQUIRY'

                if context == 'MY_POST' or context == 'UNKNOWN':
                    # Logic 1: My Blog Comment -> Reply to EVERYTHING
                    should_reply = True
                    reply_type = intent # Just follow the intent
                elif context == 'REPLY_TO_ME':
                    # Logic 2: Reply to My Comment -> Only Reply if INQUIRY
                    if intent == 'INQUIRY':
                        should_reply = True
                        reply_type = 'INQUIRY'
                    else:
                        should_reply = False # Skip Greeting
                
                if should_reply:
                    if reply_type == "GREETING":
                        # GREETING: Also reply with polite thanks
                        reply_content = self.smart_reply.generate_greeting_response(text)
                        
                        # Post it
                        driver = self.get_or_create_driver()
                        if not self.comment_poster or self.comment_poster.driver != driver:
                            self.comment_poster = CommentPoster(driver)
                            
                        success, msg = self.comment_poster.post_comment(url, reply_content, platform='blog')
                        
                        if success:
                            self.page.snack_bar = ft.SnackBar(ft.Text("✅ 감사 인사 답글 등록 완료!"), bgcolor=ft.Colors.GREEN)
                        else:
                             self.page.snack_bar = ft.SnackBar(ft.Text(f"❌ 답글 등록 실패: {msg}"), bgcolor=ft.Colors.RED)

                    else:
                        # INQUIRY
                        reply_content = self.smart_reply.generate_inquiry_response(text, contact_info)
                        
                        # Post it (using CommentPoster)
                        driver = self.get_or_create_driver()
                        if not self.comment_poster or self.comment_poster.driver != driver:
                            self.comment_poster = CommentPoster(driver)
                            
                        # Posting
                        success, msg = self.comment_poster.post_comment(url, reply_content, platform='blog') # Default blog
                        
                        if success:
                            self.page.snack_bar = ft.SnackBar(ft.Text("✅ 문의 답변 등록 완료!"), bgcolor=ft.Colors.GREEN)
                        else:
                            self.page.snack_bar = ft.SnackBar(ft.Text(f"❌ 답변 등록 실패: {msg}"), bgcolor=ft.Colors.RED)
                else:
                    # Skip Case
                    msg = "단순 답글(인사)은 건너뜁니다."
                    self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=ft.Colors.GREY_700)
                    self.page.update()

            except Exception as e:
                print(f"Reply Auto Engage Error: {e}")
                self.page.snack_bar = ft.SnackBar(ft.Text(f"❌ 오류: {e}"), bgcolor=ft.Colors.RED)
            
            try:
                self.page.snack_bar.open = True
                self.page.update()
            except:
                pass

        threading.Thread(target=process_reply, daemon=True).start()


    def _create_marketing_tab(self):
        """지역 마케팅 탭 UI 생성"""
        
        # 데이터 로드
        persona_data = self.persona_manager.load_persona()
        
        # UI 컴포넌트 생성
        self.business_name_field = ft.TextField(label="업체명 (상호)", value=persona_data.get('business_name', ''), width=300)
        self.location_field = ft.TextField(label="지역 (예: 인천 부평구, 서울 강남구, 강원도 양양군)", value=persona_data.get('location', ''), width=300)
        
        self.director_profile_field = ft.TextField(
            label="관장님/대표님 프로필 및 경력",
            value=persona_data.get('director_profile', ''),
            multiline=True,
            min_lines=3,
            max_lines=10,
            hint_text="예: 인천 26년 경력, 합기도 7단, 태권도 5단, 전국체전 금메달..."
        )
        
        self.programs_field = ft.TextField(
            label="주요 프로그램 및 특징",
            value=persona_data.get('programs', ''),
            multiline=True,
            min_lines=3,
            max_lines=10,
            hint_text="예: 유아체육, 입시반, 성인 킥복싱, 차량 운행 가능..."
        )

        self.key_instructions_field = ft.TextField(
             label="지도 방침 및 철학",
             value=persona_data.get('key_instructions', ''),
             multiline=True,
             min_lines=2,
             hint_text="예: 인성 교육 중심, 실전 호신술 중시..."
        )
        
        self.marketing_tone_field = ft.Dropdown(
            label="AI 마케팅 톤 (말투)",
            value=persona_data.get('marketing_tone', '친절한 전문가 (Polite Expert)'),
            options=[
                ft.dropdown.Option("친절한 전문가 (Polite Expert)"),
                ft.dropdown.Option("에너지 넘치는 코치 (Energetic Coach)"),
                ft.dropdown.Option("차분하고 진지한 상담사 (Serious Advisor)"),
                ft.dropdown.Option("친근한 이웃 (Friendly Neighbor)"),
            ],
            width=300
        )
        
        def save_persona_click(e):
            data = {
                "business_name": self.business_name_field.value,
                "location": self.location_field.value,
                "director_profile": self.director_profile_field.value,
                "programs": self.programs_field.value,
                "key_instructions": self.key_instructions_field.value,
                "marketing_tone": self.marketing_tone_field.value
            }
            if self.persona_manager.save_persona(data):
                self.page.snack_bar = ft.SnackBar(content=ft.Text("✅ 마케팅 페르소나 설정이 저장되었습니다!"), bgcolor=ft.Colors.GREEN)
            else:
                self.page.snack_bar = ft.SnackBar(content=ft.Text("❌ 저장 실패"), bgcolor=ft.Colors.RED)
            self.page.snack_bar.open = True
            self.page.update()

        save_btn = ft.ElevatedButton("설정 저장", on_click=save_persona_click, icon=ft.Icons.SAVE, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)

        # --- Tab 1: 설정 및 타겟 발굴 (기존 UI) ---
        
        # Define fields first (to avoid assignment inside list)
        self.search_keyword_field_mkt = ft.TextField(
            label="검색 키워드 (예: 양양 맛집)", 
            width=300,
            on_submit=self._on_marketing_search_click
        )
        self.search_platform_field_mkt = ft.Dropdown(
            label="플랫폼 (검색 대상)",
            width=150,
            options=[
                ft.dropdown.Option("blog", "네이버 블로그"),
                ft.dropdown.Option("cafe", "네이버 카페"),
                ft.dropdown.Option("band", "네이버 밴드"),
            ],
            value="blog"
        )
        
        self.marketing_results_list = ft.ListView(
            expand=True, 
            spacing=10, 
            padding=10,
            height=400 
        )

        # --- Tab 1: 설정 및 타겟 발굴 (기존 UI) ---
        target_tab_content = ft.Container(
            content=ft.Column([
                ft.Text("📍 지역 기반 마케팅 설정", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("AI가 이 정보를 바탕으로 지역 주민들과 소통합니다.", size=14, color=ft.Colors.GREY_700),
                ft.Divider(),
                
                self.business_name_field,
                self.location_field,
                self.director_profile_field,
                self.programs_field,
                self.key_instructions_field,
                self.marketing_tone_field,
                
                ft.Divider(),
                ft.Row([save_btn], alignment=ft.MainAxisAlignment.END),
                
                ft.Container(
                    content=ft.Text("💡 팁: 프로필을 자세히 적을수록 AI가 더 똑똑하게 상담합니다.", size=12, color=ft.Colors.BLUE_700),
                    bgcolor=ft.Colors.BLUE_50,
                    padding=10,
                    border_radius=5
                ),
                
                ft.Divider(),
                ft.Container(
                    content=ft.Column([
                        ft.Text("🎯 타겟 발굴 및 자동 소통", size=20, weight=ft.FontWeight.BOLD),
                        ft.Text("키워드를 검색하여 최근 게시글을 찾고, AI가 작성한 댓글로 소통합니다.", size=14, color=ft.Colors.GREY_600),
                    ]),
                    padding=ft.padding.only(bottom=10)
                ),
                
                ft.Text("🔍 지역 타겟 발굴 및 소통", size=18, weight=ft.FontWeight.BOLD),
                
                ft.Row([
                    self.search_keyword_field_mkt,
                    self.search_platform_field_mkt,
                    ft.ElevatedButton("타겟 발굴 시작", on_click=self._on_marketing_search_click, icon=ft.Icons.SEARCH)
                ]),
                
                ft.Text("검색 결과 (최신순)", size=14, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=self.marketing_results_list,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=5,
                    height=400
                )

            ], scroll=ft.ScrollMode.AUTO),
            padding=20
        )

        # --- Tab 2: 활동 내역 및 리뷰 (New UI) ---
        self.marketing_history_list = ft.ListView(expand=True, spacing=10, padding=10)
        
        def refresh_history_click(e):
             self._render_marketing_history()
        
        history_tab_content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("📅 활동 내역 (최근 50개)", size=18, weight=ft.FontWeight.BOLD),
                    ft.IconButton(ft.Icons.REFRESH, on_click=refresh_history_click, tooltip="새로고침")
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Container(
                    content=self.marketing_history_list,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=5,
                    expand=True
                )
            ]),
            padding=20
        )
        
        # Initial Render of History
        # We need to defer this maybe? No, can call safely.
        # self._render_marketing_history() # -> Logic moved to below

        # Return Tabs
        return ft.Tabs(
            animation_duration=300,
            tabs=[
                ft.Tab(text="설정 및 타겟 발굴", icon=ft.Icons.SEARCH, content=target_tab_content),
                ft.Tab(text="활동 내역 (History)", icon=ft.Icons.HISTORY, content=history_tab_content),
            ],
            expand=True,
            on_change=lambda e: self._render_marketing_history() if e.control.selected_index == 1 else None
        )

    def _render_marketing_history(self):
        """History List 렌더링"""
        self.marketing_history_list.controls.clear()
        history = self.history_manager.load_history()
        
        if not history:
            self.marketing_history_list.controls.append(ft.Text("아직 활동 내역이 없습니다.", color=ft.Colors.GREY_500))
        else:
            for i, entry in enumerate(history):
                # entry: date, title, link, comment, keyword
                
                def open_link_click(e, url=entry.get('link')):
                    import webbrowser
                    webbrowser.open(url)
                    
                def delete_history_click(e, index=i):
                    if self.history_manager.delete_entry(index):
                        self._render_marketing_history()
                        self.page.update()

                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"[{entry.get('date', '')}] {entry.get('keyword', '')}", size=12, color=ft.Colors.GREY_600),
                                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=16, on_click=delete_history_click, tooltip="기록 삭제")
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Text(entry.get('title', '제목 없음'), weight=ft.FontWeight.BOLD, size=14),
                            ft.Text(f"💬 {entry.get('comment', '')}", size=13, color=ft.Colors.BLUE_GREY_800),
                            ft.Row([
                                ft.TextButton("게시글 보기 (수정)", icon=ft.Icons.OPEN_IN_NEW, on_click=open_link_click)
                            ], alignment=ft.MainAxisAlignment.END)
                        ]),
                        padding=10
                    )
                )
                self.marketing_history_list.controls.append(card)
        
        self.marketing_history_list.update()

    def _on_marketing_search_click(self, e):
        """지역 마케팅 타겟 발굴 버튼 클릭 핸들러"""
        keyword = self.search_keyword_field_mkt.value
        platform = self.search_platform_field_mkt.value
        
        if not keyword:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("❌ 검색 키워드를 입력해주세요."), bgcolor=ft.Colors.RED)
            self.page.snack_bar.open = True
            self.page.update()
            return
            
        driver = self.get_or_create_driver()
        if not driver:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("❌ 브라우저를 먼저 실행해주세요 (블로그 시작의 '네이버 로그인')."), bgcolor=ft.Colors.RED)
            self.page.snack_bar.open = True
            self.page.update()
            return

        self.page.snack_bar = ft.SnackBar(content=ft.Text(f"🔍 [{platform}] '{keyword}' 검색 시작... (약 5초 소요)"), bgcolor=ft.Colors.BLUE)
        self.page.snack_bar.open = True
        self.page.update()
        
        def search_thread():
            try:
                finder = TargetFinder(driver)
                results = []
                if platform == 'blog':
                    results = finder.search_blog_posts(keyword)
                elif platform == 'cafe':
                    results = finder.search_cafe_posts(keyword)
                elif platform == 'band':
                    results = finder.search_band_posts(keyword)
                
                # Store results for batch processing
                self.current_search_results = results
                self.current_keyword = keyword
                self.current_platform = platform # Store platform
                # Always reset processed state for new search results
                self.processed_indices = set()
                
                self._render_marketing_results(results, keyword)
                
            except Exception as e:
                print(f"검색 중 오류: {e}")
                self.page.snack_bar = ft.SnackBar(content=ft.Text(f"❌ 검색 오류: {e}"), bgcolor=ft.Colors.RED)
                self.page.snack_bar.open = True
                self.page.update()
        
        threading.Thread(target=search_thread, daemon=True).start()

    def _render_marketing_results(self, results, keyword=None):
        """검색 결과를 UI 리스트에 렌더링"""
        if not hasattr(self, 'processed_indices'):
            self.processed_indices = set()
            
        items = []
        
        # 헤더 & 일괄 실행 버튼
        header = ft.Container(
            content=ft.Row([
                ft.Text(f"🔍 검색 결과: {len(results)}건", weight=ft.FontWeight.BOLD, size=16),
                ft.ElevatedButton(
                    "🚀 전체 자동 소통 실행 (Run All)", 
                    icon=ft.Icons.ROCKET_LAUNCH, 
                    bgcolor=ft.Colors.PURPLE_700, 
                    color=ft.Colors.WHITE,
                    on_click=lambda e: self.run_batch_engage_trigger(e) # We need to trigger the batch logic defined in search_thread or verify access
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=10,
            bgcolor=ft.Colors.GREY_100,
            border_radius=5
        )
        items.append(header)

        if not results:
            items.append(ft.Container(content=ft.Text("검색 결과가 없습니다.", color=ft.Colors.GREY), padding=20))
        else:
            for idx, post in enumerate(results):
                title = post['title']
                link = post['link']
                author = post['author']
                date = post['date']
                platform = post.get('platform', 'blog')
                
                is_processed_session = idx in self.processed_indices
                is_commented_history = self.history_manager.is_commented(link)
                is_processed = is_processed_session or is_commented_history
                
                # 답글 작성 버튼 핸들러
                def on_engage_click(e, post_item=post, index=idx):
                    self._on_marketing_auto_engage_click(post_item, keyword, index=index)

                card_color = ft.Colors.WHITE
                opacity = 1.0
                btn_text = "🤖 AI 자동 소통"
                btn_bg = ft.Colors.PURPLE_600
                btn_disabled = False
                
                if is_processed:
                    card_color = ft.Colors.GREY_200
                    opacity = 0.6
                    if is_commented_history:
                        btn_text = "이미 완료 (기록) ✅"
                    else:
                        btn_text = "완료됨 ✅"
                    btn_bg = ft.Colors.GREY_500
                    btn_disabled = True # 선택사항: 다시 하고 싶을 수도 있으니 활성화 유지하거나 비활성화
                
                # 아이콘 선택
                icon = ft.Icons.ARTICLE
                if platform == 'cafe': icon = ft.Icons.LOCAL_CAFE
                elif platform == 'band': icon = ft.Icons.GROUP

                card = ft.Card(
                    color=card_color,
                    elevation=1 if is_processed else 4,
                    content=ft.Container(
                        opacity=opacity,
                        content=ft.Column([
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.CHECK_CIRCLE if is_processed else icon, color=ft.Colors.GREEN if is_processed else ft.Colors.BLUE),
                                title=ft.Text(title, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK if not is_processed else ft.Colors.GREY_700),
                                subtitle=ft.Text(f"{author} | {date} | {platform}", color=ft.Colors.GREY_700),
                            ),
                            ft.Row(
                                [
                                    ft.ElevatedButton(btn_text, on_click=on_engage_click, icon=ft.Icons.AUTO_AWESOME, bgcolor=btn_bg, color=ft.Colors.WHITE, disabled=btn_disabled),
                                    ft.TextButton("링크 복사", on_click=lambda e, l=link: [subprocess.run(f"echo {l} | pbcopy", shell=True) if sys.platform=='darwin' else None], icon=ft.Icons.COPY),
                                ],
                                alignment=ft.MainAxisAlignment.END,
                            ),
                        ]),
                        padding=10,
                    )
                )
                items.append(card)
        
        self.marketing_results_list.controls = items
        self.marketing_results_list.update()
        self.page.update()

    def run_batch_engage_trigger(self, e):
        """일괄 실행 트리거"""
        if not hasattr(self, 'current_search_results') or not self.current_search_results:
            return

        self.page.snack_bar = ft.SnackBar(ft.Text("🚀 순차적 자동 소통을 시작합니다..."), bgcolor=ft.Colors.PURPLE_600)
        self.page.snack_bar.open = True
        self.page.update()
        
        def batch_process():
            total = len(self.current_search_results)
            keyword = getattr(self, 'current_keyword', '')
            
            for idx, post in enumerate(self.current_search_results):
                # Check session processed
                if idx in self.processed_indices:
                    continue
                
                # Check history processed
                if self.history_manager.is_commented(post['link']):
                    print(f"⏩ [{idx+1}/{total}] 이미 완료된 항목 스킵: {post['title']}")
                    continue
                    
                print(f"🔄 [{idx+1}/{total}] 일괄 처리 중: {post['title']}")
                # 개별 실행 (UI 업데이트 포함)
                self._on_marketing_auto_engage_click(post, keyword, index=idx)
                
                # 랜덤 딜레이
                time.sleep(random.uniform(4, 7))
                
            self.page.snack_bar = ft.SnackBar(ft.Text("✅ 모든 작업이 완료되었습니다!"), bgcolor=ft.Colors.GREEN_600)
            self.page.snack_bar.open = True
            self.page.update()

        threading.Thread(target=batch_process, daemon=True).start()

    def _on_marketing_auto_engage_click(self, post_item, keyword, index=None):
        """AI 자동 소통 실행"""
        from datetime import datetime
        url = post_item['link']
        title = post_item['title']
        platform = post_item.get('platform', 'blog')
        
        # 1. Generate Reply
        if self.page:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"🤖 '{title}' 분석 및 댓글 작성 중..."), duration=2000)
            self.page.snack_bar.open = True
            self.page.update()
        
        # Driver check
        driver = self.get_or_create_driver()
        if not driver:
            self.start_browser_click(None) 
            driver = self.get_or_create_driver()
            if not driver:
                return 
        
        try:
            # Init CommentPoster
            if not self.comment_poster or self.comment_poster.driver != driver:
                self.comment_poster = CommentPoster(driver)
            
            # Go to URL to scrape content for context
            driver.get(url)
            time.sleep(2)
            
            # Switch to mainFrame (only for blog/cafe)
            if platform in ['blog', 'cafe']:
                try:
                    frame_name = "mainFrame" if platform == 'blog' else "cafe_main"
                    driver.switch_to.frame(frame_name)
                except:
                    pass
            
            # Scrape content
            body_text = ""
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text[:1000]
            except:
                body_text = "본문 내용을 가져올 수 없습니다."

            # Generate Reply
            intent = self.smart_reply.classify_intent(body_text)
            reply_text = self.smart_reply.generate_reply(target_text=body_text, intent=intent, platform=platform)
            
            if not reply_text:
                self.page.snack_bar = ft.SnackBar(ft.Text("❌ 댓글 생성 실패"), bgcolor=ft.Colors.RED)
                self.page.snack_bar.open = True
                self.page.update()
                return

            # 2. Post Comment
            self.page.snack_bar = ft.SnackBar(ft.Text(f"📝 댓글 작성 중..."), duration=1000)
            self.page.snack_bar.open = True
            self.page.update()
            
            success, msg = self.comment_poster.post_comment(url, reply_text, platform=platform)
            
            if success:
                # 3. Log to History
                self.history_manager.add_entry({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "keyword": keyword if keyword else "직접 선택",
                    "title": title,
                    "link": url,
                    "comment": reply_text
                })
                
                # 4. Mark as Processed (UI Update)
                if index is not None and hasattr(self, 'processed_indices'):
                    self.processed_indices.add(index)
                
                self.page.snack_bar = ft.SnackBar(ft.Text(f"✅ 댓글 작성 완료! (활동 내역에 저장됨)"), bgcolor=ft.Colors.GREEN)
                
                # Refresh UI Lists
                try:
                    self._render_marketing_history()
                    # Re-render list to reflect grayed out state (processed)
                    if hasattr(self, 'current_search_results'):
                        # Using stored results to re-render without re-fetching
                        self._render_marketing_results(self.current_search_results, getattr(self, 'current_keyword', None))
                except:
                    pass
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"❌ 댓글 작성 실패: {msg}"), bgcolor=ft.Colors.RED)
                
        except Exception as e:
            print(f"Auto Engage Error: {e}")
            self.page.snack_bar = ft.SnackBar(ft.Text(f"오류: {e}"), bgcolor=ft.Colors.RED)
            
        try:
            self.page.snack_bar.open = True
            self.page.update()
        except:
            pass

    
    def _show_log_viewer(self, page):
        """로그 뷰어 다이얼로그 표시"""
        try:
            # 안전한 콘솔 로깅 (noconsole 빌드 대응)
            def safe_print(msg):
                try:
                    if hasattr(self, 'logger'):
                        self.logger.info(msg)
                    else:
                        print(msg)
                except:
                    pass
                    
            safe_print("📜 로그 뷰어 열기 요청됨")
            
            # 로그 내용 가져오기 & 빈 값 처리
            log_content = self.stream_logger.get_logs()
            if not log_content:
                log_content = "⏳ 로그가 아직 없습니다. (잠시 후 업데이트됩니다...)\n"
                safe_print("ℹ️ 초기 로그가 비어있음")

            # 로그 내용을 담을 텍스트
            log_text = ft.Text(
                value=log_content,
                font_family="Consolas, monospace", # 윈도우/맥 호환 폰트
                color=ft.Colors.GREEN_400,
                size=12,
                selectable=True,
                no_wrap=False 
            )
            
            # 스크롤 가능한 컨테이너
            log_view = ft.Column(
                [log_text],
                scroll=ft.ScrollMode.ALWAYS,
                auto_scroll=True,
                expand=True
            )
            
            # 다이얼로그 참조를 위한 변수
            log_dialog = None
            log_loop_running = [True]  # 스레드 제어용 플래그
            
            # 실시간 업데이트를 위한 폴링 루프 (threading.Thread 사용 방식으로 변경 - PyInstaller 호환성 목적)
            def update_log_loop():
                import time
                while log_dialog and log_dialog.open and log_loop_running[0]:
                    try:
                        current_logs = self.stream_logger.get_logs()
                        if log_text.value != current_logs:
                            log_text.value = current_logs
                            log_text.update()
                            log_view.scroll_to(offset=-1, duration=50)
                    except Exception as ex:
                        pass
                    time.sleep(0.5)  # 0.5초마다 갱신
            
            def close_dialog(e):
                log_loop_running[0] = False
                if log_dialog:
                    log_dialog.open = False
                page.update()
                
            def copy_log(e):
                page.set_clipboard(log_text.value)
                page.snack_bar = ft.SnackBar(content=ft.Text("로그가 복사되었습니다."))
                page.snack_bar.open = True
                page.update()
            
            def open_external(e):
                try:
                    if not self.console_log_path or not os.path.exists(self.console_log_path):
                        page.snack_bar = ft.SnackBar(content=ft.Text("로그 파일이 없습니다."))
                        page.snack_bar.open = True
                        page.update()
                        return
                        
                    if sys.platform == 'darwin':
                        # Mac: Terminal.app으로 tail -f 실행
                        cmd = f'tell application "Terminal" to do script "tail -f {self.console_log_path}"'
                        subprocess.run(['osascript', '-e', cmd])
                        
                    elif sys.platform == 'win32':
                        # Windows: 새 창 열어서 로그 감시
                        subprocess.Popen(
                            f'start powershell -NoExit -Command "Get-Content \'{self.console_log_path}\' -Wait"', 
                            shell=True
                        )
                    elif sys.platform == 'linux':
                         subprocess.Popen(['gnome-terminal', '--', 'tail', '-f', self.console_log_path])

                    page.snack_bar = ft.SnackBar(content=ft.Text("새 터미널 창을 열었습니다."))
                    page.snack_bar.open = True
                    page.update()
                    
                    # 🚀 중요: 앱을 계속 사용할 수 있도록 내부 다이얼로그 닫기
                    close_dialog(None)
                    
                except Exception as ex:
                     safe_print(f"터미널 열기 실패: {ex}")
                     try:
                         page.snack_bar = ft.SnackBar(content=ft.Text(f"오류: {ex}"))
                         page.snack_bar.open = True
                         page.update()
                     except: 
                        pass

            log_dialog = ft.AlertDialog(
                title=ft.Text("📜 실시간 실행 로그", size=16, weight=ft.FontWeight.BOLD),
                content=ft.Container(
                    content=log_view,
                    width=900,
                    height=600,
                    bgcolor=ft.Colors.BLACK,
                    padding=15,
                    border_radius=10,
                    border=ft.border.all(1, ft.Colors.GREY_800)
                ),
                actions=[
                    ft.TextButton("새 터미널 창으로 보기 ↗️", icon=ft.Icons.OPEN_IN_NEW, on_click=open_external),
                    ft.TextButton("복사하기", icon=ft.Icons.COPY, on_click=copy_log),
                    ft.TextButton("닫기", on_click=close_dialog),
                ],
                on_dismiss=close_dialog, # 다이얼로그 바깥을 눌러서 닫을 때도 루프 종료
            )
            
            # Flet 0.21+ 방식: page.open() 사용
            page.open(log_dialog)
            # 🆕 강제 업데이트로 다이얼로그 표시 보장 (Windows Fix)
            page.update()
            
            # 🆕 로그 업데이트 폴링 루프 시작 (백그라운드 스레드)
            import threading
            worker = threading.Thread(target=update_log_loop, daemon=True)
            worker.start()

            safe_print("✅ 로그 뷰어 열기 성공 (page.open + update + threading polling)")
            
        except Exception as e:
            try:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"로그 뷰어 열기 실패: {str(e)}"))
                page.snack_bar.open = True
                page.update()
            except:
                pass

    def _open_guide(self, section=None):
        """사용자 가이드 다이얼로그 표시 (앱 내부에서 단계별 안내 + 사이트 이동 버튼)"""
        
        guides = {
            "openai-api-키-gpt-4o-등-사용": {
                "title": "🤖 OpenAI API 키 발급 방법",
                "url": "https://platform.openai.com/api-keys",
                "btn_label": "OpenAI 사이트 이동",
                "steps": [
                    "platform.openai.com 에 접속합니다.",
                    "구글 또는 이메일로 회원가입/로그인 합니다.",
                    "왼쪽 메뉴에서 [API Keys] 를 클릭합니다.",
                    "[+ Create new secret key] 버튼을 누릅니다.",
                    "키 이름(예: MyBlogBot)을 입력하고 생성합니다.",
                    "생성된 키(sk-xxx...)를 복사합니다.",
                    "이 프로그램의 [OpenAI API 키] 칸에 붙여넣기 합니다.",
                ],
                "warning": "⚠️ 키는 생성 시 한 번만 보여줍니다! 반드시 즉시 복사하세요."
            },
            "gemini-api-키-무료-모델-사용-가능": {
                "title": "♊ Gemini API 키 발급 방법 (무료!)",
                "url": "https://aistudio.google.com/app/apikey",
                "btn_label": "Google AI Studio 이동",
                "steps": [
                    "aistudio.google.com 에 접속합니다.",
                    "구글 계정으로 로그인합니다.",
                    "[Create API key] 버튼을 클릭합니다.",
                    "프로젝트를 선택하거나 새로 만듭니다.",
                    "생성된 키를 복사합니다.",
                    "이 프로그램의 [Gemini API 키] 칸에 붙여넣기 합니다.",
                ],
                "warning": "💡 Gemini는 무료로 사용 가능합니다! 일일 990회 제한이 있습니다."
            },
            "brave-search-api-키-뉴스정보-검색용": {
                "title": "🔍 Brave Search API 키 발급 방법",
                "url": "https://brave.com/search/api/",
                "btn_label": "Brave Search 사이트 이동",
                "steps": [
                    "brave.com/search/api/ 에 접속합니다.",
                    "회원가입 후 로그인합니다.",
                    "[Get Started] 또는 Plans 에서 Free Plan을 선택합니다.",
                    "API Keys 메뉴에서 새 키를 생성합니다.",
                    "생성된 키를 복사합니다.",
                    "이 프로그램의 [Brave Search API 키] 칸에 붙여넣기 합니다.",
                ],
                "warning": "💡 Free Plan은 월 2,000회 검색이 무료입니다."
            },
            "기상청-api-키-날씨-정보용": {
                "title": "🌦️ 기상청 API 키 발급 방법",
                "url": "https://www.data.go.kr",
                "btn_label": "공공데이터포털 이동",
                "steps": [
                    "data.go.kr (공공데이터포털)에 접속합니다.",
                    "회원가입 후 로그인합니다.",
                    "검색창에 '단기예보' 를 검색합니다.",
                    "[기상청_단기예보 ((구)동네예보) 조회서비스] 를 클릭합니다.",
                    "[활용신청] 버튼을 눌러 신청합니다. (즉시 승인!)",
                    "마이페이지 → 데이터활용 → 활용신청 현황으로 이동합니다.",
                    "[인증키] 중 Decoding 키를 복사합니다.",
                    "이 프로그램의 [기상청 API 키] 칸에 붙여넣기 합니다.",
                ],
                "warning": "💡 승인은 즉시 되며, 하루 1,000회 무료입니다."
            },
            "네이버-밴드-url": {
                "title": "💚 네이버 밴드 URL 넣는 법",
                "url": "https://band.us",
                "btn_label": "네이버 밴드 이동",
                "steps": [
                    "웹 브라우저에서 band.us 에 접속합니다.",
                    "글을 올릴 밴드를 클릭합니다.",
                    "브라우저 상단 주소창의 URL을 전체 복사합니다.",
                    "예시: https://band.us/band/12345678",
                    "이 프로그램의 [밴드 URL] 칸에 붙여넣기 합니다.",
                ],
                "warning": "💡 밴드 번호(숫자)까지만 입력해도 자동 인식됩니다."
            },
            "네이버-카페-url-및-메뉴-id": {
                "title": "☕ 네이버 카페 URL & 메뉴 ID 넣는 법",
                "url": "https://cafe.naver.com",
                "btn_label": "네이버 카페 이동",
                "steps": [
                    "웹 브라우저에서 cafe.naver.com 에 접속합니다.",
                    "글을 올릴 카페를 클릭합니다.",
                    "카페 메인 주소를 복사하여 [카페 URL] 칸에 입력합니다.",
                    "예시: https://cafe.naver.com/mycafename",
                    "글을 올릴 게시판(메뉴)을 클릭합니다.",
                    "주소창에서 menuId=숫자 부분의 숫자만 복사합니다.",
                    "예시: menuId=123 → 123 을 [메뉴 ID] 칸에 입력합니다.",
                ],
                "warning": "⚠️ 메뉴 ID를 정확히 입력해야 원하는 게시판에 글이 올라갑니다!"
            },
        }
        
        guide = guides.get(section)
        if not guide:
            try:
                self.page.launch_url("https://github.com/kwanwon/naver-blog-automation")
            except:
                pass
            return
        
        # 단계별 안내 UI 구성
        step_controls = []
        for i, step in enumerate(guide["steps"], 1):
            step_controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text(str(i), size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                            bgcolor=ft.Colors.BLUE_600,
                            width=26, height=26,
                            border_radius=13,
                            alignment=ft.alignment.center
                        ),
                        ft.Text(step, size=13, expand=True)
                    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4)
                )
            )
        
        def close_dlg(e):
            guide_dlg.open = False
            self.page.update()
        
        def open_site(e):
            try:
                self.page.launch_url(guide["url"])
            except Exception as ex:
                print(f"⚠️ 사이트 열기 실패: {ex}")
        
        guide_dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(guide["title"], size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    *step_controls,
                    ft.Divider(height=10),
                    ft.Container(
                        content=ft.Text(guide.get("warning", ""), size=12, color=ft.Colors.ORANGE_700, weight=ft.FontWeight.BOLD),
                        padding=8,
                        bgcolor=ft.Colors.ORANGE_50,
                        border_radius=6
                    )
                ], spacing=6, scroll=ft.ScrollMode.AUTO),
                width=460,
                height=350
            ),
            actions=[
                ft.ElevatedButton(
                    guide["btn_label"],
                    icon=ft.Icons.OPEN_IN_NEW,
                    on_click=open_site,
                    bgcolor=ft.Colors.BLUE_600,
                    color=ft.Colors.WHITE
                ),
                ft.TextButton("닫기", on_click=close_dlg)
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        
        self.page.overlay.append(guide_dlg)
        guide_dlg.open = True
        self.page.update()


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
        
        # 주기적 검증 시작
        self.start_periodic_validation()
        
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

        # ==========================================================
        # 🆕 Phase 2 & 전역 UI 컴포넌트 및 핸들러 정의 (순서 중요)
        # ==========================================================

        # 1. 핸들러 함수들 정의
        # 개별 설정 즉시 저장 함수들
        def on_blog_drive_folder_change(e):
            val = e.control.value
            self.user_blog_drive_folder.value = val
            self.blog_drive_folder_path.value = val
            self.user_blog_drive_folder.update()
            self.blog_drive_folder_path.update()
            self._save_setting('blog_drive_folder', val)

        def on_cafe_drive_folder_change(e):
            val = e.control.value
            self.user_cafe_drive_folder.value = val
            self.cafe_drive_folder_path.value = val
            self.user_cafe_drive_folder.update()
            self.cafe_drive_folder_path.update()
            self._save_setting('cafe_drive_folder', val)

        def on_api_checkbox_change(e):
            api_key_field.visible = use_api_checkbox.value
            api_key_help_text.visible = use_api_checkbox.value
            openai_help_btn.visible = use_api_checkbox.value
            page.update()

        # 2. 공통 UI 컴포넌트 정의 (개별 탭 분리 적용 완료)
        self.blog_sheet_url = ft.TextField(
            label="📊 블로그 스프레드시트 주제 링크 (CSV 형태)",
            hint_text="블로그 포스팅용 구글 시트 공유 URL 입력",
            value=self.settings.get('blog_sheet_url', ''),
            expand=True,
            on_change=lambda e: self._save_setting('blog_sheet_url', e.control.value)
        )
        
        self.cafe_sheet_url = ft.TextField(
            label="📊 카페 스프레드시트 주제 링크 (CSV 형태)",
            hint_text="카페 포스팅용 구글 시트 공유 URL 입력",
            value=self.settings.get('cafe_sheet_url', ''),
            expand=True,
            on_change=lambda e: self._save_setting('cafe_sheet_url', e.control.value)
        )

        self.band_sheet_url = ft.TextField(
            label="📊 밴드 스프레드시트 주제 링크 (CSV 형태)",
            hint_text="밴드 자동 포스팅용 구글 시트 공유 URL 입력",
            value=self.settings.get('band_sheet_url', ''),
            expand=True,
            on_change=lambda e: self._save_setting('band_sheet_url', e.control.value)
        )

        self.user_blog_drive_folder = ft.TextField(
            label="📂 블로그 이미지 감지 폴더 (Google Drive)",
            hint_text="블로그용 드라이브 폴더 경로를 입력하세요...",
            value=self.settings.get('blog_drive_folder', ''),
            expand=True,
            on_change=on_blog_drive_folder_change
        )
        
        self.user_cafe_drive_folder = ft.TextField(
            label="📂 카페 이미지 감지 폴더 (Google Drive)",
            hint_text="카페용 드라이브 폴더 경로를 입력하세요...",
            value=self.settings.get('cafe_drive_folder', ''),
            expand=True,
            on_change=on_cafe_drive_folder_change
        )

        # 📂 블로그 / 카페 수동 이미지 폴더 선택 필드 (드라이브 감지처럼 특정 폴더 경로 저장)
        self.blog_manual_folder_path = ft.TextField(
            label="📂 블로그 수동 이미지 폴더",
            hint_text="블로그 수동 폴더 경로를 입력하세요...",
            value=self.settings.get('blog_manual_folder', ''),
            expand=True,
            on_change=lambda e: self._save_setting('blog_manual_folder', e.control.value)
        )
        
        self.cafe_manual_folder_path = ft.TextField(
            label="📂 카페 수동 이미지 폴더",
            hint_text="카페 수동 폴더 경로를 입력하세요...",
            value=self.settings.get('cafe_manual_folder', ''),
            expand=True,
            on_change=lambda e: self._save_setting('cafe_manual_folder', e.control.value)
        )

        # 🟢 자동 주제 모드 체크박스 및 상태
        auto_topic_status = ft.Text(
            value="자동 주제 모드: " + ("활성화" if self.settings.get('auto_topic', False) else "비활성화"),
            color=ft.Colors.GREEN if self.settings.get('auto_topic', False) else ft.Colors.GREY_600,
            size=12,
            italic=True,
            visible=True
        )

        # 🟢 자동 주제 모드 체크박스
        def on_auto_topic_change(e):
            if hasattr(self, 'topic_input'):
                self.topic_input.disabled = e.control.value
                self.topic_input.update()
            self._save_setting('auto_topic', e.control.value)
            
        auto_topic_checkbox = ft.Checkbox(
            label="주제 자동 순환 사용",
            value=self.settings.get('auto_topic', False),
            on_change=on_auto_topic_change
        )

        # 🟢 이미지 자동 삽입 체크박스
        def on_auto_image_change(e):
            is_on = e.control.value
            self.blog_image_mode_dropdown.disabled = not is_on
            self.blog_media_position_dropdown.disabled = not is_on
            self.blog_media_order_dropdown.disabled = not is_on
            if not is_on:
                self.blog_drive_settings_row.visible = False
                if hasattr(self, 'blog_manual_settings_row'):
                    self.blog_manual_settings_row.visible = False
            else:
                if hasattr(self, 'on_blog_image_mode_change'):
                    self.on_blog_image_mode_change(type('obj', (object,), {'control': self.blog_image_mode_dropdown}))
            
            self.blog_image_mode_dropdown.update()
            self.blog_media_position_dropdown.update()
            self.blog_media_order_dropdown.update()
            self._save_setting('auto_image', is_on)

        auto_image_checkbox = ft.Checkbox(
            label="블로그 이미지 자동 모드",
            value=self.settings.get('auto_image', True),
            on_change=on_auto_image_change
        )

        # 🟢 최종 발행 단계 관련 체크박스
        auto_final_publish_checkbox = ft.Checkbox(
            label="태그 완료 후 자동 발행 (권장)",
            value=self.settings.get('auto_final_publish', True)
        )
        
        auto_final_publish_help_text = ft.Text(
            "체크 시: 태그 입력 후 [발행]까지 자동 완료\n체크 해제: 태그 입력 후 발행 직전 멈춤 (수동 확인용)",
            size=11, color=ft.Colors.GREY_600, italic=True
        )

        # 🟢 API 사용 여부 및 자동 업로드 체크박스
        use_api_checkbox = ft.Checkbox(
            label="OpenAI API 사용 여부 (체크 해제 시 더미 데이터 사용)",
            value=not self.settings.get('use_dummy', False),
            on_change=on_api_checkbox_change
        )
        
        auto_upload_checkbox = ft.Checkbox(
            label="GPT 글 생성 완료 후 자동 블로그 업로드",
            value=self.settings.get('auto_upload', False)
        )

        # API 키 필드들
        api_key_field = ft.TextField(
            label="OpenAI API 키",
            hint_text="OpenAI API 키를 입력하세요...",
            password=True,
            can_reveal_password=False,
            visible=not self.use_dummy,
            expand=True
        )

        openai_help_btn = ft.IconButton(
            icon=ft.Icons.HELP_OUTLINE,
            tooltip="OpenAI API 키 발급 가이드 보기",
            on_click=lambda _: self._open_guide("openai-api-키-gpt-4o-등-사용"),
            visible=not self.use_dummy
        )

        gemini_api_key_field = ft.TextField(
            label="Gemini API 키",
            hint_text="Gemini API 키를 입력하세요...",
            password=True,
            can_reveal_password=False,
            visible=True,
            expand=True
        )

        gemini_help_btn = ft.IconButton(
            icon=ft.Icons.HELP_OUTLINE,
            tooltip="Gemini API 키 발급 가이드 보기",
            on_click=lambda _: self._open_guide("gemini-api-키-무료-모델-사용-가능"),
            visible=True
        )

        brave_api_key_field = ft.TextField(
            label="Brave Search API 키",
            hint_text="Brave Search API 키 (선택 사항)",
            password=True,
            can_reveal_password=True,
            visible=True,
            expand=True
        )

        brave_help_btn = ft.IconButton(
            icon=ft.Icons.HELP_OUTLINE,
            tooltip="Brave Search API 키 발급 가이드 보기",
            on_click=lambda _: self._open_guide("brave-search-api-키-뉴스정보-검색용"),
            visible=True
        )
        
        api_key_help_text = ft.Text(
            "API 키는 보안을 위해 항상 암호화되어 표시됩니다. 발급받은 키를 입력하세요.",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True,
            visible=not self.use_dummy
        )

        # 🆕 [지능형 AI 포스팅 상세 제어 옵션 부활]
        self.blog_persona_dropdown = ft.Dropdown(
            label="블로그 페르소나 (역할)",
            options=[
                ft.dropdown.Option("expert_sport", "연구원/정보 전문가 (신뢰감)"),
                ft.dropdown.Option("sabeom", "다정한 웰니스 에디터 (친근함)"),
                ft.dropdown.Option("parent_friend", "친근한 정보 큐레이터 (공감형)"),
            ],
            value=self.settings.get('blog_persona_mode', 'expert_sport'),
            width=280,
            on_change=lambda e: self._save_setting('blog_persona_mode', e.control.value)
        )
        
        self.blog_style_dropdown = ft.Dropdown(
            label="블로그 말투 (스타일)",
            options=[
                ft.dropdown.Option("haeyo", "해요체 (~해요, ~에요?)"),
                ft.dropdown.Option("imnida", "하십시오체 (~입니다, ~합니다)"),
                ft.dropdown.Option("half_half", "반반 혼합 (5:5 친근+전문)"),
            ],
            value=self.settings.get('blog_style_mode', 'haeyo'),
            width=280,
            on_change=lambda e: self._save_setting('blog_style_mode', e.control.value)
        )
        
        self.blog_theme_dropdown = ft.Dropdown(
            label="본문 강조 테마 (양념)",
            options=[
                ft.dropdown.Option("none", "강조 없음 (순수 주제)"),
                ft.dropdown.Option("spice_growth", "생애주기 신체 발달 강조"),
                ft.dropdown.Option("spice_posture", "자세 교정 & 코어 강화 강조"),
                ft.dropdown.Option("spice_stamina", "기초 체력 & 면역력 증가 강조"),
                ft.dropdown.Option("spice_obesity", "체지방 & 대사 관리 강조"),
                ft.dropdown.Option("spice_brain", "인지 기능 & 두뇌 활성화 강조"),
                ft.dropdown.Option("spice_focus", "집중력 & 마인드 컨트롤 강조"),
                ft.dropdown.Option("spice_happy", "정서적 안정 & 스트레스 케어"),
                ft.dropdown.Option("spice_confidence", "작은 성취와 자신감 배양"),
                ft.dropdown.Option("spice_social", "협력과 소통의 가치 강조"),
                ft.dropdown.Option("spice_manners", "타인 존중과 성숙한 에티켓"),
                ft.dropdown.Option("spice_safety", "유연한 안전 대처 & 밸런스"),
            ],
            value=self.settings.get('blog_theme', 'none'),
            width=280,
            on_change=lambda e: self._save_setting('blog_theme', e.control.value)
        )
        
        self.blog_hometip_checkbox = ft.Checkbox(
            label="1분 홈케어 스트레칭 팁 자동 포함 (순환 로테이션)",
            value=self.settings.get('blog_hometip', False),
            on_change=lambda e: self._save_setting('blog_hometip', e.control.value)
        )

        # GPT 설정 탭 컴포넌트
        gpt_persona = ft.TextField(
            label="GPT 페르소나",
            hint_text="GPT가 어떤 역할이나 정체성을 가지고 글을 작성할지 정의하세요...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True,
            value="""[Strict Style Rules: Anti-AI Filter]
No Quotes: 제목과 본문에 따옴표(" ", ' ') 사용 금지. 강조는 **[대괄호]**나 볼드체로 하세요.
Human-like List: 숫자(1. 2. 3.) 대신 '첫 번째는', '둘째는', '하나. 둘.' 처럼 사람의 호흡으로 쓰세요.
Forbidden Words: 최고, 최선, 소중한, 놀라운, 발전하는, 결론적으로, 요약하자면 (AI가 즐겨 쓰는 단어 제외).
Local Touch: 체육관의 지역적 정체성을 자연스럽게 녹여내세요."""
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
            expand=True,
            value="""[Content Structure: Quality over Quantity]
Target Length: 1,200 ~ 1,300 characters. (모바일 가독성과 정보성을 모두 잡는 최적의 길이)
Intro (Local & Emotional): 우리 지역의 풍경이나 날씨로 시작해 부모님의 고민을 건드리세요.
Body (Expertise): 전문 용어(예: 근방추, 성장판, 코어)를 반드시 포함하되, **"쉽게 말해 ~라는 뜻입니다"**라는 설명을 덧붙이세요. 여기서 '전문성'이 판가름 납니다.
Outro (Actionable Tip): 오늘 밤 아이에게 해줄 수 있는 작은 격려나 신체 활동을 제안하세요."""
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
            expand=True,
            value="""[Strict Style Rules: Anti-AI Filter]
No Quotes: 제목과 본문에 따옴표(" ", ' ') 사용 금지. 강조는 **[대괄호]**나 볼드체로 하세요.
Human-like List: 숫자(1. 2. 3.) 대신 '첫 번째는', '둘째는', '하나. 둘.' 처럼 사람의 호흡으로 쓰세요.
Forbidden Words: 최고, 최선, 소중한, 놀라운, 발전하는, 결론적으로, 요약하자면 (AI가 즐겨 쓰는 단어 제외).
Local Touch: 체육관의 지역적 정체성을 자연스럽게 녹여내세요."""
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
            label="밴드 전용 AI 지침",
            hint_text="밴드 글 작성 시 AI가 참고할 지침 (비워두면 기본값 사용)",
            multiline=True,
            min_lines=3,
            max_lines=10,
            expand=True,
            value="""[페르소나] 너는 [OO지역]에서 [N]년 경력을 가진 [종목] 관장님이야. 학부모님께는 신뢰받는 교육 전문가이자, 아이들에게는 따뜻한 멘토야.

[톤앤매너 (중요 ⭐)]
- 하오체/합쇼체(다, 까): 뉴스, 건강 상식, 핫이슈 등 객관적인 정보를 전달할 때는 신뢰감을 주기 위해 '다/까'를 사용해.
- 해요체(요): 첫 인사, 공감하는 대목, 학부모님께 드리는 조언과 응원 등 감성적인 대화 부분에서는 부드러운 '해요체'를 사용해.
- 이 두 말투를 한 글 안에서 자연스럽게 섞어 '따뜻한 전문가'의 이미지를 구축해줘.

[내용 구성 규칙]
- 시간/날씨 반영: 비밀 쪽지(현재 시간)를 확인해 인사를 건네고, [OO지역] 날씨에 따른 아이들의 건강 관리를 언급해.
- 학부모 대화 소재(이슈): 검색된 뉴스(교육/생활/건강) 활용.
- 생활 운동: 누구나 따라 할 수 있는 간단한 스트레칭이나 건강 팁을 포함해.
- 수련생 언급: "우리 아이들의 건강한 성장"처럼 포괄적으로 표현(특정 시간 언급 X).

[글 구조 및 제약]
- 분량: 400~500자 내외, 2~3개 문단.
- 필수 포함: 따뜻한 제목, 명언 1구절(작가 포함), 20자 이내 희망 문구, 25자 이내 응원 문구.
- 이모지: 문단 끝에 최대 2개만 허용. 질문은 딱 1회만."""
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
        
        # (Duplicate use_api_checkbox removed)
        
        # 자동 업로드 설정 도움말
        auto_upload_help_text = ft.Text(
            "이 옵션을 선택하면 GPT가 글을 생성한 후 자동으로 블로그에 업로드합니다.",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )
        
        # 자동 주제 선택 설정 도움말
        auto_topic_help_text = ft.Text(
            "체크: 사용자 설정에 등록된 주제 중 하나를 자동으로 선택하여 글을 생성합니다. 체크 해제: 수동으로 주제를 입력합니다.",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )
        
        # 이미지 삽입 모드 설정 (스케줄러/타이머 전용 - 드라이브 감지는 별도 독립 섹션)
        def on_blog_image_mode_change(e):
            save_app_settings(e)
            val = e.control.value
            is_on = auto_image_checkbox.value
            if hasattr(self, 'blog_manual_settings_row'):
                self.blog_manual_settings_row.visible = (val == "manual" and is_on)
                self.blog_manual_settings_row.update()
            
        self.on_blog_image_mode_change = on_blog_image_mode_change

        self.blog_image_mode_dropdown = ft.Dropdown(
            label="이미지 폴더 소스",
            options=[
                ft.dropdown.Option("auto", "자동 (Auto)"),
                ft.dropdown.Option("manual", "수동 (Manual)"),
                ft.dropdown.Option("off", "사용 안함 (Off)"),
            ],
            value="auto",
            width=200,
            on_change=on_blog_image_mode_change
        )
        
        self.blog_media_position_dropdown = ft.Dropdown(
            label="삽입 위치",
            options=[
                ft.dropdown.Option("start", "글 시작 부분"),
                ft.dropdown.Option("middle", "문단 사이 분산"),
                ft.dropdown.Option("end", "맨 아래 일괄"),
                ft.dropdown.Option("random", "무작위"),
            ],
            value=self.settings.get('blog_media_position', 'middle'),
            width=180,
            on_change=lambda e: self._save_setting('blog_media_position', e.control.value)
        )

        self.blog_media_order_dropdown = ft.Dropdown(
            label="사진/영상 순서",
            options=[
                ft.dropdown.Option("image_first", "사진 우선"),
                ft.dropdown.Option("video_first", "영상 우선"),
                ft.dropdown.Option("mixed", "무작위"),
                ft.dropdown.Option("off", "사용 안함"),
            ],
            value=self.settings.get('blog_media_order', 'image_first'),
            width=180,
            on_change=lambda e: self._save_setting('blog_media_order', e.control.value)
        )
        
        # 📂 구글 드라이브 감지 설정 (기본 숨김)
        self.blog_drive_folder_path = ft.TextField(
            label="감시할 드라이브 폴더 경로",
            hint_text="예: /Users/username/Google Drive/BlogImages",
            value=self.settings.get('blog_drive_folder', ''),
            expand=True,
            on_change=on_blog_drive_folder_change,
            on_blur=lambda e: self._save_setting('blog_drive_folder', self.blog_drive_folder_path.value)
        )
        
        self.blog_drive_watcher_status = ft.Text("상태: 정지됨", color=ft.Colors.GREY_600)
        self.blog_drive_watcher_btn = ft.ElevatedButton(
            "실시간 감시 시작",
            icon=ft.Icons.PLAY_ARROW,
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.GREEN_700,
            on_click=self._toggle_blog_drive_watcher
        )

        self.blog_drive_settings_row = ft.Row([
            self.blog_drive_folder_path,
            ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=lambda e: self._open_folder_picker_for(self.blog_drive_folder_path)),
            self.blog_drive_watcher_btn
        ], visible=True)  # 🆕 드라이브 감시는 드롭다운과 독립적으로 항상 표시
        
        self.blog_manual_settings_row = ft.Row([
            self.blog_manual_folder_path,
            ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=lambda e: self._open_folder_picker_for(self.blog_manual_folder_path)),
        ], visible=False)


        blog_image_help_text = ft.Text(
            "자동: 셔플 후 삽입 | 수동: 선택 창 오픈 | ❕ 폰 포스팅은 아래 감시 영역에서 독립 운영",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )
        
        # 🎯 최종 발행 설정 추가
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
        
        def on_checkbox_change(e):
            save_app_settings()  # 체크박스 변경 시 자동으로 설정 저장
            page.update()
            
        use_api_checkbox.on_change = on_api_checkbox_change
        auto_upload_checkbox.on_change = on_checkbox_change
        auto_topic_checkbox.on_change = on_checkbox_change
        auto_final_publish_checkbox.on_change = on_checkbox_change

        def save_app_settings(e=None):
            try:
                # 🔄 기존 설정 업데이트 (덮어쓰기 방지)
                self.settings.update({
                    "use_dummy": not use_api_checkbox.value,
                    "auto_upload": auto_upload_checkbox.value,
                    
                    # 블로그 이미지 설정
                    "auto_image": auto_image_checkbox.value,
                    "blog_image_mode": self.blog_image_mode_dropdown.value,
                    "blog_media_position": self.blog_media_position_dropdown.value,
                    "blog_media_order": self.blog_media_order_dropdown.value,
                    "blog_drive_folder": self.blog_drive_folder_path.value,
                    
                    # 카페 이미지 설정
                    "cafe_auto_image": self.cafe_image_mode_dropdown.value == "auto",
                    "cafe_image_mode": self.cafe_image_mode_dropdown.value,
                    "cafe_drive_folder": self.cafe_drive_folder_path.value,
                    
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
                })
                
                # 🆕 글로벌 설정 경로 사용
                app_settings_path = get_app_settings_path()
                os.makedirs(os.path.dirname(app_settings_path), exist_ok=True)
                with open(app_settings_path, 'w', encoding='utf-8') as f:
                    json.dump(self.settings, f, ensure_ascii=False, indent=2)
                
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
                # 🆕 글로벌 설정 경로 사용
                app_settings_path = get_app_settings_path()
                if os.path.exists(app_settings_path):
                    with open(app_settings_path, 'r', encoding='utf-8') as f:
                        app_settings = json.load(f)
                        use_api_checkbox.value = not app_settings.get('use_dummy', False)
                        api_key_field.visible = use_api_checkbox.value
                        api_key_help_text.visible = use_api_checkbox.value
                        # 블로그 이미지 모드 복구 (기존 'detect' 값은 'auto'로 대체)
                        saved_blog_img_mode = app_settings.get('blog_image_mode', 'auto')
                        if saved_blog_img_mode == 'detect':
                            saved_blog_img_mode = 'auto'  # detect는 독립 섹션으로 분리됨
                        self.blog_image_mode_dropdown.value = saved_blog_img_mode
                        self.blog_media_position_dropdown.value = app_settings.get('blog_media_position', 'middle')
                        self.blog_media_order_dropdown.value = app_settings.get('blog_media_order', 'image_first')
                        self.blog_drive_folder_path.value = app_settings.get('blog_drive_folder', '')
                        auto_image_checkbox.value = app_settings.get('auto_image', True)
                        
                        # 카페 이미지 모드 복구
                        self.cafe_image_mode_dropdown.value = app_settings.get('cafe_image_mode', 'auto')
                        self.cafe_drive_folder_path.value = app_settings.get('cafe_drive_folder', '')

                        auto_topic_checkbox.value = app_settings.get('auto_topic', False)
                        auto_final_publish_checkbox.value = app_settings.get('auto_final_publish', True)
                        image_insert_mode_value = app_settings.get('image_insert_mode', 'random')
                        
                        if 'idle_visit_count' in locals():
                            idle_visit_count.value = app_settings.get('idle_visit_count', 2)
                        
                        # UI 가시성 업데이트
                        self._toggle_blog_drive_watcher_ui()
                        self._toggle_cafe_drive_watcher_ui()
                        
                        # 체크박스 상태에 따른 초기화 진행
                        on_auto_topic_change(type('obj', (object,), {'control': auto_topic_checkbox}))
                        on_auto_image_change(type('obj', (object,), {'control': auto_image_checkbox}))
                        page.update()
                        
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
                    "api_key": api_key_field.value,
                    "gemini_api_key": gemini_api_key_field.value,
                    "brave_key": brave_api_key_field.value,
                    "blog_persona_mode": self.blog_persona_dropdown.value,
                    "blog_style_mode": self.blog_style_dropdown.value,
                    "blog_theme": self.blog_theme_dropdown.value,
                    "blog_hometip": self.blog_hometip_checkbox.value,
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                # 🆕 글로벌 설정 경로 사용
                gpt_settings_path = get_gpt_settings_path()
                os.makedirs(os.path.dirname(gpt_settings_path), exist_ok=True)
                with open(gpt_settings_path, 'w', encoding='utf-8') as f:
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
                    # 🆕 글로벌 설정 경로 사용
                    user_settings_path = get_user_settings_path()
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
                # 🆕 글로벌 설정 경로 사용
                gpt_settings_path = get_gpt_settings_path()
                if os.path.exists(gpt_settings_path):
                    with open(gpt_settings_path, 'r', encoding='utf-8') as f:
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
                        brave_api_key_field.value = settings.get('brave_key', '')
                        # 🆕 [지능형 AI 포스팅 옵션 복원]
                        self.blog_persona_dropdown.value = settings.get('blog_persona_mode', 'expert_sport')
                        self.blog_style_dropdown.value = settings.get('blog_style_mode', 'haeyo')
                        self.blog_theme_dropdown.value = settings.get('blog_theme', 'none')
                        self.blog_hometip_checkbox.value = settings.get('blog_hometip', False)
                
                # API 사용 여부 설정 로드
                # 🆕 글로벌 설정 경로 사용
                app_settings_path = get_app_settings_path()
                if os.path.exists(app_settings_path):
                    with open(app_settings_path, 'r', encoding='utf-8') as f:
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
                    # 🆕 글로벌 설정 경로 사용
                    user_settings_path = get_user_settings_path()
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
            label="연락처 (네이버 번호/상담 답글용)",
            hint_text="연락처를 입력하세요 (예: 010-1234-5678)..."
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

        weather_location = ft.TextField(
            label="날씨 지역 (동/면/읍 단위)",
            hint_text="예: 인천 부평구, 원주시, 강릉시"
        )

        kma_api_key = ft.TextField(
            label="기상청 API 키 (공공데이터포털)",
            hint_text="data.go.kr에서 발급받은 단기예보 인증키를 입력하세요",
            password=True,
            expand=True
        )

        kma_help_btn = ft.IconButton(
            icon=ft.Icons.HELP_OUTLINE,
            tooltip="기상청 API 키 발급 가이드 보기",
            on_click=lambda _: self._open_guide("기상청-api-키-날씨-정보용")
        )

        kakao_url = ft.TextField(
            label="카카오톡 상담 링크 (상담 답글용)",
            hint_text="카카오톡 오픈채팅방 URL을 입력하세요..."
        )

        blog_tags = ft.TextField(
            label="블로그 태그",
            hint_text="태그를 쉼표(,)로 구분하여 입력하세요. 예: 태권도,도장,무술",
            multiline=True,
            min_lines=2,
            max_lines=4
        )

        video_title = ft.TextField(
            label="🎬 동영상 업로드 제목",
            hint_text="동영상 업로드 시 사용할 기본 제목",
            value="네이버뉴스"
        )

        video_info = ft.TextField(
            label="🎬 동영상 업로드 정보(설명)",
            hint_text="동영상 업로드 시 사용할 기본 설명",
            value="네이버뉴스",
            multiline=True,
            min_lines=2,
            max_lines=3
        )

        video_tags = ft.TextField(
            label="🎬 동영상 업로드 태그 (쉼표 구분)",
            hint_text="예: 양양합기도, 태권도, 운동",
            value="양양합기도, 등등"
        )

        # 🟢 종목에 따른 기본 주제어 치환 로직
        gym_sport = self.settings.get('gym_sport', '합기도')
        primary_sport = gym_sport.split(',')[0].strip() or '합기도'
        
        def apply_sport_to_topics(topics):
            if primary_sport != '태권도':
                return topics.replace('태권도', primary_sport)
            return topics

        # 기본 주제 목록 정의
        default_blog_topics_str = apply_sport_to_topics(
            "[새학기 필독] 학교 적응 잘하는 아이들의 공통점과 멘탈 관리법, [건강] 요즘 유행하는 소아 독감 vs 감기 차이점과 예방, [교육 이슈] 초등학생 문해력 골든타임 운동이 정답인 이유, [성장 꿀팁] 우리 아이 숨은 키 1cm 찾아주는 성장판 자극 운동, 스쿨존 교통안전법규(민식이법) 최신 개정 사항과 주의점, [계절] 미세먼지 심한 날 실내에서 하는 키 크는 체조, [심리] 친구 관계 어려워하는 아이 자존감 높여주는 대화법, 소아 비만 골든타임 살이 키로 간다는 말의 진실과 오해, 스마트폰 중독 예방 무조건 금지보다 효과적인 약속 정하기, [건강] 아이들 체력 관리 실내 적정 온도와 환기의 중요성, [영양] 편식하는 아이도 잘 먹는 키 성장 슈퍼푸드 5가지, 초등학생 학교 폭력 예방 부모님이 꼭 체크해야 할 신호, [운동 효과] 줄넘기만 하면 무릎 아프다? 올바른 점프 운동법, 집중력 짧은 아이 엉덩이 힘 기르는 신체 활동의 비밀, [면역력] 잔병치레 잦은 아이 면역력 쑥쑥 올리는 생활 습관, [교육] 개정되는 초등 교육 과정 무엇이 핵심일까?, 아침밥 꼭 먹어야 할까? 두뇌 회전과 아침 식사의 관계, [수면] 밤 10시부터 새벽 2시 성장 호르몬 골든타임 사수하기, [안전] 자전거 킥보드 타는 아이 헬멧 착용과 안전 수칙, 형제 자매 싸움 줄이고 우애 깊게 키우는 부모의 중재법, [건강] 갑자기 더워진 날씨 아이들 온열 질환 예방 가이드, 비 오는 날 아이와 뭐 하고 놀지? 집콕 신체놀이 추천, [성격] 소심하고 내성적인 아이 태권도로 리더십 키우기, 인스턴트 간식 줄이기 대작전 건강하고 맛있는 대안은?, [예방] 유행성 눈병 피부질환 예방하는 위생 수칙, [자세] 구부정한 거북목 척추측만증 예방하는 바른 자세 교정, 학원 뺑뺑이로 지친 아이 멍 때리기(휴식)의 중요성, [이슈] 딥페이크 등 디지털 범죄로부터 우리 아이 지키는 법, 운동 싫어하는 아이 놀이처럼 시작하는 3가지 방법, [식습관] 밥 안 먹고 군것질만 하는 아이 습관 고치기, 사춘기 빨리 오는 성조숙증 예방하는 생활 습관 체크리스트, [발달] 아이 신발 밑창이 한쪽만 닳는다면? 골반 불균형 체크, [정보] 주말에 아이와 가볼 만한 지역 명소 박물관 추천, 칭찬 스티커의 역효과? 올바른 동기 부여와 보상 방법, [감정] 떼쓰고 화내는 아이 감정 조절 능력 키워주는 훈육, [안전] 지진 화재 발생 시 아이들에게 가르쳐야 할 대피 요령, 초등 글쓰기 실력 독서보다 경험 말하기가 먼저다, [방학] 춥거나 더울 때 실내 운동으로 체력 키 성장 잡기, 우리 아이 첫 사회생활 태권도장에서 배우는 예절과 질서, [건강] 눈 나빠지는 아이들 드림렌즈 대신 눈 건강 생활 수칙, 넘어져도 툭 털고 일어나는 회복 탄력성 기르는 법, [교육] 코딩 교육 열풍 논리적 사고력은 신체 활동에서 시작된다, 층간소음 걱정 없는 집안 운동 소리 없이 강한 동작들, [위생] 손 씻기만큼 중요한 아이들 개인 위생 용품 관리법, 아이가 거짓말을 했을 때 혼내기보다 이유를 물어보세요, [영양] 우유만 많이 먹으면 키가 클까? 칼슘 흡수의 비밀, 맞벌이 부모를 위한 아이 방과 후 돌봄 안전하게 관리하기, [트렌드] 요즘 초등학생 사이에서 유행하는 놀이 문화를 아시나요?, 실패를 두려워하지 않는 도전 정신 띠 승급 심사의 효과, [부모마음] 우리 아이가 가장 듣고 싶어 하는 말 한마디 사랑해 믿어"
        )

        default_band_topics_str = apply_sport_to_topics(
            "[육아 꿀팁] 아침 등굣길 아이 기분 좋게 깨우는 방법, [공감] 엄마 배고파 소리 무서운 방학 시즌 간식 뭐 해주시나요?, [건강] 환절기 감기 기운 있을 때 효과 좋은 민간요법 공유해요, [질문] 우리 아이가 가장 좋아하는 반찬은 무엇인가요?, [정보] 주말 비 소식 있을 때 집에서 할 수 있는 풍선 놀이 추천, [일상] 운동하고 땀 흘린 뒤 밝게 웃는 아이 표정이 제일 예쁘죠?, [안전] 스쿨존 30km 서행 우리 아이들을 위해 꼭 지켜주세요, [성장] 키 크는 스트레칭 자기 전 딱 5분만 같이 해주세요, [소통] 아이에게 들었을 때 가장 힘이 나는 말은? (댓글로 자랑해주세요), [날씨] 갑자기 추워진 날씨 아이들 옷차림 어떻게 입히셨나요?, [교육] 숙제하기 싫어하는 아이 5분 타이머 법칙 써보세요, [자랑] 오늘 태권도장에서 칭찬받았다고 자랑하던가요?, [정보] 요즘 독감이 독하네요 아이들 마스크 챙겨주시나요?, [주말] 이번 주말 가족 나들이 계획 좋은 곳 있으면 공유해요!, [습관] 정리 정돈 잘하는 아이로 키우는 바구니 법칙, [음식] 편식쟁이도 무장해제시키는 마법의 메뉴 있나요?, [심리] 아이가 속상해할 때 그랬구나 공감 한마디의 힘, [이슈] 요즘 학교 앞에서 유행한다는 불량식품 주의하세요, [계절] 꽃 피는 계절 아이 사진 예쁘게 찍어주는 팁, [응원] 오늘도 아이 키우느라 고생하신 학부모님들 모두 파이팅입니다, [메뉴] 오늘 저녁 메뉴 고민되시죠? 간단한 아이 반찬 추천해요, [질문] 하얀 도복 깨끗하게 세탁하는 노하우 있으신가요?, [공감] 학원 가기 싫다고 떼쓰는 날 어떻게 달래주시나요?, [정보] 아이들 키 크는데 도움 되는 영양제 추천해주세요, [자랑] 우리 아이가 줄넘기 쌩쌩이 성공했다고 자랑하네요!, [주말] 비 오는 주말 아이와 가볼 만한 실내 놀이터 추천, [일상] 아이 등원시키고 마시는 커피 한잔의 여유 즐기셨나요?, [교육] 초등 받아쓰기 연습 재미있게 하는 꿀팁 있을까요?, [계절] 날씨가 더워졌는데 벌써 반팔 입혀 보내시나요?, [건강] 아이들 치아 관리 양치질 전쟁 평화롭게 끝내는 법, [질문] 아이 생일 파티 집에서 하시나요 키즈카페 가시나요?, [공감] 아이가 그려준 엄마 아빠 얼굴 보고 빵 터졌던 경험, [정보] 우리 동네 소아과 주말 진료하는 곳 공유해요, [안전] 킥보드 탈 때 헬멧 꼭 씌우시나요? 안전 교육 필수!, [성장] 일찍 자야 키 큰다고 하는데 아이들 몇 시에 재우세요?, [소통] 아이가 태권도 관장님 좋다고 이야기 많이 하나요?, [날씨] 미세먼지 나쁨인 날 집에서 할 수 있는 에너지 발산 놀이, [교육] 독서 습관 들이기 거실을 서재로 바꿔보신 분 계신가요?, [자랑] 어버이날 아이에게 받은 카네이션 편지 감동이네요, [정보] 아이들 핸드폰 사용 시간 하루에 얼마나 허용하시나요?, [주말] 캠핑장 예약 전쟁! 아이랑 가기 좋은 캠핑장 추천해주세요, [습관] 아침밥 뚝딱 잘 먹는 아이들 비결이 궁금합니다, [음식] 맵지 않은 떡볶이 레시피 아이들이 정말 좋아해요, [심리] 아이가 친구랑 싸우고 왔을 때 어떻게 위로해주시나요?, [이슈] 요즘 유행하는 장난감 사달라고 조르는데 다 사주시나요?, [계절] 장마철 눅눅한 집안 관리와 아이 건강 챙기기, [응원] 일과 육아 병행하는 워킹맘 학부모님들 힘내세요!, [야식] 치킨 vs 피자 아이들이 더 좋아하는 메뉴는?, [질문] 아이 용돈 얼마씩 주시나요? 경제 교육 궁금해요, [단상] 오늘도 아이들 행복한 웃음소리에 피로가 싹 풀리네요"
        )
        
        default_cafe_topics_str = default_band_topics_str # 카페/밴드 동일 사용

        blog_topics = ft.TextField(
            label="블로그 주제 목록",
            hint_text="블로그 자동 작성에 사용될 주제들을 쉼표(,)로 구분하여 입력하세요.",
            multiline=True,
            min_lines=3,
            max_lines=5,
            value=self.settings.get('blog_topics', default_blog_topics_str)
        )

        band_topics = ft.TextField(
            label="밴드 주제 목록",
            hint_text="밴드 자동 포스팅에 사용될 주제들을 쉼표(,)로 구분하여 입력하세요.",
            multiline=True,
            min_lines=3,
            max_lines=5,
            value=self.settings.get('band_topics', default_band_topics_str)
        )

        cafe_topics = ft.TextField(
            label="카페 주제 목록",
            hint_text="카페 자동 포스팅에 사용될 주제들을 쉼표(,)로 구분하여 입력하세요.",
            multiline=True,
            min_lines=3,
            max_lines=5,
            value=self.settings.get('cafe_topics', default_cafe_topics_str)
        )

        blog_slogan = ft.TextField(
            label="블로그 마지막 슬로건",
            hint_text="블로그 글 마지막 슬로건",
            multiline=True, min_lines=2, max_lines=4,
            on_blur=lambda e: _save_user_setting_individual('blog_slogan', e.control.value)
        )
        cafe_slogan = ft.TextField(
            label="카페 마지막 슬로건",
            hint_text="카페 글 마지막 슬로건",
            multiline=True, min_lines=2, max_lines=4,
            on_blur=lambda e: _save_user_setting_individual('cafe_slogan', e.control.value)
        )
        band_slogan = ft.TextField(
            label="밴드 마지막 슬로건",
            hint_text="밴드 글 마지막 슬로건",
            multiline=True, min_lines=2, max_lines=4,
            on_blur=lambda e: _save_user_setting_individual('band_slogan', e.control.value)
        )

        # 본문 첫 문장 설정 필드 추가
        blog_first_sentence = ft.TextField(
            label="블로그 본문 첫 문장",
            hint_text="블로그 포스팅 첫 문장 (예: 안녕하세요...)",
            multiline=True, min_lines=2, max_lines=3,
            on_blur=lambda e: _save_user_setting_individual('blog_first_sentence', e.control.value)
        )
        cafe_first_sentence = ft.TextField(
            label="카페 본문 첫 문장",
            hint_text="카페 포스팅 첫 문장",
            multiline=True, min_lines=2, max_lines=3,
            on_blur=lambda e: _save_user_setting_individual('cafe_first_sentence', e.control.value)
        )
        band_first_sentence = ft.TextField(
            label="밴드 본문 첫 문장",
            hint_text="밴드 포스팅 첫 문장",
            multiline=True, min_lines=2, max_lines=3,
            on_blur=lambda e: _save_user_setting_individual('band_first_sentence', e.control.value)
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
                    "weather_location": weather_location.value,
                    "kma_api_key": kma_api_key.value,
                    "kakao_url": kakao_url.value,
                    "blog_tags": blog_tags.value,
                    "blog_topics": blog_topics.value,
                    "band_topics": band_topics.value,
                    "cafe_topics": cafe_topics.value,
                    "blog_sheet_url": self.blog_sheet_url.value,
                    "cafe_sheet_url": self.cafe_sheet_url.value,
                    "band_sheet_url": self.band_sheet_url.value,
                    "blog_drive_folder": self.user_blog_drive_folder.value,
                    "cafe_drive_folder": self.user_cafe_drive_folder.value,
                    "video_title": video_title.value,
                    "video_info": video_info.value,
                    "video_tags": video_tags.value,
                    "blog_slogan": blog_slogan.value,
                    "cafe_slogan": cafe_slogan.value,
                    "band_slogan": band_slogan.value,
                    "blog_first_sentence": blog_first_sentence.value,
                    "cafe_first_sentence": cafe_first_sentence.value,
                    "band_first_sentence": band_first_sentence.value,
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # 🆕 블로그/카페 탭의 경로 필드와 동기화
                self.blog_drive_folder_path.value = self.user_blog_drive_folder.value
                self.cafe_drive_folder_path.value = self.user_cafe_drive_folder.value
                
                with open(os.path.join(self._get_app_data_dir(), 'config', 'user_settings.txt'), 'w', encoding='utf-8') as f:
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

        def _save_user_setting_individual(key, value):
            """사용자 설정 개별 항목 자동 저장 (on_blur 용)"""
            try:
                user_settings_path = os.path.join(self._get_app_data_dir(), 'config', 'user_settings.txt')
                settings = {}
                if os.path.exists(user_settings_path):
                    with open(user_settings_path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                
                # 값 변경 시만 저장
                if settings.get(key) != value:
                    settings[key] = value
                    settings["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with open(user_settings_path, 'w', encoding='utf-8') as f:
                        json.dump(settings, f, ensure_ascii=False, indent=2)
                    print(f"✅ 사용자 설정 자동 저장됨: {key} -> {value}")
            except Exception as ex:
                print(f"⚠️ 사용자 설정 개별 저장 오류: {ex}")

        def load_user_settings():
            try:
                # 🆕 글로벌 설정 경로 사용
                user_settings_path = os.path.join(self._get_app_data_dir(), 'config', 'user_settings.txt')
                if os.path.exists(user_settings_path):
                    with open(user_settings_path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                        dojang_name.value = settings.get('dojang_name', '')
                        address.value = settings.get('address', '')
                        phone.value = settings.get('phone', '')
                        blog_url.value = settings.get('blog_url', '')
                        naver_id.value = settings.get('naver_id', '')
                        naver_pw.value = settings.get('naver_pw', '')
                        weather_location.value = settings.get('weather_location', '')
                        kma_api_key.value = settings.get('kma_api_key', '')
                        kakao_url.value = settings.get('kakao_url', '')
                        blog_tags.value = settings.get('blog_tags', '')
                        blog_topics.value = settings.get('blog_topics', '')
                        band_topics.value = settings.get('band_topics', '')
                        cafe_topics.value = settings.get('cafe_topics', '')
                        # 🆕 시트 URL 및 드라이브 폴더는 app_settings.json(self.settings)에서 별도로 관리하므로
                        # 여기서 덮어쓰지 않도록 주석 처리하거나 제거합니다.
                        # self.blog_sheet_url.value = settings.get('blog_sheet_url', self.settings.get('blog_sheet_url', ''))
                        # self.cafe_sheet_url.value = settings.get('cafe_sheet_url', self.settings.get('cafe_sheet_url', ''))
                        # self.band_sheet_url.value = settings.get('band_sheet_url', self.settings.get('band_sheet_url', ''))
                        
                        # 최신 app_settings.json 값을 보장하기 위해 self.settings 기준으로 UI를 동기화합니다.
                        self.blog_sheet_url.value = self.settings.get('blog_sheet_url', '')
                        self.cafe_sheet_url.value = self.settings.get('cafe_sheet_url', '')
                        self.band_sheet_url.value = self.settings.get('band_sheet_url', '')
                        
                        self.user_blog_drive_folder.value = self.settings.get('blog_drive_folder', '')
                        self.user_cafe_drive_folder.value = self.settings.get('cafe_drive_folder', '')

                        # 🆕 블로그/카페 탭의 경로 필드와 실시간 동기화
                        self.blog_drive_folder_path.value = self.user_blog_drive_folder.value
                        self.cafe_drive_folder_path.value = self.user_cafe_drive_folder.value
                        
                        blog_slogan.value = settings.get('blog_slogan', settings.get('slogan', ''))
                        cafe_slogan.value = settings.get('cafe_slogan', '')
                        band_slogan.value = settings.get('band_slogan', '')
                        blog_first_sentence.value = settings.get('blog_first_sentence', settings.get('first_sentence', ''))
                        cafe_first_sentence.value = settings.get('cafe_first_sentence', '')
                        band_first_sentence.value = settings.get('band_first_sentence', '')
                        reply_instruction.value = settings.get('reply_instruction', '- 댓글 내용에 공감하며 감사 표현\n- 15~30자 이내로 짧게 작성\n- 이모지 1개만 포함')
                        default_reply.value = settings.get('default_reply', '감사합니다😊,좋은 말씀 감사해요💕,응원 감사합니다🙏,행복한 하루 되세요✨,방문 감사합니다🌻')
                        video_title.value = settings.get('video_title', '네이버뉴스')
                        video_info.value = settings.get('video_info', '네이버뉴스')
                        video_tags.value = settings.get('video_tags', '양양합기도, 등등')
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
                # 🆕 글로벌 설정 경로 사용
                timer_settings_path = os.path.join(self._get_app_data_dir(), 'config', 'timer_settings.json')
                os.makedirs(os.path.dirname(timer_settings_path), exist_ok=True)
                with open(timer_settings_path, 'w', encoding='utf-8') as f:
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
                # 🆕 글로벌 설정 경로 사용
                timer_settings_path = os.path.join(self._get_app_data_dir(), 'config', 'timer_settings.json')
                if os.path.exists(timer_settings_path):
                    with open(timer_settings_path, 'r', encoding='utf-8') as f:
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
                # 🆕 글로벌 설정 경로 사용
                usage_file = os.path.join(self._get_app_data_dir(), 'config', 'usage_stats.json')
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
                # 🆕 글로벌 설정 경로 사용
                usage_file = os.path.join(self._get_app_data_dir(), 'config', 'usage_stats.json')
                
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

        topic_input = ft.TextField(
            label="🥋 오늘의 블로그 주제 (또는 키워드)",
            hint_text="글의 주제를 입력하거나 아래 '전송' 버튼을 누르세요...",
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
            label="🥋 오늘의 블로그 제목",
            hint_text="블로그 포스트 제목을 입력하세요...",
            multiline=True,
            min_lines=2,
            max_lines=3,
            expand=False,
            border_radius=10,
            border_color=ft.Colors.BLUE_400,
            focused_border_color=ft.Colors.BLUE_700,
            prefix_icon=ft.Icons.AUTO_AWESOME,
            on_change=on_title_changed
        )

        content_input = ft.TextField(
            label="📝 오늘의 블로그 본문 (미리보기)",
            hint_text="블로그 포스트 내용을 입력하세요...",
            multiline=True,
            min_lines=6,
            max_lines=15,
            expand=False,
            border_radius=15,
            border_color=ft.Colors.GREY_400,
            focused_border_color=ft.Colors.BLUE_700,
            bgcolor=ft.Colors.GREY_50,
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
                self.current_tags = result.get("tags", [])
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

            # 로그인 상태 확인 및 세션 복구
            print(f"🔍 브라우저 세션 확인 중...")
            
            # 드라이버가 없거나 죽었으면 새로 생성 (고정 프로필 사용하므로 자동 로그인 됨)
            if not hasattr(self, 'browser_driver') or not self.browser_driver or not self.is_driver_alive(self.browser_driver):
                print("⚠️ 유효한 브라우저 세션이 없습니다. 고정 프로필로 복구 시도...")
                try:
                    self.browser_driver = self.get_or_create_driver()
                    
                    if self.browser_driver:
                        # 네이버 블로그 메인으로 이동하여 로그인 상태 확인 (필요 시)
                        self.browser_driver.get('https://blog.naver.com')
                        time.sleep(1)
                        print("✅ 브라우저 세션 복구 완료")
                    else:
                        raise Exception("브라우저 드라이버 생성 실패")
                        
                except Exception as e:
                    print(f"❌ 브라우저 세션 복구 실패: {str(e)}")
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"브라우저 실행 오류: {str(e)}"),
                        bgcolor=ft.Colors.RED
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

                # 원본 내용을 모바일 친화적으로 포맷팅 및 오리지널 단순 결합 복원
                raw_title = title_input.value
                # 💡 [모바일 가독성 줄바꿈 적용]
                raw_content = format_content_for_mobile(content_input.value)
                
                # 1. 첫문장(머리말) 결합
                blog_intro = self.settings.get('blog_first_sentence', '').strip()
                if blog_intro:
                    # 첫문장 보호를 위해 단일 줄바꿈(\n)으로 지능형 연결
                    formatted_content = f"{blog_intro}\n{raw_content}"
                else:
                    formatted_content = raw_content
                
                # 2. 슬로건 결합
                blog_slogan = self.settings.get('blog_slogan', '').strip()
                if blog_slogan and blog_slogan not in formatted_content:
                    formatted_content = f"{formatted_content}\n\n{blog_slogan}"
                
                # 3. 태그 병합 (고정 15개 + AI 15개 = 30개 규칙 보장)
                gpt_tags = getattr(self, 'current_tags', [])
                if isinstance(gpt_tags, str):
                    gpt_tags = [t.strip() for t in gpt_tags.split(',') if t.strip()]
                    
                user_tags_str = self.settings.get('blog_tags', '')
                user_tags = [tag.strip() for tag in user_tags_str.split(',') if tag.strip()] if user_tags_str else []
                
                # 중복을 방지하며 최대 30개 조율
                seen_tags = set()
                merged_tags = []
                for t in user_tags[:15]:
                    if t and t not in seen_tags:
                        merged_tags.append(t)
                        seen_tags.add(t)
                for t in gpt_tags[:15]:
                    if t and t not in seen_tags and len(merged_tags) < 30:
                        merged_tags.append(t)
                        seen_tags.add(t)
                
                # 임시 파일에 내용 저장 (AppData 기반으로 변경 — 퍼미션 에러 방지)
                today = datetime.now().strftime("%Y-%m-%d")
                today_dir = os.path.join(self._get_app_data_dir(), 'data', today)
                os.makedirs(today_dir, exist_ok=True)
                
                # 윈도우 파일명 사용 불가능 문자 제거 (? 등)
                raw_title = title_input.value
                import re
                clean_title = re.sub(r'[\/:*?"<>|]', '', raw_title).strip()
                if not clean_title:
                    clean_title = "제목없음_" + datetime.now().strftime("%H%M%S")
                
                file_path = os.path.join(today_dir, f"{clean_title}.txt")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"제목: {raw_title}\n\n{formatted_content}")

                try:
                    # 기존 naver_blog_auto.py 시스템 활용
                    dlg.content.controls[0].value = "네이버 블로그 자동화 시스템 초기화 중..."
                    page.update()
                    
                    # naver_blog_auto.py import
                    from naver_blog_auto import NaverBlogAutomation
                    
                    # --- Phase 2: 이미지 삽입 모드 처리 ---
                    image_mode = self.blog_image_mode_dropdown.value
                    custom_images_folder = None
                    images_available = False
                    
                    if image_mode == "off":
                        print("🚫 이미지 삽입 모드: 사용 안함")
                    elif image_mode == "manual":
                        print("📂 이미지 삽입 모드: 수동 지정 폴더")
                        folder_path = self.blog_manual_folder_path.value
                        if folder_path and os.path.exists(folder_path):
                            custom_images_folder = folder_path
                            images_available = True
                        else:
                            print(f"⚠️ 수동 폴더를 찾을 수 없습니다: {folder_path}")
                    else: # "auto"
                        print("🤖 이미지 삽입 모드: 자동 (순차 폴더)")
                        try:
                            folder_path = self.get_smart_image_folder(raw_title)
                            if folder_path and os.path.exists(folder_path):
                                custom_images_folder = folder_path
                                images_available = True
                        except Exception as img_folder_err:
                            print(f"이미지 폴더 선정 중 오류: {img_folder_err}")
                    
                    # 이번 포스팅에 이미지 삽입 여부 결정 (체크박스 ON + 실제 이미지 존재)
                    auto_image_enabled = auto_image_checkbox.value and images_available
                    
                    # 자동화 인스턴스 생성 (기존 브라우저 세션 활용)
                     # 🆕 네이버 ID 설정 가져오기
                    naver_id = self.settings.get('naver_id', '')
                    
                    insert_position = self.blog_media_position_dropdown.value
                    
                    blog_auto = NaverBlogAutomation(
                        auto_mode=auto_image_enabled,  # 포스트 단위 이미지 사용 여부
                        image_insert_mode=insert_position,  # 'random' 또는 'end'
                        use_stickers=False,
                        custom_images_folder=custom_images_folder,  # 포스트별 단일 폴더 고정
                        naver_id=naver_id, # 🆕 네이버 ID 전달
                        media_position=self.blog_media_position_dropdown.value,
                        media_order=self.blog_media_order_dropdown.value
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
                        blog_auto.image_inserter.media_position = self.blog_media_position_dropdown.value
                        blog_auto.image_inserter.media_order = self.blog_media_order_dropdown.value
                        print("✅ 이미지 삽입 핸들러 수동 초기화 완료")
                    else:
                        print("ℹ️ 이미지 자동 삽입이 비활성화되어 있습니다.")
                        blog_auto.image_inserter = None
                    
                    dlg.content.controls[0].value = "블로그 포스팅 작성 중..."
                    page.update()
                    
                    tags = merged_tags
                    
                    # 🆕 태그 완료 후 자동 발행 로직 적용 (체크 시 자동 발행, 해제 시 발행 직전 대기)
                    blog_auto.skip_final_publish = not auto_final_publish_checkbox.value
                    print(f"📊 최종 발행 설정: {'자동 발행' if not blog_auto.skip_final_publish else '발행 전 대기'}")
                    
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
                        auto_topic_checkbox, # 🆕 자동 주제 체크박스 추가
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
                
                # 📊 블로그 전용 외부 연동 섹션 (관장님 커스텀 요청 반영)
                ft.Container(
                    content=ft.Column([
                        ft.Text("📊 블로그 전용 외부 연동", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                        self.blog_sheet_url, # 블로그 전용 시트 링크 (독립)
                        ft.Row([
                            self.user_blog_drive_folder,
                            ft.IconButton(
                                icon=ft.Icons.FOLDER_OPEN,
                                icon_color=ft.Colors.BLUE_700,
                                tooltip="이미지 감지 폴더 선택",
                                on_click=lambda e: self._open_folder_picker_for(self.user_blog_drive_folder)
                            )
                        ], spacing=10),
                    ], spacing=10),
                    padding=15,
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=10,
                    border=ft.border.all(1, ft.Colors.BLUE_200)
                ),
                
                # 🖼️ 이미지 및 발행 옵션 섹션
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            auto_image_checkbox,
                            ft.Text("🖼️ 이미지 자동 모드", size=14, weight=ft.FontWeight.BOLD)
                        ], spacing=5),
                        ft.Row([
                            self.blog_image_mode_dropdown,
                            self.blog_media_position_dropdown,
                            self.blog_media_order_dropdown,
                        ], spacing=10),
                        blog_image_help_text,
                        self.blog_manual_settings_row,
                        ft.Row([
                            ft.ElevatedButton(
                                "🔄 로컬 사진 폴더 스마트 스캔 (AI 학습)",
                                icon=ft.Icons.SYNC,
                                on_click=self._on_smart_image_scan_click,
                                bgcolor=ft.Colors.BLUE_700,
                                color=ft.Colors.WHITE
                            ),
                            ft.Text("💡 새 폴더 생성 시 스캔하여 키워드를 AI에게 자동 학습시킵니다.", size=11, color=ft.Colors.GREY_600)
                        ], spacing=10),
                        ft.Divider(height=1, color=ft.Colors.GREY_300),
                        auto_final_publish_checkbox, # 🆕 태그 완료 후 자동 발행
                        auto_final_publish_help_text,
                    ], spacing=10),
                    padding=15,
                    bgcolor=ft.Colors.GREY_50,
                    border_radius=10,
                    border=ft.border.all(1, ft.Colors.GREY_200)
                ),
                
                # 📱 드라이브 감시 독립 섹션 (폰 포스팅 전용 - 스케줄러/타이머와 분리)
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.PHONE_ANDROID, color=ft.Colors.GREEN_700),
                            ft.Text("📂 드라이브 감시 (폰 포스팅)", size=14, weight=ft.FontWeight.BOLD),
                            self.blog_drive_watcher_status,
                        ], spacing=8),
                        ft.Text(
                            "폰에서 드라이브 폴더에 사진을 전송하면 자동으로 포스팅됩니다. 스케줄러/타이머와 독립적으로 운영됩니다.",
                            size=11, color=ft.Colors.GREY_600, italic=True
                        ),
                        self.blog_drive_settings_row,
                    ], spacing=8),
                    padding=15,
                    bgcolor=ft.Colors.GREEN_50,
                    border_radius=10,
                    border=ft.border.all(1, ft.Colors.GREEN_200)
                ),
                
                upload_button,
                status_text
            ],
            spacing=15,
            expand=True
        )

        # GPT 설정 탭
        gpt_settings_tab = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("🌟 블로그 글쓰기 상세 제어 옵션 (블로그 전문가 연동)", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                    ft.Row([
                        self.blog_persona_dropdown,
                        self.blog_style_dropdown,
                        self.blog_theme_dropdown,
                    ], spacing=10),
                    self.blog_hometip_checkbox,
                    ft.Divider(height=1, color=ft.Colors.GREY_300),
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
                            ft.Row([api_key_field, openai_help_btn], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Row([gemini_api_key_field, gemini_help_btn], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Row([brave_api_key_field, brave_help_btn], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
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
                    # '외부 데이터 및 드라이브 연동' 공통 섹션 삭제됨 (각 탭에서 개별 관리)
                    ft.Text("🏢 체육관 기본 정보", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                    
                    dojang_name,
                    address,
                    phone,
                    blog_url,
                    naver_id,
                    naver_pw,
                    weather_location,
                    ft.Row([kma_api_key, kma_help_btn], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    kakao_url,
                    blog_tags,
                    blog_topics,
                    cafe_topics,
                    
                    ft.Divider(),
                    ft.Text("🎞️ 동영상 업로드 설정", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_700),
                    video_title,
                    video_info,
                    video_tags,
                    
                    ft.Divider(),
                    ft.Text("📊 밴드 주제 설정", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700),
                    band_topics,
                    ft.Divider(),

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

        # 메인 컨텐츠 탭 (상단 버튼 고정형으로 구조 변경)
        main_content_tab = ft.Column(
            controls=[
                login_button,  # 📍 상단 고정 영역 (로그인/시작/중지 버튼)
                ft.Column(  # 📜 스크롤 가능한 본문 영역
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                    controls=[
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
                    ]
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
                "neighbor": "이웃방문",
                "wait": "대기 작업"
            }
            # 🆕 플랫폼 이름 매핑 (더 읽기 좋게 표시)
            platform_map = {
                "blog": "블로그",
                "band": "밴드",
                "cafe": "카페",
                "blog_reply": "블로그 답글",
                "band_reply": "밴드 답글",
                "neighbor_visit": "이웃방문",
                "idle": "대기",
                "wait": "⏳ 대기"
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
                "댓글답글": 5,
                "wait": 0 # 가변적
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
                
                # ⏳ 대기 작업 시간 계산
                if task.platform == 'wait' and task.data and 'target_time' in task.data:
                    try:
                        target_time_str = task.data['target_time']
                        target_h, target_m = map(int, target_time_str.split(':'))
                        estimated_start_time = current_time + timedelta(minutes=cumulative_minutes)
                        target_dt = estimated_start_time.replace(hour=target_h, minute=target_m, second=0)
                        
                        # 만약 타겟 시간이 시작 시간보다 미래라면 차이를 대기 시간으로
                        if target_dt > estimated_start_time:
                            diff = (target_dt - estimated_start_time).total_seconds() / 60
                            estimated_minutes = int(diff)
                        else:
                            estimated_minutes = 0
                    except:
                        estimated_minutes = 0

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
                elif task.platform == 'wait' and task.data and 'target_time' in task.data:
                    detail_text = f"⏳ {task.data['target_time']}까지 대기"
                
                # 상태에 따른 색상 및 아이콘 설정
                if is_current:
                    status_color = ft.Colors.BLUE
                    bg_color = ft.Colors.BLUE_100
                    border_color = ft.Colors.BLUE
                    
                    if task.last_status == 'waiting':
                        status_icon = ft.Icons.HOURGLASS_TOP
                        status_text = "⏳ 대기 중"
                        status_color = ft.Colors.ORANGE
                        bg_color = ft.Colors.ORANGE_50
                    else:
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

        # ========== 🆕 대기 작업 (Wait Task) 설정 UI ==========
        wait_task_time = ft.TextField(label="대기 시간", value="09:00", width=100, hint_text="HH:MM")
        
        def add_wait_task(e):
            """대기 작업 추가"""
            target_time = wait_task_time.value
            
            # 시간 검증
            import re
            if not re.match(r"^\d{1,2}:\d{2}$", target_time):
                page.snack_bar = ft.SnackBar(content=ft.Text("시간 형식이 올바르지 않습니다 (HH:MM)"))
                page.snack_bar.open = True
                page.update()
                return
            
            # 스케줄러에 추가
            self.scheduler.add_task(
                platform='wait',
                task_type='regular',
                data={'target_time': target_time}
            )
            
            update_scheduler_ui()
            page.snack_bar = ft.SnackBar(content=ft.Text(f"⏳ 대기 작업 추가됨: {target_time}까지 대기"), bgcolor=ft.Colors.BLUE)
            page.snack_bar.open = True
            page.update()

        wait_task_section = ft.Container(
            content=ft.Column([
                ft.Text("⏳ 대기 작업 추가", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("🎵 플레이리스트 실행 중 지정된 시간까지 대기합니다. (예: 09:00까지 대기 후 다음 작업 실행)", size=11, color=ft.Colors.GREY_600),
                ft.Row([
                    wait_task_time,
                    ft.ElevatedButton("작업 추가", icon=ft.Icons.ADD_ALARM, on_click=add_wait_task, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
                ], spacing=10),
            ], spacing=8),
            padding=15,
            bgcolor=ft.Colors.BLUE_50,
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
                # 🆕 대기 작업 추가
                ft.ExpansionTile(
                    title=ft.Text("⏳ 특정 시간 대기 작업 (클릭하여 펼치기)", size=14, weight=ft.FontWeight.BOLD),
                    controls=[wait_task_section],
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
        
        band_url_help_btn = ft.IconButton(
            icon=ft.Icons.HELP_OUTLINE,
            tooltip="네이버 밴드 URL 가이드 보기",
            on_click=lambda _: self._open_guide("네이버-밴드-url")
        )
        band_title_input = ft.TextField(label="제목 (옵션)", expand=True)
        band_content_input = ft.TextField(label="내용", multiline=True, min_lines=6, max_lines=15, expand=True)
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
                
                # 🟢 밴드 파이프라인 관통시켜 유형 1 물리적 조립 수행 (Flet UI 미리보기용)
                if result and result.get('content'):
                    from modules.pipelines.band_pipeline import BandPipeline
                    gpt_tags = result.get('tags', [])
                    ai_tags_str = ",".join(gpt_tags) if isinstance(gpt_tags, list) else str(gpt_tags)
                    
                    formatted_content, merged_tags = BandPipeline.process(
                        content=result['content'],
                        ai_tags=ai_tags_str,
                        app_data_dir=self._get_app_data_dir(),
                        mode='band', # 유형 1 명시
                        fallback_settings=self.settings
                    )
                    band_title_input.value = result.get('title', '')
                    band_content_input.value = formatted_content
                
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
                        base_dir=self.base_dir,
                        instruction=self.settings.get('reply_instruction')
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
                    print(f"[Step 1] [BandManualPost] 수동 주제 포스팅 시작 (상태: 시도) - 카테고리: {category}, 주제: {topic}")
                    driver = self.get_or_create_driver()
                    band_url = self.settings.get('band_url', '')
                    
                    if not band_url:
                        print("[Step 1] [BandManualPost] 밴드 URL 미설정 오류 (상태: 실패)")
                        return
                    print("[Step 2] [BandManualPost] 밴드 드라이버 획득 완료 (상태: 성공)")
                    
                    # 이미지 수집 (수동 업로드 폴더에서)
                    image_paths = []
                    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
                    video_exts = {".mp4", ".mov", ".avi", ".mkv"}
                    
                    if folder_path and os.path.exists(folder_path):
                        for f in sorted(os.listdir(folder_path)):
                            ext = os.path.splitext(f)[1].lower()
                            if ext in valid_exts or ext in video_exts:
                                image_paths.append(os.path.join(folder_path, f))
                        print(f"[Step 3] [BandManualPost] 수동 폴더 이미지 수집 완료 (상태: 성공) - {len(image_paths)}개 발견")
                    
                    if not image_paths:
                        print("[Step 3] [BandManualPost] 이미지 수집 실패 (상태: 실패) - 폴더가 비어있거나 없음")
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
                    print(f"[Step 4] [BandManualPost] AI 글 내용 생성 시작 (상태: 시도) - 토픽: {full_topic}")
                    
                    # 🟢 수동주제포스팅 전용 지침 사용 (사용자 입력 주제 기반)
                    result = self.gpt_handler.generate_platform_content(
                        full_topic,
                        platform='manual_topic',  # 수동 주제 전용 플랫폼 사용
                        task_type='regular'
                    )
                    
                    if not result or not result.get('content'):
                        print("[Step 4] [BandManualPost] AI 글 내용 생성 실패 (상태: 실패)")
                        # 실패 시 이미지 이동
                        fail_folder = get_manual_fail_folder()
                        moved = move_images_to_folder(image_paths, fail_folder)
                        print(f"📦 실패 폴더로 이미지 {moved}개 이동")
                        return
                    print(f"[Step 4] [BandManualPost] AI 글 내용 생성 완료 (상태: 성공) - 모델: {result.get('model', '-')}")
                    
                    content = result.get('content', '')
                    gpt_tags = result.get('tags', [])
                    ai_tags_str = ",".join(gpt_tags) if isinstance(gpt_tags, list) else str(gpt_tags)
                    
                    # 🟢 밴드 파이프라인 관통시켜 유형 2 물리적 조립 수행 (모바일 가독성 최적화)
                    print("[Step 5] [BandManualPost] 밴드 파이프라인 관통 조립 시작 (상태: 시도)")
                    from modules.pipelines.band_pipeline import BandPipeline
                    formatted_content, merged_tags = BandPipeline.process(
                        content=content,
                        ai_tags=ai_tags_str,
                        app_data_dir=self._get_app_data_dir(),
                        mode='manual_topic',  # 유형 2 명시
                        fallback_settings=self.settings,
                        folder_name=category  # category 명을 folder_name으로 전달
                    )
                    print("[Step 5] [BandManualPost] 밴드 파이프라인 관통 조립 완료 (상태: 성공)")
                    
                    # 밴드에 포스팅
                    print("[Step 6] [BandManualPost] 네이버 밴드 수동 업로드 포스팅 시작 (상태: 시도)")
                    from naver_band_auto import NaverBandAutomation
                    band_auto = NaverBandAutomation(driver)
                    success = band_auto.post_to_band(
                        band_url=band_url,
                        content=formatted_content,
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
                ft.Row([band_url_input, band_url_help_btn], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
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
                        
                        # 수련계획표 URL (밴드 전용 독립 키 사용)
                        self.band_sheet_url,
                        ft.Text("💡 선택사항: 오늘 날짜의 수련내용을 자동으로 가져와 AI 글 주제로 사용합니다. 없으면 기본 주제 사용.", size=11, color=ft.Colors.GREY_600),
                        
                        # 상위 감시 폴더 (하위 폴더 자동 스캔)
                        ft.Text("📁 감시 폴더 설정:", size=14, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.TextField(
                                label="상위 폴더 경로 (하위 폴더들을 자동 감지)",
                                hint_text="/Users/.../Google Drive/수련사진및영상",
                                value=self.settings.get('drive_parent_folder', ''),
                                on_change=lambda e: self._save_setting('drive_parent_folder', e.control.value),
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
                        ft.Text("💡 AI가 이 종목에 맞는 용어로 글을 작성합니다. (예: 합기도 → 낙법, 발차기 / 태권도 → 품새, 격파)", size=11, color=ft.Colors.GREY_600),
                        
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
        
        cafe_url_help_btn = ft.IconButton(
            icon=ft.Icons.HELP_OUTLINE,
            tooltip="네이버 카페 URL 가이드 보기",
            on_click=lambda _: self._open_guide("네이버-카페-url-및-메뉴-id")
        )

        cafe_menu_input = ft.TextField(
            label="메뉴 ID (menuid)", 
            value=self.settings.get('cafe_menu_id', ''), 
            hint_text="카페 게시판 클릭 시 주소창의 menuId=숫자 부분 입력",
            expand=True,
            on_blur=on_cafe_menu_change
        )

        cafe_menu_help_btn = ft.IconButton(
            icon=ft.Icons.HELP_OUTLINE,
            tooltip="카페 메뉴 ID 가이드 보기",
            on_click=lambda _: self._open_guide("네이버-카페-url-및-메뉴-id")
        )
        cafe_title_input = ft.TextField(label="제목", expand=True)
        cafe_content_input = ft.TextField(label="내용", multiline=True, min_lines=6, max_lines=15, expand=True)
        
        # ☕ 카페 이미지 삽입 모드 설정 (체크박스 -> 드롭다운 업그레이드)
        def on_cafe_image_mode_change(e):
            save_app_settings(e)
            val = e.control.value
            self.cafe_drive_settings_row.visible = (val == "detect")
            if hasattr(self, 'cafe_manual_settings_row'):
                self.cafe_manual_settings_row.visible = (val == "manual")
            self.cafe_drive_settings_row.update()
            if hasattr(self, 'cafe_manual_settings_row'):
                self.cafe_manual_settings_row.update()
            self._toggle_cafe_drive_watcher_ui()
            
        self.cafe_image_mode_dropdown = ft.Dropdown(
            label="이미지 폴더 소스",
            options=[
                ft.dropdown.Option("auto", "자동 (Auto)"),
                ft.dropdown.Option("manual", "수동 (Manual)"),
                ft.dropdown.Option("detect", "드라이브 감지 (Detect)"),
                ft.dropdown.Option("off", "사용 안함 (Off)"),
            ],
            value="auto",
            width=200,
            on_change=on_cafe_image_mode_change
        )
        
        self.cafe_image_position_dropdown = ft.Dropdown(
            label="삽입 위치",
            options=[
                ft.dropdown.Option("random", "문단 사이 분산 삽입"),
                ft.dropdown.Option("end", "맨 아래 일괄 삽입"),
            ],
            value=self.settings.get('cafe_image_position', 'random'),
            width=180,
            on_change=lambda e: self._save_setting('cafe_image_position', e.control.value)
        )
        
        # 📂 카페 구글 드라이브 감지 설정
        self.cafe_drive_folder_path = ft.TextField(
            label="감시할 드라이브 폴더 경로",
            hint_text="예: /Users/username/Google Drive/CafeImages",
            value=self.settings.get('cafe_drive_folder', ''),
            expand=True,
            on_change=on_cafe_drive_folder_change,
            on_blur=lambda e: self._save_setting('cafe_drive_folder', self.cafe_drive_folder_path.value)
        )
        
        self.cafe_drive_watcher_status = ft.Text("상태: 정지됨", color=ft.Colors.GREY_600)
        self.cafe_drive_watcher_btn = ft.ElevatedButton(
            "실시간 감시 시작",
            icon=ft.Icons.PLAY_ARROW,
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.GREEN_700,
            on_click=self._toggle_cafe_drive_watcher
        )

        self.cafe_drive_settings_row = ft.Row([
            self.cafe_drive_folder_path,
            ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=lambda e: self._open_folder_picker_for(self.cafe_drive_folder_path)),
            self.cafe_drive_watcher_btn
        ], visible=False)
        
        self.cafe_manual_settings_row = ft.Row([
            self.cafe_manual_folder_path,
            ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=lambda e: self._open_folder_picker_for(self.cafe_manual_folder_path)),
        ], visible=False)

        cafe_image_help_text = ft.Text(
            "자동: 셔플 후 삽입 | 수동: 선택 창 오픈 | 드라이브 감지: 특정 폴더 실시간 감시 포스팅",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )
        
        def post_to_cafe_click(e):
            if not cafe_url_input.value or not cafe_menu_input.value or not cafe_content_input.value:
                page.snack_bar = ft.SnackBar(content=ft.Text("카페 URL, 메뉴 ID, 내용을 모두 입력해주세요."))
                page.snack_bar.open = True
                page.update()
                return
            
            # --- Phase 2: 이미지 삽입 모드 처리 ---
            image_mode = self.cafe_image_mode_dropdown.value
            images = []
            
            if image_mode == "off":
                print("🚫 카페 이미지 삽입 모드: 사용 안함")
            elif image_mode == "detect":
                print("🔍 카페 이미지 삽입 모드: 드라이브 감지 경로 사용")
                folder_path = self.cafe_drive_folder_path.value
                if folder_path and os.path.exists(folder_path):
                    # 해당 폴더에서 이미지 목록 가져오기
                    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
                    images = [
                        os.path.join(folder_path, f)
                        for f in os.listdir(folder_path)
                        if os.path.splitext(f)[1].lower() in valid_exts and not f.startswith('.')
                    ]
            elif image_mode == "manual":
                print("📂 카페 이미지 삽입 모드: 수동 지정 폴더")
                folder_path = self.cafe_manual_folder_path.value
                if folder_path and os.path.exists(folder_path):
                    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
                    images = [
                        os.path.join(folder_path, f)
                        for f in os.listdir(folder_path)
                        if os.path.splitext(f)[1].lower() in valid_exts and not f.startswith('.')
                    ]
                else:
                    print(f"⚠️ 카페 수동 풀더를 찾을 수 없습니다: {folder_path}")
            elif image_mode == "auto":
                print("🤖 카페 이미지 삽입 모드: 자동 (순차 폴더)")
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
                ft.Row([cafe_url_input, cafe_url_help_btn], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([cafe_menu_input, cafe_menu_help_btn], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                cafe_title_input,
                cafe_content_input,
                
                # 🆕 카페 전용 외부 연동 설정 (Phase 2 요청 사항)
                ft.Container(
                    content=ft.Column([
                        ft.Text("📊 카페 전용 외부 연동", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BROWN_700),
                        self.cafe_sheet_url, # 카페 탭 전용 인스턴스 사용
                        ft.Row([
                            self.user_cafe_drive_folder,
                            ft.IconButton(
                                icon=ft.Icons.FOLDER_OPEN,
                                icon_color=ft.Colors.BROWN_700,
                                tooltip="이미지 감지 폴더 선택",
                                on_click=lambda e: self._open_folder_picker_for(self.user_cafe_drive_folder)
                            )
                        ], spacing=10),
                    ], spacing=10),
                    padding=10,
                    bgcolor=ft.Colors.BROWN_50,
                    border_radius=8,
                    border=ft.border.all(1, ft.Colors.BROWN_200)
                ),
                
                ft.Row([
                    self.cafe_image_mode_dropdown,
                    self.cafe_image_position_dropdown,
                ], spacing=10),
                cafe_image_help_text,
                self.cafe_drive_settings_row,
                self.cafe_manual_settings_row,
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

        # 지역 마케팅 탭 생성
        marketing_settings_tab = self._create_marketing_tab()
        
        # 답글 관리 탭 생성 (New)
        reply_manager_tab = self._create_reply_manager_tab()

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
                    text="지역 마케팅",
                    icon=ft.Icons.STOREFRONT,  # 상점 아이콘 사용
                    content=marketing_settings_tab
                ),
                ft.Tab(
                    text="상담 관리", # New Tab
                    icon=ft.Icons.SUPPORT_AGENT,
                    content=reply_manager_tab
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
        
        # 로그 버튼 생성
        log_button = ft.IconButton(
            icon=ft.Icons.TERMINAL,
            tooltip="실시간 로그 보기 (개발자 모드)",
            on_click=lambda _: self._show_log_viewer(page),
            icon_color=ft.Colors.GREY_700
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
                
                # 오른쪽: 기능 버튼들 (로그, 업데이트)
                ft.Row([
                    log_button,
                    update_button
                ], spacing=5)
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
                    # 🆕 글로벌 설정 경로 사용
                    user_settings_path = get_user_settings_path()
                    if os.path.exists(user_settings_path):
                        with open(user_settings_path, 'r', encoding='utf-8') as f:
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
                remote_version, changelog, assets, release_info = updater.get_remote_version()
                
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
        """현재 버전 가져오기 (Robust)"""
        try:
            # 검색할 경로 목록 (우선순위 순)
            possible_paths = []
            
            # 1. 실행 파일/스크립트 기준 경로
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(sys.executable)
                possible_paths.append(os.path.join(exe_dir, 'version.json'))
                possible_paths.append(os.path.join(exe_dir, '..', 'Frameworks', 'version.json')) # macOS
                possible_paths.append(os.path.join(exe_dir, '_internal', 'version.json')) # PyInstaller onedir
            else:
                # 스크립트 실행 시
                script_dir = os.path.dirname(os.path.abspath(__file__))
                possible_paths.append(os.path.join(script_dir, 'version.json'))

            # 2. 현재 작업 디렉토리 기준 (개발 환경 등)
            possible_paths.append(os.path.join(os.getcwd(), 'version.json'))
            
            # 3. base_dir 기준 (앱 내부 설정 경로)
            if hasattr(self, 'base_dir'):
                possible_paths.append(os.path.join(self.base_dir, 'version.json'))

            print(f"🔍 버전 파일 검색 경로: {possible_paths}")

            for version_file in possible_paths:
                if os.path.exists(version_file):
                    try:
                        with open(version_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            version = data.get('version', '1.0.0')
                            if version != '1.0.0':
                                print(f"✅ 버전 파일 로드 성공: {version_file} (v{version})")
                                return version
                    except Exception as e:
                        print(f"⚠️ 버전 파일 읽기 실패 ({version_file}): {e}")
                        continue
            
            print("❌ 유효한 version.json을 찾을 수 없음, 기본값 1.0.0 사용")
            return '1.0.0'
        except Exception as e:
            print(f"❌ 버전 확인 중 오류 발생: {e}")
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
        # 🆕 UI 스레드 안전성을 위해 page.run_task 사용 (Windows 크래시 방지)
        async def update_process():
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
                
                # 원격 버전 확인 (네트워크 작업이므로 별도 스레드에서 비동기 실행)
                remote_version, changelog, assets, release_info = await asyncio.to_thread(updater.get_remote_version)
                
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
                
                # 확인 버튼 핸들러 (내부 함수)
                def perform_update_action(e):
                    confirm_dialog.open = False
                    page.update()
                    
                    # 🆕 업데이트 진행 및 파일 다운로드를 위한 비동기 태스크 시작
                    page.run_task(execute_update_task)

                # 실제 업데이트 실행 태스크
                async def execute_update_task():
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
                    
                    # 업데이트 실행 (다운로드 등 무거운 작업은 스레드로 분리)
                    success, message = await asyncio.to_thread(updater.check_and_update)
                    
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
                        
                        if is_built_app and sys.platform == 'win32':
                             # 윈도우 빌드 앱은 자동 재시작 스크립트가 실행됨
                             dialog_content.append(ft.Text("잠시 후 프로그램이 자동으로 재시작됩니다.", weight=ft.FontWeight.BOLD))
                        elif is_built_app:
                            # Mac 등 기타 (다운로드 유도 없음, 이미 교체됨)
                            dialog_content.append(ft.Text("프로그램을 재시작해주세요.", weight=ft.FontWeight.BOLD))
                        else:
                            dialog_content.append(ft.Text("프로그램을 재시작해주세요.", weight=ft.FontWeight.BOLD))
                        
                        success_dialog = ft.AlertDialog(
                            title=ft.Text("✅ 업데이트 준비 완료"),
                            content=ft.Column(dialog_content, tight=True),
                            actions=[ft.TextButton("확인", on_click=lambda _: self.close_dialog(page, success_dialog))]
                        )
                        page.overlay.append(success_dialog)
                        success_dialog.open = True
                        page.update()
                    else:
                        # 실패
                        fail_dialog = ft.AlertDialog(
                            title=ft.Text("❌ 업데이트 실패"),
                            content=ft.Text(f"오류: {message}"),
                            actions=[ft.TextButton("확인", on_click=lambda _: self.close_dialog(page, fail_dialog))]
                        )
                        page.overlay.append(fail_dialog)
                        fail_dialog.open = True
                        page.update()
                
                confirm_dialog = ft.AlertDialog(
                    title=ft.Text(f"🚀 새 버전 발견: v{remote_version}"),
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
        
        # 백그라운드 태스크로 실행
        page.run_task(update_process)
        
    def close_dialog(self, page, dialog):
        """다이얼로그 닫기"""
        dialog.open = False
        page.update()
        
    def restart_application(self):
        """애플리케이션 재시작"""
        try:
            print("🔄 프로그램을 재시작합니다...")
            
            # 1. 파일 시스템 이벤트 처리기 중지 (watchdog 등)
            try:
                if hasattr(self, 'observer') and self.observer:
                    self.observer.stop()
                    self.observer.join(timeout=1.0)
            except:
                pass

            # 2. 현재 창 닫기 시도 (UI 스레드 정리)
            if hasattr(self, 'page') and self.page:
                try:
                    self.page.window_close()
                except:
                    pass
            
            import subprocess
            import sys
            
            # 3. 새 프로세스 실행 준비
            if getattr(sys, 'frozen', False):
                # PyInstaller 빌드 환경
                executable = sys.executable
                
                # macOS .app 번들 처리
                if sys.platform == 'darwin' and 'Contents/MacOS' in executable:
                    # .app 번들 밖의 실제 실행 파일 경로 찾기 또는 open 명령어 사용
                    # Mac에서는 'run_command' 도구로 open 사용이 권장되지만, 
                    # 여기서는 subprocess로 직접 실행
                    
                    # 런처가 별도로 있는 경우 런처를 실행해야 할 수도 있음
                    # 현재 구조: BlogAutomation_Mac (메인 실행파일)
                    
                    cmd = [executable] + sys.argv[1:]
                else:
                    cmd = [executable] + sys.argv[1:]
            else:
                # 일반 파이썬 스크립트 실행
                executable = sys.executable
                cmd = [executable] + sys.argv
            
            print(f"🚀 새 프로세스 실행: {cmd}")
            
            # 4. 새 프로세스 실행 (독립된 프로세스로)
            if sys.platform == 'win32':
                subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                # macOS/Linux
                subprocess.Popen(cmd, start_new_session=True)
                
            # 5. 현재 프로세스 강제 종료
            print("👋 현재 프로세스를 종료합니다.")
            os._exit(0)
                
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
        
        # 버전 로드 로직 (get_current_version과 동일한 로직 적용)
        try:
            possible_paths = [
                os.path.join(current_dir, 'version.json'),
                os.path.join(os.getcwd(), 'version.json')
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        current_version = data.get('version', '1.0.0')
                        if current_version != '1.0.0':
                            print(f"🚀 앱 시작 버전 로드: {path} (v{current_version})")
                            break
        except Exception as e:
            print(f"⚠️ 앱 시작 시 버전 로드 실패: {e}")
                
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