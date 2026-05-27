#!/bin/bash
# GitKraken MCP Wrapper to prevent non-JSON output on stdout
# All stderr is redirected to a log file for debugging

LOG_FILE="/Users/gm2hapkido/Library/Application Support/Antigravity/gk_mcp_error.log"
GK_PATH="/Users/gm2hapkido/Library/Application Support/Antigravity/User/globalStorage/eamodio.gitlens/gk"

exec "$GK_PATH" "$@" 2>>"$LOG_FILE"
