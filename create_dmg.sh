#!/bin/bash
# macOS DMG 파일 생성 스크립트

APP_NAME="블로그자동화"
APP_VERSION="1.5.0"
APP_PATH="블로그자동화_v1.5.0_Complete.app"
DMG_NAME="${APP_NAME}_v${APP_VERSION}_macOS.dmg"
DMG_PATH="${DMG_NAME}"

echo "💿 macOS DMG 파일 생성 시작..."

# 앱 번들 존재 확인
if [ ! -d "$APP_PATH" ]; then
    echo "❌ 앱 번들을 찾을 수 없습니다: $APP_PATH"
    exit 1
fi

# 임시 DMG 디렉토리 생성
TEMP_DMG_DIR="temp_dmg"
rm -rf "$TEMP_DMG_DIR"
mkdir "$TEMP_DMG_DIR"

# 앱 번들 복사
echo "📦 앱 번들 복사 중..."
cp -R "$APP_PATH" "$TEMP_DMG_DIR/"

# Applications 폴더 심볼릭 링크 생성
echo "🔗 Applications 폴더 링크 생성 중..."
ln -s /Applications "$TEMP_DMG_DIR/Applications"

# README 파일 생성
echo "📝 README 파일 생성 중..."
cat > "$TEMP_DMG_DIR/README.txt" << EOF
블로그 자동화 프로그램 v${APP_VERSION}

설치 방법:
1. ${APP_NAME}.app을 Applications 폴더로 드래그하세요
2. Applications 폴더에서 앱을 실행하세요

주의사항:
- macOS 10.13 이상이 필요합니다
- 보안 경고가 나오면 시스템 환경설정 > 보안 및 개인정보보호에서 허용하세요

지원: https://github.com/kwanwon/naver-blog-automation
EOF

# DMG 파일 생성
echo "💿 DMG 파일 생성 중..."
hdiutil create -volname "${APP_NAME} ${APP_VERSION}" -srcfolder "$TEMP_DMG_DIR" -ov -format UDZO "$DMG_PATH"

# 임시 디렉토리 정리
rm -rf "$TEMP_DMG_DIR"

# DMG 파일 정보 확인
if [ -f "$DMG_PATH" ]; then
    DMG_SIZE=$(du -h "$DMG_PATH" | cut -f1)
    echo "✅ DMG 파일 생성 완료!"
    echo "📦 파일: $DMG_PATH"
    echo "📊 크기: $DMG_SIZE"
else
    echo "❌ DMG 파일 생성 실패"
    exit 1
fi

echo "🎉 DMG 생성 완료!"
