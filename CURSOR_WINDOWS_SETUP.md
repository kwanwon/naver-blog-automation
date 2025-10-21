# Windows에서 Cursor 설정 및 작업 이어가기 가이드

## 🚀 빠른 시작 (3단계)

### 1단계: 프로젝트 폴더 열기
```
1. Cursor 실행
2. File > Open Folder
3. D:\naver-blog-automation 선택
```

### 2단계: MCP 자동 설정
```cmd
# PowerShell에서 실행 (관리자 권한 불필요)
cd D:\naver-blog-automation
.\mcp-setup\install-mcp-windows.ps1
```

### 3단계: Cursor 재시작
```
Cursor 완전 종료 → 다시 실행
```

## 🔧 상세 설정 과정

### A. Cursor 기본 설정

#### 1. Cursor 설치 및 로그인
- [Cursor 다운로드](https://cursor.sh/) → Windows용 설치
- Cursor 실행 후 GitHub 계정으로 로그인

#### 2. 프로젝트 열기
```
File > Open Folder → D:\naver-blog-automation
```

#### 3. 설정 동기화 (선택사항)
- Cursor > Settings > Account
- "Sync Settings" 활성화 (Mac 설정과 동기화)

### B. MCP 서버 설정

#### 자동 설정 (권장)
```powershell
# PowerShell 실행 (관리자 권한 불필요)
cd D:\naver-blog-automation
.\mcp-setup\install-mcp-windows.ps1
```

#### 수동 설정 (자동 설정 실패 시)
1. **Cursor 설정 열기**: `Ctrl + ,`
2. **MCP 검색**: 설정에서 "MCP" 검색
3. **settings.json 편집**: "Edit in settings.json" 클릭
4. **다음 내용 추가**:

```json
{
  "mcp.enabled": true,
  "mcp.servers": {
    "desktop-commander": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-desktop-commander"],
      "allowedDirectories": ["D:\\naver-blog-automation"]
    },
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@smithery/cli@latest",
        "run",
        "@smithery-ai/github",
        "--config",
        "{\"githubPersonalAccessToken\":\"YOUR_GITHUB_TOKEN\"}"
      ]
    }
  }
}
```

### C. MCP 설정 확인

#### 1. Command Palette에서 확인
```
Ctrl + Shift + P → "MCP" 검색
```

#### 2. Desktop Commander 테스트
```
Ctrl + Shift + P → "Desktop Commander: Get Config" 실행
```

#### 3. 정상 작동 확인
- 에러 없이 설정 정보가 표시되면 성공
- 에러 발생 시 Cursor 재시작 후 재시도

## 🐍 Python 환경 설정

### 가상환경 생성
```cmd
cd D:\naver-blog-automation
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 개발자 모드 확인
```cmd
# modules\.developer_mode 파일 존재 확인
dir modules\.developer_mode
```

## 🏗️ 빌드 및 테스트

### 개발자용 빌드
```cmd
.\build_developer_windows.bat
```

### 배포용 빌드
```cmd
# 1. 배포용 설정 파일 준비
copy config\gpt_settings_distribution_template.txt config\gpt_settings_distribution.txt

# 2. config\gpt_settings_distribution.txt에서 API 키 입력

# 3. 배포용 빌드 실행
.\build_distribution_windows.bat
```

## 🔍 문제 해결

### MCP 연결 실패
```cmd
# 1. Cursor 완전 종료
# 2. PowerShell에서 MCP 재설정
.\mcp-setup\install-mcp-windows.ps1
# 3. Cursor 재시작
```

### Python 환경 문제
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
rmdir /s build
rmdir /s dist
# 빌드 재실행
.\build_developer_windows.bat
```

## 📋 작업 이어가기 체크리스트

### ✅ 환경 설정 완료 확인
- [ ] Cursor에서 프로젝트 폴더 열림
- [ ] MCP 서버 정상 연결 (Desktop Commander, GitHub)
- [ ] Python 가상환경 활성화
- [ ] 개발자 모드 파일 존재 확인

### ✅ 기능 테스트
- [ ] 프로그램 실행: `python blog_writer_app.py`
- [ ] GPT 연동 정상 작동
- [ ] 블로그 포스팅 테스트
- [ ] 개발자용 빌드 성공
- [ ] 배포용 빌드 성공

### ✅ Cursor 기능 확인
- [ ] Command Palette에서 MCP 명령어 사용 가능
- [ ] Desktop Commander로 파일 관리 가능
- [ ] GitHub MCP로 저장소 작업 가능
- [ ] 자동완성 및 AI 어시스턴트 정상 작동

## 🎯 다음 단계

환경 설정이 완료되면:

1. **개발 작업**: Mac과 동일한 환경에서 코드 수정
2. **빌드 테스트**: Windows 환경에서 빌드 및 실행 테스트
3. **배포 준비**: 배포용 빌드 및 설치 프로그램 생성
4. **Git 작업**: 변경사항을 GitHub에 푸시

## 🆘 지원

문제가 발생하면:
1. `WINDOWS_SETUP_GUIDE.md` 참조
2. `logs\` 폴더의 로그 파일 확인
3. Cursor에서 MCP 서버 상태 확인
4. PowerShell 실행 정책 확인: `Get-ExecutionPolicy`
