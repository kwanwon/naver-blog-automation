#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동 업데이트 모듈 (GitHub Releases & Assets 지원)
블로그 자동화 프로그램의 안전한 자동 업데이트 기능을 제공합니다.
"""

import os
import sys
import json
import shutil
import requests
import zipfile
import tempfile
import platform
import logging
from datetime import datetime

class AutoUpdater:
    def __init__(self, current_version="1.0.0"):
        self.current_version = current_version
        self.github_repo = "kwanwon/naver-blog-automation"
        self.github_api_url = f"https://api.github.com/repos/{self.github_repo}"
        
        # 현재 프로그램 경로
        if getattr(sys, 'frozen', False):
            # PyInstaller로 빌드된 경우
            self.app_dir = os.path.dirname(sys.executable)
            self.is_frozen = True
        else:
            # 소스 코드로 실행되는 경우
            self.app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.is_frozen = False
            
        # 백업 디렉토리 설정
        if sys.platform == 'darwin':  # macOS
            self.backup_dir = os.path.expanduser('~/Library/Application Support/BlogAutomation/backups')
        elif sys.platform == 'win32':  # Windows
            self.backup_dir = os.path.join(os.environ.get('APPDATA', ''), 'BlogAutomation', 'backups')
        else:  # Linux
            self.backup_dir = os.path.expanduser('~/.local/share/BlogAutomation/backups')
            
        self.temp_dir = tempfile.mkdtemp()
        
        # 보존해야 할 파일들
        self.preserve_files = [
            'modules/serial_config.json',
            'modules/.developer_mode',
            'naver_cookies.pkl',
            'naver_cookies.json',
            'naver_session.json',
            'naver_session.pkl',
            'config/user_settings.txt',
            'config/gpt_settings.txt',
            'config/custom_prompts.txt',
            'config/post_history.json',
            'config/smart_scheduler.json',
            'config/environment.json',
            'user_data.json',
            'config.json',
            'settings.json',
            '.env',
        ]
        
        self.setup_logging()

    def setup_logging(self):
        """로깅 설정"""
        log_dir = os.path.join(self.backup_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'auto_update.log')
        
        # 로거 설정이 중복되지 않도록 확인
        self.logger = logging.getLogger('AutoUpdater')
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)

    def get_remote_version(self):
        """깃허브 Releases에서 최신 버전 정보 가져오기"""
        try:
            # GitHub Releases API 호출
            release_url = f"{self.github_api_url}/releases/latest"
            self.logger.info(f"릴리스 정보 확인 URL: {release_url}")
            
            response = requests.get(release_url, timeout=15)
            
            if response.status_code == 200:
                release_info = response.json()
                # 'v1.2.32' -> '1.2.32'
                tag_name = release_info.get('tag_name', '').lstrip('v') 
                body = release_info.get('body', '')
                assets = release_info.get('assets', [])
                
                return tag_name, body, assets, release_info
            else:
                self.logger.warning(f"릴리스 정보를 가져올 수 없습니다. HTTP {response.status_code}")
                return None, [], [], None
                
        except Exception as e:
            self.logger.error(f"원격 버전 확인 오류: {e}")
            return None, [], [], None

    def compare_versions(self, remote_version):
        """버전 비교 (True if remote > current)"""
        if not remote_version:
            return False
        try:
            current_parts = [int(x) for x in self.current_version.split('.')]
            remote_parts = [int(x) for x in remote_version.split('.')]
            
            max_len = max(len(current_parts), len(remote_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            remote_parts.extend([0] * (max_len - len(remote_parts)))
            
            return remote_parts > current_parts
        except Exception as e:
            self.logger.error(f"버전 비교 오류: {e}")
            return False

    def _find_best_asset(self, release_info, assets):
        """
        실행 환경(Source vs Frozen)과 OS에 맞는 최적의 다운로드 URL 반환
        """
        # 1. 소스 코드로 실행 중인 경우 -> Source Code Zip 사용
        if not self.is_frozen:
            self.logger.info("소스 코드 환경 감지: Source code (zipball) 다운로드 URL 사용")
            return release_info.get('zipball_url')

        # 2. 빌드된 앱(Frozen)인 경우 -> OS별 바이너리 Asset 찾기
        system_name = platform.system().lower() # darwin, windows, linux
        
        target_keywords = []
        if system_name == 'darwin':
            target_keywords = ['mac', 'macos', 'osx']
        elif system_name == 'windows':
            target_keywords = ['windows', 'win', 'setup']
        
        # 완벽한 일치(확장자 포함) 검색 우선
        for asset in assets:
            name = asset['name'].lower()
            if system_name == 'windows' and name.endswith('.exe'):
                # 윈도우는 exe 우선 (Setup 파일 등)
                 if any(k in name for k in target_keywords):
                     self.logger.info(f"Windows Executable Asset 발견: {asset['name']}")
                     return asset['browser_download_url']
            
            if system_name == 'darwin' and name.endswith('.zip'):
                # 맥은 zip 우선
                if any(k in name for k in target_keywords):
                    self.logger.info(f"macOS Zip Asset 발견: {asset['name']}")
                    return asset['browser_download_url']

        # 일반적인 키워드 매칭 (이름에 OS 명칭이 들어간 zip)
        for asset in assets:
            name = asset['name'].lower()
            if name.endswith('.zip') and any(k in name for k in target_keywords):
                self.logger.info(f"일반 매칭 Asset 발견: {asset['name']}")
                return asset['browser_download_url']
        
        # 찾지 못했으면 소스코드 URL 반환 (Fallback)
        self.logger.warning("적절한 바이너리 Asset을 찾지 못함. Source code URL로 대체합니다.")
        return release_info.get('zipball_url')

    def download_update(self, download_url):
        """URL에서 업데이트 파일 다운로드"""
        try:
            if not download_url:
                raise ValueError("다운로드 URL이 제공되지 않았습니다.")
            
            self.logger.info(f"다운로드 시작: {download_url}")
            response = requests.get(download_url, stream=True, timeout=60)
            
            if response.status_code == 200:
                # URL에서 파일명 추측하거나 기본값 사용
                filename = "update.zip"
                if "zipball" not in download_url: 
                    # Asset URL인 경우 등
                    pass
                
                zip_path = os.path.join(self.temp_dir, filename)
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            
                self.logger.info(f"다운로드 완료 ({downloaded_size} bytes)")
                return zip_path
            else:
                self.logger.error(f"다운로드 실패: HTTP {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"다운로드 오류: {e}")
            return None

    def backup_current_version(self):
        """현재 버전 백업"""
        try:
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_v{self.current_version}_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # 전체 앱 디렉토리 백업
            # Frozen 상태일 경우 대처가 필요하나 여기선 소스/폴더 기반 백업 가정
            shutil.copytree(
                self.app_dir, 
                backup_path,
                ignore=shutil.ignore_patterns('venv', '__pycache__', '*.pyc', 'backups', 'temp_*', '.git')
            )
            
            self.logger.info(f"백업 완료: {backup_path}")
            return backup_path
        except Exception as e:
            self.logger.error(f"백업 생성 실패: {e}")
            return None

    def preserve_user_data(self):
        """사용자 데이터 메모리에 로드"""
        data = {}
        try:
            for file_path in self.preserve_files:
                full_path = os.path.join(self.app_dir, file_path)
                if os.path.exists(full_path):
                    with open(full_path, 'rb') as f:
                        data[file_path] = f.read()
            self.logger.info(f"데이터 보존: {len(data)}개 파일")
            return data
        except Exception as e:
            self.logger.error(f"데이터 보존 실패: {e}")
            return {}

    def restore_user_data(self, data):
        """사용자 데이터 복원"""
        try:
            for file_path, content in data.items():
                full_path = os.path.join(self.app_dir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'wb') as f:
                    f.write(content)
            self.logger.info("데이터 복원 완료")
            return True
        except Exception as e:
            self.logger.error(f"데이터 복원 실패: {e}")
            return False

    def extract_update(self, zip_path):
        """압축 해제 및 루트 폴더 찾기"""
        try:
            extract_path = os.path.join(self.temp_dir, 'extracted')
            if os.path.exists(extract_path):
                shutil.rmtree(extract_path)
            os.makedirs(extract_path)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            # 압축 해제 내용 확인
            items = os.listdir(extract_path)
            
            # Case 1: GitHub Source Code Zip (root -> kwanwon-repo-sha -> contents)
            if len(items) == 1 and os.path.isdir(os.path.join(extract_path, items[0])):
                inner_path = os.path.join(extract_path, items[0])
                # version.json이 있는지 확인하여 유효성 검증
                if os.path.exists(os.path.join(inner_path, 'version.json')):
                    self.logger.info(f"Source zip 구조 감지: {inner_path}")
                    return inner_path
            
            # Case 2: Flat Asset Zip (root -> contents)
            # version.json이 루트에 바로 있는 경우
            if os.path.exists(os.path.join(extract_path, 'version.json')):
                self.logger.info(f"Flat zip 구조 감지: {extract_path}")
                return extract_path
                
            # Case 3: Mac App Bundle or other structure
            # 여기서는 단순화를 위해 version.json 탐색
            for root, dirs, files in os.walk(extract_path):
                if 'version.json' in files:
                    self.logger.info(f"Deep search 구조 감지: {root}")
                    return root

            self.logger.error("유효한 업데이트 루트(version.json)를 찾을 수 없습니다.")
            return None
            
        except Exception as e:
            self.logger.error(f"압축 해제 오류: {e}")
            return None

    def apply_update(self, update_path, preserved_data):
        """업데이트 파일 덮어쓰기"""
        try:
            self.logger.info("업데이트 적용 시작...")
            
            # 소스 디렉토리에서 대상 디렉토리로 파일 복사
            for root, dirs, files in os.walk(update_path):
                # .git 등 제외
                if '.git' in dirs:
                    dirs.remove('.git')
                
                for file in files:
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, update_path)
                    dst_file = os.path.join(self.app_dir, rel_path)
                    
                    # 보존 파일은 덮어쓰지 않음 (단, 나중에 restore로 확실히 복구)
                    if rel_path in self.preserve_files:
                        continue
                        
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)
            
            # 사용자 데이터 복원 (확실하게)
            self.restore_user_data(preserved_data)
            
            self.logger.info("업데이트 적용 완료")
            return True
        except Exception as e:
            self.logger.error(f"업데이트 적용 실패: {e}")
            return False

    def update_version_file(self, new_version):
        """버전 파일 갱신"""
        try:
            version_file = os.path.join(self.app_dir, 'version.json')
            # 기존 내용을 읽어서 version만 업데이트 (다른 메타데이터 보존)
            if os.path.exists(version_file):
                with open(version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
                
            data['version'] = new_version
            data['updated_at'] = datetime.now().isoformat()
            
            with open(version_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"버전 파일 업데이트 실패: {e}")
            return False

    def cleanup_temp_files(self):
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except:
            pass

    def check_and_update(self):
        """전체 업데이트 프로세스 실행"""
        try:
            self.logger.info("업데이트 확인 시작...")
            
            # 1. 원격 버전 확인
            tag_name, body, assets, release_info = self.get_remote_version()
            
            if not tag_name:
                return False, "버전 정보를 가져올 수 없습니다."
            
            # 2. 버전 비교
            if not self.compare_versions(tag_name):
                self.logger.info(f"현재 최신 버전입니다. (Current: {self.current_version}, Remote: {tag_name})")
                return False, "최신 버전입니다."
            
            self.logger.info(f"새 버전 발견: {tag_name}")
            
            # 3. 최적의 다운로드 자산 찾기
            download_url = self._find_best_asset(release_info, assets)
            if not download_url:
                return False, "다운로드 가능한 파일을 찾을 수 없습니다."
            
            # 4. 백업
            if not self.backup_current_version():
                return False, "백업 생성에 실패했습니다."
            
            # 5. 데이터 보존
            preserved_data = self.preserve_user_data()
            
            # 6. 다운로드
            zip_path = self.download_update(download_url)
            if not zip_path:
                return False, "파일 다운로드에 실패했습니다."
            
            # 7. 압축 해제
            update_path = self.extract_update(zip_path)
            if not update_path:
                return False, "압축 해제 또는 유효한 파일 구조를 찾을 수 없습니다."
            
            # 8. 적용
            if not self.apply_update(update_path, preserved_data):
                # 롤백 로직이 필요하다면 여기에 추가
                return False, "업데이트 적용에 실패했습니다."
            
            # 9. 버전 파일 갱신 & 정리
            self.update_version_file(tag_name)
            self.cleanup_temp_files()
            
            return True, f"업데이트가 완료되었습니다. (v{tag_name})"
            
        except Exception as e:
            self.logger.error(f"치명적 오류: {e}")
            return False, f"오류 발생: {e}"

def main():
    updater = AutoUpdater("1.0.0") # 테스트용 버전
    success, msg = updater.check_and_update()
    print(msg)

if __name__ == "__main__":
    main()
