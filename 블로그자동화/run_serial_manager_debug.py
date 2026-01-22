import sys
import os
import subprocess

# 현재 디렉토리 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
# 시리얼관리 폴더가 상위 디렉토리(라이온개발자) 아래에 있음
serial_manager_dir = os.path.join(os.path.dirname(current_dir), '시리얼관리')

# 시리얼 관리자 실행
script_path = os.path.join(serial_manager_dir, 'serial_validator.py')

print(f"🚀 시리얼 관리 프로그램을 실행합니다...")
print(f"📂 경로: {script_path}")

# 가상환경 Python 경로 확인
venv_python = os.path.join(current_dir, '.venv', 'bin', 'python')
if os.path.exists(venv_python):
    python_exe = venv_python
    print(f"🐍 가상환경 Python 감지됨: {python_exe}")
else:
    python_exe = sys.executable
    print(f"🐍 시스템 Python 사용: {python_exe}")

try:
    # python3로 실행
    subprocess.run([python_exe, script_path], check=True)
except Exception as e:
    print(f"❌ 실행 중 오류 발생: {e}")
    input("프로그램을 종료하려면 엔터를 누르세요...")
