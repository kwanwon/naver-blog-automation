#!/bin/bash

# 현재 디렉토리 경로
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Python 검사
if [ -d "./venv" ]; then
    echo "가상 환경을 활성화합니다..."
    source ./venv/bin/activate
    
    # 기본 환경 변수 설정
    export PYTHONPATH="$DIR"
    
    echo "시리얼 관리자를 실행합니다..."
    python serial_validator.py
else
    echo "오류: 가상 환경이 존재하지 않습니다."
    echo "다음 명령어로 가상 환경을 생성해주세요:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi 