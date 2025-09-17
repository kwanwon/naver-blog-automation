#!/bin/bash
# 블로그 자동화 프로그램 업데이트 스크립트 (macOS/Linux)

echo "🔄 블로그 자동화 프로그램 업데이트"
echo "=================================="

# 현재 스크립트 위치로 이동
cd "$(dirname "$0")"

# Python 실행
if command -v python3 &> /dev/null; then
    python3 update.py
elif command -v python &> /dev/null; then
    python update.py
else
    echo "❌ Python이 설치되지 않았습니다."
    echo "Python 3.7 이상을 설치해주세요."
fi

echo ""
echo "업데이트 스크립트 실행 완료"
read -p "계속하려면 Enter 키를 누르세요..."
