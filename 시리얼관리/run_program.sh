#!/bin/bash

# 시리얼관리 프로그램 실행 스크립트
# 사용법: ./run_program.sh 또는 bash run_program.sh

echo "🚀 시리얼관리 프로그램을 시작합니다..."

# 현재 디렉토리로 이동
cd "$(dirname "$0")"

# 가상환경 활성화
if [ -d "venv" ]; then
    echo "📦 가상환경을 활성화합니다..."
    source venv/bin/activate
    
    # 필요한 패키지가 설치되어 있는지 확인
    python3 -c "import pandas, requests, tkcalendar, psutil" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ 모든 필수 패키지가 설치되어 있습니다."
        echo "🎯 프로그램을 실행합니다..."
        python3 serial_validator.py
    else
        echo "❌ 필수 패키지가 누락되었습니다."
        echo "📥 패키지를 설치합니다..."
        pip install requests pandas tkcalendar psutil
        echo "🎯 프로그램을 실행합니다..."
        python3 serial_validator.py
    fi
else
    echo "❌ 가상환경이 없습니다."
    echo "🔧 가상환경을 생성합니다..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📥 필수 패키지를 설치합니다..."
    pip install requests pandas tkcalendar psutil
    echo "🎯 프로그램을 실행합니다..."
    python3 serial_validator.py
fi
