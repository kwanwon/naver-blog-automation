#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 블로그 자동화 도구 - 자동 업데이트 모듈
"""

import os
import sys
import json
import time
import shutil
import tempfile
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
import ssl
import logging

# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 콘솔 핸들러
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 파일 핸들러 (업데이트 로그를 별도로 저장)
try:
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    file_handler = logging.FileHandler(os.path.join(log_dir, 'updater.log'))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
except Exception as e:
    print(f"로그 파일 설정 중 오류: {str(e)}")

class AppUpdater:
    """앱 자동 업데이트 관리 클래스"""
    
    def __init__(self, app_name="네이버블로그자동화", current_version="1.0.0"):
        """초기화"""
        self.app_name = app_name
        self.current_version = current_version
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.update_url = "https://api.github.com/repos/yourusername/naver-blog-automation/releases/latest"
        self.update_check_interval = 24 * 60 * 60  # 24시간 (초 단위)
        self.last_check_file = os.path.join(self.base_dir, 'config', 'last_update_check.json')
        self.config_file = os.path.join(self.base_dir, 'config', 'update_config.json')
        self.load_config()
        
    def load_config(self):
        """업데이트 설정 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.update_url = config.get('update_url', self.update_url)
                    self.update_check_interval = config.get('update_check_interval', self.update_check_interval)
                    logger.info(f"업데이트 설정 로드: {self.update_url}, 체크 간격: {self.update_check_interval}초")
            else:
                # 설정 파일이 없으면 기본값으로 생성
                self.save_config()
        except Exception as e:
            logger.error(f"업데이트 설정 로드 중 오류: {str(e)}")
            
    def save_config(self):
        """업데이트 설정 저장"""
        try:
            config_dir = os.path.dirname(self.config_file)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                
            config = {
                'update_url': self.update_url,
                'update_check_interval': self.update_check_interval,
                'last_saved': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
                logger.info("업데이트 설정 저장 완료")
        except Exception as e:
            logger.error(f"업데이트 설정 저장 중 오류: {str(e)}")
    
    def should_check_update(self):
        """업데이트를 확인해야 하는지 여부 확인"""
        try:
            if not os.path.exists(self.last_check_file):
                logger.info("업데이트 체크 기록 없음: 업데이트 확인 필요")
                return True
                
            with open(self.last_check_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                last_check_time = data.get('last_check_time', 0)
                
            # 마지막 체크 시간으로부터 설정된 간격이 지났는지 확인
            current_time = time.time()
            if current_time - last_check_time >= self.update_check_interval:
                logger.info(f"마지막 업데이트 체크 후 {self.update_check_interval}초가 지났습니다. 업데이트 확인 필요")
                return True
            else:
                logger.info(f"마지막 업데이트 체크 후 {int(current_time - last_check_time)}초 경과. 업데이트 확인 불필요")
                return False
        except Exception as e:
            logger.error(f"업데이트 체크 시간 확인 중 오류: {str(e)}")
            # 오류 발생 시 안전하게 업데이트 확인 수행
            return True
    
    def update_last_check_time(self):
        """마지막 업데이트 확인 시간 갱신"""
        try:
            config_dir = os.path.dirname(self.last_check_file)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                
            data = {
                'last_check_time': time.time(),
                'last_check_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self.last_check_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"마지막 업데이트 확인 시간 갱신: {data['last_check_date']}")
        except Exception as e:
            logger.error(f"마지막 업데이트 확인 시간 갱신 중 오류: {str(e)}")
    
    def check_for_updates(self, force=False):
        """최신 업데이트 확인"""
        if not force and not self.should_check_update():
            logger.info("최근에 이미 업데이트를 확인했습니다. 건너뜁니다.")
            return None
            
        try:
            logger.info(f"업데이트 확인 중: {self.update_url}")
            # SSL 인증서 검증 우회 (개발 환경에서만 사용)
            context = ssl._create_unverified_context()
            
            # API 응답 가져오기
            with urllib.request.urlopen(self.update_url, context=context) as response:
                data = json.loads(response.read().decode('utf-8'))
                
            # 마지막 업데이트 확인 시간 갱신
            self.update_last_check_time()
            
            latest_version = data.get('tag_name', '').lstrip('v')
            download_url = None
            
            # dmg 파일 URL 찾기 (macOS용)
            for asset in data.get('assets', []):
                if asset.get('name', '').endswith('.dmg'):
                    download_url = asset.get('browser_download_url')
                    break
            
            if not latest_version or not download_url:
                logger.warning("최신 버전 정보를 찾을 수 없습니다.")
                return None
                
            # 버전 비교
            if self._is_newer_version(latest_version):
                logger.info(f"새 버전 발견: {latest_version} (현재: {self.current_version})")
                return {
                    'version': latest_version,
                    'download_url': download_url,
                    'release_notes': data.get('body', '릴리스 노트가 없습니다.')
                }
            else:
                logger.info(f"이미 최신 버전 사용 중: {self.current_version}")
                return None
                
        except urllib.error.URLError as e:
            logger.error(f"업데이트 확인 중 네트워크 오류: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"업데이트 확인 중 오류: {str(e)}")
            return None
    
    def _is_newer_version(self, latest_version):
        """최신 버전이 현재 버전보다 새로운지 확인"""
        try:
            # 버전 비교 (단순 문자열 비교가 아닌 semantic versioning 비교)
            current_parts = [int(p) for p in self.current_version.split('.')]
            latest_parts = [int(p) for p in latest_version.split('.')]
            
            # 부족한 부분은 0으로 채움
            while len(current_parts) < 3:
                current_parts.append(0)
            while len(latest_parts) < 3:
                latest_parts.append(0)
            
            # 각 부분 비교
            for i in range(3):
                if latest_parts[i] > current_parts[i]:
                    return True
                elif latest_parts[i] < current_parts[i]:
                    return False
            
            # 모든 부분이 동일하면 새 버전이 아님
            return False
        except Exception as e:
            logger.error(f"버전 비교 중 오류: {str(e)}")
            # 안전하게 처리하기 위해 False 반환
            return False
    
    def download_update(self, download_url, target_path=None):
        """업데이트 파일 다운로드"""
        try:
            if not target_path:
                # 임시 디렉토리에 다운로드
                temp_dir = tempfile.gettempdir()
                filename = os.path.basename(download_url)
                target_path = os.path.join(temp_dir, filename)
            
            logger.info(f"업데이트 다운로드 중: {download_url} -> {target_path}")
            
            # SSL 인증서 검증 우회 (개발 환경에서만 사용)
            context = ssl._create_unverified_context()
            
            # 파일 다운로드
            with urllib.request.urlopen(download_url, context=context) as response, open(target_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            
            logger.info(f"업데이트 다운로드 완료: {target_path}")
            return target_path
        except Exception as e:
            logger.error(f"업데이트 다운로드 중 오류: {str(e)}")
            return None
    
    def install_update(self, dmg_path):
        """업데이트 설치 (macOS)"""
        try:
            if not os.path.exists(dmg_path):
                logger.error(f"DMG 파일이 존재하지 않습니다: {dmg_path}")
                return False
            
            logger.info(f"DMG 파일 마운트 중: {dmg_path}")
            
            # DMG 마운트
            mount_cmd = f"hdiutil attach '{dmg_path}'"
            result = subprocess.run(mount_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"DMG 마운트 실패: {result.stderr}")
                return False
            
            # 마운트된 볼륨 정보 파싱
            mount_output = result.stdout
            lines = mount_output.strip().split('\n')
            
            volume_path = None
            for line in lines:
                if '/Volumes/' in line:
                    parts = line.strip().split()
                    volume_path = parts[-1]
                    break
            
            if not volume_path:
                logger.error("마운트된 볼륨 경로를 찾을 수 없습니다.")
                return False
            
            logger.info(f"볼륨 마운트됨: {volume_path}")
            
            # 애플리케이션 폴더로 앱 복사
            app_in_volume = f"{volume_path}/{self.app_name}.app"
            if not os.path.exists(app_in_volume):
                logger.error(f"마운트된 볼륨에 앱이 없습니다: {app_in_volume}")
                # DMG 언마운트
                subprocess.run(f"hdiutil detach '{volume_path}' -force", shell=True)
                return False
            
            logger.info("애플리케이션 폴더로 앱 복사 중...")
            
            # 현재 실행 중인 앱 종료 메시지
            logger.info("업데이트를 위해 앱을 재시작해야 합니다.")
            
            # 앱 복사 명령어
            copy_cmd = f"cp -R '{app_in_volume}' /Applications/"
            copy_result = subprocess.run(copy_cmd, shell=True, capture_output=True, text=True)
            
            # DMG 언마운트
            subprocess.run(f"hdiutil detach '{volume_path}' -force", shell=True)
            
            if copy_result.returncode != 0:
                logger.error(f"앱 복사 실패: {copy_result.stderr}")
                return False
            
            logger.info("업데이트가 성공적으로 설치되었습니다.")
            return True
            
        except Exception as e:
            logger.error(f"업데이트 설치 중 오류: {str(e)}")
            return False
    
    def check_and_update(self, show_no_update_message=True, auto_install=False):
        """업데이트 확인 및 설치 프로세스 실행"""
        try:
            logger.info("업데이트 확인 및 설치 프로세스 시작")
            
            # 업데이트 확인
            update_info = self.check_for_updates()
            
            if not update_info:
                if show_no_update_message:
                    logger.info("업데이트가 필요하지 않습니다.")
                return {
                    'status': 'no_update',
                    'message': '현재 최신 버전을 사용 중입니다.'
                }
            
            # 사용자에게 업데이트 알림
            message = f"새 버전 {update_info['version']}이(가) 있습니다. (현재: {self.current_version})\n\n"
            message += "릴리스 노트:\n" + update_info['release_notes']
            
            logger.info(message)
            
            if auto_install:
                # 자동 설치 모드
                logger.info("자동 설치 모드로 업데이트를 다운로드합니다.")
                
                # 업데이트 다운로드
                dmg_path = self.download_update(update_info['download_url'])
                if not dmg_path:
                    return {
                        'status': 'download_failed',
                        'message': '업데이트 다운로드에 실패했습니다.'
                    }
                
                # 업데이트 설치
                if self.install_update(dmg_path):
                    return {
                        'status': 'updated',
                        'message': f'업데이트 {update_info["version"]}이(가) 설치되었습니다.',
                        'version': update_info['version']
                    }
                else:
                    return {
                        'status': 'install_failed',
                        'message': '업데이트 설치에 실패했습니다.'
                    }
            else:
                # 사용자 선택 모드
                return {
                    'status': 'update_available',
                    'message': message,
                    'version': update_info['version'],
                    'download_url': update_info['download_url']
                }
                
        except Exception as e:
            logger.error(f"업데이트 프로세스 중 오류: {str(e)}")
            return {
                'status': 'error',
                'message': f'업데이트 확인 중 오류가 발생했습니다: {str(e)}'
            }

# 테스트 코드
if __name__ == "__main__":
    updater = AppUpdater()
    result = updater.check_and_update(auto_install=False)
    print(result) 