@echo off
echo ====================================
echo Windows 환경 빠른 시작 가이드
echo ====================================

echo.
echo [1/5] 현재 디렉토리 확인...
cd /d "%~dp0"
echo 현재 위치: %CD%

echo.
echo [2/5] Python 환경 확인...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되지 않았습니다.
    echo    Python 3.11+ 설치 후 다시 실행하세요.
    pause
    exit /b 1
)

echo.
echo [3/5] 가상환경 설정...
if not exist venv (
    echo 가상환경 생성 중...
    python -m venv venv
    echo ✅ 가상환경 생성 완료
) else (
    echo ✅ 가상환경이 이미 존재합니다
)

echo.
echo [4/5] 의존성 설치...
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
echo ✅ 의존성 설치 완료

echo.
echo [5/5] 개발자 모드 확인...
if exist modules\.developer_mode (
    echo ✅ 개발자 모드 활성화됨 (시리얼 인증 건너뜀)
) else (
    echo ⚠️ 개발자 모드 파일이 없습니다
    echo    시리얼 인증이 필요할 수 있습니다
)

echo.
echo ====================================
echo 🎉 환경 설정 완료!
echo ====================================
echo.
echo 다음 단계:
echo 1. Cursor 실행
echo 2. File > Open Folder > 이 폴더 선택
echo 3. MCP 설정: .\mcp-setup\install-mcp-windows.ps1
echo 4. Cursor 재시작
echo 5. 프로그램 테스트: python blog_writer_app.py
echo.
echo 📖 상세 가이드: CURSOR_WINDOWS_SETUP.md
echo.
pause
