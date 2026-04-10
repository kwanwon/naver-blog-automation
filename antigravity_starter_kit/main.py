import flet as ft
import os
import json
from utils.path_utils import get_config_dir, get_app_settings_path
from utils.security_utils import obfuscate, deobfuscate, deobfuscate_dict_fields

class SecureApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Antigravity Secure App"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        
        # 1. 초기 경로 설정 (보안 룰 적용)
        self.config_dir = get_config_dir()
        self.settings_path = get_app_settings_path()
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 2. 설정 로드 (복호화 포함)
        self.settings = self.load_settings()
        
        self.build_ui()

    def load_settings(self):
        if os.path.exists(self.settings_path):
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 🔐 민감 데이터 자동으로 복호화
                return deobfuscate_dict_fields(data)
        return {"api_key": "", "user_name": "Guest"}

    def save_settings(self, new_settings):
        # 🔐 민감 데이터 저장 시 자동 암호화 (필요 시 특정 필드만 obfuscate 호출)
        # 예: new_settings['api_key'] = obfuscate(new_settings['api_key'])
        with open(self.settings_path, 'w', encoding='utf-8') as f:
            json.dump(new_settings, f, ensure_ascii=False, indent=2)

    def build_ui(self):
        self.page.add(
            ft.AppBar(title=ft.Text("🛡️ Antigravity Secure Starter"), bgcolor=ft.Colors.SURFACE_VARIANT),
            ft.Container(
                content=ft.Column([
                    ft.Text("안티그래비티 보안 규칙(ASR)이 적용된 프로젝트입니다.", size=16),
                    ft.Divider(),
                    ft.Text(f"설정 경로: {self.settings_path}", size=12, color=ft.Colors.GREY_600),
                    ft.ElevatedButton("설정 저장 테스트", on_click=lambda _: print("Saved!"))
                ]),
                padding=20
            )
        )

def main(page: ft.Page):
    SecureApp(page)

if __name__ == "__main__":
    ft.app(target=main)
