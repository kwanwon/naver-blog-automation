import PyInstaller.__main__
import flet
import os
import certifi
import shutil
import sys

def build():
    print("🚀 Starting build process with Python script...")

    # 1. 경로 설정
    base_dir = os.getcwd()
    try:
        flet_path = os.path.dirname(flet.__file__)
        flet_bin = os.path.join(flet_path, "bin")
    except Exception as e:
        print(f"⚠️ Warning: Could not find flet path: {e}")
        flet_path = None
        flet_bin = None
    
    print(f"📍 Base Directory: {base_dir}")
    print(f"📍 Flet Path: {flet_path}")

    # 2. PyInstaller 인자 설정
    path_sep = ";" if os.name == 'nt' else ":"
    
    pyinstaller_args = [
        'blog_writer_app.py',
        '--name=BlogAutomation_Windows',
        '--noconsole',
        '--onedir',
        '--clean',
        '--icon=assets/icon.ico',
        # --add-data는 경로가 확실할 때만 추가
        '--collect-all=requests',
        '--collect-all=certifi',
        '--collect-all=flet',
        '--hidden-import=flet.security',
        '--hidden-import=flet.utils',
        '--hidden-import=pandas',
        '--hidden-import=watchdog',
        '--noconfirm',
    ]

    if flet_bin and os.path.exists(flet_bin):
        print(f"✅ Adding flet binaries from: {flet_bin}")
        pyinstaller_args.append(f'--add-data={flet_bin}{path_sep}flet/bin')
    else:
        print(f"⚠️ Warning: Flet binaries not found at {flet_bin}. Skipping --add-data for flet bin.")

    print("🔧 Running PyInstaller with arguments:", pyinstaller_args)

    # 3. PyInstaller 실행
    try:
        PyInstaller.__main__.run(pyinstaller_args)
        print("✅ PyInstaller build completed successfully.")
    except Exception as e:
        print(f"❌ PyInstaller failed: {e}")
        sys.exit(1)

    # 4. 폴더 정리 (dist/BlogAutomation_Windows -> dist/BlogAutomation_Windows_App)
    dist_dir = os.path.join(base_dir, "dist")
    build_dir = os.path.join(dist_dir, "BlogAutomation_Windows")
    target_dir = os.path.join(dist_dir, "BlogAutomation_Windows_App")

    print(f"📂 Organizing output folders...")
    print(f"   Source: {build_dir}")
    print(f"   Target: {target_dir}")

    if os.path.exists(build_dir):
        # 타겟 폴더가 이미 있으면 삭제
        if os.path.exists(target_dir):
            print("   Removing existing target directory...")
            shutil.rmtree(target_dir)
        
        # 이름 변경 (이동)
        os.rename(build_dir, target_dir)
        print(f"✅ Build artifact moved to: {target_dir}")
    else:
        print(f"❌ Error: Build directory not found at {build_dir}")
        # dist 폴더 목록 출력 (디버깅용)
        if os.path.exists(dist_dir):
            print("   Contents of dist folder:", os.listdir(dist_dir))
        else:
            print("   dist folder does not exist.")
        sys.exit(1)

if __name__ == "__main__":
    build()
