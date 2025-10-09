#!/bin/bash

# GitHub MCP 초기화 및 재설정 스크립트

GITHUB_TOKEN="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"

# 디렉토리 설정
HOME_DIR=~
CURSOR_DIR="$HOME_DIR/.cursor"

echo "1. 캐시 및 임시 파일 정리 중..."
rm -rf "$CURSOR_DIR/cache" 2>/dev/null
rm -rf "$CURSOR_DIR/temp" 2>/dev/null
rm -rf "$HOME_DIR/Library/Application Support/cursor/Cache" 2>/dev/null
rm -rf "$HOME_DIR/Library/Application Support/cursor/Code Cache" 2>/dev/null

echo "2. MCP 설정 초기화 중..."
timestamp=$(date +%Y%m%d%H%M%S)
[ -f "$CURSOR_DIR/mcp.json" ] && cp "$CURSOR_DIR/mcp.json" "$CURSOR_DIR/mcp.json.backup.$timestamp"

echo "3. 새 MCP 설정 생성 중..."
cat > "$CURSOR_DIR/mcp.json" << EOF
{
  "mcpServers": {
    "github": {
      "enabled": true,
      "name": "github",
      "type": "github",
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

echo "4. 권한 설정 중..."
chmod 644 "$CURSOR_DIR/mcp.json"

echo "5. Smithery CLI 패키지 설치 중..."
npm install -g @smithery/cli@latest

echo "6. 완료! 이제 Cursor를 완전히 종료하고 재시작해주세요." 