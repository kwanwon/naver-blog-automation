#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows용 블로그자동화 빌드 스크립트
PyInstaller를 사용하여 Windows 실행 파일 생성
"""

import os
import sys
import subprocess
import shutil
import json
from pathlib import Path

class WindowsBuilder:
    def __init__(self):
        self.app_name = "블로그자동화"
        self.version = "1.5.0"
        self.build_dir = "dist"
        self.spec_file = f"{self.app_name}.spec"
        
    def check_requirements(self):
        """필요한 패키지 확인"""
        print("🔍 필요한 패키지 확인 중...")
        
        try:
            import PyInstaller
            print(f"✅ PyInstaller 버전: {PyInstaller.__version__}")
        except ImportError:
            print("❌ PyInstaller가 설치되지 않았습니다.")
            print("💡 설치 방법: pip install pyinstaller")
            return False
            
        try:
            import flet
            print("✅ Flet 설치 확인됨")
        except ImportError:
            print("❌ Flet이 설치되지 않았습니다.")
            print("💡 설치 방법: pip install flet")
            return False
            
        return True
    
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
        
        # spec 파일 내용 생성
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['blog_writer_app.py'],
    pathex=[],
    binaries=[],
    datas={datas},
    hiddenimports=[
        'flet',
        'flet.fastapi',
        'flet.web',
        'flet.pubsub',
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.common.by',
        'selenium.webdriver.support',
        'selenium.webdriver.support.ui',
        'selenium.webdriver.support.wait',
        'selenium.webdriver.support.expected_conditions',
        'selenium.common.exceptions',
        'webdriver_manager',
        'webdriver_manager.chrome',
        'openai',
        'requests',
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
        'time',
        'random',
        'os',
        'sys',
        'pathlib',
        'logging',
        'traceback',
        'base64',
        'hashlib',
        'uuid',
        'urllib',
        'urllib.parse',
        'urllib.request',
        'http.client',
        'ssl',
        'socket',
        'platform',
        'psutil',
        'webdriver_manager',  # ChromeDriver 자동 관리
        'webdriver_manager.chrome',
        'naver_blog_auto_image',  # 이미지 삽입 모듈
        'folder_manager',  # 폴더 관리 모듈
        'tempfile',
        'zipfile',
        'shutil',
        'time',
        'random',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
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
    icon='icons/app_icon.ico' if os.path.exists('icons/app_icon.ico') else None,
)
'''
        
        # spec 파일 저장
        with open(self.spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        print(f"✅ Spec 파일 생성 완료: {self.spec_file}")
        return True
    
    def build_application(self):
        """애플리케이션 빌드"""
        print(f"\n🔨 {self.app_name} 빌드 시작...")
        
        try:
            # PyInstaller 실행
            cmd = [
                'pyinstaller',
                '--clean',
                '--noconfirm',
                self.spec_file
            ]
            
            print(f"실행 명령: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            print("✅ 빌드 성공!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 빌드 실패: {e}")
            print(f"에러 출력: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            return False
    
    def create_portable_package(self):
        """포터블 패키지 생성"""
        print(f"\n📦 {self.app_name} 포터블 패키지 생성 중...")
        
        # 빌드된 실행 파일 경로
        exe_path = os.path.join(self.build_dir, f"{self.app_name}.exe")
        
        if not os.path.exists(exe_path):
            print(f"❌ 실행 파일을 찾을 수 없습니다: {exe_path}")
            return False
        
        # 포터블 폴더 생성
        portable_name = f"{self.app_name}_v{self.version}_Windows_Portable"
        portable_dir = portable_name
        
        if os.path.exists(portable_dir):
            shutil.rmtree(portable_dir)
        
        os.makedirs(portable_dir, exist_ok=True)
        
        # 실행 파일 복사
        shutil.copy2(exe_path, portable_dir)
        print(f"✅ 실행 파일 복사: {exe_path} → {portable_dir}")
        
        # 설정 파일들 복사
        config_files = [
            'config',
            'gpt_settings.txt',
            'app_settings.json',
            'version.json',
            'requirements.txt'
        ]
        
        for file_name in config_files:
            if os.path.exists(file_name):
                if os.path.isdir(file_name):
                    shutil.copytree(file_name, os.path.join(portable_dir, file_name))
                else:
                    shutil.copy2(file_name, portable_dir)
                print(f"✅ 설정 파일 복사: {file_name}")
        
        # README 파일 생성
        readme_content = f"""# {self.app_name} v{self.version} - Windows 포터블 버전

## 🚀 실행 방법
1. `{self.app_name}.exe` 파일을 더블클릭하여 실행
2. Windows Defender 경고가 나오면 "추가 정보" → "실행" 클릭
3. 관리자 권한으로 실행 권장

## ⚙️ 설정
- `config/gpt_settings.txt`에 OpenAI API 키 입력
- `config/app_settings.json`에서 앱 설정 변경

## 📋 시스템 요구사항
- Windows 10 이상
- Chrome 브라우저 최신 버전
- 인터넷 연결 (GPT API 사용시)

## 🆘 문제 해결
- 실행 안됨: 관리자 권한으로 실행
- 바이러스 경고: Windows Defender 예외 추가
- Chrome 오류: Chrome 브라우저 재설치

## 📞 지원
- GitHub: https://github.com/kwanwon/naver-blog-automation
- 이슈 리포트: GitHub Issues 페이지

---
빌드 날짜: {self.get_current_time()}
버전: {self.version}
"""
        
        with open(os.path.join(portable_dir, 'README.txt'), 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"✅ 포터블 패키지 생성 완료: {portable_dir}")
        return portable_dir
    
    def create_zip_package(self, portable_dir):
        """ZIP 패키지 생성"""
        print(f"\n📦 ZIP 패키지 생성 중...")
        
        zip_name = f"{portable_dir}.zip"
        
        try:
            shutil.make_archive(portable_dir, 'zip', portable_dir)
            print(f"✅ ZIP 패키지 생성 완료: {zip_name}")
            return zip_name
        except Exception as e:
            print(f"❌ ZIP 생성 실패: {e}")
            return None
    
    def get_current_time(self):
        """현재 시간 반환"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def show_build_summary(self, portable_dir, zip_name):
        """빌드 요약 정보 표시"""
        print(f"\n🎉 빌드 완료!")
        print(f"=" * 50)
        print(f"📱 앱 이름: {self.app_name}")
        print(f"📋 버전: {self.version}")
        print(f"📁 포터블 폴더: {portable_dir}")
        print(f"📦 ZIP 파일: {zip_name}")
        print(f"⏰ 빌드 시간: {self.get_current_time()}")
        print(f"=" * 50)
        
        # 파일 크기 확인
        if os.path.exists(zip_name):
            size_mb = os.path.getsize(zip_name) / (1024 * 1024)
            print(f"📊 패키지 크기: {size_mb:.1f} MB")
        
        print(f"\n💡 사용 방법:")
        print(f"1. {zip_name} 파일을 Windows PC로 전송")
        print(f"2. 압축 해제 후 {self.app_name}.exe 실행")
        print(f"3. config/gpt_settings.txt에 API 키 입력")
        print(f"4. 프로그램 실행 및 사용")
    
    def run_build(self):
        """전체 빌드 프로세스 실행"""
        print(f"🚀 {self.app_name} v{self.version} Windows 빌드 시작")
        print(f"=" * 50)
        
        # 1. 요구사항 확인
        if not self.check_requirements():
            return False
        
        # 2. Spec 파일 생성
        if not self.create_spec_file():
            return False
        
        # 3. 애플리케이션 빌드
        if not self.build_application():
            return False
        
        # 4. 포터블 패키지 생성
        portable_dir = self.create_portable_package()
        if not portable_dir:
            return False
        
        # 5. ZIP 패키지 생성
        zip_name = self.create_zip_package(portable_dir)
        if not zip_name:
            return False
        
        # 6. 빌드 요약 표시
        self.show_build_summary(portable_dir, zip_name)
        
        return True

def main():
    """메인 함수"""
    builder = WindowsBuilder()
    success = builder.run_build()
    
    if success:
        print(f"\n✅ Windows 빌드가 성공적으로 완료되었습니다!")
        print(f"🎯 이제 Windows PC에서 {builder.app_name}_v{builder.version}_Windows_Portable.zip을 사용할 수 있습니다.")
    else:
        print(f"\n❌ Windows 빌드가 실패했습니다.")
        print(f"💡 오류를 확인하고 다시 시도해주세요.")
        sys.exit(1)

if __name__ == "__main__":
    main()