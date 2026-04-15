#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
블로그자동화용 시리얼 인증 모듈
- 기존 시리얼관리 프로그램과 연동
- 간단하고 독립적인 구조
- 원격 서버 연동 지원
"""

import sys
import os
import json
import sqlite3
import requests
import logging
import socket
import platform
import subprocess
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime
from utils.path_utils import get_config_dir
from utils.security_utils import deobfuscate_dict_fields, obfuscate_dict_fields

class BlogSerialAuth:
    """블로그자동화용 시리얼 인증 클래스"""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        
        # 설정 파일은 사용자 홈 디렉토리에 저장 (path_utils 사용)
        self.config_dir = get_config_dir()
        # if not os.path.exists(self.config_dir):
        #     os.makedirs(self.config_dir, exist_ok=True)
        self.config_file = os.path.join(self.config_dir, "serial_config.json")
        
        self.server_url = "https://aimaster-serial.onrender.com"
        
        # 로깅 설정
        self.setup_logging()
        
        # 개발자 모드 감지 (환경 변수 또는 modules/.developer_mode 파일)
        self.developer_mode = self._check_developer_mode()
        
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
    
    def _check_developer_mode(self) -> bool:
        """개발자 모드 여부 확인 (강화된 체크)"""
        # 1. 환경 변수 체크
        env_flag = os.getenv("DEVELOPER_MODE_SECRET", "").lower() == "antigravity-dev-2026"
        
        # 2. 특정 파일 존재 확인 (내용 검증 추가)
        possible_paths = [
            os.path.join(self.base_dir, ".developer_mode"),
            os.path.join(os.path.dirname(self.base_dir), "modules", ".developer_mode"),
        ]
        
        if hasattr(sys, '_MEIPASS'):
            meipass = getattr(sys, '_MEIPASS')
            possible_paths.append(os.path.join(meipass, "modules", ".developer_mode"))
            possible_paths.append(os.path.join(meipass, ".developer_mode"))
        
        file_valid = False
        for p in possible_paths:
            if os.path.exists(p):
                try:
                    with open(p, 'r') as f:
                        if f.read().strip() == "antigravity-dev-key-9988":
                            file_valid = True
                            break
                except:
                    pass
        
        if env_flag or file_valid:
            self.logger.info("개발자 모드 활성화됨")
            return True
        return False
        
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
                    
                    # 🔐 민감 데이터 복호화 시도
                    config = deobfuscate_dict_fields(config)
                    
                    # 기본값으로 누락된 키 채우기
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                self.logger.error(f"설정 파일 로드 오류: {e}")
                
        return default_config
    
    def save_config(self, config: Dict):
        """설정 파일 저장 (민감 데이터 암호화 포함)"""
        try:
            # 🔐 민감 데이터 암호화
            save_data = obfuscate_dict_fields(config, ["serial_number"])
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            self.logger.info("설정 파일 저장 완료 (암호화 적용)")
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
        """
        시리얼 번호 종합 검증 (서버 우선, 오프라인 백업)
        
        검증 흐름:
        1. 서버 검증 (최대 3번 재시도, 점진적 타임아웃: 5초 → 25초 → 30초)
        2. 서버 실패 시 오프라인 모드 (최근 7일 내 검증 성공 이력 있으면 허용)
        3. 개발자 환경에서는 로컬 DB로 백업 검증
        """
        # 개발자 모드일 경우 바로 통과
        if self.developer_mode:
            return True, "개발자 모드 - 시리얼 인증 건너뜀", None
        
        expiry_date = None
        last_error = None
        
        # 점진적 타임아웃 설정 (총 60초)
        # 1차: 빠른 응답 기대 (5초)
        # 2차: Render 슬립 깨우기 (25초)
        # 3차: 최종 시도 (30초)
        timeouts = [5, 25, 30]
        
        # 1. 원격 서버 검증 (최대 3번 재시도 - Render 슬립 대응)
        for attempt in range(3):
            try:
                current_timeout = timeouts[attempt]
                self.logger.info(f"서버 검증 시도 {attempt + 1}/3 (타임아웃: {current_timeout}초)")
                
                response = requests.get(
                    f"{self.server_url}/api/serials/{serial_number}", 
                    timeout=current_timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status', 'unknown')
                    
                    # 블랙리스트 확인 (즉시 차단)
                    if status == '블랙리스트' or data.get('is_blacklisted', False):
                        return False, "시리얼이 블랙리스트 처리되었습니다.", None
                    
                    # 만료일 확인
                    expiry_str = data.get('expiry_date', '')
                    if expiry_str:
                        try:
                            expiry_date = datetime.strptime(expiry_str[:10], "%Y-%m-%d")
                            if expiry_date < datetime.now():
                                return False, "시리얼 번호가 만료되었습니다.", expiry_date
                            
                            # 만료 7주 전 경고
                            days_left = (expiry_date - datetime.now()).days
                            if days_left <= 49:
                                return True, f"주의: {days_left}일 후 만료됩니다.", expiry_date
                        except:
                            pass
                    
                    # 상태 확인
                    if status in ['사용가능', '사용중', 'active']:
                        return True, "서버 인증 성공", expiry_date
                    elif status == '만료됨':
                        return False, "시리얼 번호가 만료되었습니다.", expiry_date
                    else:
                        return False, f"시리얼 상태: {status}", expiry_date
                        
                elif response.status_code == 404:
                    return False, "유효하지 않은 시리얼 번호입니다.", None
                else:
                    last_error = f"서버 응답 오류: {response.status_code}"
                    self.logger.warning(last_error)
                    
            except requests.RequestException as e:
                last_error = str(e)
                self.logger.warning(f"서버 연결 시도 {attempt + 1}/3 실패: {e}")
                
                # 마지막 시도가 아니면 잠시 대기 후 재시도
                if attempt < 2:
                    import time
                    time.sleep(2)  # 2초 대기 후 재시도
                continue
        
        # 2. 모든 서버 시도 실패 - 오프라인 모드 검토
        self.logger.warning(f"서버 연결 3회 실패: {last_error}")
        
        # 2-1. 오프라인 모드: 최근 7일 내 검증 성공 이력 확인
        config = self.load_config()
        try:
            last_validation = datetime.fromisoformat(config.get("last_validation", ""))
            days_since_validation = (datetime.now() - last_validation).days
            
            if days_since_validation < 7:
                self.logger.info(f"오프라인 모드 허용: 마지막 검증 {days_since_validation}일 전")
                return True, f"오프라인 모드 (마지막 검증: {days_since_validation}일 전)", None
        except:
            pass
        
        # 2-2. 개발자 환경에서는 로컬 DB로 백업 검증
        if self.serial_db_path and os.path.exists(self.serial_db_path):
            self.logger.info("오프라인 모드: 로컬 DB로 검증 시도")
            return self.validate_serial_local(serial_number)
        
        # 3. 모든 방법 실패
        return False, "서버 연결 실패 - 인터넷 연결을 확인하세요.", None
    
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
        print(f"📡 디바이스 정보 업데이트 시작: {serial_number[:8]}...")
        self.logger.info(f"update_device_info_and_usage 호출: {serial_number}")
        
        # 디바이스 정보 수집
        device_info = self.get_device_info()
        device_info['app_name'] = '블로그자동화'  # 앱 이름 추가
        print(f"   디바이스 정보: {device_info.get('hostname', 'unknown')}, {device_info.get('platform', 'unknown')}")
        
        new_count = 1  # 기본값
        expiry_date = None
        
        # 로컬 DB가 있으면 로컬 업데이트도 수행
        if self.serial_db_path and os.path.exists(self.serial_db_path):
            try:
                device_info_json = json.dumps(device_info, ensure_ascii=False)
                
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
                self.logger.info(f"로컬 DB 업데이트 시도: {serial_number}")
                cursor.execute("""
                    UPDATE serials 
                    SET device_info = ?, 
                        activation_count = ?,
                        status = '사용중',
                        last_check_date = ?
                    WHERE serial_number = ?
                """, (device_info_json, new_count, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), serial_number))
                
                conn.commit()
                
                # 만료일 조회
                cursor.execute("SELECT expiry_date FROM serials WHERE serial_number = ?", (serial_number,))
                result = cursor.fetchone()
                if result:
                    expiry_date = result[0]
                
                conn.close()
                self.logger.info(f"로컬 DB 업데이트 완료: {serial_number} (사용횟수: {new_count})")
                
            except Exception as e:
                self.logger.warning(f"로컬 DB 업데이트 실패 (무시됨): {e}")
        else:
            print("   로컬 DB 없음 - 서버 업데이트만 수행")
            self.logger.info("로컬 DB 없음 - 서버 업데이트만 수행")
        
        # 서버에 업데이트 (로컬 DB 유무와 관계없이 항상 시도)
        try:
            # 로컬 DB에서 만료일을 못 가져온 경우, 서버에서 조회
            if not expiry_date:
                print("   서버에서 시리얼 정보 조회 중...")
                try:
                    response = requests.get(
                        f"{self.server_url}/api/serials/{serial_number}",
                        timeout=10
                    )
                    if response.status_code == 200:
                        data = response.json()
                        expiry_date = data.get('expiry_date', '')
                        # 기존 activation_count 가져오기
                        server_count = data.get('activation_count', 0)
                        new_count = server_count + 1
                        print(f"   만료일: {expiry_date}, 사용횟수: {server_count} → {new_count}")
                        self.logger.info(f"서버에서 만료일 조회: {expiry_date}, 사용횟수: {new_count}")
                    else:
                        print(f"   ❌ 서버 조회 실패: {response.status_code}")
                except Exception as fetch_e:
                    print(f"   ❌ 서버 정보 조회 실패: {fetch_e}")
                    self.logger.warning(f"서버 정보 조회 실패: {fetch_e}")
            
            update_data = {
                "device_info": device_info,
                "activation_count": new_count,
                "status": "사용중"
            }
            
            # 만료일 필수 - 서버 API 요구사항 (완화: 만료일 없어도 디바이스 정보는 업데이트 시도)
            if expiry_date:
                update_data["expiry_date"] = expiry_date
            else:
                print("   ⚠️ 만료일 정보 없음 - 만료일 제외하고 서버 업데이트 진행")
                self.logger.warning("만료일 정보 없음 - 만료일 제외하고 서버 업데이트 진행")
                # return False  <-- 기존에는 여기서 중단했으나, 디바이스 정보 업데이트를 위해 진행

            
            self.logger.info(f"서버 업데이트 시도: {serial_number}, 데이터: {update_data}")
            
            response = requests.patch(
                f"{self.server_url}/api/serials/{serial_number}",
                json=update_data,
                timeout=15
            )
            
            if response.status_code == 200:
                print(f"   ✅ 서버 업데이트 성공!")
                self.logger.info("서버 업데이트 성공")
                return True
            else:
                print(f"   ❌ 서버 업데이트 실패: {response.status_code}")
                self.logger.warning(f"서버 업데이트 실패: {response.status_code}, {response.text}")
                
        except Exception as server_e:
            print(f"   ❌ 서버 업데이트 오류: {server_e}")
            self.logger.warning(f"서버 업데이트 실패: {server_e}")
        
        # 로컬 DB 업데이트가 성공했으면 True 반환
        if self.serial_db_path and os.path.exists(self.serial_db_path):
            return True
        
        return False
    
    def is_serial_required(self) -> bool:
        """
        시리얼 입력이 필요한지 확인 (v1.2.123 개선)
        
        검증 흐름:
        1. 개발자 모드 체크
        2. 시리얼 번호 없으면 입력 요청
        3. [NEW] 로컬 만료일 먼저 체크 (서버 없이도 만료 즉시 차단)
        4. 서버 검증 시도
           - 서버 명시적 거부(만료/블랙리스트/비활성) → 즉시 차단
           - 서버 연결 불가(슬립/네트워크 오류) → 오프라인 모드 검토
        5. [개선] 오프라인 모드: 마지막 인증 14일 이내면 통과 (7일→14일 연장)
        """
        # 1. 개발자 모드
        if self.developer_mode:
            config = self.load_config()
            serial_number = config.get("serial_number")
            if serial_number:
                self.logger.info(f"개발자 모드 - 활성화 횟수 업데이트: {serial_number}")
                self.update_device_info_and_usage(serial_number)
            return False
        
        config = self.load_config()
        serial_number = config.get("serial_number")
        
        # 2. 시리얼 없으면 입력 요청
        if not serial_number:
            self.logger.info("시리얼 번호 없음 → 입력 필요")
            return True
        
        # 3. ✨ [NEW] 로컬 만료일 먼저 체크 (서버 없이도 만료 즉시 차단)
        #    만료일은 서버 인증 성공 시 로컬에 저장되는 서버 공식 데이터
        expiry_str = config.get("expiry_date", "")
        if expiry_str:
            try:
                local_expiry = datetime.fromisoformat(expiry_str)
                if local_expiry < datetime.now():
                    self.logger.info(f"로컬 만료일 체크: 만료됨 ({expiry_str}) → 재입력 필요")
                    return True  # 만료 → 서버 없이도 즉시 차단
                self.logger.info(f"로컬 만료일 체크: 유효 (만료: {local_expiry.strftime('%Y-%m-%d')})")
            except Exception as e:
                self.logger.warning(f"로컬 만료일 파싱 오류 (무시하고 계속): {e}")
        
        # 4. 서버 검증 시도
        server_explicitly_rejected = False
        server_unreachable = False
        
        try:
            valid, message, expiry_date = self.check_serial(serial_number)
            
            if valid:
                # ✅ 서버 검증 성공
                self.logger.info(f"서버 검증 성공: {message}")
                config["last_validation"] = datetime.now().isoformat()
                if expiry_date:
                    config["expiry_date"] = expiry_date.isoformat()
                self.save_config(config)
                self.update_device_info_and_usage(serial_number)
                return False
            else:
                # 서버 연결 실패(슬립) vs 서버 명시적 거부 구분
                offline_keywords = ["연결 실패", "오프라인", "서버 연결", "인터넷", "timeout", "Timeout"]
                if any(kw in message for kw in offline_keywords):
                    server_unreachable = True
                    self.logger.info(f"서버 연결 불가 → 오프라인 모드 검토: {message}")
                else:
                    # 만료됨 / 블랙리스트 / 비활성 등 명시적 거부
                    server_explicitly_rejected = True
                    self.logger.info(f"서버가 시리얼 명시적 거부: {message}")
                    
        except Exception as e:
            server_unreachable = True
            self.logger.error(f"시리얼 검증 중 예외 발생 → 오프라인 모드 검토: {e}")
        
        # 서버가 명시적으로 거부한 경우 → 오프라인 통과 없이 즉시 차단
        if server_explicitly_rejected:
            return True
        
        # 5. ✨ [개선] 오프라인 모드: 서버 연결 불가 시 14일 이내면 통과
        if server_unreachable:
            try:
                last_validation_str = config.get("last_validation", "")
                if last_validation_str:
                    last_validation = datetime.fromisoformat(last_validation_str)
                    days_since = (datetime.now() - last_validation).days
                    if days_since < 14:
                        self.logger.info(f"✅ 오프라인 모드 통과: 마지막 인증 {days_since}일 전 (14일 이내)")
                        return False
                    else:
                        self.logger.info(f"오프라인 기간 초과: {days_since}일 전 (14일 초과) → 재인증 필요")
                else:
                    self.logger.info("마지막 인증 기록 없음 → 오프라인 모드 불가")
            except Exception as e:
                self.logger.error(f"오프라인 모드 체크 오류: {e}")
        
        self.logger.info("모든 검증 실패 → 시리얼 재입력 필요")
        return True
    
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
