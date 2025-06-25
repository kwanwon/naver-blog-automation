#!/bin/bash
echo "🚀 ChromeDriver 권한 수정 시작"
echo "=" * 50

# 기존 WebDriverManager 캐시의 ChromeDriver들 수정
echo "🔍 기존 ChromeDriver 찾는 중..."

# WebDriverManager 캐시 경로
WDM_CACHE="$HOME/.wdm/drivers/chromedriver"

if [ -d "$WDM_CACHE" ]; then
    echo "📁 WebDriverManager 캐시 발견: $WDM_CACHE"
    find "$WDM_CACHE" -name "chromedriver" -type f | while read chromedriver_path; do
        echo "🔧 권한 수정 중: $chromedriver_path"
        chmod +x "$chromedriver_path"
        xattr -d com.apple.quarantine "$chromedriver_path" 2>/dev/null || true
        xattr -d com.apple.provenance "$chromedriver_path" 2>/dev/null || true
        
        # 테스트
        if "$chromedriver_path" --version >/dev/null 2>&1; then
            echo "✅ 수정 완료: $chromedriver_path"
        else
            echo "❌ 수정 실패: $chromedriver_path"
        fi
    done
else
    echo "📁 WebDriverManager 캐시가 없습니다."
fi

# 프로젝트 폴더의 ChromeDriver
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_CHROMEDRIVER="$SCRIPT_DIR/chromedriver-mac-arm64/chromedriver"

if [ -f "$PROJECT_CHROMEDRIVER" ]; then
    echo "📁 프로젝트 ChromeDriver 발견: $PROJECT_CHROMEDRIVER"
    echo "🔧 권한 수정 중..."
    chmod +x "$PROJECT_CHROMEDRIVER"
    xattr -d com.apple.quarantine "$PROJECT_CHROMEDRIVER" 2>/dev/null || true
    xattr -d com.apple.provenance "$PROJECT_CHROMEDRIVER" 2>/dev/null || true
    
    if "$PROJECT_CHROMEDRIVER" --version; then
        echo "✅ 프로젝트 ChromeDriver 수정 완료"
    else
        echo "❌ 프로젝트 ChromeDriver 수정 실패"
    fi
else
    echo "📁 프로젝트 ChromeDriver가 없습니다."
fi

echo ""
echo "=" * 50
echo "🎉 ChromeDriver 권한 수정 완료!"
echo "이제 블로그 자동화 프로그램을 실행해보세요."