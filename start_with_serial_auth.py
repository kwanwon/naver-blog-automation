#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시리얼 인증 후 블로그자동화 실행 스크립트
이 스크립트가 새로운 프로그램 시작점입니다.
"""

import sys
import os

# 현재 스크립트 경로 기반으로 base_dir 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 시리얼 인증 창 실행
if __name__ == "__main__":
    print("🚀 블로그자동화 프로그램을 시작합니다...")
    print("🔐 시리얼 인증을 먼저 진행합니다...")
    
    try:
        from serial_auth_window import SerialAuthWindow
        import flet as ft
        
        # 시리얼 인증 창 실행
        app = SerialAuthWindow()
        ft.app(target=app.main)
        
    except Exception as e:
        print(f"❌ 시리얼 인증 창 실행 중 오류: {e}")
        print("프로그램을 종료합니다.")
        sys.exit(1)
