#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows용 블로그 자동화 프로그램 빌드 스크립트
PyInstaller를 사용하여 Windows 실행 파일을 생성합니다.
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path

class WindowsBuilder:
    def __init__(self):
        self.app_name = "블로그자동화"
        self.app_version = "1.4.0"
        self.build_dir = "build"
        self.dist_dir = "dist"
        self.spec_file = f"{self.app_name}.spec"
        
        # 현재 디렉토리
        self.current_dir = Path(__file__).parent
        self.main_script = self.current_dir / "blog_writer_app.py"
        self.icon_file = self.current_dir / "icons" / "blog_automation_256x256.png"  # Windows는 PNG 사용
        
        print(f"🪟 Windows 빌드 환경 설정")
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
        
        # 아이콘 파일 확인 (PNG 또는 ICO)
        icon_found = False
        if self.icon_file.exists():
            icon_found = True
            print(f"✅ 아이콘 파일 확인: {self.icon_file}")
        else:
            # ICO 파일도 확인
            ico_file = self.current_dir / "icons" / "blog_automation.ico"
            if ico_file.exists():
                self.icon_file = ico_file
                icon_found = True
                print(f"✅ 아이콘 파일 확인: {self.icon_file}")
        
        if not icon_found:
            print(f"⚠️ 아이콘 파일을 찾을 수 없습니다. 기본 아이콘을 사용합니다.")
            self.icon_file = None
        
        # 플랫폼 확인
        if platform.system() != "Windows":
            print("⚠️ Windows가 아닌 환경에서 빌드 중입니다.")
        
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
        ]
        
        # 선택적 파일들 확인
        optional_files = [
            'naver_cookies.pkl',
            'naver_session.json', 
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
            'serials.db',  # 시리얼 인증 데이터베이스
            'serial_validator.py',  # 시리얼 검증 모듈
        ]
        
        # 시리얼 검증 패키지 폴더 추가
        if os.path.exists('serial_validator'):
            datas.append(('serial_validator', 'serial_validator'))
            print("✅ 포함할 시리얼 검증 패키지: serial_validator")
        
        for file_name in optional_files:
            if os.path.exists(file_name):
                datas.append((file_name, '.'))
                print(f"✅ 포함할 파일: {file_name}")
            else:
                print(f"⚠️ 건너뛸 파일: {file_name} (존재하지 않음)")
        
        # datas 리스트를 문자열로 변환
        datas_str = "[\n"
        for item in datas:
            datas_str += f"    {item},\n"
        datas_str += "]"
        
        # 아이콘 설정
        icon_setting = f"icon='{self.icon_file}'," if self.icon_file else ""
        
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
    'serial_validator',  # 시리얼 검증 패키지
    'serial_validator.serial_client',  # 시리얼 클라이언트
    'serial_validator.serial_ui',  # 시리얼 UI
    'serial_validator.server_check',  # 서버 체크
    'psutil',  # 시스템 정보
    'hashlib',  # 해시 함수
    'uuid',  # UUID 생성
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
    {icon_setting}
)
'''
        
        with open(self.spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        print(f"✅ spec 파일 생성 완료: {self.spec_file}")
    
    def build_exe(self):
        """실행 파일 빌드"""
        print("\n🔨 실행 파일 빌드 시작...")
        
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
        
        # 실행 파일 경로 확인 (확장자 없이 생성될 수 있음)
        exe_path = self.current_dir / self.dist_dir / f"{self.app_name}.exe"
        if not exe_path.exists():
            exe_path = self.current_dir / self.dist_dir / self.app_name
        
        if not exe_path.exists():
            print(f"❌ 실행 파일을 찾을 수 없습니다: {exe_path}")
            return False
        
        print(f"✅ 실행 파일 생성 완료: {exe_path}")
        
        # 실행 파일 크기 확인
        exe_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB로 변환
        print(f"📦 실행 파일 크기: {exe_size:.2f} MB")
        
        # 필요한 DLL 파일들 확인
        dll_files = [
            'api-ms-win-core-processthreads-l1-1-0.dll',
            'api-ms-win-core-synch-l1-2-0.dll',
            'api-ms-win-core-file-l1-2-0.dll',
        ]
        
        dist_dir = self.current_dir / self.dist_dir
        for dll in dll_files:
            dll_path = dist_dir / dll
            if dll_path.exists():
                print(f"✅ DLL 파일 확인: {dll}")
            else:
                print(f"⚠️ DLL 파일 없음: {dll}")
        
        return True
    
    def create_installer_script(self):
        """NSIS 설치 프로그램 스크립트 생성"""
        print("\n📦 NSIS 설치 프로그램 스크립트 생성 중...")
        
        nsis_script = f'''# 블로그 자동화 프로그램 설치 스크립트
# NSIS (Nullsoft Scriptable Install System) 사용

!define APP_NAME "{self.app_name}"
!define APP_VERSION "{self.app_version}"
!define APP_PUBLISHER "라이온개발자"
!define APP_URL "https://github.com/kwanwon/naver-blog-automation"
!define APP_EXECUTABLE "{self.app_name}.exe"

# 설치 프로그램 설정
Name "${{APP_NAME}}"
OutFile "{self.app_name}_v{self.app_version}_Setup.exe"
InstallDir "$PROGRAMFILES\\${{APP_NAME}}"
InstallDirRegKey HKLM "Software\\${{APP_NAME}}" "Install_Dir"
RequestExecutionLevel admin

# 압축 설정
SetCompressor /SOLID lzma

# 아이콘 설정
Icon "icons\\blog_automation_256x256.png"
UninstallIcon "icons\\blog_automation_256x256.png"

# 설치 프로그램 정보
VIProductVersion "${{APP_VERSION}}.0"
VIAddVersionKey "ProductName" "${{APP_NAME}}"
VIAddVersionKey "ProductVersion" "${{APP_VERSION}}"
VIAddVersionKey "CompanyName" "${{APP_PUBLISHER}}"
VIAddVersionKey "FileDescription" "네이버 블로그 자동화 프로그램"
VIAddVersionKey "FileVersion" "${{APP_VERSION}}"

# 설치 페이지
Page directory
Page instfiles

# 제거 페이지
UninstPage uninstConfirm
UninstPage instfiles

# 설치 섹션
Section "Main Application" SecMain
    SetOutPath "$INSTDIR"
    
    # 메인 실행 파일
    File "dist\\${{APP_EXECUTABLE}}"
    
    # 필요한 파일들
    File /r "dist\\*"
    
    # 시작 메뉴 바로가기 생성
    CreateDirectory "$SMPROGRAMS\\${{APP_NAME}}"
    CreateShortCut "$SMPROGRAMS\\${{APP_NAME}}\\${{APP_NAME}}.lnk" "$INSTDIR\\${{APP_EXECUTABLE}}"
    CreateShortCut "$SMPROGRAMS\\${{APP_NAME}}\\제거.lnk" "$INSTDIR\\Uninstall.exe"
    
    # 바탕화면 바로가기 생성
    CreateShortCut "$DESKTOP\\${{APP_NAME}}.lnk" "$INSTDIR\\${{APP_EXECUTABLE}}"
    
    # 레지스트리 항목 생성
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "DisplayName" "${{APP_NAME}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "UninstallString" "$INSTDIR\\Uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "DisplayVersion" "${{APP_VERSION}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "Publisher" "${{APP_PUBLISHER}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "URLInfoAbout" "${{APP_URL}}"
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "NoModify" 1
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "NoRepair" 1
    
    # 제거 프로그램 생성
    WriteUninstaller "$INSTDIR\\Uninstall.exe"
SectionEnd

# 제거 섹션
Section "Uninstall"
    # 파일 삭제
    Delete "$INSTDIR\\${{APP_EXECUTABLE}}"
    Delete "$INSTDIR\\Uninstall.exe"
    RMDir /r "$INSTDIR"
    
    # 바로가기 삭제
    Delete "$SMPROGRAMS\\${{APP_NAME}}\\${{APP_NAME}}.lnk"
    Delete "$SMPROGRAMS\\${{APP_NAME}}\\제거.lnk"
    RMDir "$SMPROGRAMS\\${{APP_NAME}}"
    Delete "$DESKTOP\\${{APP_NAME}}.lnk"
    
    # 레지스트리 항목 삭제
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}"
    DeleteRegKey HKLM "Software\\${{APP_NAME}}"
SectionEnd
'''
        
        nsis_file = self.current_dir / f"{self.app_name}_installer.nsi"
        with open(nsis_file, 'w', encoding='utf-8') as f:
            f.write(nsis_script)
        
        print(f"✅ NSIS 스크립트 생성 완료: {nsis_file}")
        print("📝 NSIS 설치 방법:")
        print("  1. NSIS 다운로드: https://nsis.sourceforge.io/")
        print("  2. NSIS 스크립트 실행하여 설치 프로그램 생성")
        
        return nsis_file
    
    def create_portable_package(self):
        """포터블 패키지 생성"""
        print("\n📦 포터블 패키지 생성 중...")
        
        portable_dir = self.current_dir / f"{self.app_name}_v{self.app_version}_Portable"
        
        if portable_dir.exists():
            shutil.rmtree(portable_dir)
        
        portable_dir.mkdir()
        
        # 실행 파일 복사 (확장자 없이 생성될 수 있음)
        exe_path = self.current_dir / self.dist_dir / f"{self.app_name}.exe"
        if not exe_path.exists():
            exe_path = self.current_dir / self.dist_dir / self.app_name
        
        if exe_path.exists():
            shutil.copy2(exe_path, portable_dir)
        
        # 필요한 파일들 복사
        dist_dir = self.current_dir / self.dist_dir
        for item in dist_dir.iterdir():
            if item.is_file() and item.suffix in ['.dll', '.pyd']:
                shutil.copy2(item, portable_dir)
        
        # 설정 파일들 복사
        config_files = ['config', 'modules', 'icons', 'version.json']
        for config_file in config_files:
            src_path = self.current_dir / config_file
            if src_path.exists():
                if src_path.is_dir():
                    shutil.copytree(src_path, portable_dir / config_file)
                else:
                    shutil.copy2(src_path, portable_dir)
        
        # 실행 배치 파일 생성 (확장자 없이 생성될 수 있음)
        exe_name = f"{self.app_name}.exe" if (portable_dir / f"{self.app_name}.exe").exists() else self.app_name
        batch_content = f'''@echo off
chcp 65001 > nul
title {self.app_name} v{self.app_version}
echo {self.app_name} v{self.app_version} 시작 중...
echo.
start "" "{exe_name}"
'''
        
        batch_file = portable_dir / f"{self.app_name}.bat"
        with open(batch_file, 'w', encoding='utf-8') as f:
            f.write(batch_content)
        
        # README 파일 생성
        readme_content = f'''# {self.app_name} v{self.app_version} 포터블 버전

## 사용 방법
1. {self.app_name}.bat 파일을 더블클릭하여 실행
2. 또는 {self.app_name}.exe 파일을 직접 실행

## 시스템 요구사항
- Windows 10 이상
- 인터넷 연결 (업데이트 확인용)

## 주의사항
- 이 폴더를 이동하거나 삭제하지 마세요
- 바이러스 백신 프로그램에서 차단할 수 있습니다

## 지원
- GitHub: https://github.com/kwanwon/naver-blog-automation
- 개발자: 라이온개발자

버전: {self.app_version}
빌드 날짜: {platform.system()} {platform.release()}
'''
        
        readme_file = portable_dir / "README.txt"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        # ZIP 파일 생성
        zip_file = self.current_dir / f"{self.app_name}_v{self.app_version}_Portable.zip"
        shutil.make_archive(str(zip_file.with_suffix('')), 'zip', portable_dir)
        
        print(f"✅ 포터블 패키지 생성 완료: {portable_dir}")
        print(f"✅ ZIP 파일 생성 완료: {zip_file}")
        
        return portable_dir, zip_file
    
    def run_build(self):
        """전체 빌드 프로세스 실행"""
        print("🚀 Windows 빌드 프로세스 시작!")
        print("=" * 50)
        
        # 1. 요구사항 확인
        if not self.check_requirements():
            return False
        
        # 2. 이전 빌드 정리
        self.clean_build()
        
        # 3. spec 파일 생성
        self.create_spec_file()
        
        # 4. 실행 파일 빌드
        if not self.build_exe():
            return False
        
        # 5. 빌드 후 설정
        if not self.post_build_setup():
            return False
        
        # 6. 설치 프로그램 스크립트 생성
        self.create_installer_script()
        
        # 7. 포터블 패키지 생성
        self.create_portable_package()
        
        print("\n🎉 Windows 빌드 완료!")
        print("=" * 50)
        print(f"📦 실행 파일: {self.current_dir / self.dist_dir / f'{self.app_name}.exe'}")
        print(f"📁 빌드 디렉토리: {self.current_dir / self.build_dir}")
        print(f"📁 배포 디렉토리: {self.current_dir / self.dist_dir}")
        
        return True

if __name__ == "__main__":
    builder = WindowsBuilder()
    success = builder.run_build()
    
    if success:
        print("\n✅ 빌드가 성공적으로 완료되었습니다!")
        sys.exit(0)
    else:
        print("\n❌ 빌드가 실패했습니다.")
        sys.exit(1)
