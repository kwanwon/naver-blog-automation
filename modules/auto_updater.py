#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동 업데이트 모듈
블로그 자동화 프로그램의 자동 업데이트 기능을 제공합니다.
"""

import os
import sys
import json
import requests
import tempfile
import shutil
import subprocess
import zipfile
import platform
from datetime import datetime
import logging

class AutoUpdater:
    def __init__(self, current_version="1.0.0"):
        self.current_version = current_version
        self.github_repo = "kwanwon/naver-blog-automation"
        self.github_branch = "main"
        self.github_api_url = f"https://api.github.com/repos/{self.github_repo}"
        self.github_raw_url = f"https://raw.githubusercontent.com/{self.github_repo}/{self.github_branch}"
        
        # 현재 프로그램 경로
        self.app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 로깅 설정
        self.setup_logging()
        
    def setup_logging(self):
        """로깅 설정"""
        log_file = os.path.join(self.app_dir, 'auto_update.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def get_remote_version(self):
        """깃허브에서 최신 버전 정보 가져오기"""
        try:
            version_url = f"{self.github_raw_url}/블로그자동화/config/naver-blog-automation/version.json"
            self.logger.info(f"버전 확인 URL: {version_url}")
            
            response = requests.get(version_url, timeout=10)
            
            if response.status_code == 200:
                version_info = response.json()
                remote_version = version_info.get('version')
                changelog = version_info.get('changelog', [])
                
                self.logger.info(f"원격 버전: {remote_version}, 현재 버전: {self.current_version}")
                return remote_version, changelog
            else:
                self.logger.warning(f"버전 정보를 가져올 수 없습니다. HTTP {response.status_code}")
                return None, []
                
        except Exception as e:
            self.logger.error(f"원격 버전 확인 오류: {e}")
            return None, []
            
    def compare_versions(self, remote_version):
        """버전 비교"""
        if not remote_version:
            return False
            
        try:
            current_parts = [int(x) for x in self.current_version.split('.')]
            remote_parts = [int(x) for x in remote_version.split('.')]
            
            # 버전 길이 맞추기
            max_len = max(len(current_parts), len(remote_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            remote_parts.extend([0] * (max_len - len(remote_parts)))
            
            return remote_parts > current_parts
            
        except Exception as e:
            self.logger.error(f"버전 비교 오류: {e}")
            return False
            
    def download_update(self, version):
        """업데이트 파일 다운로드"""
        try:
            # GitHub 릴리스에서 소스 코드 다운로드
            download_url = f"https://github.com/{self.github_repo}/archive/refs/heads/{self.github_branch}.zip"
            
            # 임시 디렉토리에 다운로드
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, f"update_{version}.zip")
            
            self.logger.info(f"업데이트 다운로드 중: {download_url}")
            
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            self.logger.info(f"다운로드 완료: {zip_path}")
            return zip_path, temp_dir
            
        except Exception as e:
            self.logger.error(f"다운로드 오류: {e}")
            return None, None
    
    def backup_current_version(self):
        """현재 버전 백업"""
        try:
            backup_dir = os.path.join(self.app_dir, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"backup_{self.current_version}_{timestamp}")
            
            # 중요한 파일들만 백업
            important_files = [
                'config',
                'modules', 
                'version.json',
                'blog_writer_app.py',
                'requirements.txt'
            ]
            
            os.makedirs(backup_path, exist_ok=True)
            
            for item in important_files:
                src = os.path.join(self.app_dir, item)
                if os.path.exists(src):
                    dst = os.path.join(backup_path, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
            
            self.logger.info(f"백업 완료: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"백업 오류: {e}")
            return None
    
    def apply_update(self, zip_path, temp_dir):
        """업데이트 적용"""
        try:
            self.logger.info("업데이트 적용 시작...")
            
            # ZIP 파일 압축 해제
            extract_dir = os.path.join(temp_dir, 'extracted')
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # 압축 해제된 폴더 찾기
            extracted_folders = [f for f in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, f))]
            if not extracted_folders:
                raise Exception("압축 해제된 폴더를 찾을 수 없습니다.")
            
            # 소스 디렉토리 경로 확인
            possible_paths = [
                os.path.join(extract_dir, extracted_folders[0], '블로그자동화', 'config', 'naver-blog-automation'),
                os.path.join(extract_dir, extracted_folders[0]),
                os.path.join(extract_dir, extracted_folders[0], 'naver-blog-automation')
            ]
            
            source_dir = None
            for path in possible_paths:
                if os.path.exists(path) and os.path.exists(os.path.join(path, 'blog_writer_app.py')):
                    source_dir = path
                    break
            
            if not source_dir:
                self.logger.error("가능한 경로들:")
                for path in possible_paths:
                    self.logger.error(f"  - {path} (존재: {os.path.exists(path)})")
                raise Exception(f"소스 디렉토리를 찾을 수 없습니다.")
            
            self.logger.info(f"소스 디렉토리: {source_dir}")
            
            # 사용자 데이터 보존할 파일들
            preserve_files = [
                'config/serial_config.json',
                'config/user_settings.json', 
                'config/app_settings.json',
                'naver_cookies.pkl',
                'naver_session.json',
                'naver_cookies.json',
                'used_folders.json'
            ]
            
            # 사용자 데이터 임시 저장
            preserved_data = {}
            for file_path in preserve_files:
                full_path = os.path.join(self.app_dir, file_path)
                if os.path.exists(full_path):
                    try:
                        with open(full_path, 'rb') as f:
                            preserved_data[file_path] = f.read()
                        self.logger.info(f"보존됨: {file_path}")
                    except Exception as e:
                        self.logger.warning(f"파일 보존 실패 {file_path}: {e}")
            
            # 업데이트할 파일들 복사
            update_files = ['blog_writer_app.py', 'modules', 'version.json', 'requirements.txt']
            
            for item in update_files:
                src = os.path.join(source_dir, item)
                dst = os.path.join(self.app_dir, item)
                
                if os.path.exists(src):
                    try:
                        if os.path.exists(dst):
                            if os.path.isdir(dst):
                                shutil.rmtree(dst)
                            else:
                                os.remove(dst)
                        
                        if os.path.isdir(src):
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy2(src, dst)
                        
                        self.logger.info(f"업데이트됨: {item}")
                    except Exception as e:
                        self.logger.error(f"파일 복사 실패 {item}: {e}")
                        raise
                else:
                    self.logger.warning(f"소스 파일 없음: {src}")
            
            # 사용자 데이터 복원
            for file_path, data in preserved_data.items():
                try:
                    full_path = os.path.join(self.app_dir, file_path)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, 'wb') as f:
                        f.write(data)
                    self.logger.info(f"사용자 데이터 복원: {file_path}")
                except Exception as e:
                    self.logger.warning(f"데이터 복원 실패 {file_path}: {e}")
            
            self.logger.info("업데이트 적용 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"업데이트 적용 오류: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def cleanup_temp_files(self, temp_dir):
        """임시 파일 정리"""
        try:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                self.logger.info("임시 파일 정리 완료")
        except Exception as e:
            self.logger.warning(f"임시 파일 정리 오류: {e}")
    
    def check_and_update(self):
        """업데이트 확인 및 실행"""
        try:
            self.logger.info("업데이트 확인 시작...")
            
            # 원격 버전 확인
            remote_version, changelog = self.get_remote_version()
            
            if not remote_version:
                self.logger.info("원격 버전을 확인할 수 없습니다.")
                return False, "버전 확인 실패"
                
            # 버전 비교
            if not self.compare_versions(remote_version):
                self.logger.info(f"현재 버전이 최신입니다. (현재: {self.current_version})")
                return False, "최신 버전"
                
            self.logger.info(f"새 버전 발견: {self.current_version} -> {remote_version}")
            
            # 실제 업데이트 수행
            return self.perform_update(remote_version)
                
        except Exception as e:
            self.logger.error(f"업데이트 프로세스 오류: {e}")
            return False, f"업데이트 오류: {str(e)}"
    
    def perform_update(self, remote_version):
        """실제 업데이트 수행"""
        temp_dir = None
        backup_path = None
        
        try:
            self.logger.info(f"업데이트 시작: v{self.current_version} -> v{remote_version}")
            
            # 1. 현재 버전 백업
            backup_path = self.backup_current_version()
            if not backup_path:
                return False, "백업 실패"
            
            # 2. 업데이트 파일 다운로드
            zip_path, temp_dir = self.download_update(remote_version)
            if not zip_path:
                return False, "다운로드 실패"
            
            # 3. 업데이트 적용
            if not self.apply_update(zip_path, temp_dir):
                return False, "업데이트 적용 실패"
            
            # 4. 임시 파일 정리
            self.cleanup_temp_files(temp_dir)
            
            self.logger.info(f"업데이트 완료: v{remote_version}")
            return True, f"업데이트 완료! v{self.current_version} -> v{remote_version}"
            
        except Exception as e:
            self.logger.error(f"업데이트 수행 오류: {e}")
            
            # 오류 발생 시 정리
            if temp_dir:
                self.cleanup_temp_files(temp_dir)
            
            return False, f"업데이트 실패: {str(e)}"
