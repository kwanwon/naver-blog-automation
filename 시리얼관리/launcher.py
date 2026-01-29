#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import requests
import zipfile
import shutil
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
from threading import Thread

# 설정
REPO_OWNER = "kwanwon"
REPO_NAME = "naver-blog-automation"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(CURRENT_DIR, "version.json")
MAIN_PROGRAM = os.path.join(CURRENT_DIR, "start_program.command")  # 실행할 메인 프로그램

# 색상 및 스타일
BG_COLOR = "#2C3E50"
FG_COLOR = "#ECF0F1"
ACCENT_COLOR = "#3498DB"

class UpdateLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Launcher")
        self.root.geometry("400x250")
        self.root.configure(bg=BG_COLOR)
        self.root.overrideredirect(True)  # 프레임 없는 창
        
        # 화면 중앙 배치
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 250) // 2
        self.root.geometry(f"400x250+{x}+{y}")
        
        self.status_var = tk.StringVar(value="업데이트 확인 중...")
        
        self.create_ui()
        
        # 업데이트 확인 시작
        Thread(target=self.check_and_update, daemon=True).start()
    
    def create_ui(self):
        main_frame = tk.Frame(self.root, bg=BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 제목
        tk.Label(main_frame, text="Blog Automation Launcher", 
                 font=("Helvetica", 16, "bold"), bg=BG_COLOR, fg=FG_COLOR).pack(pady=(10, 20))
        
        # 상태 메시지
        self.status_label = tk.Label(main_frame, textvariable=self.status_var, 
                 font=("Helvetica", 10), bg=BG_COLOR, fg=FG_COLOR)
        self.status_label.pack(pady=10)
        
        # 프로그레스바
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', length=300)
        self.progress.pack(pady=10)
        self.progress.start(10)
        
        # 버전 정보
        self.version_label = tk.Label(main_frame, text=f"Current: {self.get_local_version()}", 
                 font=("Helvetica", 8), bg=BG_COLOR, fg="#95A5A6")
        self.version_label.pack(side=tk.BOTTOM, pady=5)

    def get_local_version(self):
        try:
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, "r") as f:
                    data = json.load(f)
                    return data.get("version", "0.0.0")
        except:
            pass
        return "0.0.0"

    def check_and_update(self):
        try:
            local_version = self.get_local_version()
            
            # GitHub Release 확인
            try:
                response = requests.get(GITHUB_API_URL, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    latest_tag = data.get("tag_name", "").replace("v", "")
                    assets = data.get("assets", [])
                    
                    if latest_tag > local_version:
                        self.root.after(0, lambda: self.prompt_update(latest_tag, assets))
                        return
            except Exception as e:
                print(f"Update check failed: {e}")
            
            # 업데이트 없으면 실행
            self.root.after(0, lambda: self.status_var.set("최신 버전입니다. 실행 중..."))
            time.sleep(1)
            self.root.after(0, self.launch_program)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Launcher Error: {str(e)}"))
            self.root.after(0, self.launch_program)

    def prompt_update(self, latest_version, assets):
        if messagebox.askyesno("업데이트 발견", f"새로운 버전 ({latest_version})이 있습니다.\n업데이트 하시겠습니까?"):
            self.download_update(assets, latest_version)
        else:
            self.launch_program()

    def download_update(self, assets, latest_version):
        self.status_var.set("업데이트 다운로드 중...")
        self.progress.stop()
        self.progress.configure(mode='determinate')
        
        # 적절한 asset 찾기 (zip 파일 우선)
        download_url = None
        for asset in assets:
            if asset['name'].endswith('.zip'):
                download_url = asset['browser_download_url']
                break
        
        if not download_url and assets:
            download_url = assets[0]['browser_download_url']
        
        if not download_url:
            messagebox.showerror("오류", "다운로드 파일을 찾을 수 없습니다.")
            self.launch_program()
            return
            
        # 다운로드 및 압축 해제 로직
        try:
            zip_path = os.path.join(CURRENT_DIR, "update.zip")
            response = requests.get(download_url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(zip_path, 'wb') as f:
                downloaded = 0
                for data in response.iter_content(chunk_size=4096):
                    f.write(data)
                    downloaded += len(data)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        self.root.after(0, lambda: self.progress.configure(value=percent))
                        self.root.after(0, lambda: self.status_var.set(f"다운로드 중... {int(percent)}%"))
            
            self.status_var.set("압축 해제 및 설치 중...")
            
            # 압축 해제
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(CURRENT_DIR)
            
            # 버전 업데이트 (version.json)
            with open(VERSION_FILE, "w") as f:
                json.dump({"version": latest_version}, f, indent=4)
                
            os.remove(zip_path)
            
            messagebox.showinfo("완료", "업데이트가 완료되었습니다. 프로그램을 재시작합니다.")
            self.launch_program()
            
        except Exception as e:
            messagebox.showerror("업데이트 실패", f"오류: {str(e)}")
            self.launch_program()

    def launch_program(self):
        self.root.destroy()
        try:
            # 운영체제별 실행 파일 설정
            if sys.platform == "win32":
                # Windows: BlogApp.exe 실행
                target = "BlogApp.exe"
                if os.path.exists(os.path.join(CURRENT_DIR, target)):
                    subprocess.Popen([target])
                else:
                    # 개발 환경 fallback
                    subprocess.Popen(["python", "start_program.py"], shell=True)
            else:
                # macOS/Linux: start_program.command 또는 앱 번들 실행
                # 배포 환경에서는 내부의 실행파일을 호출해야 함
                if os.path.exists(os.path.join(CURRENT_DIR, "BlogApp.app")):
                    subprocess.Popen(["open", "BlogApp.app"])
                elif os.path.exists(os.path.join(CURRENT_DIR, "start_program.command")):
                    subprocess.Popen(["open", "-a", "Terminal", os.path.join(CURRENT_DIR, "start_program.command")])
                else:
                    messagebox.showerror("실행 오류", "실행할 프로그램을 찾을 수 없습니다.")
                    sys.exit(1)
                    
        except Exception as e:
            messagebox.showerror("실행 오류", f"프로그램 실행 실패: {e}")
            sys.exit(1)

if __name__ == "__main__":
    app = UpdateLauncher()
    app.root.mainloop()
