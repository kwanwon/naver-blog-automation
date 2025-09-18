#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macOS용 블로그 자동화 프로그램 빌드 스크립트
PyInstaller를 사용하여 macOS .app 번들을 생성합니다.
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path

class MacOSBuilder:
    def __init__(self):
        self.app_name = "블로그자동화"
        self.app_version = "1.4.0"
        self.build_dir = "build"
        self.dist_dir = "dist"
        self.spec_file = f"{self.app_name}.spec"
        
        # 현재 디렉토리
        self.current_dir = Path(__file__).parent
        self.main_script = self.current_dir / "blog_writer_app.py"
        self.icon_file = self.current_dir / "icons" / "blog_automation.icns"
        
        print(f"🍎 macOS 빌드 환경 설정")
        print(f"앱 이름: {self.app_name}")
        print(f"버전: {self.app_version}")
        print(f"메인 스크립트: {self.main_script}")
        print(f"아이콘 파일: {self.icon_file}")
    
    def check_requirements(self):
        """빌드 요구사항 확인"""
        print("\n🔍 빌드 요구사항 확인 중...")
        
        # Python 버전 확인
        python_version = sys.version_info
        print(f"Python 버전: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        if python_version < (3, 7):
            print("❌ Python 3.7 이상이 필요합니다.")
            return False
        
        # PyInstaller 확인
        try:
            import PyInstaller
            print(f"✅ PyInstaller 버전: {PyInstaller.__version__}")
        except ImportError:
            print("❌ PyInstaller가 설치되지 않았습니다.")
            return False
        
        # 메인 스크립트 확인
        if not self.main_script.exists():
            print(f"❌ 메인 스크립트를 찾을 수 없습니다: {self.main_script}")
            return False
        print(f"✅ 메인 스크립트 확인: {self.main_script}")
        
        # 아이콘 파일 확인
        if not self.icon_file.exists():
            print(f"❌ 아이콘 파일을 찾을 수 없습니다: {self.icon_file}")
            return False
        print(f"✅ 아이콘 파일 확인: {self.icon_file}")
        
        # 플랫폼 확인
        if platform.system() != "Darwin":
            print("⚠️ macOS가 아닌 환경에서 빌드 중입니다.")
        
        print("✅ 모든 요구사항이 충족되었습니다.")
        return True
    
    def clean_build(self):
        """이전 빌드 정리"""
        print("\n🧹 이전 빌드 정리 중...")
        
        dirs_to_clean = [self.build_dir, self.dist_dir]
        files_to_clean = [self.spec_file]
        
        for dir_path in dirs_to_clean:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
                print(f"✅ 디렉토리 삭제: {dir_path}")
        
        for file_path in files_to_clean:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"✅ 파일 삭제: {file_path}")
    
    def create_spec_file(self):
        """PyInstaller spec 파일 생성"""
        print("\n📝 PyInstaller spec 파일 생성 중...")
        
        # 존재하는 파일들만 datas에 포함
        datas = [
            ('config', 'config'),
            ('modules', 'modules'),
            ('icons', 'icons'),
            ('version.json', '.'),
            ('requirements.txt', '.'),
        ]
        
        # 이미지 폴더들 추가 (default_images와 default_images_1~10)
        image_folders = ['default_images']
        for i in range(1, 11):
            image_folders.append(f'default_images_{i}')
        
        for folder in image_folders:
            if os.path.exists(folder):
                datas.append((folder, folder))
                print(f"✅ 포함할 이미지 폴더: {folder}")
            else:
                print(f"⚠️ 건너뛸 이미지 폴더: {folder} (존재하지 않음)")
        
        # 선택적 파일들 확인
        optional_files = [
            'naver_cookies.pkl',
            'naver_session.json',
            '.env',  # 환경변수 파일 포함
            'user_data.json',
            'config.json',
            'settings.json',
            'gpt_settings.txt',
            'app_settings.json',
            'naver_api_config.py',
            'device_info.json',
            'programs.json',
            'topic_index.json',
            'used_folders.json',
            'current_folder_index.txt',
            'custom_prompts.txt',
            'image_positions.json',
            'naver_blog_auto_image.py',  # 이미지 삽입 모듈
            'folder_manager.py',  # 폴더 관리 모듈
        ]
        
        for file_name in optional_files:
            if os.path.exists(file_name):
                datas.append((file_name, '.'))
                print(f"✅ 포함할 파일: {file_name}")
            else:
                print(f"⚠️ 건너뛸 파일: {file_name} (존재하지 않음)")
        
        # config 폴더 내의 모든 파일들도 개별적으로 포함
        config_files = [
            'config/gpt_settings.txt',
            'config/app_settings.json',
            'config/naver_api_config.py',
            'config/device_info.json',
            'config/programs.json',
            'config/topic_index.json',
            'config/used_folders.json',
            'config/current_folder_index.txt',
            'config/custom_prompts.txt',
            'config/image_positions.json',
        ]
        
        for file_path in config_files:
            if os.path.exists(file_path):
                # config 폴더 내 파일은 config/ 경로로 포함
                datas.append((file_path, 'config'))
                print(f"✅ 포함할 설정 파일: {file_path}")
            else:
                print(f"⚠️ 건너뛸 설정 파일: {file_path} (존재하지 않음)")
        
        # datas 리스트를 문자열로 변환
        datas_str = "[\n"
        for item in datas:
            datas_str += f"    {item},\n"
        datas_str += "]"
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 데이터 파일들
datas = {datas_str}

# 숨겨진 임포트들 (모든 의존성 포함)
hiddenimports = [
    'flet',
    'flet.fastapi',
    'flet.controls',
    'flet.page',
    'openai',
    'openai.types',
    'requests',
    'requests.adapters',
    'requests.auth',
    'requests.cookies',
    'requests.exceptions',
    'requests.models',
    'requests.sessions',
    'requests.utils',
    'selenium',
    'selenium.webdriver',
    'selenium.webdriver.chrome',
    'selenium.webdriver.common',
    'selenium.webdriver.common.by',
    'selenium.webdriver.common.keys',
    'selenium.webdriver.support',
    'selenium.webdriver.support.ui',
    'selenium.webdriver.support.wait',
    'selenium.common.exceptions',
    'beautifulsoup4',
    'bs4',
    'bs4.builder',
    'bs4.builder._html5lib',
    'bs4.builder._htmlparser',
    'bs4.builder._lxml',
    'psutil',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'PIL.ImageTk',  # 이미지 처리
    'PIL.ImageOps',  # 이미지 연산
    'PIL.ImageEnhance',  # 이미지 향상
    'sqlite3',
    'json',
    'datetime',
    'threading',
    'subprocess',
    'platform',
    'socket',
    'wmi',  # Windows용
    'pathlib',
    'os',
    'sys',
    'logging',
    'dotenv',  # 환경변수 로딩
    'python-dotenv',
    'flet_desktop',  # Flet 데스크톱 버전
    'flet_desktop.install',
    'selenium',  # 웹 브라우저 자동화
    'selenium.webdriver',
    'selenium.webdriver.chrome',
    'selenium.webdriver.common',
    'selenium.webdriver.support',
    'webdriver_manager',  # ChromeDriver 자동 관리
    'webdriver_manager.chrome',
    'naver_blog_auto_image',  # 이미지 삽입 모듈
    'folder_manager',  # 폴더 관리 모듈
    'tempfile',
    'zipfile',
    'shutil',
    'time',
    'random',
    're',
    'urllib',
    'urllib.parse',
    'urllib.request',
    'http',
    'http.client',
    'ssl',
    'certifi',
    'charset_normalizer',
    'idna',
    'urllib3',
    'packaging',
    'packaging.version',
    'packaging.specifiers',
    'packaging.requirements',
]

# 제외할 모듈들
excludes = [
    'tkinter',
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'jupyter',
    'IPython',
]

a = Analysis(
    ['{self.main_script.name}'],
    pathex=['{self.current_dir}'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{self.app_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 모드
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{self.icon_file}',
)

app = BUNDLE(
    exe,
    name='{self.app_name}.app',
    icon='{self.icon_file}',
    bundle_identifier='com.liondeveloper.blogautomation',
    version='{self.app_version}',
    info_plist={{
        'CFBundleName': '{self.app_name}',
        'CFBundleDisplayName': '{self.app_name}',
        'CFBundleIdentifier': 'com.liondeveloper.blogautomation',
        'CFBundleVersion': '{self.app_version}',
        'CFBundleShortVersionString': '{self.app_version}',
        'CFBundleInfoDictionaryVersion': '6.0',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'LSMinimumSystemVersion': '10.13',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'NSAppleScriptEnabled': False,
        'NSSupportsAutomaticGraphicsSwitching': True,
    }},
)
'''
        
        with open(self.spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        print(f"✅ spec 파일 생성 완료: {self.spec_file}")
    
    def build_app(self):
        """앱 빌드 실행"""
        print("\n🔨 앱 빌드 시작...")
        
        try:
            # PyInstaller 실행
            cmd = [
                'pyinstaller',
                '--clean',
                '--noconfirm',
                self.spec_file
            ]
            
            print(f"실행 명령어: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=self.current_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 빌드 성공!")
                return True
            else:
                print("❌ 빌드 실패!")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ 빌드 중 오류 발생: {e}")
            return False
    
    def post_build_setup(self):
        """빌드 후 설정"""
        print("\n🔧 빌드 후 설정 중...")
        
        app_path = self.current_dir / self.dist_dir / f"{self.app_name}.app"
        
        if not app_path.exists():
            print(f"❌ 앱 번들을 찾을 수 없습니다: {app_path}")
            return False
        
        # 앱 번들 내부 구조 확인
        contents_path = app_path / "Contents"
        macos_path = contents_path / "MacOS"
        resources_path = contents_path / "Resources"
        
        print(f"✅ 앱 번들 생성 완료: {app_path}")
        print(f"  - Contents: {contents_path.exists()}")
        print(f"  - MacOS: {macos_path.exists()}")
        print(f"  - Resources: {resources_path.exists()}")
        
        # 실행 권한 설정
        executable_path = macos_path / self.app_name
        if executable_path.exists():
            os.chmod(executable_path, 0o755)
            print(f"✅ 실행 권한 설정: {executable_path}")
        
        # 앱 크기 확인
        app_size = self._get_directory_size(app_path)
        print(f"📦 앱 크기: {app_size:.2f} MB")
        
        return True
    
    def _get_directory_size(self, directory):
        """디렉토리 크기 계산 (MB)"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size / (1024 * 1024)  # MB로 변환
    
    def create_dmg(self):
        """DMG 파일 생성 (선택사항)"""
        print("\n💿 DMG 파일 생성 중...")
        
        try:
            app_path = self.current_dir / self.dist_dir / f"{self.app_name}.app"
            dmg_path = self.current_dir / f"{self.app_name}_v{self.app_version}.dmg"
            
            # create-dmg 도구 사용 (설치 필요)
            cmd = [
                'create-dmg',
                '--volname', f'{self.app_name} {self.app_version}',
                '--volicon', str(self.icon_file),
                '--window-pos', '200', '120',
                '--window-size', '600', '300',
                '--icon-size', '100',
                '--icon', f'{self.app_name}.app', '175', '120',
                '--hide-extension', f'{self.app_name}.app',
                '--app-drop-link', '425', '120',
                str(dmg_path),
                str(app_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ DMG 파일 생성 완료: {dmg_path}")
                return True
            else:
                print("⚠️ DMG 생성 실패 (create-dmg 도구가 필요합니다)")
                print("STDERR:", result.stderr)
                return False
                
        except FileNotFoundError:
            print("⚠️ create-dmg 도구를 찾을 수 없습니다.")
            print("설치 방법: brew install create-dmg")
            return False
        except Exception as e:
            print(f"❌ DMG 생성 중 오류: {e}")
            return False
    
    def run_build(self):
        """전체 빌드 프로세스 실행"""
        print("🚀 macOS 빌드 프로세스 시작!")
        print("=" * 50)
        
        # 1. 요구사항 확인
        if not self.check_requirements():
            return False
        
        # 2. 이전 빌드 정리
        self.clean_build()
        
        # 3. spec 파일 생성
        self.create_spec_file()
        
        # 4. 앱 빌드
        if not self.build_app():
            return False
        
        # 5. 빌드 후 설정
        if not self.post_build_setup():
            return False
        
        # 6. DMG 생성 (선택사항)
        self.create_dmg()
        
        print("\n🎉 macOS 빌드 완료!")
        print("=" * 50)
        print(f"📦 앱 번들: {self.current_dir / self.dist_dir / f'{self.app_name}.app'}")
        print(f"📁 빌드 디렉토리: {self.current_dir / self.build_dir}")
        print(f"📁 배포 디렉토리: {self.current_dir / self.dist_dir}")
        
        return True

if __name__ == "__main__":
    builder = MacOSBuilder()
    success = builder.run_build()
    
    if success:
        print("\n✅ 빌드가 성공적으로 완료되었습니다!")
        sys.exit(0)
    else:
        print("\n❌ 빌드가 실패했습니다.")
        sys.exit(1)
