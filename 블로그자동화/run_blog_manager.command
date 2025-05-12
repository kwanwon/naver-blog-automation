#!/bin/bash

# 현재 스크립트의 디렉토리로 이동
cd "$(dirname "$0")"

# 가상환경이 있으면 활성화
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 필요한 패키지 설치 확인
pip install -q pandas tkcalendar

# 블로그자동화관리 실행
python3 블로그자동화관리.py

# 종료 대기
read -p "프로그램이 종료되었습니다. 아무 키나 누르세요..." -n1 -s 