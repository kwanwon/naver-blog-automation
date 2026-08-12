#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
블로그자동화 런처 (빌드용)
PyInstaller로 빌드되어 BlogAutomation.exe가 됩니다.
시리얼 인증 창을 먼저 띄우고, 인증 성공 시 메인 프로그램(BlogApp.exe)을 실행합니다.
"""

import sys
import io
import os
import flet as ft

# 윈도우 인코딩 (시계 이모지 등 처리용)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
from serial_auth_window import SerialAuthWindow

# 현재 스크립트 경로 기반으로 base_dir 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

if __name__ == "__main__":
    print("🔑 블로그자동화 런처를 시작합니다...")
    app = SerialAuthWindow()
    ft.app(target=app.main)
