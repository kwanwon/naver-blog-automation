@echo off
chcp 65001 > nul
title 블로그 자동화 도구

echo =======================================================
echo 🌍 크로스 플랫폼 블로그 자동화 도구 - Windows 버전
echo =======================================================
echo.

:: 현재 디렉토리로 이동
cd /d "%~dp0"

:: Python 버전 확인
echo 🐍 Python 환경 확인 중...
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python이 설치되지 않았거나 PATH에 없습니다.
    echo    https://www.python.org/downloads/ 에서 Python을 설치하세요.
    pause
    exit /b 1
)

python --version
echo.

:: 가상환경 확인 및 활성화
if exist "venv\Scripts\activate.bat" (
    echo 🏠 가상환경 활성화 중...
    call venv\Scripts\activate.bat
    echo ✅ 가상환경 활성화 완료
) else (
    echo ⚠️ 가상환경이 없습니다. 설정 스크립트를 먼저 실행하세요.
    echo    python setup_cross_platform.py
    pause
    exit /b 1
)

echo.

:: ChromeDriver 확인
if exist "chromedriver.exe" (
    echo 🚗 ChromeDriver 발견: chromedriver.exe
) else if exist "chromedriver" (
    echo 🚗 ChromeDriver 발견: chromedriver
) else (
    echo ℹ️ ChromeDriver가 없습니다. WebDriverManager가 자동 다운로드할 예정입니다.
)

echo.

:: 애플리케이션 실행
echo 🚀 블로그 자동화 도구 시작 중...
echo.
python blog_writer_app.py

:: 오류 발생 시 대기
if errorlevel 1 (
    echo.
    echo ❌ 애플리케이션 실행 중 오류가 발생했습니다.
    echo    자세한 오류 내용은 위의 메시지를 확인하세요.
    pause
)

echo.
echo 애플리케이션이 종료되었습니다.
pause 