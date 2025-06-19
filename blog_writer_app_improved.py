#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
개선된 블로그 작성 앱
- 완벽한 자동화 워크플로우
- 안정적인 로그인 및 발행
- 사용자 친화적 UI
- 타이머 자동화 기능
"""

import flet as ft
import os
import sys
import json
import threading
import time
import random
from datetime import datetime, timedelta
from naver_blog_auto_improved import ImprovedNaverBlogAuto
from modules.gpt_handler import GPTHandler

class ImprovedBlogWriterApp:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.blog_auto = None
        self.gpt_handler = None
        self.is_running = False
        
        # 타이머 관련 변수들
        self.timer_running = False
        self.timer_thread = None
        self.next_post_time = None
        self.daily_post_count = 0
        self.timer_settings = {
            'start_time': '09:00',
            'end_time': '23:00', 
            'min_interval': 15,
            'max_interval': 20,
            'max_daily_posts': 20
        }
        
    def main(self, page: ft.Page):
        page.title = "한국체대라이온합기도 블로그 자동화 시스템"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 1000
        page.window_height = 800
        page.window_resizable = True
        
        # 공통 UI 컴포넌트들
        self.status_text = ft.Text("시스템 준비 완료", size=16, color=ft.Colors.GREEN)
        self.log_text = ft.Text("", size=12, selectable=True)
        
        # 타이머 상태 표시 (메인 탭용)
        self.timer_status_text = ft.Text("타이머 중지됨", size=14, color=ft.Colors.GREY)
        self.next_post_text = ft.Text("", size=12, color=ft.Colors.BLUE)
        self.daily_count_text = ft.Text("오늘 포스팅: 0회", size=12, color=ft.Colors.GREEN)
        
        # 타이머 제어 버튼 (메인 탭용)
        self.timer_start_btn = ft.ElevatedButton(
            "타이머 시작",
            on_click=self.start_timer,
            bgcolor=ft.Colors.GREEN,
            color=ft.Colors.WHITE,
            width=120
        )
        
        self.timer_stop_btn = ft.ElevatedButton(
            "타이머 중지",
            on_click=self.stop_timer,
            bgcolor=ft.Colors.RED,
            color=ft.Colors.WHITE,
            width=120,
            disabled=True
        )
        
        # 설정 입력 필드들
        self.naver_id_field = ft.TextField(
            label="네이버 아이디",
            width=300,
            value="gm2hapkido"
        )
        
        self.naver_pw_field = ft.TextField(
            label="네이버 비밀번호",
            password=True,
            can_reveal_password=True,
            width=300,
            value="km909090##"
        )
        
        self.blog_url_field = ft.TextField(
            label="블로그 URL",
            width=300,
            value="gm2hapkido"
        )
        
        self.title_field = ft.TextField(
            label="글 제목",
            width=600,
            value="아이들의 건강한 성장을 위한 합기도의 효과"
        )
        
        self.content_field = ft.TextField(
            label="글 내용",
            multiline=True,
            min_lines=10,
            max_lines=20,
            width=600,
            value="""안녕하세요! 한국체대라이온합기도 체육관입니다.

오늘은 아이들의 건강한 성장에 합기도가 어떤 도움을 주는지 알아보겠습니다.

## 합기도가 아이들에게 주는 효과

### 1. 신체 발달
합기도는 전신을 고르게 사용하는 운동으로, 아이들의 균형 잡힌 신체 발달에 도움을 줍니다.

### 2. 정신력 강화
규칙적인 수련을 통해 집중력과 인내심을 기를 수 있습니다.

### 3. 사회성 발달
도장에서 선후배와의 관계를 통해 예의와 배려를 배웁니다.

## 한국체대라이온합기도의 특별함

저희 체육관은 체계적인 커리큘럼과 전문 지도진을 통해 아이들의 건강한 성장을 돕고 있습니다.

궁금한 점이 있으시면 언제든 문의해 주세요!"""
        )
        
        self.tags_field = ft.TextField(
            label="태그 (쉼표로 구분)",
            width=600,
            value="합기도, 아이건강, 운동, 성장발달, 한국체대라이온합기도"
        )
        
        self.slogan_field = ft.TextField(
            label="마지막 슬로건 (예: 바른 인성을 가진 인재를 기르는 한국체대 라이온 태권도 합기도)",
            width=600,
            value="바른 인성을 가진 인재를 기르는 한국체대 라이온 태권도 합기도",
            hint_text="이상 [여기에 입력한 내용] 이었습니다 형식으로 표시됩니다"
        )
        
        # 타이머 설정 필드들
        self.start_time_field = ft.TextField(
            label="시작 시간 (HH:MM)",
            width=150,
            value="09:00",
            hint_text="예: 09:00"
        )
        
        self.end_time_field = ft.TextField(
            label="종료 시간 (HH:MM)",
            width=150,
            value="23:00",
            hint_text="예: 23:00"
        )
        
        self.min_interval_field = ft.TextField(
            label="최소 간격 (분)",
            width=150,
            value="15",
            hint_text="예: 15"
        )
        
        self.max_interval_field = ft.TextField(
            label="최대 간격 (분)",
            width=150,
            value="20",
            hint_text="예: 20"
        )
        
        self.max_posts_field = ft.TextField(
            label="일일 최대 포스팅 수",
            width=150,
            value="20",
            hint_text="예: 20"
        )
        
        # 버튼들
        self.save_settings_btn = ft.ElevatedButton(
            "설정 저장",
            on_click=self.save_settings,
            bgcolor=ft.Colors.BLUE,
            color=ft.Colors.WHITE
        )
        
        self.test_login_btn = ft.ElevatedButton(
            "로그인 테스트",
            on_click=self.test_login,
            bgcolor=ft.Colors.ORANGE,
            color=ft.Colors.WHITE
        )
        
        self.auto_write_btn = ft.ElevatedButton(
            "자동 글쓰기 & 발행",
            on_click=self.auto_write_and_publish,
            bgcolor=ft.Colors.GREEN,
            color=ft.Colors.WHITE,
            width=200,
            height=50
        )
        
        self.stop_btn = ft.ElevatedButton(
            "중지",
            on_click=self.stop_automation,
            bgcolor=ft.Colors.RED,
            color=ft.Colors.WHITE,
            disabled=True
        )
        
        self.save_timer_btn = ft.ElevatedButton(
            "타이머 설정 저장",
            on_click=self.save_timer_settings,
            bgcolor=ft.Colors.PURPLE,
            color=ft.Colors.WHITE
        )
        
        # 탭 생성
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="블로그 작성",
                    icon=ft.Icons.EDIT,
                    content=self.create_main_tab()
                ),
                ft.Tab(
                    text="타이머 설정",
                    icon=ft.Icons.TIMER,
                    content=self.create_timer_tab()
                )
            ]
        )
        
        # 메인 레이아웃
        page.add(
            ft.Container(
                content=ft.Column([
                    # 헤더
                    ft.Container(
                        content=ft.Text(
                            "한국체대라이온합기도 블로그 자동화 시스템",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_900
                        ),
                        alignment=ft.alignment.center,
                        padding=20
                    ),
                    
                    # 상태 표시
                    ft.Container(
                        content=self.status_text,
                        alignment=ft.alignment.center,
                        padding=10
                    ),
                    
                    # 탭
                    self.tabs
                ]),
                padding=20
            )
        )
        
        # 초기 설정 로드
        self.load_settings()
        self.load_timer_settings()
        self.update_timer_display()
    
    def create_main_tab(self):
        """메인 탭 (블로그 작성) 생성"""
        return ft.Container(
            content=ft.Column([
                # 타이머 상태 섹션 (메인 탭)
                ft.Container(
                    content=ft.Column([
                        ft.Text("⏰ 타이머 상태", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE),
                        ft.Row([
                            ft.Column([
                                self.timer_status_text,
                                self.next_post_text,
                                self.daily_count_text
                            ], spacing=5),
                            ft.Column([
                                self.timer_start_btn,
                                self.timer_stop_btn
                            ], spacing=10)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ]),
                    padding=20,
                    border=ft.border.all(2, ft.Colors.PURPLE_300),
                    border_radius=10,
                    margin=10,
                    bgcolor=ft.Colors.PURPLE_50
                ),
                
                # 네이버 로그인 설정 섹션
                ft.Container(
                    content=ft.Column([
                        ft.Text("네이버 로그인 설정", size=18, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            self.naver_id_field,
                            self.naver_pw_field,
                            self.blog_url_field
                        ]),
                        ft.Row([
                            self.save_settings_btn,
                            self.test_login_btn
                        ])
                    ]),
                    padding=20,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                    margin=10
                ),
                
                # 사용자 설정 섹션
                ft.Container(
                    content=ft.Column([
                        ft.Text("사용자 설정", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_700),
                        ft.Text("블로그 글 마지막에 표시될 슬로건을 설정하세요", size=14, color=ft.Colors.GREY_600),
                        self.slogan_field,
                        ft.Text("💡 예시: '이상 바른 인성을 가진 인재를 기르는 한국체대 라이온 태권도 합기도 이었습니다'", 
                               size=12, color=ft.Colors.GREY_500, italic=True)
                    ]),
                    padding=20,
                    border=ft.border.all(1, ft.Colors.PURPLE_200),
                    border_radius=10,
                    margin=10,
                    bgcolor=ft.Colors.PURPLE_50
                ),
                
                # 글 작성 섹션
                ft.Container(
                    content=ft.Column([
                        ft.Text("블로그 글 작성", size=18, weight=ft.FontWeight.BOLD),
                        self.title_field,
                        self.content_field,
                        self.tags_field,
                        ft.Row([
                            self.auto_write_btn,
                            self.stop_btn
                        ])
                    ]),
                    padding=20,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                    margin=10
                ),
                
                # 로그 섹션
                ft.Container(
                    content=ft.Column([
                        ft.Text("실행 로그", size=18, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=self.log_text,
                            height=200,
                            width=900,
                            padding=10,
                            bgcolor=ft.Colors.GREY_100,
                            border_radius=5
                        )
                    ]),
                    padding=20,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                    margin=10
                )
            ], scroll=ft.ScrollMode.AUTO),
            padding=10
        )
    
    def create_timer_tab(self):
        """타이머 설정 탭 생성"""
        return ft.Container(
            content=ft.Column([
                # 타이머 설정 설명
                ft.Container(
                    content=ft.Column([
                        ft.Text("🤖 자동 타이머 설정", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                        ft.Text("설정된 시간 동안 랜덤 간격으로 자동 포스팅을 진행합니다.", size=14, color=ft.Colors.GREY_700),
                        ft.Text("⚠️ 네이버 자동화 감지를 피하기 위해 랜덤 간격과 시간 제한을 설정하세요.", 
                               size=12, color=ft.Colors.RED_600, weight=ft.FontWeight.BOLD)
                    ]),
                    padding=20,
                    border=ft.border.all(2, ft.Colors.BLUE_300),
                    border_radius=10,
                    margin=10,
                    bgcolor=ft.Colors.BLUE_50
                ),
                
                # 시간 설정
                ft.Container(
                    content=ft.Column([
                        ft.Text("⏰ 운영 시간 설정", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text("매일 자동으로 시작/종료되는 시간을 설정하세요", size=14, color=ft.Colors.GREY_600),
                        ft.Row([
                            self.start_time_field,
                            ft.Text("부터", size=16),
                            self.end_time_field,
                            ft.Text("까지", size=16)
                        ], alignment=ft.MainAxisAlignment.START),
                        ft.Text("💡 예시: 오전 9시부터 오후 11시까지 운영", size=12, color=ft.Colors.GREY_500, italic=True)
                    ]),
                    padding=20,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                    margin=10
                ),
                
                # 간격 설정
                ft.Container(
                    content=ft.Column([
                        ft.Text("🎲 포스팅 간격 설정", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text("랜덤 간격으로 포스팅하여 자동화 감지를 방지합니다", size=14, color=ft.Colors.GREY_600),
                        ft.Row([
                            self.min_interval_field,
                            ft.Text("분 ~", size=16),
                            self.max_interval_field,
                            ft.Text("분 랜덤 간격", size=16)
                        ], alignment=ft.MainAxisAlignment.START),
                        ft.Text("💡 권장: 15분~20분 (포스팅 시간 5분 포함)", size=12, color=ft.Colors.GREY_500, italic=True)
                    ]),
                    padding=20,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                    margin=10
                ),
                
                # 포스팅 수 제한
                ft.Container(
                    content=ft.Column([
                        ft.Text("📊 일일 포스팅 제한", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text("하루 최대 포스팅 수를 설정하여 과도한 사용을 방지합니다", size=14, color=ft.Colors.GREY_600),
                        ft.Row([
                            ft.Text("하루 최대", size=16),
                            self.max_posts_field,
                            ft.Text("개 포스팅", size=16)
                        ], alignment=ft.MainAxisAlignment.START),
                        ft.Text("💰 GPT 토큰 비용 절약을 위해 적절한 수로 설정하세요", size=12, color=ft.Colors.ORANGE_600, italic=True)
                    ]),
                    padding=20,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                    margin=10
                ),
                
                # 설정 저장 버튼
                ft.Container(
                    content=ft.Row([
                        self.save_timer_btn,
                        ft.Text("설정을 저장한 후 '블로그 작성' 탭에서 타이머를 시작하세요", 
                               size=14, color=ft.Colors.BLUE_700)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    padding=20
                )
            ], scroll=ft.ScrollMode.AUTO),
            padding=10
        )
    
    def log(self, message):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.log_text.value += log_message
        self.log_text.update()
        print(message)  # 콘솔에도 출력
    
    def update_status(self, message, color=ft.Colors.BLUE):
        """상태 메시지 업데이트"""
        self.status_text.value = message
        self.status_text.color = color
        self.status_text.update()
    
    def update_timer_display(self):
        """타이머 상태 표시 업데이트"""
        try:
            if self.timer_running:
                self.timer_status_text.value = "⏰ 타이머 실행 중"
                self.timer_status_text.color = ft.Colors.GREEN
                
                if self.next_post_time:
                    time_diff = self.next_post_time - datetime.now()
                    if time_diff.total_seconds() > 0:
                        hours, remainder = divmod(int(time_diff.total_seconds()), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        self.next_post_text.value = f"다음 포스팅: {hours:02d}:{minutes:02d}:{seconds:02d} 후"
                    else:
                        self.next_post_text.value = "포스팅 준비 중..."
                else:
                    self.next_post_text.value = "다음 시간 계산 중..."
            else:
                self.timer_status_text.value = "⏸️ 타이머 중지됨"
                self.timer_status_text.color = ft.Colors.GREY
                self.next_post_text.value = ""
            
            self.daily_count_text.value = f"오늘 포스팅: {self.daily_post_count}회"
            
            # UI 업데이트
            self.timer_status_text.update()
            self.next_post_text.update()
            self.daily_count_text.update()
            
        except Exception as e:
            print(f"타이머 표시 업데이트 오류: {e}")
    
    def save_timer_settings(self, e):
        """타이머 설정 저장"""
        try:
            self.timer_settings = {
                'start_time': self.start_time_field.value,
                'end_time': self.end_time_field.value,
                'min_interval': int(self.min_interval_field.value),
                'max_interval': int(self.max_interval_field.value),
                'max_daily_posts': int(self.max_posts_field.value)
            }
            
            timer_settings_path = os.path.join(self.base_dir, 'config', 'timer_settings.json')
            with open(timer_settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.timer_settings, f, ensure_ascii=False, indent=2)
            
            self.log("✅ 타이머 설정이 저장되었습니다.")
            self.update_status("타이머 설정 저장 완료", ft.Colors.GREEN)
            
        except ValueError:
            self.log("❌ 타이머 설정 오류: 숫자 값을 확인해주세요.")
            self.update_status("타이머 설정 오류", ft.Colors.RED)
        except Exception as ex:
            self.log(f"❌ 타이머 설정 저장 실패: {ex}")
            self.update_status("타이머 설정 저장 실패", ft.Colors.RED)
    
    def load_timer_settings(self):
        """타이머 설정 로드"""
        try:
            timer_settings_path = os.path.join(self.base_dir, 'config', 'timer_settings.json')
            if os.path.exists(timer_settings_path):
                with open(timer_settings_path, 'r', encoding='utf-8') as f:
                    self.timer_settings = json.load(f)
                
                self.start_time_field.value = self.timer_settings.get('start_time', '09:00')
                self.end_time_field.value = self.timer_settings.get('end_time', '23:00')
                self.min_interval_field.value = str(self.timer_settings.get('min_interval', 15))
                self.max_interval_field.value = str(self.timer_settings.get('max_interval', 20))
                self.max_posts_field.value = str(self.timer_settings.get('max_daily_posts', 20))
                
                # UI 업데이트
                self.start_time_field.update()
                self.end_time_field.update()
                self.min_interval_field.update()
                self.max_interval_field.update()
                self.max_posts_field.update()
                
                self.log("✅ 타이머 설정을 불러왔습니다.")
            
        except Exception as ex:
            self.log(f"⚠️ 타이머 설정 로드 실패: {ex}")
    
    def is_within_operating_hours(self):
        """현재 시간이 운영 시간 내인지 확인"""
        try:
            now = datetime.now()
            start_time = datetime.strptime(self.timer_settings['start_time'], '%H:%M').time()
            end_time = datetime.strptime(self.timer_settings['end_time'], '%H:%M').time()
            current_time = now.time()
            
            if start_time <= end_time:
                return start_time <= current_time <= end_time
            else:  # 자정을 넘어가는 경우
                return current_time >= start_time or current_time <= end_time
                
        except Exception as e:
            self.log(f"운영 시간 확인 오류: {e}")
            return False
    
    def calculate_next_post_time(self):
        """다음 포스팅 시간 계산"""
        try:
            min_interval = self.timer_settings['min_interval']
            max_interval = self.timer_settings['max_interval']
            random_interval = random.randint(min_interval, max_interval)
            
            self.next_post_time = datetime.now() + timedelta(minutes=random_interval)
            self.log(f"📅 다음 포스팅 시간: {self.next_post_time.strftime('%H:%M:%S')} ({random_interval}분 후)")
            
        except Exception as e:
            self.log(f"다음 포스팅 시간 계산 오류: {e}")
    
    def start_timer(self, e):
        """타이머 시작"""
        try:
            if self.timer_running:
                self.log("⚠️ 타이머가 이미 실행 중입니다.")
                return
            
            # 일일 포스팅 수 확인
            if self.daily_post_count >= self.timer_settings['max_daily_posts']:
                self.log(f"❌ 일일 최대 포스팅 수({self.timer_settings['max_daily_posts']}개)에 도달했습니다.")
                return
            
            self.timer_running = True
            self.timer_start_btn.disabled = True
            self.timer_stop_btn.disabled = False
            self.timer_start_btn.update()
            self.timer_stop_btn.update()
            
            self.log("🚀 타이머가 시작되었습니다!")
            self.update_status("타이머 실행 중", ft.Colors.GREEN)
            
            # 첫 번째 포스팅 시간 계산
            self.calculate_next_post_time()
            
            # 타이머 스레드 시작
            self.timer_thread = threading.Thread(target=self.timer_loop, daemon=True)
            self.timer_thread.start()
            
        except Exception as ex:
            self.log(f"❌ 타이머 시작 실패: {ex}")
            self.update_status("타이머 시작 실패", ft.Colors.RED)
    
    def stop_timer(self, e):
        """타이머 중지"""
        try:
            self.timer_running = False
            self.timer_start_btn.disabled = False
            self.timer_stop_btn.disabled = True
            self.timer_start_btn.update()
            self.timer_stop_btn.update()
            
            self.log("⏹️ 타이머가 중지되었습니다.")
            self.update_status("타이머 중지됨", ft.Colors.ORANGE)
            self.update_timer_display()
            
        except Exception as ex:
            self.log(f"❌ 타이머 중지 실패: {ex}")
    
    def timer_loop(self):
        """타이머 메인 루프"""
        while self.timer_running:
            try:
                # 운영 시간 확인
                if not self.is_within_operating_hours():
                    self.log("⏰ 운영 시간이 아닙니다. 대기 중...")
                    time.sleep(60)  # 1분마다 확인
                    continue
                
                # 일일 포스팅 수 확인
                if self.daily_post_count >= self.timer_settings['max_daily_posts']:
                    self.log(f"📊 일일 최대 포스팅 수({self.timer_settings['max_daily_posts']}개)에 도달했습니다.")
                    break
                
                # 다음 포스팅 시간까지 대기
                if self.next_post_time and datetime.now() < self.next_post_time:
                    self.update_timer_display()
                    time.sleep(1)  # 1초마다 업데이트
                    continue
                
                # 자동 포스팅 실행
                self.log("🤖 자동 포스팅을 시작합니다...")
                self.execute_auto_posting()
                
                # 다음 포스팅 시간 계산
                if self.timer_running:
                    self.calculate_next_post_time()
                
            except Exception as e:
                self.log(f"❌ 타이머 루프 오류: {e}")
                time.sleep(60)  # 오류 시 1분 대기
        
        # 타이머 종료 처리
        self.timer_running = False
        self.timer_start_btn.disabled = False
        self.timer_stop_btn.disabled = True
        self.timer_start_btn.update()
        self.timer_stop_btn.update()
        self.update_timer_display()
    
    def execute_auto_posting(self):
        """자동 포스팅 실행"""
        try:
            # 기존 자동 글쓰기 로직 재사용
            self.blog_auto = ImprovedNaverBlogAuto(self.base_dir)
            
            # 1단계: 로그인 (세션 재사용)
            self.log("1️⃣ 네이버 로그인 중...")
            if not self.blog_auto.login_naver():
                raise Exception("로그인 실패")
            
            # 2단계: 글쓰기 페이지 이동
            self.log("2️⃣ 글쓰기 페이지로 이동 중...")
            if not self.blog_auto.go_to_blog_write():
                raise Exception("글쓰기 페이지 이동 실패")
            
            # 3단계: 글 작성 및 발행
            self.log("3️⃣ 글 작성 및 발행 중...")
            title = self.title_field.value
            content = self.content_field.value
            tags = [tag.strip() for tag in self.tags_field.value.split(',') if tag.strip()]
            
            if not self.blog_auto.write_post(title, content, tags):
                raise Exception("글 작성 및 발행 실패")
            
            # 포스팅 수 증가
            self.daily_post_count += 1
            self.log(f"✅ 자동 포스팅 완료! (오늘 {self.daily_post_count}번째)")
            
        except Exception as ex:
            self.log(f"❌ 자동 포스팅 실패: {ex}")
        
        finally:
            if self.blog_auto:
                self.blog_auto.close()
                self.blog_auto = None
    
    def save_settings(self, e):
        """설정 저장"""
        try:
            settings = {
                'naver_id': self.naver_id_field.value,
                'naver_pw': self.naver_pw_field.value,
                'blog_url': self.blog_url_field.value,
                'slogan': self.slogan_field.value,
                'last_updated': datetime.now().isoformat()
            }
            
            settings_path = os.path.join(self.base_dir, 'config', 'user_settings.txt')
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            self.log("✅ 설정이 저장되었습니다.")
            self.update_status("설정 저장 완료", ft.Colors.GREEN)
            
        except Exception as ex:
            self.log(f"❌ 설정 저장 실패: {ex}")
            self.update_status("설정 저장 실패", ft.Colors.RED)
    
    def load_settings(self):
        """설정 로드"""
        try:
            settings_path = os.path.join(self.base_dir, 'config', 'user_settings.txt')
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                self.naver_id_field.value = settings.get('naver_id', '')
                self.naver_pw_field.value = settings.get('naver_pw', '')
                self.blog_url_field.value = settings.get('blog_url', '')
                self.slogan_field.value = settings.get('slogan', '바른 인성을 가진 인재를 기르는 한국체대 라이온 태권도 합기도')
                
                # UI 업데이트
                self.naver_id_field.update()
                self.naver_pw_field.update()
                self.blog_url_field.update()
                self.slogan_field.update()
                
                self.log("✅ 설정을 불러왔습니다.")
            
        except Exception as ex:
            self.log(f"⚠️ 설정 로드 실패: {ex}")
    
    def test_login(self, e):
        """로그인 테스트"""
        def run_test():
            try:
                self.update_status("로그인 테스트 중...", ft.Colors.ORANGE)
                self.log("🔐 로그인 테스트 시작...")
                
                # 설정 먼저 저장
                self.save_settings(None)
                
                # 로그인 테스트
                blog_auto = ImprovedNaverBlogAuto(self.base_dir)
                
                if blog_auto.login_naver():
                    self.log("✅ 로그인 테스트 성공!")
                    self.update_status("로그인 테스트 성공", ft.Colors.GREEN)
                else:
                    self.log("❌ 로그인 테스트 실패")
                    self.update_status("로그인 테스트 실패", ft.Colors.RED)
                
                blog_auto.close()
                
            except Exception as ex:
                self.log(f"❌ 로그인 테스트 중 오류: {ex}")
                self.update_status("로그인 테스트 오류", ft.Colors.RED)
        
        # 별도 스레드에서 실행
        threading.Thread(target=run_test, daemon=True).start()
    
    def auto_write_and_publish(self, e):
        """자동 글쓰기 및 발행"""
        def run_automation():
            try:
                self.is_running = True
                self.auto_write_btn.disabled = True
                self.stop_btn.disabled = False
                self.auto_write_btn.update()
                self.stop_btn.update()
                
                self.update_status("자동화 진행 중...", ft.Colors.ORANGE)
                self.log("🚀 블로그 자동화 시작!")
                
                # 설정 저장
                self.save_settings(None)
                
                # 블로그 자동화 객체 생성
                self.blog_auto = ImprovedNaverBlogAuto(self.base_dir)
                
                # 1단계: 로그인
                self.log("1️⃣ 네이버 로그인 중...")
                if not self.blog_auto.login_naver():
                    raise Exception("로그인 실패")
                
                if not self.is_running:
                    return
                
                # 2단계: 글쓰기 페이지 이동
                self.log("2️⃣ 글쓰기 페이지로 이동 중...")
                if not self.blog_auto.go_to_blog_write():
                    raise Exception("글쓰기 페이지 이동 실패")
                
                if not self.is_running:
                    return
                
                # 3단계: 글 작성 및 발행
                self.log("3️⃣ 글 작성 및 발행 중...")
                title = self.title_field.value
                content = self.content_field.value
                tags = [tag.strip() for tag in self.tags_field.value.split(',') if tag.strip()]
                
                if not self.blog_auto.write_post(title, content, tags):
                    raise Exception("글 작성 및 발행 실패")
                
                # 완료
                self.log("🎉 블로그 자동화 완료!")
                self.update_status("자동화 완료!", ft.Colors.GREEN)
                
            except Exception as ex:
                self.log(f"❌ 자동화 실패: {ex}")
                self.update_status("자동화 실패", ft.Colors.RED)
            
            finally:
                self.is_running = False
                self.auto_write_btn.disabled = False
                self.stop_btn.disabled = True
                self.auto_write_btn.update()
                self.stop_btn.update()
                
                if self.blog_auto:
                    self.blog_auto.close()
                    self.blog_auto = None
        
        # 별도 스레드에서 실행
        threading.Thread(target=run_automation, daemon=True).start()
    
    def stop_automation(self, e):
        """자동화 중지"""
        self.is_running = False
        self.log("⏹️ 자동화 중지 요청")
        self.update_status("자동화 중지됨", ft.Colors.ORANGE)
        
        if self.blog_auto:
            self.blog_auto.close()
            self.blog_auto = None

def main(page: ft.Page):
    app = ImprovedBlogWriterApp()
    app.main(page)

if __name__ == "__main__":
    ft.app(target=main)