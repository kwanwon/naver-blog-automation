#!/usr/bin/env python3
# -*- coding: utf-8 -*-
########################################
# 블로그자동화관리.py
# 블로그 자동화 시리얼 관리 시스템
########################################

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import datetime
import logging
import os
import requests
import json
import sys
import uuid
import platform
import psutil
import socket
from datetime import datetime, timedelta
import pandas as pd
from tkcalendar import DateEntry
import threading
import queue
import subprocess

# 로깅 설정
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(current_dir, 'blog_manager.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.info(f"로깅 시작, 로그 파일: {log_file}")
except Exception as e:
    # 오류 발생 시 상대 경로 사용
    logging.basicConfig(
        filename='blog_manager.log',
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.error(f"로그 파일 경로 설정 오류: {e}")
    logging.info("상대 경로로 로깅을 시작합니다.")

# 서버 URL 설정
# 로컬 테스트 서버나 원격 서버 중 선택
# USE_LOCAL_SERVER = True로 설정하면 로컬 서버 사용, False로 설정하면 원격 서버 사용
USE_LOCAL_SERVER = False

# 서버 주소 설정
if USE_LOCAL_SERVER:
    # 로컬 테스트 서버
    BLOG_SERVER_URL = "http://localhost:5000"
else:
    # 배포된 원격 서버
    BLOG_SERVER_URL = "https://aimaster-serial.onrender.com"

def get_app_path():
    """애플리케이션 실행 디렉토리의 절대 경로를 반환합니다."""
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

def get_db_path():
    """데이터베이스 파일의 절대 경로를 반환"""
    try:
        app_dir = get_app_path()
        db_path = os.path.join(app_dir, 'blogs.db')
        logging.info(f"데이터베이스 경로: {db_path}")
        return db_path
    except Exception as e:
        logging.error(f"데이터베이스 경로 설정 오류: {e}")
        # 오류 발생 시 상대 경로 반환
        db_path = 'blogs.db'
        logging.info(f"상대 경로 사용: {db_path}")
        return db_path

def get_device_info():
    """디바이스 정보 수집 (맥 OS 버전)"""
    try:
        logging.info("디바이스 정보 수집 시작")
        
        # 로그 파일 경로를 절대 경로로 설정
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            log_path = os.path.join(current_dir, 'blog_manager.log')
            logging.info(f"로그 파일 경로: {log_path}")
        except Exception as e:
            logging.error(f"로그 파일 경로 설정 오류: {e}")
        
        # 맥 OS에서 시스템 정보 얻기
        try:
            hostname = socket.gethostname()
            logging.info(f"호스트명: {hostname}")
        except Exception as e:
            logging.error(f"호스트명 가져오기 오류: {e}")
            hostname = "unknown"
            
        try:
            ip_address = socket.gethostbyname(hostname)
            logging.info(f"IP 주소: {ip_address}")
        except Exception as e:
            logging.error(f"IP 주소 가져오기 오류: {e}")
            ip_address = "0.0.0.0"
            
        # 메모리 정보 가져오기
        try:
            memory = psutil.virtual_memory()
            logging.info(f"메모리 정보: {memory}")
        except Exception as e:
            logging.error(f"메모리 정보 가져오기 오류: {e}")
            memory = type('obj', (object,), {'total': 8000000000})
        
        # 맥에서 시스템 정보 가져오기
        system_info = {}
        
        # 모델 정보 가져오기
        try:
            model = subprocess.check_output(['sysctl', '-n', 'hw.model']).decode('utf-8').strip()
            system_info['system_model'] = model
            logging.info(f"모델 정보: {model}")
        except Exception as e:
            logging.error(f"모델 정보 가져오기 오류: {e}")
            system_info['system_model'] = "Unknown Mac"
        
        # OS 버전 정보
        try:
            system_info['os_name'] = platform.system()
            system_info['os_version'] = platform.version()
            logging.info(f"OS 정보: {system_info['os_name']} {system_info['os_version']}")
        except Exception as e:
            logging.error(f"OS 정보 가져오기 오류: {e}")
            system_info['os_name'] = "Unknown"
            system_info['os_version'] = "Unknown"
            logging.error(f"OS 정보 가져오기 오류: {e}")
            system_info['os_name'] = "Unknown"
            system_info['os_version'] = "Unknown"
        
        # 제조사는 Apple로 고정
        system_info['system_manufacturer'] = "Apple"
        
        # CPU 정보
        try:
            processor = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string']).decode('utf-8').strip()
            logging.info(f"프로세서 정보: {processor}")
        except Exception as e:
            logging.error(f"프로세서 정보 가져오기 오류: {e}")
            try:
                processor = platform.processor() or "Unknown Processor"
            except Exception as inner_e:
                logging.error(f"플랫폼 프로세서 정보 가져오기 오류: {inner_e}")
                processor = "Unknown Processor"
        device_info = {
            "hostname": hostname,
            "ip_address": ip_address,
            "system_manufacturer": system_info['system_manufacturer'],
            "system_model": system_info['system_model'],
            "os_name": system_info['os_name'],
            "os_version": system_info['os_version'],
            "processor": processor,
            "total_memory": f"{getattr(memory, 'total', 8000000000) / (1024**3):.2f}GB",
            "registration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        logging.info(f"디바이스 정보 수집 완료: {device_info}")
        return device_info
    except Exception as e:
        logging.error(f"디바이스 정보 수집 중 오류 발생: {str(e)}", exc_info=True)
        # 기본 디바이스 정보 반환
        default_info = {
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
        logging.info(f"기본 디바이스 정보 사용: {default_info}")
        return default_info

class BlogManager:
    def __init__(self, parent=None):
        # 변수 초기화
        self.is_standalone = parent is None
        self.parent = parent
        self.server_connected = False  # 서버 연결 상태 초기화
        
        if self.is_standalone:
            # 독립 실행 모드일 경우 먼저 root를 생성
            self.root = tk.Tk()
            self.root.title("블로그 자동화 시리얼 관리 시스템")
            self.root.geometry("1400x800")
            
            self.style = ttk.Style()
            self.style.theme_use('clam')
        else:
            # 탭으로 임베드될 경우
            self.root = parent
        
        # StringVar 등의 변수는 Tk 인스턴스 생성 후에 초기화
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="전체")
        self.date_filter_var = tk.StringVar(value="전체 기간")
        self.task_queue = queue.Queue()
        
        # 공통 초기화 작업 - 먼저 데이터베이스를 초기화해야 함
        self.init_database()
        
        if not self.is_standalone:
            self.setup_tab_ui(parent)
        else:
            # 메뉴바 추가
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)
            
            # 파일 메뉴
            file_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="파일", menu=file_menu)
            file_menu.add_command(label="시리얼 생성", command=self.create_serial)
            file_menu.add_command(label="새로고침", command=self.refresh_serial_list)
            file_menu.add_command(label="엑셀 내보내기", command=self.export_to_excel)
            file_menu.add_command(label="데이터 백업", command=self.backup_database)
            file_menu.add_separator()
            file_menu.add_command(label="GitHub 설정", command=self.setup_github)
            file_menu.add_command(label="GitHub 백업", command=self.manual_github_backup)
            file_menu.add_separator()
            file_menu.add_command(label="종료", command=self.root.quit)
            
            # 편집 메뉴
            edit_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="편집", menu=edit_menu)
            edit_menu.add_command(label="복사", command=self.copy_selected)
            edit_menu.add_command(label="전체 선택", command=self.select_all)
            edit_menu.add_separator()
            edit_menu.add_command(label="메모 수정", command=lambda: self.edit_memo(None))
            edit_menu.add_command(label="만료일 수정", command=self.edit_expiry_date)
            
            # 관리 메뉴
            manage_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="관리", menu=manage_menu)
            manage_menu.add_command(label="블랙리스트 설정", command=self.set_blacklist)
            manage_menu.add_command(label="블랙리스트 해제", command=self.unset_blacklist)
            manage_menu.add_separator()
            manage_menu.add_command(label="서버에서 확인", command=self.check_serial_on_server)
            manage_menu.add_separator()
            manage_menu.add_command(label="삭제", command=self.delete_serial)
            
            # GUI 생성
            self.create_main_frame(self.root)
            
            # 현재 시간 표시 레이블 추가
            self.time_label = ttk.Label(self.root, text="", font=("Helvetica", 12))
            self.time_label.pack(pady=5)
        
        # 컨텍스트 메뉴 생성
        self.context_menu = tk.Menu(self.parent if self.parent else self.root, tearoff=0)
        self.context_menu.add_command(label="복사", command=self.copy_selected)
        self.context_menu.add_command(label="전체 선택", command=self.select_all)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="메모 수정", command=lambda: self.edit_memo(None))
        self.context_menu.add_command(label="만료일 수정", command=self.edit_expiry_date)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="블랙리스트 설정", command=self.set_blacklist)
        self.context_menu.add_command(label="블랙리스트 해제", command=self.unset_blacklist)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="서버에서 확인", command=self.check_serial_on_server)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="삭제", command=self.delete_serial)
        
        # 데이터 로드
        self.refresh_serial_list()
        
        if self.is_standalone:
            self.process_background_tasks()
            self.update_time()
            self.check_serial_status()
            self.check_server_connection()
            self.check_expiring_serials()
    
    def init_database(self):
        """데이터베이스 초기화"""
        try:
            self.conn = sqlite3.connect(get_db_path())
            self.cursor = self.conn.cursor()
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS blog_serials (
                    serial_number TEXT PRIMARY KEY,
                    status TEXT,
                    created_date TEXT,
                    expiry_date TEXT,
                    device_info TEXT,
                    memo TEXT,
                    is_deleted INTEGER DEFAULT 0,
                    is_blacklisted INTEGER DEFAULT 0,
                    last_check_date TEXT,
                    activation_count INTEGER DEFAULT 0
                )
            ''')
            
            # 로컬 메모 테이블 추가
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS blog_local_memos (
                    serial_number TEXT PRIMARY KEY,
                    memo TEXT
                )
            ''')
            
            self.conn.commit()
            logging.info("블로그 자동화 데이터베이스 초기화 완료")
        except Exception as e:
            logging.error(f"데이터베이스 초기화 오류: {e}")
            messagebox.showerror("오류", "데이터베이스 초기화 중 오류가 발생했습니다.")
    
    def setup_tab_ui(self, parent):
        """탭으로 임베드될 때 UI 설정"""
        self.create_main_frame(parent)
        
    def create_main_frame(self, parent):
        """메인 프레임 생성"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)
        
        search_frame = ttk.LabelFrame(top_frame, text="검색 옵션")
        search_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Label(search_frame, text="검색어:").pack(side=tk.LEFT, padx=5)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        self.search_var.trace('w', lambda *args: self.refresh_serial_list())
        
        ttk.Label(search_frame, text="상태:").pack(side=tk.LEFT, padx=5)
        status_combo = ttk.Combobox(
            search_frame, textvariable=self.status_var, 
            values=["전체", "사용가능", "사용중", "사용불가", "만료됨", "만료 예정", "블랙리스트"], width=10
        )
        status_combo.pack(side=tk.LEFT, padx=5)
        status_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_serial_list())
        
        ttk.Button(search_frame, text="검색", command=self.refresh_serial_list).pack(side=tk.LEFT, padx=5)
        
        button_frame = ttk.LabelFrame(top_frame, text="작업")
        button_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="시리얼 생성", command=self.create_serial).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="새로고침", command=self.refresh_serial_list).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="엑셀 내보내기", command=self.export_to_excel).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="데이터 백업", command=self.backup_database).pack(side=tk.LEFT, padx=2)
        
        self.status_label = ttk.Label(main_frame, text="서버 연결 확인 중...", anchor=tk.W)
        self.status_label.pack(fill=tk.X, pady=(5,0))
        
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        columns = ("serial", "status", "created", "expiry", "device", "memo", "activation_count")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")
        
        y_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        x_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # 컬럼 헤더 설정 - 중앙 정렬 추가
        self.tree.heading("serial", text="시리얼 번호", anchor="center")
        self.tree.heading("status", text="상태", anchor="center")
        self.tree.heading("created", text="등록일시", anchor="center")
        self.tree.heading("expiry", text="만료일시", anchor="center")
        self.tree.heading("device", text="디바이스 정보", anchor="center")
        self.tree.heading("memo", text="메모", anchor="center")
        self.tree.heading("activation_count", text="활성화 횟수", anchor="center")
        
        # 컬럼 설정 - 중앙 정렬 추가
        self.tree.column("serial", width=250, anchor="center")
        self.tree.column("status", width=100, anchor="center")
        self.tree.column("created", width=150, anchor="center")
        self.tree.column("expiry", width=150, anchor="center")
        self.tree.column("device", width=300, anchor="center")
        self.tree.column("memo", width=200, anchor="center")
        self.tree.column("activation_count", width=100, anchor="center")
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.tree.bind('<Button-3>', self.show_context_menu)  # 윈도우 우클릭
        self.tree.bind('<Button-2>', self.show_context_menu)  # 맥 우클릭
        self.tree.bind('<Control-Button-1>', self.show_context_menu)  # 맥 Control+클릭
        self.tree.bind('<Meta-Button-1>', self.show_context_menu)  # 맥 Command+클릭 (추가)
        self.tree.bind('<Double-1>', self.edit_memo)
        
        # 디바이스 정보 클릭 이벤트 바인딩
        self.tree.bind('<ButtonRelease-1>', self.check_device_info_click)
        
        # 상태별 색상 태그 설정
        self.tree.tag_configure('expired', foreground='red')  # 만료됨
        self.tree.tag_configure('blacklisted', foreground='gray')  # 블랙리스트
        self.tree.tag_configure('active', foreground='green')  # 사용가능
        self.tree.tag_configure('disabled', foreground='orange')  # 사용불가
        self.tree.tag_configure('in_use', foreground='blue')  # 사용중
        self.tree.tag_configure('expiring_soon', foreground='#FFA500')  # 만료 예정
    
    def process_background_tasks(self):
        try:
            while True:
                task = self.task_queue.get_nowait()
                task()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_background_tasks)
    
    def check_server_connection(self):
        """서버 연결 상태 확인"""
        try:
            # 원격 서버 연결 확인 모듈 가져오기
            from remote_config import server_config, SERVER_URL
            logging.debug(f"원격 서버 설정 로드: URL={SERVER_URL}")
            
            # 서버 연결 상태 확인
            logging.debug("서버 연결 상태 확인 시작")
            if server_config.check_connection():
                try:
                    # 시리얼 목록 가져오기 API
                    from remote_config import get_all_serials
                    logging.debug("시리얼 목록 로드 시도")
                    serials = get_all_serials()
                    self.server_connected = True  # 서버 연결 상태 업데이트
                    serials_count = len(serials)
                    logging.info(f"시리얼 목록 로드 성공: {serials_count}개")
                    self.status_label.config(
                        text=f"서버 상태: 정상 (등록된 시리얼: {serials_count}개)", 
                        foreground="green"
                    )
                except Exception as serials_error:
                    self.server_connected = True
                    logging.error(f"시리얼 목록 로드 상세 오류: {str(serials_error)}", exc_info=True)
                    self.status_label.config(text="서버 상태: 정상 (시리얼 목록 로드 실패)", foreground="green")
            else:
                self.server_connected = False
                logging.warning("서버 연결 확인 실패")
                self.status_label.config(text="서버 상태: 연결 실패", foreground="red")
        except ImportError as ie:
            # 기존 방식으로 폴백
            logging.warning(f"원격 설정 모듈 가져오기 실패: {str(ie)}, 기본 API 사용")
            try:
                logging.debug(f"기본 API 사용 시도: {BLOG_SERVER_URL}/api/health")
                response = requests.get(f"{BLOG_SERVER_URL}/api/health", timeout=10)
                logging.debug(f"Health API 응답: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        # 시리얼 목록 가져오기 API
                        from remote_config import get_all_serials
                        logging.debug("시리얼 목록 로드 시도")
                        serials = get_all_serials()
                        self.server_connected = True  # 서버 연결 상태 업데이트
                        serials_count = len(serials)
                        logging.info(f"시리얼 목록 로드 성공: {serials_count}개")
                        self.status_label.config(
                            text=f"서버 상태: 정상 (등록된 시리얼: {serials_count}개)", 
                            foreground="green"
                        )
                    except Exception as serials_error:
                        self.server_connected = True
                        logging.error(f"시리얼 목록 로드 상세 오류: {str(serials_error)}", exc_info=True)
                        self.status_label.config(text="서버 상태: 정상 (시리얼 목록 로드 실패)", foreground="green")
                else:
                    self.server_connected = False
                    logging.warning("서버 연결 확인 실패")
                    self.status_label.config(text="서버 상태: 연결 실패", foreground="red")
                    try:
                        logging.debug("시리얼 목록 로드 시도")
                        serials = get_all_serials()
                        self.server_connected = True  # 서버 연결 상태 업데이트
                        serials_count = len(serials)
                        logging.info(f"시리얼 목록 로드 성공: {serials_count}개")
                    except Exception as serials_error:
                        self.server_connected = False
                        logging.error(f"시리얼 목록 로드 실패: {str(serials_error)}", exc_info=True)
                        self.status_label.config(
                            text=f"서버 상태: 정상 (등록된 시리얼: {serials_count}개)", 
                            foreground="green"
                        )
                    except Exception as serials_error:
                        self.server_connected = True
                        logging.error(f"시리얼 목록 로드 상세 오류: {str(serials_error)}", exc_info=True)
                        self.status_label.config(text="서버 상태: 정상 (시리얼 목록 로드 실패)", foreground="red")
                        self.server_connected = False
                        logging.warning("서버 연결 확인 실패")
                        self.status_label.config(text="서버 상태: 연결 실패", foreground="red")
                # 기존 방식으로 폴백
                logging.warning(f"원격 설정 모듈 가져오기 실패: {str(ie)}, 기본 API 사용")
                try:
                    logging.debug(f"기본 API 사용 시도: {BLOG_SERVER_URL}/api/health")
                    response = requests.get(f"{BLOG_SERVER_URL}/api/health", timeout=10)
                    logging.debug(f"Health API 응답: {response.status_code}")
                except requests.RequestException as req_error:
                    self.server_connected = False
                    logging.error(f"기본 API 요청 오류: {str(req_error)}", exc_info=True)
                    self.status_label.config(text="서버 상태: 연결 실패", foreground="red")
                    return  # 오류 발생 시 함수 종료
                if response.status_code == 200:
                    try:
                        # 시리얼 목록 가져오기 API
                        logging.debug(f"시리얼 목록 API 호출 시도: {BLOG_SERVER_URL}/api/serials")
                        serials_response = requests.get(f"{BLOG_SERVER_URL}/api/serials", timeout=10)
                        logging.debug(f"시리얼 API 응답: {serials_response.status_code}")
                    except requests.RequestException as serials_req_error:
                        self.server_connected = False
                        logging.error(f"시리얼 목록 API 요청 오류: {str(serials_req_error)}", exc_info=True)
                        self.status_label.config(text="서버 상태: 연결 실패", foreground="red")
                        return
                            
                    if serials_response.status_code == 200:
                                self.server_connected = True  # 서버 연결 상태 업데이트
                                server_data = serials_response.json()
                                serials_count = len(server_data.get("serials", []))
                                logging.info(f"시리얼 목록 로드 성공: {serials_count}개")
                                self.status_label.config(
                                    text=f"서버 상태: 정상 (등록된 시리얼: {serials_count}개)", 
                                    foreground="green"
                                )
                                # GitHub 백업 API 호출 시도
                                try:
                                    backup_response = requests.post(f"{BLOG_SERVER_URL}/api/backup", timeout=30)
                                    if backup_response.status_code == 200:
                                        logging.info("GitHub 백업 성공")
                                    else:
                                        logging.warning(f"GitHub 백업 요청 실패: {backup_response.status_code}")
                                except Exception as backup_error:
                                    logging.warning(f"GitHub 백업 요청 오류: {str(backup_error)}")
                                    self.server_connected = False
                                    logging.warning(f"시리얼 목록 API 응답 오류: {serials_response.status_code}")
                                    try:
                                        logging.debug(f"응답 내용: {serials_response.text[:200]}")
                                    except Exception as e:
                                        logging.error(f"응답 내용 로깅 오류: {str(e)}", exc_info=True)
                                        self.status_label.config(text="서버 상태: 정상 (시리얼 목록 로드 실패)", foreground="red")
                                    except Exception as e:
                                        self.server_connected = False
                                        logging.error(f"시리얼 목록 API 호출 상세 오류: {str(e)}", exc_info=True)
                                        self.status_label.config(text="서버 상태: 연결 실패", foreground="red")
                                        logging.warning(f"서버 Health API 응답 오류: {response.status_code}")
                                        try:
                                            logging.debug(f"응답 내용: {response.text[:200]}")
                                        except Exception as log_error:
                                            logging.error(f"응답 내용 로깅 오류: {str(log_error)}", exc_info=True)
                                            self.status_label.config(text="서버 상태: 응답 오류", foreground="red")
                                        self.server_connected = False
            logging.error(f"서버 연결 확인 상세 오류: {str(e)}", exc_info=True)
            self.status_label.config(text="서버 상태: 연결 실패", foreground="red")
        
        # 60초 후 다시 확인
        if self.is_standalone:
            self.root.after(60000, self.check_server_connection)
        elif self.parent:
            self.parent.after(60000, self.check_server_connection)
    
    def create_serial(self):
        for window in (self.parent if self.parent else self.root).winfo_children():
            if isinstance(window, tk.Toplevel) and window.title() == "시리얼 생성":
                window.lift()
                return
        
        create_window = tk.Toplevel(self.parent if self.parent else self.root)
        create_window.title("시리얼 생성")
        create_window.geometry("400x350")
        create_window.resizable(False, False)
        
        input_frame = ttk.LabelFrame(create_window, text="시리얼 정보")
        input_frame.pack(padx=10, pady=10, fill=tk.X)
        
        date_frame = ttk.LabelFrame(input_frame, text="만료일 선택")
        date_frame.pack(padx=5, pady=5, fill=tk.X)
        
        calendar_frame = ttk.Frame(date_frame)
        calendar_frame.pack(pady=5)
        
        ttk.Label(calendar_frame, text="날짜 선택:").pack(side=tk.LEFT, padx=5)
        date_entry = DateEntry(calendar_frame, width=12, background='darkblue',
                               foreground='white', borderwidth=2)
        date_entry.pack(side=tk.LEFT, padx=5)
        
        period_frame = ttk.Frame(date_frame)
        period_frame.pack(pady=5)
        
        ttk.Label(period_frame, text="기간 선택:").pack(side=tk.LEFT, padx=5)
        periods = [("30일", 30), ("90일", 90), ("180일", 180), ("1년", 365)]
        
        def apply_period(days):
            new_date = datetime.now().date() + timedelta(days=days)
            date_entry.set_date(new_date)
        
        for label, days in periods:
            ttk.Button(period_frame, text=label,
                       command=lambda d=days: apply_period(d)).pack(side=tk.LEFT, padx=2)
        
        memo_frame = ttk.Frame(input_frame)
        memo_frame.pack(pady=10, fill=tk.X)
        ttk.Label(memo_frame, text="메모:").pack(side=tk.LEFT, padx=5)
        memo_entry = ttk.Entry(memo_frame, width=30)
        memo_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        progress_var = tk.StringVar(value="준비")
        progress_label = ttk.Label(create_window, textvariable=progress_var)
        progress_label.pack(pady=10)
        
        def validate_and_create():
            try:
                # 서버 연결 확인
                if not hasattr(self, 'server_connected') or not self.server_connected:
                    # 서버 연결 확인 시도
                    try:
                        progress_var.set("서버 연결 확인 중...")
                        create_window.update()
                        
                        # remote_config 모듈 사용 시도
                        try:
                            from remote_config import server_config
                            if server_config.check_connection():
                                self.server_connected = True
                            else:
                                raise Exception("서버 연결 실패")
                        except ImportError:
                            # 기존 방식으로 폴백
                            response = requests.get(f"{BLOG_SERVER_URL}/api/health", timeout=5)
                            if response.status_code != 200:
                                raise Exception(f"서버 응답 코드: {response.status_code}")
                            
                            self.server_connected = True
                    except Exception as conn_error:
                        progress_var.set("서버 연결 실패")
                        create_window.update()
                        
                        logging.error(f"서버 연결 오류: {str(conn_error)}")
                        if not messagebox.askyesno("서버 연결 오류", 
                            "서버에 연결할 수 없습니다. 로컬에만 시리얼을 생성하시겠습니까?\n" + 
                            "주의: 로컬에만 생성된 시리얼은 다른 기기에서 검증되지 않습니다."):
                            return
                
                expiry_date = date_entry.get_date()
                if expiry_date < datetime.now().date():
                    raise ValueError("만료일은 현재 날짜 이후여야 합니다.")
                
                progress_var.set("디바이스 정보 수집 중...")
                create_window.update()
                
                serial = str(uuid.uuid4())
                device_info = get_device_info()
            
                # 디바이스 정보가 없더라도 빈 객체로 계속 진행
                if not device_info:
                    logging.warning("디바이스 정보를 가져올 수 없어 기본값을 사용합니다.")
                    device_info = {
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
                
                # 서버에 등록 시도
                server_registration_success = False
                if self.server_connected:
                    try:
                        progress_var.set("서버에 등록 중...")
                        create_window.update()
                        from remote_config import create_serial as remote_create_serial
                    except ImportError:
                        logging.error("remote_config 모듈을 가져올 수 없습니다.")
                        return
                            
                            # 시리얼 데이터 준비
                            serial_data = {
                                "serial_number": serial,
                                "expiry_date": expiry_date.strftime('%Y-%m-%d'),
                                "memo": memo_entry.get(),
                                "device_info": {"hostname": "auto-generated"}
                            }
                            }
                            
                            # 원격 함수 호출
                            result = remote_create_serial(serial_data)
                            
                            if result.get('success', False):
                                server_registration_success = True
                                logging.info(f"서버 등록 성공: {result}")
                                
                                # GitHub 백업 API 호출 시도
                                try:
                                    backup_response = requests.post(f"{BLOG_SERVER_URL}/api/backup", timeout=30)
                                    if backup_response.status_code == 200:
                                        logging.info("GitHub 백업 성공")
                                    else:
                                        logging.warning(f"GitHub 백업 요청 실패: {backup_response.status_code}")
                                except Exception as backup_error:
                                    logging.warning(f"GitHub 백업 요청 오류: {str(backup_error)}")
                            else:
                                error_text = result.get('message', '알 수 없는 오류')
                                logging.error(f"서버 등록 실패: {error_text}")
                                if not messagebox.askyesno("서버 등록 실패", 
                                    f"서버에 시리얼을 등록하지 못했습니다. 로컬에만 저장하시겠습니까?\n오류: {error_text}"):
                                    return
                        except ImportError:
                            # remote_config 모듈을 가져올 수 없는 경우 직접 API 호출
                            logging.warning("remote_config 모듈을 가져올 수 없어 직접 API 호출")
                            
                            # 간소화된 요청 데이터 사용
                response = requests.post(
                    f"{BLOG_SERVER_URL}/api/register",
                    json={
                        "serial_number": serial,
                        "expiry_date": expiry_date.strftime('%Y-%m-%d'),
                                    "memo": memo_entry.get(),
                                    "device_info": {"hostname": "auto-generated"}
                    },
                    timeout=30
                )
                            
                            logging.info(f"서버 응답: {response.status_code} - {response.text}")
                            
                            if response.status_code == 200:
                                server_registration_success = True
                            else:
                                error_text = response.text
                                logging.error(f"서버 등록 실패: {response.status_code} - {error_text}")
                                if not messagebox.askyesno("서버 등록 실패", 
                                    f"서버에 시리얼을 등록하지 못했습니다. 로컬에만 저장하시겠습니까?\n오류 코드: {response.status_code}"):
                                    return
                    except Exception as req_error:
                        logging.error(f"요청 오류: {str(req_error)}", exc_info=True)
                        if not messagebox.askyesno("서버 등록 실패", 
                            f"서버에 시리얼을 등록하지 못했습니다. 로컬에만 저장하시겠습니까?\n오류: {str(req_error)}"):
                            return
                else:
                # 로컬 DB에 저장
                    progress_var.set("로컬 DB에 저장 중...")
                    create_window.update()
                    
                self.cursor.execute('''
                    INSERT INTO blog_serials (
                        serial_number, status, created_date, expiry_date,
                        device_info, memo, activation_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    serial, "사용가능",
                    datetime.now().strftime('%Y-%m-%d'),
                    expiry_date.strftime('%Y-%m-%d'),
                        '{}',
                    memo_entry.get(),
                    0
                ))
                self.conn.commit()
                
                self.refresh_serial_list()
                create_window.destroy()
                
                # 결과 표시
                result_window = tk.Toplevel(self.parent if self.parent else self.root)
                result_window.title("시리얼 생성 완료")
                result_window.geometry("500x300")
                
                text_widget = tk.Text(result_window, wrap=tk.WORD, padx=10, pady=10)
                text_widget.pack(fill=tk.BOTH, expand=True)
                
                text_widget.insert(tk.END, f"시리얼 번호: {serial}\n\n")
                text_widget.insert(tk.END, f"만료일: {expiry_date.strftime('%Y-%m-%d')}\n\n")
                if server_registration_success:
                    text_widget.insert(tk.END, "서버 등록: 성공\n\n")
                else:
                    text_widget.insert(tk.END, "서버 등록: 실패 (로컬에만 저장됨)\n\n")
                text_widget.insert(tk.END, "디바이스 정보: 시리얼 생성 시에는 기록되지 않습니다.\n")
                text_widget.insert(tk.END, "사용자가 프로그램에서 시리얼 인증 시 자동으로 수집됩니다.\n")
                
                text_widget.configure(state='disabled')
                
                ttk.Button(result_window, text="확인",
                           command=result_window.destroy).pack(pady=10)
                
            except Exception as e:
                logging.error(f"시리얼 생성 오류: {e}")
                messagebox.showerror("오류", f"시리얼 생성 중 오류가 발생했습니다.\n{str(e)}")
                progress_var.set("오류 발생")
        
        button_frame = ttk.Frame(create_window)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="생성", command=validate_and_create).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="취소", command=create_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def backup_database(self):
        """데이터베이스 백업"""
        try:
            backup_dir = os.path.join(os.path.dirname(get_db_path()), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_file = os.path.join(
                backup_dir, f'blogs_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
            )
            
            self.conn.close()
            
            import shutil
            shutil.copy2(get_db_path(), backup_file)
            
            self.conn = sqlite3.connect(get_db_path())
            self.cursor = self.conn.cursor()
            
            messagebox.showinfo("성공", f"데이터베이스가 백업되었습니다.\n위치: {backup_file}")
        except Exception as e:
            logging.error(f"데이터베이스 백업 오류: {e}")
            messagebox.showerror("오류", "데이터베이스 백업 중 오류가 발생했습니다.")
        
    def refresh_serial_list(self):
        """시리얼 목록 새로고침"""
        try:
            # 트리뷰의 현재 내용 삭제
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # 서버에서 데이터 가져오기 시도
            if hasattr(self, 'server_connected') and self.server_connected:
                try:
                    # 원격 설정 모듈 사용 시도
                    try:
                        from remote_config import get_all_serials
                        logging.debug("원격 설정 모듈을 사용하여 시리얼 목록 가져오기 시도")
                        serials = get_all_serials()
                        if serials:
                            # 서버 데이터 포맷 확인
                            logging.debug(f"서버 데이터 확인: {len(serials)}개 항목 수신")
            
                            # 서버 데이터 사용
                            for serial in serials:
                                serial_number = serial.get("serial_number", "")
                                status = serial.get("status", "알 수 없음")
                                expiry_date = serial.get("expiry_date", "")
                                device_info = serial.get("device_info", {})
                                memo = serial.get("memo", "")
                                is_blacklisted = serial.get("is_blacklisted", False)
                                activation_count = serial.get("activation_count", 0)
                                
                                # 디바이스 정보가 있으면 '사용중' 상태로 표시
                                if device_info and device_info != {} and status == "사용가능":
                                    status = "사용중"
                                
                                # 블랙리스트인 경우 상태 표시
                                if is_blacklisted:
                                    status = "블랙리스트"
                                
                                # 만료일로부터 남은 일수 계산
                                remaining_days = 0
                                expiry_text = ""
                                
                                if expiry_date:
                                    try:
                                        expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
                                        today = datetime.now().date()
                                        remaining_days = (expiry - today).days
                                        
                                        expiry_text = f"{expiry_date} ({remaining_days}일 남음)"
                                        if remaining_days < 0:
                                            expiry_text = f"{expiry_date} (만료됨)"
                                            status = "만료됨"  # 만료된 경우 상태 표시
                                        elif remaining_days <= 30:
                                            # 만료 30일 이내는 '만료 예정'으로 표시
                                            status = "만료 예정"
                                    except Exception as date_err:
                                        logging.warning(f"만료일 형식 오류: {expiry_date}, {str(date_err)}")
                                        expiry_text = expiry_date
                                
                                # 디바이스 정보 형식화
                                device_info_text = self.format_device_info(json.dumps(device_info, ensure_ascii=False)) if device_info else ""
                                
                                # 트리뷰에 추가
                                self.tree.insert("", "end", values=(
                                    serial_number, status, "", expiry_text, 
                                    device_info_text, memo, activation_count
                                ))
                            
                            # 성공적으로 새로고침 완료
                            self.status_label.config(text=f"서버에서 새로고침 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                            return
                        else:
                            logging.warning("서버에서 시리얼 데이터를 가져왔으나 비어있습니다.")
                    except ImportError as ie:
                        logging.warning(f"원격 설정 모듈 가져오기 실패: {str(ie)}")
                    
                    # 기존 방식으로 폴백
                    logging.debug(f"기본 API 사용 시도: {BLOG_SERVER_URL}/api/serials")
                    response = requests.get(f"{BLOG_SERVER_URL}/api/serials", timeout=10)
                    
                    if response.status_code == 200:
                        try:
                            serials_data = response.json()
                            logging.debug(f"시리얼 데이터 응답: {len(serials_data.get('serials', []))}개 항목")
                            
                            # 서버 데이터 사용
                            for serial in serials_data.get('serials', []):
                                serial_number = serial.get("serial_number", "")
                                status = serial.get("status", "알 수 없음")
                                expiry_date = serial.get("expiry_date", "")
                                device_info = serial.get("device_info", {})
                                memo = serial.get("memo", "")
                                is_blacklisted = serial.get("is_blacklisted", False)
                                activation_count = serial.get("activation_count", 0)
                                
                                # 디바이스 정보가 있으면 '사용중' 상태로 표시
                                if device_info and device_info != {} and status == "사용가능":
                                    status = "사용중"
                                
                                # 블랙리스트인 경우 상태 표시
                if is_blacklisted:
                                    status = "블랙리스트"
                                
                                # 만료일로부터 남은 일수 계산
                                remaining_days = 0
                                expiry_text = ""
                                
                                if expiry_date:
                                    try:
                                        expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
                                        today = datetime.now().date()
                                        remaining_days = (expiry - today).days
                                        
                                        expiry_text = f"{expiry_date} ({remaining_days}일 남음)"
                                        if remaining_days < 0:
                                            expiry_text = f"{expiry_date} (만료됨)"
                                            status = "만료됨"  # 만료된 경우 상태 표시
                                        elif remaining_days <= 30:
                                            # 만료 30일 이내는 '만료 예정'으로 표시
                                            status = "만료 예정"
                                    except Exception as date_err:
                                        logging.warning(f"만료일 형식 오류: {expiry_date}, {str(date_err)}")
                                        expiry_text = expiry_date
                                
                                # 디바이스 정보 형식화
                                device_info_text = self.format_device_info(json.dumps(device_info, ensure_ascii=False)) if device_info else ""
                                
                                # 트리뷰에 추가
                                self.tree.insert("", "end", values=(
                                    serial_number, status, "", expiry_text, 
                                    device_info_text, memo, activation_count
                                ))
                            
                            # 성공적으로 새로고침 완료
                            self.status_label.config(text=f"서버에서 새로고침 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                            return
                        except Exception as parse_error:
                            logging.error(f"서버 응답 파싱 오류: {str(parse_error)}", exc_info=True)
                            # 파싱 오류 발생 시 응답 내용 로깅
                            try:
                                logging.debug(f"서버 응답 내용: {response.text[:500]}")
                            except:
                                pass
                else:
                        logging.warning(f"시리얼 목록 API 오류 응답: {response.status_code}")
                        try:
                            logging.debug(f"오류 응답 내용: {response.text[:500]}")
                        except:
                            pass
                except Exception as e:
                    logging.error(f"서버에서 시리얼 목록 가져오기 실패: {str(e)}", exc_info=True)
                    # 서버에서 가져오기 실패하면 로컬 DB 사용
                    self.status_label.config(text=f"서버 조회 실패, 로컬 데이터 사용: {str(e)[:50]}")
            
            # 로컬 데이터베이스에서 시리얼 목록 가져오기
            logging.debug("로컬 데이터베이스에서 시리얼 목록 로드")
            conn = sqlite3.connect(get_db_path())
            c = conn.cursor()
            c.execute('''
                SELECT serial_number, status, created_date, expiry_date, device_info, memo, is_blacklisted, activation_count 
                FROM blog_serials 
                WHERE is_deleted = 0
                ORDER BY created_date DESC
            ''')
            
            rows = c.fetchall()
            conn.close()
            
            for row in rows:
                try:
                    serial_number, status, created_date, expiry_date, device_info_str, memo, is_blacklisted, activation_count = row
                    
                    # 디바이스 정보가 있으면 '사용중' 상태로 표시
                    if device_info_str and device_info_str != '{}' and status == "사용가능":
                        status = "사용중"
                    
                    # 블랙리스트인 경우 상태 표시
                    if is_blacklisted:
                        status = "블랙리스트"
                    
                    # 만료일로부터 남은 일수 계산
                    remaining_days = 0
                    expiry_text = ""
                    
                    if expiry_date:
                        try:
                            expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
                            today = datetime.now().date()
                            remaining_days = (expiry - today).days
                            
                            expiry_text = f"{expiry_date} ({remaining_days}일 남음)"
                            if remaining_days < 0:
                                expiry_text = f"{expiry_date} (만료됨)"
                                status = "만료됨"  # 만료된 경우 상태 표시
                            elif remaining_days <= 30:
                                # 만료 30일 이내는 '만료 예정'으로 표시
                                status = "만료 예정"
                        except Exception as date_err:
                            logging.warning(f"로컬 DB 만료일 형식 오류: {expiry_date}, {str(date_err)}")
                            expiry_text = expiry_date
                    
                    # 디바이스 정보 형식화
                    device_info_text = self.format_device_info(device_info_str) if device_info_str else ""
                    
                    # 트리뷰에 추가
                    self.tree.insert("", "end", values=(
                        serial_number, status, created_date, expiry_text, 
                        device_info_text, memo, activation_count
                    ))
                except Exception as row_error:
                    logging.error(f"로컬 DB 행 처리 오류: {str(row_error)}", exc_info=True)
                    continue
            
            # 새로고침 시간 업데이트
            self.status_label.config(text=f"로컬 DB 새로고침 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            logging.error(f"시리얼 목록 새로고침 중 오류 발생: {str(e)}", exc_info=True)
            self.status_label.config(text=f"새로고침 오류: {str(e)[:50]}")
    
    def format_device_info(self, device_info_str):
        """디바이스 정보 문자열 포맷팅"""
        try:
            if isinstance(device_info_str, str):
                info = json.loads(device_info_str)
            else:
                info = device_info_str
            
            if info and any(info.values()):
                # 간단한 요약 정보 반환
                hostname = info.get('hostname', '알 수 없음')
                os_name = info.get('os_name', '')
                os_version = info.get('os_version', '')
                model = info.get('system_model', '')
                
                # OS 이름과 버전 조합
                os_info = f"{os_name} {os_version}" if os_name else "알 수 없는 OS"
                
                return f"{hostname} ({model}, {os_info})"
            return "미등록"
        except:
            return "미등록"
    
    def check_expiring_serials(self):
        """만료 임박 시리얼 확인"""
        try:
            self.cursor.execute("""
                SELECT serial_number, expiry_date 
                FROM blog_serials 
                WHERE is_deleted = 0 
                AND status = '사용가능'
                AND DATE(expiry_date) <= DATE('now', '+7 days')
            """)
            rows = self.cursor.fetchall()
            
            if rows:
                expiring_serials = []
                for serial, expiry_date in rows:
                    exp_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
                    days_left = (exp_date - datetime.now().date()).days
                    expiring_serials.append((serial, days_left))
                
                if expiring_serials:
                    message = "만료 임박 시리얼:\n\n"
                    for serial, days in expiring_serials:
                        message += f"시리얼: {serial}\n남은 기간: {days}일\n\n"
                    self.show_notification("만료 임박 알림", message)
        except Exception as e:
            logging.error(f"만료 체크 오류: {e}")
        
        self.root.after(3600000, self.check_expiring_serials)
    
    def show_notification(self, title, message):
        """알림 표시 (맥 OS 버전)"""
        try:
            # 맥 OS 알림 표시 (osascript 사용)
            script = f'''
            osascript -e 'display notification "{message}" with title "{title}"'
            '''
            os.system(script)
        except:
            # 기본 대화상자로 폴백
            messagebox.showwarning(title, message)
    
    def edit_expiry_date(self):
        """만료일 수정"""
        selected = self.tree.selection()
        if not selected:
            return
        
        parent = self.parent if not self.is_standalone else self.root
        for window in parent.winfo_children():
            if isinstance(window, tk.Toplevel) and window.title() == "만료일 수정":
                window.lift()
                return
        
        edit_window = tk.Toplevel(parent)
        edit_window.title("만료일 수정")
        edit_window.geometry("400x300")
        edit_window.resizable(False, False)
        
        date_frame = ttk.LabelFrame(edit_window, text="만료일 선택")
        date_frame.pack(padx=10, pady=5, fill=tk.X)
        
        calendar_frame = ttk.Frame(date_frame)
        calendar_frame.pack(pady=5)
        
        ttk.Label(calendar_frame, text="날짜 선택:").pack(side=tk.LEFT, padx=5)
        date_entry = DateEntry(calendar_frame, width=12, background='darkblue',
                             foreground='white', borderwidth=2)
        date_entry.pack(side=tk.LEFT, padx=5)
        
        period_frame = ttk.Frame(date_frame)
        period_frame.pack(pady=5)
        
        ttk.Label(period_frame, text="기간 선택:").pack(side=tk.LEFT, padx=5)
        periods = [("30일", 30), ("90일", 90), ("180일", 180), ("1년", 365)]
        
        def apply_period(days):
            new_date = datetime.now().date() + timedelta(days=days)
            date_entry.set_date(new_date)
        
        for label, days in periods:
            ttk.Button(period_frame, text=label,
                     command=lambda d=days: apply_period(d)).pack(side=tk.LEFT, padx=2)
        
        def update_expiry():
            try:
                new_date = date_entry.get_date().strftime('%Y-%m-%d')
                current_date = datetime.now().date()
                
                for item in selected:
                    serial = self.tree.item(item)['values'][0]
                    
                    # 새로운 만료일에 따른 상태 결정
                    expiry_date = datetime.strptime(new_date, '%Y-%m-%d').date()
                    
                    # 블랙리스트 상태 체크
                    self.cursor.execute("SELECT is_blacklisted FROM blog_serials WHERE serial_number = ?", (serial,))
                    is_blacklisted = self.cursor.fetchone()[0]
                    
                    if is_blacklisted:
                        new_status = '블랙리스트'
                    else:
                        if current_date >= expiry_date:
                            new_status = '만료됨'
                        elif current_date + timedelta(days=7) >= expiry_date:
                            new_status = '만료 예정'
                        else:
                            new_status = '사용가능'
                    
                    # 로컬 DB 업데이트
                    self.cursor.execute("""
                        UPDATE blog_serials 
                        SET expiry_date = ?, status = ?
                        WHERE serial_number = ?
                    """, (new_date, new_status, serial))
                    self.conn.commit()
                    
                    # UI 즉시 업데이트
                    values = list(self.tree.item(item)['values'])
                    values[1] = new_status  # 상태 업데이트
                    values[3] = new_date    # 만료일 업데이트
                    
                    # 상태에 따른 태그 설정
                    if new_status == '만료됨':
                        tag = 'expired'
                    elif new_status == '만료 예정':
                        tag = 'expiring_soon'
                    elif new_status == '블랙리스트':
                        tag = 'blacklisted'
                    else:
                        tag = 'active'
                    
                    self.tree.item(item, values=values, tags=(tag,))
                
                edit_window.destroy()
                messagebox.showinfo("성공", "만료일이 업데이트되었습니다.")
            
            except Exception as e:
                logging.error(f"만료일 수정 오류: {e}")
                messagebox.showerror("오류", f"만료일 수정 중 오류가 발생했습니다.\n{str(e)}")
                # 오류 발생 시 전체 새로고침
                self.refresh_serial_list()
        
        button_frame = ttk.Frame(edit_window)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="수정", command=update_expiry).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="취소", command=edit_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def edit_memo(self, event):
        """메모 수정"""
        selected = self.tree.selection()
        if not selected:
            return
        
        item = selected[0]
        current_values = self.tree.item(item)['values']
        current_memo = current_values[5]
        
        parent = self.parent if not self.is_standalone else self.root
        memo = simpledialog.askstring("메모 수정", "메모를 입력하세요:", initialvalue=current_memo, parent=parent)
        if memo is not None:
            serial = current_values[0]
            try:
                # 로컬 메모 테이블 업데이트
                self.cursor.execute("""
                    INSERT OR REPLACE INTO blog_local_memos (serial_number, memo)
                    VALUES (?, ?)
                """, (serial, memo))
                
                # 메인 테이블 업데이트
                self.cursor.execute("UPDATE blog_serials SET memo = ? WHERE serial_number = ?", (memo, serial))
                self.conn.commit()
                
                # UI 업데이트
                new_values = list(current_values)
                new_values[5] = memo
                self.tree.item(item, values=new_values)
                messagebox.showinfo("성공", "메모가 수정되었습니다.")
            except Exception as e:
                logging.error(f"메모 수정 오류: {e}")
                messagebox.showerror("오류", "메모 수정 중 오류가 발생했습니다.")
    
    def set_blacklist(self):
        """시리얼을 블랙리스트로 설정"""
        selected = self.tree.selection()
        if not selected:
            return
        
        if not messagebox.askyesno("확인", "선택한 시리얼을 블랙리스트로 설정하시겠습니까?"):
            return
            
        try:
            for item in selected:
                serial = self.tree.item(item)['values'][0]
                
                # 서버 API 연동
                response = requests.post(f"{BLOG_SERVER_URL}/api/serials/blacklist", json={
                    "serial_number": serial,
                    "action": "add"
                }, timeout=30)
                
                if response.status_code == 200:
                # 로컬 DB 업데이트
                self.cursor.execute("""
                    UPDATE blog_serials 
                    SET status = '블랙리스트', is_blacklisted = 1 
                    WHERE serial_number = ?
                """, (serial,))
                else:
                    raise ValueError(f"서버 응답 오류: {response.status_code}")
            
            self.conn.commit()
            self.refresh_serial_list()
            messagebox.showinfo("성공", "선택한 시리얼이 블랙리스트로 설정되었습니다.")
        except Exception as e:
            logging.error(f"블랙리스트 설정 오류: {e}")
            messagebox.showerror("오류", f"블랙리스트 설정 중 오류가 발생했습니다.\n{str(e)}")
    
    def unset_blacklist(self):
        """블랙리스트 해제"""
        selected = self.tree.selection()
        if not selected:
            return
        
        if not messagebox.askyesno("확인", "선택한 시리얼의 블랙리스트를 해제하시겠습니까?"):
            return
        
        try:
            for item in selected:
                serial = self.tree.item(item)['values'][0]
                
                # 서버 API 연동
                response = requests.post(f"{BLOG_SERVER_URL}/api/serials/blacklist", json={
                    "serial_number": serial,
                    "action": "remove"
                }, timeout=30)
                
                if response.status_code == 200:
                # 만료일로 상태 결정
                self.cursor.execute("SELECT expiry_date FROM blog_serials WHERE serial_number = ?", (serial,))
                    result = self.cursor.fetchone()
                    expiry_date_str = result[0] if result else None
                
                    new_status = '사용가능'
                if expiry_date_str:
                        try:
                    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                    current_date = datetime.now().date()
                    
                    if current_date >= expiry_date:
                        new_status = '만료됨'
                    elif current_date + timedelta(days=7) >= expiry_date:
                        new_status = '만료 예정'
                    else:
                        new_status = '사용가능'
                        except:
                            new_status = '사용가능'
                else:
                    new_status = '사용가능'
                
                # 로컬 DB 업데이트
                self.cursor.execute("""
                    UPDATE blog_serials 
                    SET status = ?, is_blacklisted = 0 
                    WHERE serial_number = ?
                """, (new_status, serial))
                else:
                    raise ValueError(f"서버 응답 오류: {response.status_code}")
            
            self.conn.commit()
            self.refresh_serial_list()
            messagebox.showinfo("성공", "블랙리스트가 해제되었습니다.")
        except Exception as e:
            logging.error(f"블랙리스트 해제 오류: {e}")
            messagebox.showerror("오류", f"블랙리스트 해제 중 오류가 발생했습니다.\n{str(e)}")
    
    def check_serial_on_server(self):
        """서버에서 시리얼 상태 확인"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("알림", "확인할 시리얼을 선택해주세요.")
            return
        
        try:
            parent = self.parent if not self.is_standalone else self.root
            results = []
            
            # remote_config 모듈 사용 시도
            try:
                from remote_config import server_config, SERVER_URL
                # 서버 연결 확인
                if not server_config.check_connection():
                    messagebox.showerror("서버 오류", "서버에 연결할 수 없습니다.")
                    return
                
            for item in selected:
                serial = self.tree.item(item)['values'][0]
                
                    # 직접 API 호출 (get_serial 함수가 없으므로)
                    try:
                        response = requests.get(f"{SERVER_URL}/api/serials/{serial}", timeout=10)
                if response.status_code == 200:
                    server_data = response.json()
                    results.append(f"시리얼: {serial}\n상태: 서버에 존재함\n상태: {server_data['status']}\n")
                elif response.status_code == 404:
                    results.append(f"시리얼: {serial}\n상태: 서버에 없음\n")
                else:
                    results.append(f"시리얼: {serial}\n상태: 확인 실패 (코드: {response.status_code})\n")
                    except Exception as req_err:
                        results.append(f"시리얼: {serial}\n상태: 확인 실패 (오류: {str(req_err)})\n")
            except ImportError:
                # 기존 방식으로 폴백
                for item in selected:
                    serial = self.tree.item(item)['values'][0]
                    
                    # 서버 API 연동
                    response = requests.get(f"{BLOG_SERVER_URL}/api/serials/{serial}", timeout=60)
                    if response.status_code == 200:
                        server_data = response.json()
                        results.append(f"시리얼: {serial}\n상태: 서버에 존재함\n상태: {server_data['status']}\n")
                    elif response.status_code == 404:
                        results.append(f"시리얼: {serial}\n상태: 서버에 없음\n")
                    else:
                        results.append(f"시리얼: {serial}\n상태: 확인 실패 (코드: {response.status_code})\n")
            
            result_window = tk.Toplevel(parent)
            result_window.title("서버 저장 상태")
            result_window.geometry("400x300")
            
            text_widget = tk.Text(result_window, wrap=tk.WORD, padx=10, pady=10)
            text_widget.pack(fill=tk.BOTH, expand=True)
            
            for result in results:
                text_widget.insert(tk.END, result + "\n")
            
            text_widget.configure(state='disabled')
            
            ttk.Button(result_window, text="확인", command=result_window.destroy).pack(pady=10)
        except Exception as e:
            logging.error(f"서버 확인 오류: {e}")
            messagebox.showerror("오류", f"서버 확인 중 오류가 발생했습니다.\n{str(e)}")
    
    def export_to_excel(self):
        """엑셀로 내보내기"""
        try:
            # 검색어와 상태 필터 가져오기
            search_text = self.search_var.get().lower()
            status_filter = self.status_var.get()
            
            # DB에서 시리얼 목록 조회
            query = "SELECT * FROM blog_serials WHERE is_deleted = 0"
            
            if status_filter != "전체":
                query += f" AND status = '{status_filter}'"
            
            query += " ORDER BY created_date DESC"
            
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            
            # 필터링
            filtered_rows = []
            for row in rows:
                serial_number = row[0]
                memo = row[5]
                
                # 검색어 필터링
                if search_text and search_text not in serial_number.lower() and search_text not in memo.lower():
                        continue
                
                filtered_rows.append(row)
            
            if not filtered_rows:
                messagebox.showinfo("알림", "내보낼 데이터가 없습니다.")
                return
            
            # 데이터프레임 생성
            df = pd.DataFrame(filtered_rows, columns=[
                "시리얼 번호", "상태", "등록일시", "만료일시", "디바이스정보", 
                "메모", "삭제여부", "블랙리스트여부", "최종확인일", "활성화횟수"
            ])
            
            # 필요없는 컬럼 제거
            df = df.drop(columns=["삭제여부"])
            
            # 디바이스 정보 포맷팅
            df["디바이스정보"] = df["디바이스정보"].apply(lambda x: self.format_device_info(x))
            
            # 파일 저장 다이얼로그
            parent = self.parent if not self.is_standalone else self.root
            from tkinter import filedialog
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel 파일", "*.xlsx"), ("모든 파일", "*.*")],
                title="엑셀 파일 저장",
                parent=parent
            )
            
            if not file_path:
                return
            
            # 엑셀 파일로 저장
            df.to_excel(file_path, index=False)
            messagebox.showinfo("성공", f"데이터가 성공적으로 내보내졌습니다.\n위치: {file_path}")
            
        except Exception as e:
            logging.error(f"엑셀 내보내기 오류: {e}")
            messagebox.showerror("오류", f"엑셀 내보내기 중 오류가 발생했습니다.\n{str(e)}")
    
    def show_context_menu(self, event):
        """컨텍스트 메뉴 표시"""
        # 클릭한 아이템 선택
        try:
            item = self.tree.identify_row(event.y)
            if item:
                # 이미 선택된 아이템이 아니면 선택 초기화
                if item not in self.tree.selection():
                    self.tree.selection_set(item)
                
                # 컨텍스트 메뉴 표시
                try:
                    self.context_menu.tk_popup(event.x_root, event.y_root)
                finally:
                    self.context_menu.grab_release()
        except Exception as e:
            logging.error(f"컨텍스트 메뉴 표시 오류: {e}")
    
    def copy_selected(self):
        """선택된 항목 복사"""
        selected = self.tree.selection()
        if not selected:
            return
            
        try:
            result = []
            for item in selected:
                values = self.tree.item(item)['values']
                result.append(str(values[0]))  # 시리얼 번호만 복사
                
            # 클립보드에 복사
            parent = self.parent if not self.is_standalone else self.root
            parent.clipboard_clear()
            parent.clipboard_append('\n'.join(result))
            
            messagebox.showinfo("복사 완료", f"{len(result)}개의 시리얼 번호가 클립보드에 복사되었습니다.")
        except Exception as e:
            logging.error(f"복사 오류: {e}")
            messagebox.showerror("오류", "클립보드에 복사하는 중 오류가 발생했습니다.")
    
    def select_all(self):
        """모든 항목 선택"""
        try:
            for item in self.tree.get_children():
                self.tree.selection_add(item)
        except Exception as e:
            logging.error(f"전체 선택 오류: {e}")
    
    def delete_serial(self):
        """시리얼 삭제"""
        selected = self.tree.selection()
        if not selected:
            return
            
        if messagebox.askyesno("삭제 확인", "선택한 시리얼을, 정말 삭제하시겠습니까?\n삭제된 데이터는 복구할 수 없습니다."):
            try:
                for item in selected:
                    serial = self.tree.item(item)['values'][0]
                    # 실제로는 삭제 표시만 함
                    self.cursor.execute("""
                        UPDATE blog_serials 
                        SET is_deleted = 1
                        WHERE serial_number = ?
                    """, (serial,))
                    
                self.conn.commit()
                self.refresh_serial_list()
                messagebox.showinfo("성공", "선택한 시리얼이 삭제되었습니다.")
            except Exception as e:
                logging.error(f"시리얼 삭제 오류: {e}")
                messagebox.showerror("오류", f"시리얼 삭제 중 오류가 발생했습니다.\n{str(e)}")
    
    def check_serial_status(self):
        """시리얼 상태 체크 및 업데이트 (1분마다)"""
        try:
            current_date = datetime.now().date()
            
            for item in self.tree.get_children():
                values = self.tree.item(item)['values']
                if not values:
                    continue
                    
                serial_number = values[0]
                status = values[1]
                expiry_date_str = values[3]
                
                if not expiry_date_str or status in ['만료됨', '블랙리스트']:
                    continue
                
                try:
                    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                    new_status = status
                    
                    # 상태 체크
                    if current_date >= expiry_date:
                        new_status = '만료됨'
                        tag = 'expired'
                    elif current_date + timedelta(days=7) >= expiry_date and status == '사용가능':
                        new_status = '만료 예정'
                        tag = 'expiring_soon'
                    else:
                        continue
                    
                    # 상태가 변경된 경우만 업데이트
                    if new_status != status:
                        # DB 업데이트
                        self.cursor.execute("""
                            UPDATE blog_serials 
                            SET status = ?
                            WHERE serial_number = ?
                        """, (new_status, serial_number))
                        self.conn.commit()
                        
                        # 트리뷰 업데이트
                        values = list(values)
                        values[1] = new_status
                        self.tree.item(item, values=values, tags=(tag,))
                except ValueError:
                    continue
            
        except Exception as e:
            logging.error(f"상태 체크 오류: {e}")
        
        # 1분 후에 다시 체크
        if self.is_standalone:
            self.root.after(60000, self.check_serial_status)
    
    def update_time(self):
        """현재 시간 업데이트"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.time_label.config(text=f"현재 시간: {current_time}")
        if self.is_standalone:
            self.root.after(1000, self.update_time)  # 시간 표시만 1초마다 업데이트
    
    def run(self):
        """애플리케이션 실행 (독립 실행 모드에서만 호출)"""
        if self.is_standalone:
            self.root.mainloop()

    def show_device_info(self, event):
        """디바이스 정보 상세 보기"""
        try:
            item = self.tree.identify_row(event.y)
            if not item:
                return
                
            # 클릭한 열이 디바이스 정보 열인지 확인
            column = self.tree.identify_column(event.x)
            if column != "#5":  # 디바이스 정보는 5번 컬럼
                return
            
            # 시리얼 번호와 디바이스 정보 가져오기
            values = self.tree.item(item)['values']
            serial = values[0]
            
            # DB에서 디바이스 정보 가져오기
            self.cursor.execute("SELECT device_info FROM blog_serials WHERE serial_number = ?", (serial,))
            result = self.cursor.fetchone()
            
            if not result or not result[0]:
                messagebox.showinfo("알림", "등록된 디바이스 정보가 없습니다.")
                return
                
            device_info = json.loads(result[0])
            
            # 디바이스 정보 표시 창
            parent = self.parent if not self.is_standalone else self.root
            info_window = tk.Toplevel(parent)
            info_window.title(f"디바이스 정보: {serial}")
            info_window.geometry("500x400")
            
            # 텍스트 영역
            text_widget = tk.Text(info_window, wrap=tk.WORD, padx=10, pady=10)
            text_widget.pack(fill=tk.BOTH, expand=True)
            
            # 정보 추가
            text_widget.insert(tk.END, f"시리얼 번호: {serial}\n\n")
            text_widget.insert(tk.END, f"만료일: {expiry_date.strftime('%Y-%m-%d')}\n\n") # type: ignore
            text_widget.insert(tk.END, "디바이스 정보: 시리얼 생성 시에는 기록되지 않습니다.\n")
            text_widget.insert(tk.END, "사용자가 프로그램에서 시리얼 인증 시 자동으로 수집됩니다.\n")
            
            text_widget.configure(state='disabled')
            
            # 확인 버튼
            ttk.Button(info_window, text="확인", command=info_window.destroy).pack(pady=10)
            
        except Exception as e:
            logging.error(f"디바이스 정보 표시 오류: {e}")
            messagebox.showerror("오류", f"디바이스 정보를 표시하는 중 오류가 발생했습니다.\n{str(e)}")
    
    def check_device_info_click(self, event):
        """클릭한 위치가 디바이스 정보 열인지 확인하고 상세 정보 표시"""
        column = self.tree.identify_column(event.x)
        if column == "#5":  # 디바이스 정보는 5번 컬럼
            self.show_device_info(event)
    
    def setup_github(self):
        """GitHub 설정 창 표시"""
        for window in (self.parent if self.parent else self.root).winfo_children():
            if isinstance(window, tk.Toplevel) and window.title() == "GitHub 설정":
                window.lift()
                return
        
        github_window = tk.Toplevel(self.parent if self.parent else self.root)
        github_window.title("GitHub 설정")
        github_window.geometry("500x300")
        github_window.resizable(False, False)
        
        input_frame = ttk.LabelFrame(github_window, text="GitHub 저장소 설정")
        input_frame.pack(padx=10, pady=10, fill=tk.X)
        
        # 정보 입력 필드
        token_frame = ttk.Frame(input_frame)
        token_frame.pack(pady=10, fill=tk.X)
        ttk.Label(token_frame, text="GitHub 토큰:").pack(side=tk.LEFT, padx=5)
        token_entry = ttk.Entry(token_frame, width=40, show="*")
        token_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        repo_frame = ttk.Frame(input_frame)
        repo_frame.pack(pady=10, fill=tk.X)
        ttk.Label(repo_frame, text="저장소 경로:").pack(side=tk.LEFT, padx=5)
        repo_entry = ttk.Entry(repo_frame, width=40)
        repo_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 안내 텍스트
        info_text = ttk.Label(
            github_window, 
            text="저장소 경로는 'username/repo' 형식으로 입력하세요.\n"
                 "예: kwanwon/serial-validator-server",
            justify=tk.LEFT
        )
        info_text.pack(pady=10, padx=10, fill=tk.X)
        
        status_var = tk.StringVar(value="GitHub 설정을 입력하세요.")
        status_label = ttk.Label(github_window, textvariable=status_var)
        status_label.pack(pady=5)
        
        def save_github_config():
            """GitHub 설정 저장"""
            token = token_entry.get().strip()
            repo = repo_entry.get().strip()
            
            if not token or not repo:
                status_var.set("토큰과 저장소 경로를 모두 입력하세요.")
                return
            
            try:
                # remote_config 모듈 사용
                try:
                    status_var.set("GitHub 설정 저장 중...")
                    github_window.update()
                    
                    from remote_config import setup_github_config
                    result = setup_github_config(token, repo)
                    
                    if result.get('success', False):
                        status_var.set("GitHub 설정이 저장되었습니다.")
                        
                        # 연결 테스트
                        from remote_config import test_github_connection
                        test_result = test_github_connection()
                        
                        if test_result.get('success', False):
                            messagebox.showinfo("성공", "GitHub 설정 및 연결 테스트 성공")
                            github_window.destroy()
                        else:
                            status_var.set(f"GitHub 연결 테스트 실패: {test_result.get('message', '')}")
                    else:
                        status_var.set(f"GitHub 설정 저장 실패: {result.get('message', '')}")
                
                except ImportError:
                    # 직접 API 호출
                    status_var.set("원격 모듈 로드 실패, 직접 API 호출 중...")
                    github_window.update()
                    
                    config_data = {
                        "github_config": {
                            "token": token,
                            "repo": repo
                        }
                    }
                    
                    response = requests.post(
                        f"{BLOG_SERVER_URL}/api/config/github", 
                        json=config_data,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        status_var.set("GitHub 설정이 저장되었습니다.")
                        
                        # 연결 테스트
                        test_response = requests.get(f"{BLOG_SERVER_URL}/api/config/github/test", timeout=30)
                        
                        if test_response.status_code == 200:
                            messagebox.showinfo("성공", "GitHub 설정 및 연결 테스트 성공")
                            github_window.destroy()
                        else:
                            status_var.set(f"GitHub 연결 테스트 실패: 응답 코드 {test_response.status_code}")
                    else:
                        status_var.set(f"GitHub 설정 저장 실패: 응답 코드 {response.status_code}")
            
            except Exception as e:
                logging.error(f"GitHub 설정 저장 오류: {str(e)}")
                status_var.set(f"GitHub 설정 저장 중 오류 발생: {str(e)[:50]}")
        
        button_frame = ttk.Frame(github_window)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="저장", command=save_github_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="취소", command=github_window.destroy).pack(side=tk.LEFT, padx=5)

    def manual_github_backup(self):
        """GitHub 수동 백업 실행"""
        try:
            # remote_config 사용 시도
            try:
                # 백업 API 호출
                status_label = ttk.Label(self.parent if self.parent else self.root, text="GitHub 백업 중...")
                status_label.pack(pady=5)
                self.root.update()
                
                response = requests.post(f"{BLOG_SERVER_URL}/api/backup", timeout=30)
                
                if response.status_code == 200:
                    messagebox.showinfo("성공", "GitHub 백업이 완료되었습니다.")
                else:
                    messagebox.showerror("오류", f"GitHub 백업 실패: 응답 코드 {response.status_code}")
                
                status_label.destroy()
            except Exception as e:
                logging.error(f"GitHub 백업 오류: {str(e)}")
                messagebox.showerror("오류", f"GitHub 백업 중 오류 발생: {str(e)}")
        except Exception as e:
            logging.error(f"GitHub 백업 함수 오류: {str(e)}")
            messagebox.showerror("오류", f"GitHub 백업 기능 오류: {str(e)}")


# 독립 실행 모드로 실행될 때
if __name__ == "__main__":
    app = BlogManager()
    app.run() 