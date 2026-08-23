#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
블로그자동화 런처 (빌드용)
PyInstaller로 빌드되어 BlogAutomation_Windows.exe가 됩니다.
시리얼 인증 창을 띄우기 전 이미 인증 완료되었는지 사전 검사하여 불필요한 빈 창 유발을 차단합니다.
"""

import sys
import io
import os
import subprocess

# 윈도우 인코딩 (시계 이모지 등 처리용) - noconsole 모드 방어 코드 추가
if sys.stdout and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from modules.serial_auth import BlogSerialAuth

def launch_direct():
    """GUI 창 없이 곧바로 메인 앱(BlogApp.exe) 실행"""
    if getattr(sys, 'frozen', False):
        bundle_dir = os.path.dirname(sys.executable)
        main_app_path = os.path.join(bundle_dir, "BlogApp.exe")
        if not os.path.exists(main_app_path):
            main_app_path = os.path.join(bundle_dir, "BlogApp", "BlogApp.exe")
        if os.path.exists(main_app_path):
            subprocess.Popen([main_app_path], cwd=os.path.dirname(main_app_path), env=os.environ.copy())
            sys.exit(0)
    else:
        blog_app_path = os.path.join(current_dir, "blog_writer_app.py")
        subprocess.Popen([sys.executable, blog_app_path], cwd=current_dir, env=os.environ.copy())
        sys.exit(0)

if __name__ == "__main__":
    serial_auth = BlogSerialAuth()
    
    # 1. 시리얼 인증이 이미 완료된 경우 -> Flet GUI 창을 띄우지 않고 즉시 메인 앱 실행 (빈 흰 창 방지)
    if not serial_auth.is_serial_required():
        config = serial_auth.load_config()
        serial_number = config.get("serial_number")
        if serial_number:
            try:
                serial_auth.update_device_info_and_usage(serial_number)
            except:
                pass
        launch_direct()
    
    # 2. 시리얼 인증이 필요한 경우에만 Flet 인증 창 실행
    else:
        import flet as ft
        from serial_auth_window import SerialAuthWindow
        app = SerialAuthWindow()
        ft.app(target=app.main)
