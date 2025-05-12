#!/bin/bash

# 스크립트가 있는 디렉토리로 이동
cd "$(dirname "$0")"

# 환경 설정
export PYTHONPATH="$(pwd)"

# 메시지 표시
echo "====================================================="
echo "      블로그 자동화 시리얼 관리 (원격 서버 모드)        "
echo "====================================================="
echo "* 이 모드에서는 로컬 서버를 실행할 필요가 없습니다."
echo "* 모든 시리얼 검증 및 관리는 원격 서버에서 이루어집니다."
echo "* Render.com에 호스팅된 서버에 연결됩니다."
echo "====================================================="

# 가상 환경 활성화 확인
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "가상 환경 활성화: $(which python)"
fi

# 시리얼 관리 프로그램 실행
echo "시리얼 관리 프로그램 시작 중..."
python serial_validator.py

# 실행 결과
EXIT_CODE=$?
echo "프로그램 종료: 종료 코드 $EXIT_CODE"

# 오류 발생 시 대기
if [ $EXIT_CODE -ne 0 ]; then
    echo "오류가 발생했습니다. 아무 키나 눌러서 종료하세요..."
    read -n 1
fi 