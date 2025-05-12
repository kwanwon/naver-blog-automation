#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
서버 연결 유틸리티 모듈
재시도 로직 및 오프라인 모드 지원
"""

import requests
import logging
import time
import json
import os
import hashlib
from datetime import datetime
import sys

# 기본 설정
DEFAULT_TIMEOUT = 65  # 기본 타임아웃 (초)
MAX_RETRIES = 3       # 최대 재시도 횟수
RETRY_DELAY = 2       # 재시도 간격 (초)
OFFLINE_MODE = False  # 오프라인 모드 (네트워크 연결 없이 작동)

def get_app_path():
    """애플리케이션 디렉토리 경로를 반환합니다."""
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except:
        # 실행 파일 내에서 실행될 때
        if hasattr(sys, 'frozen'):
            return os.path.dirname(sys.executable)
        else:
            return os.getcwd()

# 오프라인 모드 활성화 여부 확인
def is_offline_mode():
    """오프라인 모드 활성화 여부를 반환합니다."""
    return OFFLINE_MODE

# 오프라인 모드 설정
def set_offline_mode(mode=True):
    """오프라인 모드를 설정합니다."""
    global OFFLINE_MODE
    OFFLINE_MODE = mode
    logging.info(f"오프라인 모드 설정: {mode}")

# 서버 연결 테스트
def test_server_connection(server_url, endpoint="/api/health"):
    """서버 연결을 테스트합니다."""
    try:
        response = requests.get(f"{server_url}{endpoint}", timeout=DEFAULT_TIMEOUT)
        return response.status_code == 200
    except:
        return False

# 안전한 서버 요청 (재시도 로직 포함)
def safe_request(method, url, **kwargs):
    """
    안전한 서버 요청을 수행합니다. 실패 시 재시도합니다.
    
    :param method: 요청 메서드 ('get', 'post', 'put', 'delete', 'patch')
    :param url: 요청 URL
    :param kwargs: requests 라이브러리에 전달할 추가 인자
    :return: 응답 객체 또는 None (실패 시)
    """
    global OFFLINE_MODE
    
    # 오프라인 모드인 경우
    if OFFLINE_MODE:
        logging.info(f"오프라인 모드: {method.upper()} {url} 요청 무시됨")
        
        # 오프라인 모드에서의 가상 응답 생성
        class MockResponse:
            def __init__(self, status_code, data=None):
                self.status_code = status_code
                self._data = data or {}
            
            def json(self):
                return self._data
        
        # API 유형에 따른 기본 응답 생성
        if "/api/health" in url:
            return MockResponse(200, {"status": "ok", "message": "오프라인 모드에서는 항상 정상입니다."})
        elif "/api/serials" in url and method.lower() == 'get':
            # 로컬 데이터베이스 데이터를 사용하여 가상 응답 생성
            return MockResponse(200, {"serials": []})
        else:
            return MockResponse(200, {"success": True, "message": "오프라인 모드에서 처리됨"})
    
    # 타임아웃 설정
    if 'timeout' not in kwargs:
        kwargs['timeout'] = DEFAULT_TIMEOUT
    
    # 요청 메서드 선택
    request_func = getattr(requests, method.lower())
    
    # 요청 시도
    for attempt in range(MAX_RETRIES):
        try:
            logging.info(f"서버 요청 시도 ({attempt + 1}/{MAX_RETRIES}): {method.upper()} {url}")
            response = request_func(url, **kwargs)
            logging.info(f"서버 응답: {response.status_code}")
            return response
        except requests.exceptions.Timeout:
            logging.warning(f"서버 요청 타임아웃 ({attempt + 1}/{MAX_RETRIES}): {url}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))  # 지수 백오프
            else:
                logging.error(f"서버 요청 최대 재시도 횟수 초과: {url}")
                # 마지막 시도 후 오프라인 모드로 전환
                OFFLINE_MODE = True
                return None
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
            logging.warning(f"서버 연결 오류 ({attempt + 1}/{MAX_RETRIES}): {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                logging.error(f"서버 연결 실패: {str(e)}")
                # 마지막 시도 후 오프라인 모드로 전환
                OFFLINE_MODE = True
                return None

# 로컬 캐시 관리
class ResponseCache:
    """API 응답 캐싱 클래스"""
    
    def __init__(self, cache_dir=None):
        if cache_dir is None:
            # 기본 캐시 디렉토리 설정 - 애플리케이션 경로 기반으로 설정
            app_path = get_app_path()
            cache_dir = os.path.join(app_path, 'cache')
        
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        logging.info(f"캐시 디렉토리: {cache_dir}")
    
    def get_cache_path(self, key):
        """캐시 파일 경로를 반환합니다."""
        # 파일명으로 사용할 수 있도록 키 해시화
        hashed_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{hashed_key}.json")
    
    def get(self, key):
        """캐시에서 데이터를 가져옵니다."""
        cache_path = self.get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 캐시 유효 기간 확인 (24시간)
                    if data.get('timestamp'):
                        cached_time = datetime.fromisoformat(data['timestamp'])
                        if (datetime.now() - cached_time).total_seconds() < 86400:
                            return data['response']
            except Exception as e:
                logging.error(f"캐시 읽기 오류: {str(e)}")
        return None
    
    def set(self, key, response_data):
        """응답 데이터를 캐시에 저장합니다."""
        cache_path = self.get_cache_path(key)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                cache_data = {
                    'timestamp': datetime.now().isoformat(),
                    'response': response_data
                }
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"캐시 쓰기 오류: {str(e)}")

# 캐시 인스턴스 생성
cache = ResponseCache()

# 캐시 지원 API 요청
def cached_request(method, url, use_cache=True, **kwargs):
    """
    캐시를 지원하는 API 요청을 수행합니다.
    GET 요청만 캐싱합니다.
    
    :param method: 요청 메서드
    :param url: 요청 URL
    :param use_cache: 캐시 사용 여부
    :param kwargs: requests 라이브러리에 전달할 추가 인자
    :return: 응답 데이터
    """
    # GET 요청이며 캐시 사용이 활성화된 경우에만 캐시 확인
    if method.lower() == 'get' and use_cache:
        # 요청 파라미터를 포함한 캐시 키 생성
        cache_key = url
        if 'params' in kwargs:
            cache_key += json.dumps(kwargs['params'], sort_keys=True)
        
        # 캐시에서 데이터 확인
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logging.info(f"캐시에서 데이터 로드: {url}")
            return cached_data
    
    # 서버 요청 수행
    response = safe_request(method, url, **kwargs)
    
    # 응답 처리
    if response is not None and response.status_code == 200:
        try:
            response_data = response.json()
            
            # GET 요청인 경우 캐시에 저장
            if method.lower() == 'get' and use_cache:
                cache.set(cache_key, response_data)
            
            return response_data
        except Exception as e:
            logging.error(f"응답 데이터 처리 오류: {str(e)}")
            return None
    
    return None

# 편의 함수들
def get(url, **kwargs):
    """GET 요청을 수행합니다."""
    return cached_request('get', url, **kwargs)

def post(url, **kwargs):
    """POST 요청을 수행합니다."""
    return cached_request('post', url, use_cache=False, **kwargs)

def put(url, **kwargs):
    """PUT 요청을 수행합니다."""
    return cached_request('put', url, use_cache=False, **kwargs)

def patch(url, **kwargs):
    """PATCH 요청을 수행합니다."""
    return cached_request('patch', url, use_cache=False, **kwargs)

def delete(url, **kwargs):
    """DELETE 요청을 수행합니다."""
    return cached_request('delete', url, use_cache=False, **kwargs) 