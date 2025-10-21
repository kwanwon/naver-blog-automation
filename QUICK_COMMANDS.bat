@echo off
echo ====================================
echo 블로그자동화 - 빠른 명령어 모음
echo ====================================

echo.
echo 📁 현재 위치: %CD%
echo.

:menu
echo ====================================
echo 실행할 작업을 선택하세요:
echo ====================================
echo 1. 환경 설정 (처음 실행 시)
echo 2. 프로그램 실행
echo 3. 개발자용 빌드
echo 4. 배포용 빌드
echo 5. MCP 설정
echo 6. 가상환경 활성화
echo 7. 도움말 보기
echo 8. 종료
echo ====================================

set /p choice="번호를 입력하세요 (1-8): "

if "%choice%"=="1" goto setup
if "%choice%"=="2" goto run
if "%choice%"=="3" goto build_dev
if "%choice%"=="4" goto build_dist
if "%choice%"=="5" goto mcp
if "%choice%"=="6" goto activate
if "%choice%"=="7" goto help
if "%choice%"=="8" goto exit
goto menu

:setup
echo.
echo 🔧 환경 설정을 시작합니다...
echo.
if not exist venv (
    echo 가상환경 생성 중...
    python -m venv venv
    echo ✅ 가상환경 생성 완료
) else (
    echo ✅ 가상환경이 이미 존재합니다
)

call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
echo ✅ 의존성 설치 완료

if exist modules\.developer_mode (
    echo ✅ 개발자 모드 활성화됨
) else (
    echo ⚠️ 개발자 모드 파일이 없습니다
)

echo.
echo 🎉 환경 설정이 완료되었습니다!
echo.
pause
goto menu

:run
echo.
echo 🚀 프로그램을 실행합니다...
echo.
call venv\Scripts\activate
python blog_writer_app.py
echo.
echo 프로그램이 종료되었습니다.
pause
goto menu

:build_dev
echo.
echo 🔨 개발자용 빌드를 시작합니다...
echo.
call venv\Scripts\activate
.\build_developer_windows.bat
echo.
echo 개발자용 빌드가 완료되었습니다!
echo 결과: dist\블로그자동화-개발자\
pause
goto menu

:build_dist
echo.
echo 📦 배포용 빌드를 시작합니다...
echo.
if not exist config\gpt_settings_distribution.txt (
    echo ⚠️ 배포용 설정 파일이 없습니다.
    echo config\gpt_settings_distribution_template.txt를 복사하고
    echo API 키를 입력한 후 다시 시도하세요.
    pause
    goto menu
)

call venv\Scripts\activate
.\build_distribution_windows.bat
echo.
echo 배포용 빌드가 완료되었습니다!
echo 결과: dist\블로그자동화\
pause
goto menu

:mcp
echo.
echo 🔧 MCP 설정을 시작합니다...
echo.
powershell -ExecutionPolicy Bypass -File "mcp-setup\install-mcp-windows.ps1"
echo.
echo MCP 설정이 완료되었습니다!
echo Cursor를 재시작하세요.
pause
goto menu

:activate
echo.
echo 🐍 가상환경을 활성화합니다...
echo.
call venv\Scripts\activate
echo ✅ 가상환경이 활성화되었습니다.
echo.
echo 사용 가능한 명령어:
echo - python blog_writer_app.py (프로그램 실행)
echo - pip install 패키지명 (패키지 설치)
echo - pip list (설치된 패키지 목록)
echo.
pause
goto menu

:help
echo.
echo 📖 도움말
echo ====================================
echo.
echo 📁 주요 파일들:
echo - README_WINDOWS.md: 간단한 시작 가이드
echo - CURSOR_WINDOWS_SETUP.md: Cursor 설정 가이드
echo - WINDOWS_SETUP_GUIDE.md: 전체 매뉴얼
echo - EXECUTION_GUIDE.md: 실행 가이드
echo.
echo 🚀 빠른 시작:
echo 1. 이 메뉴에서 "1. 환경 설정" 선택
echo 2. Cursor 실행 후 프로젝트 폴더 열기
echo 3. "5. MCP 설정" 선택
echo 4. Cursor 재시작
echo 5. "2. 프로그램 실행" 선택
echo.
echo 🔧 문제 해결:
echo - Python 오류: "1. 환경 설정" 다시 실행
echo - MCP 연결 실패: "5. MCP 설정" 다시 실행
echo - 빌드 실패: build, dist 폴더 삭제 후 재시도
echo.
pause
goto menu

:exit
echo.
echo 👋 프로그램을 종료합니다.
echo.
exit

:error
echo.
echo ❌ 잘못된 선택입니다. 다시 시도하세요.
echo.
pause
goto menu
