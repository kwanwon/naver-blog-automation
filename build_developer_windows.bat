@echo off
echo ====================================
echo 개발자용 Windows 빌드 시작
echo ====================================

REM 가상환경 활성화
call venv\Scripts\activate

REM 이전 빌드 정리
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM PyInstaller 빌드
echo.
echo [1/3] PyInstaller 빌드 중...
pyinstaller --clean --noconfirm ^
  --onedir ^
  --windowed ^
  --name="블로그자동화-개발자" ^
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

echo.
echo [2/3] .developer_mode 파일 복사...
copy modules\.developer_mode dist\블로그자동화-개발자\modules\

echo.
echo [3/3] 빌드 완료!
echo 실행 파일 위치: dist\블로그자동화-개발자\블로그자동화-개발자.exe
echo.
pause
