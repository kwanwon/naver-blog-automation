# 🚀 Windows 실행 가이드 - 단계별 따라하기

## 📁 폴더 구조 확인

```
D:\naver-blog-automation\
├── 📄 quick-start-windows.bat          ← 1단계: 환경 설정
├── 📄 setup-windows-environment.bat    ← 1단계: 환경 설정 (대안)
├── 📄 README_WINDOWS.md                ← 간단한 시작 가이드
├── 📄 CURSOR_WINDOWS_SETUP.md          ← Cursor 설정 가이드
├── 📄 WINDOWS_SETUP_GUIDE.md           ← 전체 가이드
├── 📄 blog_writer_app.py               ← 메인 프로그램
├── 📄 build_developer_windows.bat      ← 개발자용 빌드
├── 📄 build_distribution_windows.bat   ← 배포용 빌드
├── 📄 installer_script.iss            ← 설치 프로그램 스크립트
├── 📁 mcp-setup\
│   └── 📄 install-mcp-windows.ps1     ← MCP 설정 스크립트
├── 📁 modules\                         ← 핵심 모듈들
├── 📁 config\                          ← 설정 파일들
└── 📁 default_images\                    ← 기본 이미지들
```

## 🎯 실행 순서 (단계별 따라하기)

### 1단계: 환경 설정 (필수)

#### 방법 A: 자동 설정 (권장)
```cmd
# 1. 명령 프롬프트(cmd) 또는 PowerShell 열기
# 2. 프로젝트 폴더로 이동
cd D:\naver-blog-automation

# 3. 자동 설정 실행
quick-start-windows.bat
```

#### 방법 B: 수동 설정
```cmd
# 1. 프로젝트 폴더로 이동
cd D:\naver-blog-automation

# 2. 가상환경 생성
python -m venv venv

# 3. 가상환경 활성화
.\venv\Scripts\activate

# 4. 의존성 설치
pip install -r requirements.txt
```

### 2단계: Cursor 설정

#### 2-1. Cursor 실행 및 프로젝트 열기
```
1. Cursor 실행
2. File > Open Folder
3. D:\naver-blog-automation 선택
4. "Yes, I trust the authors" 클릭
```

#### 2-2. MCP 설정
```powershell
# PowerShell 열기 (관리자 권한 불필요)
# 프로젝트 폴더에서 실행
.\mcp-setup\install-mcp-windows.ps1
```

#### 2-3. Cursor 재시작
```
1. Cursor 완전 종료
2. Cursor 다시 실행
3. 프로젝트 폴더 다시 열기
```

### 3단계: 프로그램 실행

#### 3-1. 가상환경 활성화
```cmd
# 명령 프롬프트에서
cd D:\naver-blog-automation
.\venv\Scripts\activate
```

#### 3-2. 프로그램 실행
```cmd
python blog_writer_app.py
```

#### 3-3. 정상 작동 확인
- ✅ UI가 정상적으로 표시되는지
- ✅ GPT 연동이 작동하는지
- ✅ 블로그 포스팅이 정상적으로 되는지

## 🏗️ 빌드 실행

### 개발자용 빌드 (테스트용)
```cmd
# 프로젝트 폴더에서
.\build_developer_windows.bat
```

**결과 확인:**
```
D:\naver-blog-automation\dist\블로그자동화-개발자\
├── 블로그자동화-개발자.exe
└── (기타 필요한 파일들)
```

### 배포용 빌드 (실제 배포용)

#### 1. 배포용 설정 파일 준비
```cmd
# 프로젝트 폴더에서
copy config\gpt_settings_distribution_template.txt config\gpt_settings_distribution.txt
```

#### 2. API 키 입력
```
1. config\gpt_settings_distribution.txt 파일 열기
2. "YOUR_DEVELOPER_API_KEY_HERE" 부분을 실제 API 키로 교체
3. 파일 저장
```

#### 3. 배포용 빌드 실행
```cmd
.\build_distribution_windows.bat
```

**결과 확인:**
```
D:\naver-blog-automation\dist\블로그자동화\
├── 블로그자동화.exe
└── (기타 필요한 파일들)
```

## 📦 설치 프로그램 생성

### 1. Inno Setup 설치
```
1. https://jrsoftware.org/isinfo.php 방문
2. Inno Setup 다운로드 및 설치
```

### 2. 설치 스크립트 수정
```
1. installer_script.iss 파일 열기
2. AppId GUID 수정:
   #define MyAppId "{YOUR-UNIQUE-APP-ID-HERE}"
   ↓
   #define MyAppId "{12345678-1234-1234-1234-123456789012}"
```

### 3. 설치 프로그램 생성
```
1. Inno Setup Compiler 실행
2. File > Open > installer_script.iss 선택
3. Build > Compile 실행
4. installer_output\블로그자동화_Setup_v1.5.0.exe 생성 확인
```

## 🔧 Cursor에서 작업하기

### MCP 기능 사용
```
1. Command Palette (Ctrl+Shift+P)
2. "MCP" 검색
3. 사용 가능한 MCP 명령어들:
   - Desktop Commander: Get Config
   - Desktop Commander: List Directory
   - GitHub: Search Repositories
   - GitKraken: Git Status
```

### 파일 관리
```
1. Cursor에서 파일 편집
2. Ctrl+S로 저장
3. Git 작업 (자동 커밋/푸시 가능)
```

## 🚨 문제 해결

### Python 오류
```cmd
# 가상환경 재생성
rmdir /s venv
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### MCP 연결 실패
```powershell
# PowerShell에서 MCP 재설정
.\mcp-setup\install-mcp-windows.ps1
# Cursor 재시작
```

### 빌드 실패
```cmd
# 이전 빌드 정리
rmdir /s build
rmdir /s dist
# 빌드 재실행
.\build_developer_windows.bat
```

### PowerShell 실행 정책 오류
```powershell
# PowerShell 관리자 권한으로 실행
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 📋 체크리스트

### ✅ 환경 설정 완료
- [ ] Python 3.11+ 설치됨
- [ ] Git 설치됨
- [ ] 가상환경 생성됨
- [ ] 의존성 설치됨
- [ ] 개발자 모드 파일 존재

### ✅ Cursor 설정 완료
- [ ] Cursor 설치됨
- [ ] 프로젝트 폴더 열림
- [ ] MCP 서버 연결됨
- [ ] Desktop Commander 작동 확인

### ✅ 프로그램 실행 완료
- [ ] 프로그램 정상 실행
- [ ] GPT 연동 작동
- [ ] 블로그 포스팅 테스트 성공

### ✅ 빌드 완료
- [ ] 개발자용 빌드 성공
- [ ] 배포용 빌드 성공
- [ ] 설치 프로그램 생성 성공

## 🎯 빠른 참조

### 자주 사용하는 명령어
```cmd
# 환경 활성화
.\venv\Scripts\activate

# 프로그램 실행
python blog_writer_app.py

# 개발자용 빌드
.\build_developer_windows.bat

# 배포용 빌드
.\build_distribution_windows.bat

# MCP 설정
.\mcp-setup\install-mcp-windows.ps1
```

### 중요한 파일들
- `README_WINDOWS.md` - 간단한 시작 가이드
- `CURSOR_WINDOWS_SETUP.md` - Cursor 설정 상세 가이드
- `WINDOWS_SETUP_GUIDE.md` - 전체 매뉴얼
- `quick-start-windows.bat` - 자동 환경 설정

---

**💡 팁**: 문제가 발생하면 `README_WINDOWS.md`를 먼저 확인하세요!
