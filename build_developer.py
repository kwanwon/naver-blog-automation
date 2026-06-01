#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
개발자 전용 빌드 스크립트
- 개발자 모드 파일 포함
- 시리얼 인증 우회
- 프로젝트 config 디렉토리 사용
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime

def main():
    print("🔧 개발자 전용 빌드 스크립트")
    print("=" * 50)
    
    # 현재 디렉토리 확인
    current_dir = os.getcwd()
    print(f"📁 현재 디렉토리: {current_dir}")
    
    # 필수 파일 확인
    required_files = ['blog_writer_app.py', 'requirements.txt', 'version.json']
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ 필수 파일 없음: {file}")
            return False
    
    # 필수 디렉토리 확인
    required_dirs = ['config', 'modules']
    for dir in required_dirs:
        if not os.path.exists(dir):
            print(f"❌ 필수 디렉토리 없음: {dir}")
            return False
    
    print("✅ 모든 필수 파일/디렉토리 확인 완료")
    
    # 개발자 모드 파일 생성
    developer_mode_file = os.path.join('modules', '.developer_mode')
    try:
        with open(developer_mode_file, 'w', encoding='utf-8') as f:
            f.write("DEVELOPER_MODE=true\n")
            f.write("# 이 파일이 존재하면 시리얼 인증을 우회합니다.\n")
            f.write("# 개발 환경에서만 사용하세요.\n")
            f.write(f"# 생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        print(f"✅ 개발자 모드 파일 생성: {developer_mode_file}")
    except Exception as e:
        print(f"❌ 개발자 모드 파일 생성 실패: {e}")
        return False
    
    # 기존 빌드 디렉토리 정리
    dist_dir = 'dist'
    build_dir = 'build'
    
    if os.path.exists(dist_dir):
        print(f"🧹 기존 빌드 디렉토리 정리: {dist_dir}")
        shutil.rmtree(dist_dir)
    
    if os.path.exists(build_dir):
        print(f"🧹 기존 빌드 디렉토리 정리: {build_dir}")
        shutil.rmtree(build_dir)
    
    # PyInstaller 명령어 구성
    pyinstaller_bin = 'pyinstaller'
    # 가상환경의 pyinstaller 경로 자동 탐색
    venv_pyinstaller = os.path.join(os.path.dirname(sys.executable), 'pyinstaller')
    if os.path.exists(venv_pyinstaller):
        pyinstaller_bin = venv_pyinstaller
        
    pyinstaller_cmd = [
        pyinstaller_bin,
        '--onedir',
        '--windowed',
        '--name=블로그자동화-개발자',
        '--add-data', 'config:config',
        '--add-data', 'modules:modules',
        '--add-data', 'default_images:default_images',
        '--add-data', 'default_images_1:default_images_1',
        '--add-data', 'default_images_2:default_images_2',
        '--add-data', 'default_images_3:default_images_3',
        '--add-data', 'default_images_4:default_images_4',
        '--add-data', 'default_images_5:default_images_5',
        '--add-data', 'default_images_6:default_images_6',
        '--add-data', 'default_images_7:default_images_7',
        '--add-data', 'default_images_8:default_images_8',
        '--add-data', 'default_images_9:default_images_9',
        '--add-data', 'default_images_10:default_images_10',
        '--add-data', 'requirements.txt:.',
        '--add-data', 'version.json:.',
        '--add-data', 'chromedriver:.',
        '--hidden-import=flet',
        '--hidden-import=openai',
        '--hidden-import=selenium',
        '--hidden-import=PIL',
        '--collect-all=flet',
        'blog_writer_app.py'
    ]
    
    # 이미지 디렉토리 존재 여부 확인 후 추가
    for i in range(1, 11):
        img_dir = f'default_images_{i}'
        if os.path.exists(img_dir):
            print(f"📁 이미지 디렉토리 발견: {img_dir}")
        else:
            # 존재하지 않는 디렉토리는 명령어에서 제거
            pyinstaller_cmd = [cmd for cmd in pyinstaller_cmd if not cmd.startswith(f'{img_dir}:')]
    
    # ChromeDriver 존재 확인
    if os.path.exists('chromedriver'):
        print("✅ ChromeDriver 발견")
    else:
        print("⚠️ ChromeDriver 없음 - 빌드에서 제외")
        pyinstaller_cmd = [cmd for cmd in pyinstaller_cmd if not cmd.startswith('chromedriver:')]
    
    # PyInstaller 실행
    print("\n🔨 PyInstaller 빌드 시작...")
    print(f"명령어: {' '.join(pyinstaller_cmd)}")
    
    try:
        result = subprocess.run(pyinstaller_cmd, check=True, capture_output=True, text=True)
        print("✅ PyInstaller 빌드 성공!")
        
        # 빌드 결과 확인
        app_dir = os.path.join('dist', '블로그자동화-개발자')
        if os.path.exists(app_dir):
            print(f"📦 빌드 결과: {app_dir}")
            
            # 개발자 모드 파일이 포함되었는지 확인
            dev_mode_in_build = os.path.join(app_dir, '_internal', 'modules', '.developer_mode')
            if os.path.exists(dev_mode_in_build):
                print("✅ 개발자 모드 파일이 빌드에 포함됨")
            else:
                print("⚠️ 개발자 모드 파일이 빌드에 포함되지 않음")
            
            # macOS .app 번들 확인
            app_bundle = os.path.join('dist', '블로그자동화-개발자.app')
            if os.path.exists(app_bundle):
                print(f"🍎 macOS 앱 번들 생성: {app_bundle}")
        
        print("\n🎉 개발자 빌드 완료!")
        print("=" * 50)
        print("📋 사용 방법:")
        print("1. 개발자 환경에서 시리얼 인증 없이 실행 가능")
        print("2. 프로젝트 config 디렉토리의 설정 사용")
        print("3. GPT API 키는 UI에서 설정 가능")
        print("=" * 50)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller 빌드 실패:")
        print(f"반환 코드: {e.returncode}")
        print(f"오류 출력: {e.stderr}")
        return False
    
    except Exception as e:
        print(f"❌ 빌드 중 예상치 못한 오류: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
