#!/bin/bash

# MCP 설치 스크립트

GITHUB_TOKEN="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"

# 홈 디렉토리와 커서 디렉토리 설정
HOME_DIR=~
CURSOR_DIR="$HOME_DIR/.cursor"
APP_SUPPORT_DIR="$HOME_DIR/Library/Application Support/cursor"

# MCP 설정 파일 생성
echo "MCP 설정 파일 생성 중..."
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

# 설정 파일 업데이트
echo "커서 설정 파일 업데이트 중..."
cat > "$CURSOR_DIR/settings.json" << EOF
{
    "telemetry.telemetryLevel": "off",
    "privacy.mode": "off",
    "mcp.enabled": true,
    "mcp.configPath": "$CURSOR_DIR/mcp.json",
    "workbench.colorTheme": "Default Dark+",
    "terminal.integrated.env.osx": {
        "CURSOR_MCP_PATH": "$CURSOR_DIR/mcp.json"
    }
}
EOF

# Application Support 디렉토리에 설정 복사
mkdir -p "$APP_SUPPORT_DIR/User"
cp "$CURSOR_DIR/mcp.json" "$APP_SUPPORT_DIR/User/mcp.json"

# 파일 권한 설정
chmod 644 "$CURSOR_DIR/mcp.json"
chmod 644 "$CURSOR_DIR/settings.json"
chmod 644 "$APP_SUPPORT_DIR/User/mcp.json"

echo "설치가 완료되었습니다. 커서를 완전히 종료하고 다시 시작해 주세요." 