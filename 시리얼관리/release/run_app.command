#!/bin/bash

# 스크립트의 디렉토리 경로 가져오기
APP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$(dirname "$APP_DIR")"

echo "앱 시작 중... 경로: $PARENT_DIR"
echo "시간: $(date)"

# 실행 권한 확인 및 부여
if [ ! -x "$PARENT_DIR/시리얼관리.app/Contents/MacOS/시리얼관리" ]; then
    echo "실행 권한 부여 중..."
    chmod +x "$PARENT_DIR/시리얼관리.app/Contents/MacOS/시리얼관리"
fi

# 앱 실행
open -a "$PARENT_DIR/시리얼관리.app"

echo "앱이 성공적으로 실행되었습니다."
exit 0 