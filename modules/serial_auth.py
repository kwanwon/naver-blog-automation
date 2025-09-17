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
        # 현재 경로: /Desktop/-/블로그자동화/config/naver-blog-automation/modules/
        # 목표 경로: /Desktop/-/시리얼관리/serials.db
        
        # 현재 디렉토리에서 상위로 올라가면서 시리얼관리 폴더 찾기
        current_dir = self.base_dir
        possible_paths = []
        
        # 상위 디렉토리를 순차적으로 탐색 (최대 10단계)
        for i in range(10):
            if i == 0:
                search_dir = current_dir
            else:
                search_dir = current_dir
                for _ in range(i):
                    search_dir = os.path.dirname(search_dir)
            
            # 시리얼관리 폴더가 있는지 확인
            serial_dir = os.path.join(search_dir, "시리얼관리")
            if os.path.exists(serial_dir):
                db_path = os.path.join(serial_dir, "serials.db")
                possible_paths.append(db_path)
        
        # 추가 백업 경로들 (기존 방식)
        backup_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(self.base_dir))))), "시리얼관리", "serials.db"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(self.base_dir))), "시리얼관리", "serials.db"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(self.base_dir)))), "시리얼관리", "serials.db"),
        ]
        
        # 중복 제거하면서 백업 경로 추가
        for path in backup_paths:
            if path not in possible_paths:
                possible_paths.append(path)
        
        self.logger.info(f"현재 base_dir: {self.base_dir}")
        
        for i, path in enumerate(possible_paths):
            self.logger.info(f"경로 {i+1} 시도: {path}")
            if os.path.exists(path):
                self.logger.info(f"✅ 시리얼 DB 발견: {path}")
                return path
            else:
                self.logger.info(f"❌ 경로 없음: {path}")
                
        self.logger.error("❌ 모든 경로에서 시리얼 DB를 찾을 수 없습니다.")
        self.logger.error("가능한 해결방법:")
        self.logger.error("1. 시리얼관리 프로그램이 실행 중인지 확인")
        self.logger.error("2. serials.db 파일이 시리얼관리 폴더에 있는지 확인")
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
        """로컬 DB에서 시리얼 유효성 검증 (블랙리스트 확인 추가)"""
        if not self.serial_db_path or not os.path.exists(self.serial_db_path):
            return False, "시리얼 관리 DB를 찾을 수 없습니다.", None
            
        try:
            conn = sqlite3.connect(self.serial_db_path)
            cursor = conn.cursor()
            
            # 시리얼 번호 조회 (블랙리스트 확인 추가)
            cursor.execute("""
                SELECT status, expiry_date, memo, is_blacklisted 
                FROM serials 
                WHERE serial_number = ? 
                AND is_deleted = 0
            """, (serial_number,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return False, "유효하지 않은 시리얼 번호입니다.", None
                
            status, expiry_date_str, memo, is_blacklisted = result
            
            # 블랙리스트 확인 (AI마스터와 동일)
            if is_blacklisted or status == "블랙리스트":
                return False, "블랙리스트된 시리얼입니다.", None
            
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
    
    def validate_serial_server_first(self, serial_number: str) -> Tuple[bool, str, Optional[datetime]]:
        """서버 우선 시리얼 검증 (AI마스터 방식)"""
        try:
            # 1. 서버에서 전체 시리얼 목록 조회 (AI마스터와 동일한 방식)
            self.logger.info(f"서버 우선 검증 시작: {serial_number[:8]}...")
            response = requests.get(
                f"{self.server_url}/api/serials", 
                timeout=30
            )
            
            if response.status_code == 200:
                serials_list = response.json()
                self.logger.info(f"서버에서 {len(serials_list)}개 시리얼 조회 완료")
                
                # 2. 입력한 시리얼과 매칭 검색
                matched_serial = None
                for serial_data in serials_list:
                    if serial_data.get("serial_number") == serial_number:
                        matched_serial = serial_data
                        break
                
                if not matched_serial:
                    return False, "유효하지 않은 시리얼 번호입니다.", None
                
                # 3. 실시간 상태 확인 (AI마스터와 동일한 로직)
                status = matched_serial.get("status", "알 수 없음")
                is_blacklisted = matched_serial.get("is_blacklisted", False)
                is_deleted = matched_serial.get("is_deleted", False)
                
                self.logger.info(f"서버 상태 확인 - status: {status}, blacklisted: {is_blacklisted}, deleted: {is_deleted}")
                
                # 4. 블랙리스트 즉시 차단
                if is_blacklisted or status == "블랙리스트":
                    return False, "블랙리스트된 시리얼입니다.", None
                
                # 5. 삭제된 시리얼 즉시 차단
                if is_deleted:
                    return False, "삭제된 시리얼입니다.", None
                
                # 6. 사용중 상태 확인 (다른 디바이스에서 사용중)
                if status == "사용중":
                    return False, "다른 디바이스에서 사용중입니다.", None
                
                # 7. 유효한 상태만 통과
                if status not in ["사용가능", "만료 예정"]:
                    return False, f"사용할 수 없는 상태입니다: {status}", None
                
                # 8. 만료일 확인
                expiry_date_str = matched_serial.get("expiry_date")
                expiry_date = None
                if expiry_date_str:
                    try:
                        expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
                        if expiry_date < datetime.now():
                            return False, "시리얼 번호가 만료되었습니다.", expiry_date
                        
                        # 7주 전 알림 (49일)
                        warning_date = expiry_date - timedelta(days=49)
                        if datetime.now() >= warning_date:
                            days_left = (expiry_date - datetime.now()).days
                            return True, f"주의: {days_left}일 후 만료됩니다. 갱신이 필요합니다.", expiry_date
                    except ValueError:
                        return False, "만료일 형식 오류입니다.", None
                
                return True, "서버 검증 성공 - 유효한 시리얼입니다.", expiry_date
            else:
                self.logger.warning(f"서버 응답 오류: {response.status_code}")
                return False, f"서버 오류: {response.status_code}", None
                
        except requests.RequestException as e:
            self.logger.warning(f"서버 연결 실패: {e}")
            return False, "서버 연결 실패 (오프라인 모드)", None
        except Exception as e:
            self.logger.error(f"서버 검증 중 예외 발생: {e}")
            return False, f"서버 검증 오류: {str(e)}", None
    
    def validate_serial_remote(self, serial_number: str) -> Tuple[bool, str]:
        """원격 서버에서 시리얼 유효성 검증 (기존 호환성 유지)"""
        valid, message, expiry_date = self.validate_serial_server_first(serial_number)
        return valid, message
    
    def check_serial(self, serial_number: str) -> Tuple[bool, str, Optional[datetime]]:
        """시리얼 번호 종합 검증 (서버 우선, 로컬 백업 - AI마스터 방식)"""
        
        # 1. 서버 우선 검증 (AI마스터와 동일한 방식)
        self.logger.info(f"시리얼 검증 시작 (서버 우선): {serial_number[:8]}...")
        
        try:
            server_valid, server_message, expiry_date = self.validate_serial_server_first(serial_number)
            
            if server_valid:
                self.logger.info("서버 검증 성공")
                # AI마스터 방식: 검증 성공 시 사용횟수 증가
                self.update_device_info_and_usage(serial_number)
                return True, server_message, expiry_date
            elif "오프라인" not in server_message and "연결 실패" not in server_message:
                # 서버에서 명확히 거부한 경우 (블랙리스트, 삭제, 사용중 등)
                self.logger.warning(f"서버에서 시리얼 거부: {server_message}")
                return False, server_message, expiry_date
            else:
                # 서버 연결 실패 시에만 로컬 DB로 백업
                self.logger.warning(f"서버 연결 실패, 로컬 DB로 백업 검증: {server_message}")
                
        except Exception as e:
            self.logger.error(f"서버 검증 중 예외: {e}")
        
        # 2. 로컬 DB 백업 검증 (서버 연결 실패 시에만)
        self.logger.info("로컬 DB 백업 검증 시작")
        local_valid, local_message, local_expiry = self.validate_serial_local(serial_number)
        
        if local_valid:
            self.logger.info("로컬 DB 백업 검증 성공")
            # AI마스터 방식: 로컬 검증 성공 시에도 사용횟수 증가
            self.update_device_info_and_usage(serial_number)
            return True, f"{local_message} (오프라인 모드)", local_expiry
        else:
            self.logger.warning(f"로컬 DB 검증도 실패: {local_message}")
            return False, local_message, local_expiry
    
    def _cleanup_same_device_serials(self, cursor, current_serial: str, current_device_info: dict):
        """같은 디바이스에서 같은 앱을 사용하는 다른 시리얼들을 정리"""
        try:
            current_hostname = current_device_info.get('hostname', '')
            current_app = current_device_info.get('app_name', '블로그자동화')
            
            if not current_hostname:
                return
            
            self.logger.info(f"같은 디바이스 시리얼 정리 시작 - 호스트: {current_hostname}, 앱: {current_app}")
            
            # 현재 설정 파일의 시리얼 확인 (보호 대상)
            config = self.load_config()
            protected_serial = config.get("serial_number", "")
            self.logger.info(f"보호 대상 시리얼: {protected_serial[:8]}... (설정 파일)")
            
            # 같은 디바이스에서 같은 앱을 사용하는 다른 시리얼들 찾기
            cursor.execute("""
                SELECT serial_number, device_info 
                FROM serials 
                WHERE serial_number != ? 
                AND serial_number != ?
                AND is_deleted = 0
                AND status = '사용중'
                AND device_info != '{}'
            """, (current_serial, protected_serial))
            
            other_serials = cursor.fetchall()
            cleaned_count = 0
            
            for serial, device_info_str in other_serials:
                try:
                    if device_info_str and len(device_info_str) > 10:
                        other_device_info = json.loads(device_info_str)
                        other_hostname = other_device_info.get('hostname', '')
                        other_app = other_device_info.get('app_name', '')
                        
                        # 같은 디바이스이고 같은 앱인 경우 정리
                        if (other_hostname == current_hostname and 
                            other_app == current_app):
                            
                            self.logger.info(f"같은 디바이스의 이전 시리얼 정리: {serial[:8]}...")
                            
                            cursor.execute("""
                                UPDATE serials 
                                SET device_info = '{}', 
                                    activation_count = 0,
                                    status = '사용가능'
                                WHERE serial_number = ?
                            """, (serial,))
                            
                            cleaned_count += 1
                            
                except json.JSONDecodeError:
                    continue
            
            if cleaned_count > 0:
                self.logger.info(f"같은 디바이스의 이전 시리얼 {cleaned_count}개 정리 완료")
            else:
                self.logger.info("정리할 같은 디바이스 시리얼 없음")
                
        except Exception as e:
            self.logger.error(f"같은 디바이스 시리얼 정리 중 오류: {e}")
    
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
            
            # 같은 디바이스의 다른 시리얼들 정리 (같은 앱에서 사용된 것들만)
            self._cleanup_same_device_serials(cursor, serial_number, device_info)
            
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
            self.logger.info(f"업데이트 시도: {serial_number}, 디바이스 정보 길이: {len(device_info_json)}")
            cursor.execute("""
                UPDATE serials 
                SET device_info = ?, 
                    activation_count = ?,
                    status = '사용중',
                    last_check_date = ?
                WHERE serial_number = ?
            """, (device_info_json, new_count, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), serial_number))
            
            # 업데이트된 행 수 확인
            updated_rows = cursor.rowcount
            self.logger.info(f"업데이트된 행 수: {updated_rows}")
            
            conn.commit()
            
            # 업데이트 후 확인 및 만료일 조회
            cursor.execute("SELECT device_info, activation_count, expiry_date FROM serials WHERE serial_number = ?", (serial_number,))
            result = cursor.fetchone()
            if result:
                self.logger.info(f"업데이트 후 확인 - 디바이스 정보 길이: {len(result[0])}, 사용횟수: {result[1]}")
                expiry_date = result[2]  # 만료일 저장
            else:
                self.logger.error(f"업데이트 후 시리얼을 찾을 수 없음: {serial_number}")
                expiry_date = None
            
            conn.close()
            
            self.logger.info(f"디바이스 정보 및 사용횟수 업데이트 완료: {serial_number} (사용횟수: {new_count})")
            
            # 서버에도 업데이트 시도
            try:
                
                update_data = {
                    "device_info": device_info,
                    "activation_count": new_count,
                    "status": "사용중"
                }
                
                # 만료일이 있으면 추가
                if expiry_date:
                    update_data["expiry_date"] = expiry_date
                
                self.logger.info(f"서버 업데이트 데이터: {update_data}")
                
                response = requests.patch(
                    f"{self.server_url}/api/serials/{serial_number}",
                    json=update_data,
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
        """시리얼 입력이 필요한지 확인 (캐시된 결과 사용으로 중복 호출 방지)"""
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
        
        # 중복 호출 방지: 캐시된 검증 결과만 확인
        # 실제 검증은 메인 앱에서 별도로 수행
        self.logger.info("시리얼 설정 확인됨 - 추가 검증은 메인 앱에서 수행")
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
        
        # 주의: 사용횟수는 check_serial에서 증가하므로 여기서는 제거
        # (중복 증가 방지)

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
