#!/usr/bin/env python3
"""
크로스 플랫폼 블로그 자동화 도구 - 통합 시작 스크립트
Windows, macOS, Linux 모든 플랫폼에서 동작

사용법:
    python start_blog_automation.py
"""

import os
import sys
import platform
import subprocess
from pathlib import Path

def detect_platform():
    """플랫폼 감지"""
    system = platform.system().lower()
    return {
        'system': system,
        'is_windows': system == 'windows',
        'is_macos': system == 'darwin',
        'is_linux': system == 'linux',
        'machine': platform.machine(),
        'python_version': platform.python_version()
    }

def print_header(platform_info):
    """헤더 출력"""
    print("=" * 60)
    print("🌍 크로스 플랫폼 블로그 자동화 도구")
    print("=" * 60)
    print(f"💻 플랫폼: {platform.system()} ({platform.machine()})")
    print(f"🐍 Python: {platform_info['python_version']}")
    print(f"📂 경로: {os.getcwd()}")
    print("=" * 60)
    print()

def check_environment():
    """환경 확인"""
    print("🔍 환경 확인 중...")
    
    # Python 버전 확인
    min_version = (3, 8)
    current_version = sys.version_info[:2]
    
    if current_version < min_version:
        print(f"❌ Python 버전이 너무 낮습니다.")
        print(f"   현재: {'.'.join(map(str, current_version))}")
        print(f"   최소 요구: {'.'.join(map(str, min_version))}")
        return False
    
    print(f"✅ Python {'.'.join(map(str, current_version))}")
    
    # 필수 파일 확인
    required_files = ['blog_writer_app.py', 'requirements_cross_platform.txt']
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ 필수 파일이 없습니다: {', '.join(missing_files)}")
        return False
    
    print("✅ 필수 파일 확인 완료")
    return True

def setup_virtual_environment(platform_info):
    """가상 환경 설정"""
    venv_path = Path("venv")
    
    if not venv_path.exists():
        print("🏠 가상 환경이 없습니다. 생성 중...")
        try:
            subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
            print("✅ 가상 환경 생성 완료")
        except subprocess.CalledProcessError as e:
            print(f"❌ 가상 환경 생성 실패: {e}")
            return False
    else:
        print("✅ 가상 환경 발견")
    
    # 가상 환경 활성화 및 패키지 설치
    if platform_info['is_windows']:
        pip_path = venv_path / "Scripts" / "pip.exe"
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"
    
    # pip 업그레이드
    try:
        print("🔄 pip 업그레이드 중...")
        subprocess.run([str(python_path), '-m', 'pip', 'install', '--upgrade', 'pip'], 
                      check=True, capture_output=True)
        print("✅ pip 업그레이드 완료")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ pip 업그레이드 실패: {e}")
    
    # 패키지 설치
    requirements_file = "requirements_cross_platform.txt"
    if os.path.exists(requirements_file):
        try:
            print("📦 패키지 설치 중...")
            subprocess.run([str(pip_path), 'install', '-r', requirements_file], 
                          check=True, capture_output=True)
            print("✅ 패키지 설치 완료")
        except subprocess.CalledProcessError as e:
            print(f"❌ 패키지 설치 실패: {e}")
            return False
    
    return python_path

def setup_chromedriver(platform_info):
    """ChromeDriver 설정"""
    print("🚗 ChromeDriver 확인 중...")
    
    # 플랫폼별 ChromeDriver 파일명
    if platform_info['is_windows']:
        driver_names = ['chromedriver.exe', 'chromedriver']
    else:
        driver_names = ['chromedriver']
    
    found_driver = None
    for driver_name in driver_names:
        if os.path.exists(driver_name):
            found_driver = driver_name
            break
    
    if found_driver:
        print(f"✅ ChromeDriver 발견: {found_driver}")
        
        # Unix 계열에서 실행 권한 확인
        if not platform_info['is_windows']:
            try:
                current_mode = os.stat(found_driver).st_mode
                if not (current_mode & 0o111):  # 실행 권한이 없으면
                    os.chmod(found_driver, 0o755)
                    print("🔑 실행 권한 부여 완료")
                
                # macOS에서 quarantine 제거
                if platform_info['is_macos']:
                    try:
                        subprocess.run(['xattr', '-d', 'com.apple.quarantine', found_driver], 
                                     capture_output=True, check=False)
                        print("🔓 macOS quarantine 제거 완료")
                    except:
                        pass
                        
            except Exception as e:
                print(f"⚠️ ChromeDriver 권한 설정 중 오류: {e}")
    else:
        print("ℹ️ ChromeDriver가 없습니다. WebDriverManager가 자동 다운로드할 예정입니다.")
    
    return True

def run_application(python_path):
    """애플리케이션 실행"""
    print("🚀 블로그 자동화 도구 시작 중...")
    print()
    print("=" * 60)
    
    try:
        # 애플리케이션 실행
        result = subprocess.run([str(python_path), 'blog_writer_app.py'])
        return result.returncode
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
        return 1
    except Exception as e:
        print(f"❌ 애플리케이션 실행 중 오류: {e}")
        return 1

def main():
    """메인 함수"""
    try:
        # 플랫폼 감지
        platform_info = detect_platform()
        
        # 헤더 출력
        print_header(platform_info)
        
        # 환경 확인
        if not check_environment():
            print("\n❌ 환경 확인 실패. 설정을 확인하고 다시 시도하세요.")
            return 1
        
        print()
        
        # 가상 환경 설정
        python_path = setup_virtual_environment(platform_info)
        if not python_path:
            print("\n❌ 가상 환경 설정 실패.")
            return 1
        
        print()
        
        # ChromeDriver 설정
        if not setup_chromedriver(platform_info):
            print("\n❌ ChromeDriver 설정 실패.")
            return 1
        
        print()
        
        # 애플리케이션 실행
        exit_code = run_application(python_path)
        
        print()
        print("=" * 60)
        if exit_code == 0:
            print("✅ 애플리케이션이 정상적으로 종료되었습니다.")
        else:
            print(f"❌ 애플리케이션이 오류와 함께 종료되었습니다. (코드: {exit_code})")
        print("=" * 60)
        
        return exit_code
        
    except Exception as e:
        print(f"❌ 예상치 못한 오류 발생: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    
    # Windows에서는 키 입력 대기
    if platform.system().lower() == 'windows':
        input("\n아무 키나 눌러서 종료하세요...")
    
    sys.exit(exit_code) 