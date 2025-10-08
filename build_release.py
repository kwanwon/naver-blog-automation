#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
배포용 빌드 스크립트
- 시리얼 인증 필수
- 사용자별 설정 저장
- 개발자 모드 파일 제외
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime

def main():
    print("📦 배포용 빌드 스크립트")
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
    
    # 개발자 모드 파일 제거 (배포용)
    developer_mode_file = os.path.join('modules', '.developer_mode')
    if os.path.exists(developer_mode_file):
        try:
            os.remove(developer_mode_file)
            print(f"🗑️ 개발자 모드 파일 제거: {developer_mode_file}")
        except Exception as e:
            print(f"⚠️ 개발자 모드 파일 제거 실패: {e}")
    
    # 기존 빌드 디렉토리 정리
    dist_dir = 'dist'
    build_dir = 'build'
    
    if os.path.exists(dist_dir):
        print(f"🧹 기존 빌드 디렉토리 정리: {dist_dir}")
        shutil.rmtree(dist_dir)
    
    if os.path.exists(build_dir):
        print(f"🧹 기존 빌드 디렉토리 정리: {build_dir}")
        shutil.rmtree(build_dir)
    
    # 배포용 기본 설정 템플릿 생성
    create_release_config_templates()
    
    # PyInstaller 명령어 구성
    pyinstaller_cmd = [
        'pyinstaller',
        '--onedir',
        '--windowed',
        '--name=블로그자동화',
        '--add-data', 'config:config',
        '--add-data', 'modules:modules',
        '--add-data', 'default_images:default_images',
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
    
    # 이미지 디렉토리 추가
    for i in range(1, 11):
        img_dir = f'default_images_{i}'
        if os.path.exists(img_dir):
            pyinstaller_cmd.extend(['--add-data', f'{img_dir}:{img_dir}'])
            print(f"📁 이미지 디렉토리 포함: {img_dir}")
    
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
        app_dir = os.path.join('dist', '블로그자동화')
        if os.path.exists(app_dir):
            print(f"📦 빌드 결과: {app_dir}")
            
            # 개발자 모드 파일이 제외되었는지 확인
            dev_mode_in_build = os.path.join(app_dir, '_internal', 'modules', '.developer_mode')
            if not os.path.exists(dev_mode_in_build):
                print("✅ 개발자 모드 파일이 빌드에서 제외됨 (정상)")
            else:
                print("⚠️ 개발자 모드 파일이 빌드에 포함됨 (비정상)")
            
            # macOS .app 번들 확인
            app_bundle = os.path.join('dist', '블로그자동화.app')
            if os.path.exists(app_bundle):
                print(f"🍎 macOS 앱 번들 생성: {app_bundle}")
        
        print("\n🎉 배포용 빌드 완료!")
        print("=" * 50)
        print("📋 배포 특징:")
        print("1. 시리얼 인증 필수 (정식 라이선스 필요)")
        print("2. 사용자별 설정 저장 (~/Documents/블로그자동화/)")
        print("3. 커스텀 설정 가능")
        print("4. 자동 업데이트 지원")
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

def create_release_config_templates():
    """배포용 기본 설정 템플릿을 생성합니다."""
    print("📋 배포용 설정 템플릿 생성...")
    
    # GPT 설정 템플릿
    gpt_template = {
        "api_key": "",
        "persona": "친근하고 전문적인 블로그 작성자",
        "instructions": "1500자 이상 ~ 1600자 이내로 작성하며, 도입-본문-결론 구조로 구성해주세요.",
        "style": "친근하고 따뜻한 부드러운 존댓말 사용",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 사용자 설정 템플릿
    user_template = {
        "theme": "light",
        "auto_save": True,
        "notification": True,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        import json
        
        # GPT 설정 템플릿 저장
        gpt_template_path = os.path.join('config', 'gpt_settings_template.txt')
        with open(gpt_template_path, 'w', encoding='utf-8') as f:
            json.dump(gpt_template, f, ensure_ascii=False, indent=2)
        print(f"✅ GPT 설정 템플릿 생성: {gpt_template_path}")
        
        # 사용자 설정 템플릿 저장
        user_template_path = os.path.join('config', 'user_settings_template.txt')
        with open(user_template_path, 'w', encoding='utf-8') as f:
            json.dump(user_template, f, ensure_ascii=False, indent=2)
        print(f"✅ 사용자 설정 템플릿 생성: {user_template_path}")
        
    except Exception as e:
        print(f"⚠️ 설정 템플릿 생성 실패: {e}")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
