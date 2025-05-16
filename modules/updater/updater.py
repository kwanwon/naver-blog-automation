import os
import json
import requests
import tempfile
import shutil
import platform
import subprocess
from datetime import datetime

class AppUpdater:
    """애플리케이션 업데이트 관리 클래스"""
    
    update_server_url = "http://localhost:5000/api/check-update"
    
    def __init__(self, app_name, current_version):
        self.app_name = app_name
        self.current_version = current_version
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.config_dir = os.path.join(self.base_dir, 'config')
        self.update_file = os.path.join(self.config_dir, 'update_info.json')
        
        # 설정 디렉토리가 없으면 생성
        os.makedirs(self.config_dir, exist_ok=True)
    
    def check_for_updates(self, force=False, license_handler=None):
        """업데이트 확인"""
        try:
            # 마지막 업데이트 확인 시간 로드
            last_check = self._load_last_check()
            
            # 강제 확인이 아니고 24시간 이내에 확인했으면 건너뜀
            if not force and last_check:
                last_check_time = datetime.strptime(last_check['timestamp'], "%Y-%m-%d %H:%M:%S")
                elapsed = (datetime.now() - last_check_time).total_seconds() / 3600
                
                if elapsed < 24 and 'update_info' in last_check:
                    return last_check['update_info']
            
            # 라이선스 정보 가져오기 (제공된 경우)
            license_key = None
            if license_handler:
                license_data = license_handler.load_license()
                if license_data and 'license_key' in license_data:
                    license_key = license_data['license_key']
            
            # 서버에 업데이트 확인 요청
            response = requests.post(
                self.update_server_url,
                json={
                    'app_name': self.app_name,
                    'current_version': self.current_version,
                    'platform': platform.system(),
                    'architecture': platform.machine(),
                    'license_key': license_key
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 업데이트 정보 저장
                self._save_check_result(result)
                
                # 업데이트가 있으면 정보 반환
                if result.get('update_available', False):
                    return result
            
            return None
            
        except Exception as e:
            print(f"업데이트 확인 중 오류: {str(e)}")
            return None
    
    def download_update(self, update_info):
        """업데이트 다운로드"""
        try:
            if not update_info or 'download_url' not in update_info:
                return False, "다운로드 URL이 없습니다."
            
            # 임시 디렉토리에 다운로드
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = os.path.join(temp_dir, "update.zip")
                
                # 파일 다운로드
                response = requests.get(update_info['download_url'], stream=True)
                if response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    # 다운로드 정보 저장
                    update_info['download_path'] = file_path
                    update_info['download_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self._save_check_result({'update_info': update_info})
                    
                    return True, file_path
                else:
                    return False, f"다운로드 실패: {response.status_code}"
                
        except Exception as e:
            print(f"업데이트 다운로드 중 오류: {str(e)}")
            return False, f"다운로드 중 오류 발생: {str(e)}"
    
    def install_update(self, file_path):
        """업데이트 설치"""
        try:
            # 플랫폼별 설치 로직
            system = platform.system()
            
            if system == "Windows":
                # Windows에서는 설치 프로그램 실행
                subprocess.Popen([file_path])
                return True, "업데이트 설치 프로그램이 실행되었습니다."
            elif system == "Darwin":  # macOS
                # macOS에서는 .app 파일 압축 해제 및 이동
                # 실제 구현은 더 복잡할 수 있음
                return False, "macOS 업데이트 설치는 아직 구현되지 않았습니다."
            else:
                return False, f"지원되지 않는 플랫폼: {system}"
                
        except Exception as e:
            print(f"업데이트 설치 중 오류: {str(e)}")
            return False, f"설치 중 오류 발생: {str(e)}"
    
    def _load_last_check(self):
        """마지막 업데이트 확인 결과 로드"""
        try:
            if os.path.exists(self.update_file):
                with open(self.update_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"업데이트 정보 로드 중 오류: {str(e)}")
            return None
    
    def _save_check_result(self, result):
        """업데이트 확인 결과 저장"""
        try:
            data = {
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'app_name': self.app_name,
                'current_version': self.current_version,
                'update_info': result
            }
            
            with open(self.update_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            return True
        except Exception as e:
            print(f"업데이트 정보 저장 중 오류: {str(e)}")
            return False 