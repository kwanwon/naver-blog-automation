import flet as ft
import os
import json
import time
from datetime import datetime, timedelta
import re

class BlogTab:
    def __init__(self, app):
        self.app = app
        self.page = app.page
        self._init_controls()

    def _init_controls(self):
        # 1. State/UI Controls that were previously local in blog_writer_app.py
        self.status_text = ft.Text(
            value="",
            color=ft.Colors.GREY_700,
            size=12,
            italic=True
        )

        self.topic_input = ft.TextField(
            label="🥋 오늘의 블로그 주제 (또는 키워드)",
            hint_text="글의 주제를 입력하거나 아래 '전송' 버튼을 누르세용...",
            multiline=True,
            min_lines=2,
            max_lines=3,
            expand=True
        )

        self.chat_messages = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=10
        )

        self.title_input = ft.TextField(
            label="🥋 오늘의 블로그 제목",
            hint_text="블로그 포스트 제목을 입력하세요...",
            multiline=True,
            min_lines=2,
            max_lines=3,
            expand=False,
            border_radius=10,
            border_color=ft.Colors.BLUE_400,
            focused_border_color=ft.Colors.BLUE_700,
            prefix_icon=ft.Icons.AUTO_AWESOME,
            on_change=self.on_title_changed
        )

        self.content_input = ft.TextField(
            label="📝 오늘의 블로그 본문 (미리보기)",
            hint_text="블로그 포스트 내용을 입력하세요...",
            multiline=True,
            min_lines=6,
            max_lines=15,
            expand=False,
            border_radius=15,
            border_color=ft.Colors.GREY_400,
            focused_border_color=ft.Colors.BLUE_700,
            bgcolor=ft.Colors.GREY_50,
            on_change=self.app.on_content_change
        )

        # Labels/Status
        self.current_model_text = ft.Text(
            value="현재 모델: -",
            size=12,
            color=ft.Colors.BLUE_800
        )
        self.model_spinner = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)

        # Usage Stats UI
        self.daily_usage_text = ft.Text("오늘 사용: -", size=12, color=ft.Colors.GREY_700)
        self.total_usage_text = ft.Text("총 사용: -", size=12, color=ft.Colors.GREY_700)
        self.next_post_time_text = ft.Text("", size=11, color=ft.Colors.BLUE_GREY_400, italic=True)

        # Buttons
        self.send_button = ft.ElevatedButton(
            text="GPT 글 생성 (전송)",
            icon=ft.Icons.SEND,
            on_click=self.send_message,
            bgcolor=ft.Colors.BLUE_600,
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            expand=True
        )

        self.upload_button = ft.ElevatedButton(
            text="naver 블로그에 업로드 하기 (포스팅)",
            icon=ft.Icons.UPLOAD,
            on_click=self.upload_to_blog,
            bgcolor=ft.Colors.GREEN_600,
            color=ft.Colors.WHITE,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.padding.all(10)
            )
        )

    def on_title_changed(self, e):
        self.app.auto_save() # Reusing app logic or moving it here

    def send_message(self, e):
        # Implementation moved from blog_writer_app.py
        # Needs to refer to self.app.gpt_handler, etc.
        pass

    def upload_to_blog(self, e=None, is_retry: bool = False):
        # Implementation moved from blog_writer_app.py
        pass

    def get_content(self):
        # Assemble left and right panels
        left_panel = ft.Column(
            controls=[
                self.topic_input,
                ft.Row(
                    controls=[
                        self.send_button,
                        self.app.auto_topic_checkbox, # Shared state
                        self.app.auto_topic_status
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("📊 사용 현황", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_700),
                        self.daily_usage_text,
                        self.total_usage_text,
                        self.next_post_time_text,
                        ft.Row([self.model_spinner, self.current_model_text], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=10,
                    margin=ft.margin.only(top=10, bottom=10),
                    bgcolor=ft.Colors.PURPLE_50,
                    border_radius=8,
                    border=ft.border.all(1, ft.Colors.PURPLE_200)
                ),
                self.chat_messages
            ],
            spacing=10,
            expand=True
        )

        right_panel = ft.Column(
            controls=[
                self.title_input,
                self.content_input,
                # ... existing right panel content ...
            ],
            spacing=15,
            expand=True
        )

        return ft.Column(
            scroll=ft.ScrollMode.AUTO,
            controls=[
                self.app.login_button,
                ft.Row(
                    controls=[
                        ft.Container(content=left_panel, padding=10, border=ft.border.all(1, ft.Colors.GREY_400), border_radius=10, expand=True),
                        ft.Container(content=right_panel, padding=10, border=ft.border.all(1, ft.Colors.GREY_400), border_radius=10, expand=True)
                    ],
                    spacing=20, expand=True
                )
            ],
            spacing=10, expand=True
        )
