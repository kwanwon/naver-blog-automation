@echo off
echo ====================================
echo 배포용 Windows 빌드 시작
echo ====================================

REM 가상환경 활성화
call venv\Scripts\activate

REM 설정 파일 백업 및 교체
echo [준비] 배포용 설정 적용 중...
if exist config\gpt_settings.txt (
    copy config\gpt_settings.txt config\gpt_settings_backup.txt
)
copy config\gpt_settings_distribution.txt config\gpt_settings.txt

REM 이미지 폴더를 빈 폴더로 교체
echo [준비] 이미지 폴더 백업 및 빈 폴더 생성...
mkdir default_images_backup 2>nul
for /L %%i in (1,1,10) do (
    if exist default_images_%%i (
        move default_images_%%i default_images_backup\
    )
    mkdir default_images_%%i
)
if exist default_images move default_images default_images_backup\
mkdir default_images

REM 이전 빌드 정리
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM PyInstaller 빌드
echo.
echo [1/4] PyInstaller 빌드 중...
pyinstaller --clean --noconfirm ^
  --onedir ^
  --windowed ^
  --name="블로그자동화" ^
  --add-data "config;config" ^
  --add-data "modules;modules" ^
  --add-data "default_images;default_images" ^
  --add-data "default_images_1;default_images_1" ^
  --add-data "default_images_2;default_images_2" ^
  --add-data "default_images_3;default_images_3" ^
  --add-data "default_images_4;default_images_4" ^
  --add-data "default_images_5;default_images_5" ^
  --add-data "default_images_6;default_images_6" ^
  --add-data "default_images_7;default_images_7" ^
  --add-data "default_images_8;default_images_8" ^
  --add-data "default_images_9;default_images_9" ^
  --add-data "default_images_10;default_images_10" ^
  --add-data "requirements.txt;." ^
  --add-data "version.json;." ^
  --hidden-import=openai ^
  --hidden-import=openai._client ^
  --hidden-import=openai.resources ^
  --hidden-import=openai.resources.chat ^
  --hidden-import=openai.resources.chat.completions ^
  --hidden-import=flet ^
  --hidden-import=selenium ^
  --hidden-import=PIL ^
  --collect-all=openai ^
  --collect-all=flet ^
  blog_writer_app.py

REM 설정 파일 복원
echo.
echo [2/4] 개발자 설정 파일 복원...
if exist config\gpt_settings_backup.txt (
    move /y config\gpt_settings_backup.txt config\gpt_settings.txt
)

REM 이미지 폴더 복원
echo [3/4] 이미지 폴더 복원...
if exist default_images_backup (
    rmdir /s /q default_images
    for /L %%i in (1,1,10) do (
        rmdir /s /q default_images_%%i
    )
    move default_images_backup\* .
    rmdir default_images_backup
)

echo.
echo [4/4] 배포 정보 파일 생성...
(
echo 블로그 자동화 프로그램 - Windows 배포판
echo ==========================================
echo.
echo 버전: 1.5.0
echo 빌드 날짜: %date% %time%
echo 플랫폼: Windows x64
echo.
echo 시작하기:
echo 1. '블로그자동화.exe' 파일을 실행하세요
echo 2. 시리얼 번호를 입력하여 인증받으세요
echo 3. GPT 설정에서 원하는 글쓰기 스타일과 지침을 설정하세요
echo 4. default_images 폴더에 원하는 이미지를 추가하세요
echo 5. 네이버 블로그 자동화를 시작하세요!
echo.
echo 폴더 구조:
echo - default_images/: 블로그 포스팅에 사용할 이미지를 넣으세요
echo - default_images_1 ~ 10/: 추가 이미지 폴더 (선택사항^)
echo - config/: 설정 파일이 자동으로 저장됩니다
echo.
echo 사용자 설정:
echo - GPT 설정(지침, 스타일^)은 프로그램 내에서 커스터마이징 가능
echo - 모든 설정은 자동으로 사용자 디바이스에 저장됩니다
echo - API 키는 마스킹되어 표시됩니다 (보안)
echo.
echo 문제 해결:
echo - Windows Defender 경고: '자세한 정보' ^> '실행' 클릭
echo - 실행되지 않을 경우: 관리자 권한으로 실행
echo - 시리얼 인증 문제: 개발자에게 문의하세요
) > dist\블로그자동화\배포_정보.txt

echo.
echo ====================================
echo 빌드 완료!
echo 실행 파일 위치: dist\블로그자동화\블로그자동화.exe
echo ====================================
pause
