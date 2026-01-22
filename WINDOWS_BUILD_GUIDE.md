# Windows 빌드 가이드

## 환경 준비

### 필수 프로그램
1. Python 3.11+
2. Git
3. Inno Setup (설치 프로그램 생성용)
4. Cursor (또는 VSCode)

### 저장소 클론
```powershell
git clone https://github.com/kwanwon/naver-blog-automation.git
cd naver-blog-automation/블로그자동화/config/naver-blog-automation
```

### 가상환경 설정
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
```

## 개발자 환경

### 개발자 모드 활성화
1. `modules/.developer_mode` 파일 생성
2. `config/gpt_settings.txt`에 API 키 설정

### 실행
```powershell
.\venv\Scripts\activate
python blog_writer_app.py
```

## 빌드

### 개발자용 빌드
```powershell
.\build_developer_windows.bat
```

### 배포용 빌드
1. `config/gpt_settings_distribution.txt` 준비 (개발자 API 키 포함)
2. `.\build_distribution_windows.bat` 실행
3. Inno Setup으로 설치 프로그램 생성

## 자동 업데이트

- 프로그램 시작 시 자동으로 GitHub에서 버전 확인
- 새 버전 발견 시 UI에서 알림 표시
- 사용자가 업데이트 버튼 클릭 시 자동 다운로드 및 설치

## API 키 보안

- API 키는 password=True로 자동 마스킹 처리됨
- 사용자 화면에서 ****로 표시
- 추가 수정 불필요
