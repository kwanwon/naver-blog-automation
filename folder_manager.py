#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from datetime import datetime

class ImageFolderManager:
    """이미지 폴더 순환 관리 클래스"""
    
    def __init__(self, base_dir=None):
        self.base_dir = base_dir if base_dir else os.path.abspath(".")
        self.config_file = os.path.join(self.base_dir, 'config', 'folder_index.json')
        self.ensure_config_dir()
    
    def ensure_config_dir(self):
        """config 디렉토리가 없으면 생성"""
        config_dir = os.path.dirname(self.config_file)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
    
    def get_available_folders(self):
        """사용 가능한 이미지 폴더 목록 반환"""
        folders = []
        
        # default_images 폴더 확인
        default_folder = os.path.join(self.base_dir, 'default_images')
        if os.path.exists(default_folder) and self._has_images(default_folder):
            folders.append('default_images')
        
        # default_images_1부터 default_images_10까지 확인
        for i in range(1, 11):
            folder_name = f'default_images_{i}'
            folder_path = os.path.join(self.base_dir, folder_name)
            if os.path.exists(folder_path) and self._has_images(folder_path):
                folders.append(folder_name)
        
        return folders
    
    def _has_images(self, folder_path):
        """폴더에 이미지 파일이 있는지 확인"""
        try:
            for file in os.listdir(folder_path):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    return True
            return False
        except:
            return False
    
    def load_folder_index(self):
        """현재 폴더 인덱스 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('current_index', 0)
            return 0
        except Exception as e:
            print(f"폴더 인덱스 로드 오류: {e}")
            return 0
    
    def save_folder_index(self, index):
        """폴더 인덱스 저장"""
        try:
            data = {
                'current_index': index,
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"폴더 인덱스 저장 오류: {e}")
    
    def get_current_folder(self):
        """현재 사용할 폴더 반환"""
        available_folders = self.get_available_folders()
        if not available_folders:
            print("사용 가능한 이미지 폴더가 없습니다.")
            return None
        
        current_index = self.load_folder_index()
        
        # 인덱스가 폴더 수를 초과하면 0으로 리셋
        if current_index >= len(available_folders):
            current_index = 0
        
        current_folder = available_folders[current_index]
        print(f"현재 사용할 폴더: {current_folder} (인덱스: {current_index}/{len(available_folders)-1})")
        
        return current_folder
    
    def get_next_folder(self):
        """다음 폴더로 이동하고 폴더명 반환"""
        available_folders = self.get_available_folders()
        if not available_folders:
            print("사용 가능한 이미지 폴더가 없습니다.")
            return None
        
        current_index = self.load_folder_index()
        next_index = (current_index + 1) % len(available_folders)
        
        # 다음 인덱스 저장
        self.save_folder_index(next_index)
        
        next_folder = available_folders[next_index]
        print(f"다음 폴더로 이동: {next_folder} (인덱스: {next_index}/{len(available_folders)-1})")
        
        return next_folder
    
    def get_folder_path(self, folder_name):
        """폴더명으로 전체 경로 반환"""
        if not folder_name:
            return None
        return os.path.join(self.base_dir, folder_name)
    
    def get_images_from_folder(self, folder_name):
        """특정 폴더에서 이미지 파일 목록 반환"""
        folder_path = self.get_folder_path(folder_name)
        if not folder_path or not os.path.exists(folder_path):
            return []
        
        images = []
        try:
            for file in os.listdir(folder_path):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    full_path = os.path.join(folder_path, file)
                    images.append(full_path)
        except Exception as e:
            print(f"폴더 {folder_name}에서 이미지 읽기 오류: {e}")
        
        return sorted(images)
    
    def reset_folder_index(self):
        """폴더 인덱스를 0으로 리셋"""
        self.save_folder_index(0)
        print("폴더 인덱스가 0으로 리셋되었습니다.")
    
    def show_folder_status(self):
        """현재 폴더 상태 출력"""
        available_folders = self.get_available_folders()
        current_index = self.load_folder_index()
        
        print(f"\n=== 이미지 폴더 상태 ===")
        print(f"사용 가능한 폴더 수: {len(available_folders)}")
        print(f"현재 인덱스: {current_index}")
        
        for i, folder in enumerate(available_folders):
            marker = "👉" if i == current_index else "  "
            image_count = len(self.get_images_from_folder(folder))
            print(f"{marker} {i}: {folder} ({image_count}장)")
        print("========================\n") 