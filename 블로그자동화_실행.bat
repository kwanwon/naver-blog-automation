@echo off
chcp 65001 >nul
title 블로그 자동화 프로그램

echo.
echo ========================================
echo    🎉 블로그 자동화 프로그램
echo ========================================
echo.

:: 현재 디렉토리로 이동
cd /d "%~dp0"

:: Python 실행 파일 확인
if not exist "blog_writer_app.py" (
    echo ❌ 오류: blog_writer_app.py 파일을 찾을 수 없습니다.
    echo 💡 올바른 폴더에서 실행하고 있는지 확인하세요.
    echo.
    pause
    exit /b 1
)

:: Python 설치 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 오류: Python이 설치되어 있지 않습니다.
    echo 💡 Python 3.8 이상을 설치해주세요: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: 가상환경 확인 및 활성화
if exist "venv\Scripts\activate.bat" (
    echo 🔧 가상환경을 활성화합니다...
    call venv\Scripts\activate.bat
) else if exist "blog_venv\Scripts\activate.bat" (
    echo 🔧 가상환경을 활성화합니다...
    call blog_venv\Scripts\activate.bat
) else (
    echo ⚠️ 가상환경을 찾을 수 없습니다. 시스템 Python을 사용합니다.
)

:: 필요한 패키지 설치 확인
echo 📦 필요한 패키지들을 확인하고 설치합니다...
python -c "import tkinter, selenium, openai, requests" 2>nul
if errorlevel 1 (
    echo 📥 필요한 패키지들을 설치합니다...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ 패키지 설치에 실패했습니다.
        echo 💡 인터넷 연결을 확인하고 다시 시도해주세요.
        echo.
        pause
        exit /b 1
    )
)

:: 프로그램 실행
echo.
echo 🚀 블로그 자동화 프로그램을 시작합니다...
echo.
python blog_writer_app.py

:: 오류 발생 시
if errorlevel 1 (
    echo.
    echo ❌ 프로그램 실행 중 오류가 발생했습니다.
    echo 💡 log.txt 파일을 확인하거나 개발자에게 문의하세요.
    echo.
    pause
)
