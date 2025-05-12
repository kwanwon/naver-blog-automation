# 블로그 자동화 시스템 서버 배포 지침

이 문서는 블로그 자동화 시스템의 서버 부분을 Render.com에 배포하는 방법을 설명합니다.

## 1. 사전 준비

- GitHub 계정
- Render.com 계정 (무료 서비스로 시작 가능)

## 2. GitHub 저장소 준비

1. GitHub에 새 저장소를 생성합니다.
2. 다음 파일들을 저장소에 업로드합니다:
   - `blog_automation_server.py` (서버 코드)
   - `requirements.txt` (종속성 목록)

## 3. Render.com에 서비스 배포

### 3.1. 웹 서비스 생성

1. Render.com에 로그인합니다.
2. 대시보드에서 **New** > **Web Service**를 선택합니다.
3. GitHub 저장소를 연결합니다.

### 3.2. 웹 서비스 구성

다음과 같이 설정합니다:

- **Name**: 원하는 서비스 이름 (예: `blog-automation-server`)
- **Region**: 서버 위치 (가장 가까운 지역 선택)
- **Branch**: `main` (또는 기본 브랜치)
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn blog_automation_server:app`

### 3.3. 고급 설정

필요한 경우 다음 고급 설정을 구성합니다:

- **Auto-Deploy**: Enabled (GitHub 저장소 변경 시 자동 배포)
- **환경 변수**: 필요한 경우 설정 (예: `FLASK_ENV=production`)

### 3.4. 배포 완료

1. **Create Web Service** 버튼을 클릭합니다.
2. Render가 자동으로 코드를 배포하고 서비스를 시작합니다.
3. 배포가 완료되면 서비스 URL을 확인합니다. (예: `https://blog-automation-server.onrender.com`)

## 4. 서버 URL 설정

1. 블로그자동화관리.py 파일에서 `BLOG_SERVER_URL` 변수를 배포된 URL로 업데이트합니다.
```python
# 서버 주소 설정
BLOG_SERVER_URL = "https://your-service-name.onrender.com"
```

## 5. 서버 기능 확인

배포 후 다음 엔드포인트를 확인하여 서버가 제대로 작동하는지 테스트합니다:

- 상태 확인: `GET /api/health`
- 시리얼 목록 조회: `GET /api/serials`

## 6. 주의사항

- Render의 무료 티어는 제한된 자원을 제공하며, 일정 시간 동안 활동이 없으면 서비스가 휴면 상태로 전환됩니다.
- 첫 요청 시 서비스 시작에 시간이 걸릴 수 있습니다.
- 실제 운영 환경에서는 보안 설정과 데이터베이스 백업을 고려해야 합니다.

## 7. 문제 해결

- 배포 문제: Render 대시보드에서 로그를 확인합니다.
- 연결 문제: 클라이언트에서 올바른 URL을 사용하고 있는지 확인합니다.
- 404 오류: API 엔드포인트 경로가 올바른지 확인합니다. 