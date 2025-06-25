# 🌍 크로스 플랫폼 블로그 자동화 도구

**Windows, macOS, Linux** 모든 플랫폼에서 실행 가능한 네이버 블로그 자동화 도구입니다.

## 📋 지원 플랫폼

### ✅ Windows
- **Windows 10** 이상 (64-bit 권장)
- **Windows 11** 완전 지원
- **Intel/AMD** 프로세서 모두 지원
- **PowerShell 5.1** 이상 권장

### ✅ macOS  
- **macOS 10.15 (Catalina)** 이상
- **Intel Mac** 완전 지원
- **Apple Silicon (M1/M2/M3)** 완전 지원
- **Xcode Command Line Tools** 권장

### ✅ Linux
- **Ubuntu 18.04** 이상
- **CentOS 7** 이상  
- **Fedora 30** 이상
- **Debian 10** 이상
- 기타 주요 배포판 지원

## 🚀 빠른 시작

### 1️⃣ **시스템 요구사항 확인**

```bash
# 시스템 호환성 확인
python setup_cross_platform.py --check-only
```

### 2️⃣ **자동 설정 (권장)**

```bash
# 모든 플랫폼 자동 설정
python setup_cross_platform.py
```

### 3️⃣ **수동 설정 (고급 사용자)**

<details>
<summary>Windows 수동 설정</summary>

```powershell
# 1. Python 가상 환경 생성
python -m venv venv

# 2. 가상 환경 활성화
venv\Scripts\activate

# 3. 패키지 설치
pip install -r requirements_cross_platform.txt

# 4. 애플리케이션 실행
python blog_writer_app.py
```

</details>

<details>
<summary>macOS 수동 설정</summary>

```bash
# 1. Python 가상 환경 생성
python3 -m venv venv

# 2. 가상 환경 활성화
source venv/bin/activate

# 3. 패키지 설치
pip install -r requirements_cross_platform.txt

# 4. ChromeDriver 권한 설정 (필요시)
chmod +x chromedriver

# 5. 애플리케이션 실행
python blog_writer_app.py
```

</details>

<details>
<summary>Linux 수동 설정</summary>

```bash
# 1. 시스템 의존성 설치 (Ubuntu/Debian)
sudo apt update
sudo apt install python3-venv python3-pip

# 또는 CentOS/RHEL/Fedora
sudo dnf install python3-venv python3-pip

# 2. Python 가상 환경 생성
python3 -m venv venv

# 3. 가상 환경 활성화
source venv/bin/activate

# 4. 패키지 설치
pip install -r requirements_cross_platform.txt

# 5. ChromeDriver 권한 설정 (필요시)
chmod +x chromedriver

# 6. 애플리케이션 실행
python blog_writer_app.py
```

</details>

## 📦 실행 파일 빌드

### 🔧 **현재 플랫폼용 빌드**

```bash
# 현재 운영체제용 실행 파일 생성
python build_cross_platform.py
```

### 🌐 **특정 플랫폼용 빌드**

```bash
# Windows용 빌드
python build_cross_platform.py --platform windows

# macOS용 빌드  
python build_cross_platform.py --platform macos

# Linux용 빌드
python build_cross_platform.py --platform linux
```

### 📁 **빌드 결과물**

빌드 완료 후 `dist/` 디렉토리에 다음과 같은 파일들이 생성됩니다:

- **Windows**: `BlogAutomation_Windows/BlogAutomation_Windows.exe`
- **macOS**: `BlogAutomation_Macos.app` (앱 번들)
- **Linux**: `BlogAutomation_Linux/BlogAutomation_Linux` (실행 파일)

## 🔧 고급 기능

### 🎯 **플랫폼별 최적화**

#### Windows 최적화
- Windows 서비스 통합
- PowerShell 스크립트 지원
- Windows 보안 정책 준수
- 시스템 트레이 지원

#### macOS 최적화
- 앱 번들 (.app) 생성
- macOS 권한 관리
- Apple Silicon 네이티브 지원
- 키체인 통합
- **🔋 자동 절전 모드 방지** - 프로그램 실행 중 맥북 잠들기 방지

#### Linux 최적화
- 다양한 배포판 지원
- systemd 서비스 통합
- X11/Wayland 호환성
- 패키지 관리자 통합

### 🔐 **보안 기능**

- **암호화된 설정 저장**
- **플랫폼별 키스토어 활용**
- **안전한 크리덴셜 관리**
- **자동 업데이트 검증**

### 🌐 **네트워크 최적화**

- **프록시 자동 감지**
- **방화벽 호환성**
- **IPv6 지원**
- **DNS 캐싱**

## 🛠️ 문제 해결

### 📋 **일반적인 문제들**

<details>
<summary>🚫 Python 버전 호환성 문제</summary>

**문제**: `Python 버전이 너무 낮습니다`

**해결책**:
```bash
# Python 3.8 이상 설치 확인
python --version

# 또는 특정 버전 사용
python3.9 -m venv venv
```

</details>

<details>
<summary>🚫 ChromeDriver 권한 문제</summary>

**문제**: `ChromeDriver 실행 권한 없음`

**해결책**:
```bash
# macOS/Linux
chmod +x chromedriver
xattr -d com.apple.quarantine chromedriver  # macOS만

# Windows (관리자 권한으로)
icacls chromedriver.exe /grant Everyone:F
```

</details>

<details>
<summary>🚫 가상 환경 문제</summary>

**문제**: `가상 환경 생성 실패`

**해결책**:
```bash
# 기존 가상 환경 삭제
rm -rf venv

# 새로 생성
python -m venv venv --clear

# 또는 시스템 pip 업그레이드
pip install --upgrade pip setuptools virtualenv
```

</details>

<details>
<summary>🚫 패키지 설치 문제</summary>

**문제**: `패키지 설치 실패`

**해결책**:
```bash
# pip 업그레이드
pip install --upgrade pip

# 캐시 클리어
pip cache purge

# 개별 설치
pip install -r requirements_cross_platform.txt --no-cache-dir

# 또는 conda 사용
conda env create -f environment.yml
```

</details>

### 🔧 **플랫폼별 문제 해결**

#### Windows 문제들
```powershell
# Windows Defender 예외 추가
Add-MpPreference -ExclusionPath "C:\path\to\blog-automation"

# 실행 정책 변경
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Visual C++ 재배포 패키지 설치 필요시
# https://docs.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
```

#### macOS 문제들
```bash
# Gatekeeper 비활성화 (임시)
sudo spctl --master-disable

# 개발자 도구 설치
xcode-select --install

# Homebrew 설치 (필요시)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 🔋 절전 모드 수동 제어 (필요시)
# 절전 모드 완전 비활성화
sudo pmset -a sleep 0

# 디스플레이만 30분 후 끄기
sudo pmset -a displaysleep 30

# 설정 확인
pmset -g
```

**💡 절전 모드 방지 기능**
- 프로그램이 **자동으로 절전 모드를 방지**합니다
- `caffeinate` 명령어를 사용하여 맥북이 잠들지 않게 합니다
- 프로그램 종료 시 **자동으로 절전 모드 방지가 해제**됩니다
- 수동으로 절전 설정을 변경할 필요가 없습니다

#### Linux 문제들
```bash
# 시스템 의존성 설치 (Ubuntu/Debian)
sudo apt install build-essential python3-dev libffi-dev libssl-dev

# 시스템 의존성 설치 (CentOS/RHEL)
sudo dnf groupinstall "Development Tools"
sudo dnf install python3-devel libffi-devel openssl-devel

# GUI 라이브러리 설치 (필요시)
sudo apt install python3-tk  # Ubuntu/Debian
sudo dnf install tkinter      # CentOS/RHEL
```

## 📞 기술 지원

### 🆘 **지원 요청**

문제가 해결되지 않으면 다음 정보와 함께 문의해주세요:

1. **운영체제 및 버전**
2. **Python 버전**
3. **오류 메시지 전체**
4. **실행 환경** (가상환경, 시스템 Python 등)

### 📧 **연락처**

- **라이온 개발팀**
- **이관원**: 010-7282-5529
- **이예린**: 010-3852-5339

### 🔗 **유용한 링크**

- [Python 공식 다운로드](https://www.python.org/downloads/)
- [Git 설치 가이드](https://git-scm.com/downloads)
- [Chrome 브라우저 다운로드](https://www.google.com/chrome/)
- [Visual Studio Code](https://code.visualstudio.com/) (개발용)

## 📈 **성능 최적화**

### 🚀 **시스템 요구사항**

| 구분 | 최소 | 권장 |
|-----|------|------|
| **RAM** | 4GB | 8GB+ |
| **저장공간** | 2GB | 5GB+ |
| **네트워크** | 10Mbps | 50Mbps+ |
| **Python** | 3.8 | 3.9+ |

### ⚡ **최적화 팁**

1. **SSD 사용** - 응답 속도 향상
2. **충분한 RAM** - 메모리 스왑 방지
3. **빠른 인터넷** - 업로드 속도 향상
4. **최신 Chrome** - 호환성 보장

## 📚 **추가 학습 자료**

### 🎓 **초보자용**
- [Python 기초 튜토리얼](https://docs.python.org/ko/3/tutorial/)
- [가상환경 사용법](https://docs.python.org/ko/3/tutorial/venv.html)
- [블로그 운영 가이드](#)

### 🔬 **고급 사용자용**
- [Selenium 자동화](https://selenium-python.readthedocs.io/)
- [PyInstaller 사용법](https://pyinstaller.readthedocs.io/)
- [크로스 플랫폼 개발](https://docs.python.org/3/library/platform.html)

---

## 📄 **라이선스**

이 소프트웨어는 라이온 개발팀에서 개발되었습니다.

© 2025 라이온 개발팀. All rights reserved.

---

**🎉 이제 모든 플랫폼에서 블로그 자동화를 즐기세요!** 