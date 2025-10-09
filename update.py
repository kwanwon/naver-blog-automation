#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수동 업데이트 스크립트
블로그 자동화 프로그램을 수동으로 업데이트합니다.
"""

import os
import sys
import json
from modules.auto_updater import AutoUpdater

def main():
    """메인 함수"""
    print("=" * 50)
    print("🔄 블로그 자동화 프로그램 업데이트")
    print("=" * 50)
    
    try:
        # 현재 버전 확인
        current_dir = os.path.dirname(os.path.abspath(__file__))
        version_file = os.path.join(current_dir, 'version.json')
        
        current_version = '1.0.0'
        if os.path.exists(version_file):
            with open(version_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                current_version = data.get('version', '1.0.0')
                
        print(f"📦 현재 버전: v{current_version}")
        
        # 업데이터 초기화
        updater = AutoUpdater(current_version)
        
        # 원격 버전 확인
        print("🌐 원격 저장소에서 버전 확인 중...")
        remote_version, changelog = updater.get_remote_version()
        
        if not remote_version:
            print("❌ 원격 버전을 확인할 수 없습니다.")
            print("🌐 인터넷 연결을 확인해주세요.")
            return False
            
        print(f"🆕 최신 버전: v{remote_version}")
        
        # 버전 비교
        if not updater.compare_versions(remote_version):
            print("✅ 현재 버전이 최신입니다!")
            return True
            
        # 변경사항 표시
        if changelog:
            print("\n📋 변경사항:")
            for i, change in enumerate(changelog, 1):
                print(f"  {i}. {change}")
                
        # 업데이트 확인
        print(f"\n🔄 v{current_version} → v{remote_version} 업데이트를 진행하시겠습니까?")
        response = input("계속하려면 'y' 또는 'yes'를 입력하세요: ").lower().strip()
        
        if response not in ['y', 'yes', 'ㅇ', '예']:
            print("❌ 업데이트가 취소되었습니다.")
            return False
            
        # 업데이트 실행
        print("\n🚀 업데이트를 시작합니다...")
        print("⚠️  업데이트 중에는 프로그램을 종료하지 마세요!")
        
        success, message = updater.check_and_update()
        
        if success:
            print(f"\n✅ {message}")
            print("🎉 업데이트가 성공적으로 완료되었습니다!")
            print("📝 모든 설정과 시리얼 정보는 안전하게 보존되었습니다.")
            print("\n🔄 프로그램을 다시 시작해주세요.")
            return True
        else:
            print(f"\n❌ 업데이트 실패: {message}")
            print("💡 문제가 지속되면 개발자에게 문의해주세요.")
            return False
            
    except KeyboardInterrupt:
        print("\n\n❌ 사용자에 의해 업데이트가 중단되었습니다.")
        return False
        
    except Exception as e:
        print(f"\n❌ 업데이트 중 오류 발생: {e}")
        print("💡 문제가 지속되면 개발자에게 문의해주세요.")
        return False
        
    finally:
        print("\n" + "=" * 50)
        input("계속하려면 Enter 키를 누르세요...")


if __name__ == "__main__":
    main()
