#!/usr/bin/env python3
"""
네이버 블로그 자동화 프로그램 빌드 스크립트
"""
import os
import sys
import shutil
import subprocess
import platform

def build_app():
    print("=== 네이버 블로그 자동화 프로그램 빌드 시작 ===")
    
    # 운영체제 확인
    system = platform.system()
    print(f"운영체제: {system}")
    
    # 기존 build 및 dist 디렉토리 삭제
    for directory in ['build', 'dist']:
        if os.path.exists(directory):
            print(f"{directory} 디렉토리 삭제 중...")
            shutil.rmtree(directory)
    
    # ChromeDriver 확인 및 권한 설정
    chromedriver_path = "chromedriver"
    if os.path.exists(chromedriver_path):
        print(f"ChromeDriver 발견: {chromedriver_path}")
        # 실행 권한 부여
        if system != 'Windows':
            os.chmod(chromedriver_path, 0o755)
            print("ChromeDriver에 실행 권한 부여됨")
    else:
        print(f"경고: ChromeDriver를 찾을 수 없습니다: {chromedriver_path}")
        print("빌드가 계속되지만 앱이 올바르게 작동하지 않을 수 있습니다.")
    
    # 아이콘 경로 설정
    if system == 'Darwin':  # macOS
        icon_path = os.path.join('build_resources', 'app_icon.icns')
    elif system == 'Windows':
        icon_path = os.path.join('build_resources', 'app_icon.ico')
    else:  # Linux 등
        icon_path = os.path.join('build_resources', 'app_icon.png')
    
    # 아이콘 확인
    if not os.path.exists(icon_path):
        print(f"아이콘 파일을 찾을 수 없습니다: {icon_path}")
        if system == 'Darwin' and os.path.exists(os.path.join('build_resources', 'app_icon.png')):
            print("PNG 아이콘은 있으나 icns 파일이 없습니다. 아이콘 스크립트를 실행하세요.")
            return False
    
    # 추가 데이터 파일 설정
    datas = [
        ('config', 'config'),
        ('default_images', 'default_images'),  # 기본 이미지 폴더 추가
        ('default_images_1', 'default_images_1'),
        ('default_images_2', 'default_images_2'),
        ('default_images_3', 'default_images_3'),
        ('default_images_4', 'default_images_4'),
        ('default_images_5', 'default_images_5'),
        ('default_images_6', 'default_images_6'),
        ('default_images_7', 'default_images_7'),
        ('default_images_8', 'default_images_8'),
        ('default_images_9', 'default_images_9'),
        ('default_images_10', 'default_images_10'),
        ('default_images_11', 'default_images_11'),
        ('chromedriver', '.'), # ChromeDriver 추가
        ('.env', '.'), # .env 파일 추가
        ('naver_blog_auto.py', '.'), # 메인 클래스 파일 추가
        ('naver_blog_auto_image.py', '.'), # 이미지 처리 클래스 파일 추가
        ('naver_blog_post_finisher.py', '.'), # 포스트 마무리 처리 클래스 파일 추가
        ('modules', 'modules') # 모듈 디렉토리 추가
    ]
    
    # data 인자 구성
    data_args = []
    for src, dst in datas:
        if os.path.exists(src):
            data_args.append(f'--add-data={src}:{dst}' if system != 'Windows' else f'--add-data={src};{dst}')
        else:
            print(f"경고: 데이터 디렉토리를 찾을 수 없습니다: {src}")
    
    # PyInstaller 명령어 생성
    cmd = [
        'pyinstaller',
        '--name=네이버블로그자동화',
        '--windowed',  # GUI 모드
        '--onedir',    # 하나의 디렉토리로 빌드
        f'--icon={icon_path}',
        '--clean',
        '--noconfirm'
    ]
    
    # hidden imports 추가
    hidden_imports = [
        'PIL', 
        'selenium', 
        'flet', 
        'webdriver_manager',
        'json', 
        'os', 
        'sys', 
        'time', 
        'datetime', 
        'random',
        'nltk',
        'konlpy',
        'openai'
    ]
    
    for imp in hidden_imports:
        cmd.append(f'--hidden-import={imp}')
    
    # 데이터 경로 추가
    cmd.extend(data_args)
    
    # 메인 파일 추가
    cmd.append('blog_writer_app.py')
    
    # 명령어 출력
    print(f"실행 명령어: {' '.join(cmd)}")
    
    # PyInstaller 실행
    try:
        subprocess.run(cmd, check=True)
        print("\n=== 빌드 성공 ===")
        
        # 실행 파일 또는 앱 경로
        if system == 'Darwin':
            app_path = os.path.join('dist', '네이버블로그자동화.app')
        elif system == 'Windows':
            app_path = os.path.join('dist', '네이버블로그자동화', '네이버블로그자동화.exe')
        else:
            app_path = os.path.join('dist', '네이버블로그자동화', '네이버블로그자동화')
        
        print(f"생성된 애플리케이션 경로: {os.path.abspath(app_path)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n=== 빌드 실패 ===\n{str(e)}")
        return False

if __name__ == "__main__":
    build_app() 