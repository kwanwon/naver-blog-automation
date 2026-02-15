import json
import os
import urllib.parse
from datetime import datetime
import sys
import platform

class HistoryManager:
    def __init__(self, history_file=None):
        if history_file:
            self.history_file = history_file
        else:
            # 기본 경로 설정 (OS별/실행환경별 분기)
            if getattr(sys, 'frozen', False):
                # 빌드된 앱: 사용자 데이터 폴더 사용
                if sys.platform == 'win32':
                    base_dir = os.path.join(os.environ.get('APPDATA', ''), 'BlogAutomation')
                elif sys.platform == 'darwin':
                    base_dir = os.path.expanduser('~/Library/Application Support/BlogAutomation')
                else:
                    base_dir = os.path.expanduser('~/.local/share/BlogAutomation')
                
                self.history_file = os.path.join(base_dir, 'data', 'marketing_history.json')
            else:
                # 개발 환경: 로컬 data 폴더 사용
                self.history_file = "data/marketing_history.json"
                
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(os.path.dirname(self.history_file)):
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def load_history(self):
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
            return []

    def add_entry(self, entry):
        """
        Adds a new entry to the history.
        entry should be a dict with keys: 'date', 'keyword', 'title', 'url', 'comment', 'platform'.
        """
        history = self.load_history()
        # Add timestamp if not present
        if 'timestamp' not in entry:
            entry['timestamp'] = datetime.now().isoformat()
        
        # Insert at the beginning (newest first)
        history.insert(0, entry)
        
        self._save_history(history)

    def delete_entry(self, index):
        history = self.load_history()
        if 0 <= index < len(history):
            del history[index]
            self._save_history(history)
            return True
        return False

    def clear_history(self):
        self._save_history([])

    def _save_history(self, history):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def _normalize_url(self, url):
        """
        Normalizes the URL by removing query parameters to prevent duplicates.
        """
        try:
            parsed = urllib.parse.urlparse(url)
            # For Naver Blog, the post ID is usually in the path or as a query param 'logNo'.
            # Case 1: cafe.naver.com/cafename/1234
            # Case 2: blog.naver.com/blogId/1234
            # Case 3: blog.naver.com/PostView.naver?blogId=...&logNo=...
            
            # Simple normalization: remove query params for now, unless it's essential.
            # For Naver blogs with query params, we might need to be careful.
            # But usually, just checking the base path or specific params is better.
            
            # Reconstruct without query params for basic duplicate check if acceptable
            # OR, strictly check if the exact normalized version exists.
            
            # Let's try to keep it simple: Strip query params for standard URLs, 
            # but for Naver specific structures, we might need to handle 'logNo'.
            
            # If it is a Naver blog 'PostView', we need blogId and logNo.
            if "blog.naver.com" in url and "PostView.naver" in url:
                query_params = urllib.parse.parse_qs(parsed.query)
                blog_id = query_params.get('blogId', [''])[0]
                log_no = query_params.get('logNo', [''])[0]
                if blog_id and log_no:
                    return f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
            
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        except:
            return url

    def is_commented(self, url):
        """
        Checks if the URL has already been commented on.
        """
        normalized_target = self._normalize_url(url)
        history = self.load_history()
        
        for entry in history:
            history_url = entry.get('url', '')
            if self._normalize_url(history_url) == normalized_target:
                return True
        return False
