import sys
import subprocess
import importlib.util
import os

def install_package(package_name):
    print(f"Installing {package_name}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
    except Exception as e:
        print(f"Failed to install {package_name}: {e}")

def main():
    # 필수 패키지 목록
    required_packages = ['requests', 'pandas', 'tkcalendar', 'psutil', 'cryptography']
    
    for package in required_packages:
        if importlib.util.find_spec(package) is None:
            install_package(package)
            
    # 시리얼 관리자 실행
    script_path = os.path.join(os.path.dirname(__file__), "serial_validator.py")
    if os.path.exists(script_path):
        subprocess.run([sys.executable, script_path])
    else:
        print(f"Error: {script_path} not found.")

if __name__ == "__main__":
    main()
