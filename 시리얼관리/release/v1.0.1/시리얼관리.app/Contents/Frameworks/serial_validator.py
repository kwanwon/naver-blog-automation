########################################
# serial_validator.py
# (개발자용, SERVER_URL = "https://aimaster-serial.onrender.com")
# 모든 API 호출 시 "/api" 붙이도록 수정
########################################

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import datetime
import logging
import os
import requests # type: ignore
import json
import sys
import uuid
import platform
import psutil # type: ignore
import socket
from datetime import datetime, timedelta
import pandas as pd # type: ignore
from tkcalendar import DateEntry # type: ignore
import threading
import queue
import subprocess
import importlib.util

# 로깅 설정
logging.basicConfig(
    filename='serial_manager.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ----------------------------------------------------------------
# 서버 주소(도메인만) - /api는 여기에 붙이지 않음
# ----------------------------------------------------------------
SERVER_URL = "https://aimaster-serial.onrender.com"
# 예) GET /api/serials => requests.get(f"{SERVER_URL}/api/serials")
# ----------------------------------------------------------------

def get_db_path():
    """데이터베이스 파일의 절대 경로를 반환"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'serials.db')

def get_device_info():
    """디바이스 정보 수집 (맥 OS 버전)"""
    try:
        # 맥 OS에서 시스템 정보 얻기
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        memory = psutil.virtual_memory()
        
        # 맥에서 시스템 정보 가져오기
        system_info = {}
        
        # 모델 정보 가져오기
        try:
            model = subprocess.check_output(['sysctl', '-n', 'hw.model']).decode('utf-8').strip()
            system_info['system_model'] = model
        except:
            system_info['system_model'] = "Unknown Mac"
        
        # OS 버전 정보
        system_info['os_name'] = platform.system()
        system_info['os_version'] = platform.version()
        
        # 제조사는 Apple로 고정
        system_info['system_manufacturer'] = "Apple"
        
        # CPU 정보
        try:
            processor = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string']).decode('utf-8').strip()
        except:
            processor = platform.processor() or "Unknown Processor"
        
        device_info = {
            "hostname": hostname,
            "ip_address": ip_address,
            "system_manufacturer": system_info['system_manufacturer'],
            "system_model": system_info['system_model'],
            "os_name": system_info['os_name'],
            "os_version": system_info['os_version'],
            "processor": processor,
            "total_memory": f"{memory.total / (1024**3):.2f}GB",
            "registration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return device_info
    except Exception as e:
        logging.error(f"디바이스 정보 수집 중 오류 발생: {e}")
        return None

class SerialManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("시리얼 관리 시스템")
        self.root.geometry("1400x800")
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.init_database()
        
        # 로컬 메모 테이블 추가
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS local_memos (
                serial_number TEXT PRIMARY KEY,
                memo TEXT
            )
        ''')
        self.conn.commit()
        
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="전체")
        self.date_filter_var = tk.StringVar(value="전체 기간")
        
        self.task_queue = queue.Queue()
        
        # 컨텍스트 메뉴 생성 - 트리뷰 바인딩 전에 먼저 실행
        self.context_menu = tk.Menu(self.root, tearoff=0)
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
        
        # GUI 생성
        self.create_gui()
        
        # 현재 시간 표시 레이블 추가
        self.time_label = ttk.Label(self.root, text="", font=("Helvetica", 12))
        self.time_label.pack(pady=5)
        
        # 초기화 순서 변경
        self.refresh_serial_list()
        self.process_background_tasks()
        self.update_time()
        self.check_serial_status()  # 상태 체크 시작
        self.check_server_connection()
        self.root.after(3600000, self.check_expiring_serials)
        
        self.check_server_connection()
    
    def init_database(self):
        """데이터베이스 초기화"""
        try:
            self.conn = sqlite3.connect(get_db_path())
            self.cursor = self.conn.cursor()
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS serials (
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
            self.conn.commit()
            logging.info("데이터베이스 초기화 완료")
        except Exception as e:
            logging.error(f"데이터베이스 초기화 오류: {e}")
            messagebox.showerror("오류", "데이터베이스 초기화 중 오류가 발생했습니다.")
    
    def create_gui(self):
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
        
        # 탭 컨트롤 생성
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 첫 번째 탭: AI마스터관리 (시리얼 관리)
        self.ai_master_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.ai_master_tab, text="AI마스터관리")
        
        # 두 번째 탭: 블로그자동화
        self.blog_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.blog_tab, text="블로그자동화")
        
        # AI마스터관리 탭 내용 구성
        main_frame = ttk.Frame(self.ai_master_tab)
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
        
        # 상태별 색상 태그 설정
        self.tree.tag_configure('expired', foreground='red')  # 만료됨
        self.tree.tag_configure('blacklisted', foreground='gray')  # 블랙리스트
        self.tree.tag_configure('active', foreground='green')  # 사용가능
        self.tree.tag_configure('disabled', foreground='orange')  # 사용불가
        self.tree.tag_configure('in_use', foreground='blue')  # 사용중
        self.tree.tag_configure('expiring_soon', foreground='#FFA500')  # 만료 예정
        
        # 블로그자동화 탭 내용 구성
        self.create_blog_automation_tab()
        
        # 현재 시간 표시 레이블 추가
        self.time_label = ttk.Label(self.root, text="", font=("Helvetica", 12))
        self.time_label.pack(pady=5)
    
    def create_blog_automation_tab(self):
        """블로그자동화 탭 내용 구성 - 블로그자동화관리.py와 연결"""
        try:
            # 블로그자동화관리 모듈 임포트
            import importlib.util
            import os
            
            # 현재 파일 위치에서 블로그자동화관리.py 경로 가져오기
            current_dir = os.path.dirname(os.path.abspath(__file__))
            module_path = os.path.join(current_dir, '블로그자동화관리.py')
            
            if os.path.exists(module_path):
                # 모듈 로드
                spec = importlib.util.spec_from_file_location("blog_manager", module_path)
                blog_manager = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(blog_manager)
                
                # 블로그매니저 클래스의 인스턴스 생성하여 탭에 연결
                self.blog_manager = blog_manager.BlogManager(parent=self.blog_tab)
                logging.info("블로그자동화관리 모듈 로드 성공")
            else:
                # 파일이 없는 경우 기본 메시지 표시
                main_frame = ttk.Frame(self.blog_tab)
                main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                # 블로그자동화 제목
                title_label = ttk.Label(main_frame, text="블로그자동화 관리", font=("Helvetica", 16, "bold"))
                title_label.pack(pady=20)
                
                # 정보 메시지
                info_frame = ttk.LabelFrame(main_frame, text="알림")
                info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
                
                message = """
블로그자동화관리.py 파일을 찾을 수 없습니다.

필요한 파일을 설치하고 다시 시도하세요.
                """
                
                info_label = ttk.Label(info_frame, text=message, font=("Helvetica", 12))
                info_label.pack(pady=30, padx=20)
                
                # 하단 라벨
                version_label = ttk.Label(main_frame, text="버전: 1.0.0", font=("Helvetica", 10))
                version_label.pack(side=tk.BOTTOM, pady=10)
                
                logging.error("블로그자동화관리.py 파일을 찾을 수 없음")
        except Exception as e:
            # 오류 발생 시 기본 메시지 표시
            main_frame = ttk.Frame(self.blog_tab)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 블로그자동화 제목
            title_label = ttk.Label(main_frame, text="블로그자동화 관리", font=("Helvetica", 16, "bold"))
            title_label.pack(pady=20)
            
            # 정보 메시지
            info_frame = ttk.LabelFrame(main_frame, text="오류")
            info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            message = f"""
블로그자동화 관리 모듈을 로드하는 중 오류가 발생했습니다.

오류 내용: {str(e)}
            """
            
            info_label = ttk.Label(info_frame, text=message, font=("Helvetica", 12))
            info_label.pack(pady=30, padx=20)
            
            # 하단 라벨
            version_label = ttk.Label(main_frame, text="버전: 1.0.0", font=("Helvetica", 10))
            version_label.pack(side=tk.BOTTOM, pady=10)
            
            logging.error(f"블로그자동화 모듈 로드 오류: {e}")
    
    def check_server_connection(self):
        """서버 연결 상태 확인"""
        try:
            # /api/health
            response = requests.get(f"{SERVER_URL}/api/health", timeout=65)
            if response.status_code == 200:
                try:
                    # /api/serials
                    serials_response = requests.get(f"{SERVER_URL}/api/serials", timeout=60)
                    if serials_response.status_code == 200:
                        server_serials = serials_response.json()
                        self.status_label.config(
                            text=f"서버 상태: 정상 (등록된 시리얼: {len(server_serials)}개)", 
                            foreground="green"
                        )
                    else:
                        self.status_label.config(text="서버 상태: 정상", foreground="green")
                except:
                    self.status_label.config(text="서버 상태: 정상", foreground="green")
            else:
                self.status_label.config(text="서버 상태: 오류", foreground="red")
        except:
            self.status_label.config(text="서버 상태: 연결 실패", foreground="red")
        
        self.root.after(60000, self.check_server_connection)
    
    def process_background_tasks(self):
        try:
            while True:
                task = self.task_queue.get_nowait()
                task()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_background_tasks)
    
    def backup_to_github(self):
        """GitHub에 데이터 백업"""
        try:
            self.cursor.execute("""
                SELECT serial_number, status, created_date, expiry_date, 
                       device_info, memo, is_blacklisted, activation_count
                FROM serials 
                WHERE is_deleted = 0
            """)
            rows = self.cursor.fetchall()
            
            data = []
            for row in rows:
                serial_data = {
                    "serial_number": row[0],
                    "status": row[1],
                    "created_date": row[2],
                    "expiry_date": row[3],
                    "device_info": json.loads(row[4]) if row[4] else {},
                    "memo": row[5],
                    "is_blacklisted": bool(row[6]),
                    "activation_count": row[7]
                }
                data.append(serial_data)
            
            # /api/backup
            response = requests.post(f"{SERVER_URL}/api/backup", json={"data": data}, timeout=60)
            
            if response.status_code == 200:
                messagebox.showinfo("성공", "GitHub에 성공적으로 백업되었습니다.")
            else:
                raise Exception(f"서버 응답 오류: {response.status_code}")
            
        except Exception as e:
            logging.error(f"GitHub 백업 오류: {e}")
            messagebox.showerror("오류", f"GitHub 백업 중 오류가 발생했습니다.\n{str(e)}")
    
    def backup_database(self):
        """데이터베이스 백업"""
        try:
            backup_dir = os.path.join(os.path.dirname(get_db_path()), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_file = os.path.join(
                backup_dir, f'serials_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
            )
            
            self.conn.close()
            
            import shutil
            shutil.copy2(get_db_path(), backup_file)
            
            self.conn = sqlite3.connect(get_db_path())
            self.cursor = self.conn.cursor()
            
            self.backup_to_github()
            
            messagebox.showinfo("성공", f"데이터베이스가 백업되었습니다.\n위치: {backup_file}")
        except Exception as e:
            logging.error(f"데이터베이스 백업 오류: {e}")
            messagebox.showerror("오류", "데이터베이스 백업 중 오류가 발생했습니다.")
    
    def edit_expiry_date(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        for window in self.root.winfo_children():
            if isinstance(window, tk.Toplevel) and window.title() == "만료일 수정":
                window.lift()
                return
        
        edit_window = tk.Toplevel(self.root)
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
            new_date = date_entry.get_date().strftime('%Y-%m-%d')
            current_date = datetime.now().date()
            try:
                for item in selected:
                    serial = self.tree.item(item)['values'][0]
                    
                    # 새로운 만료일에 따른 상태 결정
                    expiry_date = datetime.strptime(new_date, '%Y-%m-%d').date()
                    
                    # 블랙리스트 상태 체크
                    self.cursor.execute("SELECT is_blacklisted FROM serials WHERE serial_number = ?", (serial,))
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
                    
                    # 먼저 로컬 DB 업데이트
                    self.cursor.execute("""
                        UPDATE serials 
                        SET expiry_date = ?, status = ?
                        WHERE serial_number = ?
                    """, (new_date, new_status, serial))
                    self.conn.commit()
                    
                    # 서버에 상태와 만료일 업데이트 요청
                    response = requests.patch(
                        f"{SERVER_URL}/api/serials/{serial}",
                        json={
                            "expiry_date": new_date,
                            "status": new_status
                        },
                        timeout=30
                    )
                    
                    if response.status_code != 200:
                        raise Exception(f"서버 응답 오류: {response.status_code}")
                    
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
    
    def create_serial(self):
        for window in self.root.winfo_children():
            if isinstance(window, tk.Toplevel) and window.title() == "시리얼 생성":
                window.lift()
                return
        
        create_window = tk.Toplevel(self.root)
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
                expiry_date = date_entry.get_date()
                if expiry_date < datetime.now().date():
                    raise ValueError("만료일은 현재 날짜 이후여야 합니다.")
                
                progress_var.set("디바이스 정보 수집 중...")
                create_window.update()
                
                serial = str(uuid.uuid4())
                device_info = get_device_info()
                
                if not device_info:
                    raise ValueError("디바이스 정보를 수집할 수 없습니다.")
                
                progress_var.set("서버에 등록 중...")
                create_window.update()
                
                # /api/register
                response = requests.post(
                    f"{SERVER_URL}/api/register",
                    json={
                        "serial_number": serial,
                        "expiry_date": expiry_date.strftime('%Y-%m-%d'),
                        "memo": memo_entry.get()
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    # 로컬 DB에 저장
                    self.cursor.execute('''
                        INSERT INTO serials (
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
                    
                    try:
                        self.backup_to_github()
                    except Exception as e:
                        logging.error(f"GitHub 백업 실패: {e}")
                    
                    # 결과 표시
                    result_window = tk.Toplevel(self.root)
                    result_window.title("시리얼 생성 완료")
                    result_window.geometry("500x300")
                    
                    text_widget = tk.Text(result_window, wrap=tk.WORD, padx=10, pady=10)
                    text_widget.pack(fill=tk.BOTH, expand=True)
                    
                    text_widget.insert(tk.END, f"시리얼 번호: {serial}\n\n")
                    text_widget.insert(tk.END, f"만료일: {expiry_date.strftime('%Y-%m-%d')}\n\n")
                    text_widget.insert(tk.END, "디바이스 정보:\n")
                    for key, value in device_info.items():
                        text_widget.insert(tk.END, f"{key}: {value}\n")
                    
                    text_widget.configure(state='disabled')
                    
                    ttk.Button(result_window, text="확인",
                               command=result_window.destroy).pack(pady=10)
                else:
                    raise ValueError(f"서버 응답 오류: {response.status_code}\n{response.text}")
                
            except Exception as e:
                logging.error(f"시리얼 생성 오류: {e}")
                messagebox.showerror("오류", f"시리얼 생성 중 오류가 발생했습니다.\n{str(e)}")
                progress_var.set("오류 발생")
        
        button_frame = ttk.Frame(create_window)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="생성", command=validate_and_create).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="취소", command=create_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def refresh_serial_list(self):
        """시리얼 목록 새로고침"""
        try:
            # 현재 로컬 메모 저장
            self.cursor.execute("SELECT serial_number, memo FROM local_memos")
            local_memos = dict(self.cursor.fetchall())
            
            response = requests.get(f"{SERVER_URL}/api/serials", timeout=60)
            if response.status_code == 200:
                server_data = response.json()
                
                # 트랜잭션 시작
                self.cursor.execute("BEGIN TRANSACTION")
                
                try:
                    self.cursor.execute("DELETE FROM serials")
                    
                    # 현재 활성화된 디바이스 정보를 저장할 딕셔너리
                    active_devices = {}
                    
                    for serial in server_data:
                        serial_number = serial.get('serial_number')
                        is_blacklisted = serial.get('is_blacklisted', False)
                        activation_count = serial.get('activation_count', 0)
                        server_status = serial.get('status', '')
                        device_info = serial.get('device_info', {})
                        
                        if isinstance(device_info, str):
                            try:
                                device_info = json.loads(device_info)
                            except:
                                device_info = {}
                        
                        # 디바이스 정보가 있는 경우
                        if device_info and any(device_info.values()):
                            device_id = device_info.get('hostname', '') + device_info.get('ip_address', '')
                            if device_id:
                                # 이미 해당 디바이스에 다른 시리얼이 활성화되어 있다면
                                if device_id in active_devices:
                                    # 이전 시리얼의 디바이스 정보 활성화 횟수 초기화
                                    old_serial = active_devices[device_id]
                                    self.cursor.execute("""
                                        UPDATE serials 
                                        SET device_info = '{}', activation_count = 0
                                        WHERE serial_number = ?
                                    """, (old_serial,))
                                active_devices[device_id] = serial_number
                        
                        # 서버에서 받은 상태 그대로 사용
                        status = server_status if server_status else '사용가능'
                        
                        if is_blacklisted:
                            status = '블랙리스트'
                        
                        # 로컬 메모가 있으면 그것을 사용, 없으면 서버 메모 사용
                        memo = local_memos.get(serial_number, serial.get('memo', ''))
                        
                        self.cursor.execute('''
                            INSERT INTO serials (
                                serial_number, status, created_date, expiry_date,
                                device_info, memo, is_blacklisted, is_deleted,
                                activation_count
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            serial_number,
                            status,
                            serial.get('created_date'),
                            serial.get('expiry_date'),
                            json.dumps(device_info),
                            memo,
                            1 if is_blacklisted else 0,
                            0,
                            activation_count
                        ))
                    
                    # 트랜잭션 커밋
                    self.cursor.execute("COMMIT")
                    self.update_ui()
                except Exception as e:
                    # 오류 발생 시 롤백
                    self.cursor.execute("ROLLBACK")
                    raise e
            else:
                logging.error(f"서버 응답 실패: {response.status_code}")
                messagebox.showerror("오류", "서버에서 데이터를 가져오는데 실패했습니다.")
        except requests.exceptions.Timeout:
            messagebox.showerror("오류", "서버 연결 시간이 초과되었습니다.")
        except requests.exceptions.RequestException as e:
            logging.error(f"서버 통신 오류: {e}")
            messagebox.showerror("오류", f"서버 통신 중 오류가 발생했습니다.\n{str(e)}")
        except Exception as e:
            logging.error(f"데이터 동기화 오류: {e}")
            messagebox.showerror("오류", f"데이터 동기화 중 오류가 발생했습니다.\n{str(e)}")
    
    def format_device_info(self, device_info_str):
        try:
            if isinstance(device_info_str, str):
                info = json.loads(device_info_str)
            else:
                info = device_info_str
            
            if info and any(info.values()):
                return "등록됨 (사용중)"
            return "미등록"
        except:
            return "미등록"
    
    def check_expiring_serials(self):
        try:
            self.cursor.execute("""
                SELECT serial_number, expiry_date 
                FROM serials 
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
    
    def export_to_excel(self):
        try:
            self.cursor.execute("""
                SELECT serial_number, status, created_date, expiry_date, 
                       device_info, memo, activation_count
                FROM serials 
                WHERE is_deleted = 0
                ORDER BY created_date DESC
            """)
            rows = self.cursor.fetchall()
            
            import pandas as pd # type: ignore
            df = pd.DataFrame(rows, columns=[
                "시리얼 번호", "상태", "등록일시", "만료일시",
                "디바이스정보", "메모", "활성화횟수"
            ])
            df["디바이스정보"] = df["디바이스정보"].apply(lambda x: self.format_device_info(x))
            
            filename = f"시리얼목록_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='시리얼목록')
                worksheet = writer.sheets['시리얼목록']
                
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
            
            messagebox.showinfo("성공", f"엑셀 파일이 생성되었습니다.\n파일명: {filename}")
            # os.startfile(filename) - 맥에서는 사용할 수 없음
            # 대신 subprocess로 파일 열기
            subprocess.call(['open', filename])
        except Exception as e:
            logging.error(f"엑셀 내보내기 오류: {e}")
            messagebox.showerror("오류", "엑셀 파일 생성 중 오류가 발생했습니다.")
    
    def show_context_menu(self, event):
        try:
            # 이벤트 정보 로깅
            logging.info(f"컨텍스트 메뉴 이벤트: {event.type}, x={event.x}, y={event.y}")
            
            # 먼저 이벤트가 발생한 항목 선택
            item = self.tree.identify_row(event.y)
            if item:
                # 이미 선택된 항목이 있는지 확인
                if not self.tree.selection() or item not in self.tree.selection():
                    # 선택된 항목이 없거나 클릭한 항목이 선택되지 않았다면 해당 항목만 선택
                    self.tree.selection_set(item)
            
            # 마우스 위치 조정 (맥에서는 화면 좌표가 다를 수 있음)
            try:
                screen_x = self.root.winfo_pointerx()
                screen_y = self.root.winfo_pointery()
                self.context_menu.tk_popup(screen_x, screen_y)
            except:
                # 실패하면 기존 방식으로 시도
                self.context_menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            logging.error(f"컨텍스트 메뉴 표시 오류: {e}")
        finally:
            # 그랩 해제는 메뉴가 사라질 때 항상 호출
            self.context_menu.grab_release()
    
    def edit_memo(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        
        item = selected[0]
        current_values = self.tree.item(item)['values']
        current_memo = current_values[5]
        
        memo = simpledialog.askstring("메모 수정", "메모를 입력하세요:", initialvalue=current_memo)
        if memo is not None:
            serial = current_values[0]
            try:
                # 로컬 메모 테이블 업데이트
                self.cursor.execute("""
                    INSERT OR REPLACE INTO local_memos (serial_number, memo)
                    VALUES (?, ?)
                """, (serial, memo))
                
                # 메인 테이블 업데이트
                self.cursor.execute("UPDATE serials SET memo = ? WHERE serial_number = ?", (memo, serial))
                self.conn.commit()
                
                # UI 업데이트
                new_values = list(current_values)
                new_values[5] = memo
                self.tree.item(item, values=new_values)
                messagebox.showinfo("성공", "메모가 수정되었습니다.")
            except Exception as e:
                logging.error(f"메모 수정 오류: {e}")
                messagebox.showerror("오류", "메모 수정 중 오류가 발생했습니다.")
    
    def copy_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        text = ""
        for item in selected:
            serial = self.tree.item(item)['values'][0]
            text += f"{serial}\n"
        
        self.root.clipboard_clear()
        self.root.clipboard_append(text.strip())
    
    def select_all(self):
        for item in self.tree.get_children():
            self.tree.selection_add(item)
    
    def set_blacklist(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        try:
            for item in selected:
                serial = self.tree.item(item)['values'][0]
                # /api/blacklist
                response = requests.post(f"{SERVER_URL}/api/blacklist", json={
                    "serial_number": serial,
                    "action": "add"
                }, timeout=30)
                
                if response.status_code == 200:
                    self.cursor.execute("""
                        UPDATE serials 
                        SET status = '블랙리스트', is_blacklisted = 1 
                        WHERE serial_number = ?
                    """, (serial,))
                else:
                    raise Exception(f"서버 응답 오류: {response.status_code}")
            
            self.conn.commit()
            self.refresh_serial_list()
            messagebox.showinfo("성공", "블랙리스트로 설정되었습니다.")
        except Exception as e:
            logging.error(f"블랙리스트 설정 오류: {e}")
            messagebox.showerror("오류", f"블랙리스트 설정 중 오류가 발생했습니다.\n{str(e)}")
    
    def unset_blacklist(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        try:
            for item in selected:
                serial = self.tree.item(item)['values'][0]
                response = requests.post(f"{SERVER_URL}/api/blacklist", json={
                    "serial_number": serial,
                    "action": "remove"
                }, timeout=30)
                
                if response.status_code == 200:
                    self.cursor.execute("""
                        UPDATE serials 
                        SET status = '사용가능', is_blacklisted = 0 
                        WHERE serial_number = ?
                    """, (serial,))
                else:
                    raise Exception(f"서버 응답 오류: {response.status_code}")
            
            self.conn.commit()
            self.refresh_serial_list()
            messagebox.showinfo("성공", "블랙리스트가 해제되었습니다.")
        except Exception as e:
            logging.error(f"블랙리스트 해제 오류: {e}")
            messagebox.showerror("오류", f"블랙리스트 해제 중 오류가 발생했습니다.\n{str(e)}")
    
    def delete_serial(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        if not messagebox.askyesno("확인", "선택한 시리얼을 삭제하시겠습니까?"):
            return
        
        try:
            for item in selected:
                serial = self.tree.item(item)['values'][0]
                # /api/serial/<serial_number> (DELETE)
                response = requests.delete(f"{SERVER_URL}/api/serial/{serial}", timeout=60)
                
                if response.status_code == 200:
                    self.cursor.execute("UPDATE serials SET is_deleted = 1 WHERE serial_number = ?", (serial,))
                else:
                    messagebox.showerror("오류", f"서버 응답 오류: {response.status_code}")
                    return
            
            self.conn.commit()
            self.refresh_serial_list()
            messagebox.showinfo("성공", "시리얼이 삭제되었습니다.")
        except Exception as e:
            logging.error(f"시리얼 삭제 오류: {e}")
            messagebox.showerror("오류", "시리얼 삭제 중 오류가 발생했습니다.")
    
    def check_serial_on_server(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("알림", "확인할 시리얼을 선택해주세요.")
            return
        
        try:
            results = []
            for item in selected:
                serial = self.tree.item(item)['values'][0]
                # /api/serials/<serial_number> (GET)
                response = requests.get(f"{SERVER_URL}/api/serial/{serial}", timeout=60)
                if response.status_code == 200:
                    server_data = response.json()
                    results.append(f"시리얼: {serial}\n상태: 서버에 존재함\n상태: {server_data['status']}\n")
                elif response.status_code == 404:
                    results.append(f"시리얼: {serial}\n상태: 서버에 없음\n")
                else:
                    results.append(f"시리얼: {serial}\n상태: 확인 실패 (코드: {response.status_code})\n")
            
            result_window = tk.Toplevel(self.root)
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
    
    def update_ui(self):
        """UI 업데이트"""
        try:
            current_items = {
                self.tree.item(item)['values'][0]: item 
                for item in self.tree.get_children()
            }
            
            # DB에서 데이터 조회
            self.cursor.execute('''
                SELECT serial_number, status, created_date, expiry_date,
                       device_info, memo, activation_count, is_blacklisted
                FROM serials 
                WHERE is_deleted = 0
                ORDER BY created_date DESC
            ''')
            rows = self.cursor.fetchall()
            
            # 검색어와 상태 필터 가져오기
            search_text = self.search_var.get().lower()
            status_filter = self.status_var.get()
            
            new_items = set()
            
            # 필터링 및 표시
            for row in rows:
                serial_number = row[0]
                status = row[1]
                created_date = row[2]
                expiry_date = row[3]
                device_info = row[4]
                memo = row[5]
                activation_count = row[6]
                is_blacklisted = row[7]
                
                # 검색어 필터링
                if search_text and search_text not in serial_number.lower() and search_text not in memo.lower():
                    continue
                    
                # 상태 필터링
                if status_filter != "전체" and status != status_filter:
                    continue
                
                # 상태에 따른 태그 결정
                if is_blacklisted or status == '블랙리스트':
                    tag = 'blacklisted'
                elif status == '만료됨':
                    tag = 'expired'
                elif status == '만료 예정':
                    tag = 'expiring_soon'
                elif status == '사용중':
                    tag = 'in_use'
                elif status == '사용불가':
                    tag = 'disabled'
                else:
                    tag = 'active'
                
                new_items.add(serial_number)
                values = (
                    serial_number,
                    status,
                    created_date,
                    expiry_date,
                    self.format_device_info(device_info),
                    memo,
                    activation_count
                )
                
                if serial_number in current_items:
                    # 기존 항목 업데이트
                    item_id = current_items[serial_number]
                    if self.tree.item(item_id)['values'] != values:
                        self.tree.item(item_id, values=values, tags=(tag,))
                else:
                    # 새 항목 추가
                    self.tree.insert('', 'end', values=values, tags=(tag,))
            
            # 삭제된 항목 제거
            for serial_number, item_id in current_items.items():
                if serial_number not in new_items:
                    self.tree.delete(item_id)
                
        except Exception as e:
            logging.error(f"UI 업데이트 오류: {e}")
            messagebox.showerror("오류", "UI 업데이트 중 오류가 발생했습니다.")
    
    def update_time(self):
        """현재 시간 업데이트"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.time_label.config(text=f"현재 시간: {current_time}")
        self.root.after(1000, self.update_time)  # 시간 표시만 1초마다 업데이트
        
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
                    elif current_date + timedelta(days=7) >= expiry_date and status == '사용가능':
                        new_status = '만료 예정'
                    
                    # 상태가 변경된 경우만 업데이트
                    if new_status != status:
                        # DB 업데이트
                        self.cursor.execute("""
                            UPDATE serials 
                            SET status = ?
                            WHERE serial_number = ?
                        """, (new_status, serial_number))
                        
                        # 트리뷰 업데이트
                        values = list(values)
                        values[1] = new_status
                        self.tree.item(item, values=values)
                        
                        # 서버에 상태 업데이트 요청
                        try:
                            response = requests.patch(
                                f"{SERVER_URL}/api/serials/{serial_number}",
                                json={
                                    "status": new_status,
                                    "expiry_date": expiry_date_str
                                },
                                timeout=30
                            )
                            
                            if response.status_code == 200:
                                self.conn.commit()
                                logging.info(f"시리얼 {serial_number} 상태 업데이트: {new_status}")
                        except Exception as e:
                            logging.error(f"서버 상태 업데이트 실패: {str(e)}")
                            
                except ValueError:
                    continue
                    
        except Exception as e:
            logging.error(f"상태 체크 오류: {e}")
        
        # 1분 후에 다시 체크
        self.root.after(60000, self.check_serial_status)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SerialManager()
    app.run()
