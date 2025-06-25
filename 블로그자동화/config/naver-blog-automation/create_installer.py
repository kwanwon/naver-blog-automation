#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 블로그 자동화 도구 - macOS용 DMG 설치 프로그램 생성 스크립트
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime

# 설정
APP_NAME = "네이버블로그자동화"
VERSION = "1.0.0"  # 버전 정보
DMG_FILENAME = f"{APP_NAME}-{VERSION}.dmg"
DMG_VOLUME_NAME = f"{APP_NAME} {VERSION}"

# 경로 설정
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
APP_PATH = os.path.join(DIST_DIR, f"{APP_NAME}.app")
INSTALLER_DIR = os.path.join(BASE_DIR, "installer")
DMG_PATH = os.path.join(INSTALLER_DIR, DMG_FILENAME)

def run_command(command):
    """명령어 실행 및 결과 출력"""
    print(f"실행: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("명령어 실행 성공")
        return True
    else:
        print(f"명령어 실행 실패: {result.stderr}")
        return False

def check_requirements():
    """필요한 도구가 설치되어 있는지 확인"""
    print("=== 필수 도구 확인 ===")
    
    if not shutil.which("create-dmg"):
        print("create-dmg 도구가 설치되지 않았습니다. 설치를 시도합니다...")
        if shutil.which("brew"):
            if run_command("brew install create-dmg"):
                print("create-dmg 설치 완료")
            else:
                print("create-dmg 설치 실패. Homebrew로 수동 설치 필요: brew install create-dmg")
                return False
        else:
            print("Homebrew가 설치되지 않았습니다. 먼저 Homebrew를 설치해주세요.")
            print("설치 방법: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
            return False
    else:
        print("create-dmg ✓")
        
    return True

def create_installer_directory():
    """인스톨러 디렉토리 생성"""
    print("=== 인스톨러 디렉토리 준비 ===")
    if not os.path.exists(INSTALLER_DIR):
        os.makedirs(INSTALLER_DIR)
        print(f"인스톨러 디렉토리 생성: {INSTALLER_DIR}")
    else:
        print(f"인스톨러 디렉토리 이미 존재: {INSTALLER_DIR}")
    
    # 기존 DMG 파일 삭제
    if os.path.exists(DMG_PATH):
        os.remove(DMG_PATH)
        print(f"기존 DMG 파일 삭제: {DMG_PATH}")

def create_dmg():
    """DMG 파일 생성"""
    print("=== DMG 생성 시작 ===")
    
    if not os.path.exists(APP_PATH):
        print(f"오류: 앱이 존재하지 않습니다: {APP_PATH}")
        print("먼저 build.py를 실행하여 앱을 빌드해주세요.")
        return False
    
    # 버전 정보 추가 (앱 번들에 Info.plist 파일이 있다면)
    info_plist_path = os.path.join(APP_PATH, "Contents", "Info.plist")
    if os.path.exists(info_plist_path):
        print(f"앱 버전 정보 업데이트: {VERSION}")
        # 버전 정보 업데이트 명령어 (선택 사항)
        run_command(f"/usr/libexec/PlistBuddy -c \"Set :CFBundleShortVersionString {VERSION}\" \"{info_plist_path}\"")
        run_command(f"/usr/libexec/PlistBuddy -c \"Set :CFBundleVersion {VERSION}\" \"{info_plist_path}\"")
    
    # DMG 생성 명령어
    cmd = (
        f"create-dmg "
        f"--volname \"{DMG_VOLUME_NAME}\" "
        f"--volicon \"build_resources/app_icon.icns\" "
        f"--background \"build_resources/dmg_background.png\" "
        f"--window-pos 200 120 "
        f"--window-size 800 400 "
        f"--icon-size 100 "
        f"--icon \"{APP_NAME}.app\" 200 200 "
        f"--app-drop-link 600 200 "
        f"--no-internet-enable "
        f"\"{DMG_PATH}\" "
        f"\"{APP_PATH}\""
    )
    
    # 배경 이미지 파일이 없으면 간단한 명령어로 대체
    if not os.path.exists("build_resources/dmg_background.png"):
        print("배경 이미지 파일이 없어 기본 스타일로 DMG를 생성합니다.")
        cmd = (
            f"create-dmg "
            f"--volname \"{DMG_VOLUME_NAME}\" "
            f"--no-internet-enable "
            f"\"{DMG_PATH}\" "
            f"\"{APP_PATH}\""
        )
    
    success = run_command(cmd)
    if success:
        print(f"DMG 파일 생성 완료: {DMG_PATH}")
        return True
    else:
        print("DMG 파일 생성 실패")
        return False

def main():
    """메인 함수"""
    print(f"=== {APP_NAME} 설치 프로그램 생성 시작 ===")
    print(f"버전: {VERSION}")
    
    # 필수 요소 확인
    if not check_requirements():
        print("필수 요소가 충족되지 않았습니다. 설치 프로그램 생성을 중단합니다.")
        return 1
    
    # 인스톨러 디렉토리 준비
    create_installer_directory()
    
    # DMG 생성
    if create_dmg():
        print("=== 설치 프로그램 생성 성공 ===")
        print(f"DMG 파일 위치: {DMG_PATH}")
        return 0
    else:
        print("=== 설치 프로그램 생성 실패 ===")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 