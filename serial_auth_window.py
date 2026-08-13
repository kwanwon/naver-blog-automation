#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시리얼 인증 전용 창
블로그자동화 프로그램 실행 전 시리얼 번호 검증을 위한 독립적인 Flet 애플리케이션
"""

import flet as ft
import sys
import os
import subprocess
import threading
import time

# 현재 스크립트 경로 기반으로 base_dir 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from modules.serial_auth import BlogSerialAuth

class SerialAuthWindow:
    def __init__(self):
        self.serial_auth = BlogSerialAuth()
        self.base_dir = current_dir
        self.show_error_message = None
        
    def main(self, page: ft.Page):
        # 페이지 설정
        page.title = "🔐 시리얼 번호 인증"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 500
        page.window_height = 400
        page.window_resizable = False
        
        print("🔐 시리얼 인증 창이 시작되었습니다.")
        
        # 시리얼 인증이 이미 완료되어 있는지 확인 (is_serial_required에서 유효성까지 검증함)
        if not self.serial_auth.is_serial_required():
            config = self.serial_auth.load_config()
            serial_number = config.get("serial_number")
            
            print("✅ 시리얼 인증이 이미 완료되어 있습니다. 메인 프로그램을 실행합니다.")
            print("🔄 디바이스 정보 및 사용횟수 업데이트 중...")
            self.serial_auth.update_device_info_and_usage(serial_number)
            self.launch_main_app(page)
            return
        else:
            # 시리얼 인증이 필요한 경우 (무효하거나 없는 경우)
            config = self.serial_auth.load_config()
            serial_number = config.get("serial_number")
            
            if serial_number:
                # 기존 무효한 시리얼이 있는 경우
                print(f"❌ 기존 시리얼이 유효하지 않습니다: {serial_number}")
                print("🔐 새로운 시리얼 번호 입력이 필요합니다.")
                # 기존 설정 삭제
                config["serial_number"] = ""
                config["last_validation"] = ""
                self.serial_auth.save_config(config)
                self.show_error_message = "기존 시리얼이 만료되었거나 유효하지 않습니다"
            else:
                # 시리얼이 없는 경우
                print("🔐 시리얼 번호 입력이 필요합니다.")
        
        # UI 컴포넌트들
        title_text = ft.Text(
            "🔐 시리얼 번호 인증",
            size=24,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.BLUE_700
        )
        
        subtitle_text = ft.Text(
            "블로그자동화 프로그램 사용을 위해\n시리얼 번호 인증이 필요합니다.",
            size=14,
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.GREY_700
        )
        
        serial_input = ft.TextField(
            label="시리얼 번호",
            hint_text="시리얼 번호를 입력하세요",
            width=350,
            autofocus=True
        )
        
        # 기존 시리얼이 유효하지 않은 경우 에러 메시지 표시
        initial_message = ""
        initial_color = ft.Colors.RED
        if hasattr(self, 'show_error_message') and self.show_error_message:
            initial_message = f"❌ {self.show_error_message}\n🔐 새로운 시리얼 번호를 입력해주세요."
        
        status_text = ft.Text(
            initial_message,
            size=14,
            text_align=ft.TextAlign.CENTER,
            color=initial_color
        )
        
        loading_ring = ft.ProgressRing(visible=False, width=30, height=30)
        
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
                        # 성공
                        self.serial_auth.save_validation(serial_number, expiry_date)
                        
                        # UI 업데이트
                        loading_ring.visible = False
                        status_text.value = "✅ 인증 성공! 프로그램을 시작합니다..."
                        status_text.color = ft.Colors.GREEN
                        
                        # 만료 경고가 있으면 표시
                        if "주의:" in message:
                            warning_dialog = ft.AlertDialog(
                                title=ft.Text("⚠️ 만료 알림"),
                                content=ft.Text(message, size=14),
                                actions=[
                                    ft.TextButton("확인", on_click=lambda e: setattr(warning_dialog, 'open', False) or page.update())
                                ]
                            )
                            page.dialog = warning_dialog
                            warning_dialog.open = True
                        
                        page.update()
                        time.sleep(2)
                        
                        # 메인 프로그램 실행
                        self.launch_main_app(page)
                        
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
        
        # 이벤트 핸들러 설정
        serial_input.on_submit = on_serial_submit
        
        submit_button = ft.ElevatedButton(
            "인증",
            on_click=on_serial_submit,
            width=150,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE,
                color=ft.Colors.WHITE
            )
        )
        
        cancel_button = ft.TextButton(
            "취소",
            on_click=on_cancel,
            width=100
        )
        
        # 레이아웃 구성
        content = ft.Column([
            ft.Container(height=30),  # 상단 여백
            title_text,
            ft.Container(height=10),
            subtitle_text,
            ft.Container(height=30),
            serial_input,
            ft.Container(height=10),
            ft.Row([
                loading_ring
            ], alignment=ft.MainAxisAlignment.CENTER),
            status_text,
            ft.Container(height=20),
            ft.Row([
                cancel_button,
                submit_button
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
            ft.Container(height=30)  # 하단 여백
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        # 페이지에 추가
        page.add(ft.Container(
            content=content,
            padding=30,
            alignment=ft.alignment.center
        ))
        
        # 포커스 설정
        try:
            serial_input.focus()
        except:
            pass
    
    def launch_main_app(self, page):
        """메인 블로그자동화 프로그램 실행"""
        try:
            print("🚀 메인 블로그자동화 프로그램을 실행합니다...")
            
            # 현재 창 닫기
            try:
                page.window_close()
            except:
                pass
            
            # BlogApp.exe 실행 후 런처는 완전 종료
            import os, threading
            def _exit():
                import time
                time.sleep(1)   # BlogApp.exe 실행 시간 확보
                os._exit(0)     # 런처 프로세스 강제 종료
            threading.Thread(target=_exit, daemon=True).start()
            
            # Application Path Setup
            if getattr(sys, 'frozen', False):
                # PyInstaller로 빌드된 환경 (Frozen)
                bundle_dir = os.path.dirname(sys.executable)
                
                if sys.platform == "win32":
                    # Windows: BlogApp.exe가 런처(BlogAutomation.exe)와 같은 폴더에 있다고 가정 (onedir)
                    # build.yml에서 BlogAutomation.exe를 BlogApp 폴더로 복사하거나 
                    # BlogApp 폴더를 BlogAutomation 폴더로 변경하는 로직에 따라 상대 경로 결정
                    
                    # 1. 런처와 같은 폴더에 있는 경우 (가장 일반적)
                    main_app_path = os.path.join(bundle_dir, "BlogApp.exe")
                    
                    # 2. BlogApp 하위 폴더에 있는 경우 (예비)
                    if not os.path.exists(main_app_path):
                        main_app_path = os.path.join(bundle_dir, "BlogApp", "BlogApp.exe")

                    # 3. 개발 중 테스트 (dist/BlogAutomation_Windows_App/BlogApp.exe)
                    # build.yml 로직:
                    # BlogApp (PyInstaller output) -> renamed to BlogAutomation_Windows_App
                    # Launcher (BlogAutomation.exe) copied to BlogAutomation_Windows_App
                    # So they are in the SAME directory.
                    
                elif sys.platform == "darwin":
                    # macOS: BlogAutomation_Mac.app/Contents/MacOS/BlogAutomation_Mac 이 실행됨
                    # 같은 폴더에 있음
                    # 하지만 macOS .app 번들 구조상 다를 수 있음.
                    # flet pack은 실행파일을 생성함.
                    # Mac 빌드 스크립트: flet pack blog_writer_app.py --name BlogAutomation_Mac
                    # Launcher script usage on Mac logic needs verification if we change to Launcher pattern.
                    # For now, focus on Windows Fix mostly, but try to keep generic.
                    
                    # Mac의 경우 런처 없이 단일 앱으로 빌드되었을 수 있음.
                    # 만약 런처를 쓴다면 로직 추가 필요.
                    # 현재 Mac 빌드는 런처 없이 바로 blog_writer_app.py를 flet pack 함.
                    # 따라서 이 코드는 Windows Launcher 로직에 집중.
                    main_app_path = os.path.join(bundle_dir, "BlogAutomation_Mac") 
                
                print(f"📂 실행 경로(Frozen): {main_app_path}")
                
                if os.path.exists(main_app_path):
                     subprocess.Popen([main_app_path], 
                           cwd=os.path.dirname(main_app_path),
                           env=os.environ.copy())
                else:
                    print(f"❌ 메인 실행 파일을 찾을 수 없습니다: {main_app_path}")
                    # 개발자 디버그용 메시지
                    print(f"참고: bundle_dir={bundle_dir}")
                    
            else:
                # 일반 Python 스크립트 환경 (Dev)
                blog_app_path = os.path.join(self.base_dir, "blog_writer_app.py")
                
                # Python 환경 설정
                if os.path.exists(os.path.join(self.base_dir, "venv")):
                    # 가상환경이 있으면 가상환경 사용
                    if sys.platform == "win32":
                        python_exe = os.path.join(self.base_dir, "venv", "Scripts", "python.exe")
                    else:
                        python_exe = os.path.join(self.base_dir, "venv", "bin", "python3")
                else:
                    python_exe = sys.executable
                
                # 메인 프로그램 실행
                subprocess.Popen([python_exe, blog_app_path], 
                               cwd=self.base_dir,
                               env=os.environ.copy())
            
            print("✅ 메인 프로그램 실행 요청 완료!")
            
            import threading
            import time
            def _exit():
                time.sleep(1)
                import os
                os._exit(0)
            threading.Thread(target=_exit, daemon=True).start()
            
        except Exception as e:
            print(f"❌ 메인 프로그램 실행 중 오류: {e}")

if __name__ == "__main__":
    print("🔐 시리얼 인증 창을 시작합니다...")
    app = SerialAuthWindow()
    ft.app(target=app.main)
