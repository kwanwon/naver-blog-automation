# 네이버 블로그 자동화 도구

![버전](https://img.shields.io/badge/버전-1.0.0-blue)
![플랫폼](https://img.shields.io/badge/플랫폼-macOS-lightgrey)
![언어](https://img.shields.io/badge/언어-Python-green)

GPT를 활용한 네이버 블로그 콘텐츠 자동 생성 및 포스팅 도구입니다.

## 주요 기능

- GPT-4를 활용한 고품질 블로그 콘텐츠 자동 생성
- 네이버 블로그 자동 로그인 및 포스팅
- 이미지 자동 삽입 및 관리
- 태그 자동 생성
- 지도/위치 정보 자동 삽입
- 카카오톡 링크 자동 삽입
- 자동 업데이트 기능

## 시스템 요구사항

- macOS 11.0 이상
- 인터넷 연결
- GPT API 키
- 네이버 계정

## 설치 방법

1. [최신 릴리즈](https://github.com/yourusername/naver-blog-automation/releases/latest)에서 DMG 파일을 다운로드합니다.
2. DMG 파일을 마운트하고 애플리케이션을 응용 프로그램 폴더로 드래그합니다.
3. 첫 실행 시 GPT API 키와 네이버 계정 정보를 설정합니다.

## 사용 방법

1. 애플리케이션을 실행합니다.
2. 주제를 입력하고 GPT 글 생성 버튼을 클릭합니다.
3. 생성된 글을 검토하고 필요시 수정합니다.
4. 삽입할 이미지를 선택하거나 기본 이미지를 사용합니다.
5. 네이버 블로그에 발행 버튼을 클릭합니다.

자세한 사용법은 [사용자 가이드](https://github.com/yourusername/naver-blog-automation/wiki)를 참고해주세요.

## 개발 환경 설정

개발 환경을 설정하려면 다음 단계를 따르세요:

```bash
# 저장소 클론
git clone https://github.com/yourusername/naver-blog-automation.git
cd naver-blog-automation

# 가상 환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# .env 파일 생성
cp .env.example .env
# .env 파일을 편집하여 API 키 등 설정

# 애플리케이션 실행
python blog_writer_app.py
```

## 빌드 방법

애플리케이션을 빌드하려면 다음 명령어를 실행하세요:

```bash
# 앱 빌드
python build.py

# 설치 프로그램 생성
python create_installer.py
```

생성된 DMG 파일은 `installer` 폴더에서 찾을 수 있습니다.

## 기여 방법

1. 이 저장소를 포크합니다.
2. 새 브랜치를 생성합니다: `git checkout -b feature/amazing-feature`
3. 변경사항을 커밋합니다: `git commit -m '새로운 기능 추가'`
4. 브랜치에 푸시합니다: `git push origin feature/amazing-feature`
5. Pull Request를 생성합니다.

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.

## 연락처

문의사항이나 피드백은 [이슈](https://github.com/yourusername/naver-blog-automation/issues)를 통해 알려주세요. 