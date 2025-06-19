#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
개선된 블로그 작성 앱
- 완벽한 자동화 워크플로우
- 안정적인 로그인 및 발행
- 사용자 친화적 UI
"""

import flet as ft
import os
import sys
import json
import threading
import time
from datetime import datetime
from naver_blog_auto_improved import ImprovedNaverBlogAuto
from modules.gpt_handler import GPTHandler

class ImprovedBlogWriterApp:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.blog_auto = None
        self.gpt_handler = None
        self.is_running = False
        
    def main(self, page: ft.Page):
        page.title = "한국체대라이온합기도 블로그 자동화 시스템"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 1000
        page.window_height = 800
        page.window_resizable = True
        
        # UI 컴포넌트들
        self.status_text = ft.Text("시스템 준비 완료", size=16, color=ft.Colors.GREEN)
        self.log_text = ft.Text("", size=12, selectable=True)
        
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
        
        # 탭 생성
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="블로그 작성",
                    icon=ft.Icons.EDIT_NOTE,
                    content=self.create_blog_tab()
                ),
                ft.Tab(
                    text="시간 설정",
                    icon=ft.Icons.TIMER,
                    content=self.create_timer_tab()
                ),
                ft.Tab(
                    text="GPT 설정",
                    icon=ft.Icons.SETTINGS_APPLICATIONS,
                    content=self.create_gpt_tab()
                ),
                ft.Tab(
                    text="사용자 설정",
                    icon=ft.Icons.PERSON,
                    content=self.create_user_tab()
                )
            ],
            expand=True
        )
        
        # 페이지에 헤더와 탭 추가
        page.add(
            ft.Column([
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
                tabs
            ], expand=True)
        )
        
        # 초기 설정 로드
        self.load_settings()
    
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
    
    def create_blog_tab(self):
        """블로그 작성 탭 생성"""
        return ft.Container(
            content=ft.Column([
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
            padding=20
        )
    
    def create_timer_tab(self):
        """시간 설정 탭 생성"""
        return ft.Container(
            content=ft.Column([
                # 시간 설정 설명
                ft.Container(
                    content=ft.Column([
                        ft.Text("⏰ 자동 시간 설정", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                        ft.Text("설정된 시간에 자동으로 블로그 포스팅을 진행합니다.", size=14, color=ft.Colors.GREY_700),
                        ft.Text("⚠️ 아직 개발 중인 기능입니다. 곧 업데이트 예정입니다.", 
                               size=12, color=ft.Colors.ORANGE_600, weight=ft.FontWeight.BOLD)
                    ]),
                    padding=20,
                    border=ft.border.all(2, ft.Colors.BLUE_300),
                    border_radius=10,
                    margin=10,
                    bgcolor=ft.Colors.BLUE_50
                ),
                
                # 시간 설정 플레이스홀더
                ft.Container(
                    content=ft.Column([
                        ft.Text("🚧 개발 중", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text("시간 설정 기능이 곧 추가될 예정입니다.", size=14, color=ft.Colors.GREY_600),
                        ft.Text("• 특정 시간 설정", size=12, color=ft.Colors.GREY_500),
                        ft.Text("• 랜덤 간격 설정", size=12, color=ft.Colors.GREY_500),
                        ft.Text("• 일일 포스팅 제한", size=12, color=ft.Colors.GREY_500),
                    ]),
                    padding=20,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                    margin=10
                )
            ], scroll=ft.ScrollMode.AUTO),
            padding=20
        )
    
    def create_gpt_tab(self):
        """GPT 설정 탭 생성"""
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Text("🤖 GPT 설정", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_900),
                        ft.Text("GPT 관련 설정을 여기서 관리할 수 있습니다.", size=14, color=ft.Colors.GREY_700),
                        ft.Text("⚠️ 아직 개발 중인 기능입니다. 곧 업데이트 예정입니다.", 
                               size=12, color=ft.Colors.ORANGE_600, weight=ft.FontWeight.BOLD)
                    ]),
                    padding=20,
                    border=ft.border.all(2, ft.Colors.GREEN_300),
                    border_radius=10,
                    margin=10,
                    bgcolor=ft.Colors.GREEN_50
                )
            ], scroll=ft.ScrollMode.AUTO),
            padding=20
        )
    
    def create_user_tab(self):
        """사용자 설정 탭 생성"""
        return ft.Container(
            content=ft.Column([
                # 사용자 설정 섹션
                ft.Container(
                    content=ft.Column([
                        ft.Text("사용자 설정", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_700),
                        ft.Text("블로그 글 마지막에 표시될 슬로건을 설정하세요", size=14, color=ft.Colors.GREY_600),
                        self.slogan_field,
                        ft.Text("💡 예시: '이상 바른 인성을 가진 인재를 기르는 한국체대 라이온 태권도 합기도 이었습니다'", 
                               size=12, color=ft.Colors.GREY_500, italic=True),
                        ft.Row([
                            ft.ElevatedButton(
                                "사용자 설정 저장",
                                on_click=self.save_settings,
                                bgcolor=ft.Colors.PURPLE,
                                color=ft.Colors.WHITE
                            )
                        ])
                    ]),
                    padding=20,
                    border=ft.border.all(1, ft.Colors.PURPLE_200),
                    border_radius=10,
                    margin=10,
                    bgcolor=ft.Colors.PURPLE_50
                )
            ], scroll=ft.ScrollMode.AUTO),
            padding=20
        )

def main(page: ft.Page):
    app = ImprovedBlogWriterApp()
    app.main(page)

if __name__ == "__main__":
    ft.app(target=main)