#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시리얼 인증 서버 상태 확인 유틸리티
"""

import requests
import json
import time
import uuid

# 서버 URL 설정
SERVER_URL = "https://aimaster-serial.onrender.com"

def check_server_status():
    """서버 상태 확인 함수"""
    print(f"서버 상태 확인 중 (URL: {SERVER_URL})...")
    
    # 테스트용 시리얼 번호 생성
    test_serial = str(uuid.uuid4())
    
    # 1. 시리얼 목록 엔드포인트 확인 - 실제 사용하는 엔드포인트
    serials_url = f"{SERVER_URL}/api/serials"
    print(f"\n1. 시리얼 목록 엔드포인트 확인: {serials_url}")
    check_endpoint(serials_url, method="GET")
    
    # 2. 디바이스 업데이트 엔드포인트 확인 (여러 가능한 엔드포인트)
    endpoints = [
        "/api/update_device",
        "/api/devices/update",
        "/api/register_device",
        "/api/device"
    ]
    
    device_info = {
        "hostname": "test-host",
        "ip_address": "127.0.0.1",
        "system_manufacturer": "Test",
        "system_model": "Test-Model",
        "os_name": "TestOS",
        "os_version": "1.0",
        "processor": "Test CPU",
        "total_memory": "16GB",
        "registration_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "app_name": "블로그자동화",
        "device_hash": "test-hash-123456"
    }
    
    device_data = {
        "serial_number": test_serial,
        "app_name": "블로그자동화",
        "device_info": device_info
    }
    
    for endpoint in endpoints:
        full_url = f"{SERVER_URL}{endpoint}"
        print(f"\n2. 디바이스 업데이트 엔드포인트 확인: {full_url}")
        check_endpoint(full_url, device_data)
    
    # 3. 루트 페이지 확인 (POST 방식도 시도)
    root_url = SERVER_URL
    print(f"\n3-1. 루트 페이지 확인 (GET): {root_url}")
    check_endpoint(root_url, method="GET")
    
    print(f"\n3-2. 루트 페이지 확인 (POST): {root_url}")
    check_endpoint(root_url, device_data)
    
    # 4. 디바이스 등록을 위한 다른 가능한 API 엔드포인트 확인
    other_endpoints = [
        "/api/validate",
        "/api/verify",
        "/api/devices",
        "/v1/api/devices",
        "/v1/api/serials"
    ]
    
    for endpoint in other_endpoints:
        full_url = f"{SERVER_URL}{endpoint}"
        print(f"\n4. 추가 엔드포인트 확인: {full_url}")
        # GET과 POST 모두 시도
        print(f"- GET 메서드:")
        check_endpoint(full_url, method="GET")
        print(f"- POST 메서드:")
        check_endpoint(full_url, device_data)

def check_endpoint(url, payload=None, method="POST", timeout=30):
    """특정 엔드포인트 확인"""
    try:
        start_time = time.time()
        
        if method == "POST" and payload:
            response = requests.post(url, json=payload, timeout=timeout)
        else:
            response = requests.get(url, timeout=timeout)
            
        end_time = time.time()
        
        print(f"응답 시간: {end_time - start_time:.2f}초")
        print(f"상태 코드: {response.status_code}")
        
        if response.status_code >= 200 and response.status_code < 300:
            print("서버가 정상적으로 응답했습니다.")
            try:
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    response_data = response.json()
                    print("\n응답 데이터(일부):")
                    print(json.dumps(response_data, indent=2, ensure_ascii=False)[:500])
                    if len(json.dumps(response_data)) > 500:
                        print("... (응답 데이터가 너무 길어 일부만 표시)")
                else:
                    print("\n응답 내용(일부):")
                    print(response.text[:500])
                    if len(response.text) > 500:
                        print("... (응답 내용이 너무 길어 일부만 표시)")
            except:
                print("\n응답 내용(일부):")
                print(response.text[:500])
        else:
            print(f"서버가 오류 응답을 반환했습니다: {response.status_code}")
            print(f"응답 내용: {response.text[:200]}")
    except requests.exceptions.Timeout:
        print(f"서버 응답 시간 초과 ({timeout}초)")
    except requests.exceptions.ConnectionError:
        print("서버 연결 실패")
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    check_server_status() 