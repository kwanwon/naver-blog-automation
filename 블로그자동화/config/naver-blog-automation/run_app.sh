#!/bin/bash

# 스크립트 디렉토리로 이동
cd "$(dirname "$0")"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 헤더 출력
echo "======================================================="
echo "🌍 크로스 플랫폼 블로그 자동화 도구 - Unix 버전"
echo "======================================================="
echo

# 플랫폼 감지
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macOS"
    PYTHON_CMD="python3"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="Linux"
    PYTHON_CMD="python3"
else
    PLATFORM="Unknown"
    PYTHON_CMD="python"
fi

echo "🖥️  플랫폼: $PLATFORM"

# Python 버전 확인
echo "🐍 Python 환경 확인 중..."
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo -e "${RED}❌ Python이 설치되지 않았거나 PATH에 없습니다.${NC}"
    echo "   다음 명령어로 Python을 설치하세요:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "   brew install python3"
        echo "   또는 https://www.python.org/downloads/ 에서 다운로드"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "   sudo apt install python3 python3-pip  # Ubuntu/Debian"
        echo "   sudo dnf install python3 python3-pip  # Fedora/CentOS"
    fi
    exit 1
fi

$PYTHON_CMD --version
echo

# 가상환경 확인 및 활성화
if [ -f "venv/bin/activate" ]; then
    echo "🏠 가상환경 활성화 중..."
    source venv/bin/activate
    echo -e "${GREEN}✅ 가상환경 활성화 완료${NC}"
else
    echo -e "${YELLOW}⚠️ 가상환경이 없습니다. 설정 스크립트를 먼저 실행하세요.${NC}"
    echo "   $PYTHON_CMD setup_cross_platform.py"
    exit 1
fi

echo

# ChromeDriver 확인 및 권한 설정
if [ -f "chromedriver" ]; then
    echo "🚗 ChromeDriver 발견: chromedriver"
    
    # 실행 권한 확인
    if [ ! -x "chromedriver" ]; then
        echo "🔑 ChromeDriver에 실행 권한 부여 중..."
        chmod +x chromedriver
        echo -e "${GREEN}✅ 실행 권한 부여 완료${NC}"
    fi
    
    # macOS에서 quarantine 속성 제거
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if xattr chromedriver 2>/dev/null | grep -q "com.apple.quarantine"; then
            echo "🔓 macOS quarantine 속성 제거 중..."
            xattr -d com.apple.quarantine chromedriver 2>/dev/null
            echo -e "${GREEN}✅ quarantine 속성 제거 완료${NC}"
        fi
    fi
elif [ -f "chromedriver.exe" ]; then
    echo "🚗 ChromeDriver 발견: chromedriver.exe"
else
    echo "ℹ️ ChromeDriver가 없습니다. WebDriverManager가 자동 다운로드할 예정입니다."
fi

echo

# 애플리케이션 실행
echo "🚀 블로그 자동화 도구 시작 중..."

# macOS에서 절전 모드 방지 안내
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🔋 macOS 절전 모드 방지 기능이 자동으로 활성화됩니다."
    echo "   (프로그램 실행 중 맥북이 잠들지 않습니다)"
fi

echo

# Python 스크립트 실행
$PYTHON_CMD blog_writer_app.py

# 종료 코드 확인
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo
    echo -e "${RED}❌ 애플리케이션 실행 중 오류가 발생했습니다. (종료 코드: $exit_code)${NC}"
    echo "   자세한 오류 내용은 위의 메시지를 확인하세요."
    echo
    echo "🔧 일반적인 해결 방법:"
    echo "   1. 의존성 재설치: pip install -r requirements_cross_platform.txt"
    echo "   2. 가상환경 재생성: rm -rf venv && python3 -m venv venv"
    echo "   3. 설정 스크립트 재실행: $PYTHON_CMD setup_cross_platform.py"
    echo
    read -p "아무 키나 눌러서 종료하세요..."
    exit $exit_code
fi

echo
echo -e "${GREEN}애플리케이션이 정상적으로 종료되었습니다.${NC}" 