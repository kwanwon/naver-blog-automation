#!/usr/bin/env python3
"""
크로스 플랫폼 블로그 자동화 도구 - 초기 설정 스크립트
Windows, macOS, Linux 환경 자동 설정

사용법:
    python setup_cross_platform.py [--check-only]
"""

import os
import sys
import platform
import subprocess
import json
import shutil
from pathlib import Path
import argparse

class CrossPlatformSetup:
    def __init__(self):
        self.platform_info = self.detect_platform()
        self.script_dir = Path(__file__).parent.absolute()
        self.project_root = self.script_dir
        
    def detect_platform(self):
        """플랫폼 감지 및 정보 수집"""
        system = platform.system()
        machine = platform.machine()
        
        info = {
            'system': system,
            'system_lower': system.lower(),
            'machine': machine,
            'machine_lower': machine.lower(),
            'python_version': platform.python_version(),
            'python_implementation': platform.python_implementation(),
            'platform_string': platform.platform(),
            'is_windows': system.lower() == 'windows',
            'is_macos': system.lower() == 'darwin',
            'is_linux': system.lower() == 'linux',
            'is_64bit': '64' in machine or machine.lower() in ['amd64', 'x86_64', 'arm64', 'aarch64'],
            'is_arm': 'arm' in machine.lower() or 'aarch' in machine.lower(),
            'is_intel': 'intel' in machine.lower() or 'x86' in machine.lower() or 'amd64' in machine.lower()
        }
        
        return info
    
    def print_platform_info(self):
        """플랫폼 정보 출력"""
        print("🌍 플랫폼 정보:")
        print(f"  💻 운영체제: {self.platform_info['system']}")
        print(f"  🔧 아키텍처: {self.platform_info['machine']}")
        print(f"  🐍 Python 버전: {self.platform_info['python_version']}")
        print(f"  📦 Python 구현: {self.platform_info['python_implementation']}")
        print(f"  🏷️ 플랫폼: {self.platform_info['platform_string']}")
        
        # 특수 환경 표시
        special_env = []
        if self.platform_info['is_arm']:
            special_env.append("ARM 프로세서")
        if self.platform_info['is_64bit']:
            special_env.append("64bit 시스템")
        
        if special_env:
            print(f"  ⭐ 특수 환경: {', '.join(special_env)}")
    
    def check_python_version(self):
        """Python 버전 확인"""
        print("\n🐍 Python 환경 확인:")
        
        min_version = (3, 8)
        current_version = sys.version_info[:2]
        
        if current_version >= min_version:
            print(f"  ✅ Python {'.'.join(map(str, current_version))} (최소 요구: {'.'.join(map(str, min_version))})")
            return True
        else:
            print(f"  ❌ Python {'.'.join(map(str, current_version))} (최소 요구: {'.'.join(map(str, min_version))})")
            print(f"  🔄 Python을 업그레이드해야 합니다.")
            return False
    
    def check_dependencies(self):
        """필수 의존성 확인"""
        print("\n📦 의존성 확인:")
        
        required_packages = [
            'pip',
            'setuptools',
            'wheel'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
                print(f"  ✅ {package}")
            except ImportError:
                print(f"  ❌ {package} (누락)")
                missing_packages.append(package)
        
        return len(missing_packages) == 0, missing_packages
    
    def check_system_tools(self):
        """시스템 도구 확인"""
        print("\n🔧 시스템 도구 확인:")
        
        tools = {
            'git': 'Git 버전 관리',
            'pip': 'Python 패키지 관리자'
        }
        
        if self.platform_info['is_windows']:
            tools.update({
                'powershell': 'PowerShell',
                'cmd': '명령 프롬프트'
            })
        else:
            tools.update({
                'bash': 'Bash 셸',
                'curl': 'cURL 다운로더'
            })
        
        available_tools = {}
        
        for tool, description in tools.items():
            try:
                result = subprocess.run([tool, '--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"  ✅ {tool}: {description}")
                    available_tools[tool] = True
                else:
                    print(f"  ❌ {tool}: {description} (사용 불가)")
                    available_tools[tool] = False
            except (subprocess.TimeoutExpired, FileNotFoundError):
                print(f"  ❌ {tool}: {description} (설치되지 않음)")
                available_tools[tool] = False
        
        return available_tools
    
    def setup_virtual_environment(self):
        """가상 환경 설정"""
        print("\n🏠 가상 환경 설정:")
        
        venv_path = self.project_root / 'venv'
        
        if venv_path.exists():
            print(f"  ℹ️ 기존 가상 환경 발견: {venv_path}")
            return True
        
        try:
            print(f"  🔨 가상 환경 생성 중: {venv_path}")
            subprocess.run([sys.executable, '-m', 'venv', str(venv_path)], 
                         check=True, capture_output=True)
            print("  ✅ 가상 환경 생성 완료")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  ❌ 가상 환경 생성 실패: {e}")
            return False
    
    def get_activation_command(self):
        """플랫폼별 가상 환경 활성화 명령어 반환"""
        venv_path = self.project_root / 'venv'
        
        if self.platform_info['is_windows']:
            return str(venv_path / 'Scripts' / 'activate.bat')
        else:
            return f"source {venv_path / 'bin' / 'activate'}"
    
    def install_requirements(self, use_cross_platform=True):
        """요구사항 설치"""
        print("\n📥 패키지 설치:")
        
        req_file = 'requirements_cross_platform.txt' if use_cross_platform else 'requirements.txt'
        req_path = self.project_root / req_file
        
        if not req_path.exists():
            print(f"  ❌ 요구사항 파일을 찾을 수 없습니다: {req_file}")
            return False
        
        venv_path = self.project_root / 'venv'
        
        # 가상 환경의 pip 경로
        if self.platform_info['is_windows']:
            pip_path = venv_path / 'Scripts' / 'pip.exe'
        else:
            pip_path = venv_path / 'bin' / 'pip'
        
        # pip가 없으면 시스템 pip 사용
        if not pip_path.exists():
            pip_path = 'pip'
        
        try:
            print(f"  📦 {req_file}에서 패키지 설치 중...")
            
            cmd = [str(pip_path), 'install', '-r', str(req_path), '--upgrade']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print("  ✅ 패키지 설치 완료")
                return True
            else:
                print(f"  ❌ 패키지 설치 실패:")
                print(f"    {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("  ⏰ 패키지 설치 시간 초과")
            return False
        except Exception as e:
            print(f"  ❌ 패키지 설치 중 오류: {e}")
            return False
    
    def setup_chromedriver(self):
        """ChromeDriver 설정"""
        print("\n🚗 ChromeDriver 설정:")
        
        # 기존 ChromeDriver 확인
        chromedriver_files = ['chromedriver', 'chromedriver.exe']
        
        found_driver = False
        for driver_file in chromedriver_files:
            driver_path = self.project_root / driver_file
            if driver_path.exists():
                print(f"  ✅ 기존 ChromeDriver 발견: {driver_path}")
                
                # Unix 계열에서 실행 권한 확인
                if not self.platform_info['is_windows']:
                    current_mode = driver_path.stat().st_mode
                    if not (current_mode & 0o111):  # 실행 권한이 없으면
                        try:
                            os.chmod(driver_path, 0o755)
                            print(f"  🔑 실행 권한 부여: {driver_path}")
                        except Exception as e:
                            print(f"  ⚠️ 실행 권한 부여 실패: {e}")
                
                found_driver = True
                break
        
        if not found_driver:
            print("  ℹ️ ChromeDriver가 없습니다. WebDriverManager가 자동 다운로드할 예정입니다.")
        
        return True
    
    def create_config_files(self):
        """기본 설정 파일 생성"""
        print("\n⚙️ 설정 파일 생성:")
        
        config_dir = self.project_root / 'config'
        config_dir.mkdir(exist_ok=True)
        
        # 플랫폼 정보 저장
        platform_config = self.project_root / 'config' / 'platform_info.json'
        
        try:
            with open(platform_config, 'w', encoding='utf-8') as f:
                json.dump(self.platform_info, f, indent=2, ensure_ascii=False)
            print(f"  ✅ 플랫폼 정보 저장: {platform_config}")
        except Exception as e:
            print(f"  ❌ 플랫폼 정보 저장 실패: {e}")
        
        # 환경별 설정 파일 생성
        env_config = {
            'platform': self.platform_info['system_lower'],
            'setup_date': platform.uname().system,
            'python_version': self.platform_info['python_version'],
            'project_root': str(self.project_root)
        }
        
        env_config_file = self.project_root / 'config' / 'environment.json'
        
        try:
            with open(env_config_file, 'w', encoding='utf-8') as f:
                json.dump(env_config, f, indent=2, ensure_ascii=False)
            print(f"  ✅ 환경 설정 저장: {env_config_file}")
        except Exception as e:
            print(f"  ❌ 환경 설정 저장 실패: {e}")
        
        return True
    
    def print_next_steps(self):
        """다음 단계 안내"""
        print("\n🚀 설정 완료! 다음 단계:")
        print("\n1️⃣ 가상 환경 활성화:")
        activation_cmd = self.get_activation_command()
        print(f"   {activation_cmd}")
        
        print("\n2️⃣ 애플리케이션 실행:")
        print("   python blog_writer_app.py")
        
        print("\n3️⃣ 크로스 플랫폼 빌드 (선택사항):")
        print("   python build_cross_platform.py")
        
        print("\n4️⃣ 플랫폼별 빌드:")
        print("   python build_cross_platform.py --platform windows")
        print("   python build_cross_platform.py --platform macos")
        print("   python build_cross_platform.py --platform linux")
    
    def run_check_only(self):
        """시스템 확인만 실행"""
        print("🔍 시스템 확인 모드")
        print("=" * 50)
        
        self.print_platform_info()
        python_ok = self.check_python_version()
        deps_ok, missing = self.check_dependencies()
        tools = self.check_system_tools()
        
        print("\n📋 확인 결과:")
        if python_ok and deps_ok:
            print("  ✅ 시스템이 요구사항을 만족합니다!")
        else:
            print("  ❌ 시스템에 문제가 있습니다:")
            if not python_ok:
                print("    - Python 버전이 너무 낮습니다")
            if not deps_ok:
                print(f"    - 누락된 패키지: {', '.join(missing)}")
        
        return python_ok and deps_ok
    
    def run_full_setup(self):
        """전체 설정 실행"""
        print("🛠️ 크로스 플랫폼 설정 시작")
        print("=" * 50)
        
        self.print_platform_info()
        
        # 1. 기본 확인
        if not self.check_python_version():
            print("\n❌ Python 버전이 요구사항을 만족하지 않습니다.")
            return False
        
        deps_ok, missing = self.check_dependencies()
        if not deps_ok:
            print(f"\n⚠️ 누락된 기본 패키지: {', '.join(missing)}")
            print("pip install --upgrade pip setuptools wheel 명령어로 설치하세요.")
        
        # 2. 시스템 도구 확인
        self.check_system_tools()
        
        # 3. 가상 환경 설정
        if not self.setup_virtual_environment():
            print("\n❌ 가상 환경 설정 실패")
            return False
        
        # 4. 요구사항 설치
        if not self.install_requirements():
            print("\n❌ 패키지 설치 실패")
            return False
        
        # 5. ChromeDriver 설정
        self.setup_chromedriver()
        
        # 6. 설정 파일 생성
        self.create_config_files()
        
        # 7. 다음 단계 안내
        self.print_next_steps()
        
        print("\n🎉 크로스 플랫폼 설정 완료!")
        return True

def main():
    parser = argparse.ArgumentParser(
        description="크로스 플랫폼 블로그 자동화 도구 설정"
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help="시스템 확인만 실행 (설치하지 않음)"
    )
    
    args = parser.parse_args()
    
    setup = CrossPlatformSetup()
    
    if args.check_only:
        success = setup.run_check_only()
    else:
        success = setup.run_full_setup()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 