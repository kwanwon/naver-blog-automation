# 🪟 Windows 환경 작업 가이드

## 🚀 빠른 시작 (3분 완료)

### 1️⃣ 환경 설정
```cmd
# 프로젝트 폴더에서 실행
quick-start-windows.bat
```

### 2️⃣ Cursor 설정
```
1. Cursor 실행
2. File > Open Folder > 이 폴더 선택
3. PowerShell에서: .\mcp-setup\install-mcp-windows.ps1
4. Cursor 재시작
```

### 3️⃣ 작업 시작
```cmd
# 가상환경 활성화
.\venv\Scripts\activate

# 프로그램 실행
python blog_writer_app.py
```

## 📋 상세 가이드

- **기본 설정**: `CURSOR_WINDOWS_SETUP.md`
- **전체 가이드**: `WINDOWS_SETUP_GUIDE.md`
- **빠른 시작**: `quick-start-windows.bat`

## 🔧 주요 기능

### 개발 환경
- ✅ Python 가상환경 자동 설정
- ✅ Cursor MCP 서버 자동 연결
- ✅ 개발자 모드 (시리얼 인증 건너뜀)
- ✅ Mac과 동일한 개발 환경

### 빌드 시스템
- ✅ 개발자용 빌드: `build_developer_windows.bat`
- ✅ 배포용 빌드: `build_distribution_windows.bat`
- ✅ Inno Setup 설치 프로그램: `installer_script.iss`

### MCP 서버
- ✅ Desktop Commander: 파일 관리
- ✅ GitHub: 저장소 작업
- ✅ GitKraken: Git 작업

## 🎯 작업 흐름

### 1. 개발 작업
```cmd
# 환경 활성화
.\venv\Scripts\activate

# 프로그램 실행
python blog_writer_app.py

# Cursor에서 코드 편집
# MCP로 파일 관리 및 Git 작업
```

### 2. 빌드 테스트
```cmd
# 개발자용 빌드
.\build_developer_windows.bat

# 결과 확인
dir dist\블로그자동화-개발자\
```

### 3. 배포 준비
```cmd
# 배포용 설정 파일 준비
copy config\gpt_settings_distribution_template.txt config\gpt_settings_distribution.txt
# config\gpt_settings_distribution.txt에서 API 키 입력

# 배포용 빌드
.\build_distribution_windows.bat
```

### 4. 설치 프로그램 생성
```
1. Inno Setup 설치
2. installer_script.iss 열기
3. AppId GUID 수정
4. Compile 실행
5. installer_output\블로그자동화_Setup_v1.5.0.exe 생성
```

## 🔍 문제 해결

### MCP 연결 안됨
```cmd
# PowerShell에서 재설정
.\mcp-setup\install-mcp-windows.ps1
# Cursor 재시작
```

### Python 오류
```cmd
# 가상환경 재생성
rmdir /s venv
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 빌드 실패
```cmd
# 이전 빌드 정리
rmdir /s build dist
# 빌드 재실행
.\build_developer_windows.bat
```

## 📞 지원

- **상세 가이드**: `CURSOR_WINDOWS_SETUP.md`
- **전체 매뉴얼**: `WINDOWS_SETUP_GUIDE.md`
- **빠른 시작**: `quick-start-windows.bat`

---

**💡 팁**: Mac에서 작업하던 것과 동일하게 Cursor에서 MCP를 사용하여 파일 관리, Git 작업, 빌드 등을 할 수 있습니다!
