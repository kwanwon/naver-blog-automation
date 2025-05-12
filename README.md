# 시리얼관리통합

이 프로젝트는 시리얼 인증 관리 시스템과 블로그 자동화 도구를 통합한 애플리케이션입니다.

## 폴더 구조

- `/시리얼관리통합`
  - `/블로그자동화` - 네이버 블로그 자동화 애플리케이션
  - `/시리얼관리` - 시리얼 번호 관리 시스템
  - `/modules` 
    - `/serial_validator` - 시리얼 인증 모듈

## 설치 및 실행

### 블로그 자동화 실행

1. `시리얼관리통합/블로그자동화` 폴더로 이동
2. 필요한 패키지 설치: `pip install -r requirements.txt`
3. 애플리케이션 실행: `python blog_writer_app.py`

### 시리얼 관리 시스템 실행

1. `시리얼관리통합/시리얼관리` 폴더로 이동
2. 필요한 패키지 설치: `pip install -r requirements.txt`
3. 애플리케이션 실행: `python run_mac_app.py`

## 개발 환경 설정

1. Git 저장소 클론: `git clone [저장소 URL]`
2. 가상 환경 설정: `python -m venv venv`
3. 가상 환경 활성화:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

## 기여 방법

1. 저장소 포크
2. 새 브랜치 생성: `git checkout -b feature-name`
3. 변경사항 커밋: `git commit -m "변경 내용"`
4. 변경사항 푸시: `git push origin feature-name`
5. Pull Request 요청 