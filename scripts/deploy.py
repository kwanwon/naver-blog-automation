#!/usr/bin/env python3
"""
배포 자동화 스크립트 (One-Click Deploy)
- version.json 버전 업데이트
- git add & commit
- git tag 생성
- git push (메인 & 태그)
"""
import os
import json
import sys
import subprocess

def get_current_version():
    with open('version.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('version', '1.0.0')

def update_version_file(new_version):
    with open('version.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    data['version'] = new_version
    
    with open('version.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ version.json 업데이트 완료: {new_version}")

def run_command(cmd):
    print(f"🚀 실행: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌ 명령어 실패: {cmd}")
        sys.exit(1)

def main():
    print("=== 블로그 자동화 배포 도우미 ===")
    current = get_current_version()
    print(f"현재 버전: {current}")
    
    # 버전 입력
    new_version = input(f"새 버전을 입력하세요 (Enter = Patch 업데이트): ").strip()
    
    if not new_version:
        # 1.2.34 -> 1.2.35
        parts = current.split('.')
        parts[-1] = str(int(parts[-1]) + 1)
        new_version = ".".join(parts)
    
    print(f"🎯 목표 버전: {new_version}")
    confirm = input("배포를 진행하시겠습니까? (y/n): ").lower()
    if confirm != 'y':
        print("취소되었습니다.")
        return

    # 1. version.json 업데이트
    update_version_file(new_version)
    
    # 2. Git 작업
    msg = f"Release v{new_version}"
    
    run_command("git add .")
    run_command(f'git commit -m "{msg}"')
    run_command(f"git tag v{new_version}")
    
    print("\n📦 GitHub로 푸시 중... (잠시만 기다려주세요)")
    run_command("git push origin main")
    run_command(f"git push origin v{new_version}")
    
    print("\n✨ 배포 완료!")
    print(f"🔗 릴리스 페이지: https://github.com/kwanwon/naver-blog-automation/releases/tag/v{new_version}")
    print("⏳ 빌드가 완료될 때까지 약 5~10분 정도 소요됩니다.")

if __name__ == "__main__":
    main()
