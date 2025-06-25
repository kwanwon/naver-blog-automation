#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
기존 크롬 프로필 폴더 정리 스크립트
manual_chrome_profile만 남기고 나머지는 삭제
"""

import os
import shutil
import glob

def cleanup_chrome_profiles():
    """기존 크롬 프로필 폴더들 정리"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("🧹 크롬 프로필 폴더 정리 시작...")
    
    # 삭제할 패턴들
    patterns_to_delete = [
        "chrome_profile_*",  # 타임스탬프가 있는 프로필들
        "chrome_profile_manual_*"  # 기존 수동 프로필들
    ]
    
    # 보존할 폴더
    keep_folders = [
        "manual_chrome_profile"  # 새로운 통합 프로필
    ]
    
    deleted_count = 0
    
    for pattern in patterns_to_delete:
        folders = glob.glob(os.path.join(base_dir, pattern))
        
        for folder_path in folders:
            folder_name = os.path.basename(folder_path)
            
            if folder_name not in keep_folders:
                try:
                    print(f"삭제 중: {folder_name}")
                    shutil.rmtree(folder_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"삭제 실패: {folder_name} - {e}")
    
    print(f"✅ 정리 완료! {deleted_count}개 폴더 삭제됨")
    print(f"보존된 폴더: manual_chrome_profile")

if __name__ == "__main__":
    cleanup_chrome_profiles() 