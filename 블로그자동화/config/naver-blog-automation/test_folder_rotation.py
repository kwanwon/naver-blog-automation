#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from folder_manager import ImageFolderManager

def test_folder_rotation():
    """폴더 순환 시스템 테스트"""
    fm = ImageFolderManager()
    
    print("=== 폴더 순환 시스템 테스트 ===\n")
    
    # 3번의 포스팅 시뮬레이션
    for i in range(1, 4):
        print(f"📝 {i}번째 포스팅:")
        current_folder = fm.get_current_folder()
        print(f"   사용할 폴더: {current_folder}")
        
        # 이미지 개수 확인
        images = fm.get_images_from_folder(current_folder)
        print(f"   이미지 개수: {len(images)}장")
        
        # 다음 폴더로 이동 (실제 업로드 완료 후 호출됨)
        next_folder = fm.get_next_folder()
        print(f"   ➡️  다음 폴더로 이동: {next_folder}")
        print()
    
    print("=== 현재 상태 확인 ===")
    fm.show_folder_status()

if __name__ == "__main__":
    test_folder_rotation() 