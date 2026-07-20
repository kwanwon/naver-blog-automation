#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from datetime import datetime
import unicodedata

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
        
        # '블로그사진폴더' 경로를 먼저 확인
        blog_photo_dir = os.path.join(self.base_dir, '블로그사진폴더')
        search_base = blog_photo_dir if os.path.exists(blog_photo_dir) else self.base_dir
        
        # default_images 폴더 확인
        default_folder = os.path.join(search_base, 'default_images')
        if os.path.exists(default_folder) and self._has_images(default_folder):
            folders.append('default_images')
        
        # default_images_1부터 default_images_10까지 확인
        for i in range(1, 11):
            folder_name = f'default_images_{i}'
            folder_path = os.path.join(search_base, folder_name)
            if os.path.exists(folder_path) and self._has_images(folder_path):
                folders.append(folder_name)
        
        return folders
    
    def _has_images(self, folder_path):
        """폴더에 이미지 파일이 있는지 확인"""
        try:
            for file in os.listdir(folder_path):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.mov', '.avi', '.mkv', '.webm')):
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
        """폴더명으로 전체 경로 반환 ('블로그사진폴더' 우선 탐색 및 macOS 자모음 정규화 처리)"""
        if not folder_name:
            return None
            
        # 1. '블로그사진폴더' 하위 경로를 1순위로 조립 및 검사
        gym_img_dir = os.path.join(self.base_dir, '블로그사진폴더')
        if os.path.exists(gym_img_dir):
            target_path = os.path.join(gym_img_dir, folder_name)
            
            # macOS 한글 자모음 정규화 호환 다중 확인
            if os.path.exists(target_path):
                return target_path
                
            nfc_p = unicodedata.normalize('NFC', target_path)
            if os.path.exists(nfc_p):
                return nfc_p
                
            nfd_p = unicodedata.normalize('NFD', target_path)
            if os.path.exists(nfd_p):
                return nfd_p
                
            return target_path
            
        # 2. 2순위 디렉토리 (프로젝트 루트 기준)
        fallback_path = os.path.join(self.base_dir, folder_name)
        if os.path.exists(fallback_path):
            return fallback_path
            
        nfc_f = unicodedata.normalize('NFC', fallback_path)
        if os.path.exists(nfc_f):
            return nfc_f
            
        nfd_f = unicodedata.normalize('NFD', fallback_path)
        if os.path.exists(nfd_f):
            return nfd_f
            
        return fallback_path
    
    def get_images_from_folder(self, folder_name):
        """특정 폴더에서 이미지 파일 목록 반환"""
        folder_path = self.get_folder_path(folder_name)
        if not folder_path or not os.path.exists(folder_path):
            return []
        
        images = []
        try:
            for file in os.listdir(folder_path):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.mov', '.avi', '.mkv', '.webm')):
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

    def load_smart_rules(self):
        """Load AI folder keyword mapping rules from JSON."""
        rules_file = os.path.join(self.base_dir, 'config', 'smart_folder_rules.json')
        if not os.path.exists(rules_file):
            return {}
        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading smart rules: {e}")
            return {}

    def save_smart_rules(self, rules):
        """Save AI folder keyword mapping rules to JSON."""
        rules_file = os.path.join(self.base_dir, 'config', 'smart_folder_rules.json')
        rules_dir = os.path.dirname(rules_file)
        if not os.path.exists(rules_dir):
            os.makedirs(rules_dir, exist_ok=True)
        try:
            with open(rules_file, 'w', encoding='utf-8') as f:
                json.dump(rules, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving smart rules: {e}")

    def get_all_subfolders(self):
        """Scan and return all subfolders containing image files, excluding system folders."""
        excluded_dirs = {
            'venv', '.venv', '.git', '.agent', '.agents', '.cursor', 'modules', 'config', 'logs',
            'temp', 'chromedriver', 'chrome_profile', '__pycache__', 'scratch', 'tests', 'build',
            'dist', 'assets', 'resources', 'installer', 'settings', '_temp_upload', 'chrome_data',
            'naver_automation_profile', 'manual_chrome_profile', 'default_images', 'temp_images'
        }
        
        folders = []
        
        # Check standard Gym blog image folder priority
        gym_img_dir = os.path.join(self.base_dir, '블로그사진폴더')
        scan_base = gym_img_dir if os.path.exists(gym_img_dir) else self.base_dir
        
        try:
            for item in os.listdir(scan_base):
                item_path = os.path.join(scan_base, item)
                if os.path.isdir(item_path) and item not in excluded_dirs and not item.startswith('.'):
                    if self._has_images(item_path):
                        # Store relative path from scan_base
                        folders.append(item)
        except Exception as e:
            print(f"Error scanning subfolders: {e}")
            
        return folders

    def get_folder_priority(self, folder_name):
        """Calculate initial match priority based on folder names (Gym specific)."""
        name = folder_name.lower()
        if '대회' in name or 'competition' in name:
            return 5
        elif '대련' in name or 'sparring' in name:
            return 4
        elif '기술' in name or 'technique' in name:
            return 3
        elif '체육' in name or 'sports' in name or '종목' in name:
            return 2
        return 1

    def scan_and_learn_keywords(self, ai_ask_fn=None, force_rescan=False):
        """Scan Gym image folders and extract associated keywords via AI learning."""
        current_rules = self.load_smart_rules()
        if force_rescan:
            current_rules = {}
            
        folders = self.get_all_subfolders()
        if not folders:
            return {}
            
        updated = False
        for folder in folders:
            if folder in current_rules and not force_rescan:
                continue
                
            priority = self.get_folder_priority(folder)
            keywords = [folder]  # Folder name is always a keyword
            
            # 단순 글자 쪼개기(morphological breakdown)는 '음악줄넘기' -> '음악' 등 
            # 치명적인 오작동(음악학원 매칭)을 유발하므로 삭제합니다.
            
            # If AI helper function is provided, fetch richer keyword context
            if ai_ask_fn:
                prompt = (
                    f"당신은 체육관(태권도, 합기도 등) 블로그 마케팅 전문가입니다.\n"
                    f"주어진 폴더 이름: '{folder}'\n"
                    f"이 폴더 이름과 '가장 직접적이고 직관적으로 일치하는' 단어 딱 1개~3개만 추출하세요.\n"
                    f"절대 금지: '뛰기', '점핑', '음악', '학원', '훈련', '수업', '체육관', '스포츠' 처럼 다른 종목과 겹칠 수 있는 단어나 포괄적 명사는 절대 넣지 마세요. 사용자가 정확한 명칭을 쓸 때만 매칭되도록 극도로 보수적으로 뽑으세요.\n"
                    f"[예시 1] 폴더가 '줄넘기'일 경우 -> 줄넘기 (O) / 음악줄넘기, 뛰기, 점핑 (X)\n"
                    f"[예시 2] 폴더가 '호신술'일 경우 -> 호신술, 호신, 셀프디펜스 (O) / 방어, 기술, 실전 (X)\n"
                    f"[예시 3] 폴더가 '발차기'일 경우 -> 발차기, 킥 (O) / 차기, 공격, 다리 (X)\n"
                    f"출력 형식: 다른 설명 없이 콤마(,)로 구분된 1~3개의 단어만 한 줄로 출력하세요."
                )
                try:
                    ai_res = ai_ask_fn(prompt)
                    if ai_res:
                        extracted = [kw.strip() for kw in ai_res.split(',') if kw.strip()]
                        if extracted:
                            keywords.extend(extracted)
                except Exception as e:
                    print(f"AI learning failed for folder '{folder}': {e}")
                    
            # Deduplicate keywords
            keywords = list(set(keywords))
            
            current_rules[folder] = {
                "keywords": keywords,
                "priority": priority,
                "learned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            updated = True
            
        if updated:
            self.save_smart_rules(current_rules)
            
        return current_rules

    def find_matching_folder(self, text, title):
        """Analyze post title & body to select the best matching image folder."""
        print(f"[Step 1] [FolderManager] 스마트 이미지 매칭 수행 (주제: '{title}') (상태: 시도)")
        rules = self.load_smart_rules()
        if rules is None:
            rules = {}
            
        # 모든 하위 폴더를 스캔하여 rules에 없는 경우 기본 키워드(폴더명)로 자동 추가
        all_folders = self.get_all_subfolders()
        for folder in all_folders:
            if folder.startswith("default_images"):
                continue
            if folder not in rules:
                rules[folder] = {
                    "keywords": [folder],
                    "priority": self.get_folder_priority(folder)
                }
            else:
                if folder not in rules[folder].get("keywords", []):
                    rules[folder].setdefault("keywords", []).append(folder)
                    
        if not rules:
            print("[Warning] [FolderManager] 매칭할 수 있는 특정 주제 폴더가 없어 기본 폴더 순환을 사용합니다.")
            return self.get_current_folder()
            
        best_folder = None
        max_score = -1
        
        # Normalize search inputs to NFC (Standard Korean compatibility)
        norm_title = unicodedata.normalize('NFC', title).strip().lower()
        norm_text = unicodedata.normalize('NFC', text).strip().lower()
        search_text = (norm_title + " " + norm_text)
        
        print(f"[DEBUG] [FolderManager] 정규화 검색어: '{search_text}'")
        
        for folder, rule in rules.items():
            score = 0
            keywords = rule.get("keywords", [])
            priority = rule.get("priority", 1)
            
            # Normalize folder name to NFC for strict priority substring checking
            norm_folder = unicodedata.normalize('NFC', folder).lower()
            
            # Score matches based on NFC normalized keyword frequency
            for kw in keywords:
                norm_kw = unicodedata.normalize('NFC', kw).strip().lower()
                if not norm_kw or len(norm_kw) < 2:
                    continue
                
                # Check for direct matches in search text
                if norm_kw in search_text:
                    # Grant higher weight for matching in title
                    title_weight = 3 if norm_kw in norm_title else 1
                    matches_count = search_text.count(norm_kw)
                    score += matches_count * title_weight
                    
            # Boost score based on folder priority
            if score > 0:
                score += priority
                print(f"[DEBUG] [FolderManager] 매칭 후보 폴더: '{folder}' (Score: {score}, Priority: {priority})")
                
            if score > max_score:
                max_score = score
                best_folder = folder
                
        # If no keywords matched, rotate sequentially via sequential list
        if max_score <= 0 or not best_folder:
            print(f"[Step 1] [FolderManager] 매칭되는 키워드가 없어 순차 폴더 순환으로 전환 (상태: 실패)")
            return self.get_current_folder()
            
        print(f"[Step 1] [FolderManager] 스마트 이미지 매칭 결과: 폴더 '{best_folder}' (Score: {max_score}) (상태: 성공)")
        return best_folder 