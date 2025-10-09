#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
개발자용 배포 스크립트
간편하게 코드를 배포하고 사용자들에게 자동 업데이트를 제공합니다.
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime

class DeploymentManager:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.version_file = os.path.join(self.script_dir, 'version.json')
        
    def get_current_version(self):
        """현재 버전 가져오기"""
        try:
            if os.path.exists(self.version_file):
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('version', '1.1.0')
            return '1.1.0'
        except Exception as e:
            print(f"⚠️ 버전 파일 읽기 실패: {e}")
            return '1.1.0'
    
    def check_git_status(self):
        """Git 상태 확인"""
        try:
            # 변경사항 확인
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True, cwd=self.script_dir)
            
            if result.returncode != 0:
                print("❌ Git 저장소가 아니거나 Git 명령어를 찾을 수 없습니다.")
                return False
                
            if result.stdout.strip():
                print("📝 변경사항이 감지되었습니다:")
                print(result.stdout)
                return True
            else:
                print("✅ 변경사항이 없습니다.")
                return False
                
        except Exception as e:
            print(f"❌ Git 상태 확인 실패: {e}")
            return False
    
    def get_commit_message(self, change_type="patch"):
        """커밋 메시지 생성"""
        current_version = self.get_current_version()
        
        print(f"\n📝 커밋 메시지를 입력해주세요 (현재 버전: v{current_version})")
        print("예시:")
        print("  🐛 버그 수정")
        print("  ✨ 새로운 기능 추가")
        print("  🔧 성능 개선")
        print("  📝 문서 업데이트")
        
        message = input("\n커밋 메시지: ").strip()
        
        if not message:
            message = "🔧 코드 업데이트"
        
        # 버전 태그 추가
        if change_type == "major":
            message = f"[MAJOR] {message}"
        elif change_type == "minor":
            message = f"[MINOR] {message}"
        # patch는 태그 없음 (기본값)
        
        return message
    
    def deploy(self, change_type="patch", message=None, auto_commit=False):
        """배포 실행"""
        print("🚀 자동 배포 시스템 시작")
        print("=" * 50)
        
        current_version = self.get_current_version()
        print(f"📦 현재 버전: v{current_version}")
        
        # Git 상태 확인
        has_changes = self.check_git_status()
        
        if not has_changes and not auto_commit:
            print("ℹ️ 배포할 변경사항이 없습니다.")
            return True
        
        # 커밋 메시지 생성
        if not message:
            if auto_commit:
                message = "🔧 자동 배포"
                if change_type != "patch":
                    message = f"[{change_type.upper()}] {message}"
            else:
                message = self.get_commit_message(change_type)
        
        print(f"\n📝 커밋 메시지: {message}")
        
        # 사용자 확인
        if not auto_commit:
            confirm = input("\n배포를 진행하시겠습니까? (y/N): ").lower().strip()
            if confirm not in ['y', 'yes', 'ㅇ', '예']:
                print("❌ 배포가 취소되었습니다.")
                return False
        
        try:
            print("\n🔄 배포 진행 중...")
            
            # 1. Git add
            print("1/3 변경사항 스테이징...")
            subprocess.run(['git', 'add', '.'], cwd=self.script_dir, check=True)
            
            # 2. Git commit
            print("2/3 커밋 생성...")
            subprocess.run(['git', 'commit', '-m', message], cwd=self.script_dir, check=True)
            
            # 3. Git push
            print("3/3 GitHub에 푸시...")
            result = subprocess.run(['git', 'push', 'origin', 'main'], 
                                  cwd=self.script_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 배포 완료!")
                print("\n🎉 자동 업데이트 프로세스:")
                print("  1. GitHub Actions가 자동으로 버전 증가")
                print("  2. 새로운 릴리스 자동 생성")
                print("  3. 사용자들이 다음 실행 시 업데이트 알림 받음")
                print("\n🔗 GitHub Actions 상태 확인:")
                print("  https://github.com/kwanwon/naver-blog-automation/actions")
                return True
            else:
                print("❌ 푸시 실패:")
                print(result.stderr)
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"❌ 배포 실패: {e}")
            return False
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            return False
    
    def check_deployment_status(self):
        """배포 상태 확인"""
        print("🔍 배포 상태 확인")
        print("=" * 30)
        
        current_version = self.get_current_version()
        print(f"📦 로컬 버전: v{current_version}")
        
        try:
            # 최근 커밋 확인
            result = subprocess.run(['git', 'log', '--oneline', '-5'], 
                                  capture_output=True, text=True, cwd=self.script_dir)
            
            if result.returncode == 0:
                print("\n📋 최근 커밋:")
                for line in result.stdout.strip().split('\n'):
                    print(f"  {line}")
            
            # 원격 상태 확인
            result = subprocess.run(['git', 'status', '-uno'], 
                                  capture_output=True, text=True, cwd=self.script_dir)
            
            if result.returncode == 0:
                print(f"\n📊 Git 상태:")
                print(result.stdout)
                
        except Exception as e:
            print(f"⚠️ 상태 확인 중 오류: {e}")
    
    def show_help(self):
        """도움말 표시"""
        print("🚀 자동 배포 시스템 사용법")
        print("=" * 40)
        print()
        print("기본 사용법:")
        print("  python deploy.py                    # 대화형 배포 (PATCH 버전)")
        print("  python deploy.py --minor            # MINOR 버전 증가")
        print("  python deploy.py --major            # MAJOR 버전 증가")
        print()
        print("고급 사용법:")
        print("  python deploy.py -m '🐛 버그 수정'    # 커밋 메시지 지정")
        print("  python deploy.py --auto             # 자동 배포 (확인 없음)")
        print("  python deploy.py --status           # 배포 상태 확인")
        print()
        print("버전 관리:")
        print("  PATCH (1.1.0 → 1.1.1): 버그 수정, 작은 개선")
        print("  MINOR (1.1.0 → 1.2.0): 새로운 기능 추가")
        print("  MAJOR (1.1.0 → 2.0.0): 대규모 변경, 호환성 변경")
        print()
        print("자동 업데이트 흐름:")
        print("  1. 코드 수정 → 2. deploy.py 실행 → 3. 자동 버전 증가")
        print("  4. GitHub Release 생성 → 5. 사용자 업데이트 알림")

def main():
    parser = argparse.ArgumentParser(description='자동 배포 시스템')
    parser.add_argument('--minor', action='store_true', help='MINOR 버전 증가')
    parser.add_argument('--major', action='store_true', help='MAJOR 버전 증가')
    parser.add_argument('-m', '--message', help='커밋 메시지')
    parser.add_argument('--auto', action='store_true', help='자동 배포 (확인 없음)')
    parser.add_argument('--status', action='store_true', help='배포 상태 확인')
    parser.add_argument('--help-detail', action='store_true', help='상세 도움말')
    
    args = parser.parse_args()
    
    deployer = DeploymentManager()
    
    if args.help_detail:
        deployer.show_help()
        return
    
    if args.status:
        deployer.check_deployment_status()
        return
    
    # 버전 변경 유형 결정
    change_type = "patch"  # 기본값
    if args.major:
        change_type = "major"
    elif args.minor:
        change_type = "minor"
    
    # 배포 실행
    success = deployer.deploy(
        change_type=change_type,
        message=args.message,
        auto_commit=args.auto
    )
    
    if success:
        print("\n💡 팁: 배포 상태를 확인하려면 'python deploy.py --status'를 실행하세요.")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
