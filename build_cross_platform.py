#!/usr/bin/env python3
"""
크로스 플랫폼 블로그 자동화 도구 빌드 스크립트
Windows, macOS, Linux 모든 플랫폼 지원

사용법:
    python build_cross_platform.py [--platform TARGET_PLATFORM]
    
예시:
    python build_cross_platform.py              # 현재 플랫폼용 빌드
    python build_cross_platform.py --platform windows
    python build_cross_platform.py --platform macos
    python build_cross_platform.py --platform linux
"""

import os
import sys
import shutil
import subprocess
import platform
import argparse
from pathlib import Path
import json

class CrossPlatformBuilder:
    def __init__(self, target_platform=None):
        self.host_system = platform.system().lower()
        self.host_machine = platform.machine().lower()
        self.target_platform = target_platform or self.host_system
        
        # 플랫폼 매핑
        self.platform_map = {
            'windows': 'windows',
            'win32': 'windows', 
            'win': 'windows',
            'darwin': 'macos',
            'macos': 'macos',
            'mac': 'macos',
            'linux': 'linux',
            'linux2': 'linux'
        }
        
        self.target_platform = self.platform_map.get(self.target_platform.lower(), self.target_platform.lower())
        
        self.script_dir = Path(__file__).parent.absolute()
        self.project_root = self.script_dir
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        
        print(f"🌍 호스트 플랫폼: {platform.system()} ({platform.machine()})")
        print(f"🎯 타겟 플랫폼: {self.target_platform}")
        print(f"📂 프로젝트 루트: {self.project_root}")
        
    def clean_build_dirs(self):
        """기존 빌드 디렉토리들 정리"""
        print("🧹 기존 빌드 디렉토리 정리 중...")
        
        for directory in [self.build_dir, self.dist_dir]:
            if directory.exists():
                print(f"  삭제 중: {directory}")
                shutil.rmtree(directory)
        
        # __pycache__ 디렉토리도 정리
        for pycache in self.project_root.rglob("__pycache__"):
            if pycache.is_dir():
                print(f"  캐시 삭제: {pycache}")
                shutil.rmtree(pycache)
                
    def setup_chromedriver(self):
        """플랫폼별 ChromeDriver 설정"""
        print("🚗 ChromeDriver 설정 중...")
        
        chromedriver_files = {
            'windows': ['chromedriver.exe', 'chromedriver'],
            'macos': ['chromedriver', 'chromedriver-mac-arm64/chromedriver'],
            'linux': ['chromedriver', 'chromedriver-linux64/chromedriver']
        }
        
        found_driver = False
        for driver_name in chromedriver_files.get(self.target_platform, ['chromedriver']):
            driver_path = self.project_root / driver_name
            if driver_path.exists():
                print(f"  ✅ ChromeDriver 발견: {driver_path}")
                # Unix 계열에서 실행 권한 부여
                if self.target_platform in ['macos', 'linux']:
                    os.chmod(driver_path, 0o755)
                    print(f"  🔑 실행 권한 부여: {driver_path}")
                found_driver = True
                break
        
        if not found_driver:
            print("  ⚠️ ChromeDriver를 찾을 수 없습니다.")
            print("    WebDriverManager가 자동으로 다운로드할 예정입니다.")
        
        return found_driver
    
    def get_app_icon(self):
        """플랫폼별 앱 아이콘 경로 반환"""
        icon_extensions = {
            'windows': '.ico',
            'macos': '.icns', 
            'linux': '.png'
        }
        
        icon_ext = icon_extensions.get(self.target_platform, '.png')
        icon_path = self.project_root / 'build_resources' / f'app_icon{icon_ext}'
        
        # 아이콘이 없으면 PNG를 기본으로 사용
        if not icon_path.exists():
            png_icon = self.project_root / 'build_resources' / 'app_icon.png'
            if png_icon.exists():
                print(f"  📸 기본 PNG 아이콘 사용: {png_icon}")
                return str(png_icon)
            else:
                print("  ⚠️ 앱 아이콘을 찾을 수 없습니다.")
                return None
        
        print(f"  🎨 앱 아이콘: {icon_path}")
        return str(icon_path)
    
    def collect_data_files(self):
        """빌드에 포함할 데이터 파일들 수집"""
        print("📦 데이터 파일 수집 중...")
        
        data_mappings = []
        
        # 기본 데이터 디렉토리들
        data_dirs = [
            'config',
            'modules', 
            'utils',
            'default_images',
            'build_resources'
        ]
        
        # 이미지 폴더들 (1-10)
        for i in range(1, 11):
            data_dirs.append(f'default_images_{i}')
        
        # 존재하는 디렉토리만 추가
        for data_dir in data_dirs:
            dir_path = self.project_root / data_dir
            if dir_path.exists():
                data_mappings.append((str(dir_path), data_dir))
                print(f"  📁 {data_dir}")
        
        # 개별 파일들
        data_files = [
            'naver_blog_auto.py',
            'naver_blog_auto_image.py', 
            'naver_blog_post_finisher.py',
            'manual_session_helper.py',
            'manual_login_helper.py',
            'setup_chrome_permissions.py',
            'chromedriver'
        ]
        
        # ChromeDriver 플랫폼별 추가
        if self.target_platform == 'windows':
            data_files.append('chromedriver.exe')
        elif self.target_platform == 'macos':
            data_files.extend(['chromedriver-mac-arm64/chromedriver'])
        
        # 존재하는 파일만 추가
        for data_file in data_files:
            file_path = self.project_root / data_file
            if file_path.exists():
                data_mappings.append((str(file_path), '.'))
                print(f"  📄 {data_file}")
        
        # .env 파일 (있다면)
        env_file = self.project_root / '.env'
        if env_file.exists():
            data_mappings.append((str(env_file), '.'))
            print(f"  🔐 .env")
        
        return data_mappings
    
    def get_hidden_imports(self):
        """숨겨진 import 모듈들 반환"""
        return [
            # GUI
            'flet', 'flet.core', 'flet.app',
            
            # 웹 자동화
            'selenium', 'selenium.webdriver', 'selenium.webdriver.chrome',
            'selenium.webdriver.common', 'selenium.webdriver.support',
            'webdriver_manager', 'webdriver_manager.chrome',
            
            # 이미지 처리
            'PIL', 'PIL.Image', 'PIL.ImageTk',
            
            # 네트워크
            'requests', 'urllib3', 'httpx',
            
            # AI/ML
            'openai',
            
            # 시스템
            'psutil', 'platform', 'subprocess',
            
            # 데이터 처리  
            'json', 'yaml', 'csv',
            'pandas', 'numpy',
            
            # 자연어 처리
            'nltk', 'konlpy', 'jpype1',
            
            # 날짜/시간
            'datetime', 'dateutil',
            
            # 암호화
            'cryptography',
            
            # 환경 변수
            'dotenv',
            
            # 플랫폼별 모듈
            'win32api' if self.target_platform == 'windows' else None,
            'AppKit' if self.target_platform == 'macos' else None,
            'Xlib' if self.target_platform == 'linux' else None,
        ]
    
    def build_pyinstaller_command(self):
        """PyInstaller 명령어 생성"""
        print("⚙️ PyInstaller 명령어 생성 중...")
        
        # 기본 명령어
        cmd = ['pyinstaller']
        
        # 출력 설정
        app_name = f"BlogAutomation_{self.target_platform.title()}"
        cmd.extend(['--name', app_name])
        
        # 빌드 옵션
        cmd.extend([
            '--windowed',      # GUI 모드 (콘솔 숨김)
            '--onedir',        # 디렉토리 형태로 빌드
            '--clean',         # 이전 빌드 캐시 정리
            '--noconfirm',     # 확인 없이 덮어쓰기
        ])
        
        # 아이콘 설정
        icon_path = self.get_app_icon()
        if icon_path:
            cmd.extend(['--icon', icon_path])
        
        # 숨겨진 import 추가
        hidden_imports = [imp for imp in self.get_hidden_imports() if imp is not None]
        for imp in hidden_imports:
            cmd.extend(['--hidden-import', imp])
        
        # 데이터 파일 추가
        data_mappings = self.collect_data_files()
        separator = ';' if self.target_platform == 'windows' else ':'
        
        for src, dst in data_mappings:
            cmd.extend(['--add-data', f'{src}{separator}{dst}'])
        
        # 플랫폼별 추가 옵션
        if self.target_platform == 'macos':
            cmd.extend([
                '--osx-bundle-identifier', 'com.lion.blogautomation',
                '--codesign-identity', '-'  # 임시 서명
            ])
        elif self.target_platform == 'windows':
            cmd.extend([
                '--version-file', str(self.project_root / 'build_resources' / 'version_info.txt')
            ]) if (self.project_root / 'build_resources' / 'version_info.txt').exists() else None
        
        # 메인 스크립트
        cmd.append(str(self.project_root / 'blog_writer_app.py'))
        
        return cmd
    
    def run_build(self):
        """빌드 실행"""
        print("🔨 빌드 시작...")
        
        cmd = self.build_pyinstaller_command()
        
        print("📋 실행 명령어:")
        print(f"  {' '.join(cmd)}")
        
        try:
            # PyInstaller 실행
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            print("✅ 빌드 성공!")
            
            # 결과 파일 경로 출력
            app_name = f"BlogAutomation_{self.target_platform.title()}"
            
            if self.target_platform == 'macos':
                result_path = self.dist_dir / f"{app_name}.app"
            elif self.target_platform == 'windows':
                result_path = self.dist_dir / app_name / f"{app_name}.exe"
            else:  # Linux
                result_path = self.dist_dir / app_name / app_name
            
            if result_path.exists():
                print(f"📱 생성된 앱: {result_path.absolute()}")
                
                # 파일 크기 출력
                if result_path.is_file():
                    size_mb = result_path.stat().st_size / (1024 * 1024)
                    print(f"📏 앱 크기: {size_mb:.1f}MB")
                elif result_path.is_dir():
                    total_size = sum(f.stat().st_size for f in result_path.rglob('*') if f.is_file())
                    size_mb = total_size / (1024 * 1024)
                    print(f"📏 앱 크기: {size_mb:.1f}MB")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print("❌ 빌드 실패!")
            print(f"에러 출력: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {str(e)}")
            return False
    
    def create_distribution_info(self):
        """배포 정보 파일 생성"""
        print("📋 배포 정보 생성 중...")
        
        info = {
            "app_name": "Blog Automation Tool",
            "version": "1.0.0",
            "build_platform": self.host_system,
            "target_platform": self.target_platform,
            "build_date": platform.uname().system,
            "python_version": platform.python_version(),
            "requirements": "requirements_cross_platform.txt"
        }
        
        info_file = self.dist_dir / "build_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        
        print(f"📄 빌드 정보: {info_file}")
    
    def run_full_build(self):
        """전체 빌드 프로세스 실행"""
        print("=" * 60)
        print("🚀 크로스 플랫폼 블로그 자동화 도구 빌드 시작")
        print("=" * 60)
        
        try:
            # 1. 빌드 디렉토리 정리
            self.clean_build_dirs()
            
            # 2. ChromeDriver 설정
            self.setup_chromedriver()
            
            # 3. 빌드 실행
            if self.run_build():
                # 4. 배포 정보 생성
                self.create_distribution_info()
                
                print("=" * 60)
                print("🎉 빌드 완료!")
                print("=" * 60)
                return True
            else:
                print("=" * 60)
                print("💥 빌드 실패!")
                print("=" * 60)
                return False
                
        except Exception as e:
            print(f"❌ 빌드 프로세스 중 오류 발생: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(
        description="크로스 플랫폼 블로그 자동화 도구 빌드"
    )
    parser.add_argument(
        '--platform',
        choices=['windows', 'macos', 'linux'],
        help="타겟 플랫폼 (기본값: 현재 플랫폼)"
    )
    
    args = parser.parse_args()
    
    builder = CrossPlatformBuilder(args.platform)
    success = builder.run_full_build()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 