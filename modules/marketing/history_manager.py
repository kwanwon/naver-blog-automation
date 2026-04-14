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
        네이버 블로그/카페 주소를 표준 형식으로 정규화하여 중복 체크의 정확도를 높입니다.
        """
        if not url:
            return ""
            
        try:
            url = url.strip()
            # 1. 쿼리 스트링 분리
            parsed = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed.query)
            
            # --- 네이버 블로그 정규화 ---
            if "blog.naver.com" in url:
                blog_id = ""
                log_no = ""
                
                # Case A: blog.naver.com/blogId/logNo (경로형)
                # Case B: m.blog.naver.com/blogId/logNo (모바일 경로형)
                path_parts = [p for p in parsed.path.split('/') if p]
                if len(path_parts) >= 2 and not path_parts[0].endswith('.naver') and not path_parts[0].endswith('.nhn'):
                    blog_id = path_parts[0]
                    log_no = path_parts[1]
                
                # Case C: blog.naver.com/PostView.naver?blogId=...&logNo=... (쿼리형)
                if not log_no:
                    blog_id = query_params.get('blogId', [''])[0]
                    log_no = query_params.get('logNo', [''])[0]
                
                if blog_id and log_no:
                    # 표준 형식으로 반환: blog.naver.com/blogId/logNo
                    return f"https://blog.naver.com/{blog_id}/{log_no}"

            # --- 네이버 카페 정규화 ---
            if "cafe.naver.com" in url:
                cafe_name = ""
                article_id = ""
                
                # Case A: cafe.naver.com/cafename/1234 (경로형)
                path_parts = [p for p in parsed.path.split('/') if p]
                if len(path_parts) >= 2 and path_parts[0] not in ['ca-fe', 'ArticleRead.nhn', 'ArticleList.nhn']:
                    cafe_name = path_parts[0]
                    article_id = path_parts[1]
                
                # Case B: m.cafe.naver.com/ca-fe/web/cafes/cafename/articles/1234 (모바일)
                if "ca-fe/web/cafes" in url:
                    try:
                        # path_parts: ['ca-fe', 'web', 'cafes', 'cafename', 'articles', '1234']
                        if len(path_parts) >= 6:
                            cafe_name = path_parts[3]
                            article_id = path_parts[5]
                    except:
                        pass
                
                # Case C: ArticleRead.nhn?articleid=...&clubid=... (쿼리형)
                if not article_id:
                    article_id = query_params.get('articleid', [''])[0]
                    # clubid만 있고 cafe_name이 없는 경우 대비
                    club_id = query_params.get('clubid', [''])[0]
                    if club_id and not cafe_name:
                        cafe_name = f"clubid_{club_id}"
                
                if article_id:
                    # 카페명이나 클럽아이디가 있으면 포함, 없으면 포스트번호만이라도 비교
                    prefix = f"/{cafe_name}" if cafe_name else ""
                    return f"https://cafe.naver.com{prefix}/{article_id}"

            # --- 기타 (밴드 등) ---
            # 쿼리 파라미터 제거한 기본 주소 반환
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
            
        except Exception as e:
            print(f"URL 정규화 중 오류: {e}")
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
