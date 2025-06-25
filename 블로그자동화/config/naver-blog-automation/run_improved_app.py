#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
개선된 블로그 자동화 앱 실행 스크립트
"""

import os
import sys

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from blog_writer_app_improved import main
    import flet as ft
    
    print("🚀 개선된 블로그 자동화 앱을 시작합니다...")
    print("📍 작업 디렉토리:", current_dir)
    
    # Flet 앱 실행
    ft.app(target=main)
    
except ImportError as e:
    print(f"❌ 모듈 import 오류: {e}")
    print("필요한 패키지를 설치해주세요:")
    print("pip install flet selenium webdriver-manager")
    
except Exception as e:
    print(f"❌ 앱 실행 중 오류: {e}")
    import traceback
    traceback.print_exc()