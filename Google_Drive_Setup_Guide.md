# Google Drive 설정 가이드

## 개요
블로그 자동화 앱에서 Google Drive 연동을 설정하는 방법을 안내합니다.

## 사전 요구사항
1. Google 계정
2. Google Cloud Console 접근

## 설정 단계

### 1단계: Google Cloud Console 프로젝트 생성
1. [Google Cloud Console](https://console.cloud.google.com)에 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택

### 2단계: Google Drive API 활성화
1. "API 및 서비스" → "라이브러리" 이동
2. "Google Drive API" 검색 및 활성화

### 3단계: 서비스 계정 생성
1. "API 및 서비스" → "사용자 인증 정보" 이동
2. "사용자 인증 정보 만들기" → "서비스 계정" 선택
3. 역할: "편집자" 권한 부여

### 4단계: JSON 키 다운로드
1. 생성된 서비스 계정 클릭
2. "키" 탭 → "키 추가" → "JSON" 선택
3. 다운로드된 JSON 파일을 앱에서 지정한 경로에 저장

### 5단계: 앱에서 설정
1. 앱 설정 탭에서 "Google Drive" 섹션 찾기
2. JSON 키 파일 경로 입력
3. Google 스프레드시트 URL 입력 (선택사항)

## 문제 해결

### Q: 인증 오류가 발생합니다
A: JSON 키 파일 경로와 권한을 확인하세요.

### Q: 파일이 보이지 않습니다
A: 스프레드시트가 서비스 계정과 공유되어 있는지 확인하세요.

## 참고
- Google Cloud Console: https://console.cloud.google.com
- Google Drive API 문서: https://developers.google.com/drive
