#!/bin/bash

# 간단한 MCP 수정 스크립트

GITHUB_TOKEN="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"

# 디렉토리 설정
HOME_DIR=~
CURSOR_DIR="$HOME_DIR/.cursor"
APP_SUPPORT_DIR="$HOME_DIR/Library/Application Support/cursor"

# 백업 생성
echo "백업 생성 중..."
timestamp=$(date +%Y%m%d%H%M%S)
[ -f "$CURSOR_DIR/mcp.json" ] && cp "$CURSOR_DIR/mcp.json" "$CURSOR_DIR/mcp.json.backup.$timestamp"

# Smithery CLI 설치 및 초기화
echo "Smithery CLI 설치 및 초기화 중..."
npx -y @smithery/cli@latest reset --client cursor

# 모듈 설치
echo "GitHub 모듈 설치 중..."
npx -y @smithery/cli@latest install @smithery-ai/github --client cursor

# MCP 설정 수정
echo "MCP 설정 수정 중..."
cat > "$CURSOR_DIR/mcp.json" << EOF
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@smithery/cli@latest",
        "run",
        "@smithery-ai/github",
        "--config",
        "{\\"githubPersonalAccessToken\\":\\"$GITHUB_TOKEN\\"}"
      ]
    }
  }
}
EOF

# 파일 권한 설정
chmod 644 "$CURSOR_DIR/mcp.json"

echo "설치가 완료되었습니다. 커서를 완전히 종료하고 다시 시작해 주세요." 