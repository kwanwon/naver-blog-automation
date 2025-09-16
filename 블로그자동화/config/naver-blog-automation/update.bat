@echo off
chcp 65001 > nul
title 블로그 자동화 프로그램 업데이트

echo 🔄 블로그 자동화 프로그램 업데이트
echo ==================================

cd /d "%~dp0"

REM Python 실행
python update.py 2>nul
if %errorlevel% neq 0 (
    python3 update.py 2>nul
    if %errorlevel% neq 0 (
        echo ❌ Python이 설치되지 않았습니다.
        echo Python 3.7 이상을 설치해주세요.
    )
)

echo.
echo 업데이트 스크립트 실행 완료
pause
