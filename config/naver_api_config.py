# 네이버 API 설정
NAVER_API_CONFIG = {
    'CLIENT_ID': 'sVqQaykvFMsaiG02MRdj',
    'CLIENT_SECRET': '4iulWFPjXs',  # Client Secret 값 입력 완료
    'REDIRECT_URI': 'http://localhost:8000/callback',
    'STATE': 'RANDOM_STATE'
}

# 로그인 관련 URL
NAVER_URLS = {
    'AUTH': 'https://nid.naver.com/oauth2.0/authorize',
    'TOKEN': 'https://nid.naver.com/oauth2.0/token',
    'PROFILE': 'https://openapi.naver.com/v1/nid/me'
} 