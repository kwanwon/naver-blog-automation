# 블로그 자동화 시스템 - 시리얼 관리 서버

이 프로젝트는 블로그 자동화 시스템의 시리얼 번호 관리를 위한 서버 API를 제공합니다.

## 기능

- 시리얼 번호 생성 및 등록
- 시리얼 번호 조회 및 관리
- 블랙리스트 관리
- 상태 확인 API

## 시작하기

### 필수 조건

- Python 3.6 이상
- Flask
- Flask-CORS

### 설치

1. 저장소를 클론합니다:
```
git clone https://github.com/kwanwon/serial-validator-server.git
cd serial-validator-server
```

2. 의존성을 설치합니다:
```
pip install -r requirements.txt
```

3. 서버를 실행합니다:
```
python main.py
```

## API 엔드포인트

### 상태 확인
- `GET /api/health`: 서버 상태 확인

### 시리얼 관리
- `POST /api/serial/register`: 새 시리얼 등록
- `GET /api/serials`: 모든 시리얼 조회
- `GET /api/serial/{serial_number}`: 특정 시리얼 조회
- `PATCH /api/serials/{serial_number}`: 시리얼 상태 업데이트
- `DELETE /api/serial/{serial_number}`: 시리얼 삭제

### 블랙리스트 관리
- `POST /api/blacklist`: 블랙리스트 관리 (추가/제거)

## 배포

이 서버는 Render.com에 배포되어 있습니다. 자세한 배포 지침은 [deploy_instructions.md](deploy_instructions.md)를 참조하세요.

## 서버 데이터베이스

서버는 `blog_serials.db` SQLite 데이터베이스를 사용합니다. 데이터베이스는 처음 서버 실행 시 자동으로 생성됩니다.

### 테이블 구조

```sql
CREATE TABLE blog_serials (
  serial_number TEXT PRIMARY KEY, 
  activation_date TEXT,
  expiry_date TEXT,
  status TEXT DEFAULT '사용가능',
  device_info TEXT,
  memo TEXT DEFAULT '',
  activation_count INTEGER DEFAULT 0,
  is_blacklisted INTEGER DEFAULT 0,
  is_deleted INTEGER DEFAULT 0,
  created_date TEXT
)
``` 