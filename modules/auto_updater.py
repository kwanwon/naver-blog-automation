#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동 업데이트 모듈
블로그 자동화 프로그램의 안전한 자동 업데이트 기능을 제공합니다.
"""

import os
import sys
import json
import shutil
import requests
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
import logging

class AutoUpdater:
    def __init__(self, current_version="1.0.0"):
        self.current_version = current_version
        self.github_repo = "kwanwon/naver-blog-automation"  # 올바른 저장소 이름
        self.github_branch = "main"  # 올바른 브랜치 이름
        self.github_api_url = f"https://api.github.com/repos/{self.github_repo}"
        self.github_raw_url = f"https://raw.githubusercontent.com/{self.github_repo}/{self.github_branch}"
        
        # 올바른 경로 설정 (블로그자동화/config/naver-blog-automation 폴더 내의 파일들)
        self.remote_base_path = "블로그자동화/config/naver-blog-automation"
        
        # 현재 프로그램 경로
        self.app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.backup_dir = os.path.join(self.app_dir, 'backups')
        self.temp_dir = tempfile.mkdtemp()
        
        # 보존해야 할 파일들 (업데이트되지 않아야 함)
        self.preserve_files = [
            'modules/serial_config.json',
            'modules/serial_auth.py',  # 설정만 보존, 코드는 업데이트
            'naver_cookies.pkl',
            'naver_session.json',
            'user_data.json',
            'config.json',
            'settings.json'
        ]
        
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
            response = requests.get(version_url, timeout=10)
            
            if response.status_code == 200:
                version_info = response.json()
                return version_info.get('version'), version_info.get('changelog', [])
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
            
    def backup_current_version(self):
        """현재 버전 백업"""
        try:
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_v{self.current_version}_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # 전체 앱 디렉토리 백업 (venv 제외)
            shutil.copytree(
                self.app_dir, 
                backup_path,
                ignore=shutil.ignore_patterns('venv', '__pycache__', '*.pyc', 'backups', 'temp_*')
            )
            
            self.logger.info(f"백업 완료: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"백업 생성 실패: {e}")
            return None
            
    def preserve_user_data(self):
        """사용자 데이터 보존"""
        preserved_data = {}
        
        try:
            for file_path in self.preserve_files:
                full_path = os.path.join(self.app_dir, file_path)
                if os.path.exists(full_path):
                    # 파일 내용 읽기
                    if file_path.endswith('.json'):
                        with open(full_path, 'r', encoding='utf-8') as f:
                            preserved_data[file_path] = f.read()
                    else:
                        # 바이너리 파일
                        with open(full_path, 'rb') as f:
                            preserved_data[file_path] = f.read()
                            
            self.logger.info(f"사용자 데이터 보존 완료: {len(preserved_data)}개 파일")
            return preserved_data
            
        except Exception as e:
            self.logger.error(f"사용자 데이터 보존 실패: {e}")
            return {}
            
    def restore_user_data(self, preserved_data):
        """사용자 데이터 복원"""
        try:
            for file_path, content in preserved_data.items():
                full_path = os.path.join(self.app_dir, file_path)
                
                # 디렉토리 생성
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # 파일 복원
                if file_path.endswith('.json'):
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                else:
                    with open(full_path, 'wb') as f:
                        f.write(content)
                        
            self.logger.info("사용자 데이터 복원 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"사용자 데이터 복원 실패: {e}")
            return False
            
    def download_update(self):
        """최신 버전 다운로드"""
        try:
            # 깃허브 저장소의 ZIP 다운로드
            zip_url = f"https://github.com/{self.github_repo}/archive/refs/heads/main.zip"
            
            self.logger.info("최신 버전 다운로드 중...")
            response = requests.get(zip_url, stream=True, timeout=60)
            
            if response.status_code == 200:
                zip_path = os.path.join(self.temp_dir, 'update.zip')
                
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
                self.logger.info("다운로드 완료")
                return zip_path
            else:
                self.logger.error(f"다운로드 실패: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"다운로드 오류: {e}")
            return None
            
    def extract_update(self, zip_path):
        """업데이트 파일 압축 해제"""
        try:
            extract_path = os.path.join(self.temp_dir, 'extracted')
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
                
            # 압축 해제된 폴더 찾기
            extracted_items = os.listdir(extract_path)
            if extracted_items:
                repo_folder = os.path.join(extract_path, extracted_items[0])
                blog_automation_path = os.path.join(repo_folder, '블로그자동화', 'config', 'naver-blog-automation')
                
                if os.path.exists(blog_automation_path):
                    self.logger.info("업데이트 파일 압축 해제 완료")
                    return blog_automation_path
                    
            self.logger.error("블로그 자동화 폴더를 찾을 수 없습니다")
            return None
            
        except Exception as e:
            self.logger.error(f"압축 해제 오류: {e}")
            return None
            
    def apply_update(self, update_path, preserved_data):
        """업데이트 적용"""
        try:
            self.logger.info("업데이트 적용 중...")
            
            # 기존 파일들을 새 파일로 교체 (보존 파일 제외)
            for root, dirs, files in os.walk(update_path):
                # __pycache__, .git 등 제외
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                
                for file in files:
                    if file.endswith('.pyc') or file.startswith('.'):
                        continue
                        
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, update_path)
                    dst_file = os.path.join(self.app_dir, rel_path)
                    
                    # 보존 파일인지 확인
                    if rel_path in self.preserve_files:
                        self.logger.info(f"보존 파일 건너뛰기: {rel_path}")
                        continue
                        
                    # 디렉토리 생성
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    
                    # 파일 복사
                    shutil.copy2(src_file, dst_file)
                    
            # 사용자 데이터 복원
            self.restore_user_data(preserved_data)
            
            self.logger.info("업데이트 적용 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"업데이트 적용 실패: {e}")
            return False
            
    def update_version_file(self, new_version):
        """버전 파일 업데이트"""
        try:
            version_file = os.path.join(self.app_dir, 'version.json')
            version_data = {
                'version': new_version,
                'updated_at': datetime.now().isoformat(),
                'previous_version': self.current_version
            }
            
            with open(version_file, 'w', encoding='utf-8') as f:
                json.dump(version_data, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"버전 파일 업데이트: {self.current_version} -> {new_version}")
            return True
            
        except Exception as e:
            self.logger.error(f"버전 파일 업데이트 실패: {e}")
            return False
            
    def cleanup_temp_files(self):
        """임시 파일 정리"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            self.logger.info("임시 파일 정리 완료")
        except Exception as e:
            self.logger.error(f"임시 파일 정리 실패: {e}")
            
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
            
            # 백업 생성
            backup_path = self.backup_current_version()
            if not backup_path:
                return False, "백업 실패"
                
            # 사용자 데이터 보존
            preserved_data = self.preserve_user_data()
            
            # 업데이트 다운로드
            zip_path = self.download_update()
            if not zip_path:
                return False, "다운로드 실패"
                
            # 압축 해제
            update_path = self.extract_update(zip_path)
            if not update_path:
                return False, "압축 해제 실패"
                
            # 업데이트 적용
            if not self.apply_update(update_path, preserved_data):
                return False, "업데이트 적용 실패"
                
            # 버전 파일 업데이트
            self.update_version_file(remote_version)
            
            # 임시 파일 정리
            self.cleanup_temp_files()
            
            self.logger.info(f"업데이트 완료: {self.current_version} -> {remote_version}")
            return True, f"업데이트 완료: v{remote_version}"
            
        except Exception as e:
            self.logger.error(f"업데이트 프로세스 오류: {e}")
            return False, f"업데이트 오류: {str(e)}"
            
    def rollback_update(self, backup_path):
        """업데이트 롤백"""
        try:
            if not backup_path or not os.path.exists(backup_path):
                self.logger.error("백업 파일이 없습니다.")
                return False
                
            self.logger.info("업데이트 롤백 중...")
            
            # 현재 앱 디렉토리 삭제 (venv 제외)
            for item in os.listdir(self.app_dir):
                if item not in ['venv', 'backups']:
                    item_path = os.path.join(self.app_dir, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                        
            # 백업에서 복원
            for item in os.listdir(backup_path):
                src = os.path.join(backup_path, item)
                dst = os.path.join(self.app_dir, item)
                
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                    
            self.logger.info("롤백 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"롤백 실패: {e}")
            return False


def main():
    """메인 함수 - 업데이트 확인 및 실행"""
    updater = AutoUpdater()
    
    print("🔄 자동 업데이트 확인 중...")
    success, message = updater.check_and_update()
    
    if success:
        print(f"✅ {message}")
        print("🔄 프로그램을 재시작해주세요.")
    else:
        print(f"ℹ️ {message}")
        
    return success


if __name__ == "__main__":
    main()
