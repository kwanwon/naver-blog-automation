#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from folder_manager import ImageFolderManager
from naver_blog_auto_image import NaverBlogImageInserter
import os

def debug_image_insertion():
    """이미지 삽입 문제 디버깅"""
    
    print("=== 이미지 삽입 디버깅 시작 ===\n")
    
    # 1. 폴더 관리자 테스트
    print("1️⃣ 폴더 관리자 테스트:")
    fm = ImageFolderManager()
    fm.show_folder_status()
    
    current_folder = fm.get_current_folder()
    print(f"현재 사용할 폴더: {current_folder}")
    
    if current_folder:
        images = fm.get_images_from_folder(current_folder)
        print(f"해당 폴더의 이미지 개수: {len(images)}장")
        if images:
            print(f"첫 번째 이미지: {images[0]}")
            print(f"이미지 파일 존재 확인: {os.path.exists(images[0])}")
    
    print("\n" + "="*50)
    
    # 2. 이미지 인서터 초기화 테스트 (드라이버 없이)
    print("\n2️⃣ 이미지 인서터 초기화 테스트:")
    try:
        # 드라이버 없이 초기화해서 get_image_files만 테스트
        inserter = NaverBlogImageInserter(driver=None)
        print("✅ 이미지 인서터 초기화 성공")
        
        # get_image_files 메서드 테스트
        print("\n📁 get_image_files() 메서드 테스트:")
        image_files = inserter.get_image_files()
        print(f"반환된 이미지 개수: {len(image_files)}")
        
        if image_files:
            print("✅ 이미지 파일 목록 획득 성공")
            for i, img in enumerate(image_files[:3]):  # 처음 3개만 출력
                print(f"  {i+1}. {img}")
            if len(image_files) > 3:
                print(f"  ... 외 {len(image_files)-3}개")
        else:
            print("❌ 이미지 파일을 찾을 수 없음")
            
    except Exception as e:
        print(f"❌ 이미지 인서터 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== 디버깅 완료 ===")

if __name__ == "__main__":
    debug_image_insertion() 