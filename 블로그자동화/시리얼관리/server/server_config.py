#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
블로그 자동화 시스템의 서버 URL 설정
"""

# 서버 접속 정보
# 로컬 서버 (개발용)
LOCAL_SERVER_URL = "http://localhost:5000"

# 원격 서버 (배포용)
REMOTE_SERVER_URL = "https://blog-automation-server.onrender.com"

# 사용할 서버 URL 설정 (LOCAL 또는 REMOTE)
SERVER_MODE = "LOCAL"  # 로컬 서버 사용시 "LOCAL", 원격 서버 사용시 "REMOTE"

# 현재 사용할 서버 URL
CURRENT_SERVER_URL = LOCAL_SERVER_URL if SERVER_MODE == "LOCAL" else REMOTE_SERVER_URL 