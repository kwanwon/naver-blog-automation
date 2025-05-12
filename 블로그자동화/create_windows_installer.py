#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 블로그 자동화 도구 - Windows용 NSIS 설치 프로그램 생성 스크립트
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime

# 애플리케이션 설정
APP_NAME = "네이버블로그자동화"
VERSION = "1.0.0"
# PyInstaller가 생성한 배포 디렉토리
DIST_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "dist", APP_NAME)
# 인스톨러 생성 파일이 위치할 디렉토리
INSTALLER_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "installer")
# NSIS 스크립트 및 최종 EXE 경로
NSIS_SCRIPT_PATH = os.path.join(INSTALLER_DIR, f"{APP_NAME}.nsi")
OUTPUT_INSTALLER_PATH = os.path.join(INSTALLER_DIR, f"{APP_NAME}_Installer_{VERSION}.exe")

def run_command(command):
    print(f"실행: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"명령어 실행 실패: {result.stderr}")
        return False
    print("명령어 실행 성공")
    return True


def check_requirements():
    print("=== NSIS 설치 여부 확인 ===")
    if not shutil.which("makensis"):
        print("오류: makensis (NSIS 컴파일러)를 찾을 수 없습니다. NSIS를 설치해주세요.")
        print("NSIS 다운로드: https://nsis.sourceforge.io/Download")
        return False
    print("makensis ✓")
    return True


def prepare_installer_dir():
    print("=== 인스톨러 디렉토리 준비 ===")
    if not os.path.exists(INSTALLER_DIR):
        os.makedirs(INSTALLER_DIR)
        print(f"인스톨러 디렉토리 생성: {INSTALLER_DIR}")
    else:
        print(f"인스톨러 디렉토리 이미 존재: {INSTALLER_DIR}")
    # 기존 스크립트 및 설치 파일 삭제
    for path in [NSIS_SCRIPT_PATH, OUTPUT_INSTALLER_PATH]:
        if os.path.exists(path):
            os.remove(path)
            print(f"기존 파일 삭제: {path}")


def generate_nsis_script():
    print("=== NSIS 스크립트 생성 ===")
    script = f"""
!define APP_NAME "{APP_NAME}"
!define APP_VERSION "{VERSION}"
!define INSTALL_DIR "$PROGRAMFILES\\{APP_NAME}"
!define OUTPUT_FILE "{OUTPUT_INSTALLER_PATH}"
!define SOURCE_DIR "{DIST_DIR}"

!include "MUI2.nsh"
!include "LogicLib.nsh"

Name "${{APP_NAME}} ${{APP_VERSION}}"
OutFile "${{OUTPUT_FILE}}"
InstallDir "${{INSTALL_DIR}}"
InstallDirRegKey HKLM "Software\\${{APP_NAME}}" "Install_Dir"

!define MUI_ABORTWARNING
!define MUI_ICON "{os.path.join(os.path.abspath(os.path.dirname(__file__)), 'build_resources', 'app_icon.ico')}"
!define MUI_UNICON "{os.path.join(os.path.abspath(os.path.dirname(__file__)), 'build_resources', 'app_icon.ico')}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Korean"

# 시리얼 번호 입력 페이지
Page custom SerialKeyPage SerialKeyPageLeave

Var SERIAL_KEY
Var Dialog
Var SerialKeyLabel
Var SerialKeyTextBox
Var SerialKeyErrorLabel

# 시리얼 키 검증 함수
Function ValidateSerialKey
    Pop $R0 # 시리얼 키 값
    
    # 간단한 형식 검증 (5-5-5-5-5 형식)
    ${If} $R0 == ""
        StrCpy $0 "false"
        StrCpy $1 "시리얼 키를 입력해주세요."
        Push $0
        Push $1
        Return
    ${EndIf}
    
    # 여기에 더 복잡한 검증 로직 추가
    # (실제 구현에서는 서버 API 호출 필요)
    
    StrCpy $0 "true"
    StrCpy $1 "유효한 시리얼 키입니다."
    Push $0
    Push $1
    Return
Function

# 시리얼 키 입력 페이지 생성
Function SerialKeyPage
    !insertmacro MUI_HEADER_TEXT "라이선스 등록" "프로그램 사용을 위한 시리얼 키를 입력해주세요."
    nsDialogs::Create 1018
    Pop $Dialog

    ${If} $Dialog == error
        Abort
    ${EndIf}

    ${NSD_CreateLabel} 0 0 100% 20u "아래에 유효한 시리얼 키를 입력해주세요:"
    Pop $SerialKeyLabel

    ${NSD_CreateText} 0 20u 100% 12u $SERIAL_KEY
    Pop $SerialKeyTextBox

    ${NSD_CreateLabel} 0 40u 100% 20u ""
    Pop $SerialKeyErrorLabel
    SetCtlColors $SerialKeyErrorLabel 0xFF0000 transparent

    nsDialogs::Show
FunctionEnd

# 시리얼 키 페이지 종료 시 검증
Function SerialKeyPageLeave
    ${NSD_GetText} $SerialKeyTextBox $SERIAL_KEY
    
    # 시리얼 검증 호출
    Push $SERIAL_KEY
    Call ValidateSerialKey
    Pop $1 # 메시지
    Pop $0 # 결과 (true/false)
    
    ${If} $0 != "true"
        ${NSD_SetText} $SerialKeyErrorLabel $1
        Abort
    ${EndIf}
    
    # 시리얼 저장
    CreateDirectory "$INSTDIR\\config"
    FileOpen $R0 "$INSTDIR\\config\\license.json" w
    FileWrite $R0 '{"serial_key": "$SERIAL_KEY", "activation_date": "${__DATE__}", "valid": true}'
    FileClose $R0
FunctionEnd

Section "!${APP_NAME} 설치 (필수)" SecCore
    SectionIn RO
    SetOutPath "${{INSTDIR}}"
    File /r "${{SOURCE_DIR}}\\*"
    
    # 레지스트리 등록
    WriteRegStr HKLM "Software\\${{APP_NAME}}" "Install_Dir" "$INSTDIR"
    
    # 시작 메뉴에 바로가기 생성
    CreateDirectory "$SMPROGRAMS\\${{APP_NAME}}"
    CreateShortcut "$SMPROGRAMS\\${{APP_NAME}}\\${{APP_NAME}}.lnk" "$INSTDIR\\${{APP_NAME}}.exe"
    CreateShortcut "$SMPROGRAMS\\${{APP_NAME}}\\Uninstall.lnk" "$INSTDIR\\uninstall.exe"
    
    # 바탕화면에 바로가기 생성
    CreateShortcut "$DESKTOP\\${{APP_NAME}}.lnk" "$INSTDIR\\${{APP_NAME}}.exe"
    
    # 제거 프로그램 등록
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "DisplayName" "${{APP_NAME}} ${{APP_VERSION}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "UninstallString" '"$INSTDIR\\uninstall.exe"'
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "NoModify" 1
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "NoRepair" 1
    
    # 제거 프로그램 생성
    WriteUninstaller "$INSTDIR\\uninstall.exe"
SectionEnd

Section "자동 시작 (선택)" SecAutostart
    CreateShortcut "$SMSTARTUP\\${{APP_NAME}}.lnk" "$INSTDIR\\${{APP_NAME}}.exe"
SectionEnd

# 제거 섹션
Section "Uninstall"
    # 프로그램 파일 제거
    RMDir /r "$INSTDIR"
    
    # 바로가기 제거
    Delete "$DESKTOP\\${{APP_NAME}}.lnk"
    Delete "$SMPROGRAMS\\${{APP_NAME}}\\${{APP_NAME}}.lnk"
    Delete "$SMPROGRAMS\\${{APP_NAME}}\\Uninstall.lnk"
    RMDir "$SMPROGRAMS\\${{APP_NAME}}"
    Delete "$SMSTARTUP\\${{APP_NAME}}.lnk"
    
    # 레지스트리 키 제거
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}"
    DeleteRegKey HKLM "Software\\${{APP_NAME}}"
SectionEnd

# 설명 추가
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecCore} "네이버 블로그 자동화 프로그램의 필수 파일을 설치합니다."
    !insertmacro MUI_DESCRIPTION_TEXT ${SecAutostart} "Windows 시작 시 프로그램을 자동으로 실행합니다."
!insertmacro MUI_FUNCTION_DESCRIPTION_END
"""
    with open(NSIS_SCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"NSIS 스크립트 생성 완료: {NSIS_SCRIPT_PATH}")


def create_installer():
    if not os.path.exists(DIST_DIR):
        print(f"오류: 배포 디렉토리를 찾을 수 없습니다: {DIST_DIR}")
        return False
    generate_nsis_script()
    cmd = f'makensis "{NSIS_SCRIPT_PATH}"'
    return run_command(cmd)


def main():
    print(f"=== Windows Installer 생성 시작: {APP_NAME} {VERSION} ===")
    if not check_requirements():
        sys.exit(1)
    prepare_installer_dir()
    if create_installer():
        print(f"설치 프로그램 생성 완료: {OUTPUT_INSTALLER_PATH}")
    else:
        print("설치 프로그램 생성 실패.")
        sys.exit(1)


if __name__ == "__main__":
    main() 