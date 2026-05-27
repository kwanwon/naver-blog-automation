import os
import shutil
import sys

def init_secure_project():
    print("🛸 Antigravity Secure Project Initializer (ASR v1.1)")
    print("-" * 50)
    
    project_name = input("프로젝트 이름을 입력하세요: ").strip().replace(" ", "_")
    if not project_name:
        print("❌ 프로젝트 이름을 입력해야 합니다.")
        return
        
    target_dir = os.path.abspath(os.path.join(os.getcwd(), "..", project_name))
    
    if os.path.exists(target_dir):
        print(f"⚠️ 이미 존재하는 폴더입니다: {target_dir}")
        overwrite = input("덮어쓰시겠습니까? (y/n): ").lower()
        if overwrite != 'y':
            print("❌ 작업을 취소합니다.")
            return

    # 1. 스타터 킷 소스 경로 확인 (현재 스크립트 위치 기준)
    starter_kit_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "antigravity_starter_kit"))
    
    if not os.path.exists(starter_kit_path):
        print(f"❌ 스타터 킷 폴더를 찾을 수 없습니다: {starter_kit_path}")
        return

    # 2. 폴더 복사
    try:
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        shutil.copytree(starter_kit_path, target_dir)
        print(f"✅ 프로젝트 생성 완료: {target_dir}")
        print("-" * 50)
        print(f"👉 시작하려면: cd {project_name} && python main.py")
        print("-" * 50)
        print("💡 Antigravity Security Rule (ASR)이 모든 파일에 적용되었습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    init_secure_project()
