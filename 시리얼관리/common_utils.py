#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공통 유틸리티 모듈
시리얼 관리 시스템에서 공유되는 유틸리티 함수들을 제공합니다.

포함 기능:
- 디바이스 정보 수집
- 애플리케이션 경로 관리
- 백업 파일 자동 정리
"""

import os
import sys
import logging
import socket
import platform
import subprocess
from datetime import datetime, timedelta

# psutil 가져오기 (없으면 None)
try:
    import psutil
except ImportError:
    psutil = None


def get_app_path():
    """
    애플리케이션 실행 디렉토리의 절대 경로를 반환합니다.
    
    Returns:
        str: 애플리케이션 실행 디렉토리 경로
    """
    try:
        # 일반 실행 환경
        return os.path.dirname(os.path.abspath(__file__))
    except:
        # PyInstaller 등으로 패키징된 환경
        if hasattr(sys, 'frozen'):
            return os.path.dirname(sys.executable)
        else:
            # 다른 방법으로도 시도
            try:
                import inspect
                return os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
            except:
                return os.getcwd()


def get_device_info():
    """
    현재 디바이스 정보를 수집합니다. (macOS 및 일반 시스템 지원)
    
    Returns:
        dict: 디바이스 정보 딕셔너리
            - hostname: 호스트명
            - ip_address: IP 주소
            - system_manufacturer: 제조사
            - system_model: 모델명
            - os_name: 운영체제 이름
            - os_version: 운영체제 버전
            - processor: 프로세서 정보
            - total_memory: 총 메모리
            - registration_date: 등록 날짜
    """
    try:
        logging.info("디바이스 정보 수집 시작")
        
        # 호스트명 가져오기
        try:
            hostname = socket.gethostname()
        except Exception as e:
            logging.error(f"호스트명 가져오기 오류: {e}")
            hostname = "unknown"
        
        # IP 주소 가져오기
        try:
            ip_address = socket.gethostbyname(hostname)
        except Exception as e:
            logging.error(f"IP 주소 가져오기 오류: {e}")
            ip_address = "0.0.0.0"
        
        # 메모리 정보 가져오기
        try:
            if psutil:
                memory = psutil.virtual_memory()
                total_memory = f"{memory.total / (1024**3):.2f}GB"
            else:
                total_memory = "Unknown"
        except Exception as e:
            logging.error(f"메모리 정보 가져오기 오류: {e}")
            total_memory = "Unknown"
        
        # 시스템 정보 초기화
        system_info = {
            'system_manufacturer': 'Unknown',
            'system_model': 'Unknown',
            'os_name': platform.system(),
            'os_version': platform.version()
        }
        
        # macOS인 경우 추가 정보 수집
        if platform.system() == "Darwin":
            system_info['system_manufacturer'] = "Apple"
            
            # 모델 정보 가져오기
            try:
                model = subprocess.check_output(['sysctl', '-n', 'hw.model']).decode('utf-8').strip()
                system_info['system_model'] = model
            except Exception as e:
                logging.error(f"모델 정보 가져오기 오류: {e}")
                system_info['system_model'] = "Unknown Mac"
            
            # CPU 정보 가져오기
            try:
                processor = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string']).decode('utf-8').strip()
            except Exception:
                processor = platform.processor() or "Unknown Processor"
        else:
            # Windows/Linux
            processor = platform.processor() or "Unknown Processor"
        
        device_info = {
            "hostname": hostname,
            "ip_address": ip_address,
            "system_manufacturer": system_info['system_manufacturer'],
            "system_model": system_info['system_model'],
            "os_name": system_info['os_name'],
            "os_version": system_info['os_version'],
            "processor": processor,
            "total_memory": total_memory,
            "registration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        logging.info(f"디바이스 정보 수집 완료: {device_info}")
        return device_info
        
    except Exception as e:
        logging.error(f"디바이스 정보 수집 중 오류 발생: {str(e)}", exc_info=True)
        # 기본 디바이스 정보 반환
        return {
            "hostname": "unknown",
            "ip_address": "0.0.0.0",
            "system_manufacturer": "Unknown",
            "system_model": "Unknown",
            "os_name": platform.system(),
            "os_version": "Unknown",
            "processor": "Unknown Processor",
            "total_memory": "Unknown",
            "registration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


def cleanup_old_backups(backup_dir, max_age_days=30, keep_minimum=3):
    """
    지정된 일수보다 오래된 백업 파일을 자동으로 정리합니다.
    
    Args:
        backup_dir (str): 백업 폴더 경로
        max_age_days (int): 보관 기간 (일), 기본 30일
        keep_minimum (int): 최소 보관 개수, 기본 3개
        
    Returns:
        tuple: (삭제된 파일 수, 삭제된 파일 목록)
    """
    if not os.path.exists(backup_dir):
        logging.warning(f"백업 디렉토리가 존재하지 않습니다: {backup_dir}")
        return 0, []
    
    try:
        deleted_count = 0
        deleted_files = []
        
        # 백업 파일 목록 (수정 시간 기준 정렬)
        backup_files = []
        for filename in os.listdir(backup_dir):
            filepath = os.path.join(backup_dir, filename)
            if os.path.isfile(filepath) and filename.endswith('.db'):
                mtime = os.path.getmtime(filepath)
                backup_files.append((filepath, filename, mtime))
        
        # 수정 시간 기준 정렬 (최신순)
        backup_files.sort(key=lambda x: x[2], reverse=True)
        
        # 최소 보관 개수 유지
        if len(backup_files) <= keep_minimum:
            logging.info(f"백업 파일이 {len(backup_files)}개로 최소 보관 개수({keep_minimum})이하입니다. 삭제하지 않습니다.")
            return 0, []
        
        # 오래된 파일 삭제
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        cutoff_timestamp = cutoff_time.timestamp()
        
        for filepath, filename, mtime in backup_files[keep_minimum:]:
            if mtime < cutoff_timestamp:
                try:
                    os.remove(filepath)
                    deleted_count += 1
                    deleted_files.append(filename)
                    logging.info(f"오래된 백업 파일 삭제: {filename}")
                except Exception as e:
                    logging.error(f"백업 파일 삭제 실패 ({filename}): {e}")
        
        if deleted_count > 0:
            logging.info(f"백업 정리 완료: {deleted_count}개 파일 삭제")
        else:
            logging.info("삭제할 오래된 백업 파일이 없습니다.")
        
        return deleted_count, deleted_files
        
    except Exception as e:
        logging.error(f"백업 정리 중 오류 발생: {e}")
        return 0, []


def get_db_path(db_name='serials.db'):
    """
    데이터베이스 파일의 절대 경로를 반환합니다.
    
    Args:
        db_name (str): 데이터베이스 파일명
        
    Returns:
        str: 데이터베이스 파일 절대 경로
    """
    try:
        app_dir = get_app_path()
        db_path = os.path.join(app_dir, db_name)
        logging.info(f"데이터베이스 경로: {db_path}")
        return db_path
    except Exception as e:
        logging.error(f"데이터베이스 경로 설정 오류: {e}")
        return db_name


# 테스트 코드
if __name__ == "__main__":
    print("=== 공통 유틸리티 모듈 테스트 ===\n")
    
    print("1. 앱 경로:")
    print(f"   {get_app_path()}\n")
    
    print("2. 디바이스 정보:")
    device_info = get_device_info()
    for key, value in device_info.items():
        print(f"   {key}: {value}")
    
    print("\n3. 데이터베이스 경로:")
    print(f"   {get_db_path()}")
