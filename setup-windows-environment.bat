@echo off
echo ====================================
echo Windows 환경 자동 설정 시작
echo ====================================

REM 현재 디렉토리를 프로젝트 루트로 설정
cd /d "%~dp0"

echo.
echo [1/4] Python 가상환경 생성 중...
if not exist venv (
    python -m venv venv
    echo ✅ 가상환경 생성 완료
) else (
    echo ✅ 가상환경이 이미 존재합니다
)

echo.
echo [2/4] 가상환경 활성화 및 의존성 설치 중...
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
echo ✅ 의존성 설치 완료

echo.
echo [3/4] 개발자 모드 확인 중...
if exist modules\.developer_mode (
    echo ✅ 개발자 모드 파일이 존재합니다
) else (
    echo ⚠️ 개발자 모드 파일이 없습니다. 시리얼 인증이 필요할 수 있습니다.
)

echo.
echo [4/4] Cursor MCP 설정 중...
if exist mcp-setup\install-mcp-windows.ps1 (
    echo MCP 자동 설정을 실행합니다...
    powershell -ExecutionPolicy Bypass -File "mcp-setup\install-mcp-windows.ps1"
    echo ✅ MCP 설정 완료
) else (
    echo ⚠️ MCP 설정 스크립트를 찾을 수 없습니다
)

echo.
echo ====================================
echo 설정 완료!
echo ====================================
echo.
echo 다음 단계:
echo 1. Cursor를 실행하고 이 폴더를 열어주세요
echo 2. 가상환경이 활성화된 상태에서 python blog_writer_app.py 실행
echo 3. 정상 작동 확인 후 빌드 진행
echo.
echo 개발자용 빌드: .\build_developer_windows.bat
echo 배포용 빌드: .\build_distribution_windows.bat
echo.
pause
