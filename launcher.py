#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
블로그자동화 런처 (빌드용)
PyInstaller로 빌드되어 BlogAutomation.exe가 됩니다.
시리얼 인증 창을 먼저 띄우고, 인증 성공 시 메인 프로그램(BlogApp.exe)을 실행합니다.
"""

import sys
import os
import flet as ft
from serial_auth_window import SerialAuthWindow

# 현재 스크립트 경로 기반으로 base_dir 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

if __name__ == "__main__":
    # Windows에서 콘솔 창 숨기기 (선택적, pyinstaller --noconsole 옵션으로 처리됨)
    # 하지만 런처는 GUI가 필요하므로 flet app으로 실행
    
    print("🚀 블로그자동화(런처)를 시작합니다...")
    
    try:
        # 시리얼 인증 창 실행
        app = SerialAuthWindow()
        ft.app(target=app.main)
        
    except Exception as e:
        print(f"❌ 런처 실행 중 오류 발생: {e}")
        # 오류 발생 시 잠시 대기 (콘솔 모드일 경우 확인용)
        # time.sleep(5)
        sys.exit(1)
