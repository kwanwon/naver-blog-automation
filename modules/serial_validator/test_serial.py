#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시리얼 번호 검증 테스트 스크립트
"""

import sys
import os
import json
import time
import requests
from serial_client import SerialClient, SERVER_URL

def test_serial_validation():
    """시리얼 번호 검증 테스트"""
    client = SerialClient(app_name="블로그자동화")
    
    print("서버에서 시리얼 목록 가져오기...")
    try:
        response = requests.get(
            f"{SERVER_URL}/api/serials",
            timeout=30
        )
        
        if response.status_code == 200:
            serials = response.json()
            print(f"총 {len(serials)}개의 시리얼이 발견되었습니다.")
            
            # 모든 시리얼 표시
            print("\n사용 가능한 시리얼 번호:")
            for idx, serial in enumerate(serials, 1):
                status = serial.get("status", "상태 없음")
                expiry = serial.get("expiry_date", "만료일 없음")
                serial_num = serial.get("serial_number", "번호 없음")
                print(f"{idx}. {serial_num} - 상태: {status}, 만료일: {expiry}")
                
            # 첫 번째 '사용가능' 상태의 시리얼 선택
            test_serial = None
            for serial in serials:
                if serial.get("status") == "사용가능" and not serial.get("is_blacklisted", False):
                    test_serial = serial.get("serial_number")
                    break
            
            if test_serial:
                print(f"\n테스트할 시리얼 번호: {test_serial}")
                
                # 시리얼 검증 테스트
                print("\n시리얼 검증 테스트 중...")
                result = client.validate_serial(test_serial)
                
                print(f"검증 결과: {'성공' if result else '실패'}")
                print(f"상태: {client.status}")
                print(f"만료일: {client.expiry_date}")
                print(f"남은 일수: {client.get_remaining_days()}일")
                
                # 결과가 성공이면 로컬 저장 테스트도 실행
                if result:
                    print("\n로컬 저장 및 로드 테스트...")
                    # 클라이언트 종료
                    client.close()
                    
                    # 새 클라이언트 생성
                    new_client = SerialClient(app_name="블로그자동화")
                    print(f"새 클라이언트에서 저장된 시리얼 로드 결과: {'성공' if new_client.is_valid else '실패'}")
                    print(f"로드된 시리얼 번호: {new_client.serial_number}")
                    print(f"상태: {new_client.status}")
                    new_client.close()
            else:
                print("\n사용 가능한 시리얼을 찾을 수 없습니다.")
        else:
            print(f"시리얼 목록을 가져오는데 실패했습니다. 상태 코드: {response.status_code}")
    except Exception as e:
        print(f"오류 발생: {str(e)}")

if __name__ == "__main__":
    test_serial_validation() 