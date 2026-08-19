"""
구글 드라이브 사진 감지 자동 포스팅 시스템
- 폴더 감지 → 스프레드시트 주제 읽기 → AI 글 생성 → 밴드 포스팅 → 파일 백업
"""

import os
import threading
import unicodedata  # 한글 Unicode 정규화용
from datetime import datetime
from typing import Dict, List, Optional, Callable
from pathlib import Path

from modules.drive_watcher import DriveWatcher, send_macos_notification
from modules.sheets_reader import GoogleSheetsReader
from modules.file_manager import FileManager


class DriveAutoPostSystem:
    """
    구글 드라이브 사진 감지 자동 포스팅 시스템
    
    흐름:
    1. 폴더에 사진 감지 (60초 디바운스)
    2. 스프레드시트에서 오늘 수련내용 가져오기
    3. UI 수동입력 > 스프레드시트 순으로 주제 결정
    4. AI로 글 생성
    5. 밴드에 포스팅
    6. 사진 백업 폴더로 이동
    """
    
    def __init__(self, settings: dict = None):
        """
        Args:
            settings: 앱 설정 딕셔너리
        """
        self.settings = settings or {}
        
        # 모듈 초기화
        self.watcher = DriveWatcher(debounce_seconds=180, polling_interval=10)
        self.sheets_reader = GoogleSheetsReader(read_mode='xlsx')
        self.file_manager = FileManager()
        
        # 콜백 함수들
        self.on_post_success: Optional[Callable] = None
        self.on_post_fail: Optional[Callable] = None
        self.get_manual_topic: Optional[Callable] = None  # UI에서 수동 주제 가져오기
        self.post_to_band: Optional[Callable] = None  # 밴드 포스팅 함수
        self.generate_content: Optional[Callable] = None  # AI 글 생성 함수
        
        # 상태
        self.is_running = False
        self.last_post_time: Optional[datetime] = None
        self.post_count = 0
        
        # 포스팅 중복 방지
        self.is_processing = False  # 현재 포스팅 처리 중인지
        self.processing_lock = threading.Lock()  # 스레드 안전을 위한 잠금
        
        # 해시태그 순환 인덱스
        self.hashtag_cycle_index = 0
        
        # 기본 해시태그 풀 (전체 목록 - 종목은 사용자 설정에서 동적으로 추가됨)
        self.default_hashtags = [
            "#한국체대", "#라이온체육관", 
            "#전문체육", "#생활체육", "#어린이건강", "#청소년건강", "#성인건강",
            "#어린이운동", "#청소년운동", "#성인운동", "#건강다이어트", "#체력단련",
            "#무도교육", "#인성교육", "#자기방어", "#호신술", "#운동습관"
        ]
        
        # 감시 콜백 설정
        self.watcher.set_callback(self._on_files_detected)
    
    def configure(self, settings: dict):
        """설정 적용"""
        self.settings = settings
        
        # 스프레드시트 URL 설정
        sheet_url = settings.get('google_sheet_url', '')
        if sheet_url:
            self.sheets_reader.set_url(sheet_url)
        
        # 백업 디렉토리 설정
        backup_dir = settings.get('backup_dir', '')
        if backup_dir:
            self.file_manager.set_backup_dir(backup_dir)
        
        # 에러 디렉토리 설정
        error_dir = settings.get('error_dir', '')
        if error_dir:
            self.file_manager.set_error_dir(error_dir)
        
        # 감시 폴더 설정
        watch_folders = settings.get('watch_folders', [])
        for folder in watch_folders:
            path = folder.get('path', '')
            name = folder.get('name', os.path.basename(path))
            if path:
                self.watcher.add_folder(path, name)
    
    def add_watch_folder(self, path: str, name: str) -> bool:
        """감시 폴더 추가"""
        return self.watcher.add_folder(path, name)
    
    def scan_and_add_subfolders(self, parent_path: str, exclude_folders: List[str] = None) -> List[Dict]:
        """
        상위 폴더의 하위 폴더들을 자동으로 스캔하여 감시 대상에 추가
        
        Args:
            parent_path: 상위 폴더 경로 (예: /Users/.../Google Drive/수련사진및영상)
            exclude_folders: 제외할 폴더 이름 목록 (예: ['백업사진', '실패사진'])
        
        Returns:
            스캔된 폴더 정보 리스트 [{"path": "...", "name": "..."}, ...]
        """
        if not os.path.exists(parent_path):
            print(f"❌ 상위 폴더가 존재하지 않습니다: {parent_path}")
            return []
        
        # 🔄 기존 핸들러 초기화 (새로 스캔하기 전에)
        if self.watcher.handlers:
            print(f"🔄 기존 핸들러 {len(self.watcher.handlers)}개 초기화...")
            self.watcher.handlers.clear()
        
        # 기본 제외 폴더 (NFC 정규화)
        default_excludes = {'백업사진', '실패사진', 'Backup', 'Error', '.DS_Store', '@eaDir'}
        exclude_set = {unicodedata.normalize('NFC', f) for f in default_excludes}
        if exclude_folders:
            exclude_set |= {unicodedata.normalize('NFC', f) for f in exclude_folders}
        
        print(f"🚫 제외 목록: {exclude_set}")
        
        scanned_folders = []
        
        try:
            # 디버그 로그
            all_items = os.listdir(parent_path)
            print(f"📂 스캔 대상 경로: {parent_path}")
            print(f"📂 발견된 항목 수: {len(all_items)}")
            
            for item in all_items:
                item_path = os.path.join(parent_path, item)
                
                # 폴더만 처리
                if not os.path.isdir(item_path):
                    continue
                
                # 🔧 한글 폴더명 NFC 정규화 (macOS NFD 호환)
                item_normalized = unicodedata.normalize('NFC', item)
                
                # 제외 폴더 건너뛰기
                if item_normalized in exclude_set:
                    print(f"⏭️ 제외됨: {item}")
                    continue
                
                # 숨김 폴더 건너뛰기
                if item.startswith('.'):
                    continue
                
                # 감시 폴더 추가
                result = self.watcher.add_folder(item_path, item)
                if result:
                    scanned_folders.append({
                        "path": item_path,
                        "name": item
                    })
                else:
                    print(f"⚠️ 폴더 등록 실패: {item}")
            
            print(f"✅ 총 {len(scanned_folders)}개 하위 폴더 감시 등록됨")
            
        except Exception as e:
            print(f"❌ 폴더 스캔 오류: {e}")
            import traceback
            traceback.print_exc()
        
        return scanned_folders
    
    def get_subfolders(self, parent_path: str, exclude_folders: List[str] = None) -> List[Dict]:
        """
        상위 폴더의 하위 폴더 목록 조회 (감시 등록 없이)
        
        Args:
            parent_path: 상위 폴더 경로
            exclude_folders: 제외할 폴더 이름 목록
        
        Returns:
            폴더 정보 리스트 [{"path": "...", "name": "..."}, ...]
        """
        if not os.path.exists(parent_path):
            return []
        
        default_excludes = {'백업사진', '실패사진', 'Backup', 'Error', '.DS_Store', '@eaDir'}
        exclude_set = default_excludes | set(exclude_folders or [])
        
        folders = []
        
        try:
            for item in sorted(os.listdir(parent_path)):
                item_path = os.path.join(parent_path, item)
                
                if not os.path.isdir(item_path):
                    continue
                
                if item in exclude_set or item.startswith('.'):
                    continue
                
                folders.append({
                    "path": item_path,
                    "name": item
                })
        except Exception as e:
            print(f"⚠️ 폴더 조회 오류: {e}")
        
        return folders

    def remove_watch_folder(self, path: str):
        """감시 폴더 제거"""
        self.watcher.remove_folder(path)
    
    def start(self) -> bool:
        """시스템 시작"""
        if self.is_running:
            print("ℹ️ 이미 실행 중입니다.")
            return True
        
        # 스프레드시트 데이터 미리 로드
        if self.sheets_reader.sheet_url:
            self.sheets_reader.fetch_data()
        
        # 폴더 감시 시작
        if self.watcher.start():
            self.is_running = True
            
            # 자동 정리 스케줄러 시작 (6시간마다)
            self.file_manager.start_auto_cleanup(interval_hours=6)
            
            print("✅ 드라이브 자동 포스팅 시스템 시작됨")
            send_macos_notification(
                "자동 포스팅 시작",
                f"{len(self.watcher.handlers)}개 폴더 감시 중"
            )
            return True
        
        return False
    
    def stop(self):
        """시스템 중지"""
        self.watcher.stop()
        self.is_running = False
        print("🛑 드라이브 자동 포스팅 시스템 중지됨")
    
    def _on_files_detected(self, folder_path: str, folder_name: str, files: List[str]):
        """
        파일 감지 시 호출되는 콜백
        
        Args:
            folder_path: 감지된 폴더 경로
            folder_name: 폴더 이름 (예: "3시부")
            files: 감지된 파일 경로 리스트
        """
        print(f"\n{'='*60}")
        print(f"📷 [{folder_name}] 사진 {len(files)}개 감지됨!")
        print(f"   경로: {folder_path}")
        print(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print('='*60)
        
        # 이미 처리 중이면 대기
        if self.is_processing:
            print("⏳ 이전 포스팅 처리 중... 대기합니다.")
            # 최대 5분 대기
            wait_start = datetime.now()
            while self.is_processing:
                if (datetime.now() - wait_start).seconds > 300:
                    print("⚠️ 대기 시간 초과, 포스팅 건너뜀")
                    return
                import time
                time.sleep(5)
            print("✅ 대기 완료, 포스팅 시작")
        
        send_macos_notification(
            f"{folder_name} 사진 감지",
            f"{len(files)}개 파일 처리 시작"
        )
        
        # 별도 스레드에서 처리 (UI 블로킹 방지)
        threading.Thread(
            target=self._process_and_post,
            args=(folder_path, folder_name, files),
            daemon=True
        ).start()
    
    def _get_rotating_hashtags(self, count: int = 8) -> str:
        """
        해시태그 순환 시스템
        - 사용자 설정에 해시태그가 있으면 그것 사용 (전체 또는 순환)
        - 없으면 기본 해시태그 풀에서 순환
        
        Args:
            count: 한 번에 사용할 해시태그 개수 (기본 8개)
        
        Returns:
            해시태그 문자열 (예: "#태권도 #한국체대 #라이온체육관")
        """
        # 사용자 설정에서 해시태그 가져오기
        user_hashtags = self.settings.get('band_hashtags', '').strip()
        
        if user_hashtags:
            # 사용자가 설정한 해시태그가 있으면 그것 사용
            # 해시태그 파싱 (# 또는 공백으로 분리)
            tags = [t.strip() for t in user_hashtags.replace('#', ' #').split() if t.strip().startswith('#')]
            if not tags:
                tags = ['#' + t.strip() for t in user_hashtags.split(',') if t.strip()]
            
            if len(tags) <= count:
                # 태그가 적으면 전체 사용
                return ' '.join(tags)
            else:
                # 많으면 순환
                hashtag_pool = tags
        else:
            # 사용자 설정 없으면 기본 해시태그 풀 사용
            hashtag_pool = self.default_hashtags
        
        # 순환 선택
        total = len(hashtag_pool)
        if total == 0:
            return ''
        
        # 시작 인덱스에서 count개 선택 (순환)
        selected = []
        for i in range(count):
            idx = (self.hashtag_cycle_index + i) % total
            selected.append(hashtag_pool[idx])
        
        # 다음 포스팅을 위해 인덱스 이동
        self.hashtag_cycle_index = (self.hashtag_cycle_index + count) % total
        
        return ' '.join(selected)
    
    def _process_and_post(self, folder_path: str, folder_name: str, files: List[str]):
        """
        포스팅 처리 (백그라운드 스레드)
        """
        # 처리 시작 - 잠금
        with self.processing_lock:
            if self.is_processing:
                print("⚠️ 이미 포스팅 처리 중입니다. 이 요청은 건너뜁니다.")
                return
            self.is_processing = True
        
        success = False
        
        try:
            # 🛡️ [안전장치] 폴더 내의 모든 미디어 파일 다시 확인 (누락 방지)
            print(f"🔍 [{folder_name}] 폴더 전체 스캔 중...")
            all_files_in_folder = []
            valid_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif',
                          '.mp4', '.mov', '.avi', '.mkv', '.m4v'}
            
            if os.path.exists(folder_path):
                try:
                    for f in os.listdir(folder_path):
                        # 🔧 한글 파일명 NFC 정규화
                        f_normalized = unicodedata.normalize('NFC', f)
                        ext = os.path.splitext(f_normalized)[1].lower()
                        if ext in valid_exts:
                            full_path = os.path.join(folder_path, f)
                            all_files_in_folder.append(full_path)
                except Exception as scan_err:
                    print(f"⚠️ 폴더 스캔 오류: {scan_err}")
            
            # 기존 감지된 파일과 합치기 (중복 제거)
            # files는 이미 절대경로임
            combined_files = set(files)
            for f in all_files_in_folder:
                combined_files.add(f)
            
            files = list(combined_files)
            print(f"📦 최종 처리 파일: {len(files)}개")

            # 🔄 스프레드시트 매번 새로고침 (캐시 무시)
            if self.sheets_reader.sheet_url:
                print("📊 스프레드시트 새로고침 중...")
                self.sheets_reader.fetch_data(force_refresh=True)
            
            # 1. 주제 결정 (수동 > 스프레드시트)
            topic = self._get_topic(folder_name)
            if not topic:
                print(f"⚠️ 주제를 찾을 수 없습니다. 기본 주제 사용.")
                topic = f"한국체대 라이온짐 {folder_name} 수련"
            
            print(f"📝 주제: {topic}")
            
            # 특별활동 여부 확인 (캠프, 키즈카페 등)
            is_special_activity = any(keyword in folder_name.lower() or keyword in topic.lower() 
                                      for keyword in ['캠프', '키즈카페', '견학', '체험', '행사'])
            
            # 안내문 (사용자 설정에서 가져옴, 특별활동에는 추가 안함)
            safety_notice = ""
            if not is_special_activity:
                default_notice = "수련의 생생한 현장을 담았습니다. 사진 및 영상 화질이 다소 아쉬울 수 있으나, 열심히 수련하는 모습을 함께 나눕니다! 🙏"
                user_notice = self.settings.get('band_footer_notice', default_notice)
                if user_notice and user_notice.strip():
                    safety_notice = "\n\n" + user_notice
                    print(f"📝 하단 안내문 추가됨")
            else:
                print(f"ℹ️ 특별활동 - 하단 안내문 생략")
            
            # 해시태그 처리 (순환 시스템)
            hashtags = self._get_rotating_hashtags()
            if hashtags:
                hashtags = "\n\n" + hashtags
            
            # 2. AI 글 생성
            content = None
            if self.generate_content:
                print("🤖 AI 글 생성 중...")
                try:
                    result = self.generate_content(topic, folder_name)
                    if result:
                        content = result.get('content', '')
                        # AI 생성 글 뒤에 안내문 추가는 band_pipeline에서 처리하므로 여기서 중복 추가하지 않음
                except Exception as e:
                    print(f"❌ AI 글 생성 오류: {e}")
            
            if not content:
                print("⚠️ AI 글 생성 실패, 기본 내용 사용")
                # 기본 내용 + 안내문 + 해시태그
                content = f"""[{folder_name}] {topic}

오늘도 열심히 수련했습니다! 💪{safety_notice}{hashtags}"""
            
            # 3. 밴드에 포스팅 (사진/동영상 분리 순차 포스팅)
            if self.post_to_band:
                print("📤 밴드 포스팅 중...")
                try:
                    # 사진/동영상 분리
                    media = self._separate_media_files(files)
                    photos = media['images']
                    videos = media['videos']
                    
                    print(f"   📷 사진: {len(photos)}개")
                    print(f"   🎬 동영상: {len(videos)}개")
                    
                    # Case 1: 사진과 동영상이 둘 다 있는 경우 -> 분리하여 순차 포스팅
                    if photos and videos:
                        print(f"📤 [1단계: 사진 포스팅] 본문 글과 사진 {len(photos)}개 업로드 시작...")
                        success = self.post_to_band(
                            content=content,
                            image_paths=photos
                        )
                        
                        if success:
                            import time
                            print("✅ 1차 사진 포스팅 완료 확인됨! 5초 대기 후 2차 동영상 포스팅을 진행합니다...")
                            time.sleep(5)
                            
                            chunk_size = 10
                            total_chunks = (len(videos) + chunk_size - 1) // chunk_size
                            for v_idx in range(0, len(videos), chunk_size):
                                v_chunk = videos[v_idx:v_idx + chunk_size]
                                chunk_num = (v_idx // chunk_size) + 1
                                
                                video_notice = f"🎥 [{folder_name}] 수련 현장을 생생하게 담은 수련 영상입니다! 즐겁게 감상해 주세요. 😊"
                                if total_chunks > 1:
                                    video_notice = f"🎥 [{folder_name}] 생생 수련 영상 ({chunk_num}/{total_chunks}) 입니다! 즐겁게 감상해 주세요. 😊"
                                
                                video_content = f"{video_notice}{safety_notice}{hashtags}"
                                print(f"📤 [2단계: 동영상 포스팅 {chunk_num}/{total_chunks}] 영상 {len(v_chunk)}개 업로드 시작...")
                                self.post_to_band(
                                    content=video_content,
                                    image_paths=v_chunk
                                )
                                time.sleep(3)
                    
                    # Case 2: 사진만 있는 경우
                    elif photos:
                        print(f"📤 [사진 포스팅] 본문 글과 사진 {len(photos)}개 업로드 시작...")
                        success = self.post_to_band(
                            content=content,
                            image_paths=photos
                        )
                        
                    # Case 3: 동영상만 있는 경우
                    elif videos:
                        print(f"📤 [동영상 포스팅] 본문 글과 동영상 {len(videos)}개 업로드 시작...")
                        success = self.post_to_band(
                            content=content,
                            image_paths=videos
                        )
                        
                    # Case 4: 텍스트만 있는 경우
                    else:
                        print("📤 [텍스트 포스팅] 글 내용 업로드 시작...")
                        success = self.post_to_band(
                            content=content,
                            image_paths=None
                        )
                        
                except Exception as e:
                    print(f"❌ 밴드 포스팅 오류: {e}")
                    success = False
            else:
                print("⚠️ 밴드 포스팅 함수가 설정되지 않음")
                # 테스트 모드: 포스팅 없이 성공 처리
                success = True
            
            # 4. 파일 처리
            if success:
                print("✅ 포스팅 성공!")
                self.post_count += 1
                self.last_post_time = datetime.now()
                
                # 백업 폴더로 이동
                self.file_manager.move_to_backup(files, folder_name)
                
                send_macos_notification(
                    f"{folder_name} 업로드 성공",
                    f"{len(files)}개 사진 포스팅 완료"
                )
                
                if self.on_post_success:
                    self.on_post_success(folder_name, len(files))
            else:
                print("❌ 포스팅 실패")
                
                # 에러 폴더로 이동
                self.file_manager.move_to_error(files, folder_name)
                
                send_macos_notification(
                    f"{folder_name} 업로드 실패",
                    "에러 폴더로 이동됨"
                )
                
                if self.on_post_fail:
                    self.on_post_fail(folder_name, "포스팅 실패")
        
        except Exception as e:
            print(f"❌ 처리 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            
            # 에러 발생 시 파일 보존
            self.file_manager.move_to_error(files, f"{folder_name}_error")
            
            send_macos_notification(
                "자동 포스팅 오류",
                str(e)[:50]
            )
            
            if self.on_post_fail:
                self.on_post_fail(folder_name, str(e))
        
        finally:
            # 처리 완료 - 잠금 해제
            with self.processing_lock:
                self.is_processing = False
            print(f"🔓 [{folder_name}] 포스팅 처리 완료, 다음 감지 대기 중...")
    
    def _folder_to_period(self, folder_name: str) -> str:
        """
        폴더명을 시간대로 매핑
        
        Returns:
            '오전', '오후', '저녁' 중 하나
        """
        folder_lower = folder_name.lower()
        
        # 오전 폴더
        morning_folders = {'생활체육오전반', '오전반'}
        
        # 저녁 폴더 (7시부~9시부, 선수부, 시범부, 합숙훈련)
        evening_folders = {'7시부', '8시부', '9시부', 
                           '한체대팀라이온선수부', '선수부',
                           '한체대팀라이온시범부', '시범부',
                           '한체대라이온짐합숙훈련', '합숙훈련', '합숙'}
        
        # 오후 폴더 (1시부~6시부, 승급심사, 승단심사, 대회 등)
        afternoon_folders = {'1시부', '2시부', '3시부', '4시부', '5시부', '6시부',
                             '한체대라이온승급심사', '승급심사',
                             '합기도승단심사', '승단심사',
                             '합기도대회', '대회'}
        
        # 캠프는 오전 우선 (오전 없으면 오후 폴백)
        if '캠프' in folder_name:
            return '오전'  # 오전 우선, 폴백 로직은 sheets_reader에서 처리
        
        if folder_name in morning_folders:
            return '오전'
        elif folder_name in evening_folders:
            return '저녁'
        elif folder_name in afternoon_folders:
            return '오후'
        else:
            # 기본값: 오후
            return '오후'
    
    def _get_topic(self, folder_name: str) -> str:
        """
        주제 결정 (폴더명에 구애받지 않고 스프레드시트 우선 참조)
        """
        # 1순위: 수동 입력
        if self.get_manual_topic:
            manual = self.get_manual_topic()
            if manual and manual.strip():
                print(f"📌 수동 입력 주제 사용: {manual[:30]}...")
                return manual.strip()
        
        # 2순위: 스프레드시트 참조 (모든 폴더 대상)
        if self.sheets_reader.sheet_url:
            try:
                # 폴더명에서 시간대 유추 시도
                period = self._folder_to_period(folder_name)
                print(f"📊 폴더 '{folder_name}' → 유추된 시간대: {period}")
                
                # 시간대별 수련내용 가져오기 시도
                sheet_content = self.sheets_reader.get_combined_content_by_period(period)
                
                # 시간대별 열이 없으면 공통 열(C열 등) 단독 확인
                if not sheet_content:
                    print(f"   ℹ️ 시간대별 내용 없음, 공통 수련내용(C열) 확인...")
                    sheet_content = self.sheets_reader.get_today_content()
                
                if sheet_content:
                    # 폴더명과 시트 수련내용 결합
                    topic = f"한국체대 라이온짐 {folder_name} 수련\n수련내용: {sheet_content}"
                    print(f"📊 구글 시트 주제 적용 완료")
                    return topic
            except Exception as e:
                print(f"⚠️ 스프레드시트 조회 오류: {e}")
        
        # 3순위: 구글 시트 미설정 또는 오늘 데이터가 없을 때 기본 템플릿 (Fallback)
        print(f"⚠️ 시트 정보를 찾지 못했습니다. 기본 템플릿으로 우회합니다.")
        return f"한국체대 라이온짐 {folder_name} 활동"
    
    def _get_special_folder_topic(self, folder_name: str) -> str:
        """
        별도 지침이 필요한 폴더의 주제 생성
        """
        special_topics = {
            '시범부': "한국체대 라이온짐 시범부 수련\n시범 기술 연습 및 품새, 격파 훈련",
            '선수부': "한국체대 라이온짐 선수부 훈련\n대회 준비 및 고강도 체력/기술 훈련",
            '승급심사': "한국체대 라이온짐 승급심사\n열심히 준비한 수련생들의 승급 도전",
            '승단심사': "한국체대 라이온짐 승단심사\n더 높은 단계를 향한 도전",
            '오전반': "한국체대 라이온짐 오전반 수련\n오전 시간대 특별 수련 프로그램"
        }
        
        return special_topics.get(folder_name, f"한국체대 라이온짐 {folder_name} 활동")
    
    def _is_image(self, filepath: str) -> bool:
        """이미지 파일 여부 확인"""
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif'}
        return Path(filepath).suffix.lower() in image_exts
    
    def _is_video(self, filepath: str) -> bool:
        """동영상 파일 여부 확인"""
        video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.wmv', '.webm'}
        return Path(filepath).suffix.lower() in video_exts
    
    def _separate_media_files(self, files: List[str]) -> dict:
        """
        미디어 파일을 사진/동영상으로 분리
        
        Returns:
            {"images": [...], "videos": [...], "all": [...]}
        """
        images = [f for f in files if self._is_image(f)]
        videos = [f for f in files if self._is_video(f)]
        
        return {
            "images": images,
            "videos": videos,
            "all": images + videos  # 사진 먼저, 동영상 나중
        }
    
    def get_status(self) -> dict:
        """시스템 상태 반환"""
        watcher_status = self.watcher.get_status()
        backup_stats = self.file_manager.get_backup_stats()
        
        return {
            "is_running": self.is_running,
            "watch_folders": watcher_status.get("folders", []),
            "folder_count": watcher_status.get("folder_count", 0),
            "post_count": self.post_count,
            "last_post_time": self.last_post_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_post_time else None,
            "backup_stats": backup_stats,
            "sheet_url": self.sheets_reader.sheet_url or "미설정"
        }
    
    def manual_trigger(self, folder_path: str, folder_name: str):
        """
        수동으로 특정 폴더 처리 트리거
        (테스트용)
        """
        if not os.path.exists(folder_path):
            print(f"❌ 폴더가 존재하지 않습니다: {folder_path}")
            return
        
        # 폴더 내 미디어 파일 수집
        files = []
        valid_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif',
                      '.mp4', '.mov', '.avi', '.mkv', '.m4v'}
        
        for f in os.listdir(folder_path):
            if Path(f).suffix.lower() in valid_exts:
                files.append(os.path.join(folder_path, f))
        
        if not files:
            print(f"⚠️ 폴더에 미디어 파일이 없습니다: {folder_path}")
            return
        
        print(f"🔧 수동 트리거: {len(files)}개 파일")
        self._on_files_detected(folder_path, folder_name, files)


# 테스트 코드
if __name__ == "__main__":
    print("드라이브 자동 포스팅 시스템 테스트")
    
    system = DriveAutoPostSystem()
    
    # 테스트 설정
    system.configure({
        "google_sheet_url": "",  # 테스트용 빈 값
        "backup_dir": "/tmp/test_backup",
        "error_dir": "/tmp/test_error",
        "watch_folders": [
            {"path": "/tmp/test_watch", "name": "테스트"}
        ]
    })
    
    # 테스트용 콜백
    def test_generate(topic, folder_name):
        return {"content": f"테스트 글: {topic}"}
    
    def test_post(content, image_paths):
        print(f"[테스트 포스팅] {content[:50]}... / 이미지 {len(image_paths)}개")
        return True
    
    system.generate_content = test_generate
    system.post_to_band = test_post
    
    print("\n상태:", system.get_status())
