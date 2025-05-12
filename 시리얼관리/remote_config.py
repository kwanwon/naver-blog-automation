#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
원격 서버 설정 모듈
블로그 자동화 시스템을 위한 원격 서버 설정 및 사용법
"""

import os
import json
import logging
from datetime import datetime
import requests

# 서버 URL 설정
SERVER_URL = "https://aimaster-serial.onrender.com"

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='remote_server.log'
)

class RemoteServerConfig:
    """원격 서버 설정 및 연결 관리 클래스"""
    
    def __init__(self, server_url=None):
        self.server_url = server_url or SERVER_URL
        self.is_connected = False
        self.last_check_time = None
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'remote_config.json')
        self.load_config()
    
    def load_config(self):
        """설정 파일 로드"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.server_url = config.get('server_url', self.server_url)
                    logging.info(f"원격 서버 설정 로드: {self.server_url}")
        except Exception as e:
            logging.error(f"설정 파일 로드 오류: {str(e)}")
    
    def save_config(self):
        """설정 파일 저장"""
        try:
            config = {
                'server_url': self.server_url,
                'last_check_time': datetime.now().isoformat() if self.last_check_time else None,
                'is_connected': self.is_connected
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logging.info("원격 서버 설정 저장 완료")
        except Exception as e:
            logging.error(f"설정 파일 저장 오류: {str(e)}")
    
    def check_connection(self):
        """서버 연결 상태 확인"""
        try:
            response = requests.get(f"{self.server_url}/api/health", timeout=5)
            self.is_connected = response.status_code == 200
            self.last_check_time = datetime.now()
            self.save_config()
            return self.is_connected
        except Exception as e:
            logging.error(f"서버 연결 확인 오류: {str(e)}")
            self.is_connected = False
            self.last_check_time = datetime.now()
            self.save_config()
            return False
    
    def get_connection_status(self):
        """현재 연결 상태 정보 반환"""
        return {
            'is_connected': self.is_connected,
            'server_url': self.server_url,
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None
        }

# 원격 서버 API 호출 함수
def get_all_serials():
    """모든 시리얼 정보 가져오기"""
    try:
        response = requests.get(f"{SERVER_URL}/api/serials", timeout=30)
        logging.debug(f"서버 응답 (get_all_serials): {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logging.debug(f"서버 데이터: {json.dumps(data, ensure_ascii=False)[:200]}...")
            
            # 서버 응답 형식 확인 및 처리
            if isinstance(data, dict) and 'serials' in data:
                # {'serials': [...]} 형식인 경우
                return data.get('serials', [])
            elif isinstance(data, list):
                # 직접 리스트를 반환하는 경우
                return data
            else:
                logging.warning(f"예상치 못한 서버 응답 형식: {type(data)}")
                return []
        
        logging.error(f"시리얼 목록 요청 실패: {response.status_code}, {response.text[:200]}")
        return []
    except Exception as e:
        logging.error(f"시리얼 목록 가져오기 오류: {str(e)}")
        return []

def validate_serial(serial_number, device_info=None):
    """시리얼 번호 유효성 검증"""
    try:
        data = {
            'serial_number': serial_number
        }
        if device_info:
            # 디바이스 정보 간소화
            data['device_info'] = {'hostname': device_info.get('hostname', 'unknown')}
        
        logging.debug(f"검증 요청 데이터: {json.dumps(data, ensure_ascii=False)}")
        response = requests.post(f"{SERVER_URL}/api/validate", json=data, timeout=30)
        logging.debug(f"서버 응답 (validate_serial): {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            logging.debug(f"검증 결과: {json.dumps(result, ensure_ascii=False)}")
            return result
        logging.error(f"시리얼 검증 요청 실패: {response.status_code}, {response.text[:200]}")
        return {'valid': False, 'message': f'서버 오류: {response.status_code}'}
    except Exception as e:
        logging.error(f"시리얼 검증 오류: {str(e)}")
        return {'valid': False, 'message': f'연결 오류: {str(e)}'}

def create_serial(serial_data):
    """새 시리얼 생성"""
    try:
        # 디바이스 정보 간소화
        if 'device_info' in serial_data and isinstance(serial_data['device_info'], dict):
            serial_data['device_info'] = {'hostname': serial_data['device_info'].get('hostname', 'auto-generated')}
        
        logging.debug(f"생성 요청 데이터: {json.dumps(serial_data, ensure_ascii=False)}")
        # /api/serials 대신 /api/register 엔드포인트 사용
        response = requests.post(f"{SERVER_URL}/api/register", json=serial_data, timeout=30)
        logging.debug(f"서버 응답 (create_serial): {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                logging.debug(f"생성 결과: {json.dumps(result, ensure_ascii=False)}")
                
                # 응답 형식에 따라 유연하게 처리
                if isinstance(result, dict):
                    # 'success' 키가 있으면 그대로 반환
                    if 'success' in result:
                        success = result.get('success', False)
                    # 'status'가 'success'인 경우
                    elif result.get('status') == 'success':
                        success = True
                    # 메시지만 있는 경우
                    elif 'message' in result:
                        success = True
                    # 기타 경우
                    else:
                        success = True
                else:
                    # 다른 응답 형식이면 성공으로 처리
                    success = True
                
                # 시리얼 등록 성공 시 GitHub 백업 실행
                if success:
                    logging.info("시리얼 등록 성공, GitHub 백업 시작")
                    backup_result = backup_to_github()
                    logging.info(f"GitHub 백업 결과: {backup_result.get('message')}")
                
                # 'success' 키가 있으면 그대로 반환
                if isinstance(result, dict) and 'success' in result:
                    return result
                # 'status'가 'success'인 경우
                elif isinstance(result, dict) and result.get('status') == 'success':
                    return {'success': True, 'message': result.get('message', '성공적으로 등록되었습니다.')}
                # 메시지만 있는 경우
                elif isinstance(result, dict) and 'message' in result:
                    return {'success': True, 'message': result['message']}
                # 기타 경우
                else:
                    return {'success': True, 'message': '시리얼이 등록되었습니다.'}
                
            except ValueError as json_err:
                # JSON 파싱 오류 처리
                logging.warning(f"JSON 파싱 오류: {str(json_err)}, 텍스트 응답: {response.text[:100]}")
                return {'success': True, 'message': '시리얼이 등록되었습니다. (응답 형식 경고)'}
        
        logging.error(f"시리얼 생성 요청 실패: {response.status_code}, {response.text[:200]}")
        return {'success': False, 'message': f'서버 오류: {response.status_code}'}
    except Exception as e:
        logging.error(f"시리얼 생성 오류: {str(e)}")
        return {'success': False, 'message': f'연결 오류: {str(e)}'}

def setup_github_config(github_token=None, github_repo=None):
    """GitHub 설정 정보 설정
    
    Args:
        github_token: GitHub 접근 토큰
        github_repo: GitHub 저장소 (username/repo 형식)
    
    Returns:
        성공 여부와 메시지를 담은 딕셔너리
    """
    try:
        config_data = {
            "github_config": {
                "token": github_token,
                "repo": github_repo
            }
        }
        
        if github_token is None or github_repo is None:
            logging.warning("GitHub 설정 정보가 불완전합니다.")
            return {"success": False, "message": "GitHub 설정 정보가 불완전합니다."}
        
        response = requests.post(
            f"{SERVER_URL}/api/config/github", 
            json=config_data,
            timeout=30
        )
        
        logging.debug(f"GitHub 설정 응답: {response.status_code}")
        
        if response.status_code == 200:
            return {"success": True, "message": "GitHub 설정이 업데이트되었습니다."}
        else:
            return {"success": False, "message": f"GitHub 설정 업데이트 실패: {response.status_code}"}
    except Exception as e:
        logging.error(f"GitHub 설정 오류: {str(e)}")
        return {"success": False, "message": f"GitHub 설정 오류: {str(e)}"}

def test_github_connection():
    """GitHub 연결 테스트
    
    Returns:
        성공 여부와 메시지를 담은 딕셔너리
    """
    try:
        response = requests.get(f"{SERVER_URL}/api/config/github/test", timeout=30)
        
        logging.debug(f"GitHub 연결 테스트 응답: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            return {"success": True, "message": "GitHub 연결 테스트 성공", "details": result}
        else:
            return {"success": False, "message": f"GitHub 연결 테스트 실패: {response.status_code}"}
    except Exception as e:
        logging.error(f"GitHub 연결 테스트 오류: {str(e)}")
        return {"success": False, "message": f"GitHub 연결 테스트 오류: {str(e)}"}

# GitHub 백업 함수
def backup_to_github():
    """GitHub에 백업 실행"""
    try:
        # ai마스터관리와 동일한 GitHub 설정 값으로 설정
        github_token = "ghp_4a5hUoiXUfXkNPYOx2Kkc4QRjspg1o4LJtK7"  # ai마스터관리와 동일한 토큰
        github_repo = "kwanwon/serial-validator-server"  # 실제 저장소
        
        # 먼저 GitHub 설정 요청
        config_data = {
            "github_config": {
                "token": github_token,
                "repo": github_repo
            }
        }
        
        # GitHub 설정 요청
        logging.debug(f"GitHub 설정 요청: {json.dumps(config_data, ensure_ascii=False)}")
        config_response = requests.post(
            f"{SERVER_URL}/api/config/github", 
            json=config_data,
            timeout=30
        )
        
        if config_response.status_code != 200:
            logging.warning(f"GitHub 설정 실패: {config_response.status_code}")
        else:
            logging.info("GitHub 설정 성공")
        
        # 백업 요청
        logging.debug("GitHub 백업 요청")
        backup_response = requests.post(f"{SERVER_URL}/api/backup", timeout=30)
        
        if backup_response.status_code == 200:
            logging.info("GitHub 백업 성공")
            return {"success": True, "message": "GitHub 백업이 완료되었습니다."}
        else:
            logging.error(f"GitHub 백업 실패: {backup_response.status_code}, {backup_response.text[:200]}")
            return {"success": False, "message": f"GitHub 백업 실패: {backup_response.status_code}"}
    except Exception as e:
        logging.error(f"GitHub 백업 오류: {str(e)}")
        return {"success": False, "message": f"GitHub 백업 오류: {str(e)}"}

# 인스턴스 생성 
server_config = RemoteServerConfig() 

# 테스트 함수
def test_github_backup():
    """GitHub 백업 테스트 함수"""
    print("GitHub 백업 테스트 시작...")
    result = backup_to_github()
    print(f"결과: {result['success']}")
    print(f"메시지: {result['message']}")
    return result

if __name__ == '__main__':
    # 서버 연결 테스트
    print("서버 연결 상태:", server_config.check_connection())
    
    # 테스트를 원하는 경우 아래 주석을 해제하세요
    test_github_backup() 