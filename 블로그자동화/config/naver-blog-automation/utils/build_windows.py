import os
import shutil
import subprocess
import sys
import glob

def build():
    print("🚀 Starting build process with flet pack...")

    # 1. flet pack 실행
    cmd = [
        "flet", "pack", "blog_writer_app.py",
        "--name", "BlogAutomation_Windows",
        "--icon", "assets/icon.ico",
        "--copyright", "LionDeveloper"
    ]
    
    print(f"🔧 Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode != 0:
        print("❌ flet pack failed.")
        sys.exit(1)
        
    print("✅ flet pack completed successfully.")

    # 2. 결과물 이동 및 정리
    # flet pack은 dist 폴더에 BlogAutomation_Windows.exe를 생성하거나
    # dist/BlogAutomation_Windows.exe 로 생성함.
    
    dist_dir = "dist"
    target_dir = os.path.join(dist_dir, "BlogAutomation_Windows_App")
    
    # 타겟 폴더 초기화
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir)
    
    # exe 파일 찾기 (재귀적)
    exe_files = glob.glob(f"{dist_dir}/**/*.exe", recursive=True)
    
    if not exe_files:
        print("❌ Error: No .exe file found in dist folder!")
        # 디버깅: 파일 목록 출력
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                print(os.path.join(root, file))
        sys.exit(1)
        
    src_exe = exe_files[0]
    dst_exe = os.path.join(target_dir, "BlogAutomation_Windows.exe")
    
    print(f"📦 Found executable: {src_exe}")
    print(f"🚚 Moving to: {dst_exe}")
    
    shutil.move(src_exe, dst_exe)
    
    print("✅ Build artifact prepared successfully.")

if __name__ == "__main__":
    build()
