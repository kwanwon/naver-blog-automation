#!/usr/bin/env python3
"""
ChromeDriver 권한 수정 및 자동 설정 스크립트
macOS에서 ChromeDriver 실행 권한 문제를 해결합니다.
"""

import os
import subprocess
import sys
import requests
import zipfile
import json
from pathlib import Path
import shutil

def run_command(command, timeout=30):
    """안전하게 명령어 실행"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "명령 실행 시간 초과"
    except Exception as e:
        return False, "", str(e)

def get_chrome_version():
    """Chrome 브라우저 버전 확인"""
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser"
    ]
    
    for chrome_path in chrome_paths:
        if os.path.exists(chrome_path):
            success, stdout, stderr = run_command(f'"{chrome_path}" --version')
            if success and stdout:
                version = stdout.strip().split()[-1]
                print(f"✅ Chrome 버전 확인: {version}")
                return version
    
    print("❌ Chrome 브라우저를 찾을 수 없습니다.")
    return None

def download_chromedriver(version, download_dir):
    """ChromeDriver 다운로드"""
    try:
        # Chrome for Testing API에서 최신 ChromeDriver URL 가져오기
        major_version = version.split('.')[0]
        
        # API URL
        api_url = f"https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
        
        print(f"📥 ChromeDriver 다운로드 정보 확인 중...")
        response = requests.get(api_url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # 버전에 맞는 다운로드 URL 찾기
            download_url = None
            for version_info in reversed(data['versions']):  # 최신 버전부터 확인
                if version_info['version'].startswith(major_version):
                    downloads = version_info.get('downloads', {})
                    chromedriver_downloads = downloads.get('chromedriver', [])
                    
                    for download in chromedriver_downloads:
                        if download['platform'] == 'mac-arm64':
                            download_url = download['url']
                            actual_version = version_info['version']
                            break
                    
                    if download_url:
                        break
            
            if not download_url:
                print(f"❌ Chrome {major_version}에 맞는 ChromeDriver를 찾을 수 없습니다.")
                return None
            
            print(f"📥 ChromeDriver {actual_version} 다운로드 중...")
            print(f"URL: {download_url}")
            
            # 다운로드
            response = requests.get(download_url, timeout=120)
            zip_path = os.path.join(download_dir, "chromedriver.zip")
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            # 압축 해제
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(download_dir)
            
            # zip 파일 삭제
            os.remove(zip_path)
            
            # ChromeDriver 경로 찾기
            for root, dirs, files in os.walk(download_dir):
                for file in files:
                    if file == 'chromedriver':
                        chromedriver_path = os.path.join(root, file)
                        print(f"✅ ChromeDriver 다운로드 완료: {chromedriver_path}")
                        return chromedriver_path
            
            print("❌ 다운로드된 ChromeDriver를 찾을 수 없습니다.")
            return None
            
        else:
            print(f"❌ API 요청 실패: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ ChromeDriver 다운로드 실패: {e}")
        return None

def fix_chromedriver_permissions(chromedriver_path):
    """ChromeDriver 권한 수정"""
    print(f"🔧 ChromeDriver 권한 수정 중: {chromedriver_path}")
    
    # 실행 권한 부여
    success, stdout, stderr = run_command(f"chmod +x '{chromedriver_path}'")
    if success:
        print("✅ 실행 권한 부여 완료")
    else:
        print(f"❌ 실행 권한 부여 실패: {stderr}")
        return False
    
    # quarantine 속성 제거
    success, stdout, stderr = run_command(f"xattr -d com.apple.quarantine '{chromedriver_path}' 2>/dev/null || true")
    if success:
        print("✅ quarantine 속성 제거 완료")
    
    # provenance 속성 제거
    success, stdout, stderr = run_command(f"xattr -d com.apple.provenance '{chromedriver_path}' 2>/dev/null || true")
    if success:
        print("✅ provenance 속성 제거 완료")
    
    # 실행 테스트
    success, stdout, stderr = run_command(f"'{chromedriver_path}' --version")
    if success and stdout:
        print(f"✅ ChromeDriver 실행 테스트 성공: {stdout.strip()}")
        return True
    else:
        print(f"❌ ChromeDriver 실행 테스트 실패: {stderr}")
        return False

def fix_existing_chromedrivers():
    """기존 ChromeDriver들 권한 수정"""
    print("🔍 기존 ChromeDriver 찾는 중...")
    
    # WebDriverManager 캐시 경로
    wdm_cache = os.path.expanduser("~/.wdm/drivers/chromedriver")
    fixed_count = 0
    
    if os.path.exists(wdm_cache):
        for root, dirs, files in os.walk(wdm_cache):
            for file in files:
                if file == 'chromedriver':
                    chromedriver_path = os.path.join(root, file)
                    print(f"📁 발견: {chromedriver_path}")
                    if fix_chromedriver_permissions(chromedriver_path):
                        fixed_count += 1
    
    # 프로젝트 폴더의 ChromeDriver
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_chromedriver = os.path.join(script_dir, "chromedriver-mac-arm64", "chromedriver")
    
    if os.path.exists(project_chromedriver):
        print(f"📁 프로젝트 ChromeDriver 발견: {project_chromedriver}")
        if fix_chromedriver_permissions(project_chromedriver):
            fixed_count += 1
    
    return fixed_count

def main():
    print("🚀 ChromeDriver 권한 수정 및 설정 시작")
    print("=" * 50)
    
    # 1. 기존 ChromeDriver 권한 수정
    fixed_count = fix_existing_chromedrivers()
    print(f"✅ 수정된 ChromeDriver 개수: {fixed_count}")
    
    # 2. Chrome 버전 확인
    chrome_version = get_chrome_version()
    if not chrome_version:
        print("❌ Chrome 브라우저를 먼저 설치해주세요.")
        return False
    
    # 3. 최신 ChromeDriver 다운로드 (선택사항)
    download_new = input("\n🤔 최신 ChromeDriver를 다운로드하시겠습니까? (y/N): ").lower().strip()
    
    if download_new == 'y':
        script_dir = os.path.dirname(os.path.abspath(__file__))
        download_dir = os.path.join(script_dir, "latest_chromedriver")
        os.makedirs(download_dir, exist_ok=True)
        
        chromedriver_path = download_chromedriver(chrome_version, download_dir)
        if chromedriver_path:
            fix_chromedriver_permissions(chromedriver_path)
            print(f"✅ 최신 ChromeDriver 설정 완료: {chromedriver_path}")
        else:
            print("❌ 최신 ChromeDriver 다운로드 실패")
    
    print("\n" + "=" * 50)
    print("🎉 ChromeDriver 설정 완료!")
    print("이제 블로그 자동화 프로그램을 실행해보세요.")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)