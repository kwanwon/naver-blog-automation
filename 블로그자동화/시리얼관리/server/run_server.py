#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
블로그 자동화 서버를 로컬에서 실행하기 위한 스크립트
"""

import os
import sys
import subprocess

def check_dependencies():
    """필요한 패키지가 설치되어 있는지 확인"""
    try:
        import flask
        import flask_cors
        print("✅ 필요한 패키지가 이미 설치되어 있습니다.")
        return True
    except ImportError:
        print("⚠️ 필요한 패키지가 설치되어 있지 않습니다.")
        return False

def install_dependencies():
    """필요한 패키지 설치"""
    try:
        print("📦 필요한 패키지 설치 중...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 패키지 설치 완료")
        return True
    except subprocess.CalledProcessError:
        print("❌ 패키지 설치 실패")
        return False

def run_server():
    """서버 실행"""
    try:
        print("🚀 블로그 자동화 서버 시작 중...")
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blog_automation_server.py")
        
        if not os.path.exists(script_path):
            print(f"❌ 서버 스크립트를 찾을 수 없습니다: {script_path}")
            return False
        
        print("📡 서버가 http://localhost:5000 에서 실행됩니다.")
        print("🛑 서버를 중지하려면 Ctrl+C를 누르세요.")
        subprocess.call([sys.executable, script_path])
        return True
    except Exception as e:
        print(f"❌ 서버 실행 중 오류 발생: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 환경 확인 중...")
    
    if not check_dependencies():
        if not install_dependencies():
            print("❌ 필요한 패키지를 설치할 수 없습니다. 수동으로 설치하세요.")
            print("📝 명령어: pip install -r requirements.txt")
            sys.exit(1)
    
    run_server() 