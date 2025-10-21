# Windows용 MCP 자동 설정 스크립트
# Cursor IDE에서 MCP 서버들을 자동으로 설정합니다.

Write-Host "🚀 Windows용 MCP 설정을 시작합니다..." -ForegroundColor Green

# 현재 프로젝트 경로 확인
$PROJECT_PATH = Get-Location
Write-Host "📁 프로젝트 경로: $PROJECT_PATH" -ForegroundColor Yellow

# Cursor 설정 디렉토리 경로
$CURSOR_CONFIG_DIR = "$env:APPDATA\Cursor\User"
$CURSOR_MCP_DIR = "$env:APPDATA\Cursor\User\globalStorage\cursor-mcp"

# 필요한 디렉토리 생성
Write-Host "📂 Cursor 설정 디렉토리 생성 중..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $CURSOR_CONFIG_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $CURSOR_MCP_DIR | Out-Null

# MCP 설정 파일 생성
Write-Host "⚙️ MCP 설정 파일 생성 중..." -ForegroundColor Yellow
$MCP_CONFIG = @{
    "mcpServers" = @{
        "desktop-commander" = @{
            "command" = "npx"
            "args" = @("-y", "@modelcontextprotocol/server-desktop-commander")
            "allowedDirectories" = @($PROJECT_PATH)
        }
        "github" = @{
            "command" = "npx"
            "args" = @(
                "-y",
                "@smithery/cli@latest",
                "run",
                "@smithery-ai/github",
                "--config",
                '{"githubPersonalAccessToken":"YOUR_GITHUB_TOKEN_HERE"}'
            )
        }
        "gitkraken" = @{
            "command" = "npx"
            "args" = @("-y", "@modelcontextprotocol/server-gitkraken")
        }
    }
}

# MCP 설정을 JSON으로 변환하여 저장
$MCP_JSON = $MCP_CONFIG | ConvertTo-Json -Depth 10
$MCP_JSON | Out-File -FilePath "$CURSOR_MCP_DIR\mcp.json" -Encoding UTF8

# Cursor 사용자 설정 파일 생성
Write-Host "🔧 Cursor 사용자 설정 생성 중..." -ForegroundColor Yellow
$CURSOR_SETTINGS = @{
    "telemetry.telemetryLevel" = "off"
    "privacy.mode" = "off"
    "mcp.enabled" = $true
    "mcp.configPath" = "$CURSOR_MCP_DIR\mcp.json"
    "workbench.colorTheme" = "Default Dark+"
    "terminal.integrated.env.windows" = @{
        "CURSOR_MCP_PATH" = "$CURSOR_MCP_DIR\mcp.json"
    }
}

$SETTINGS_JSON = $CURSOR_SETTINGS | ConvertTo-Json -Depth 10
$SETTINGS_JSON | Out-File -FilePath "$CURSOR_CONFIG_DIR\settings.json" -Encoding UTF8

# 파일 권한 설정
Write-Host "🔐 파일 권한 설정 중..." -ForegroundColor Yellow
if (Test-Path "$CURSOR_MCP_DIR\mcp.json") {
    icacls "$CURSOR_MCP_DIR\mcp.json" /grant "$env:USERNAME:(R,W)" /T | Out-Null
}
if (Test-Path "$CURSOR_CONFIG_DIR\settings.json") {
    icacls "$CURSOR_CONFIG_DIR\settings.json" /grant "$env:USERNAME:(R,W)" /T | Out-Null
}

Write-Host "✅ MCP 설정이 완료되었습니다!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 다음 단계:" -ForegroundColor Cyan
Write-Host "1. Cursor를 완전히 종료하고 다시 시작하세요" -ForegroundColor White
Write-Host "2. Command Palette (Ctrl+Shift+P)에서 'MCP' 검색하여 설정 확인" -ForegroundColor White
Write-Host "3. GitHub 토큰이 필요하면 settings.json에서 'YOUR_GITHUB_TOKEN_HERE' 부분을 실제 토큰으로 교체" -ForegroundColor White
Write-Host ""
Write-Host "🔍 설정 파일 위치:" -ForegroundColor Cyan
Write-Host "MCP 설정: $CURSOR_MCP_DIR\mcp.json" -ForegroundColor White
Write-Host "Cursor 설정: $CURSOR_CONFIG_DIR\settings.json" -ForegroundColor White

Write-Host ""
Write-Host "🎯 다음 단계:" -ForegroundColor Green
Write-Host "1. Cursor를 완전히 종료하고 다시 시작하세요" -ForegroundColor White
Write-Host "2. Command Palette (Ctrl+Shift+P)에서 'MCP' 검색하여 설정 확인" -ForegroundColor White
Write-Host "3. 'Desktop Commander: Get Config' 실행하여 정상 작동 확인" -ForegroundColor White
Write-Host "4. README_WINDOWS.md 파일을 참조하여 작업을 이어가세요" -ForegroundColor White
