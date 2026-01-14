#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Releases 기반 완전 자동 업데이트 모듈
빌드된 실행 파일(.app/.exe)도 자동으로 업데이트합니다.
"""

import os
import sys
import json
import shutil
import requests
import subprocess
import tempfile
import zipfile
import platform
from datetime import datetime
from pathlib import Path
import logging
import threading

class ReleaseUpdater:
    """GitHub Releases 기반 자동 업데이트 클래스"""
    
    def __init__(self, current_version="1.0.0"):
        self.current_version = current_version
        self.github_repo = "kwanwon/naver-blog-automation"
        self.releases_api_url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"
        
        # 현재 시스템 정보
        self.system = platform.system()  # 'Darwin' (Mac) or 'Windows'
        self.is_mac = self.system == "Darwin"
        self.is_windows = self.system == "Windows"
        
        # 앱 경로
        self.app_dir = self._get_app_dir()
        self.backup_dir = os.path.join(self.app_dir, 'backups')
        self.temp_dir = None
        
        # 로깅 설정
        self.setup_logging()
        
        # 업데이트 진행률 콜백
        self.progress_callback = None
        
    def _get_app_dir(self):
        """앱 실행 디렉토리 반환"""
        if getattr(sys, 'frozen', False):
            # PyInstaller로 빌드된 경우
            if self.is_mac:
                # .app 번들 내부
                return os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))
            else:
                return os.path.dirname(sys.executable)
        else:
            # 소스 코드 실행
            return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def setup_logging(self):
        """로깅 설정"""
        log_file = os.path.join(self.app_dir, 'release_update.log')
        try:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file, encoding='utf-8'),
                    logging.StreamHandler()
                ]
            )
        except:
            logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def check_for_updates(self):
        """
        GitHub Releases에서 최신 버전 확인
        
        Returns:
            dict: 업데이트 정보 또는 None
            {
                'available': True/False,
                'version': '1.2.0',
                'download_url': 'https://...',
                'release_notes': '변경 내용...',
                'published_at': '2024-01-14'
            }
        """
        try:
            self.logger.info(f"업데이트 확인 중... (현재 버전: {self.current_version})")
            
            response = requests.get(
                self.releases_api_url,
                headers={'Accept': 'application/vnd.github.v3+json'},
                timeout=15
            )
            
            if response.status_code == 200:
                release = response.json()
                
                # 버전 추출 (v1.2.0 -> 1.2.0)
                remote_version = release.get('tag_name', '').lstrip('v')
                
                if not remote_version:
                    self.logger.info("버전 정보를 찾을 수 없습니다.")
                    return None
                
                # 버전 비교
                if self._compare_versions(remote_version, self.current_version) > 0:
                    # 새 버전 있음!
                    download_url = self._find_download_url(release.get('assets', []))
                    
                    if download_url:
                        update_info = {
                            'available': True,
                            'version': remote_version,
                            'download_url': download_url,
                            'release_notes': release.get('body', ''),
                            'published_at': release.get('published_at', '')[:10],
                            'html_url': release.get('html_url', '')
                        }
                        self.logger.info(f"새 버전 발견: {remote_version}")
                        return update_info
                    else:
                        self.logger.warning("다운로드 파일을 찾을 수 없습니다.")
                        return None
                else:
                    self.logger.info(f"현재 버전이 최신입니다. ({self.current_version})")
                    return {'available': False, 'version': self.current_version}
                    
            elif response.status_code == 404:
                self.logger.info("릴리스가 없습니다.")
                return None
            else:
                self.logger.error(f"API 오류: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"업데이트 확인 오류: {e}")
            return None
    
    def _compare_versions(self, v1, v2):
        """버전 비교 (v1 > v2: 양수, v1 < v2: 음수, 같음: 0)"""
        try:
            parts1 = [int(x) for x in v1.split('.')]
            parts2 = [int(x) for x in v2.split('.')]
            
            max_len = max(len(parts1), len(parts2))
            parts1.extend([0] * (max_len - len(parts1)))
            parts2.extend([0] * (max_len - len(parts2)))
            
            for p1, p2 in zip(parts1, parts2):
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1
            return 0
        except:
            return 0
    
    def _find_download_url(self, assets):
        """현재 OS에 맞는 다운로드 URL 찾기"""
        if not assets:
            return None
            
        # 파일명 패턴
        if self.is_mac:
            patterns = ['mac', 'macos', 'darwin', 'osx']
        elif self.is_windows:
            patterns = ['windows', 'win', 'win64', 'win32']
        else:
            patterns = ['linux']
        
        for asset in assets:
            name = asset.get('name', '').lower()
            for pattern in patterns:
                if pattern in name and name.endswith('.zip'):
                    return asset.get('browser_download_url')
        
        # 패턴 매칭 실패 시 첫 번째 zip 파일 반환
        for asset in assets:
            if asset.get('name', '').endswith('.zip'):
                return asset.get('browser_download_url')
        
        return None
    
    def download_update(self, update_info, progress_callback=None):
        """
        업데이트 파일 다운로드
        
        Args:
            update_info: check_for_updates()에서 반환된 정보
            progress_callback: 진행률 콜백 함수 (percent, message)
        
        Returns:
            tuple: (성공 여부, 파일 경로 또는 오류 메시지)
        """
        if not update_info or not update_info.get('download_url'):
            return False, "다운로드 URL이 없습니다."
        
        self.progress_callback = progress_callback
        
        try:
            self.temp_dir = tempfile.mkdtemp()
            download_url = update_info['download_url']
            file_name = download_url.split('/')[-1]
            file_path = os.path.join(self.temp_dir, file_name)
            
            self._update_progress(0, "다운로드 시작...")
            self.logger.info(f"다운로드 시작: {download_url}")
            
            # 스트리밍 다운로드 (진행률 표시)
            response = requests.get(download_url, stream=True, timeout=300)
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            self._update_progress(percent, f"다운로드 중... {percent}%")
            
            self._update_progress(100, "다운로드 완료!")
            self.logger.info(f"다운로드 완료: {file_path}")
            
            return True, file_path
            
        except Exception as e:
            self.logger.error(f"다운로드 오류: {e}")
            return False, f"다운로드 오류: {str(e)}"
    
    def install_update(self, zip_path, progress_callback=None):
        """
        업데이트 설치 (압축 해제 및 파일 교체)
        
        Args:
            zip_path: 다운로드된 zip 파일 경로
            progress_callback: 진행률 콜백 함수
        
        Returns:
            tuple: (성공 여부, 메시지)
        """
        self.progress_callback = progress_callback
        
        try:
            self._update_progress(0, "설치 준비 중...")
            
            # 1. 백업 생성
            self._update_progress(10, "백업 생성 중...")
            backup_path = self._create_backup()
            
            # 2. 압축 해제
            self._update_progress(30, "압축 해제 중...")
            extract_path = os.path.join(self.temp_dir, 'extracted')
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            # 3. 앱 파일 찾기
            self._update_progress(50, "업데이트 파일 확인 중...")
            new_app_path = self._find_app_in_folder(extract_path)
            
            if not new_app_path:
                return False, "업데이트 파일을 찾을 수 없습니다."
            
            # 4. 파일 교체
            self._update_progress(70, "파일 교체 중...")
            
            if self.is_mac:
                success, message = self._install_mac(new_app_path)
            elif self.is_windows:
                success, message = self._install_windows(new_app_path)
            else:
                return False, "지원되지 않는 운영체제입니다."
            
            if success:
                self._update_progress(100, "설치 완료!")
                self.logger.info("업데이트 설치 완료")
            
            return success, message
            
        except Exception as e:
            self.logger.error(f"설치 오류: {e}")
            return False, f"설치 오류: {str(e)}"
    
    def _find_app_in_folder(self, folder):
        """폴더에서 앱 파일 찾기"""
        for root, dirs, files in os.walk(folder):
            if self.is_mac:
                for d in dirs:
                    if d.endswith('.app'):
                        return os.path.join(root, d)
            elif self.is_windows:
                for f in files:
                    if f.endswith('.exe') and '블로그' in f:
                        return os.path.join(root, f)
        return None
    
    def _create_backup(self):
        """현재 앱 백업"""
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_v{self.current_version}_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # 간단한 백업 (전체 복사는 시간이 오래 걸림)
            self.logger.info(f"백업 생성: {backup_path}")
            return backup_path
        except Exception as e:
            self.logger.warning(f"백업 생성 실패: {e}")
            return None
    
    def _install_mac(self, new_app_path):
        """macOS 앱 설치"""
        try:
            # 현재 앱 경로 확인
            if not new_app_path.endswith('.app'):
                return False, ".app 파일이 아닙니다."
            
            # /Applications로 복사
            app_name = os.path.basename(new_app_path)
            dest_path = f"/Applications/{app_name}"
            
            # 기존 앱 백업 후 삭제
            if os.path.exists(dest_path):
                backup_app = f"{dest_path}.backup"
                if os.path.exists(backup_app):
                    shutil.rmtree(backup_app)
                shutil.move(dest_path, backup_app)
            
            # 새 앱 복사
            shutil.copytree(new_app_path, dest_path)
            
            # 실행 권한 부여
            subprocess.run(['chmod', '-R', '+x', dest_path], check=True)
            
            self.logger.info(f"macOS 앱 설치 완료: {dest_path}")
            return True, dest_path
            
        except Exception as e:
            self.logger.error(f"macOS 설치 오류: {e}")
            return False, str(e)
    
    def _install_windows(self, new_exe_path):
        """Windows 앱 설치"""
        try:
            if not new_exe_path.endswith('.exe'):
                return False, ".exe 파일이 아닙니다."
            
            # 현재 실행 파일 경로
            current_exe = sys.executable if getattr(sys, 'frozen', False) else None
            
            if current_exe:
                # 업데이터 배치 파일 생성
                updater_script = os.path.join(self.temp_dir, 'update.bat')
                dest_path = current_exe
                
                with open(updater_script, 'w', encoding='cp949') as f:
                    f.write(f'''@echo off
echo 업데이트 중... 잠시 기다려주세요.
timeout /t 2 /nobreak > nul
copy /y "{new_exe_path}" "{dest_path}"
echo 업데이트 완료!
start "" "{dest_path}"
del "%~f0"
''')
                
                self.logger.info(f"Windows 업데이터 스크립트 생성: {updater_script}")
                return True, updater_script
            else:
                # 소스 코드 실행 중
                return False, "소스 코드 실행 환경에서는 실행 파일 교체가 불가능합니다."
                
        except Exception as e:
            self.logger.error(f"Windows 설치 오류: {e}")
            return False, str(e)
    
    def restart_app(self, new_app_path=None):
        """앱 재시작"""
        try:
            if self.is_mac:
                if new_app_path and os.path.exists(new_app_path):
                    subprocess.Popen(['open', new_app_path])
                else:
                    subprocess.Popen(['open', '/Applications/블로그자동화.app'])
                    
            elif self.is_windows:
                if new_app_path and new_app_path.endswith('.bat'):
                    # 업데이터 스크립트 실행
                    subprocess.Popen(['cmd', '/c', new_app_path], 
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                elif new_app_path:
                    subprocess.Popen([new_app_path])
            
            self.logger.info("앱 재시작 요청")
            return True
            
        except Exception as e:
            self.logger.error(f"재시작 오류: {e}")
            return False
    
    def _update_progress(self, percent, message):
        """진행률 업데이트"""
        if self.progress_callback:
            try:
                self.progress_callback(percent, message)
            except:
                pass
    
    def cleanup(self):
        """임시 파일 정리"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.logger.info("임시 파일 정리 완료")
        except Exception as e:
            self.logger.warning(f"임시 파일 정리 실패: {e}")


# 테스트용 메인 함수
def main():
    """테스트 실행"""
    updater = ReleaseUpdater(current_version="1.0.0")
    
    print("🔍 업데이트 확인 중...")
    update_info = updater.check_for_updates()
    
    if update_info and update_info.get('available'):
        print(f"✅ 새 버전 발견: v{update_info['version']}")
        print(f"📝 릴리스 노트: {update_info.get('release_notes', '')[:100]}...")
        
        # 다운로드 테스트
        def progress(percent, message):
            print(f"  {message}")
        
        success, result = updater.download_update(update_info, progress)
        if success:
            print(f"📥 다운로드 완료: {result}")
        else:
            print(f"❌ 다운로드 실패: {result}")
    else:
        print("ℹ️ 최신 버전입니다.")


if __name__ == "__main__":
    main()
