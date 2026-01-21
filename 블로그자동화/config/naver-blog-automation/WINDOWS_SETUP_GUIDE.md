# Windows 환경 설정 가이드

## 🚀 빠른 시작 (자동 설정)

### 1단계: USB에서 Windows로 복사
```
USB → D:\naver-blog-automation\ (또는 원하는 경로)
```

### 2단계: 자동 설정 실행
```cmd
cd D:\naver-blog-automation
setup-windows-environment.bat
```

이 스크립트가 자동으로 수행하는 작업:
- ✅ Python 가상환경 생성
- ✅ 필요한 패키지 설치
- ✅ 개발자 모드 확인
- ✅ Cursor MCP 설정

### 3단계: Cursor에서 프로젝트 열기
1. Cursor 실행
2. `File > Open Folder` → `D:\naver-blog-automation` 선택
3. Cursor 재시작 (MCP 설정 적용)

### 4단계: 프로그램 테스트
```cmd
# 가상환경 활성화 (자동 설정에서 이미 활성화됨)
.\venv\Scripts\activate

# 프로그램 실행
python blog_writer_app.py
```

## 🔧 수동 설정 (자동 설정이 실패할 경우)

### Python 환경 설정
```powershell
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
.\venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### Cursor MCP 설정
```powershell
# MCP 설정 스크립트 실행
.\mcp-setup\install-mcp-windows.ps1
```

또는 수동 설정:
1. Cursor > Settings (Ctrl+,)
2. "MCP Servers" 검색
3. Edit in settings.json 클릭
4. 다음 내용 추가:

```json
{
  "mcp.enabled": true,
  "mcp.servers": {
    "desktop-commander": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-desktop-commander"],
      "allowedDirectories": ["D:\\naver-blog-automation"]
    }
  }
}
```

## 🏗️ 빌드 과정

### 개발자용 빌드 (테스트용)
```cmd
.\build_developer_windows.bat
```
- 결과: `dist\블로그자동화-개발자\` 폴더
- 시리얼 인증 건너뜀 (개발자 모드)

### 배포용 빌드 (실제 배포용)
1. **배포용 설정 파일 준비**:
   ```cmd
   copy config\gpt_settings_distribution_template.txt config\gpt_settings_distribution.txt
   ```
   - `config\gpt_settings_distribution.txt`에서 API 키 입력

2. **배포용 빌드 실행**:
   ```cmd
   .\build_distribution_windows.bat
   ```
   - 결과: `dist\블로그자동화\` 폴더
   - 시리얼 인증 필요
   - 빈 이미지 폴더 제공

## 📦 설치 프로그램 생성

### Inno Setup 설치
1. [Inno Setup 다운로드](https://jrsoftware.org/isinfo.php)
2. 설치 후 Inno Setup Compiler 실행

### 설치 스크립트 수정
`installer_script.iss` 파일에서:
```pascal
#define MyAppId "{YOUR-UNIQUE-APP-ID-HERE}"  // 고유 GUID로 변경
```

### 설치 프로그램 생성
1. Inno Setup Compiler에서 `installer_script.iss` 열기
2. Build > Compile 실행
3. `installer_output\블로그자동화_Setup_v1.5.0.exe` 생성 확인

## 🔍 문제 해결

### Python 관련 문제
```cmd
# Python 버전 확인
python --version

# 가상환경 재생성
rmdir /s venv
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Cursor MCP 문제
```cmd
# MCP 설정 재실행
.\mcp-setup\install-mcp-windows.ps1

# Cursor 완전 재시작
```

### 빌드 문제
```cmd
# 이전 빌드 정리
rmdir /s build
rmdir /s dist

# 빌드 재실행
.\build_developer_windows.bat
```

## 📁 프로젝트 구조

```
D:\naver-blog-automation\
├── blog_writer_app.py          # 메인 애플리케이션
├── modules\                     # 핵심 모듈들
├── config\                     # 설정 파일들
├── default_images\             # 기본 이미지들
├── build_developer_windows.bat # 개발자용 빌드
├── build_distribution_windows.bat # 배포용 빌드
├── installer_script.iss       # Inno Setup 스크립트
├── setup-windows-environment.bat # 자동 설정 스크립트
└── mcp-setup\                 # MCP 설정 스크립트들
```

## ⚠️ 주의사항

1. **API 키 보안**: `config\gpt_settings.txt`에 API 키가 포함되어 있으므로 Git 커밋 시 주의
2. **가상환경**: Windows에서 새로 생성해야 함 (Mac의 venv는 호환 안됨)
3. **ChromeDriver**: Windows 환경에 맞는 ChromeDriver가 자동으로 다운로드됨
4. **개발자 모드**: `modules\.developer_mode` 파일 존재 시 시리얼 인증 건너뜀
5. **배포용 빌드**: 빌드 전 반드시 `config\gpt_settings_distribution.txt` 준비 필요

## 🆘 지원

문제가 발생하면:
1. 이 가이드의 문제 해결 섹션 확인
2. `logs\` 폴더의 로그 파일 확인
3. Cursor에서 MCP 서버 상태 확인 (Command Palette > "MCP")
