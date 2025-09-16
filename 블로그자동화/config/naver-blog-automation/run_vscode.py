#!/usr/bin/env python3
import sys
import os
import subprocess

# 현재 스크립트의 디렉토리로 작업 디렉토리 변경
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# 가상환경의 python3 경로
venv_python = os.path.join(script_dir, "venv_temp", "bin", "python3")

# 가상환경이 있는지 확인
if not os.path.exists(venv_python):
    print("❌ 가상환경을 찾을 수 없습니다!")
    print(f"경로를 확인하세요: {venv_python}")
    sys.exit(1)

# 가상환경의 python으로 blog_writer_app.py 실행
try:
    print("🚀 가상환경에서 블로그 앱을 실행합니다...")
    subprocess.run([venv_python, "blog_writer_app.py"], check=True)
except subprocess.CalledProcessError as e:
    print(f"❌ 실행 중 오류 발생: {e}")
    sys.exit(1)
except KeyboardInterrupt:
    print("\n⏹️  사용자에 의해 중단되었습니다.") 