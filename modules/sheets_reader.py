"""
구글 스프레드시트 읽기 모듈 (API 키 없이)
- 공유 링크를 CSV 내보내기 URL로 변환
- pandas 또는 requests로 읽기
- 오늘 날짜의 수련내용 매칭
"""

import os
import re
from datetime import datetime
from typing import Optional, Dict, List
from io import StringIO, BytesIO

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("⚠️ pandas 라이브러리가 설치되지 않았습니다. pip install pandas")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️ requests 라이브러리가 설치되지 않았습니다. pip install requests")


class GoogleSheetsReader:
    """
    구글 스프레드시트 CSV 읽기 (API 키 없이)
    
    시트 컬럼 구조:
    - A열: 날짜 (YYYY-MM-DD 또는 MM/DD 등)
    - B열: 요일
    - C열: 수련내용
    """
    
    def __init__(self, sheet_url: str = None, sheet_name: str = None, read_mode: str = 'csv'):
        """
        Args:
            sheet_url: 구글 스프레드시트 공유 URL
            sheet_name: 특정 시트 이름 (없으면 첫 번째 시트)
            read_mode: 'csv' (단일 탭) 또는 'xlsx' (모든 탭 로드)
        """
        self.sheet_url = sheet_url
        self.sheet_name = sheet_name
        self.read_mode = read_mode
        self.data: Optional[pd.DataFrame] = None
        self.all_sheets_data: Dict[str, pd.DataFrame] = {}
        self.last_fetch_time: Optional[datetime] = None
        self.cache_minutes = 5  # 5분 캐시
    
    def set_url(self, sheet_url: str):
        """스프레드시트 URL 설정"""
        self.sheet_url = sheet_url
        self.data = None  # 캐시 초기화
    
    def set_sheet_name(self, sheet_name: str):
        """시트 이름 설정"""
        self.sheet_name = sheet_name
        self.data = None
        
    def _convert_to_xlsx_url(self, share_url: str) -> str:
        """
        공유 URL을 Excel(.xlsx) 내보내기 URL로 변환
        """
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, share_url)
        
        if not match:
            raise ValueError(f"유효하지 않은 구글 스프레드시트 URL: {share_url}")
            
        sheet_id = match.group(1)
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    
    def _convert_to_csv_url(self, share_url: str) -> str:
        """
        공유 URL을 CSV 내보내기 URL로 변환
        
        입력 예시:
        - https://docs.google.com/spreadsheets/d/1ABC123/edit?usp=sharing
        - https://docs.google.com/spreadsheets/d/1ABC123/edit#gid=0
        
        출력:
        - https://docs.google.com/spreadsheets/d/1ABC123/gviz/tq?tqx=out:csv&gid=0
        """
        # 스프레드시트 ID 추출
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, share_url)
        
        if not match:
            raise ValueError(f"유효하지 않은 구글 스프레드시트 URL: {share_url}")
        
        sheet_id = match.group(1)
        
        # gid 추출 (없으면 0)
        gid_pattern = r'gid=(\d+)'
        gid_match = re.search(gid_pattern, share_url)
        gid = gid_match.group(1) if gid_match else '0'
        
        print(f"   📋 Sheet ID: {sheet_id[:20]}...")
        print(f"   📋 GID 추출됨: {gid}")
        
        # gviz/tq 형식 사용 (export 형식보다 안정적)
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}"
        return csv_url
    
    def fetch_data(self, force_refresh: bool = False) -> bool:
        """
        스프레드시트 데이터 가져오기
        
        Args:
            force_refresh: 캐시 무시하고 강제 갱신
        
        Returns:
            성공 여부
        """
        if not PANDAS_AVAILABLE or not REQUESTS_AVAILABLE:
            print("❌ pandas와 requests 라이브러리가 필요합니다.")
            return False
        
        if not self.sheet_url:
            print("❌ 스프레드시트 URL이 설정되지 않았습니다.")
            return False
        
        # 캐시 확인
        if not force_refresh and self.data is not None and self.last_fetch_time:
            elapsed = (datetime.now() - self.last_fetch_time).total_seconds() / 60
            if elapsed < self.cache_minutes:
                print(f"ℹ️ 캐시 사용 (마지막 갱신: {elapsed:.1f}분 전)")
                return True
                
        # 로컬 파일인지 확인
        is_local_file = False
        if not self.sheet_url.startswith('http'):
            if os.path.exists(self.sheet_url):
                is_local_file = True
            else:
                print(f"❌ 파일을 찾을 수 없습니다: {self.sheet_url}")
                return False

        if is_local_file:
            try:
                print(f"📊 로컬 엑셀 파일 읽는 중... {self.sheet_url}")
                self.all_sheets_data = pd.read_excel(self.sheet_url, sheet_name=None)
                if not self.all_sheets_data:
                    return False
                for sheet, df in self.all_sheets_data.items():
                    df.columns = [str(col).strip() for col in df.columns]
                first_sheet = list(self.all_sheets_data.keys())[0]
                self.data = self.all_sheets_data[first_sheet]
                self.last_fetch_time = datetime.now()
                print(f"✅ 로컬 데이터 로드 완료: {len(self.data)}행, {len(self.data.columns)}열 (총 {len(self.all_sheets_data)}개 탭)")
                return True
            except Exception as e:
                print(f"❌ 로컬 엑셀 파일 로드 오류: {e}")
                return False
        
        try:
            if self.read_mode == 'xlsx':
                url = self._convert_to_xlsx_url(self.sheet_url)
                print(f"📊 엑셀(.xlsx) 형태로 데이터 가져오는 중...")
            else:
                url = self._convert_to_csv_url(self.sheet_url)
                print(f"📊 스프레드시트 데이터(CSV) 가져오는 중...")
                
            print(f"   URL: {url[:80]}...")
            
            # 세션 사용하여 쿠키 처리
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/csv,text/plain,*/*',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            })
            
            # 첫 번째 시도
            response = session.get(url, timeout=30, allow_redirects=True)
            
            # 상태 코드 로깅
            print(f"   📡 응답 코드: {response.status_code}")
            
            # 리다이렉트 후 다시 시도
            if response.status_code != 200:
                print(f"   ⚠️ 첫 시도 실패 ({response.status_code}), 재시도 중...")
                import time
                time.sleep(2)
                response = session.get(url, timeout=30, allow_redirects=True)
                print(f"   📡 재시도 응답 코드: {response.status_code}")
            
            # 400/403/404 오류 상세 처리
            if response.status_code in [400, 403, 404]:
                print(f"   ❌ HTTP {response.status_code} 오류")
                print(f"   💡 원인:")
                print(f"      - 스프레드시트가 '링크가 있는 모든 사용자'에게 공유되어 있는지 확인")
                if self.read_mode != 'xlsx':
                    print(f"      - URL에 올바른 gid(시트 ID)가 포함되어 있는지 확인")
                print(f"   📋 현재 URL: {self.sheet_url}")
                return False
            
            response.raise_for_status()
            
            if self.read_mode == 'xlsx':
                # 엑셀 전체 탭 로드
                excel_data = BytesIO(response.content)
                self.all_sheets_data = pd.read_excel(excel_data, sheet_name=None)
                if not self.all_sheets_data:
                    print("   ⚠️ 스프레드시트에 데이터 탭이 없습니다.")
                    return False
                
                # 컬럼명 정리 및 호환성 처리
                for sheet, df in self.all_sheets_data.items():
                    df.columns = [str(col).strip() for col in df.columns]
                first_sheet = list(self.all_sheets_data.keys())[0]
                self.data = self.all_sheets_data[first_sheet]
            else:
                # 단일 CSV 파싱
                response.encoding = 'utf-8'
                content = response.text.strip()
                if content.startswith('<!DOCTYPE html>') or content.startswith('<HTML>'):
                    print("   ❌ HTML 응답 감지 - 스프레드시트 접근 불가")
                    print("   💡 스프레드시트가 공개 설정되어 있는지 확인하세요.")
                    return False
                    
                csv_data = StringIO(content)
                self.data = pd.read_csv(csv_data)
                
                # 데이터 유효성 검사
                if len(self.data) == 0:
                    print("   ⚠️ 스프레드시트에 데이터가 없습니다.")
                    return False
                
                # 컬럼명 정리 (공백 제거)
                self.data.columns = [str(col).strip() for col in self.data.columns]
                self.all_sheets_data = {self.sheet_name or 'Sheet1': self.data}
            
            self.last_fetch_time = datetime.now()
            print(f"✅ 데이터 로드 완료: {len(self.data)}행, {len(self.data.columns)}열 (총 {len(self.all_sheets_data)}개 탭)")
            print(f"   컬럼: {list(self.data.columns)}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 네트워크 오류: {e}")
            print(f"   💡 스프레드시트가 '링크가 있는 모든 사용자'에게 공유되어 있는지 확인하세요.")
            print(f"   📋 현재 URL: {self.sheet_url}")
            return False
        except Exception as e:
            print(f"❌ 데이터 로드 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        다양한 날짜 형식을 YYYY-MM-DD로 변환
        
        지원 형식:
        - 2024-12-30
        - 2024/12/30
        - 12/30
        - 12-30
        - 12월 30일
        """
        if not date_str or pd.isna(date_str):
            return None
        
        date_str = str(date_str).strip()
        today = datetime.now()
        
        # YYYY-MM-DD 또는 YYYY/MM/DD
        patterns = [
            (r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
            (r'(\d{1,2})[-/](\d{1,2})', lambda m: f"{today.year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"),
            (r'(\d{1,2})월\s*(\d{1,2})일', lambda m: f"{today.year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"),
        ]
        
        for pattern, converter in patterns:
            match = re.match(pattern, date_str)
            if match:
                try:
                    return converter(match)
                except:
                    continue
        
        return None
    
    def get_today_content(self, date_column: str = None, content_column: str = None) -> Optional[str]:
        """
        오늘 날짜의 수련내용 가져오기
        
        Args:
            date_column: 날짜 컬럼명 (기본: 첫 번째 컬럼 또는 '날짜')
            content_column: 내용 컬럼명 (기본: '수련내용' 또는 세 번째 컬럼)
        
        Returns:
            수련내용 문자열 또는 None
        """
        if self.data is None:
            if not self.fetch_data():
                return None
        
        # self.all_sheets_data가 설정되지 않은 경우 호환성 보장
        if not hasattr(self, 'all_sheets_data') or not self.all_sheets_data:
            self.all_sheets_data = {'Sheet1': self.data}
            
        today_str = datetime.now().strftime("%Y-%m-%d")
        print(f"[Date] 오늘 날짜: {today_str}")
        
        # 모든 시트 순회 (첫 번째 탭은 건너뜀)
        sheets = list(self.all_sheets_data.items())
        if len(sheets) > 1:
            sheets = sheets[1:]
            
        for sheet_name, df in sheets:
            if df is None or len(df.columns) == 0:
                continue
                
            # 날짜 컬럼 찾기
            if date_column and date_column in df.columns:
                date_col = date_column
            elif '날짜' in df.columns:
                date_col = '날짜'
            else:
                date_col = df.columns[0]  # 첫 번째 컬럼
            
            # 내용 컬럼 찾기
            if content_column and content_column in df.columns:
                content_col = content_column
            elif '수련내용' in df.columns:
                content_col = '수련내용'
            elif '내용' in df.columns:
                content_col = '내용'
            elif len(df.columns) >= 3:
                content_col = df.columns[2]  # 세 번째 컬럼
            else:
                content_col = df.columns[-1]  # 마지막 컬럼
            
            # 날짜 매칭
            for idx, row in df.iterrows():
                date_value = row[date_col]
                parsed_date = self._parse_date(date_value)
                
                if parsed_date == today_str:
                    content = row[content_col]
                    if pd.notna(content) and str(content).strip():
                        print(f"✅ 오늘의 수련내용 발견 (탭: {sheet_name}): {str(content)[:50]}...")
                        return str(content).strip()
        
        print(f"ℹ️ 오늘({today_str}) 날짜의 데이터가 없습니다.")
        return None
    
    def get_latest_content(self, content_column: str = None) -> Optional[str]:
        """
        날짜와 상관없이 가장 마지막으로 입력된 수련내용/주제를 가져오기 (블로그 전용)
        """
        if self.data is None:
            if not self.fetch_data():
                return None
                
        # 내용 컬럼 찾기 (우선순위: 지정 -> '수련내용' -> '주제' -> '내용' -> 2번째/3번째 열)
        if content_column and content_column in self.data.columns:
            content_col = content_column
        elif '수련내용' in self.data.columns:
            content_col = '수련내용'
        elif '주제' in self.data.columns:
            content_col = '주제'
        elif '내용' in self.data.columns:
            content_col = '내용'
        elif len(self.data.columns) >= 2 and any(k in str(self.data.columns[1]).lower() for k in ['주제', '내용', 'content', 'topic']):
            content_col = self.data.columns[1]
        elif len(self.data.columns) >= 3:
            content_col = self.data.columns[2]
        else:
            content_col = self.data.columns[0] # 첫 번째 컬럼 기본값
            
        print(f"   내용 컬럼: {content_col} (날짜 무시하고 가장 마지막 데이터 탐색)")
        
        # 마지막 행부터 역순으로 탐색하여 데이터가 있는 첫 번째 값 반환
        for idx in range(len(self.data) - 1, -1, -1):
            row = self.data.iloc[idx]
            
            # 1순위: 선택된 컬럼 확인
            content = row[content_col]
            if pd.notna(content) and str(content).strip():
                result = str(content).strip()
                print(f"✅ 최신 주제 발견 (지정 컬럼 '{content_col}'): {result[:50]}...")
                return result
            
            # 2순위: 지정 컬럼에 없으면 모든 컬럼 탐색 (데이터가 하나뿐인 시트 대비)
            for col in self.data.columns:
                val = row[col]
                if pd.notna(val) and str(val).strip():
                    result = str(val).strip()
                    if result != str(col): # 헤더값이 아닌 경우만
                        print(f"✅ 최신 주제 발견 (자동 대체 컬럼 '{col}'): {result[:50]}...")
                        return result
                
        print(f"ℹ️ 시트에 유효한 데이터가 없습니다. (전체 행 수: {len(self.data)})")
        return None
    
    def get_content_by_date(self, target_date: str) -> Optional[str]:
        """
        특정 날짜의 수련내용 가져오기
        
        Args:
            target_date: 찾을 날짜 (YYYY-MM-DD 형식)
        
        Returns:
            수련내용 문자열 또는 None
        """
        if self.data is None:
            if not self.fetch_data():
                return None
                
        if not hasattr(self, 'all_sheets_data') or not self.all_sheets_data:
            self.all_sheets_data = {'Sheet1': self.data}
        
        sheets = list(self.all_sheets_data.items())
        if len(sheets) > 1:
            sheets = sheets[1:]
            
        for sheet_name, df in sheets:
            if df is None or len(df.columns) == 0:
                continue
                
            date_col = df.columns[0]
            content_col = df.columns[2] if len(df.columns) >= 3 else df.columns[-1]
            
            for idx, row in df.iterrows():
                date_value = row[date_col]
                parsed_date = self._parse_date(date_value)
                
                if parsed_date == target_date:
                    content = row[content_col]
                    if pd.notna(content):
                        return str(content).strip()
        
        return None
    
    def get_all_data(self) -> Optional[List[Dict]]:
        """전체 데이터를 딕셔너리 리스트로 반환"""
        if self.data is None:
            if not self.fetch_data():
                return None
        
        return self.data.to_dict('records')
    
    def get_combined_content_by_period(self, period: str = '오후') -> Optional[str]:
        """
        시간대별 수련내용 가져오기 (C열 행사명 + D/E/F열 시간대 결합)
        
        Args:
            period: '오전', '오후', '저녁'
        
        Returns:
            결합된 수련내용 문자열 또는 None
            - C열 + 시간대열 (둘 다 있으면)
            - C열만 (시간대열 공란)
            - 시간대열만 (C열 공란)
            - 폴백: 다른 시간대 → C열 → None
        """
        if self.data is None:
            if not self.fetch_data():
                return None
                
        if not hasattr(self, 'all_sheets_data') or not self.all_sheets_data:
            self.all_sheets_data = {'Sheet1': self.data}
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        print(f"[Date] [시간대별] 오늘 날짜: {today_str}, 요청 시간대: {period}")
        
        # 컬럼 매핑 (다양한 헤더명 지원)
        column_mapping = {
            '오전': ['오전', '오전내용', 'morning', 'D'],
            '오후': ['오후', '오후내용', 'afternoon', 'E'],
            '저녁': ['저녁', '저녁내용', 'evening', 'F']
        }
        
        today_row = None
        current_df = None
        
        # 모든 탭 순회하여 오늘 날짜가 있는 행 찾기 (첫 번째 탭은 건너뜀)
        sheets = list(self.all_sheets_data.items())
        if len(sheets) > 1:
            sheets = sheets[1:]
            
        for sheet_name, df in sheets:
            if df is None or len(df.columns) == 0:
                continue
                
            # 날짜 컬럼 찾기
            date_col = None
            for col_name in ['날짜', '날짜 (A열)', 'date', 'Date']:
                if col_name in df.columns:
                    date_col = col_name
                    break
            if date_col is None:
                date_col = df.columns[0]
                
            for idx, row in df.iterrows():
                date_value = row[date_col]
                parsed_date = self._parse_date(date_value)
                
                if parsed_date == today_str:
                    today_row = row
                    current_df = df
                    break
            if today_row is not None:
                break
                
        if today_row is None or current_df is None:
            print(f"ℹ️ 오늘({today_str}) 날짜의 데이터가 없습니다.")
            return None
            
        # C열 (행사명/공통내용) 컬럼 찾기
        event_col = None
        for col_name in ['수련내용', '수련내용 (C열)', '행사명', 'content']:
            if col_name in current_df.columns:
                event_col = col_name
                break
        if event_col is None and len(current_df.columns) >= 3:
            event_col = current_df.columns[2]
        
        # 시간대별 컬럼 찾기
        def find_period_column(period_name: str) -> Optional[str]:
            for possible_name in column_mapping.get(period_name, []):
                for col in current_df.columns:
                    if possible_name.lower() in str(col).lower():
                        return col
            return None
        
        morning_col = find_period_column('오전')
        afternoon_col = find_period_column('오후')
        evening_col = find_period_column('저녁')
        
        print(f"   컬럼 발견: 날짜={date_col}, 행사명={event_col}, 오전={morning_col}, 오후={afternoon_col}, 저녁={evening_col}")
        
        # 시간대별 우선순위 설정
        period_priority = {
            '오전': [morning_col, afternoon_col, evening_col],
            '오후': [afternoon_col, morning_col, evening_col],
            '저녁': [evening_col, afternoon_col, morning_col]
        }
        
        # C열 (행사명) 가져오기
        event_name = None
        if event_col and event_col in today_row.index:
            val = today_row[event_col]
            if pd.notna(val) and str(val).strip():
                event_name = str(val).strip()
        
        # 시간대별 컬럼에서 내용 가져오기 (우선순위대로)
        period_content = None
        for col in period_priority.get(period, []):
            if col and col in today_row.index:
                val = today_row[col]
                if pd.notna(val) and str(val).strip():
                    period_content = str(val).strip()
                    print(f"   ✅ 시간대 내용 발견 ({col}): {period_content[:30]}...")
                    break
        
        # 결합 로직
        if event_name and period_content:
            result = f"{event_name} {period_content}"
            print(f"   ✅ 결합 결과: {result[:50]}...")
            return result
        elif event_name:
            print(f"   ✅ 행사명만 사용: {event_name[:50]}...")
            return event_name
        elif period_content:
            print(f"   ✅ 시간대 내용만 사용: {period_content[:50]}...")
            return period_content
        else:
            print(f"   ℹ️ 시간대별 내용 없음, 기본 C열 폴백")
            return None


# 테스트 코드
if __name__ == "__main__":
    # 테스트용 공개 스프레드시트 URL
    test_url = input("구글 스프레드시트 공유 URL 입력: ").strip()
    
    if test_url:
        reader = GoogleSheetsReader(sheet_url=test_url)
        
        if reader.fetch_data():
            print("\n📋 전체 데이터 미리보기:")
            print(reader.data.head(10))
            
            print("\n[Date] 오늘의 수련내용:")
            content = reader.get_today_content()
            if content:
                print(f"  → {content}")
            else:
                print("  → 오늘 데이터 없음")
    else:
        print("URL을 입력하지 않아 테스트를 건너뜁니다.")
