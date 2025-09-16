#!/usr/bin/env python3
"""
시리얼관리 프로그램 시작 스크립트
IDE의 런 버튼으로 실행할 수 있습니다.
"""

import os
import sys
import subprocess
import platform

def get_script_dir():
    """스크립트가 있는 디렉토리 경로 반환"""
    return os.path.dirname(os.path.abspath(__file__))

def check_and_install_packages():
    """필요한 패키지들이 설치되어 있는지 확인하고 없으면 설치"""
    required_packages = ['requests', 'pandas', 'tkcalendar', 'psutil']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} 패키지 확인됨")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} 패키지 누락")
    
    if missing_packages:
        print(f"📥 누락된 패키지들을 설치합니다: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install'
            ] + missing_packages)
            print("✅ 패키지 설치 완료")
        except subprocess.CalledProcessError as e:
            print(f"❌ 패키지 설치 실패: {e}")
            print("💡 터미널에서 다음 명령어를 실행해보세요:")
            print(f"   pip install {' '.join(missing_packages)}")
            return False
    
    return True

def main():
    """메인 실행 함수"""
    print("🚀 시리얼관리 프로그램을 시작합니다...")
    print(f"📁 작업 디렉토리: {get_script_dir()}")
    print(f"🐍 Python 경로: {sys.executable}")
    print(f"💻 운영체제: {platform.system()} {platform.release()}")
    
    # 작업 디렉토리 변경
    os.chdir(get_script_dir())
    
    # 패키지 확인 및 설치
    if not check_and_install_packages():
        print("❌ 패키지 설치에 실패했습니다.")
        input("Enter 키를 눌러 종료하세요...")
        return
    
    try:
        print("🎯 serial_validator.py를 실행합니다...")
        
        # subprocess로 serial_validator.py 실행
        import subprocess
        result = subprocess.run([sys.executable, 'serial_validator.py'], 
                              cwd=get_script_dir(),
                              check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 프로그램 실행 오류: {e}")
        print("💡 자세한 오류 내용은 serial_manager.log 파일을 확인해주세요.")
        input("Enter 키를 눌러 종료하세요...")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        input("Enter 키를 눌러 종료하세요...")

if __name__ == "__main__":
    main()
