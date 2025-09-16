#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시리얼 검증 클라이언트 모듈
블로그 자동화 프로그램의 라이센스 검증 기능을 제공합니다.
"""

import os
import sys
import json
import requests
import platform
import socket
import hashlib
import logging
import sqlite3
from datetime import datetime, timedelta
import psutil

# 서버 URL 설정
SERVER_URL = "https://aimaster-serial.onrender.com"

class SerialClient:
    def __init__(self, app_name="BlogAutomation"):
        """
        시리얼 검증 클라이언트 초기화
        
        Args:
            app_name (str): 애플리케이션 이름
        """
        self.app_name = app_name
        self.serial_number = None
        self.is_valid = False
        self.expiry_date = None
        self.status = None
        self.device_info = None
        self.validation_interval = 1.0  # 서버 검증 간격(1.0일 = 24시간)
        self.last_valid_hash = None  # 마지막으로 유효성이 확인된 디바이스 해시
        
        # 로깅 설정
        self.setup_logging()
        
        # 기본 경로 설정
        self.app_dir = self.get_app_path()
        self.db_path = os.path.join(self.app_dir, 'serial_data.db')
        
        # DB 초기화
        self.init_database()
        
        # 저장된 시리얼 로드
        self.load_saved_serial()
        
        # 저장된 디바이스 정보 로드 시도
        if self.serial_number:
            self.load_device_info()
            
            # 디바이스 정보가 없는 경우 생성
            if not self.device_info:
                self.device_info = self.get_device_info()
                self.save_device_info()
        
        # 유효성 검사 수행
        if self.serial_number:
            # 마지막 검증 시간 확인 후 필요 시 재검증
            self.check_validation_time()
            
    def get_app_path(self):
        """애플리케이션 실행 경로 반환"""
        try:
            # 실행 파일로 패키징된 경우
            if getattr(sys, 'frozen', False):
                return os.path.dirname(sys.executable)
            # 스크립트로 실행된 경우
            else:
                return os.path.dirname(os.path.abspath(__file__))
        except:
            return os.getcwd()
    
    def setup_logging(self):
        """로깅 설정"""
        try:
            logging.basicConfig(
                filename='serial_client.log',
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
            logging.info("시리얼 클라이언트 로깅 시작")
        except Exception as e:
            print(f"로깅 설정 오류: {str(e)}")
    
    def init_database(self):
        """시리얼 정보 저장용 데이터베이스 초기화"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS serial_data (
                    id INTEGER PRIMARY KEY,
                    serial_number TEXT UNIQUE,
                    status TEXT,
                    expiry_date TEXT,
                    registered_date TEXT,
                    last_check_date TEXT,
                    device_hash TEXT,
                    app_name TEXT
                )
            ''')
            
            # 기존 테이블에 app_name 컬럼이 없으면 추가
            try:
                self.cursor.execute("PRAGMA table_info(serial_data)")
                columns = [col[1] for col in self.cursor.fetchall()]
                
                if 'app_name' not in columns:
                    self.cursor.execute("ALTER TABLE serial_data ADD COLUMN app_name TEXT")
                    logging.info("데이터베이스에 app_name 컬럼 추가 완료")
            except Exception as schema_error:
                logging.error(f"스키마 업데이트 오류: {str(schema_error)}")
                
            self.conn.commit()
            logging.info("데이터베이스 초기화 완료")
        except Exception as e:
            logging.error(f"데이터베이스 초기화 오류: {str(e)}")
            print(f"데이터베이스 초기화 오류: {str(e)}")
    
    def load_saved_serial(self):
        """저장된 시리얼 정보 로드"""
        try:
            self.cursor.execute("SELECT serial_number, status, expiry_date FROM serial_data ORDER BY id DESC LIMIT 1")
            result = self.cursor.fetchone()
            
            if result:
                self.serial_number = result[0]
                self.status = result[1]
                self.expiry_date = result[2]
                
                # 유효성 검사 - "사용가능", "만료 예정" 상태만 유효함
                if (self.status == "사용가능" or self.status == "만료 예정") and self.expiry_date:
                    try:
                        # 만료일 파싱
                        expiry = datetime.strptime(self.expiry_date, "%Y-%m-%d").date()
                        current_date = datetime.now().date()
                        
                        # 현재 날짜와 만료일 비교
                        logging.info(f"현재 날짜: {current_date}, 만료일: {expiry}")
                        
                        if expiry >= current_date:
                            self.is_valid = True
                            logging.info(f"유효한 시리얼 로드: {self.serial_number}, 남은 일수: {(expiry - current_date).days}일")
                        else:
                            self.is_valid = False
                            self.status = "만료됨"
                            logging.info(f"만료된 시리얼: {self.serial_number}, 만료일: {expiry}, 현재: {current_date}")
                    except Exception as date_error:
                        logging.error(f"날짜 비교 오류: {str(date_error)}")
                        self.is_valid = False
                        self.status = "날짜 오류"
                else:
                    # "사용중" 상태인 경우 명시적으로 거부
                    if self.status == "사용중":
                        self.status = "다른 디바이스에서 사용중"
                    
                    self.is_valid = False
                    logging.info(f"유효하지 않은 시리얼 상태: {self.status}")
            else:
                logging.info("저장된 시리얼 정보 없음")
        except Exception as e:
            logging.error(f"시리얼 로드 오류: {str(e)}")
            self.is_valid = False
    
    def get_device_info(self):
        """디바이스 정보 수집"""
        try:
            # 기본 시스템 정보
            system = platform.system()
            processor = platform.processor()
            
            # 호스트명 및 IP 주소 (오류에 강건하게 수정)
            try:
                hostname = socket.gethostname()
                try:
                    ip_address = socket.gethostbyname(hostname)
                except:
                    ip_address = "127.0.0.1"  # 기본 로컬호스트 IP로 설정
            except:
                hostname = "unknown-host"
                ip_address = "127.0.0.1"
            
            # 메모리 정보
            try:
                memory = psutil.virtual_memory()
                total_memory = f"{memory.total / (1024**3):.2f}GB"
            except:
                total_memory = "Unknown"
            
            # 앱 이름이 비어있거나 None인 경우 기본값 설정
            current_app_name = self.app_name
            if not current_app_name:
                current_app_name = "BlogAutomation"
                logging.warning(f"앱 이름이 비어있어 기본값으로 설정: {current_app_name}")
                self.app_name = current_app_name
            
            # 디바이스 정보 생성
            device_info = {
                "hostname": hostname,
                "ip_address": ip_address,
                "system_manufacturer": "Apple" if system == "Darwin" else system,
                "system_model": platform.machine(),
                "os_name": system,
                "os_version": platform.version(),
                "processor": processor,
                "total_memory": total_memory,
                "registration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "app_name": current_app_name  # 확인된 앱 이름 사용
            }
            
            logging.info(f"앱 이름 설정: {current_app_name}")
            
            # 디바이스 해시 생성
            device_hash = self.create_device_hash(device_info)
            device_info["device_hash"] = device_hash
            
            logging.info(f"디바이스 정보 수집 성공: {hostname}, 앱: {current_app_name}, 해시: {device_hash[:20]}")
            return device_info
        except Exception as e:
            logging.error(f"디바이스 정보 수집 오류: {str(e)}")
            # 기본 디바이스 정보 반환
            default_info = {
                "hostname": "unknown",
                "ip_address": "0.0.0.0",
                "system_manufacturer": "Unknown",
                "system_model": "Unknown",
                "os_name": "Unknown",
                "os_version": "Unknown",
                "processor": "Unknown",
                "total_memory": "Unknown",
                "registration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "app_name": self.app_name,
                "device_hash": "unknown",
                "error_info": f"정보 수집 실패: {str(e)[:50]}"
            }
            return default_info
    
    def create_device_hash(self, device_info):
        """디바이스 정보에서 고유 해시 생성"""
        try:
            # 앱 이름을 별도로 추출하고 확인
            app_name = device_info.get('app_name', self.app_name)
            if not app_name:
                app_name = self.app_name
                logging.warning("디바이스 정보에 앱 이름이 없어 기본값 사용: " + self.app_name)
            
            # app_name이 None이거나 빈 문자열인 경우 기본값 사용
            if not app_name:
                app_name = "BlogAutomation"  # 기본값 설정
                logging.warning(f"앱 이름이 비어있어 기본값 사용: {app_name}")
            
            # 앱 이름에 특수 프리픽스 추가하여 앱 간 구분 더 명확히 함
            app_name_hash = f"APP_{app_name}"
            
            # 해시에 사용할 주요 정보 추출 - MAC 주소 등 더 많은 정보 포함 시도
            hash_data = (
                f"{device_info['hostname']}|"
                f"{device_info['ip_address']}|"
                f"{device_info['system_model']}|"
                f"{device_info['processor']}|"
                f"{device_info['total_memory']}|"
                f"{app_name_hash}"  # 강화된 앱 이름 형식 사용
            )
            
            # 디버그 로깅 추가
            logging.info(f"해시 생성에 사용된 데이터: {hash_data}")
            logging.info(f"현재 앱 이름: {app_name}")
            
            # SHA-256 해시 생성
            hash_value = hashlib.sha256(hash_data.encode()).hexdigest()
            logging.info(f"생성된 디바이스 해시: {hash_value[:20]}...")
            return hash_value
        except Exception as e:
            logging.error(f"디바이스 해시 생성 오류: {str(e)}")
            return "unknown"
    
    def validate_serial(self, serial_number, update_device=True):
        """
        시리얼 번호 유효성 검증
        
        Args:
            serial_number (str): 검증할 시리얼 번호
            update_device (bool): 디바이스 정보 업데이트 여부
            
        Returns:
            bool: 유효성 여부
        """
        try:
            self.serial_number = serial_number
            
            # 디바이스 정보 수집
            if update_device:
                try:
                    self.device_info = self.get_device_info()
                    if "error_info" in self.device_info:
                        logging.warning(f"디바이스 정보 수집에 문제 발생: {self.device_info.get('error_info')}")
                except Exception as e:
                    logging.error(f"디바이스 정보 수집 중 예외 발생: {str(e)}")
                    self.device_info = {
                        "hostname": "error-device",
                        "app_name": self.app_name,
                        "error_info": f"수집 예외: {str(e)[:50]}"
                    }
            else:
                # 기존 저장된 디바이스 정보 로드
                device_info_loaded = self.load_device_info()
                if not device_info_loaded or not self.device_info:
                    self.device_info = self.get_device_info()
            
            # 현재 디바이스 해시
            current_hash = self.device_info.get('device_hash', 'unknown') if self.device_info else 'unknown'
            
            # 마지막 유효 해시와 비교
            if self.last_valid_hash and current_hash != 'unknown' and self.last_valid_hash == current_hash:
                logging.info(f"현재 디바이스 해시가 마지막 유효 해시와 일치합니다: {current_hash[:10]}...")
            
            # 로그에 현재 디바이스 해시 기록
            logging.info(f"현재 디바이스 해시: {current_hash[:10]}...")
            
            # 저장된 디바이스 해시 확인
            stored_hash = self.get_stored_device_hash(serial_number)
            if stored_hash:
                logging.info(f"저장된 디바이스 해시: {stored_hash[:10]}...")
                
                # 현재 해시와 저장된 해시 비교
                if current_hash != 'unknown' and stored_hash == current_hash:
                    logging.info("현재 디바이스는 이전에 인증된 디바이스와 동일합니다.")
                    self.last_valid_hash = current_hash
            
            # 서버 검증 요청 - 정상 작동하는 엔드포인트 사용
            try:
                # 먼저 모든 시리얼 목록을 가져옴
                logging.info(f"서버 URL: {SERVER_URL}/api/serials로 요청 시작")
                serials_response = requests.get(
                    f"{SERVER_URL}/api/serials",
                    timeout=30
                )
                
                logging.info(f"시리얼 목록 응답 코드: {serials_response.status_code}")
                
                if serials_response.status_code == 200:
                    # 시리얼 목록에서 입력한 시리얼 번호 검색
                    serials_list = serials_response.json()
                    matched_serial = None
                    
                    logging.info(f"서버에서 응답한 시리얼 수: {len(serials_list)}")
                    
                    for serial_data in serials_list:
                        if serial_data.get("serial_number") == serial_number:
                            matched_serial = serial_data
                            break
                    
                    if matched_serial:
                        # 시리얼 정보 추출 - 사용가능, 만료 예정 상태만 유효함
                        status = matched_serial.get("status", "알 수 없음")
                        self.is_valid = (status == "사용가능" or status == "만료 예정") and not matched_serial.get("is_blacklisted", False)
                        self.status = status
                        
                        # 사용중 상태인 경우 명시적으로 거부
                        if status == "사용중":
                            self.is_valid = False
                            self.status = "다른 디바이스에서 사용중"
                            logging.warning(f"이미 다른 디바이스에서 사용 중인 시리얼입니다: {serial_number}")
                            
                        self.expiry_date = matched_serial.get("expiry_date")
                        
                        # 시리얼이 만료되었는지 확인
                        if self.expiry_date:
                            expiry = datetime.strptime(self.expiry_date, "%Y-%m-%d").date()
                            if expiry < datetime.now().date():
                                self.is_valid = False
                                self.status = "만료됨"
                        
                        # 디바이스 정보 업데이트 - 대체 방법 구현
                        if update_device and self.is_valid and self.device_info:
                            try:
                                # 시리얼 정보 + 디바이스 정보를 담은 데이터 생성
                                device_update_data = {
                                    "serial_number": serial_number,
                                    "app_name": self.app_name,
                                    "device_info": self.device_info
                                }
                                
                                # 여러 가능한 API 엔드포인트 설정
                                api_endpoints = [
                                    "/api/validate",   # 가장 가능성 높은 엔드포인트
                                    "/api/check",      # 다음 시도
                                    "/api/register",   # 또 다른 시도
                                    "/api/device/update"  # 마지막 시도
                                ]
                                
                                device_updated = False
                                
                                # 각 엔드포인트 시도
                                for endpoint in api_endpoints:
                                    try:
                                        full_url = f"{SERVER_URL}{endpoint}"
                                        logging.info(f"디바이스 정보 업데이트 시도 ({endpoint} 엔드포인트)")
                                        
                                        response = requests.post(
                                            full_url,
                                            json=device_update_data,
                                            timeout=10
                                        )
                                        logging.info(f"{endpoint} 응답 코드: {response.status_code}")
                                        
                                        if response.status_code >= 200 and response.status_code < 300:
                                            logging.info(f"디바이스 정보 업데이트 성공 ({endpoint})")
                                            
                                            # 응답 내용 저장
                                            try:
                                                data = response.json()
                                                logging.info(f"응답 데이터: {data}")
                                                
                                                # 타입 체크 및 안전한 접근
                                                if not isinstance(data, dict):
                                                    logging.warning(f"응답 데이터가 예상 형식이 아닙니다: {type(data)}")
                                                    data = {"status": "응답 형식 오류", "message": "서버 응답 형식이 유효하지 않습니다."}
                                                
                                                # 서버에서 반환된 상태 값 우선 적용
                                                if 'status' in data:
                                                    self.status = data['status']
                                                    logging.info(f"서버에서 받은 상태 업데이트: {self.status}")
                                                    
                                                    # 블랙리스트나 만료됨 상태는 무효처리
                                                    if self.status == "블랙리스트" or self.status == "만료됨":
                                                        self.is_valid = False
                                                        logging.warning(f"서버에서 무효 상태 반환: {self.status}")
                                                    # 사용중 상태인 경우 처리
                                                    elif self.status == "사용중":
                                                        # 디바이스 정보가 있고 디바이스 해시가 일치하는지 확인
                                                        registered_hash = None
                                                        if 'device_info' in data and 'device_hash' in data['device_info']:
                                                            registered_hash = data['device_info']['device_hash']
                                                        
                                                        current_hash = self.device_info.get('device_hash', 'unknown')
                                                        
                                                        # 해시 정보 로깅
                                                        logging.info(f"현재 디바이스 해시: {current_hash}")
                                                        logging.info(f"서버에 등록된 디바이스 해시: {registered_hash}")
                                                        
                                                        # 서버에서 '사용중'으로 반환했지만 성공 메시지가 있으면 임시로 허용
                                                        # 이는 서버가 디바이스 해시 정보를 제공하지 않는 경우를 위한 임시 방편
                                                        if 'message' in data and isinstance(data['message'], str) and '성공적으로 검증' in data['message']:
                                                            registered_app = data.get('app_name', '')
                                                            if registered_app and registered_app != self.app_name:
                                                                self.is_valid = False
                                                                self.status = f"다른 앱({registered_app})에서 사용중"
                                                                logging.warning(f"동일 디바이스지만 다른 앱({registered_app})에서 사용중인 시리얼입니다.")
                                                                
                                                                # 명확한 로깅 추가
                                                                print(f"시리얼 인증 오류: {serial_number}는 이미 {registered_app}에서 사용 중입니다.")
                                                                print(f"현재 앱: {self.app_name}, 등록된 앱: {registered_app}")
                                                            else:
                                                                self.is_valid = True
                                                                self.status = "사용가능"  # 실제로는 서버에서 성공 응답이 왔으므로 사용가능으로 변경
                                                                logging.info(f"서버에서 성공 메시지를 받았습니다. 정상 처리합니다: {data['message']}")
                                                        # 동일한 디바이스인 경우 유효 처리
                                                        elif registered_hash and registered_hash == current_hash:
                                                            registered_app = None
                                                            if 'device_info' in data:
                                                                registered_app = data['device_info'].get('app_name', '')
                                                            
                                                            # 해시는 같지만 앱이 다른 경우 - 더 명확한 처리
                                                            if registered_app and registered_app != self.app_name:
                                                                self.is_valid = False
                                                                self.status = f"다른 앱({registered_app})에서 사용중"
                                                                logging.warning(f"동일 디바이스지만 다른 앱({registered_app})에서 사용중인 시리얼입니다.")
                                                                
                                                                # 명확한 로깅 추가
                                                                print(f"시리얼 인증 오류: {serial_number}는 이미 {registered_app}에서 사용 중입니다.")
                                                                print(f"현재 앱: {self.app_name}, 등록된 앱: {registered_app}")
                                                            else:
                                                                self.is_valid = True
                                                                self.status = "사용가능"  # 실제로는 같은 장치에서 사용 중이므로 사용가능으로 변경
                                                                logging.info(f"동일한 디바이스에서 사용 중인 시리얼입니다. 정상 처리합니다.")
                                                    else:
                                                        # 서버에서 해시 정보를 제공하지 않는 경우 로컬 해시 확인
                                                        if not registered_hash:
                                                            # 이전에 저장된 디바이스 정보 로드
                                                            local_device_hash = self.get_stored_device_hash(serial_number)
                                                            local_app_name = self.get_stored_app_name(serial_number)
                                                            
                                                            # 해시와 앱 이름 모두 체크 - 로직 개선
                                                            if local_device_hash and local_device_hash == current_hash:
                                                                # 앱 이름이 없거나 일치하는 경우
                                                                if not local_app_name or local_app_name == self.app_name:
                                                                    self.is_valid = True
                                                                    self.status = "사용가능"
                                                                    logging.info(f"로컬에 저장된 해시와 앱 정보가 일치합니다. 정상 처리합니다.")
                                                                # 해시는 같지만 앱이 다른 경우 - 명확하게 거부
                                                                else:
                                                                    self.is_valid = False
                                                                    self.status = f"다른 앱({local_app_name})에서 사용중"
                                                                    logging.warning(f"로컬 저장 해시는 일치하지만 다른 앱({local_app_name})에서 사용중입니다.")
                                                                    
                                                                    # 명확한 로깅 추가
                                                                    print(f"시리얼 인증 오류: {serial_number}는 이미 {local_app_name}에서 사용 중입니다.")
                                                                    print(f"현재 앱: {self.app_name}, 저장된 앱: {local_app_name}")
                                                            else:
                                                                self.is_valid = False
                                                                self.status = "다른 디바이스에서 사용중"
                                                                logging.warning(f"이미 다른 디바이스에서 사용 중인 시리얼입니다: {serial_number}")
                                                
                                                # 성공/실패 여부 확인
                                                if 'success' in data and not data['success']:
                                                    self.is_valid = False
                                                    if 'message' in data:
                                                        logging.warning(f"서버 응답 실패: {data['message']}")
                                                
                                                # 서버에서 '사용중' 응답 처리 추가 보강
                                                if self.status == "사용중" or self.status == "다른 디바이스에서 사용중":
                                                    # 로컬에 저장된 디바이스 정보와 현재 디바이스를 비교하여 재검증
                                                    current_device_hash = self.device_info.get('device_hash', 'unknown')
                                                    stored_device_hash = self.get_stored_device_hash(serial_number)
                                                    
                                                    if stored_device_hash and stored_device_hash == current_device_hash:
                                                        # 저장된 해시와 현재 해시가 일치하면 동일한 디바이스로 간주
                                                        self.is_valid = True
                                                        self.status = "사용가능"
                                                        logging.info("로컬 저장 해시와 현재 해시가 일치하여 동일 디바이스로 판단. 정상 처리합니다.")
                                                
                                                # 시리얼이 다른 디바이스에서 사용 중인 경우
                                                if response.status_code == 403 and 'message' in data and '다른 디바이스' in data['message']:
                                                    self.is_valid = False
                                                    self.status = "다른 디바이스에서 사용중"
                                                    logging.warning(f"다른 디바이스에서 사용 중: {data['message']}")
                                                
                                                # 사용가능이나 만료 예정 상태는 유효 처리
                                                elif self.status == "사용가능" or self.status == "만료 예정":
                                                    self.is_valid = True
                                                    logging.info(f"서버에서 유효 상태 반환: {self.status}")
                                                
                                                # 만료일 정보가 있으면 업데이트
                                                if 'expiry_date' in data:
                                                    self.expiry_date = data['expiry_date']
                                                    logging.info(f"서버에서 받은 만료일: {self.expiry_date}")
                                                
                                                # 디바이스 정보가 응답에 포함되어 있으면 업데이트
                                                if 'device_info' in data:
                                                    self.device_info.update(data['device_info'])
                                                    logging.info("디바이스 정보 업데이트됨")
                                                    
                                                # 디바이스 정보 유효성을 다시 확인
                                                if self.status != "사용가능" and self.status != "만료 예정":
                                                    self.is_valid = False
                                                    logging.warning(f"업데이트 후 유효하지 않은 상태: {self.status}")
                                                else:
                                                    logging.info(f"유효한 상태로 설정됨: {self.status}, 유효성: {self.is_valid}")
                                            except Exception as json_error:
                                                logging.warning(f"응답 데이터 처리 중 오류 발생: {str(json_error)}")
                                                
                                            # 성공한 경우 다음 엔드포인트 시도하지 않음
                                            device_updated = True
                                            break
                                        else:
                                            try:
                                                error_text = response.text
                                                error_data = response.json() if response.text else {}
                                                
                                                # 오류 응답에서 상태 정보 추출
                                                if 'status' in error_data:
                                                    self.status = error_data['status']
                                                    logging.warning(f"오류 응답의 상태: {self.status}")
                                                    
                                                    # 블랙리스트 상태 처리
                                                    if self.status == "블랙리스트":
                                                        self.is_valid = False
                                                        logging.warning("블랙리스트 상태가 감지되었습니다.")
                                                
                                                # 클라이언트 상태 업데이트
                                                if response.status_code == 403:
                                                    self.is_valid = False
                                                    if 'message' in error_data:
                                                        logging.warning(f"접근 거부됨: {error_data['message']}")
                                                
                                                logging.warning(f"{endpoint} 오류 응답: {error_text}")
                                            except Exception as error_parse_error:
                                                logging.error(f"오류 응답 파싱 실패: {str(error_parse_error)}")
                                    except Exception as e:
                                        logging.error(f"{endpoint} 요청 실패: {str(e)}")
                                        
                                if not device_updated:
                                    logging.warning("모든 디바이스 정보 업데이트 시도 실패")
                                
                            except Exception as e:
                                logging.error(f"디바이스 정보 등록 처리 오류: {str(e)}")
                        
                        # 디바이스 정보를 로컬에 저장 - 유효한 시리얼인 경우에만 저장
                        if self.is_valid:
                            self.save_device_info()
                        else:
                            logging.warning(f"유효하지 않은 시리얼이므로 디바이스 정보를 저장하지 않습니다: {serial_number}, 상태: {self.status}")
                        
                        # 시리얼 정보 DB에 저장
                        self.save_serial_info()
                        
                        logging.info(f"시리얼 검증 결과: {self.is_valid}, 상태: {self.status}")
                        return self.is_valid
                    else:
                        # 일치하는 시리얼 없음
                        self.is_valid = False
                        self.status = "등록되지 않음"
                        logging.warning(f"일치하는 시리얼 없음: {serial_number}")
                        return False
                else:
                    # 시리얼 목록 가져오기 실패 시 로컬 검증
                    logging.warning(f"시리얼 목록 가져오기 실패: {serials_response.status_code}")
                    self.status = f"서버 오류 ({serials_response.status_code})"
                    self.validate_local()
                    return self.is_valid
            except requests.exceptions.Timeout:
                # 시간 초과 시 로컬 검증
                logging.error("서버 연결 시간 초과")
                self.status = "서버 연결 시간 초과"
                self.validate_local()
                return self.is_valid
            except requests.exceptions.ConnectionError:
                # 연결 오류 시 로컬 검증
                logging.error("서버 연결 실패")
                self.status = "서버 연결 실패"
                self.validate_local()
                return self.is_valid
            except Exception as e:
                # 서버 연결 실패 시 로컬 검증
                logging.error(f"서버 연결 오류: {str(e)}")
                self.status = f"응답처리 오류: {str(e)[:50]}"
                self.validate_local()
                return self.is_valid
                
        except Exception as e:
            logging.error(f"시리얼 검증 오류: {str(e)}")
            # 연결 오류 시 로컬 검증
            self.status = f"검증 오류: {str(e)[:50]}"
            self.validate_local()
            return self.is_valid
    
    def validate_local(self):
        """로컬 데이터베이스 기반 유효성 검증"""
        try:
            # 시리얼 번호 확인
            self.cursor.execute(
                "SELECT status, expiry_date, app_name, device_hash FROM serial_data WHERE serial_number = ?", 
                (self.serial_number,)
            )
            result = self.cursor.fetchone()
            
            # 결과 처리
            if result:
                self.status = result[0]
                self.expiry_date = result[1]
                local_app_name = result[2]
                local_device_hash = result[3]
                
                # 현재 디바이스 정보 및 해시 가져오기
                if not self.device_info:
                    self.device_info = self.get_device_info()
                current_hash = self.device_info.get('device_hash', 'unknown') if self.device_info else 'unknown'
                
                # 해시가 같지만 앱이 다른 경우 사용 중으로 표시 - 명확하게 인증 거부
                if (local_device_hash and current_hash != 'unknown' and 
                    local_device_hash == current_hash and 
                    local_app_name and local_app_name != self.app_name):
                    
                    self.is_valid = False
                    self.status = f"다른 앱({local_app_name})에서 사용중"
                    logging.warning(f"로컬 저장 해시는 일치하지만 다른 앱({local_app_name})에서 사용중입니다.")
                    
                    # 명확한 로깅 추가
                    print(f"시리얼 인증 오류: {self.serial_number}는 이미 {local_app_name}에서 사용 중입니다.")
                    return
                
                # "사용가능" 또는 "만료 예정" 상태만 유효함
                if (self.status == "사용가능" or self.status == "만료 예정") and self.expiry_date:
                    try:
                        # 만료일 파싱
                        expiry = datetime.strptime(self.expiry_date, "%Y-%m-%d").date()
                        current_date = datetime.now().date()
                        
                        # 현재 날짜와 만료일 비교 (로그 추가)
                        logging.info(f"로컬 검증 - 현재 날짜: {current_date}, 만료일: {expiry}")
                        
                        if expiry >= current_date:
                            self.is_valid = True
                            logging.info(f"로컬 유효성 확인 성공: {self.serial_number}, 남은 일수: {(expiry - current_date).days}일")
                        else:
                            self.is_valid = False
                            self.status = "만료됨"
                            logging.info(f"로컬 만료된 시리얼: {self.serial_number}, 만료일: {expiry}, 현재: {current_date}")
                    except Exception as date_error:
                        logging.error(f"로컬 날짜 비교 오류: {str(date_error)}")
                        self.is_valid = False
                        self.status = "날짜 오류"
                else:
                    # 사용중 상태는 명시적으로 거부
                    if self.status == "사용중":
                        self.status = "다른 디바이스에서 사용중"
                        logging.info(f"로컬에서 다른 디바이스 사용중 감지: {self.serial_number}")
                    
                    self.is_valid = False
                    logging.info(f"로컬 유효하지 않은 시리얼 상태: {self.status}")
            else:
                # 없는 시리얼
                self.is_valid = False
                self.status = "등록되지 않음"
                logging.info(f"로컬에 등록되지 않은 시리얼: {self.serial_number}")
            
            logging.info(f"로컬 검증 결과: {self.is_valid}, 상태: {self.status}")
            
            # 오프라인 검증 결과 저장
            self.save_serial_info(is_offline=True)
            
        except Exception as e:
            logging.error(f"로컬 검증 오류: {str(e)}")
            self.is_valid = False
            self.status = "오류"
    
    def save_serial_info(self, is_offline=False):
        """시리얼 정보 DB에 저장"""
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            device_hash = self.device_info.get("device_hash", "") if self.device_info else ""
            app_name = self.app_name  # 앱 이름 저장
            
            # 기존 데이터 확인
            self.cursor.execute(
                "SELECT id FROM serial_data WHERE serial_number = ?", 
                (self.serial_number,)
            )
            exists = self.cursor.fetchone()
            
            if exists:
                # 기존 데이터 업데이트
                self.cursor.execute("""
                    UPDATE serial_data SET 
                    status = ?, 
                    expiry_date = ?,
                    last_check_date = ?,
                    app_name = ?
                    WHERE serial_number = ?
                """, (self.status, self.expiry_date, now, app_name, self.serial_number))
            else:
                # 새 데이터 삽입
                self.cursor.execute("""
                    INSERT INTO serial_data 
                    (serial_number, status, expiry_date, registered_date, last_check_date, device_hash, app_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (self.serial_number, self.status, self.expiry_date, now, now, device_hash, app_name))
            
            self.conn.commit()
            logging.info(f"시리얼 정보 저장 완료: {self.serial_number} (오프라인: {is_offline})")
        except Exception as e:
            logging.error(f"시리얼 정보 저장 오류: {str(e)}")
    
    def get_remaining_days(self):
        """남은 사용 일수 계산"""
        if not self.expiry_date:
            return 0
            
        try:
            # 만료일 파싱
            expiry = datetime.strptime(self.expiry_date, "%Y-%m-%d").date()
            current_date = datetime.now().date()
            
            # 현재 날짜와 만료일 사이의 차이 계산
            remaining = (expiry - current_date).days
            
            # 로그에 계산 과정 기록 (디버깅용)
            logging.info(f"남은 일수 계산 - 현재 날짜: {current_date}, 만료일: {expiry}, 남은 일수: {remaining}")
            
            # 음수가 되지 않도록 처리
            return max(0, remaining)
        except Exception as e:
            logging.error(f"남은 일수 계산 오류: {str(e)}")
            return 0
    
    def clear_serial(self):
        """시리얼 정보 초기화 (로그아웃)"""
        try:
            # 로그아웃 시간 기록
            logout_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logging.info(f"시리얼 로그아웃 시작: {logout_time}")
            
            # 시리얼 정보 저장 (로그아웃 시 디버깅 용도)
            serial_backup = {
                "serial_number": self.serial_number,
                "status": self.status,
                "expiry_date": self.expiry_date,
                "logout_time": logout_time
            }
            
            # DB 완전 초기화
            try:
                self.cursor.execute("DELETE FROM serial_data")
                self.conn.commit()
                logging.info("DB에서 시리얼 정보 삭제 완료")
                
                # 추가: 더 많은 테이블이 있는지 확인하고 모두 초기화
                self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = self.cursor.fetchall()
                for table in tables:
                    table_name = table[0]
                    if table_name != 'sqlite_sequence':  # 시스템 테이블 제외
                        try:
                            self.cursor.execute(f"DELETE FROM {table_name}")
                        except Exception as e:
                            logging.error(f"테이블 {table_name} 초기화 오류: {str(e)}")
                
                self.conn.commit()
                logging.info("모든 테이블 초기화 완료")
                
            except Exception as db_error:
                logging.error(f"DB 정리 중 오류: {str(db_error)}")
            
            # 서버에 로그아웃 알림 시도
            try:
                if self.serial_number:
                    logout_data = {
                        "serial_number": self.serial_number,
                        "action": "logout",
                        "device_info": self.device_info
                    }
                    
                    # 가능한 로그아웃 엔드포인트 시도
                    for endpoint in ["/api/logout", "/api/validate", "/api/check"]:
                        try:
                            logging.info(f"서버에 로그아웃 알림 시도 (엔드포인트: {endpoint})")
                            response = requests.post(
                                f"{SERVER_URL}{endpoint}",
                                json=logout_data,
                                timeout=5  # 짧은 타임아웃 설정
                            )
                            if response.status_code >= 200 and response.status_code < 300:
                                logging.info(f"서버 로그아웃 성공: {response.status_code}")
                                break
                        except Exception as req_error:
                            logging.warning(f"서버 로그아웃 요청 실패: {str(req_error)}")
            except Exception as server_error:
                logging.error(f"서버 로그아웃 처리 오류: {str(server_error)}")
            
            # 디바이스 정보 파일들 삭제 - 모든 가능한 위치 검색
            paths_to_check = [
                # 현재 디렉토리의 config
                os.path.join(self.app_dir, 'config', 'device_info.json'),
                # 상위 디렉토리의 config
                os.path.join(os.path.dirname(os.path.dirname(self.app_dir)), 'config', 'device_info.json'),
                # 앱 루트 디렉토리의 config
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config', 'device_info.json')
            ]
            
            # 추가: 가능한 더 많은 경로 검색
            try:
                # 홈 디렉토리의 config
                home_dir = os.path.expanduser("~")
                paths_to_check.append(os.path.join(home_dir, 'config', 'device_info.json'))
                paths_to_check.append(os.path.join(home_dir, '.config', 'device_info.json'))
                
                # 현재 작업 디렉토리
                curr_dir = os.getcwd()
                paths_to_check.append(os.path.join(curr_dir, 'config', 'device_info.json'))
                
                # 디렉토리 검색 로직 추가
                for base_path in [self.app_dir, os.path.dirname(self.app_dir), os.getcwd()]:
                    for root, dirs, files in os.walk(base_path):
                        if 'config' in dirs:
                            paths_to_check.append(os.path.join(root, 'config', 'device_info.json'))
            except Exception as search_error:
                logging.error(f"추가 경로 검색 오류: {str(search_error)}")
            
            for path in paths_to_check:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                        logging.info(f"디바이스 정보 파일 삭제 완료: {path}")
                    except Exception as file_error:
                        logging.error(f"파일 삭제 오류 ({path}): {str(file_error)}")
            
            # 기타 시리얼 관련 임시 파일 삭제
            temp_files = [
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config', 'last_serial.json')
            ]
            
            # 추가: 모든 가능한 경로에서 시리얼 관련 파일 검색
            for base_path in [self.app_dir, os.path.dirname(self.app_dir), os.getcwd()]:
                temp_files.append(os.path.join(base_path, 'serial_data.db'))
                temp_files.append(os.path.join(base_path, 'config', 'last_serial.json'))
            
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        logging.info(f"임시 파일 삭제 완료: {temp_file}")
                    except Exception as tmp_error:
                        logging.error(f"임시 파일 삭제 오류 ({temp_file}): {str(tmp_error)}")
            
            # 로그아웃 상태 파일 생성 - 앱이 시작할 때 확인할 파일
            try:
                # 여러 위치에 로그아웃 상태 파일 생성
                logout_paths = [
                    os.path.join(self.app_dir, 'config'),
                    os.path.join(os.path.dirname(os.path.dirname(self.app_dir)), 'config'),
                    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config')
                ]
                
                for logout_dir in logout_paths:
                    if not os.path.exists(logout_dir):
                        os.makedirs(logout_dir, exist_ok=True)
                    
                    logout_file = os.path.join(logout_dir, 'logout_status.txt')
                    with open(logout_file, 'w', encoding='utf-8') as f:
                        f.write(f"Serial {self.serial_number} logged out at {logout_time}")
                    
                    logging.info(f"로그아웃 상태 파일 생성 완료: {logout_file}")
            except Exception as logout_error:
                logging.error(f"로그아웃 상태 파일 생성 오류: {str(logout_error)}")
            
            # 인메모리 데이터 초기화
            self.serial_number = None
            self.is_valid = False
            self.status = None
            self.expiry_date = None
            self.device_info = None
            self.last_valid_hash = None
            
            logging.info(f"시리얼 로그아웃 완료: {logout_time}")
            return True
        except Exception as e:
            logging.error(f"시리얼 로그아웃 중 오류 발생: {str(e)}")
            # 오류가 있더라도 메모리상의 데이터는 초기화
            self.serial_number = None
            self.is_valid = False
            self.status = None
            self.expiry_date = None
            self.device_info = None
            self.last_valid_hash = None
            return False
    
    def close(self):
        """리소스 정리"""
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
                logging.info("데이터베이스 연결 종료")
        except Exception as e:
            logging.error(f"리소스 정리 오류: {str(e)}")
    
    def check_validation_time(self):
        """마지막 검증 시간을 확인하고 필요시 서버 재검증"""
        try:
            # 마지막 검증 시간 확인
            self.cursor.execute(
                "SELECT last_check_date FROM serial_data WHERE serial_number = ?", 
                (self.serial_number,)
            )
            result = self.cursor.fetchone()
            
            if result:
                last_check = result[0]
                
                # 마지막 검증 시간이 설정된 간격보다 오래된 경우
                if last_check:
                    last_datetime = datetime.strptime(last_check, "%Y-%m-%d %H:%M:%S")
                    hours_since_check = (datetime.now() - last_datetime).total_seconds() / 3600
                    
                    if hours_since_check >= 1:  # 1시간 간격으로 검증 (24시간에서 변경)
                        logging.info(f"검증 간격이 지나 서버 재검증 수행 ({hours_since_check:.1f}시간 경과)")
                        self.validate_serial(self.serial_number, update_device=False)
                    else:
                        logging.info(f"최근에 검증됨 (경과: {hours_since_check:.1f}시간, 간격: 1시간)")
                else:
                    # 마지막 검증 시간이 없는 경우
                    self.validate_serial(self.serial_number, update_device=False)
        except Exception as e:
            logging.error(f"검증 시간 확인 중 오류: {e}")
            # 오류 발생 시 안전을 위해 로컬 검증만 수행
            self.validate_local() 
    
    def save_device_info(self):
        """디바이스 정보를 별도 저장"""
        try:
            if not self.device_info or not self.is_valid:
                logging.info("디바이스 정보가 없거나 유효하지 않은 시리얼이므로 디바이스 정보를 저장하지 않습니다.")
                return
                
            # 디바이스 정보를 로컬 파일에 저장
            config_dir = os.path.join(self.app_dir, 'config')
            os.makedirs(config_dir, exist_ok=True)
            
            device_file = os.path.join(config_dir, 'device_info.json')
            
            # 시리얼 번호와 함께 저장
            save_data = {
                "serial_number": self.serial_number,
                "device_info": self.device_info,
                "is_valid": self.is_valid,
                "status": self.status,
                "app_name": self.app_name,  # 앱 이름도 별도로 저장
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(device_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
                
            logging.info(f"디바이스 정보 저장됨: {device_file}")
            
            # 데이터베이스에도 디바이스 해시 업데이트
            try:
                device_hash = self.device_info.get('device_hash', '')
                if device_hash:
                    self.cursor.execute(
                        "UPDATE serial_data SET device_hash = ?, app_name = ? WHERE serial_number = ?",
                        (device_hash, self.app_name, self.serial_number)
                    )
                    self.conn.commit()
                    logging.info(f"데이터베이스에 디바이스 해시와 앱 이름 업데이트됨: {device_hash[:10]}..., 앱: {self.app_name}")
            except Exception as db_error:
                logging.error(f"데이터베이스 디바이스 해시 업데이트 오류: {str(db_error)}")
            
            # 상위 디렉토리에도 디바이스 정보 저장 (블로그자동화 앱에서 사용)
            try:
                # 상위 디렉토리 구조 확인 (../config)
                parent_config = os.path.join(os.path.dirname(os.path.dirname(self.app_dir)), 'config')
                os.makedirs(parent_config, exist_ok=True)
                parent_device_file = os.path.join(parent_config, 'device_info.json')
                
                with open(parent_device_file, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                    
                logging.info(f"상위 디렉토리에 디바이스 정보 저장됨: {parent_device_file}")
            except Exception as e:
                logging.warning(f"상위 디렉토리에 디바이스 정보 저장 실패: {str(e)}")
                
        except Exception as e:
            logging.error(f"디바이스 정보 저장 중 오류: {str(e)}")
            
    def load_device_info(self):
        """저장된 디바이스 정보 로드"""
        try:
            device_file = os.path.join(self.app_dir, 'config', 'device_info.json')
            
            if os.path.exists(device_file):
                with open(device_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if data.get('serial_number') == self.serial_number:
                    self.device_info = data.get('device_info', {})
                    # 추가로 디바이스 정보가 유효한지 확인
                    if data.get('is_valid') == False:
                        logging.warning(f"저장된 디바이스 정보가 유효하지 않은 상태입니다: {data.get('status')}")
                        return False
                    logging.info(f"디바이스 정보 로드됨: {device_file}")
                    return True
                else:
                    logging.warning(f"저장된 시리얼과 일치하지 않음: {data.get('serial_number')} != {self.serial_number}")
                    
            return False
        except Exception as e:
            logging.error(f"디바이스 정보 로드 중 오류: {str(e)}")
            return False
            
    def is_valid_with_server_check(self):
        """앱 시작 시 서버에 강제로 재검증 요청을 보내는 메서드"""
        logging.info("앱 시작 시 서버 강제 검증 수행")
        result = False
        if self.serial_number:
            # 마지막 검증 시간 확인
            try:
                self.cursor.execute(
                    "SELECT last_check_date FROM serial_data WHERE serial_number = ?", 
                    (self.serial_number,)
                )
                result = self.cursor.fetchone()
                
                if result and result[0]:
                    last_check = result[0]
                    last_datetime = datetime.strptime(last_check, "%Y-%m-%d %H:%M:%S")
                    hours_since_check = (datetime.now() - last_datetime).total_seconds() / 3600
                    
                    if hours_since_check < 1:  # 1시간 이내에 검증했으면 로컬 검증으로 대체 (24시간에서 변경)
                        logging.info(f"최근에 검증됨 (경과: {hours_since_check:.1f}시간, 1시간 이내) - 로컬 검증으로 대체")
                        # 로컬 검증 수행 - 다른 앱 사용 여부도 확인
                        self.validate_local()
                        
                        # 다른 앱에서 사용 중인지 확인
                        if "다른 앱" in self.status:
                            logging.warning(f"로컬 검증 결과 다른 앱에서 사용 중: {self.status}")
                            print(f"시리얼 인증 실패: {self.status}")
                            self.is_valid = False
                            return False
                            
                        return self.is_valid
            except Exception as e:
                logging.error(f"마지막 검증 시간 확인 중 오류: {e}")
            
            # 서버에 강제로 재검증 요청
            result = self.validate_serial(self.serial_number, update_device=True)
            logging.info(f"서버 강제 검증 결과: {result}, 상태: {self.status}")
        return result

    def get_stored_device_hash(self, serial_number):
        """저장된 디바이스 해시 정보를 가져옵니다."""
        try:
            # 로컬 디바이스 정보 파일 검색
            config_paths = [
                os.path.join(self.app_dir, 'config', 'device_info.json'),
                os.path.join(os.path.dirname(os.path.dirname(self.app_dir)), 'config', 'device_info.json')
            ]
            
            for path in config_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get('serial_number') == serial_number and 'device_info' in data:
                            device_hash = data['device_info'].get('device_hash')
                            if device_hash:
                                logging.info(f"로컬에 저장된 디바이스 해시 발견: {device_hash[:10]}...")
                                return device_hash
            
            # 데이터베이스에서 디바이스 해시 검색
            try:
                self.cursor.execute(
                    "SELECT device_hash FROM serial_data WHERE serial_number = ?", 
                    (serial_number,)
                )
                result = self.cursor.fetchone()
                if result and result[0]:
                    logging.info(f"데이터베이스에서 디바이스 해시 발견: {result[0][:10]}...")
                    return result[0]
            except Exception as db_error:
                logging.error(f"데이터베이스에서 디바이스 해시 검색 오류: {str(db_error)}")
            
            return None
        except Exception as e:
            logging.error(f"저장된 디바이스 해시 검색 중 오류: {str(e)}")
            return None

    def get_stored_app_name(self, serial_number):
        """저장된 앱 이름 정보를 가져옵니다."""
        try:
            # 로컬 디바이스 정보 파일 검색
            config_paths = [
                os.path.join(self.app_dir, 'config', 'device_info.json'),
                os.path.join(os.path.dirname(os.path.dirname(self.app_dir)), 'config', 'device_info.json')
            ]
            
            for path in config_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get('serial_number') == serial_number and 'device_info' in data:
                            app_name = data['device_info'].get('app_name')
                            if app_name:
                                logging.info(f"로컬에 저장된 앱 이름 발견: {app_name}")
                                return app_name
            
            # 데이터베이스에서 앱 이름 검색 시도
            try:
                if hasattr(self, 'cursor') and self.cursor:
                    # 데이터베이스에 app_name 필드가 있는지 확인
                    self.cursor.execute("PRAGMA table_info(serial_data)")
                    columns = [col[1] for col in self.cursor.fetchall()]
                    
                    if 'app_name' in columns:
                        self.cursor.execute(
                            "SELECT app_name FROM serial_data WHERE serial_number = ?", 
                            (serial_number,)
                        )
                        result = self.cursor.fetchone()
                        if result and result[0]:
                            logging.info(f"데이터베이스에서 앱 이름 발견: {result[0]}")
                            return result[0]
            except Exception as db_error:
                logging.error(f"데이터베이스에서 앱 이름 검색 오류: {str(db_error)}")
            
            return None
        except Exception as e:
            logging.error(f"저장된 앱 이름 검색 중 오류: {str(e)}")
            return None 