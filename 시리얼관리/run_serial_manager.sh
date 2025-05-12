#!/bin/bash

# 시리얼 관리 프로그램 실행 스크립트
cd "$(dirname "$0")"
source venv/bin/activate
python serial_validator.py 