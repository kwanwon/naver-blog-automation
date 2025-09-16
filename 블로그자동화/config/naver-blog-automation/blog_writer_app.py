import flet as ft # type: ignore
from modules.gpt_handler import GPTHandler
from modules.serial_auth import BlogSerialAuth
from modules.auto_updater import AutoUpdater  # 자동 업데이트 추가

import subprocess
import os
import sys  # sys 모듈 추가
import platform  # 플랫폼 감지 추가
from datetime import datetime, timedelta
import json
from utils.folder_cleanup import FolderCleanup  # 추가
import random
import hashlib
import threading
import time

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
        
        # 설정 파일에서 use_dummy 값 로드
        self.use_dummy = False  # 기본값을 False로 변경
        try:
            if os.path.exists(os.path.join(self.base_dir, 'config/app_settings.json')):
                with open(os.path.join(self.base_dir, 'config/app_settings.json'), 'r', encoding='utf-8') as f:
                    app_settings = json.load(f)
                    self.use_dummy = app_settings.get('use_dummy', False)  # 기본값을 False로 변경
        except Exception as e:
            print(f"앱 설정 로드 중 오류 발생: {str(e)}")
            
        self.gpt_handler = GPTHandler(use_dummy=self.use_dummy)
        self.current_title = ""
        self.current_content = ""
        self.last_save_content = None
        self.browser_driver = None  # 브라우저 드라이버 인스턴스
        self.temp_driver = None  # 임시 브라우저 드라이버 인스턴스
        
        # 순차적 주제 선택을 위한 인덱스 추적 변수
        self.current_topic_index = -1
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
        if self.is_macos:
            self._start_caffeinate()
    
    def _start_caffeinate(self):
        """macOS에서 절전 모드 방지 시작"""
        try:
            import subprocess
            # caffeinate 명령어로 절전 모드 방지
            # -d: 디스플레이 절전 방지, -i: 시스템 유휴 절전 방지, -s: 시스템 절전 방지
            self.caffeinate_process = subprocess.Popen(
                ['caffeinate', '-d', '-i', '-s'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("🔋 macOS 절전 모드 방지 활성화됨 (caffeinate 실행)")
        except Exception as e:
            print(f"⚠️ macOS 절전 모드 방지 설정 실패: {str(e)}")
            self.caffeinate_process = None
    
    def _stop_caffeinate(self):
        """macOS에서 절전 모드 방지 중지"""
        if self.caffeinate_process:
            try:
                self.caffeinate_process.terminate()
                self.caffeinate_process.wait(timeout=5)
                print("🔋 macOS 절전 모드 방지 해제됨 (caffeinate 종료)")
            except Exception as e:
                print(f"⚠️ caffeinate 종료 중 오류: {str(e)}")
                try:
                    self.caffeinate_process.kill()
                except:
                    pass
            finally:
                self.caffeinate_process = None

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
    
    def get_serial_status(self):
        """시리얼 인증 상태 정보 반환"""
        try:
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
            width=200,
            height=50
        )
        
        # 타이머 제어 버튼들
        self.timer_start_btn = ft.ElevatedButton(
            text="시작",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=ft.Colors.GREEN_400,
            color=ft.Colors.WHITE,
            disabled=False,  # 기능 활성화
            width=90,
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
        """저장된 주제 인덱스 로드"""
        try:
            if os.path.exists(os.path.join(self.base_dir, 'config/topic_index.json')):
                with open(os.path.join(self.base_dir, 'config/topic_index.json'), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_topic_index = data.get('current_index', -1)
        except Exception as e:
            print(f"주제 인덱스 로드 중 오류 발생: {str(e)}")
            self.current_topic_index = -1
            
    def save_topic_index(self):
        """현재 주제 인덱스 저장"""
        try:
            with open(os.path.join(self.base_dir, 'config/topic_index.json'), 'w', encoding='utf-8') as f:
                json.dump({'current_index': self.current_topic_index}, f)
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
                        content=ft.Text("🤖 타이머가 전송 버튼을 클릭했습니다!"),
                        bgcolor=ft.Colors.GREEN
                    )
                    self.page_ref.snack_bar.open = True
                    self.page_ref.update()
                
                return True  # 전송 클릭 성공
            else:
                print("❌ 전송 버튼 함수가 설정되지 않았습니다.")
                return False
                
        except Exception as e:
            print(f"전송 버튼 클릭 중 오류: {str(e)}")
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
            
    def load_folder_index(self):
        """현재 이미지 폴더 인덱스를 로드합니다."""
        try:
            index_file = os.path.join(self.base_dir, 'config/current_folder_index.txt')
            if os.path.exists(index_file):
                with open(index_file, 'r') as f:
                    return int(f.read().strip())
            return 0  # 파일이 없으면 0부터 시작
        except Exception as e:
            print(f"폴더 인덱스 로드 중 오류 발생: {str(e)}")
            return 0
            
    def save_folder_index(self, index):
        """현재 이미지 폴더 인덱스를 저장합니다."""
        try:
            index_file = os.path.join(self.base_dir, 'config/current_folder_index.txt')
            with open(index_file, 'w') as f:
                f.write(str(index))
            return True
        except Exception as e:
            print(f"폴더 인덱스 저장 중 오류 발생: {str(e)}")
            return False
            
    def load_used_folders(self):
        """사용된 이미지 폴더 이력을 로드합니다."""
        try:
            used_folders_file = os.path.join(self.base_dir, 'config/used_folders.json')
            if os.path.exists(used_folders_file):
                with open(used_folders_file, 'r') as f:
                    return json.load(f)
            return {"used_folders": [], "cycle_count": 0}
        except Exception as e:
            print(f"사용된 폴더 이력 로드 중 오류 발생: {str(e)}")
            return {"used_folders": [], "cycle_count": 0}
            
    def save_used_folders(self, used_folders):
        """사용된 이미지 폴더 이력을 저장합니다."""
        try:
            used_folders_file = os.path.join(self.base_dir, 'config/used_folders.json')
            with open(used_folders_file, 'w') as f:
                json.dump(used_folders, f)
            return True
        except Exception as e:
            print(f"사용된 폴더 이력 저장 중 오류 발생: {str(e)}")
            return False
            
    def get_next_image_folder(self):
        """다음 이미지 폴더 경로를 반환하고 인덱스를 업데이트합니다.
           이미 사용된 폴더는 건너뛰고 다음 폴더를 선택합니다."""
        # 사용된 폴더 이력 로드
        used_data = self.load_used_folders()
        used_folders = used_data["used_folders"]
        cycle_count = used_data["cycle_count"]
        
        # 현재 인덱스 로드
        current_index = self.load_folder_index()
        
        # 모든 폴더 사용 여부 확인
        all_used = True
        for i in range(1, 11):
            folder_name = f"default_images_{i}"
            if folder_name not in used_folders:
                all_used = False
                break
                
        # 모든 폴더가 사용되었으면 초기화
        if all_used:
            used_folders = []
            cycle_count += 1
            print(f"모든 이미지 폴더를 사용했습니다. 새로운 사이클({cycle_count}) 시작")
            
        # 사용되지 않은 다음 폴더 찾기
        found = False
        next_index = current_index
        
        for _ in range(10):  # 최대 10번 시도
            next_index = (next_index % 10) + 1  # 1~10 순환
            folder_name = f"default_images_{next_index}"
            folder_path = os.path.join(self.base_dir, folder_name)
            
            # 폴더가 존재하고 아직 사용되지 않았으면 선택
            if os.path.exists(folder_path) and folder_name not in used_folders:
                found = True
                break
        
        if not found:
            print("사용 가능한 이미지 폴더를 찾을 수 없습니다. 기본 폴더 사용.")
            # 기본 이미지 폴더 사용
            return os.path.join(self.base_dir, "default_images")
        
        # 선택된 폴더를 사용된 목록에 추가
        used_folders.append(f"default_images_{next_index}")
        used_data = {"used_folders": used_folders, "cycle_count": cycle_count}
        self.save_used_folders(used_data)
        
        # 인덱스 업데이트 및 저장
        self.save_folder_index(next_index)
        
        folder_path = os.path.join(self.base_dir, f"default_images_{next_index}")
        print(f"이미지 폴더 선택: {folder_path} (사이클 {cycle_count})")
        return folder_path

    def select_sequential_topic(self):
        """저장된 주제 목록에서 순차적으로 주제 선택"""
        try:
            if os.path.exists(os.path.join(self.base_dir, 'config/user_settings.txt')):
                with open(os.path.join(self.base_dir, 'config/user_settings.txt'), 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    topics_str = settings.get('blog_topics', '')
                    if topics_str:
                        topics = [topic.strip() for topic in topics_str.split(',') if topic.strip()]
                        if topics:
                            # 다음 인덱스로 이동 (마지막 주제를 사용했으면 처음으로 돌아감)
                            self.current_topic_index = (self.current_topic_index + 1) % len(topics)
                            # 선택된 인덱스 저장
                            self.save_topic_index()
                            # 현재 인덱스의 주제 반환
                            return topics[self.current_topic_index]
            return None
        except Exception as e:
            print(f"주제 선택 중 오류 발생: {str(e)}")
            return None

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
        # 시리얼 인증 확인 (필수)
        if self.serial_auth.is_serial_required():
            print("🔐 시리얼 인증이 필요합니다. 시리얼 인증 창을 실행합니다...")
            try:
                # 시리얼 인증 창 실행
                current_dir = os.path.dirname(os.path.abspath(__file__))
                serial_auth_path = os.path.join(current_dir, "start_with_serial_auth.py")
                python_executable = sys.executable
                
                subprocess.Popen([python_executable, serial_auth_path], 
                               cwd=current_dir,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True)
                
                # 현재 프로그램 종료
                sys.exit(0)
                return
            except Exception as e:
                print(f"❌ 시리얼 인증 창 실행 중 오류: {e}")
                # 시리얼 인증 실패 시 프로그램 종료
                sys.exit(1)
                return
        
        # 페이지 설정
        page.title = "블로그 글쓰기 도우미"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.padding = 20
        page.window_width = 1200
        page.window_height = 800
        page.window_resizable = True
        

        
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
                    "auto_final_publish": auto_final_publish_checkbox.value,  # 🎯 최종 발행 설정 추가
                    "image_insert_mode": image_insert_mode_value,  # 이미지 삽입 방식 저장
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
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
                        auto_final_publish_checkbox.value = app_settings.get('auto_final_publish', True)  # 🎯 최종 발행 설정 로드
                        image_insert_mode_value = app_settings.get('image_insert_mode', 'random')  # 이미지 삽입 방식 로드
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
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                with open(os.path.join(self.base_dir, 'config/gpt_settings.txt'), 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)
                
                # API 키 저장 (환경 변수 파일에)
                if use_api_checkbox.value and api_key_field.value:
                    env_content = f"OPENAI_API_KEY={api_key_field.value}\n"
                    with open(os.path.join(self.base_dir, '.env'), 'w', encoding='utf-8') as f:
                        f.write(env_content)
                
                # GPT 핸들러 재초기화
                self.use_dummy = not use_api_checkbox.value
                self.gpt_handler = GPTHandler(use_dummy=self.use_dummy)
                
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
            hint_text="자동 작성에 사용될 주제들을 쉼표(,)로 구분하여 입력하세요. 예: 유산소운동의 중요성,근력운동의 효과,단백질 섭취의 중요성",
            multiline=True,
            min_lines=3,
            max_lines=6
        )

        slogan = ft.TextField(
            label="마지막 슬로건",
            hint_text="블로그 글 마지막에 표시될 슬로건을 입력하세요. 예: 바른 인성을 가진 인재를 기르는 한국체대 라이온 태권도 합기도",
            multiline=True,
            min_lines=2,
            max_lines=4
        )

        # 본문 첫 문장 설정 필드 추가
        first_sentence = ft.TextField(
            label="본문 글의 첫 문장 (선택사항)",
            hint_text="본문에 고정으로 사용할 첫 문장을 입력하세요. 예: 안녕하세요, 한국체대 라이온 블로거 입니다. 함께 공부한다고 지식을 나누고자 합니다.",
            multiline=True,
            min_lines=2,
            max_lines=3
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
                    "slogan": slogan.value,
                    "first_sentence": first_sentence.value,
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
                        slogan.value = settings.get('slogan', '바른 인성을 가진 인재를 기르는 한국체대 라이온 태권도 합기도')
                        first_sentence.value = settings.get('first_sentence', '')
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
            # 자동 주제 모드 체크
            if auto_topic_checkbox.value:
                # 순차적 주제 선택
                selected_topic = self.select_sequential_topic()
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
            page.update()
            
            try:
                # GPT 응답 생성
                result = self.gpt_handler.generate_content(topic_input.value)
                self.current_title = result["title"]
                self.current_content = result["content"]

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
                page.update()
                
                # 자동 업로드가 설정된 경우
                if auto_upload_checkbox.value:
                    upload_result = upload_to_blog(None)
                    # 업로드 결과를 저장 (자동 포스팅에서 사용)
                    if hasattr(self, 'last_upload_success'):
                        self.last_upload_success = upload_result if upload_result is not None else False
                
            except Exception as e:
                # 진행 대화상자 닫기
                progress_dlg.open = False
                page.update()
                
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
            page.update()

        # 블로그 업로드 처리
        def upload_to_blog(e):
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
                    
                    # 자동화 인스턴스 생성 (기존 브라우저 세션 활용)
                    blog_auto = NaverBlogAutomation(
                        auto_mode=auto_image_checkbox.value,  # UI 체크박스 값 사용
                        image_insert_mode="random",
                        use_stickers=False
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
                    
                    # 블로그 포스팅 작성 (기존 시스템 활용)
                    success = blog_auto.write_post(
                        title=title_input.value,
                        content=formatted_content,
                        tags=tags
                    )
                    
                    if success:
                        # 사용 횟수 증가
                        increment_usage_count()
                        
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
                    else:
                        raise Exception("블로그 포스팅 작성에 실패했습니다")
                        
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
                
                # 실패 상태 저장
                if hasattr(self, 'last_upload_success'):
                    self.last_upload_success = False
                
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
            on_click=upload_to_blog
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
                        next_post_time_text
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
                    use_api_checkbox,
                    api_key_field,
                    api_key_help_text,
                    auto_upload_checkbox,
                    auto_upload_help_text,
                    auto_topic_checkbox,
                    auto_topic_help_text,
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
                    slogan,
                    first_sentence,
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

        # 탭 컨트롤
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="블로그 작성",
                    icon=ft.Icons.EDIT_NOTE,
                    content=main_content_tab
                ),
                ft.Tab(
                    text="시간 설정",
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
        
        # 설정 로드
        load_gpt_settings()
        load_user_settings()
        load_app_settings()
        load_timer_settings()
        load_usage_stats()  # 사용 통계 로드 추가
        load_draft()

        # auto_topic_checkbox 변경 이벤트 처리
        def on_auto_topic_change(e):
            if auto_topic_checkbox.value:
                # 주제 목록 수와 현재 인덱스 가져오기
                topic_count = 0
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
                
                auto_topic_status.value = f"자동 주제 모드: 활성화 (다음: {self.current_topic_index + 2}/{topic_count})"
            else:
                auto_topic_status.value = "자동 주제 모드: 비활성화"
                
            auto_topic_status.color = ft.Colors.GREEN if auto_topic_checkbox.value else ft.Colors.GREY_600
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
        
        # 시리얼 상태 실시간 업데이트 시작
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
            version_file = os.path.join(self.base_dir, 'version.json')
            if os.path.exists(version_file):
                with open(version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('version', '1.0.0')
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
                        # 성공 다이얼로그
                        success_dialog = ft.AlertDialog(
                            title=ft.Text("🎉 업데이트 완료!"),
                            content=ft.Column([
                                ft.Text(message),
                                ft.Text("모든 설정과 시리얼 정보는 안전하게 보존되었습니다.", color=ft.Colors.GREEN_600),
                                ft.Text("프로그램을 재시작해주세요.", weight=ft.FontWeight.BOLD)
                            ]),
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
            python = sys.executable
            os.execl(python, python, *sys.argv)
        except Exception as e:
            print(f"❌ 재시작 실패: {e}")
            print("수동으로 프로그램을 재시작해주세요.")

if __name__ == "__main__":
    # 프로그램 시작 전 업데이트 확인
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        version_file = os.path.join(current_dir, 'version.json')
        
        current_version = '1.0.0'
        if os.path.exists(version_file):
            with open(version_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                current_version = data.get('version', '1.0.0')
                
        updater = AutoUpdater(current_version)
        
        # 업데이트 확인 및 적용
        print("🚀 블로그 자동화 프로그램 시작...")
        success, message = updater.check_and_update()
        
        if success:
            print(f"✅ {message}")
            print("🔄 업데이트된 프로그램을 시작합니다...")
            time.sleep(2)  # 잠깐 대기
            
    except Exception as e:
        print(f"⚠️ 업데이트 확인 중 오류: {e}")
        print("🔄 기존 프로그램을 시작합니다...")
    
    # 메인 앱 실행
    app = BlogWriterApp()
    ft.app(target=app.main) 