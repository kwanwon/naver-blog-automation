#!/bin/bash
# 시리얼관리 프로그램 실행 스크립트

echo "🚀 시리얼관리 프로그램을 시작합니다..."

# 현재 스크립트 위치로 이동
cd "$(dirname "$0")"

# 가상환경 존재 여부 확인
if [ ! -d "venv" ]; then
    echo "❌ 가상환경이 없습니다. 가상환경을 생성합니다..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📦 필요한 패키지를 설치합니다..."
    pip install requests psutil pandas tkcalendar openpyxl
else
    # 가상환경 활성화
    echo "📦 가상환경 활성화 중..."
    source venv/bin/activate
fi

# 프로그램 실행 (start_program.py 또는 직접 serial_validator.py)
echo "🎯 프로그램 실행 중..."
if [ -f "start_program.py" ]; then
    python3 start_program.py
else
    python3 serial_validator.py
fi

# 가상환경 비활성화
deactivate

echo "✅ 프로그램이 종료되었습니다."
