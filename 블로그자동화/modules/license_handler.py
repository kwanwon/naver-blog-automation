import hashlib
import os
import json
import uuid
import datetime
import requests

class LicenseHandler:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.license_file = os.path.join(self.base_dir, 'config', 'license.json')
        self.license_server_url = "https://your-license-server.com/api/validate"  # 라이선스 서버 URL
        
    def generate_machine_id(self):
        """기기 고유 ID 생성"""
        machine_id = str(uuid.getnode())  # MAC 주소 기반 ID
        return hashlib.sha256(machine_id.encode()).hexdigest()
        
    def validate_license(self, serial_key):
        """시리얼 키 유효성 검사"""
        machine_id = self.generate_machine_id()
        
        try:
            # 로컬 검증
            key_parts = serial_key.split('-')
            if len(key_parts) != 5 or any(len(part) != 5 for part in key_parts):
                return False, "잘못된 시리얼 키 형식입니다."
                
            # 서버 검증 (온라인)
            try:
                response = requests.post(
                    self.license_server_url,
                    json={
                        'serial_key': serial_key,
                        'machine_id': machine_id
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('valid'):
                        # 라이선스 저장
                        self.save_license(serial_key, data.get('expiry'), machine_id)
                        return True, "라이선스가 유효합니다."
                    else:
                        return False, data.get('message', "유효하지 않은 라이선스입니다.")
                        
            except requests.RequestException:
                # 오프라인 모드: 로컬 라이선스 확인
                if os.path.exists(self.license_file):
                    with open(self.license_file, 'r') as f:
                        license_data = json.load(f)
                        
                    if license_data.get('serial_key') == serial_key and license_data.get('machine_id') == machine_id:
                        # 만료일 확인
                        if 'expiry' in license_data:
                            expiry = datetime.datetime.fromisoformat(license_data['expiry'])
                            if expiry > datetime.datetime.now():
                                return True, "라이선스가 유효합니다. (오프라인 모드)"
                            else:
                                return False, "라이선스가 만료되었습니다."
                
            return False, "라이선스를 확인할 수 없습니다."
                
        except Exception as e:
            return False, f"라이선스 검증 중 오류 발생: {str(e)}"
    
    def save_license(self, serial_key, expiry, machine_id):
        """라이선스 정보 저장"""
        os.makedirs(os.path.dirname(self.license_file), exist_ok=True)
        
        license_data = {
            'serial_key': serial_key,
            'machine_id': machine_id,
            'activation_date': datetime.datetime.now().isoformat(),
            'expiry': expiry
        }
        
        with open(self.license_file, 'w') as f:
            json.dump(license_data, f)
            
    def check_license_status(self):
        """현재 라이선스 상태 확인"""
        if not os.path.exists(self.license_file):
            return False, "라이선스가 등록되지 않았습니다."
            
        try:
            with open(self.license_file, 'r') as f:
                license_data = json.load(f)
                
            serial_key = license_data.get('serial_key')
            machine_id = license_data.get('machine_id')
            
            # 기기 ID 확인
            current_machine_id = self.generate_machine_id()
            if machine_id != current_machine_id:
                return False, "라이선스가 이 기기에 등록되지 않았습니다."
                
            # 만료일 확인
            if 'expiry' in license_data:
                expiry = datetime.datetime.fromisoformat(license_data['expiry'])
                if expiry <= datetime.datetime.now():
                    return False, "라이선스가 만료되었습니다."
            
            # 온라인 검증 시도
            try:
                return self.validate_license(serial_key)
            except:
                # 오프라인 모드에서는 로컬 정보만으로 유효성 검사
                return True, "라이선스가 유효합니다. (오프라인 모드)"
                
        except Exception as e:
            return False, f"라이선스 상태 확인 중 오류 발생: {str(e)}" 