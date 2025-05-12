import flet as ft
from modules.gpt_handler import GPTHandler
import subprocess
import os
import sys  # sys 모듈 추가
from datetime import datetime, timedelta
import json
from utils.folder_cleanup import FolderCleanup  # 추가
import random
import hashlib
import tempfile  # 임시 파일 관리를 위한 모듈 추가
import threading
import time  # 추가

# 상위 디렉토리의 modules 추가
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

class BlogWriterApp:
    def __init__(self):
        # 기본 디렉토리 설정
        if getattr(sys, 'frozen', False):
            # 실행 파일로 실행된 경우 (PyInstaller 등으로 빌드된 경우)
            self.base_dir = os.path.dirname(sys.executable)
            print(f"Frozen 모드: {self.base_dir}")
            
            # 맥OS .app 번들일 경우 처리
            if "Contents/MacOS" in self.base_dir:
                print(f"맥OS 앱 번들 감지")
                # dist 디렉토리 찾기 시도
                possible_dirs = [
                    # 기본 위치
                    os.path.dirname(os.path.dirname(os.path.dirname(self.base_dir))),
                    # 현재 작업 디렉토리
                    os.getcwd(),
                    # 실행 파일 디렉토리
                    self.base_dir
                ]
                
                for dir_path in possible_dirs:
                    print(f"확인 중: {dir_path}")
                    if os.path.exists(dir_path):
                        print(f"- 디렉토리 존재함")
                        # config 디렉토리 확인
                        config_path = os.path.join(dir_path, 'config')
                        if os.path.exists(config_path):
                            print(f"- config 디렉토리 찾음: {config_path}")
                            self.base_dir = dir_path
                            break
                            
                        # 상위 디렉토리의 config 확인
                        parent_config = os.path.join(os.path.dirname(dir_path), 'config')
                        if os.path.exists(parent_config):
                            print(f"- 상위 디렉토리에서 config 찾음: {parent_config}")
                            self.base_dir = os.path.dirname(dir_path)
                            break
            
            # base_dir에 리소스 디렉토리가 없는 경우 추가 탐색
            config_dir = os.path.join(self.base_dir, 'config')
            if not os.path.exists(config_dir):
                print(f"기본 디렉토리에 config 폴더가 없습니다.")
                # 실행 파일 경로에서 상위 디렉토리들 탐색
                test_dir = self.base_dir
                for _ in range(3):  # 최대 3단계 상위까지 확인
                    test_dir = os.path.dirname(test_dir)
                    test_config = os.path.join(test_dir, 'config')
                    if os.path.exists(test_config):
                        print(f"상위 디렉토리에서 config 찾음: {test_config}")
                        self.base_dir = test_dir
                        break
        else:
            # 스크립트로 실행된 경우
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            print(f"스크립트 모드: {self.base_dir}")
        
        print(f"최종 기본 디렉토리: {self.base_dir}")
        print(f"현재 작업 디렉토리: {os.getcwd()}")
        try:
            print(f"디렉토리 내용: {os.listdir(self.base_dir)}")
        except Exception as e:
            print(f"디렉토리 내용 확인 실패: {str(e)}")
        
        # 디렉토리 생성
        os.makedirs(os.path.join(self.base_dir, 'config'), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'drafts'), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'settings'), exist_ok=True)
        
        # 이미지 폴더 생성
        self.create_image_folders()
        
        # 폴더 정리 실행
        cleanup = FolderCleanup(retention_days=2)
        cleanup.cleanup_old_folders()
        
        # 설정 파일에서 use_dummy 값 로드
        self.use_dummy = False  # 기본값을 False로 변경
        try:
            if os.path.exists(os.path.join(self.base_dir, 'config/app_settings.json')):
                with open(os.path.join(self.base_dir, 'config/app_settings.json'), 'r', encoding='utf-8') as f:
                    app_settings = json.load(f)
                    self.use_dummy = app_settings.get('use_dummy', False)  # 기본값을 False로 변경
        except Exception as e:
            print(f"앱 설정 로드 중 오류 발생: {str(e)}")
        
        # API 키 로드 (초기화 시)
        api_key = None
        try:
            # 1. 저장된 API 키 파일 확인
            api_key_file = os.path.join(self.base_dir, 'config/api_key.json')
            if os.path.exists(api_key_file):
                with open(api_key_file, 'r', encoding='utf-8') as f:
                    api_key_data = json.load(f)
                    api_key = api_key_data.get('api_key', '')
                    if api_key:
                        os.environ['OPENAI_API_KEY'] = api_key
                        print(f"저장된 API 키를 로드했습니다. (첫 8자: {api_key[:8]}...)")
            
            # 2. API 키가 없으면 .env 파일 확인
            if not api_key and os.path.exists(os.path.join(self.base_dir, '.env')):
                with open(os.path.join(self.base_dir, '.env'), 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('OPENAI_API_KEY='):
                            api_key_val = line.split('=', 1)[1].strip()
                            if api_key_val and api_key_val != "sk-empty-key-for-initialization":
                                api_key = api_key_val
                                os.environ['OPENAI_API_KEY'] = api_key
                                print(f".env 파일에서 API 키를 로드했습니다. (첫 8자: {api_key[:8]}...)")
                                # API 키 파일에도 저장
                                os.makedirs(os.path.dirname(api_key_file), exist_ok=True)
                                with open(api_key_file, 'w', encoding='utf-8') as kf:
                                    json.dump({"api_key": api_key}, kf, ensure_ascii=False)
                            break
        except Exception as e:
            print(f"API 키 로드 중 오류 발생: {str(e)}")
            
        self.gpt_handler = GPTHandler(api_key=api_key, use_dummy=self.use_dummy)
        self.current_title = ""
        self.current_content = ""
        self.last_save_content = None
        
        # 순차적 주제 선택을 위한 인덱스 추적 변수
        self.current_topic_index = -1
        self.load_topic_index()  # 저장된 인덱스 로드
        
        # 시리얼 관련 속성 초기화
        self.serial_number = None
        self.serial_client = None

    def calculate_image_positions(self, content, mode):
        """본문 분석하여 이미지 삽입 위치 계산"""
        lines = content.split('\n')
        total_lines = len(lines)
        positions = []
        
        # 문단 끝과 문장 끝 위치 찾기
        sentence_end_markers = ['. ', '다. ', '요. ', '죠. ', '!', '?']
        key_points = []
        
        for i, line in enumerate(lines):
            # 빈 줄은 문단의 끝
            if not line.strip():
                if i > 0:  # 첫 줄이 아닌 경우만
                    key_points.append({
                        'line': i-1,
                        'weight': 1.0,
                        'type': 'paragraph_end'
                    })
                continue
            
            # 문장 끝 체크
            if any(line.strip().endswith(marker) for marker in sentence_end_markers):
                key_points.append({
                    'line': i,
                    'weight': 0.8,
                    'type': 'sentence_end'
                })
        
        # 모드별 위치 계산
        if mode == "random":
            num_sections = random.randint(3, 5)
            target_positions = [i * total_lines // num_sections for i in range(1, num_sections)]
        elif mode == "three_parts":
            target_positions = [total_lines // 3, (2 * total_lines) // 3]
        elif mode == "five_parts":
            target_positions = [
                total_lines // 5,
                (2 * total_lines) // 5,
                (3 * total_lines) // 5,
                (4 * total_lines) // 5
            ]
        else:  # "end" 모드
            return []
        
        # 각 목표 위치에 대해 가장 적절한 실제 위치 찾기
        for target in target_positions:
            # 가장 가까운 key_point 찾기
            closest_point = min(key_points, 
                key=lambda x: (abs(x['line'] - target), -x['weight']),
                default={'line': target}
            )
            if closest_point['line'] not in [p['line'] for p in positions]:
                positions.append(closest_point)
        
        # 위치를 라인 번호 순으로 정렬
        positions.sort(key=lambda x: x['line'])
        return positions

    def save_image_positions(self, content, mode):
        """이미지 삽입 위치 정보 저장"""
        try:
            positions = self.calculate_image_positions(content, mode)
            image_data = {
                'content_hash': hashlib.md5(content.encode()).hexdigest(),
                'mode': mode,
                'positions': positions,
                'total_lines': len(content.split('\n')),
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 설정 폴더가 없으면 생성
            os.makedirs(os.path.join(self.base_dir, 'config'), exist_ok=True)
            
            # 위치 정보 저장
            with open(os.path.join(self.base_dir, 'config/image_positions.json'), 'w', encoding='utf-8') as f:
                json.dump(image_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"이미지 위치 저장 중 오류 발생: {str(e)}")
            return False

    def load_image_positions(self, content):
        """저장된 이미지 위치 정보 로드"""
        try:
            if os.path.exists(os.path.join(self.base_dir, 'config/image_positions.json')):
                with open(os.path.join(self.base_dir, 'config/image_positions.json'), 'r', encoding='utf-8') as f:
                    image_data = json.load(f)
                    
                # 현재 컨텐츠의 해시값과 비교
                current_hash = hashlib.md5(content.encode()).hexdigest()
                if current_hash == image_data['content_hash']:
                    return image_data
            return None
        except Exception as e:
            print(f"이미지 위치 로드 중 오류 발생: {str(e)}")
            return None

    def load_topic_index(self):
        """저장된 주제 인덱스 로드"""
        try:
            if os.path.exists(os.path.join(self.base_dir, 'config/topic_index.json')):
                with open(os.path.join(self.base_dir, 'config/topic_index.json'), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_topic_index = data.get('current_index', -1)
        except Exception as e:
            print(f"주제 인덱스 로드 중 오류 발생: {str(e)}")
            self.current_topic_index = -1
            
    def save_topic_index(self):
        """현재 주제 인덱스 저장"""
        try:
            with open(os.path.join(self.base_dir, 'config/topic_index.json'), 'w', encoding='utf-8') as f:
                json.dump({'current_index': self.current_topic_index}, f)
        except Exception as e:
            print(f"주제 인덱스 저장 중 오류 발생: {str(e)}")
            
    def create_image_folders(self):
        """10개의 이미지 폴더를 생성합니다."""
        try:
            for i in range(1, 11):
                folder_name = f"default_images_{i}"
                folder_path = os.path.join(self.base_dir, folder_name)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                    print(f"이미지 폴더 생성 완료: {folder_path}")
            return True
        except Exception as e:
            print(f"이미지 폴더 생성 중 오류 발생: {str(e)}")
            return False
            
    def load_folder_index(self):
        """현재 이미지 폴더 인덱스를 로드합니다."""
        try:
            index_file = os.path.join(self.base_dir, 'config/current_folder_index.txt')
            if os.path.exists(index_file):
                with open(index_file, 'r') as f:
                    return int(f.read().strip())
            return 0  # 파일이 없으면 0부터 시작
        except Exception as e:
            print(f"폴더 인덱스 로드 중 오류 발생: {str(e)}")
            return 0
            
    def save_folder_index(self, index):
        """현재 이미지 폴더 인덱스를 저장합니다."""
        try:
            index_file = os.path.join(self.base_dir, 'config/current_folder_index.txt')
            with open(index_file, 'w') as f:
                f.write(str(index))
            return True
        except Exception as e:
            print(f"폴더 인덱스 저장 중 오류 발생: {str(e)}")
            return False
            
    def load_used_folders(self):
        """사용된 이미지 폴더 이력을 로드합니다."""
        try:
            used_folders_file = os.path.join(self.base_dir, 'config/used_folders.json')
            if os.path.exists(used_folders_file):
                with open(used_folders_file, 'r') as f:
                    return json.load(f)
            return {"used_folders": [], "cycle_count": 0}
        except Exception as e:
            print(f"사용된 폴더 이력 로드 중 오류 발생: {str(e)}")
            return {"used_folders": [], "cycle_count": 0}
            
    def save_used_folders(self, used_folders):
        """사용된 이미지 폴더 이력을 저장합니다."""
        try:
            used_folders_file = os.path.join(self.base_dir, 'config/used_folders.json')
            with open(used_folders_file, 'w') as f:
                json.dump(used_folders, f)
            return True
        except Exception as e:
            print(f"사용된 폴더 이력 저장 중 오류 발생: {str(e)}")
            return False
            
    def get_next_image_folder(self):
        """다음 이미지 폴더 경로를 반환하고 인덱스를 업데이트합니다.
           이미 사용된 폴더는 건너뛰고 다음 폴더를 선택합니다."""
        # 사용된 폴더 이력 로드
        used_data = self.load_used_folders()
        used_folders = used_data["used_folders"]
        cycle_count = used_data["cycle_count"]
        
        # 현재 인덱스 로드
        current_index = self.load_folder_index()
        
        # 모든 폴더 사용 여부 확인
        all_used = True
        for i in range(1, 11):
            folder_name = f"default_images_{i}"
            if folder_name not in used_folders:
                all_used = False
                break
                
        # 모든 폴더가 사용되었으면 초기화
        if all_used:
            used_folders = []
            cycle_count += 1
            print(f"모든 이미지 폴더를 사용했습니다. 새로운 사이클({cycle_count}) 시작")
            
        # 사용되지 않은 다음 폴더 찾기
        found = False
        next_index = current_index
        
        for _ in range(10):  # 최대 10번 시도
            next_index = (next_index % 10) + 1  # 1~10 순환
            folder_name = f"default_images_{next_index}"
            folder_path = os.path.join(self.base_dir, folder_name)
            
            # 폴더가 존재하고 아직 사용되지 않았으면 선택
            if os.path.exists(folder_path) and folder_name not in used_folders:
                found = True
                break
        
        if not found:
            print("사용 가능한 이미지 폴더를 찾을 수 없습니다. 기본 폴더 사용.")
            # 기본 이미지 폴더 사용
            return os.path.join(self.base_dir, "default_images")
        
        # 선택된 폴더를 사용된 목록에 추가
        used_folders.append(f"default_images_{next_index}")
        used_data = {"used_folders": used_folders, "cycle_count": cycle_count}
        self.save_used_folders(used_data)
        
        # 인덱스 업데이트 및 저장
        self.save_folder_index(next_index)
        
        folder_path = os.path.join(self.base_dir, f"default_images_{next_index}")
        print(f"이미지 폴더 선택: {folder_path} (사이클 {cycle_count})")
        return folder_path

    def select_sequential_topic(self):
        """저장된 주제 목록에서 순차적으로 주제 선택"""
        try:
            if os.path.exists(os.path.join(self.base_dir, 'config/user_settings.txt')):
                with open(os.path.join(self.base_dir, 'config/user_settings.txt'), 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    topics_str = settings.get('blog_topics', '')
                    if topics_str:
                        topics = [topic.strip() for topic in topics_str.split(',') if topic.strip()]
                        if topics:
                            # 다음 인덱스로 이동 (마지막 주제를 사용했으면 처음으로 돌아감)
                            self.current_topic_index = (self.current_topic_index + 1) % len(topics)
                            # 선택된 인덱스 저장
                            self.save_topic_index()
                            # 현재 인덱스의 주제 반환
                            return topics[self.current_topic_index]
            return None
        except Exception as e:
            print(f"주제 선택 중 오류 발생: {str(e)}")
            return None

    def on_content_change(self, e):
        """본문 내용이 변경될 때마다 호출되는 함수"""
        try:
            if self.current_content:  # 본문이 있는 경우
                # 자동 저장
                self.auto_save()
                
                # 이미지 위치 계산 및 저장
                if auto_image_checkbox.value:  # type: ignore # 자동 이미지 삽입이 활성화된 경우
                    self.save_image_positions(self.current_content, image_insert_mode_value) # type: ignore
        except Exception as e:
            print(f"본문 변경 처리 중 오류 발생: {str(e)}")

    def check_serial_validation(self):
        """시리얼 번호 인증 상태 확인"""
        try:
            # 로그아웃 상태 파일 확인 - 추가된 로직
            logout_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'logout_status.txt'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules/serial_validator/config', 'logout_status.txt')
            ]
            
            for logout_file in logout_paths:
                if os.path.exists(logout_file):
                    try:
                        # 로그아웃 파일이 있으면 삭제하고 로그아웃 상태로 처리
                        print(f"로그아웃 상태 파일 발견: {logout_file}")
                        with open(logout_file, 'r', encoding='utf-8') as f:
                            logout_info = f.read()
                            print(f"로그아웃 정보: {logout_info}")
                        
                        # 파일 삭제 - 중복 처리 방지
                        os.remove(logout_file)
                        print(f"로그아웃 상태 파일 삭제: {logout_file}")
                        
                        return False  # 로그아웃 상태로 처리
                    except Exception as e:
                        print(f"로그아웃 파일 처리 오류: {str(e)}")
            
            # 시리얼 클라이언트 초기화 및 검증
            from modules.serial_validator import SerialClient
            self.serial_client = SerialClient(app_name="BlogAutomation")
            
            # 검증 실행
            is_valid = self.serial_client.is_valid_with_server_check()
            
            # 다른 앱에서 사용 중인 경우 명확하게 처리
            if "다른 앱" in self.serial_client.status:
                print(f"다른 앱에서 사용 중 감지: {self.serial_client.status}")
                self.serial_number = None  # 시리얼 번호 초기화하여 다시 인증받도록 함
                return False
            
            # 다른 디바이스에서 사용중인 경우 - 동일 디바이스 확인 로직 강화
            if self.serial_client.status == "다른 디바이스에서 사용중":
                try:
                    # 디바이스 정보 확인
                    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
                    device_file = os.path.join(config_dir, 'device_info.json')
                    
                    # 디바이스 정보 파일이 없는 경우
                    if not os.path.exists(device_file):
                        print("디바이스 정보 파일이 없습니다. 새로운 시리얼 인증이 필요합니다.")
                        return False
                    
                    # 디바이스 정보 로드
                    with open(device_file, 'r', encoding='utf-8') as f:
                        device_data = json.load(f)
                    
                    # 현재 디바이스 해시와 앱 이름이 저장된 것과 일치하는지 확인
                    if self.serial_client.device_info and device_data.get('device_info'):
                        current_hash = self.serial_client.device_info.get('device_hash')
                        stored_hash = device_data['device_info'].get('device_hash')
                        current_app = self.serial_client.app_name
                        stored_app = device_data.get('app_name')
                        
                        print(f"현재 해시: {current_hash[:10]}..., 저장된 해시: {stored_hash[:10] if stored_hash else 'None'}")
                        print(f"현재 앱: {current_app}, 저장된 앱: {stored_app}")
                        
                        # 현재 시리얼과 저장된 시리얼이 일치하고 현재 해시와 저장된 해시가 일치하면 같은 디바이스
                        if (device_data.get('serial_number') == self.serial_client.serial_number and
                            device_data['device_info'].get('device_hash') == self.serial_client.device_info.get('device_hash') and
                            (not stored_app or stored_app == current_app)):  # 앱 이름도 확인
                            
                            print("동일한 디바이스에서 시리얼을 사용 중입니다. 정상 처리합니다.")
                            self.serial_client.status = "사용가능"
                            self.serial_client.is_valid = True
                        else:
                            print("디바이스 정보가 일치하지 않습니다. 시리얼 재인증이 필요합니다.")
                            if stored_app and stored_app != current_app:
                                print(f"다른 앱({stored_app})에서 사용 중인 시리얼입니다.")
                    else:
                        print("디바이스 정보가 불완전합니다. 시리얼 재인증이 필요합니다.")
                except Exception as e:
                    print(f"디바이스 정보 비교 중 오류: {str(e)}")
            
            # 검증 결과에 따라 시리얼 번호 저장 또는 초기화
            if is_valid and self.serial_client.serial_number:
                self.serial_number = self.serial_client.serial_number
            else:
                self.serial_number = None
                
            print(f"시리얼 상태: {self.serial_client.status}")
            print(f"시리얼 유효성: {is_valid}")
            
            return is_valid
        except Exception as e:
            print(f"시리얼 검증 중 오류 발생: {str(e)}")
            return False
            
    def periodic_serial_check(self, page):
        """주기적으로 시리얼 인증 상태를 확인하는 함수"""
        try:
            # 앱이 종료 중이면 검사 중단
            if hasattr(page, '_closing') and page._closing:
                print("앱이 종료 중이므로 주기적 시리얼 검사를 중단합니다.")
                return
                
            # 로그아웃 상태 파일 확인
            logout_file = os.path.join(self.base_dir, 'config/logout_status.txt')
            if os.path.exists(logout_file):
                print("주기적 검사: 로그아웃 상태 파일 발견. 앱을 종료합니다.")
                
                # 간단한 로그아웃 메시지 표시 후 즉시 종료
                try:
                    dialog = ft.AlertDialog(
                        title=ft.Text("로그아웃 감지"),
                        content=ft.Text("시리얼이 로그아웃되었습니다. 앱을 종료합니다."),
                        actions=[
                            ft.TextButton("종료", on_click=lambda e: sys.exit()),
                        ],
                    )
                    
                    page.dialog = dialog
                    dialog.open = True
                    page.update()
                    
                    # 잠시 후 종료 (다이얼로그가 보이도록)
                    time.sleep(2)
                except:
                    pass
                    
                # 앱 종료
                sys.exit()
            
            # 시리얼 클라이언트 초기화 (필요시)
            if not hasattr(self, 'serial_client') or self.serial_client is None:
                from modules.serial_validator import SerialClient
                self.serial_client = SerialClient(app_name="BlogAutomation")
                
                # 이전 시리얼이 있으면 로드
                if self.serial_client.serial_number:
                    self.serial_number = self.serial_client.serial_number
            
            # 시리얼 정보가 없으면 검사 불필요
            if not hasattr(self, 'serial_number') or not self.serial_number:
                print("시리얼 번호가 설정되지 않아 주기적 검사를 건너뜁니다.")
                return
            
            # 현재 시간 기준으로 마지막 검증 시간 확인
            now = datetime.now()
            
            # 마지막 검증 시간 확인
            try:
                self.serial_client.cursor.execute(
                    "SELECT last_check_date FROM serial_data WHERE serial_number = ?", 
                    (self.serial_number,)
                )
                result = self.serial_client.cursor.fetchone()
                
                if result and result[0]:
                    last_check = result[0]
                    last_datetime = datetime.strptime(last_check, "%Y-%m-%d %H:%M:%S")
                    hours_since_check = (now - last_datetime).total_seconds() / 3600
                    
                    # 24시간 이내에 이미 검증했으면 패스
                    if hours_since_check < 24:
                        print(f"최근에 검증됨 (경과: {hours_since_check:.1f}시간, 24시간 이내)")
                        return
                    
                    print(f"검증 간격 경과 ({hours_since_check:.1f}시간), 재검증 필요")
            except Exception as e:
                print(f"마지막 검증 시간 확인 중 오류: {e}")
            
            # 서버 검증 수행
            print("주기적 시리얼 검증 수행 중...")
            
            if not self.serial_client.is_valid_with_server_check():
                print("시리얼이 유효하지 않음. 앱을 종료합니다.")
                
                # 시리얼 인증 실패 메시지
                try:
                    status_msg = f"시리얼 상태: {self.serial_client.status}" if self.serial_client.status else "시리얼 인증 실패"
                    
                    dialog = ft.AlertDialog(
                        title=ft.Text("시리얼 인증 실패"),
                        content=ft.Text(f"주기적 검사 결과 시리얼이 유효하지 않습니다.\n{status_msg}\n앱을 종료합니다."),
                        actions=[
                            ft.TextButton("종료", on_click=lambda e: sys.exit()),
                        ],
                    )
                    
                    page.dialog = dialog
                    dialog.open = True
                    page.update()
                    
                    # 잠시 후 종료 (다이얼로그가 보이도록)
                    time.sleep(3)
                except:
                    pass
                
                # 앱 종료
                sys.exit()
            else:
                print("주기적 시리얼 검증 성공")
                
        except Exception as e:
            print(f"주기적 시리얼 검증 중 오류 발생: {str(e)}")
            
        # 다음 검증 일정 설정 (24시간 후) - page.after 대신 타이머 사용
        try:
            # 타이머 생성 (24시간 후 실행)
            timer = threading.Timer(24 * 60 * 60, lambda: self.periodic_serial_check(page))
            timer.daemon = True  # 데몬 스레드로 설정하여 메인 스레드 종료 시 자동 종료
            timer.start()
            print(f"다음 시리얼 검증 일정이 {datetime.now() + timedelta(days=1)} 에 설정되었습니다.")
        except Exception as timer_error:
            print(f"타이머 설정 오류: {str(timer_error)}")

    def main(self, page: ft.Page):
        # 페이지 설정
        page.title = "블로그 글쓰기 도우미"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.padding = 20
        page.window_width = 1200
        page.window_height = 800
        page.window_resizable = True
        
        # 페이지 객체 저장 - 다른 메서드에서 접근 가능하게 함
        self.page = page
        
        # 종료 플래그 초기화
        page._closing = False
        
        # 시리얼 인증 상태 표시
        serial_status = ft.Text(
            "인증 상태 확인 중...",
            color=ft.Colors.BLUE_600,
            size=12
        )

        # 시리얼 검증 먼저 실행
        def check_and_show_serial():
            # 앱 실행 전에 이미 시리얼 인증을 했으므로, 바로 앱 내용 표시
            initialize_serial_status()
            show_app_content()
            
            # 주기적인 시리얼 상태 검사 시작 (5초 후)
            # 타이머 대신 page.update 후에 직접 함수 호출로 변경
            self.periodic_serial_check(page)
        
        # 시리얼 인증 UI 표시 (대화상자로 표시)
        def show_serial_ui_dialog(e):
            # 시리얼 UI를 별도 프로세스로 실행
            try:
                # 파이썬 인터프리터 및 시리얼 UI 스크립트 경로
                python_path = sys.executable
                ui_script = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "modules/serial_validator/serial_ui.py"
                )
                
                print("시리얼 UI 실행 중...")
                
                # 블로킹 모드로 실행하여 시리얼 UI가 종료될 때까지 대기
                # 추가 환경 변수 설정 - 앱 이름 전달
                env = os.environ.copy()
                env['APP_NAME'] = 'BlogAutomation'
                
                result = subprocess.run(
                    [python_path, ui_script],
                    env=env,
                    check=False
                )
                
                print(f"시리얼 UI 종료됨, 반환 코드: {result.returncode}")
                
                # 인증 성공 시 특수 반환 코드 확인
                if result.returncode == 0:
                    print("시리얼 인증 성공 코드 감지")
                    
                    # 인증 성공 파일 확인
                    success_paths = [
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'validation_success.json'),
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules/serial_validator/config', 'validation_success.json')
                    ]
                    
                    success_info = None
                    for path in success_paths:
                        if os.path.exists(path):
                            try:
                                with open(path, 'r', encoding='utf-8') as f:
                                    success_info = json.load(f)
                                print(f"인증 성공 정보 로드: {path}")
                                # 사용 후 파일 삭제
                                os.remove(path)
                                break
                            except Exception as e:
                                print(f"인증 성공 파일 처리 오류: {str(e)}")
                    
                    # 성공 정보가 있으면 직접 설정
                    if success_info:
                        try:
                            if not hasattr(self, 'serial_client') or self.serial_client is None:
                                from modules.serial_validator import SerialClient
                                self.serial_client = SerialClient(app_name="BlogAutomation")
                            
                            # 시리얼 정보 직접 설정
                            self.serial_client.serial_number = success_info.get('serial_number')
                            self.serial_client.status = success_info.get('status', '사용가능')
                            self.serial_client.expiry_date = success_info.get('expiry_date')
                            self.serial_client.is_valid = True
                            self.serial_number = self.serial_client.serial_number
                            
                            print(f"시리얼 정보 직접 설정: {self.serial_number}")
                            
                            # 시리얼 정보 저장 - 나중에 불러올 수 있도록
                            if hasattr(self.serial_client, 'save_serial_info'):
                                try:
                                    self.serial_client.save_serial_info()
                                    print("시리얼 정보 저장 완료")
                                except Exception as save_error:
                                    print(f"시리얼 정보 저장 오류: {str(save_error)}")
                        except Exception as setup_error:
                            print(f"시리얼 정보 설정 오류: {str(setup_error)}")
                
                    # 핵심 부분: GUI를 표시하고 페이지 업데이트 (수정된 부분)
                    try:
                        # 중요: 앱 UI 표시 전에 페이지 초기화
                        if hasattr(self, 'page') and self.page:
                            # 기존 컨트롤 제거
                            self.page.controls.clear()
                            self.page.update()
                        
                        # 앱 UI 표시
                        show_app_content()
                        
                        # 주기적 검증 시작
                        self.periodic_serial_check(page)
                        
                        # 성공 메시지 표시
                        page.snack_bar = ft.SnackBar(
                            content=ft.Text(f"시리얼 인증 성공: {self.serial_number[:8]}...{self.serial_number[-8:] if len(self.serial_number) > 16 else self.serial_number}"),
                            bgcolor=ft.Colors.GREEN_700,
                            duration=5000  # 5초간 표시
                        )
                        page.snack_bar.open = True
                        page.update()
                        
                        return True
                    except Exception as gui_error:
                        print(f"GUI 초기화 오류: {str(gui_error)}")
                        # 오류 발생 시에도 계속 진행
                
                # 반환 코드가 2인 경우 로그아웃 처리
                elif result.returncode == 2:
                    print("시리얼이 로그아웃되었습니다. 앱을 즉시 종료합니다.")
                    self.show_alert_dialog(
                        title="로그아웃",
                        content="시리얼이 로그아웃되었습니다. 앱을 종료합니다."
                    )
                    self.exit_app()
                    return
                
                # 시리얼 UI 종료 후 시리얼 인증 상태 재확인
                is_valid = self.check_serial_validation()
                
                if is_valid:
                    # 시리얼 유효함 - 상태 업데이트 및 UI 표시
                    print("시리얼 인증 상태: 유효함")
                    try:
                        # 중요: 앱 UI 표시 전에 페이지 초기화
                        if hasattr(self, 'page') and self.page:
                            # 기존 컨트롤 제거
                            self.page.controls.clear()
                            self.page.update()
                        
                        # 앱 내용 표시
                        show_app_content()
                        
                        # 성공 메시지 표시
                        page.snack_bar = ft.SnackBar(
                            content=ft.Text("시리얼 인증이 확인되었습니다."),
                            bgcolor=ft.Colors.GREEN
                        )
                        page.snack_bar.open = True
                        page.update()
                    except Exception as show_error:
                        print(f"GUI 표시 오류: {str(show_error)}")
                else:
                    # 시리얼 인증 실패 - 앱 종료
                    print("시리얼 인증 실패. 앱을 종료합니다.")
                    self.show_alert_dialog(
                        title="인증 실패",
                        content="시리얼 인증에 실패했습니다. 앱을 종료합니다."
                    )
                    self.exit_app()
            
            except Exception as e:
                print(f"시리얼 UI 처리 중 오류: {str(e)}")
                # 오류 발생 시 앱 종료
                self.show_alert_dialog(
                    title="오류 발생",
                    content=f"시리얼 인증 처리 중 오류가 발생했습니다: {str(e)}"
                )
                self.exit_app()
        
        # 앱 내용 표시 함수 (기존 UI 구성 코드)
        def show_app_content():
            # 먼저 페이지가 초기화되었는지 확인
            if not hasattr(self, 'page') or not self.page:
                print("페이지 객체가 초기화되지 않았습니다.")
                return
                
            try:
                # 페이지 컨트롤이 이미 초기화되었는지 확인
                if len(self.page.controls) > 0:
                    print("기존 컨트롤 제거 중...")
                    self.page.controls.clear()
                    self.page.update()
                    
                # 시리얼 상태 초기화
                initialize_serial_status()
                
                # 앱 바 생성
                create_app_bar()
                
                # 페이지에 탭 추가
                self.page.add(tabs)
                
                # 설정 로드
                load_gpt_settings()
                load_user_settings()
                load_app_settings()
                load_draft()
                
                # 페이지 업데이트 강제 실행
                self.page.update()
                print("앱 UI가 성공적으로 초기화되었습니다.")
                
            except Exception as ui_error:
                print(f"UI 초기화 중 오류 발생: {str(ui_error)}")
                # 오류 발생 시에도 최소한의 UI는 표시
                try:
                    self.page.add(
                        ft.Text("UI 초기화 중 오류가 발생했습니다. 앱을 재시작해주세요.", 
                               color=ft.Colors.RED_700, 
                               size=20)
                    )
                    self.page.update()
                except:
                    pass

        # 닫기 버튼 이벤트 핸들러 추가
        def on_window_close(e):
            print("앱 종료 요청 감지됨")
            try:
                # 페이지에 종료 중 플래그 설정
                page._closing = True
                print("페이지 종료 플래그 설정됨")
                
                # 시리얼 클라이언트 리소스 정리
                if hasattr(self, 'serial_client') and self.serial_client:
                    try:
                        self.serial_client.close()
                        print("시리얼 클라이언트 리소스 정리 완료")
                    except Exception as serial_e:
                        print(f"시리얼 클라이언트 정리 중 오류: {str(serial_e)}")
                
                # 모든 스레드 정리
                import threading
                for thread in threading.enumerate():
                    if thread != threading.current_thread() and not thread.daemon:
                        try:
                            print(f"스레드 종료 시도: {thread.name}")
                            # 메인 스레드가 아닌 일반 스레드만 종료 시도
                            if thread.name != "MainThread":
                                thread.join(0.1)  # 100ms 대기
                        except Exception as te:
                            print(f"스레드 종료 중 오류: {str(te)}")
                
                # 실행 중인 모든 크롬 드라이버 프로세스 종료
                if sys.platform == "win32":
                    os.system("taskkill /f /im chromedriver.exe")
                    os.system("taskkill /f /im chrome.exe")
                else:
                    os.system("pkill -f chromedriver")
                    os.system("pkill -f chrome")
                    
                # 현재 프로세스의 모든 자식 프로세스 종료
                import psutil
                current_process = psutil.Process()
                children = current_process.children(recursive=True)
                for child in children:
                    try:
                        print(f"자식 프로세스 종료 시도: {child.pid}")
                        child.terminate()
                    except:
                        pass
                
                # 타이머 스레드가 있으면 모두 취소
                import sys
                for obj in list(sys.modules.values()):
                    if hasattr(obj, "_timer"):
                        try:
                            obj._timer.cancel()
                            print("타이머 취소 완료")
                        except:
                            pass
                
                # 앱 종료
                page.window_destroy()
                
                # 프로세스 강제 종료
                pid = os.getpid()
                if sys.platform == "win32":
                    os.system(f"taskkill /F /PID {pid}")
                else:
                    os.system(f"kill -9 {pid}")
                
            except Exception as e:
                print(f"종료 중 오류 발생: {str(e)}")
                sys.exit(1)
            
        # 윈도우 이벤트 핸들러 설정
        page.on_window_event = on_window_close

        # GPT 설정 탭 컴포넌트
        gpt_persona = ft.TextField(
            label="GPT 페르소나",
            hint_text="GPT가 어떤 역할이나 정체성을 가지고 글을 작성할지 정의하세요...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True
        )
        
        persona_help_text = ft.Text(
            "페르소나 예시: '*** 분야 전문가', '*** 관련 블로거' 등 (권장 길이: 100-300자)",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )
        
        gpt_instructions = ft.TextField(
            label="GPT 지침",
            hint_text="글 작성 시 따라야 할 구체적인 지침이나 규칙을 정의하세요...",
            multiline=True,
            min_lines=3,
            max_lines=5,
            expand=True
        )
        
        instructions_help_text = ft.Text(
            "지침 예시: '*** 내용을 자연스럽게 포함', '*** 대상 설득력 있는 내용' 등 (권장 길이: 200-500자)",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )
        
        gpt_style = ft.TextField(
            label="글쓰기 스타일",
            hint_text="원하는 글쓰기 스타일을 설정하세요...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True
        )
        
        style_help_text = ft.Text(
            "스타일 예시: '친근한 대화체', '전문적인 설명식', '*** 스타일' 등 (권장 길이: 100-300자)",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )
        
        use_api_checkbox = ft.Checkbox(
            label="실제 OpenAI API 사용 (체크 해제 시 더미 데이터 사용)",
            value=not self.use_dummy
        )
        
        api_key_field = ft.TextField(
            label="OpenAI API 키",
            hint_text="OpenAI API 키를 입력하세요...",
            password=True,  # 비밀번호 형태로 표시
            can_reveal_password=False,  # 비밀번호 표시 버튼 제거
            visible=not self.use_dummy
        )
        
        api_key_help_text = ft.Text(
            "API 키는 보안을 위해 항상 암호화되어 표시됩니다. *** 웹사이트에서 발급받은 키를 입력하세요.",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True,
            visible=not self.use_dummy
        )
        
        # 자동 업로드 설정
        auto_upload_checkbox = ft.Checkbox(
            label="글 생성 후 자동으로 블로그에 업로드",
            value=False
        )
        
        auto_upload_help_text = ft.Text(
            "이 옵션을 선택하면 GPT가 글을 생성한 후 자동으로 블로그에 업로드합니다.",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )
        
        # 자동 주제 선택 설정
        auto_topic_checkbox = ft.Checkbox(
            label="주제 자동 선택",
            value=False
        )
        
        auto_topic_help_text = ft.Text(
            "체크: 사용자 설정에 등록된 주제 중 하나를 자동으로 선택하여 글을 생성합니다. 체크 해제: 수동으로 주제를 입력합니다.",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )
        
        # 이미지 자동 삽입 설정 추가
        auto_image_checkbox = ft.Checkbox(
            label="이미지 자동 삽입 모드",
            value=True
        )
        
        auto_image_help_text = ft.Text(
            "체크: 이미지를 자동으로 삽입합니다. 체크 해제: 수동으로 이미지를 선택합니다.",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True
        )

        # 이미지 삽입 모드 기본값 설정 (UI 요소 제거)
        image_insert_mode_value = "random"
        
        # API 사용 여부에 따라 API 키 필드 표시/숨김
        def on_api_checkbox_change(e):
            api_key_field.visible = use_api_checkbox.value
            api_key_help_text.visible = use_api_checkbox.value
            page.update()
            
        use_api_checkbox.on_change = on_api_checkbox_change

        def save_app_settings(e=None):
            try:
                app_settings = {
                    "use_dummy": not use_api_checkbox.value,
                    "auto_upload": auto_upload_checkbox.value,
                    "auto_image": auto_image_checkbox.value,
                    "auto_topic": auto_topic_checkbox.value,
                    "image_insert_mode": image_insert_mode_value,  # 이미지 삽입 방식 저장
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                with open(os.path.join(self.base_dir, 'config/app_settings.json'), 'w', encoding='utf-8') as f:
                    json.dump(app_settings, f, ensure_ascii=False, indent=2)
                
                if e:  # 직접 호출이 아닌 경우에만 메시지 표시
                    page.snack_bar = ft.SnackBar(content=ft.Text("앱 설정이 저장되었습니다."))
                    page.snack_bar.open = True
                    page.update()
            except Exception as e:
                if e:  # 직접 호출이 아닌 경우에만 메시지 표시
                    page.snack_bar = ft.SnackBar(content=ft.Text(f"저장 중 오류 발생: {str(e)}"))
                    page.snack_bar.open = True
                    page.update()

        def load_app_settings():
            try:
                if os.path.exists(os.path.join(self.base_dir, 'config/app_settings.json')):
                    with open(os.path.join(self.base_dir, 'config/app_settings.json'), 'r', encoding='utf-8') as f:
                        app_settings = json.load(f)
                        use_api_checkbox.value = not app_settings.get('use_dummy', False)
                        api_key_field.visible = use_api_checkbox.value
                        api_key_help_text.visible = use_api_checkbox.value
                        auto_upload_checkbox.value = app_settings.get('auto_upload', False)
                        auto_image_checkbox.value = app_settings.get('auto_image', True)
                        auto_topic_checkbox.value = app_settings.get('auto_topic', False)
                        image_insert_mode_value = app_settings.get('image_insert_mode', 'random')  # 이미지 삽입 방식 로드
                        page.update()
                        
                    # 자동 주제 모드 상태 표시 업데이트    
                    # on_auto_topic_change가 호출 가능한지 확인
                    try:
                        # 함수가 있다면 호출
                        if 'on_auto_topic_change' in locals() or 'on_auto_topic_change' in globals():
                            on_auto_topic_change(None)
                        else:
                            # 함수가 정의되지 않았다면 로그만 남김
                            print("on_auto_topic_change 함수가 아직 정의되지 않았습니다.")
                    except Exception as e:
                        print(f"자동 주제 상태 업데이트 중 오류: {str(e)}")
            except Exception as e:
                print(f"앱 설정 로드 중 오류 발생: {str(e)}")

        def save_gpt_settings(e):
            try:
                settings = {
                    "persona": gpt_persona.value,
                    "instructions": gpt_instructions.value,
                    "style": gpt_style.value,
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                with open(os.path.join(self.base_dir, 'config/gpt_settings.txt'), 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)
                
                # API 키 저장 로직 개선
                if use_api_checkbox.value and api_key_field.value:
                    # 1. config 디렉토리 내 api_key.json 파일에 저장
                    api_key_file = os.path.join(self.base_dir, 'config/api_key.json')
                    with open(api_key_file, 'w', encoding='utf-8') as f:
                        json.dump({"api_key": api_key_field.value}, f, ensure_ascii=False)
                    
                    # 2. 환경 변수에 설정 (현재 실행 환경에서 사용)
                    os.environ['OPENAI_API_KEY'] = api_key_field.value
                    
                    # 3. 가능하다면 .env 파일도 업데이트 (빌드된 앱에서는 동작하지 않을 수 있음)
                    try:
                        env_path = os.path.join(self.base_dir, '.env')
                        env_content = f"OPENAI_API_KEY={api_key_field.value}\n"
                        with open(env_path, 'w', encoding='utf-8') as f:
                            f.write(env_content)
                    except Exception as env_error:
                        print(f".env 파일 업데이트 실패 (무시됨): {str(env_error)}")
                
                # GPT 핸들러 재초기화
                self.use_dummy = not use_api_checkbox.value
                # API 키를 명시적으로 전달하여 환경 변수 외에도 직접 사용하도록 함
                api_key = api_key_field.value if use_api_checkbox.value else None
                self.gpt_handler = GPTHandler(api_key=api_key, use_dummy=self.use_dummy)
                
                # 앱 설정 저장
                save_app_settings()
                
                page.snack_bar = ft.SnackBar(content=ft.Text("GPT 설정이 저장되었습니다."))
                page.snack_bar.open = True
                page.update()
            except Exception as e:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"저장 중 오류 발생: {str(e)}"))
                page.snack_bar.open = True
                page.update()

        def load_gpt_settings():
            try:
                if os.path.exists(os.path.join(self.base_dir, 'config/gpt_settings.txt')):
                    with open(os.path.join(self.base_dir, 'config/gpt_settings.txt'), 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                        gpt_persona.value = settings.get('persona', '')
                        
                        # 고정 검토 지침 제거 (UI에 표시하지 않음)
                        instructions = settings.get('instructions', '')
                        fixed_review_prefix = """글 작성 후 반드시 다음 사항을 검토해주세요:
1. 오타와 맞춤법 오류가 없는지 확인
2. 문장 간 연결이 자연스러운지 확인
3. 논리적 흐름이 일관되는지 확인
4. 불필요한 반복이나 중복 표현이 없는지 확인
5. 전체적인 글의 통일성과 완성도 검토

"""
                        if instructions.startswith(fixed_review_prefix):
                            # 고정 검토 지침을 제외한 사용자 지침만 표시
                            gpt_instructions.value = instructions[len(fixed_review_prefix):]
                        else:
                            gpt_instructions.value = instructions
                            
                        gpt_style.value = settings.get('style', '')
                
                # API 사용 여부 설정 로드
                if os.path.exists(os.path.join(self.base_dir, 'config/app_settings.json')):
                    with open(os.path.join(self.base_dir, 'config/app_settings.json'), 'r', encoding='utf-8') as f:
                        app_settings = json.load(f)
                        use_api_checkbox.value = not app_settings.get('use_dummy', False)
                        api_key_field.visible = use_api_checkbox.value
                        api_key_help_text.visible = use_api_checkbox.value
                        auto_upload_checkbox.value = app_settings.get('auto_upload', False)
                        auto_image_checkbox.value = app_settings.get('auto_image', True)
                        auto_topic_checkbox.value = app_settings.get('auto_topic', False)
                
                # API 키 로드 (개선된 로직)
                # 1. 먼저 저장된 API 키 파일 확인
                api_key_file = os.path.join(self.base_dir, 'config/api_key.json')
                if os.path.exists(api_key_file):
                    try:
                        with open(api_key_file, 'r', encoding='utf-8') as f:
                            api_key_data = json.load(f)
                            api_key_field.value = api_key_data.get('api_key', '')
                            # 환경 변수에도 설정
                            if api_key_field.value:
                                os.environ['OPENAI_API_KEY'] = api_key_field.value
                    except Exception as e:
                        print(f"API 키 파일 로드 중 오류: {str(e)}")
                
                # 2. 기존 방식으로 .env 파일 확인 (백업)
                if not api_key_field.value and os.path.exists(os.path.join(self.base_dir, '.env')):
                    try:
                        with open(os.path.join(self.base_dir, '.env'), 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.startswith('OPENAI_API_KEY='):
                                    api_key_val = line.split('=', 1)[1].strip()
                                    # 기본값이나 빈 값이 아닌 경우에만 설정
                                    if api_key_val and api_key_val != "sk-empty-key-for-initialization":
                                        api_key_field.value = api_key_val
                                        os.environ['OPENAI_API_KEY'] = api_key_val
                                        # API 키 파일에도 저장
                                        with open(api_key_file, 'w', encoding='utf-8') as kf:
                                            json.dump({"api_key": api_key_val}, kf, ensure_ascii=False)
                                    break
                    except Exception as e:
                        print(f".env 파일 로드 중 오류: {str(e)}")
                
                page.update()
            except Exception as e:
                print(f"GPT 설정 로드 중 오류 발생: {str(e)}")

        # 사용자 설정 탭 컴포넌트
        dojang_name = ft.TextField(
            label="도장 이름",
            hint_text="도장 이름을 입력하세요..."
        )

        address = ft.TextField(
            label="주소",
            hint_text="도장 주소를 입력하세요..."
        )

        phone = ft.TextField(
            label="연락처",
            hint_text="연락처를 입력하세요..."
        )

        blog_url = ft.TextField(
            label="블로그 URL",
            hint_text="네이버 블로그 URL을 입력하세요..."
        )

        naver_id = ft.TextField(
            label="네이버 아이디",
            hint_text="네이버 아이디를 입력하세요..."
        )

        naver_pw = ft.TextField(
            label="네이버 비밀번호",
            password=True,
            hint_text="네이버 비밀번호를 입력하세요..."
        )

        kakao_url = ft.TextField(
            label="카카오톡 오픈채팅방 주소",
            hint_text="카카오톡 오픈채팅방 URL을 입력하세요..."
        )

        blog_tags = ft.TextField(
            label="블로그 태그",
            hint_text="태그를 쉼표(,)로 구분하여 입력하세요. 예: 태권도,도장,무술",
            multiline=True,
            min_lines=2,
            max_lines=4
        )

        blog_topics = ft.TextField(
            label="블로그 주제 목록",
            hint_text="자동 작성에 사용될 주제들을 쉼표(,)로 구분하여 입력하세요. 예: 유산소운동의 중요성,근력운동의 효과,단백질 섭취의 중요성",
            multiline=True,
            min_lines=3,
            max_lines=6
        )

        # 개발자 정보
        developer_info = ft.Container(
            content=ft.Column([
                ft.Text("개발자 정보", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("라이온 개발팀"),
                ft.Text("이관원 (010-7282-5529)"),
                ft.Text("이예린 (010-3852-5339)")
            ]),
            padding=20,
            bgcolor=ft.Colors.ON_SURFACE_VARIANT,
            border_radius=10,
            margin=ft.margin.only(top=20)
        )

        def save_user_settings(e, base_dir=None):
            try:
                if base_dir is None:
                    base_dir = self.base_dir
                    
                settings = {
                    "dojang_name": dojang_name.value,
                    "address": address.value,
                    "phone": phone.value,
                    "blog_url": blog_url.value,
                    "naver_id": naver_id.value,
                    "naver_pw": naver_pw.value,
                    "kakao_url": kakao_url.value,
                    "blog_tags": blog_tags.value,
                    "blog_topics": blog_topics.value,
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                with open(os.path.join(base_dir, 'config/user_settings.txt'), 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)
                
                # 환경 변수 설정
                os.environ['NAVER_ID'] = naver_id.value
                os.environ['NAVER_PW'] = naver_pw.value
                
                page.snack_bar = ft.SnackBar(content=ft.Text("사용자 설정이 저장되었습니다."))
                page.snack_bar.open = True
                page.update()
            except Exception as e:
                page.snack_bar = ft.SnackBar(content=ft.Text(f"저장 중 오류 발생: {str(e)}"))
                page.snack_bar.open = True
                page.update()

        def load_user_settings():
            try:
                if os.path.exists(os.path.join(self.base_dir, 'config/user_settings.txt')):
                    with open(os.path.join(self.base_dir, 'config/user_settings.txt'), 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                        dojang_name.value = settings.get('dojang_name', '')
                        address.value = settings.get('address', '')
                        phone.value = settings.get('phone', '')
                        blog_url.value = settings.get('blog_url', '')
                        naver_id.value = settings.get('naver_id', '')
                        naver_pw.value = settings.get('naver_pw', '')
                        kakao_url.value = settings.get('kakao_url', '')
                        blog_tags.value = settings.get('blog_tags', '')
                        blog_topics.value = settings.get('blog_topics', '')
                        page.update()
            except Exception as e:
                print(f"사용자 설정 로드 중 오류 발생: {str(e)}")

        # 자동 저장 함수
        def auto_save(e=None):
            try:
                if title_input.value or content_input.value:
                    save_data = {
                        "title": title_input.value,
                        "content": content_input.value,
                        "last_saved": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    with open(os.path.join(self.base_dir, 'drafts/auto_save.json'), 'w', encoding='utf-8') as f:
                        json.dump(save_data, f, ensure_ascii=False, indent=2)
                    
                    status_text.value = f"마지막 저장: {save_data['last_saved']}"
                    page.update()
            except Exception as e:
                print(f"자동 저장 중 오류 발생: {str(e)}")

        def load_draft():
            try:
                if os.path.exists(os.path.join(self.base_dir, 'drafts/auto_save.json')):
                    with open(os.path.join(self.base_dir, 'drafts/auto_save.json'), 'r', encoding='utf-8') as f:
                        save_data = json.load(f)
                        title_input.value = save_data.get('title', '')
                        content_input.value = save_data.get('content', '')
                        if save_data.get('last_saved'):
                            status_text.value = f"마지막 저장: {save_data['last_saved']}"
                        page.update()
            except Exception as e:
                print(f"임시 저장 로드 중 오류 발생: {str(e)}")

        # 제목과 내용이 변경될 때마다 자동 저장
        def on_title_changed(e):
            auto_save()

        def on_content_changed(e):
            auto_save()

        # 상태 표시 텍스트
        status_text = ft.Text(
            value="",
            color=ft.Colors.GREY_700,
            size=12,
            italic=True
        )

        # UI 컴포넌트
        topic_input = ft.TextField(
            label="주제 입력",
            hint_text="블로그 포스트 주제를 입력하세요...",
            multiline=True,
            min_lines=2,
            max_lines=3,
            expand=True
        )

        chat_messages = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=10
        )

        title_input = ft.TextField(
            label="제목",
            hint_text="블로그 포스트 제목을 입력하세요...",
            multiline=True,
            min_lines=1,
            max_lines=2,
            expand=True,
            on_change=on_title_changed
        )

        content_input = ft.TextField(
            label="본문",
            hint_text="블로그 포스트 내용을 입력하세요...",
            multiline=True,
            min_lines=15,
            max_lines=30,
            expand=True,
            on_change=self.on_content_change
        )

        # 메시지 전송 처리
        def send_message(e):
            # 자동 주제 모드 체크
            if auto_topic_checkbox.value:
                # 순차적 주제 선택
                selected_topic = self.select_sequential_topic()
                if not selected_topic:
                    page.snack_bar = ft.SnackBar(content=ft.Text("자동 주제 선택 실패: 주제 목록이 비어 있습니다. 사용자 설정에서 주제를 추가해주세요."))
                    page.snack_bar.open = True
                    page.update()
                    return
                # 선택된 주제를 입력 필드에 설정
                topic_input.value = selected_topic
                page.update()
                
            # 수동 모드 체크
            if not topic_input.value:
                return

            # 입력값 처리
            chat_messages.controls.append(ft.Container(
                content=ft.Text(f"입력: {topic_input.value}"),
                bgcolor=ft.Colors.BLUE_100,
                padding=10,
                border_radius=10,
                margin=ft.margin.only(bottom=10)
            ))
            
            # 처리 중 표시
            progress_dlg = ft.AlertDialog(
                title=ft.Text("처리 중..."),
                content=ft.Column([
                    ft.Text("GPT가 글을 생성하고 있습니다. 잠시만 기다려주세요."),
                    ft.ProgressBar(width=400)
                ], tight=True),
            )
            page.dialog = progress_dlg
            progress_dlg.open = True
            page.update()
            
            try:
                # GPT 응답 생성
                result = self.gpt_handler.generate_content(topic_input.value)
                self.current_title = result["title"]
                self.current_content = result["content"]

                # 제목과 내용 업데이트
                title_input.value = self.current_title
                content_input.value = self.current_content

                # GPT 응답 표시
                chat_messages.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Text("제목: " + result["title"], size=16, weight=ft.FontWeight.BOLD),
                        ft.Text(result["content"])
                    ]),
                    bgcolor=ft.Colors.GREY_100,
                    padding=10,
                    border_radius=10,
                    margin=ft.margin.only(bottom=10)
                ))
                
                # 진행 대화상자 닫기
                progress_dlg.open = False
                page.update()
                
                # 자동 업로드가 설정된 경우
                if auto_upload_checkbox.value:
                    upload_to_blog(None)
                
            except Exception as e:
                # 진행 대화상자 닫기
                progress_dlg.open = False
                page.update()
                
                chat_messages.controls.append(ft.Container(
                    content=ft.Text(f"오류 발생: {str(e)}", color=ft.Colors.RED),
                    padding=10,
                    margin=ft.margin.only(bottom=10)
                ))
            
            # 자동 주제 모드이고 입력 필드를 지우는 경우에만 - 다음 자동 선택을 위해
            if auto_topic_checkbox.value:
                topic_input.value = ""
            else:
                topic_input.value = ""  # 수동 모드에서도 입력 필드 초기화
            page.update()

        # 블로그 업로드 처리
        def upload_to_blog(e):
            if not title_input.value or not content_input.value:
                page.snack_bar = ft.SnackBar(content=ft.Text("제목과 내용을 모두 입력해주세요."))
                page.snack_bar.open = True
                page.update()
                return

            try:
                # 업로드 진행 상태 표시
                progress = ft.ProgressBar(width=400)
                dlg = ft.AlertDialog(
                    title=ft.Text("업로드 중..."),
                    content=ft.Column([
                        ft.Text("네이버 블로그에 포스팅을 업로드하고 있습니다."),
                        progress
                    ], tight=True),
                )
                page.dialog = dlg
                dlg.open = True
                page.update()

                # 줄바꿈 처리 (한 줄이 25자를 넘지 않도록, 단어가 잘리지 않게)
                def format_content_for_mobile(content, max_chars=25):
                    formatted_content = ""
                    paragraphs = content.split('\n')
                    
                    for paragraph in paragraphs:
                        if not paragraph.strip():
                            formatted_content += "\n"
                            continue
                            
                        words = paragraph.split()
                        current_line = ""
                        
                        for word in words:
                            # 단어 자체가 max_chars보다 길면 그대로 사용
                            if len(word) > max_chars:
                                if current_line:
                                    formatted_content += current_line + "\n"
                                    current_line = ""
                                formatted_content += word + "\n"
                                continue
                                
                            # 현재 줄에 단어를 추가했을 때 max_chars를 초과하는지 확인
                            if len(current_line) + len(word) + (1 if current_line else 0) > max_chars:
                                formatted_content += current_line + "\n"
                                current_line = word
                            else:
                                if current_line:
                                    current_line += " " + word
                                else:
                                    current_line = word
                        
                        # 마지막 줄 추가
                        if current_line:
                            formatted_content += current_line + "\n"
                        
                        # 문단 사이에 빈 줄 추가
                        formatted_content += "\n"
                    
                    return formatted_content.strip()
                
                # 원본 내용을 모바일 친화적으로 포맷팅
                formatted_content = format_content_for_mobile(content_input.value)
                
                # 임시 파일에 내용 저장
                today = datetime.now().strftime("%Y-%m-%d")
                os.makedirs(os.path.join(self.base_dir, today), exist_ok=True)
                
                file_path = os.path.join(os.path.join(self.base_dir, today), f"{title_input.value}.txt")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"제목: {title_input.value}\n\n{formatted_content}")

                try:
                    # naver_blog_auto.py 실행
                    from naver_blog_auto import NaverBlogAutomation
                    
                    # 현재 이미지 폴더 인덱스 기반으로 커스텀 이미지 폴더 가져오기
                    custom_images_folder = None
                    try:
                        # get_next_image_folder() 함수 호출 - 이미 사용된 폴더를 제외하고 다음 폴더 선택
                        folder_path = self.get_next_image_folder()
                        
                        if os.path.exists(folder_path):
                            custom_images_folder = folder_path
                            print(f"커스텀 이미지 폴더 사용: {folder_path}")
                    except Exception as e:
                        print(f"커스텀 이미지 폴더 설정 오류: {str(e)}")
                    
                    # 블로그 자동화 인스턴스 생성 (이미지 자동 삽입 모드와 삽입 방식 전달)
                    blog_auto = NaverBlogAutomation(
                        auto_mode=auto_image_checkbox.value,
                        image_insert_mode=image_insert_mode_value,
                        use_stickers=False,  # 스티커 사용 비활성화
                        custom_images_folder=custom_images_folder  # 커스텀 이미지 폴더 전달
                    )
                    
                    try:
                        # 드라이버 설정
                        blog_auto.setup_driver()
                        dlg.content.controls[0].value = "크롬 드라이버 설정 완료..."
                        page.update()
                        
                        # 네이버 로그인
                        if blog_auto.login_naver():
                            dlg.content.controls[0].value = "네이버 로그인 완료..."
                            page.update()
                            
                            # 블로그 글쓰기 페이지로 이동
                            if blog_auto.go_to_blog():
                                dlg.content.controls[0].value = "블로그 글쓰기 페이지 이동 완료..."
                                page.update()
                                
                                # 저장된 태그 가져오기
                                tags = []
                                if os.path.exists(os.path.join(self.base_dir, 'config/user_settings.txt')):
                                    with open(os.path.join(self.base_dir, 'config/user_settings.txt'), 'r', encoding='utf-8') as f:
                                        settings = json.load(f)
                                        tags = [tag.strip() for tag in settings.get('blog_tags', '').split(',') if tag.strip()]
                                
                                # 포맷팅된 내용으로 포스트 작성 및 발행
                                if blog_auto.write_post(title_input.value, formatted_content, tags=tags):
                                    dlg.open = False
                                    page.update()
                                    page.snack_bar = ft.SnackBar(content=ft.Text("블로그에 성공적으로 업로드되었습니다!"))
                                    page.snack_bar.open = True
                                    page.update()
                                    return
                                else:
                                    raise Exception("포스트 작성 실패")

                    except Exception as e:
                        print(f"블로그 자동화 중 오류 발생: {str(e)}")
                        raise e
                        
                except Exception as e:
                    print(f"NaverBlogAutomation 초기화 중 오류 발생: {str(e)}")
                    raise e
                    
            except Exception as e:
                print(f"업로드 중 오류 발생: {str(e)}")
                dlg.open = False
                page.update()
                page.snack_bar = ft.SnackBar(content=ft.Text(f"업로드 중 오류가 발생했습니다: {str(e)}"))
                page.snack_bar.open = True
                page.update()

        # 버튼 컴포넌트
        send_button = ft.ElevatedButton(
            text="전송",
            icon=ft.Icons.SEND,
            on_click=send_message
        )

        upload_button = ft.ElevatedButton(
            text="블로그에 업로드",
            icon=ft.Icons.UPLOAD,
            on_click=upload_to_blog
        )

        # GPT 설정 저장 버튼
        save_gpt_button = ft.ElevatedButton(
            text="GPT 설정 저장",
            icon=ft.Icons.SAVE,
            on_click=save_gpt_settings
        )

        # 사용자 설정 저장 버튼
        save_user_button = ft.ElevatedButton(
            text="사용자 설정 저장",
            icon=ft.Icons.SAVE,
            on_click=lambda e: save_user_settings(e, self.base_dir)
        )

        # 왼쪽 패널
        auto_topic_status = ft.Text(
            value="자동 주제 모드: " + ("활성화" if auto_topic_checkbox.value else "비활성화"),
            color=ft.Colors.GREEN if auto_topic_checkbox.value else ft.Colors.GREY_600,
            size=12,
            italic=True,
            visible=True
        )
        
        left_panel = ft.Column(
            controls=[
                topic_input,
                ft.Row(
                    controls=[
                        send_button,
                        auto_topic_status
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                chat_messages
            ],
            spacing=10,
            expand=True
        )

        # 오른쪽 패널
        right_panel = ft.Column(
            controls=[
                title_input,
                content_input,
                auto_image_checkbox,
                auto_image_help_text,
                upload_button,
                status_text
            ],
            spacing=10,
            expand=True
        )

        # GPT 설정 탭
        gpt_settings_tab = ft.Container(
            content=ft.Column(
                controls=[
                    gpt_persona,
                    persona_help_text,
                    gpt_instructions,
                    instructions_help_text,
                    gpt_style,
                    style_help_text,
                    use_api_checkbox,
                    api_key_field,
                    api_key_help_text,
                    auto_upload_checkbox,
                    auto_upload_help_text,
                    auto_topic_checkbox,
                    auto_topic_help_text,
                    save_gpt_button
                ],
                spacing=20,
                scroll=ft.ScrollMode.AUTO
            ),
            padding=20,
            expand=True
        )

        # 사용자 설정 탭
        user_settings_tab = ft.Container(
            content=ft.Column(
                controls=[
                    dojang_name,
                    address,
                    phone,
                    blog_url,
                    naver_id,
                    naver_pw,
                    kakao_url,
                    blog_tags,
                    blog_topics,
                    save_user_button,
                    developer_info
                ],
                spacing=20,
                scroll=ft.ScrollMode.AUTO
            ),
            padding=20,
            expand=True
        )

        # 메인 컨텐츠 탭
        main_content_tab = ft.Row(
            controls=[
                ft.Container(
                    content=left_panel,
                    padding=10,
                    border=ft.border.all(1, ft.Colors.GREY_400),
                    border_radius=10,
                    expand=True
                ),
                ft.Container(
                    content=right_panel,
                    padding=10,
                    border=ft.border.all(1, ft.Colors.GREY_400),
                    border_radius=10,
                    expand=True
                )
            ],
            spacing=20,
            expand=True
        )

        # 탭 컨트롤
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="블로그 작성",
                    icon=ft.Icons.EDIT_NOTE,
                    content=main_content_tab
                ),
                ft.Tab(
                    text="GPT 설정",
                    icon=ft.Icons.SETTINGS_APPLICATIONS,
                    content=gpt_settings_tab
                ),
                ft.Tab(
                    text="사용자 설정",
                    icon=ft.Icons.PERSON,
                    content=user_settings_tab
                )
            ],
            expand=True
        )

        # 탭 컨트롤 위에 앱 바와 시리얼 아이콘 추가
        # 시리얼 인증 상태 표시
        serial_status = ft.Text(
            "인증 상태 확인 중...",
            color=ft.Colors.BLUE_600,
            size=12
        )
        
        # 앱 바 생성
        page.appbar = ft.AppBar(
            title=ft.Text("네이버 블로그 자동화"),
            center_title=True,
            bgcolor=ft.Colors.ON_SURFACE_VARIANT,
            actions=[
                # 시리얼 관리 버튼
                ft.IconButton(
                    icon=ft.Icons.KEY,
                    tooltip="시리얼 관리",
                    on_click=show_serial_ui_dialog,
                    icon_color=ft.Colors.YELLOW
                ),
                serial_status,  # 시리얼 상태 표시
                ft.Container(width=20)  # 우측 여백
            ]
        )

        # 페이지에 탭 추가
        page.add(tabs)
        
        # 설정 로드
        load_gpt_settings()
        load_user_settings()
        load_app_settings()
        load_draft()

        # auto_topic_checkbox 변경 이벤트 처리
        def on_auto_topic_change(e):
            if auto_topic_checkbox.value:
                # 주제 목록 수와 현재 인덱스 가져오기
                topic_count = 0
                try:
                    if os.path.exists(os.path.join(self.base_dir, 'config/user_settings.txt')):
                        with open(os.path.join(self.base_dir, 'config/user_settings.txt'), 'r', encoding='utf-8') as f:
                            settings = json.load(f)
                            topics_str = settings.get('blog_topics', '')
                            if topics_str:
                                topics = [topic.strip() for topic in topics_str.split(',') if topic.strip()]
                                topic_count = len(topics)
                except Exception:
                    pass
                
                auto_topic_status.value = f"자동 주제 모드: 활성화 (다음: {self.current_topic_index + 2}/{topic_count})"
            else:
                auto_topic_status.value = "자동 주제 모드: 비활성화"
                
            auto_topic_status.color = ft.Colors.GREEN if auto_topic_checkbox.value else ft.Colors.GREY_600
            page.update()
            
        auto_topic_checkbox.on_change = on_auto_topic_change

        # 시리얼 관리 UI 실행 함수 (앱바의 키 아이콘용)
        def run_serial_ui(e):
            print("\n====== 시리얼 UI 직접 실행 ======")
            
            try:
                # 서브프로세스로 시리얼 UI 실행
                script_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "modules/serial_validator/serial_ui.py"
                )
                print(f"시리얼 UI 경로: {script_path}")
                
                # 파이썬 인터프리터 경로 결정
                python_exe = sys.executable
                
                # 시리얼 UI 실행
                result = subprocess.run(
                    [python_exe, script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # 종료 코드가 2이면 로그아웃 성공을 의미함
                if result.returncode == 2:
                    print("시리얼이 로그아웃되었습니다. 앱을 종료합니다.")
                    # 종료 대화상자 표시
                    error_dialog = ft.AlertDialog(
                        title=ft.Text("로그아웃 완료"),
                        content=ft.Text("시리얼 번호가 로그아웃되었습니다.\n앱을 종료합니다. 다시 시작하여 시리얼 인증을 진행해주세요."),
                        actions=[
                            ft.TextButton("종료", on_click=lambda e: sys.exit(1))
                        ],
                        modal=True
                    )
                    page.dialog = error_dialog
                    error_dialog.open = True
                    page.update()
                    return
                
                # 시리얼 UI 종료 후 시리얼 인증 상태 재확인
                is_valid = self.check_serial_validation()
                
                if is_valid:
                    # 시리얼 유효함 - 상태 업데이트
                    print("시리얼 인증 상태: 유효함")
                    # 시리얼 상태 UI 초기화 - 기존 initialize_serial_status 함수 대신 내부 구현
                    self.update_serial_status()
                else:
                    # 시리얼 인증 실패 - 앱 종료
                    print("시리얼 인증 실패. 앱을 종료합니다.")
                    self.show_alert_dialog(
                        title="인증 실패",
                        content="시리얼 인증에 실패했습니다. 앱을 종료합니다."
                    )
                    self.exit_app()
            except Exception as e:
                print(f"시리얼 UI 실행 중 오류 발생: {str(e)}")
                serial_status.value = f"시리얼 UI 오류: {str(e)}"
                serial_status.color = ft.Colors.RED_600
                page.update()
        
        # 시리얼 상태 초기화 및 확인 함수
        def initialize_serial_status():
            try:
                # 시리얼 인증 상태 확인
                is_valid = self.check_serial_validation()
                
                # 시리얼 클라이언트가 존재하는지 확인
                if hasattr(self, 'serial_client') and self.serial_client:
                    # 인증 상태별 메시지 표시
                    if is_valid:
                        # 시리얼 번호 전체 표시 (마스킹 제거)
                        serial_num = self.serial_client.serial_number if self.serial_client.serial_number else "없음"
                        serial_status.value = f"인증됨: {serial_num}"
                        serial_status.color = ft.Colors.GREEN
                        
                        # 데이터베이스에서 직접 시리얼 정보 조회 (최신 정보 확보)
                        try:
                            # 데이터베이스 연결이 유효한지 확인
                            if hasattr(self.serial_client, 'cursor') and self.serial_client.cursor:
                                self.serial_client.cursor.execute(
                                    "SELECT serial_number, status, expiry_date FROM serial_data WHERE serial_number = ?", 
                                    (self.serial_client.serial_number,)
                                )
                                result = self.serial_client.cursor.fetchone()
                                
                                if result and result[2]:  # expiry_date 확인
                                    # 현재 날짜와 만료일 비교
                                    expiry_date = datetime.strptime(result[2], "%Y-%m-%d").date()
                                    today = datetime.now().date()
                                    days_left = (expiry_date - today).days
                                    
                                    print(f"[Serial] 현재 날짜: {today}, 만료일: {expiry_date}, 남은 일수: {days_left}")
                                    
                                    # 남은 일수에 따른 메시지 표시
                                    if days_left > 30:
                                        serial_status.value = f"인증됨: {serial_num}"
                                        serial_status.color = ft.Colors.GREEN
                                    elif days_left > 0:
                                        serial_status.value = f"인증됨: {serial_num} (만료 {days_left}일 전)"
                                        serial_status.color = ft.Colors.ORANGE
                                    else:
                                        serial_status.value = f"만료됨: {serial_num} (유효기간 종료)"
                                        serial_status.color = ft.Colors.RED
                        except Exception as db_error:
                            print(f"[Serial] 데이터베이스 조회 오류: {str(db_error)}")
                            
                            # 기존 방식으로 폴백: client 객체의 속성 사용
                            if self.serial_client.expiry_date:
                                try:
                                    expiry_date = datetime.strptime(self.serial_client.expiry_date, "%Y-%m-%d").date()
                                    today = datetime.now().date()
                                    days_left = (expiry_date - today).days
                                    
                                    print(f"[Serial] (폴백) 현재 날짜: {today}, 만료일: {expiry_date}, 남은 일수: {days_left}")
                                    
                                    # 남은 일수에 따른 메시지 표시
                                    if days_left <= 30 and days_left > 0:
                                        serial_status.value = f"인증됨: {serial_num} (만료 {days_left}일 전)"
                                        serial_status.color = ft.Colors.ORANGE
                                except Exception as ex:
                                    print(f"[Serial] 만료일 계산 오류 (폴백): {str(ex)}")
                    else:
                        # 인증 실패 상태 표시
                        status_text = self.serial_client.status if self.serial_client.status else "인증되지 않음"
                        serial_status.value = f"상태: {status_text}"
                        serial_status.color = ft.Colors.RED
                else:
                    # 시리얼 클라이언트가 없는 경우
                    serial_status.value = "시리얼 정보 없음"
                    serial_status.color = ft.Colors.RED
                
                # UI 업데이트
                page.update()
            except Exception as e:
                print(f"시리얼 상태 초기화 오류: {str(e)}")
                # 오류 발생 시 기본 상태로 설정
                serial_status.value = "시리얼 상태 오류"
                serial_status.color = ft.Colors.RED
                page.update()

        # 앱 바 생성 함수
        def create_app_bar():
            page.appbar = ft.AppBar(
                title=ft.Text("네이버 블로그 자동화"),
                center_title=True,
                bgcolor=ft.Colors.ON_SURFACE_VARIANT,
                actions=[
                    # 시리얼 관리 버튼
                    ft.IconButton(
                        icon=ft.Icons.KEY,
                        tooltip="시리얼 관리",
                        on_click=show_serial_ui_dialog,
                        icon_color=ft.Colors.YELLOW
                    ),
                    serial_status,  # 시리얼 상태 표시
                    ft.Container(width=20)  # 우측 여백
                ]
            )

        # 앱 시작 시 시리얼 인증 확인
        check_and_show_serial()

    def exit_app(self):
        """앱을 안전하게 종료합니다"""
        print("앱 종료 중...")
        self.is_closing = True
        sys.exit(0)

    def update_serial_status(self):
        """시리얼 상태 UI 업데이트"""
        try:
            if hasattr(self, 'page') and self.page:
                # UI 요소 찾기
                for control in self.page.controls:
                    if isinstance(control, ft.AppBar) and control.title:
                        # AppBar의 제목 업데이트
                        if hasattr(self, 'serial_client') and self.serial_client:
                            status_text = "✅ 인증됨"
                            if self.serial_client.expiry_date:
                                try:
                                    expiry = datetime.strptime(self.serial_client.expiry_date, "%Y-%m-%d").date()
                                    days_left = (expiry - datetime.now().date()).days
                                    if days_left > 0:
                                        status_text += f" (남은 기간: {days_left}일)"
                                except Exception as e:
                                    print(f"만료일 계산 오류: {str(e)}")
                            
                            # 시리얼 상태 텍스트 업데이트
                            for child in control.actions:
                                if isinstance(child, ft.Text):
                                    child.value = status_text
                                    child.color = ft.Colors.GREEN_400
                
                # 페이지 업데이트
                self.page.update()
                print("시리얼 상태 UI 업데이트 완료")
        except Exception as e:
            print(f"시리얼 상태 UI 업데이트 오류: {str(e)}")
            
    def show_alert_dialog(self, title, content, actions=None):
        """경고 대화상자 표시"""
        try:
            if not hasattr(self, 'page') or not self.page:
                print(f"대화상자 표시 실패 (페이지 없음): {title} - {content}")
                return False
                
            # 기본 종료 버튼
            if actions is None:
                actions = [
                    ft.TextButton("확인", on_click=lambda e: self.close_dialog(e))
                ]
                
            # 대화상자 생성
            alert_dialog = ft.AlertDialog(
                title=ft.Text(title),
                content=ft.Text(content),
                actions=actions,
                modal=True
            )
            
            # 대화상자 표시
            self.page.dialog = alert_dialog
            alert_dialog.open = True
            self.page.update()
            return True
        except Exception as e:
            print(f"대화상자 표시 오류: {str(e)}")
            return False
            
    def close_dialog(self, e=None):
        """열려있는 대화상자 닫기"""
        try:
            if hasattr(self, 'page') and self.page and self.page.dialog:
                self.page.dialog.open = False
                self.page.update()
        except Exception as e:
            print(f"대화상자 닫기 오류: {str(e)}")

if __name__ == "__main__":
    # 시리얼 검증 처리
    from modules.serial_validator.serial_client import SerialClient
    
    # 애플리케이션 초기화
    app = BlogWriterApp()
    
    # 로그아웃 상태 파일 체크 (시리얼 검증 전에 실행)
    logout_files = [
        os.path.join(app.base_dir, 'config/logout_status.txt'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules/serial_validator/config/logout_status.txt')
    ]
    
    logout_detected = False
    for logout_file in logout_files:
        if os.path.exists(logout_file):
            print(f"로그아웃 상태 파일 발견: {logout_file}")
            
            try:
                # 파일 내용 확인 후 삭제
                with open(logout_file, 'r', encoding='utf-8') as f:
                    logout_info = f.read()
                    print(f"로그아웃 정보: {logout_info}")
                os.remove(logout_file)
                print(f"로그아웃 상태 파일 삭제 완료: {logout_file}")
                logout_detected = True
            except Exception as e:
                print(f"로그아웃 상태 파일 처리 오류: {str(e)}")
    
    # 최소 1개의 로그아웃 상태 파일이 발견되었다면 시리얼 인증 UI 실행
    if logout_detected:
        # 시리얼 데이터베이스 초기화 추가
        try:
            # 모든 가능한 시리얼 정보 DB 경로
            db_paths = [
                os.path.join(app.base_dir, 'modules/serial_validator/serial_data.db'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules/serial_validator/serial_data.db')
            ]
            
            for db_path in db_paths:
                if os.path.exists(db_path):
                    try:
                        import sqlite3
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM serial_data")
                        conn.commit()
                        conn.close()
                        print(f"시리얼 데이터베이스 초기화 완료: {db_path}")
                    except Exception as db_error:
                        print(f"시리얼 데이터베이스 초기화 오류: {str(db_error)}")
        except Exception as init_error:
            print(f"데이터베이스 초기화 처리 오류: {str(init_error)}")
        
        # 시리얼 인증 UI 실행
        import subprocess
        import sys
        import os
        
        # 파이썬 인터프리터 및 시리얼 UI 스크립트 경로
        python_exe = sys.executable
        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "modules/serial_validator/serial_ui.py"
        )
        
        print("로그아웃 후 재시작: 시리얼 인증이 필요합니다. 인증 창이 열립니다.")
        
        # 블로킹 모드로 실행하여 시리얼 UI가 종료될 때까지 대기
        result = subprocess.run(
            [python_exe, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 종료 코드가 2이면 로그아웃 성공을 의미함
        if result.returncode == 2:
            print("시리얼이 로그아웃되었습니다. 앱을 즉시 종료합니다.")
            os._exit(1)  # 강제 종료
        
        # 시리얼 UI 종료 후 인증 상태 재확인
        is_valid = app.check_serial_validation()
        
        if is_valid:
            # 시리얼 검증이 성공한 경우, 앱 실행
            print("시리얼 인증에 성공했습니다. 앱을 시작합니다.")
            app = BlogWriterApp()  # 새 인스턴스 생성하여 최신 시리얼 정보 반영
            ft.app(target=app.main)
        else:
            # 시리얼이 여전히 유효하지 않은 경우
            print("시리얼 인증에 실패했습니다. 앱을 종료합니다.")
            os._exit(1)  # 강제 종료
    else:
        # 로그아웃 상태가 아니면 일반적인 시리얼 검증 절차 진행
        # 시리얼 클라이언트 인스턴스 직접 생성하여 상태 확인
        serial_client = SerialClient(app_name="BlogAutomation")
        is_valid = serial_client.is_valid_with_server_check()
        
        # 시리얼 상태 출력
        print(f"시리얼 상태: {serial_client.status}")
        print(f"시리얼 유효성: {is_valid}")
        
        # 인증된 경우 앱 실행
        if is_valid or app.check_serial_validation():
            print("시리얼 인증이 확인되었습니다. 앱을 시작합니다.")
            ft.app(target=app.main)
        else:
            # 인증되지 않은 경우 인증 UI 실행
            import subprocess
            import sys
            import os
            
            # 파이썬 인터프리터 및 시리얼 UI 스크립트 경로
            python_exe = sys.executable
            script_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "modules/serial_validator/serial_ui.py"
            )
            
            print("시리얼 인증이 필요합니다. 인증 창이 열립니다.")
            
            # 블로킹 모드로 실행하여 시리얼 UI가 종료될 때까지 대기
            result = subprocess.run(
                [python_exe, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 종료 코드가 2이면 로그아웃 성공을 의미함
            if result.returncode == 2:
                print("시리얼이 로그아웃되었습니다. 앱을 즉시 종료합니다.")
                os._exit(1)  # 강제 종료
            
            # 시리얼 UI 종료 후 인증 상태 재확인
            is_valid = app.check_serial_validation()
            
            if is_valid:
                # 시리얼 검증이 성공한 경우, 앱 실행
                print("시리얼 인증에 성공했습니다. 앱을 시작합니다.")
                app = BlogWriterApp()  # 새 인스턴스 생성하여 최신 시리얼 정보 반영
                ft.app(target=app.main)
            else:
                # 시리얼이 여전히 유효하지 않은 경우
                if hasattr(app, 'serial_client') and app.serial_client and app.serial_client.status:
                    print(f"시리얼 인증 실패: {app.serial_client.status}")
                    error_message = "시리얼 인증 실패"
                    
                    if app.serial_client.status == "만료됨":
                        error_message = "시리얼이 만료되었습니다. 갱신이 필요합니다."
                    elif app.serial_client.status == "사용중" or app.serial_client.status == "다른 디바이스에서 사용중":
                        error_message = "시리얼이 다른 기기에서 사용 중입니다."
                    elif app.serial_client.status == "블랙리스트":
                        error_message = "사용할 수 없는 시리얼 번호입니다."
                    else:
                        error_message = f"시리얼 인증 실패: {app.serial_client.status}"
                    
                    # 명령줄에 오류 메시지 출력
                    print(error_message)
                else:
                    print("시리얼 인증에 실패했습니다.")
                
                os._exit(1)  # 강제 종료