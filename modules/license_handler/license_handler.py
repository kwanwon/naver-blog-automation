import os
import json
import requests
import hashlib
import platform
import uuid

class LicenseHandler:
    """라이선스 관리 클래스"""
    
    license_server_url = "http://localhost:5000/api/validate"
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.config_dir = os.path.join(self.base_dir, 'config')
        self.license_file = os.path.join(self.config_dir, 'license.json')
        
        # 설정 디렉토리가 없으면 생성
        os.makedirs(self.config_dir, exist_ok=True)
    
    def get_device_info(self):
        """기기 정보 수집"""
        try:
            # 시스템 정보 수집
            system_info = {
                'platform': platform.system(),
                'platform_release': platform.release(),
                'platform_version': platform.version(),
                'architecture': platform.machine(),
                'processor': platform.processor(),
                'hostname': platform.node()
            }
            
            # 고유 식별자 생성
            system_str = json.dumps(system_info, sort_keys=True)
            device_hash = hashlib.sha256(system_str.encode()).hexdigest()
            
            # MAC 주소 추가 시도 (보안상의 이유로 실패할 수 있음)
            try:
                mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 8*6, 8)][::-1])
                device_hash = hashlib.sha256((device_hash + mac).encode()).hexdigest()
            except:
                pass
                
            return {
                'device_hash': device_hash,
                'system_info': system_info
            }
        except Exception as e:
            print(f"기기 정보 수집 중 오류: {str(e)}")
            return {'device_hash': 'unknown', 'system_info': {}}
    
    def save_license(self, license_key, license_data):
        """라이선스 정보 저장"""
        try:
            data = {
                'license_key': license_key,
                'license_data': license_data,
                'device_info': self.get_device_info()
            }
            
            with open(self.license_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            return True
        except Exception as e:
            print(f"라이선스 저장 중 오류: {str(e)}")
            return False
    
    def load_license(self):
        """저장된 라이선스 정보 로드"""
        try:
            if os.path.exists(self.license_file):
                with open(self.license_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"라이선스 로드 중 오류: {str(e)}")
            return None
    
    def validate_license(self, license_key=None):
        """라이선스 유효성 검증"""
        try:
            # 라이선스 키가 제공되지 않으면 저장된 키 사용
            if not license_key:
                license_data = self.load_license()
                if license_data and 'license_key' in license_data:
                    license_key = license_data['license_key']
                else:
                    return False, "라이선스 키가 없습니다."
            
            # 기기 정보 수집
            device_info = self.get_device_info()
            
            # 서버에 검증 요청
            try:
                response = requests.post(
                    self.license_server_url,
                    json={
                        'license_key': license_key,
                        'device_info': device_info
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('valid', False):
                        # 유효한 라이선스면 저장
                        self.save_license(license_key, result)
                        return True, "라이선스가 유효합니다."
                    else:
                        return False, result.get('message', "유효하지 않은 라이선스입니다.")
                else:
                    return False, f"서버 오류: {response.status_code}"
            except requests.RequestException as e:
                # 서버 연결 실패 시 로컬 검증 시도
                return self.validate_license_locally(license_key)
                
        except Exception as e:
            print(f"라이선스 검증 중 오류: {str(e)}")
            return False, f"검증 중 오류 발생: {str(e)}"
    
    def validate_license_locally(self, license_key):
        """오프라인 상태에서 로컬 라이선스 검증"""
        try:
            # 저장된 라이선스 정보 로드
            license_data = self.load_license()
            
            if not license_data:
                return False, "저장된 라이선스 정보가 없습니다."
                
            # 라이선스 키 일치 여부 확인
            if license_data.get('license_key') != license_key:
                return False, "라이선스 키가 일치하지 않습니다."
                
            # 기기 정보 일치 여부 확인
            current_device = self.get_device_info()
            saved_device = license_data.get('device_info', {})
            
            if current_device.get('device_hash') != saved_device.get('device_hash'):
                return False, "기기 정보가 일치하지 않습니다."
                
            # 라이선스 만료 여부 확인 (라이선스 데이터에 expiry_date가 있는 경우)
            license_info = license_data.get('license_data', {})
            if 'expiry_date' in license_info:
                from datetime import datetime
                try:
                    expiry = datetime.strptime(license_info['expiry_date'], "%Y-%m-%d").date()
                    today = datetime.now().date()
                    
                    if today > expiry:
                        return False, "라이선스가 만료되었습니다."
                except:
                    pass
            
            return True, "로컬 라이선스 검증 성공"
            
        except Exception as e:
            print(f"로컬 라이선스 검증 중 오류: {str(e)}")
            return False, f"로컬 검증 중 오류 발생: {str(e)}" 