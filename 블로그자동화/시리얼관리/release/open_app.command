#!/bin/bash

# 현재 디렉토리 경로
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 앱 경로
APP_PATH="$DIR/dist/시리얼관리.app"

# 앱 존재 확인
if [ -d "$APP_PATH" ]; then
    echo "시리얼관리 앱을 실행합니다..."
    open "$APP_PATH"
else
    echo "오류: $APP_PATH 경로에 앱이 존재하지 않습니다."
    exit 1
fi 