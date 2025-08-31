#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
블로그자동화용 시리얼 인증 모듈
- 기존 시리얼관리 프로그램과 연동
- 간단하고 독립적인 구조
- 원격 서버 연동 지원
"""

import os
import json
import sqlite3
import requests
import logging
import socket
import platform
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

class BlogSerialAuth:
    """블로그자동화용 시리얼 인증 클래스"""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(self.base_dir, "serial_config.json")
        self.server_url = "https://aimaster-serial.onrender.com"
        
        # 로깅 설정
        self.setup_logging()
        
        # 시리얼관리 DB 경로 (동적으로 찾기)
        self.serial_db_path = self.find_serial_db()
        
    def setup_logging(self):
        """로깅 설정"""
        log_file = os.path.join(self.base_dir, "blog_serial_auth.log")
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def find_serial_db(self) -> Optional[str]:
        """시리얼관리 DB 파일 찾기"""
        possible_paths = [
            # 상위 디렉토리에서 시리얼관리 찾기
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(self.base_dir))), "시리얼관리", "serials.db"),
            # 같은 레벨에서 찾기
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(self.base_dir)))), "시리얼관리", "serials.db"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.logger.info(f"시리얼 DB 발견: {path}")
                return path
                
        self.logger.warning("시리얼 DB를 찾을 수 없습니다.")
        return None
    
    def get_device_info(self) -> Dict:
        """현재 디바이스 정보 수집"""
        try:
            # 호스트명 가져오기
            try:
                hostname = socket.gethostname()
            except:
                hostname = "unknown"
            
            # IP 주소 가져오기
            try:
                ip_address = socket.gethostbyname(hostname)
            except:
                ip_address = "0.0.0.0"
            
            # macOS 시스템 정보 가져오기
            device_info = {
                "hostname": hostname,
                "ip_address": ip_address,
                "system_manufacturer": "Apple",
                "os_name": platform.system(),
                "os_version": platform.version(),
                "processor": platform.processor() or "Apple Silicon",
                "registration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 시스템 모델 정보 가져오기 (macOS)
            try:
                model = subprocess.check_output(['sysctl', '-n', 'hw.model']).decode('utf-8').strip()
                device_info['system_model'] = model
            except:
                device_info['system_model'] = "Unknown Mac"
            
            # CPU 정보 가져오기
            try:
                processor = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string']).decode('utf-8').strip()
                device_info['processor'] = processor
            except:
                pass
            
            # 메모리 정보 가져오기
            try:
                import psutil
                memory = psutil.virtual_memory()
                device_info['total_memory'] = f"{memory.total / (1024**3):.2f}GB"
            except:
                device_info['total_memory'] = "8.00GB"
            
            self.logger.info(f"디바이스 정보 수집 완료: {device_info}")
            return device_info
            
        except Exception as e:
            self.logger.error(f"디바이스 정보 수집 오류: {e}")
            # 기본 정보 반환
            return {
                "hostname": "unknown",
                "ip_address": "0.0.0.0",
                "system_manufacturer": "Apple",
                "system_model": "Unknown Mac",
                "os_name": "macOS",
                "os_version": "Unknown",
                "processor": "Unknown Processor",
                "total_memory": "8.00GB",
                "registration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def load_config(self) -> Dict:
        """설정 파일 로드"""
        default_config = {
            "serial_number": "",
            "last_validation": "",
            "expiry_date": "",
            "validation_count": 0
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 기본값으로 누락된 키 채우기
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                self.logger.error(f"설정 파일 로드 오류: {e}")
                
        return default_config
    
    def save_config(self, config: Dict):
        """설정 파일 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.logger.info("설정 파일 저장 완료")
        except Exception as e:
            self.logger.error(f"설정 파일 저장 오류: {e}")
    
    def validate_serial_local(self, serial_number: str) -> Tuple[bool, str, Optional[datetime]]:
        """로컬 DB에서 시리얼 유효성 검증"""
        if not self.serial_db_path or not os.path.exists(self.serial_db_path):
            return False, "시리얼 관리 DB를 찾을 수 없습니다.", None
            
        try:
            conn = sqlite3.connect(self.serial_db_path)
            cursor = conn.cursor()
            
            # 시리얼 번호 조회
            cursor.execute("""
                SELECT status, expiry_date, memo 
                FROM serials 
                WHERE serial_number = ? AND is_deleted = 0
            """, (serial_number,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return False, "유효하지 않은 시리얼 번호입니다.", None
                
            status, expiry_date_str, memo = result
            
            # 만료일 확인
            if expiry_date_str:
                try:
                    expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
                    
                    # 만료 확인
                    if expiry_date < datetime.now():
                        return False, "시리얼 번호가 만료되었습니다.", expiry_date
                    
                    # 7주 전 알림 (49일)
                    warning_date = expiry_date - timedelta(days=49)
                    if datetime.now() >= warning_date:
                        days_left = (expiry_date - datetime.now()).days
                        return True, f"주의: {days_left}일 후 만료됩니다. 갱신이 필요합니다.", expiry_date
                    
                    return True, "유효한 시리얼 번호입니다.", expiry_date
                    
                except ValueError:
                    return False, "만료일 형식 오류입니다.", None
            else:
                return False, "만료일이 설정되지 않았습니다.", None
                
        except Exception as e:
            self.logger.error(f"로컬 DB 검증 오류: {e}")
            return False, f"DB 오류: {str(e)}", None
    
    def validate_serial_remote(self, serial_number: str) -> Tuple[bool, str]:
        """원격 서버에서 시리얼 유효성 검증"""
        try:
            response = requests.get(
                f"{self.server_url}/api/serial/{serial_number}", 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                
                if status == 'active':
                    return True, "서버 인증 성공"
                else:
                    return False, f"서버에서 비활성 상태: {status}"
            else:
                return False, "서버 인증 실패"
                
        except requests.RequestException as e:
            self.logger.warning(f"서버 연결 실패: {e}")
            return False, "서버 연결 실패 (오프라인 모드)"
    
    def check_serial(self, serial_number: str) -> Tuple[bool, str, Optional[datetime]]:
        """시리얼 번호 종합 검증 (로컬 우선, 서버 보조)"""
        
        # 1. 로컬 DB 검증 (주요)
        local_valid, local_message, expiry_date = self.validate_serial_local(serial_number)
        
        if not local_valid:
            return False, local_message, expiry_date
        
        # 2. 원격 서버 검증 (보조) - 실패해도 로컬이 유효하면 통과
        try:
            remote_valid, remote_message = self.validate_serial_remote(serial_number)
            if not remote_valid and "오프라인" not in remote_message:
                self.logger.warning(f"서버 검증 실패: {remote_message}")
                # 서버 검증 실패해도 로컬이 유효하면 경고만 표시
                local_message += f" (서버: {remote_message})"
        except Exception as e:
            self.logger.warning(f"서버 검증 중 오류: {e}")
        
        return True, local_message, expiry_date
    
    def update_device_info_and_usage(self, serial_number: str) -> bool:
        """시리얼에 디바이스 정보 등록 및 사용횟수 증가"""
        if not self.serial_db_path or not os.path.exists(self.serial_db_path):
            self.logger.error("시리얼 DB를 찾을 수 없습니다.")
            return False
        
        try:
            # 디바이스 정보 수집
            device_info = self.get_device_info()
            device_info_json = json.dumps(device_info, ensure_ascii=False)
            
            # 로컬 DB 업데이트
            conn = sqlite3.connect(self.serial_db_path)
            cursor = conn.cursor()
            
            # 현재 사용횟수 가져오기
            cursor.execute("""
                SELECT activation_count 
                FROM serials 
                WHERE serial_number = ?
            """, (serial_number,))
            
            result = cursor.fetchone()
            current_count = result[0] if result else 0
            new_count = current_count + 1
            
            # 디바이스 정보와 사용횟수, 상태 업데이트
            cursor.execute("""
                UPDATE serials 
                SET device_info = ?, 
                    activation_count = ?,
                    status = '사용중',
                    last_check_date = ?
                WHERE serial_number = ?
            """, (device_info_json, new_count, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), serial_number))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"디바이스 정보 및 사용횟수 업데이트 완료: {serial_number} (사용횟수: {new_count})")
            
            # 서버에도 업데이트 시도
            try:
                response = requests.patch(
                    f"{self.server_url}/api/serials/{serial_number}",
                    json={
                        "device_info": device_info,
                        "activation_count": new_count,
                        "status": "사용중"
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.logger.info("서버 업데이트 성공")
                else:
                    self.logger.warning(f"서버 업데이트 실패: {response.status_code}")
                    
            except Exception as server_e:
                self.logger.warning(f"서버 업데이트 실패: {server_e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"디바이스 정보 업데이트 오류: {e}")
            return False
    
    def is_serial_required(self) -> bool:
        """시리얼 입력이 필요한지 확인 (실제 유효성 검증 포함)"""
        config = self.load_config()
        
        # 시리얼이 없으면 필요
        serial_number = config.get("serial_number")
        if not serial_number:
            return True
        
        # 마지막 검증일이 없으면 필요
        if not config.get("last_validation"):
            return True
        
        # 마지막 검증이 7일 이상 지났으면 재검증 필요
        try:
            last_validation = datetime.fromisoformat(config["last_validation"])
            if (datetime.now() - last_validation).days >= 7:
                return True
        except:
            return True
        
        # 실제 시리얼 유효성 확인
        try:
            valid, message, expiry_date = self.check_serial(serial_number)
            if not valid:
                self.logger.info(f"시리얼이 무효하므로 재입력 필요: {message}")
                return True
        except Exception as e:
            self.logger.error(f"시리얼 검증 중 오류: {e}")
            return True
        
        return False
    
    def save_validation(self, serial_number: str, expiry_date: Optional[datetime] = None):
        """검증 성공 정보 저장 및 디바이스 정보 업데이트"""
        config = self.load_config()
        config["serial_number"] = serial_number
        config["last_validation"] = datetime.now().isoformat()
        config["validation_count"] = config.get("validation_count", 0) + 1
        
        if expiry_date:
            config["expiry_date"] = expiry_date.isoformat()
        
        self.save_config(config)
        self.logger.info(f"시리얼 검증 저장: {serial_number}")
        
        # 디바이스 정보 업데이트 및 사용횟수 증가
        self.update_device_info_and_usage(serial_number)

# 간단한 테스트 함수
if __name__ == "__main__":
    auth = BlogSerialAuth()
    
    # 테스트용 시리얼 번호 (실제로는 UI에서 입력받음)
    test_serial = "TEST-SERIAL-001"
    
    valid, message, expiry = auth.check_serial(test_serial)
    print(f"검증 결과: {valid}")
    print(f"메시지: {message}")
    if expiry:
        print(f"만료일: {expiry}")
