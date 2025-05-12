#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시리얼 인증 UI 모듈
블로그 자동화 프로그램에서 시리얼 번호 인증을 위한 UI를 제공합니다.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
from pathlib import Path
import webbrowser
import json
import requests
import time
import flet as ft

# 상대 경로 임포트 처리
current_dir = os.path.dirname(os.path.abspath(__file__))
module_dir = os.path.dirname(current_dir)
if module_dir not in sys.path:
    sys.path.append(module_dir)

# 시리얼 클라이언트 임포트
from serial_validator.serial_client import SerialClient

# 구매 페이지 URL
PURCHASE_URL = "https://aimaster-serial.onrender.com"

class SerialValidatorUI:
    def __init__(self, app_name="BlogAutomation", master=None, callback=None):
        """
        시리얼 인증 UI 초기화
        
        Args:
            app_name (str): 애플리케이션 이름
            master: 부모 위젯
            callback: 인증 결과 콜백 함수
        """
        # 환경 변수 확인 (blog_writer_app.py에서 설정한 값 사용)
        env_app_name = os.environ.get('APP_NAME')
        if env_app_name:
            app_name = env_app_name
            print(f"환경 변수에서 앱 이름을 가져왔습니다: {app_name}")
            
        self.app_name = app_name
        self.callback = callback
        self.master = master
        self.logout_success = False  # 로그아웃 성공 여부 추적
        
        # 기본 디렉토리 설정
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 시리얼 클라이언트 초기화
        self.client = SerialClient(app_name=app_name)
        
        # 독립 창 모드 여부 확인
        if master is None:
            self.root = tk.Tk()
        else:
            self.root = tk.Toplevel(master)
            self.root.transient(master)
            
        # UI 초기화
        self.setup_ui()
        
        # ESC 키 설정
        self.root.bind("<Escape>", lambda e: self.on_close())
        
        # 창 닫힘 이벤트 처리
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 독립 창 모드인 경우 이벤트 루프 시작
        if master is None:
            self.root.mainloop()
        
    def setup_ui(self):
        """UI 초기화"""
        self.root.title(f"{self.app_name} - 시리얼 인증")
        
        # 창 크기 및 위치 설정
        window_width = 450
        window_height = 450  # 높이를 더 키움
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int((screen_width - window_width) / 2)
        center_y = int((screen_height - window_height) / 2)
        
        # 화면의 위쪽에 배치하여 아래 버튼들이 모두 보이도록 함
        center_y = int(center_y * 0.5)
        
        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        self.root.resizable(False, False)
        
        # 항상 최상위에 표시되도록 설정
        self.root.attributes('-topmost', True)
        
        # UI 구성 요소 생성
        self.create_ui_elements()
        
        # 서버 상태 확인
        self.check_server_status()
        
        # 포커스 설정
        self.serial_entry.focus()
        
    def setup_style(self):
        """스타일 설정"""
        # ttk 테마 적용 시도 - 맥에서 더 잘 보이도록
        try:
            if sys.platform == "darwin":
                self.style.theme_use("aqua")  # macOS 테마
        except tk.TclError:
            pass
            
        # 인증 버튼용 특별 스타일
        self.style.configure(
            "Accent.TButton",
            background="#1a73e8",
            foreground="white",
            padding=5,
            font=("Arial", 11, "bold")  # 글꼴 크기 증가 및 굵게 설정
        )
        
        # 버튼 매핑 추가 (ttk 버튼의 배경색 문제 해결)
        self.style.map("Accent.TButton",
            background=[('active', '#1565c0'), ('pressed', '#0d47a1')],
            foreground=[('active', 'white'), ('pressed', 'white')]
        )
        
        # 일반 버튼 스타일 (붙여넣기, 구매 버튼용)
        self.style.configure(
            "TButton",
            font=("Arial", 10)
        )
        
        self.style.configure(
            "Valid.TLabel",
            foreground="#00796b",
            font=("Arial", 12, "bold")
        )
        
        self.style.configure(
            "Invalid.TLabel",
            foreground="#d32f2f",
            font=("Arial", 12, "bold")
        )
    
    def show_context_menu(self, event):
        """우클릭 메뉴 표시"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def cut_text(self, event=None):
        """선택된 텍스트 잘라내기"""
        try:
            if self.copy_text():
                self.serial_entry.delete("sel.first", "sel.last")
            return True
        except:
            return False
    
    def copy_text(self, event=None):
        """선택된 텍스트 복사"""
        try:
            selected_text = self.serial_entry.get("sel.first", "sel.last")
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            return True
        except:
            return False
    
    def paste_text(self, event=None):
        """클립보드 내용 붙여넣기"""
        try:
            self.serial_entry.delete("sel.first", "sel.last")
        except:
            pass
        
        try:
            clipboard_text = self.root.clipboard_get()
            self.serial_entry.insert(tk.INSERT, clipboard_text)
            return True
        except Exception as e:
            print(f"텍스트 붙여넣기 오류: {str(e)}")
            return False
    
    def select_all_text(self, event=None):
        """텍스트 전체 선택"""
        try:
            self.serial_entry.select_range(0, tk.END)
            return "break"  # 기본 이벤트 처리 중단
        except Exception as e:
            print(f"텍스트 전체 선택 오류: {str(e)}")
            
    def update_status(self):
        """UI 상태 업데이트"""
        # 위젯 존재 여부 확인
        if not self.root or not self.root.winfo_exists():
            return
        
        # status_label, expiry_label이 유효한지 확인
        try:
            # 시리얼이 유효한 경우
            if self.client.is_valid:
                serial_num = self.client.serial_number
                # 전체 시리얼 번호 표시 (마스킹 제거)
                
                self.status_label.configure(
                    text=f"인증됨: {serial_num}",
                    style="Valid.TLabel"
                )
                
                # 디바이스 정보가 있는 경우 디바이스 정보 업데이트
                if hasattr(self, 'device_info_table'):
                    try:
                        self.update_device_info()
                    except Exception as e:
                        logging.error(f"디바이스 정보 업데이트 중 오류: {str(e)}")
                
                if self.client.expiry_date:
                    try:
                        # 만료일 파싱
                        expiry_date = datetime.strptime(self.client.expiry_date, "%Y-%m-%d").date()
                        today = datetime.now().date()
                        days_left = (expiry_date - today).days
                        
                        # 로그 추가 (디버깅용)
                        logging.info(f"UI 만료일 계산 - 현재 날짜: {today}, 만료일: {expiry_date}, 남은 일수: {days_left}")
                        
                        if days_left > 30:
                            self.expiry_label.configure(
                                text=f"유효기간: {self.client.expiry_date} ({days_left}일 남음)",
                                style="Valid.TLabel"
                            )
                        elif days_left > 0:
                            self.expiry_label.configure(
                                text=f"유효기간: {self.client.expiry_date} (곧 만료됨, {days_left}일 남음)",
                                style="Warning.TLabel"
                            )
                        else:
                            self.expiry_label.configure(
                                text=f"만료됨: {self.client.expiry_date}",
                                style="Invalid.TLabel"
                            )
                    except Exception as date_error:
                        logging.error(f"만료일 계산 오류: {str(date_error)}")
                        self.expiry_label.configure(
                            text=f"유효기간: {self.client.expiry_date} (날짜 계산 오류)",
                            style="Warning.TLabel"
                        )
                else:
                    self.expiry_label.configure(
                        text="유효기간: 정보 없음",
                        style="TLabel"
                    )
            else:
                # 시리얼이 유효하지 않은 경우
                self.status_label.configure(
                    text=f"상태: {self.client.status or '인증되지 않음'}",
                    style="Invalid.TLabel"
                )
                
                self.expiry_label.configure(
                    text="",
                    style="TLabel"
                )
                
                # 디바이스 정보 테이블 초기화
                if hasattr(self, 'device_info_table'):
                    for row in self.device_info_table.get_children():
                        self.device_info_table.delete(row)
                    
        except Exception as e:
            logging.error(f"UI 상태 업데이트 중 오류: {str(e)}")
    
    def validate_serial(self):
        """시리얼 번호 검증"""
        # 입력된 시리얼 번호 가져오기
        serial_num = self.serial_entry.get().strip()
        
        if not serial_num:
            # 기존 창을 최상위에서 일시적으로 해제
            self.root.attributes('-topmost', False)
            
            messagebox.showwarning(
                "시리얼 번호 없음",
                "시리얼 번호를 입력해주세요."
            )
            
            # 메인 창을 다시 최상위로 설정
            self.root.attributes('-topmost', True)
            self.root.lift()
            # 버튼 상태 확인 및 복원
            self.validate_button.config(state=tk.NORMAL)
            self.validate_button.config(text="인증하기")
            self.root.update()
            return

        # 버튼 비활성화
        try:
            self.validate_button.config(state=tk.DISABLED)
            self.validate_button.config(text="인증 중...")
            self.root.update()
        except Exception as e:
            print(f"버튼 비활성화 중 오류: {e}")
        
        try:
            # 시리얼 검증
            is_valid = self.client.validate_serial(serial_num)
            
            if is_valid:
                # 인증 성공 파일 생성 - GUI 대신 터미널이 나타나는 문제 해결
                try:
                    # 성공 정보를 파일로 저장
                    success_info = {
                        "serial_number": self.client.serial_number,
                        "status": self.client.status,
                        "expiry_date": self.client.expiry_date,
                        "is_valid": True,
                        "validation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "app_name": self.client.app_name,
                        "device_hash": self.client.device_info.get('device_hash', '')
                    }
                    
                    # 여러 경로에 성공 상태 파일 저장
                    success_paths = [
                        os.path.join(self.base_dir, 'config'),
                        os.path.join(os.path.dirname(os.path.dirname(self.base_dir)), 'config'),
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
                    ]
                    
                    for path in success_paths:
                        try:
                            if not os.path.exists(path):
                                os.makedirs(path, exist_ok=True)
                            
                            success_file = os.path.join(path, 'validation_success.json')
                            with open(success_file, 'w', encoding='utf-8') as f:
                                json.dump(success_info, f, ensure_ascii=False, indent=2)
                            
                            print(f"인증 성공 정보 저장: {success_file}")
                        except Exception as path_error:
                            print(f"인증 성공 정보 저장 오류 ({path}): {str(path_error)}")
                except Exception as save_error:
                    print(f"인증 성공 정보 저장 중 오류: {str(save_error)}")
                
                # 기존 창을 최상위에서 일시적으로 해제
                self.root.attributes('-topmost', False)
                
                # 성공 메시지
                try:
                    messagebox.showinfo(
                        "인증 성공",
                        "시리얼 번호가 성공적으로 인증되었습니다.\n"
                        f"만료일: {self.client.expiry_date}"
                    )
                except:
                    print("인증 성공 메시지 표시 실패")
                    
                # 성공 후 앱 재시작을 위한 환경 변수 설정
                try:
                    os.environ['SERIAL_VALIDATED'] = 'TRUE'
                    print("인증 환경 변수 설정 완료")
                except Exception as env_error:
                    print(f"환경 변수 설정 오류: {str(env_error)}")
                
                # 디바이스 정보 저장 확실히 하기
                try:
                    if hasattr(self.client, 'save_device_info'):
                        self.client.save_device_info()
                        print("디바이스 정보 저장 완료")
                except Exception as dev_error:
                    print(f"디바이스 정보 저장 오류: {str(dev_error)}")
                
                # 독립 창 모드인 경우 성공 후 종료 처리
                if self.master is None:
                    print("인증 성공 - 독립 창 모드에서 정상 종료 중")
                    try:
                        # 창 파괴 - 명시적으로 파괴 후 처리
                        self.root.withdraw()  # 먼저 숨기고
                        self.root.quit()      # tkinter 이벤트 루프 종료
                        self.root.destroy()   # 창 파괴
                        
                        # 인증 성공 시 특수 코드로 종료하여 부모 프로세스에 성공 신호 전달
                        print("인증 성공 - 종료 코드 0으로 프로그램 종료")
                        sys.exit(0)  # 성공 코드 0으로 종료
                    except Exception as exit_error:
                        print(f"종료 처리 중 오류: {str(exit_error)}")
                        sys.exit(0)  # 오류가 발생해도 성공 코드로 종료
                    
                    return  # 여기서 종료
            else:
                # 기존 창을 최상위에서 일시적으로 해제
                try:
                    if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                        self.root.attributes('-topmost', False)
                except:
                    pass
                
                # 실패
                try:
                    messagebox.showerror(
                        "인증 실패",
                        f"시리얼 번호 인증에 실패했습니다.\n"
                        f"사유: {self.client.status}"
                    )
                except:
                    print("인증 실패 메시지 표시 실패")
                    
                # 메인 창을 다시 최상위로 설정 (앱이 살아있는 경우)
                try:
                    if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                        self.root.attributes('-topmost', True)
                        self.root.lift()
                        # 버튼 상태 복원 추가
                        self.validate_button.config(state=tk.NORMAL)
                        self.validate_button.config(text="인증하기")
                        self.root.update()
                except:
                    pass
                    
                # 실패 후 시리얼 필드 초기화
                try:
                    self.serial_entry.delete(0, tk.END)
                    self.serial_entry.focus()
                except:
                    pass
        except Exception as e:
            # 기존 창을 최상위에서 일시적으로 해제
            try:
                if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                    self.root.attributes('-topmost', False)
            except:
                pass
                
            # 오류 메시지
            try:
                messagebox.showerror(
                    "오류 발생",
                    f"인증 과정에서 오류가 발생했습니다: {str(e)}"
                )
            except:
                print(f"오류 발생: {e}")
                
            # 메인 창을 다시 최상위로 설정 (앱이 살아있는 경우)
            try:
                if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                    self.root.attributes('-topmost', True)
                    self.root.lift()
                    # 버튼 상태 복원 추가
                    self.validate_button.config(state=tk.NORMAL)
                    self.validate_button.config(text="인증하기")
                    self.root.update()
            except:
                pass
                
            # 오류 후 시리얼 필드 초기화
            try:
                self.serial_entry.delete(0, tk.END)
                self.serial_entry.focus()
            except:
                pass
                
        finally:
            # UI 상태 업데이트 시도
            try:
                # tkinter 객체가 아직 존재하는지 확인
                if 'self.root' in dir(self) and self.root and self.root.winfo_exists():
                    # tkinter 창이 아직 파괴되지 않았는지 확인
                    try:
                        tk_state = self.root.state()
                        self.update_status()
                    except:
                        pass
            except:
                pass
            
            # 버튼 상태 복원 시도 - 더 확실하게 처리
            try:
                # 인증이 성공했고 독립 창 모드가 아니라면, 버튼 활성화
                if hasattr(self, 'validate_button') and self.validate_button:
                    self.validate_button.config(state=tk.NORMAL)
                    self.validate_button.config(text="인증하기")
                    # 인증 실패 시 시리얼 번호 입력 필드 초기화하고 포커스 주기
                    if not self.client.is_valid:
                        self.serial_entry.delete(0, tk.END)
                        self.serial_entry.focus()
                    self.root.update()  # UI 즉시 업데이트
            except Exception as e:
                print(f"버튼 상태 복원 실패: {e}")
                # 다시 한번 더 시도
                try:
                    if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                        self.validate_button.config(state=tk.NORMAL)
                        self.validate_button.config(text="인증하기")
                        self.root.update()
                except:
                    pass
    
    def logout_serial(self):
        """시리얼 로그아웃 처리"""
        try:
            if self.client and self.client.serial_number:
                # 기존 창을 최상위에서 일시적으로 해제
                self.root.attributes('-topmost', False)
                
                # 로그아웃 확인 대화상자 (tkinter 사용)
                confirm = messagebox.askyesno(
                    "로그아웃 확인",
                    "정말로 시리얼을 로그아웃 하시겠습니까?",
                    icon="question"
                )
                
                if confirm:
                    self.do_logout_tk()
                
                # 메인 창을 다시 최상위로 설정
                self.root.attributes('-topmost', True)
                self.root.lift()
        except Exception as e:
            print(f"로그아웃 대화상자 오류: {str(e)}")
            
    def do_logout_tk(self):
        """실제 로그아웃 처리 (tkinter 버전)"""
        try:
            # 시리얼 정보 백업 (디버깅 용도)
            try:
                serial_info = {
                    "serial_number": self.client.serial_number,
                    "status": self.client.status,
                    "expiry_date": self.client.expiry_date,
                    "logout_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # 디버깅용 로그 저장
                debug_dir = os.path.join(self.base_dir, 'logs')
                os.makedirs(debug_dir, exist_ok=True)
                debug_file = os.path.join(debug_dir, f'logout_debug_{datetime.now().strftime("%Y%m%d%H%M%S")}.json')
                
                with open(debug_file, 'w', encoding='utf-8') as f:
                    json.dump(serial_info, f, ensure_ascii=False, indent=2)
                    
                print(f"로그아웃 디버그 정보 저장: {debug_file}")
            except Exception as backup_error:
                print(f"로그아웃 정보 백업 오류 (무시됨): {str(backup_error)}")
            
            # 시리얼 로그아웃 실행
            self.client.clear_serial()
            
            # 디바이스 정보 초기화
            self.client.device_info = None
            
            # 즉시 UI 업데이트
            self.update_device_info()
            
            # 추가: 모든 가능한 로그아웃 상태 파일 생성
            try:
                # 여러 위치에 로그아웃 상태 파일 생성
                logout_paths = [
                    os.path.join(self.base_dir, 'config'),
                    os.path.join(os.path.dirname(os.path.dirname(self.base_dir)), 'config'),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
                ]
                
                for logout_dir in logout_paths:
                    if not os.path.exists(logout_dir):
                        os.makedirs(logout_dir, exist_ok=True)
                    
                    logout_file = os.path.join(logout_dir, 'logout_status.txt')
                    with open(logout_file, 'w', encoding='utf-8') as f:
                        f.write(f"Serial logged out at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    print(f"추가 로그아웃 상태 파일 생성: {logout_file}")
            except Exception as lout_error:
                print(f"추가 로그아웃 상태 파일 생성 오류: {str(lout_error)}")
            
            # 추가: 시리얼 데이터베이스 직접 초기화
            try:
                # 가능한 모든 DB 경로 체크
                db_paths = [
                    os.path.join(self.base_dir, 'serial_data.db'),
                    os.path.join(os.path.dirname(os.path.dirname(self.base_dir)), 'modules/serial_validator/serial_data.db'),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'serial_data.db')
                ]
                
                for db_path in db_paths:
                    if os.path.exists(db_path):
                        import sqlite3
                        try:
                            conn = sqlite3.connect(db_path)
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM serial_data")
                            conn.commit()
                            conn.close()
                            print(f"시리얼 데이터베이스 초기화: {db_path}")
                        except Exception as db_err:
                            print(f"DB 초기화 오류 ({db_path}): {str(db_err)}")
            except Exception as db_ex:
                print(f"데이터베이스 초기화 처리 오류: {str(db_ex)}")
            
            # 로그아웃 완료 메시지
            messagebox.showinfo(
                "로그아웃 완료",
                "시리얼이 성공적으로 로그아웃되었습니다.\n다음 실행 시 새로운 시리얼 인증이 필요합니다."
            )
            
            # 로그아웃 성공 표시
            self.logout_success = True
            
            # UI 업데이트
            if hasattr(self, 'status_label'):
                self.status_label.configure(
                    text="상태: 로그아웃됨",
                    style="Invalid.TLabel"
                )
            
            if hasattr(self, 'expiry_label'):
                self.expiry_label.configure(
                    text="",
                    style="TLabel"
                )
            
            # 앱 종료
            self.on_close()
            
        except Exception as e:
            print(f"로그아웃 처리 오류: {str(e)}")
            
            # 오류 메시지 표시
            messagebox.showerror(
                "로그아웃 오류",
                f"로그아웃 처리 중 오류가 발생했습니다: {str(e)}"
            )

    def open_purchase_page(self):
        """구매 페이지 열기"""
        try:
            webbrowser.open(PURCHASE_URL)
        except Exception as e:
            # 기존 창을 최상위에서 일시적으로 해제
            self.root.attributes('-topmost', False)
            
            messagebox.showerror(
                "오류 발생",
                f"구매 페이지를 열 수 없습니다.\n{str(e)}"
            )
            
            # 메인 창을 다시 최상위로 설정
            self.root.attributes('-topmost', True)
            self.root.lift()
    
    def on_close(self):
        """창 닫기 이벤트 처리"""
        # 리소스 정리
        if hasattr(self, 'client'):
            try:
                # 로그아웃이 성공했으면 특수 종료 코드로 종료
                if self.logout_success:
                    print("로그아웃 성공 상태로 종료합니다.")
                    sys.exit(2)
                    
                self.client.close()
            except Exception as e:
                print(f"클라이언트 닫기 오류: {str(e)}")
        
        # 독립 창 모드인 경우 직접 종료
        if self.master is None:
            self.root.destroy()
            
            # 로그아웃했으면 특수 종료 코드로 종료
            if self.logout_success:
                sys.exit(2)

    def check_server_status(self):
        """서버 상태 확인"""
        server_label = self.create_server_status_label()
        
        # 상태 확인 시작
        server_label.config(text="서버 연결 확인 중...")
        self.root.update()
        
        try:
            # 정상 작동하는 엔드포인트 사용
            start_time = time.time()
            response = requests.get(f"{self.client.SERVER_URL}/api/serials", timeout=5)
            
            if response.status_code == 200:
                try:
                    serials = response.json()
                    server_label.config(
                        text=f"서버 상태: 정상 (등록된 시리얼: {len(serials)}개)",
                        foreground="#00796b"
                    )
                except:
                    server_label.config(
                        text="서버 상태: 응답 처리 오류",
                        foreground="#d32f2f"
                    )
            else:
                server_label.config(
                    text=f"서버 상태: 오류 ({response.status_code})",
                    foreground="#d32f2f"
                )
        except requests.exceptions.Timeout:
            server_label.config(
                text="서버 상태: 시간 초과",
                foreground="#ff9800"
            )
        except requests.exceptions.ConnectionError:
            server_label.config(
                text="서버 상태: 연결 실패",
                foreground="#d32f2f"
            )
        except Exception as e:
            server_label.config(
                text=f"서버 상태: 오류 ({str(e)[:30]}...)",
                foreground="#d32f2f"
            )

    def create_server_status_label(self):
        """서버 상태 표시 라벨 생성"""
        # 이미 있는지 확인
        if hasattr(self, 'server_status_label') and self.server_status_label:
            return self.server_status_label
        
        # 새로 생성
        server_frame = ttk.Frame(self.root)
        server_frame.pack(pady=(10, 0), padx=20, fill=tk.X)
        
        server_title = ttk.Label(
            server_frame, 
            text=f"{self.app_name} 서버:",
            font=("Arial", 10)
        )
        server_title.pack(side=tk.LEFT, padx=(0, 5))
        
        self.server_status_label = ttk.Label(
            server_frame,
            text="서버 상태 확인 중...",
            font=("Arial", 10)
        )
        self.server_status_label.pack(side=tk.LEFT)
        
        # 새로고침 버튼
        refresh_button = ttk.Button(
            server_frame,
            text="🔄",
            width=2,
            command=self.check_server_status
        )
        refresh_button.pack(side=tk.RIGHT)
        
        return self.server_status_label

    def create_ui_elements(self):
        """UI 구성 요소 생성"""
        # 스타일 설정
        self.style = ttk.Style()
        self.setup_style()
        
        # 메인 프레임
        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 제목
        title_label = ttk.Label(
            self.main_frame, 
            text=f"{self.app_name} 시리얼 인증", 
            font=("Arial", 16, "bold"),
            foreground="#1a73e8"
        )
        title_label.pack(pady=(0, 20))
        
        # 앱 헤더에 시리얼 정보 추가 - 현재 등록된 시리얼 번호와 만료일 표시
        if self.client and self.client.serial_number:
            try:
                # 데이터베이스에서 실제 시리얼 정보를 확인
                self.client.cursor.execute(
                    "SELECT serial_number, status, expiry_date FROM serial_data WHERE serial_number = ?", 
                    (self.client.serial_number,)
                )
                result = self.client.cursor.fetchone()
                
                if result:
                    serial_number = result[0]
                    status = result[1]
                    expiry_date = result[2]
                    
                    # 현재 날짜와 만료일 비교
                    current_date = datetime.now().date()
                    exp_date = datetime.strptime(expiry_date, "%Y-%m-%d").date()
                    days_left = (exp_date - current_date).days
                    
                    # 헤더에 시리얼 정보 표시 (간략한 형식)
                    serial_header = ttk.Label(
                        self.main_frame,
                        text=f"인증됨: {serial_number[:8]}...{serial_number[-8:]} (만료일: {expiry_date})"
                             f" ({days_left}일 남음)",
                        font=("Arial", 10),
                        foreground="#00796b" if days_left > 30 else "#ff9800" if days_left > 0 else "#d32f2f"
                    )
                    serial_header.pack(pady=(0, 10))
            except Exception as e:
                print(f"시리얼 헤더 생성 오류: {str(e)}")
        
        # 시리얼 상태 정보 프레임
        self.status_frame = ttk.LabelFrame(
            self.main_frame, 
            text="라이센스 상태", 
            padding=10
        )
        self.status_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 상태 레이블
        self.status_label = ttk.Label(
            self.status_frame,
            text="인증 확인 중...",
            font=("Arial", 12)
        )
        self.status_label.pack(anchor=tk.W)
        
        # 만료일 레이블
        self.expiry_label = ttk.Label(
            self.status_frame,
            text="",
            font=("Arial", 10)
        )
        self.expiry_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 로그아웃 버튼 추가
        self.logout_button = tk.Button(
            self.status_frame,
            text="로그아웃",
            command=self.logout_serial,
            bg="#f0f0f0",
            fg="#d32f2f",  # 빨간색 글자색
            activebackground="#e0e0e0",
            activeforeground="#d32f2f",
            font=("Arial", 10),
            padx=8,
            pady=3,
            borderwidth=1,
            relief=tk.RAISED,
            cursor="hand2"
        )
        self.logout_button.pack(anchor=tk.E, pady=(5, 0))
        
        # 시리얼 입력 프레임
        input_frame = ttk.LabelFrame(
            self.main_frame, 
            text="시리얼 번호 입력",
            padding=8  # 패딩 값 축소
        )
        input_frame.pack(fill=tk.X)
        
        # 시리얼 입력 필드
        self.serial_entry = ttk.Entry(
            input_frame,
            width=40,
            font=("Arial", 12)
        )
        self.serial_entry.pack(pady=(5, 8), fill=tk.X)  # 하단 패딩 축소
        
        # 복사/붙여넣기를 위한 키보드 단축키 설정
        self.serial_entry.bind("<Control-c>", self.copy_text)
        self.serial_entry.bind("<Control-v>", self.paste_text)
        self.serial_entry.bind("<Control-a>", self.select_all_text)
        # macOS 단축키 추가
        self.serial_entry.bind("<Command-c>", self.copy_text)
        self.serial_entry.bind("<Command-v>", self.paste_text)
        self.serial_entry.bind("<Command-a>", self.select_all_text)
        
        # 우클릭 메뉴 설정
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="잘라내기", command=self.cut_text)
        self.context_menu.add_command(label="복사", command=self.copy_text)
        self.context_menu.add_command(label="붙여넣기", command=self.paste_text)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="모두 선택", command=self.select_all_text)
        
        # 우클릭 이벤트 바인딩 - 맥에서는 Button-2나 Button-3가 다를 수 있어 여러 버튼 바인딩
        self.serial_entry.bind("<Button-2>", self.show_context_menu)
        self.serial_entry.bind("<Button-3>", self.show_context_menu)
        
        # 버튼 프레임
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill=tk.X, pady=(0, 5))  # 아래쪽 여백 추가
        
        # 각 버튼의 크기와 레이아웃 최적화
        button_width = 8  # 모든 버튼의 기본 너비 설정
        
        # 붙여넣기 버튼
        self.paste_button = tk.Button(
            button_frame,
            text="붙여넣기",
            command=self.paste_text,
            bg="#f0f0f0",
            fg="#333333",
            activebackground="#e0e0e0",
            activeforeground="#333333", 
            font=("Arial", 10),
            padx=5,  # 패딩 축소
            pady=2,  # 패딩 축소
            borderwidth=1,
            relief=tk.RAISED,
            cursor="hand2"
        )
        self.paste_button.pack(side=tk.LEFT, padx=(0, 5))
        self.paste_button.config(width=button_width)
        
        # 인증 버튼
        self.validate_button = tk.Button(
            button_frame,
            text="인증하기",
            command=self.validate_serial,
            bg="#f0f0f0",
            fg="#000000",
            activebackground="#e0e0e0",
            activeforeground="#000000",
            font=("Arial", 10, "bold"),  # 글자 크기 축소
            padx=5,  # 패딩 축소
            pady=2,  # 패딩 축소
            borderwidth=1,
            relief=tk.RAISED,
            cursor="hand2"
        )
        self.validate_button.pack(side=tk.LEFT, padx=(0, 5))
        self.validate_button.config(width=button_width)
        
        # 구매 버튼
        self.purchase_button = tk.Button(
            button_frame,
            text="시리얼 구매",
            command=self.open_purchase_page,
            bg="#f0f0f0",
            fg="#333333",
            activebackground="#e0e0e0",
            activeforeground="#333333", 
            font=("Arial", 10),
            padx=5,  # 패딩 축소
            pady=2,  # 패딩 축소
            borderwidth=1,
            relief=tk.RAISED,
            cursor="hand2"
        )
        self.purchase_button.pack(side=tk.LEFT)
        self.purchase_button.config(width=button_width)
        
        # 정보 프레임
        info_frame = ttk.Frame(self.main_frame, padding=(0, 20, 0, 0))
        info_frame.pack(fill=tk.X)
        
        # 도움말 텍스트
        help_text = (
            "시리얼 번호가 없으신가요? '시리얼 구매' 버튼을 클릭하세요.\n"
            "※ 이미 구매한 시리얼은 입력 후 '인증하기' 버튼을 클릭하세요."
        )
        
        help_label = ttk.Label(
            info_frame,
            text=help_text,
            justify=tk.LEFT,
            wraplength=440
        )
        help_label.pack(anchor=tk.W)
        
        # 저작권 정보
        copyright_label = ttk.Label(
            self.main_frame,
            text=f"© {datetime.now().year} AI Master - 모든 권리 보유",
            font=("Arial", 8),
            foreground="#666666"
        )
        copyright_label.pack(side=tk.BOTTOM, pady=(20, 0))
        
        # 디바이스 정보 섹션
        device_frame = ttk.LabelFrame(self.main_frame, text="디바이스 정보", padding=10)
        device_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 디바이스 정보 테이블 - 높이를 4로 줄임
        columns = ("key", "value")
        self.device_info_table = ttk.Treeview(device_frame, columns=columns, show="headings", height=4)
        
        # 열 설정
        self.device_info_table.heading("key", text="항목")
        self.device_info_table.heading("value", text="정보")
        self.device_info_table.column("key", width=100)
        self.device_info_table.column("value", width=250)
        
        # 스크롤바 설정
        scrollbar = ttk.Scrollbar(device_frame, orient=tk.VERTICAL, command=self.device_info_table.yview)
        self.device_info_table.configure(yscrollcommand=scrollbar.set)
        
        # 배치
        self.device_info_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 초기 디바이스 정보 업데이트
        self.update_device_info()
        
        # 초기 상태 업데이트
        self.update_status()

    def update_device_info(self):
        """디바이스 정보 테이블 업데이트"""
        # 기존 항목 삭제
        for row in self.device_info_table.get_children():
            self.device_info_table.delete(row)
            
        if not self.client or not self.client.device_info:
            # 디바이스 정보가 없는 경우
            self.device_info_table.insert("", "end", values=("상태", "디바이스 정보 없음"))
            return
            
        # 디바이스 정보 표시용 항목 정의
        display_items = [
            ("호스트명", "hostname"),
            ("IP 주소", "ip_address"),
            ("제조사", "system_manufacturer"),
            ("모델", "system_model"),
            ("OS", "os_name"),
            ("OS 버전", "os_version"),
            ("프로세서", "processor"),
            ("메모리", "total_memory"),
            ("등록일", "registration_date"),
            ("디바이스 해시", "device_hash"),
        ]
        
        # 테이블에 표시
        for label, key in display_items:
            value = self.client.device_info.get(key, "-")
            # 해시는 너무 길어서 짧게 표시
            if key == "device_hash" and len(value) > 20:
                value = f"{value[:10]}...{value[-10:]}"
            self.device_info_table.insert("", "end", values=(label, value))

    def close_dialog(self, e=None):
        """Flet 대화상자 닫기 (호환성 위한 더미 함수)"""
        # Flet에서 사용되던 메서드로, 호환성을 위해 유지
        pass

# 독립 실행 시 테스트
if __name__ == "__main__":
    import sys
    
    # 환경 변수에서 앱 이름 가져오기 시도
    app_name = os.environ.get('APP_NAME', 'BlogAutomation')
    print(f"앱 이름: {app_name}")
    
    # 인증 UI 실행
    validator = SerialValidatorUI(app_name=app_name)
    
    # 인증 결과에 따라 종료 코드 설정
    if validator.logout_success:
        # 로그아웃 성공 시 특별한 종료 코드(2) 반환
        print("로그아웃 성공. 앱 재시작이 필요합니다.")
        sys.exit(2)
    elif validator.client.is_valid:
        # 유효한 시리얼일 경우 성공(0) 반환
        sys.exit(0)
    else:
        # 유효하지 않은 시리얼일 경우 실패(1) 반환
        sys.exit(1)

def check_server_status():
    """서버 상태 진단 함수"""
    url = "https://aimaster-serial.onrender.com/api/serials"
    
    try:
        import requests
        response = requests.get(url, timeout=30)
        print(f"상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            serials = response.json()
            print(f"서버가 정상적으로 응답하고 있습니다. 등록된 시리얼: {len(serials)}개")
            return True
        else:
            print(f"서버가 오류 응답을 반환했습니다: {response.status_code}")
            return False
    except Exception as e:
        print(f"서버 연결 오류: {e}")
        return False 