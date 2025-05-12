import os
import sys
import json
import subprocess
import flet as ft
from modules.license_handler import LicenseHandler
from modules.updater import AppUpdater

# 라이선스 핸들러의 URL 수정을 위한 패치
import importlib.util
spec = importlib.util.find_spec('modules.license_handler')
if spec:
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # 라이선스 서버 URL 변경
    module.LicenseHandler.license_server_url = "http://localhost:5000/api/validate"

class ProgramManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.programs_file = os.path.join(self.base_dir, 'config', 'programs.json')
        self.programs = self.load_programs()
        
    def load_programs(self):
        """등록된 프로그램 목록 로드"""
        default_programs = {
            "네이버블로그자동화": {
                "name": "네이버 블로그 자동화",
                "path": os.path.join(self.base_dir, "blog_writer_app.py"),
                "version": "1.0.0",
                "icon": "blog_icon.png",
                "description": "네이버 블로그 글 자동 생성 및 포스팅 도구"
            }
        }
        
        try:
            if os.path.exists(self.programs_file):
                with open(self.programs_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                os.makedirs(os.path.dirname(self.programs_file), exist_ok=True)
                with open(self.programs_file, 'w', encoding='utf-8') as f:
                    json.dump(default_programs, f, ensure_ascii=False, indent=2)
                return default_programs
        except Exception as e:
            print(f"프로그램 목록 로드 중 오류: {str(e)}")
            return default_programs
    
    def save_programs(self):
        """프로그램 목록 저장"""
        try:
            with open(self.programs_file, 'w', encoding='utf-8') as f:
                json.dump(self.programs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"프로그램 목록 저장 중 오류: {str(e)}")
    
    def add_program(self, id, name, path, version="1.0.0", icon=None, description=None):
        """새 프로그램 등록"""
        if id in self.programs:
            return False, "이미 등록된 프로그램 ID입니다."
            
        self.programs[id] = {
            "name": name,
            "path": path,
            "version": version,
            "icon": icon or "default_icon.png",
            "description": description or ""
        }
        
        self.save_programs()
        return True, "프로그램이 등록되었습니다."
    
    def remove_program(self, id):
        """프로그램 제거"""
        if id not in self.programs:
            return False, "등록되지 않은 프로그램입니다."
            
        del self.programs[id]
        self.save_programs()
        return True, "프로그램이 제거되었습니다."
    
    def launch_program(self, id):
        """프로그램 실행"""
        if id not in self.programs:
            return False, "등록되지 않은 프로그램입니다."
            
        program = self.programs[id]
        path = program["path"]
        
        try:
            if path.endswith('.py'):
                # Python 스크립트 실행
                subprocess.Popen([sys.executable, path])
            elif os.path.isfile(path):
                # 실행 파일 직접 실행
                subprocess.Popen([path])
            else:
                return False, "잘못된 프로그램 경로입니다."
                
            return True, "프로그램이 실행되었습니다."
        except Exception as e:
            return False, f"프로그램 실행 중 오류: {str(e)}"
    
    def check_updates(self, id):
        """특정 프로그램의 업데이트 확인"""
        if id not in self.programs:
            return False, "등록되지 않은 프로그램입니다."
            
        program = self.programs[id]
        
        # 프로그램별 업데이트 설정
        if id == "네이버블로그자동화":
            updater = AppUpdater(app_name=program["name"], current_version=program["version"])
            license_handler = LicenseHandler()
            
            update_info = updater.check_for_updates(force=True, license_handler=license_handler)
            if update_info:
                return True, update_info
            else:
                return False, "업데이트가 없거나 확인할 수 없습니다."
        else:
            return False, "이 프로그램은 자동 업데이트를 지원하지 않습니다."

def main(page: ft.Page):
    page.title = "프로그램 관리자"
    page.window_width = 800
    page.window_height = 600
    page.theme_mode = ft.ThemeMode.LIGHT
    
    manager = ProgramManager()
    
    # 프로그램이 없을 경우 테스트용 프로그램 추가
    if not manager.programs:
        manager.add_program(
            "네이버블로그자동화", 
            "네이버 블로그 자동화", 
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "blog_writer_app.py"),
            "1.0.0"
        )
    
    # 라이선스 활성화 UI
    license_title = ft.Text("라이선스 활성화", size=20, weight=ft.FontWeight.BOLD)
    
    license_key_field = ft.TextField(
        label="시리얼 키",
        hint_text="XXXXX-XXXXX-XXXXX-XXXXX-XXXXX 형식으로 입력하세요",
        width=400
    )
    
    status_text = ft.Text(
        value="",
        color=ft.colors.RED_400
    )
    
    def validate_license(e):
        try:
            # 라이선스 검증
            handler = LicenseHandler()
            is_valid, message = handler.validate_license(license_key_field.value)
            
            if is_valid:
                status_text.value = "라이선스가 성공적으로 등록되었습니다!"
                status_text.color = ft.colors.GREEN_400
            else:
                status_text.value = f"오류: {message}"
                status_text.color = ft.colors.RED_400
            
            page.update()
        except Exception as ex:
            status_text.value = f"검증 중 오류 발생: {str(ex)}"
            status_text.color = ft.colors.RED_400
            page.update()
    
    activate_button = ft.ElevatedButton(
        text="라이선스 활성화",
        on_click=validate_license
    )
    
    license_ui = ft.Column([
        license_title,
        license_key_field,
        activate_button,
        status_text
    ], spacing=20, alignment=ft.MainAxisAlignment.CENTER)
    
    # 기존 관리자 UI 기능
    def launch_selected_program(e):
        selected = program_list.selected_index
        if selected is not None and 0 <= selected < len(program_items):
            program_id = list(manager.programs.keys())[selected]
            success, message = manager.launch_program(program_id)
            page.snack_bar = ft.SnackBar(content=ft.Text(message))
            page.snack_bar.open = True
            page.update()
    
    def check_program_update(e):
        selected = program_list.selected_index
        if selected is not None and 0 <= selected < len(program_items):
            program_id = list(manager.programs.keys())[selected]
            success, result = manager.check_updates(program_id)
            
            if success:
                # 업데이트 정보 표시
                update_dialog = ft.AlertDialog(
                    title=ft.Text("업데이트 가능"),
                    content=ft.Column([
                        ft.Text(f"새 버전: {result.get('version')}"),
                        ft.Text(f"현재 버전: {manager.programs[program_id]['version']}"),
                        ft.Text("업데이트 내용:"),
                        ft.Container(
                            content=ft.Text(result.get('release_notes', '릴리스 노트가 없습니다.')),
                            padding=10,
                            border=ft.border.all(1, ft.colors.GREY_400),
                            border_radius=5,
                            width=400,
                            height=150
                        )
                    ]),
                    actions=[
                        ft.TextButton("업데이트", on_click=lambda e: download_update(e, program_id, result)),
                        ft.TextButton("취소", on_click=lambda e: close_dialog(e))
                    ]
                )
                page.dialog = update_dialog
                update_dialog.open = True
            else:
                page.snack_bar = ft.SnackBar(content=ft.Text(result))
                page.snack_bar.open = True
                
            page.update()
    
    def close_dialog(e):
        page.dialog.open = False
        page.update()
    
    def download_update(e, program_id, update_info):
        page.dialog.open = False
        page.update()
        
        # 업데이트 다운로드 로직 (간소화됨)
        page.snack_bar = ft.SnackBar(content=ft.Text("업데이트 다운로드 중..."))
        page.snack_bar.open = True
        page.update()
        
        # 실제로는 updater.download_update와 install_update를 호출
    
    # 프로그램 목록 생성
    program_items = []
    for id, program in manager.programs.items():
        program_items.append(
            ft.ListTile(
                leading=ft.Icon(ft.icons.APPS),
                title=ft.Text(program["name"]),
                subtitle=ft.Text(f"버전: {program['version']}"),
                trailing=ft.Text("실행"),
                on_click=launch_selected_program
            )
        )
    
    program_list = ft.ListView(
        controls=program_items,
        expand=True,
        spacing=10,
        padding=20
    )
    
    program_ui = ft.Column([
        ft.Text("프로그램 관리", size=20, weight=ft.FontWeight.BOLD),
        ft.Container(
            content=program_list,
            expand=True,
            border=ft.border.all(1, ft.colors.GREY_400),
            border_radius=10,
            padding=10
        ),
        ft.Row(
            [
                ft.ElevatedButton("실행", on_click=launch_selected_program),
                ft.ElevatedButton("업데이트 확인", on_click=check_program_update)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20
        )
    ], spacing=20, expand=True)
    
    # 탭 UI 설정
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(
                text="라이선스 관리",
                icon=ft.icons.KEY,
                content=ft.Container(
                    content=license_ui,
                    padding=20,
                    alignment=ft.alignment.center
                )
            ),
            ft.Tab(
                text="프로그램 관리",
                icon=ft.icons.APPS,
                content=ft.Container(
                    content=program_ui,
                    padding=20
                )
            )
        ],
        expand=True
    )
    
    page.add(
        ft.AppBar(
            title=ft.Text("프로그램 관리자"),
            center_title=True,
            bgcolor=ft.colors.SURFACE_VARIANT
        ),
        tabs
    )

if __name__ == "__main__":
    ft.app(target=main) 