# 🦁 프로젝트 개발 아카이브 (ARCHIVE.md)

이 문서는 토큰 효율성을 위해 오래된 개발 기록 및 히스토리를 보관하는 **'과거 로직 창고'**입니다. 
관장님께서는 이 파일을 직접 보실 필요가 없으며, 제가 과거의 복잡했던 코드를 참고해야 할 때만 들여다보는 용도입니다.

---

### 📅 최근 이관 기록 (Latest Migration)

#### 2026-05-05 (플랫폼 로직 대이관)
- **대상**: `blog_writer_app.py` 내에 존재하던 구버전 통합 텍스트 처리 및 태그 병합 로직.
- **사유**: 플랫폼별 독립성 확보를 위해 `modules/pipelines/`로 기능을 분리하며, 기존 코드는 더 이상 사용하지 않으므로 아카이브함.

---

## 📅 과거 세션 기록 (Legacy Logs)

### [실패 기록] 2026-05-08~09: 밴드 감지 모드 품질 이슈
- **주요 현상**:
    - 본문 소실: `[4시부] 한체대 라이온입니다.` (인사말 외 내용 없음)
    - 기호 노출: `, 대회연습, 호신술...` (나열식, 문장 시작 콤마 발생)
- **교훈 및 방지 대책**:
    - AI 지침 설계 시 '생략(Omit)' 규칙은 데이터가 부족한 상황에서 본문 전체를 삭제할 위험이 있으므로 '생성 가이드'를 더 우선시해야 함.
    - 외부 데이터(Google Sheets) 정제 시 중복 단어 제거 후 반드시 양끝 기호(`.strip(' ,')`)를 정제하여 찌꺼기 노출을 방어해야 함.
    - 달력형 시트 구조에서는 고정 인덱스가 아닌 요일명(월~금) 기반의 동적 열 매칭이 필수임.

### 2026-04-21 (세션 2)
- **팀 재가동**: PM(대장), Coder(지휘관), Tester(검수관), Recorder(기록원) 체제 복구.
- **사고 복구**: 이전 작업자의 실수로 삭제된 `gpt_handler.py` 등 핵심 파일 7종을 v1.2.126 버전으로 롤백 완료.
- **정상화**: 마케팅 댓글 바보화 및 시작 버튼 작동 중단 현상 해결.

### 2026-04-17 (세션 1)
- **밴드 포스팅 오류 분석**: `DriveAutoPostSystem` -> `GoogleSheetsReader` 경로의 수련 주제 추출 오류 해결.
- **URL 참조**: 정확한 참조를 위해 `#gid=1351962847` 포함 URL 사용 권장.
- **월별 탭 설계**: `1월`~`12월` 명칭의 탭 지원 및 자동 전환 기능 수립.

---

## 🛠️ 초기 개발 컨텍스트 (v1.2.126 기준)

### 🚑 긴급 수정 사항
- **실행 불가 버그**: `idle_activity.py`의 들여쓰기 및 `blog_writer_app.py`의 인코딩(UTF-8) 충돌 해결.
- **보안 대응**: macOS 인터넷 다운로드 파일 보안 차단 해제 가이드 적용.

### 🛡️ 핵심 보안 및 라이선스
- **로컬 만료일 체크**: 서버 연결 없이도 로컬 만료일 기반 사용 차단 로직 적용.
- **오프라인 유예**: 서버 연결 실패 시 마지막 인증 후 14일간 사용 허용.

### 🤝 이웃 소통 개선
- **필터링**: 광고글/날씨 관련 키워드 차단.
- **안정화**: 150자 제한 및 자연스러운 문장 마무리(중복 방지) 적용.

---
*(이전 기록 종료)*
# 🦁 라이온 개발자: 네이버 자동화 시스템 히스토리 (History)

## 📊 전담 부대 시스템 아키텍처 및 흐름 분석 보고서 (2026-04-26)

관장님, 현재 시스템의 전체 흐름과 최근 반복되는 문제의 원인을 꼼꼼히 파악하여 보고합니다. **(이 보고서는 파악용이며, 코드 수정은 포함되어 있지 않습니다.)**

### 1. 시스템 구조 및 데이터 흐름
현재 프로그램은 다음과 같은 4단계 구조로 유기적으로 연결되어 있습니다.

1.  **지휘 본부 (UI - `blog_writer_app.py`)**
    *   사용자의 명령(수동 포스팅, 시트 로드, 드라이브 감지)을 수신합니다.
    *   `config/` 폴더의 모든 설정값을 취합하여 하위 모듈로 전달하는 컨트롤러 역할을 합니다.
2.  **작전 설계 (AI - `modules/gpt_handler.py`)**
    *   콘텐츠의 '내용'을 생성하는 두뇌입니다.
    *   **지침 계층**: [공통 규칙] + [플랫폼별 지침] + [사용자 설정]을 결합하여 AI에게 전달합니다.
    *   **모델 선택**: GPT-4o-mini 또는 Gemini-2.5-flash-lite 등을 사용하여 초안을 작성합니다.
3.  **실행 부대 (Automation - `naver_xxx_auto.py`)**
    *   셀레니움(Selenium) 엔진을 사용하여 실제 브라우저를 제어합니다.
    *   생성된 텍스트와 이미지를 네이버 블로그/밴드/카페의 각 요소에 정확히 입력합니다.
4.  **지원 및 자원 (`config/`, `utils/`)**
    *   `user_settings.txt`: 슬로건, 첫 문장, 태그 등 고정 자원을 관리합니다.
    *   `gpt_settings.txt`: AI 모델 선택 및 페르소나 지침을 관리합니다.

### 2. "다람쥐 쳇바퀴" 문제 원인 분석
요청하신 "결론적으로", "잊지 마세요" 등 AI 특유의 말투가 반복되고, 한 쪽을 고치면 다른 쪽이 틀어지는 현상의 원인은 다음과 같습니다.

*   **지침의 상호 간섭 (Cross-interference)**: 현재 AI 지침이 한 파일(`gpt_handler.py`) 내에서 조건문으로 분기되어 있어, 로직이 복잡해질수록 AI가 서로 다른 플랫폼의 규칙을 혼동할 가능성이 있습니다.
*   **모델의 습성 (Model Prior)**: 제미나이(Gemini)와 같은 모델은 기본적으로 친절한 마무리를 하려는 성향이 강해, "마무리와 명언 포함"이라는 긍정 지침이 들어오면 금지어 규칙보다 우선순위를 높게 잡는 경우가 발생합니다.
*   **단일 지침 체계**: 현재 AI 지침 파일이 논리적으로 하나(`gpt_settings.txt`)에 통합되어 있어, 플랫폼별 독립성을 보장하기 어려운 구조입니다.

### 3. 향후 개편 방향 (관장님 확인용)
*   **용어 및 파일명 통일**: `GPT`라는 용어를 `AI`로 통합하여 `AI 설정` UI 및 `ai_handler.py`로 변경할 계획입니다.
*   **지침 격리 (Isolation)**: 플랫폼별(블로그/밴드/카페) 지침을 완전히 독립된 파일로 분리하여, 하나를 수정해도 다른 플랫폼에 영향이 가지 않도록 물리적으로 격리하는 것을 검토 중입니다.
*   **모델별 맞춤 지침**: 지침을 잘 따르는 GPT와 창의적인 Gemini의 특성에 맞춰, 모델별로 지침의 강도를 다르게 설정하는 전략이 필요합니다.

## 📅 2026-04-26 (세션 5 - 현재)
### 🎖️ 주요 성과: 시스템 명칭 개편 및 구조 안정화 (1단계 완료)
- **[2026-04-26] GPT -> AI 명칭 통합 및 리팩토링**
    - **파일 및 클래스 개편**: `gpt_handler.py`를 `ai_handler.py`로, `GPTHandler`를 `AIHandler`로 변경하여 특정 모델에 국한되지 않는 구조 확립.
    - **설정 파일 마이그레이션**: `gpt_settings.txt`를 `ai_settings.txt`로 변경하고 관련 경로 유틸리티(`path_utils.py`) 업데이트 완료.
- **[2026-04-26] 2단계: 지침 격리 및 외부화 완료**
    - **외부 지침 파일 생성**: `config/` 폴더 내에 `rules_common.txt`, `rules_blog.txt`, `rules_band.txt`, `rules_cafe.txt` 파일을 생성하여 플랫폼별 규칙을 물리적으로 격리했습니다.
    - **동적 로딩 시스템**: `ai_handler.py`가 실행 시점에 플랫폼(블로그, 밴드, 카페)을 판단하여 해당 지침만 골라서 읽어오도록 로직을 수정했습니다.
    - **효과**: 이제 블로그 지침을 수정해도 밴드나 카페의 말투가 변하는 '간섭 현상'이 원천적으로 차단됩니다.
- 이전 기록은 [ARCHIVE.md](file:///Users/gm2hapkido/Desktop/라이온개발자/ARCHIVE.md)에서 확인하십시오.

---

## 📅 2026-04-25 (세션 4 - 현재)
### 🎖️ 주요 성과: 로그인 안정화 설계 및 밴드 포맷 최적화
- **[2026-04-25] Naver Band 포스팅 최적화 및 구조 정립**
    - **밴드 분량 축소**: 모바일 가독성 향상을 위해 밴드 및 자동 포스팅 글자 수를 200~300자로 대폭 축소.
    - **저녁 포스팅 고도화**: 밴드 저녁(`closing`) 포스팅 시 내일의 기온 및 미세먼지 정보를 정확히 주입하고, AI가 자연스럽고 다양한 마무리 인사를 하도록 프롬프트 개선. (상투적인 '옷차림' 멘트 지양)
    - **게시글 구조 정립**: `blog_writer_app.py`에서 `[본문] -> [슬로건] -> [태그]` 순서로 고정되도록 통합 포맷터(`_get_formatted_content`) 강화.
    - **슬로건 로직 분리**: `gpt_handler.py`의 자동 슬로건 삽입을 블로그 전용으로 제한하고, 밴드/카페는 앱 단에서 최종 조립하도록 분리하여 순서 혼선 해결.
    - **코드 및 데이터 정제**: `gpt_handler.py` 내부의 '음악줄넘기' 관련 하드코딩 지침과 보조활동 분류 로직을 제거하여 주제별 유연성을 확보했습니다.
- **레거시 제거**: 중복되거나 오래된 페르소나 정보가 포함된 구 폴더(`블로그자동화`)를 삭제하여 데이터 간섭을 차단했습니다.
    - **태그 로직 정교화**: 블로그는 고정 태그 우선, 밴드/카페는 AI 태그가 우선적으로 배치되도록 플랫폼별 특성을 반영했습니다.
    - **블로그 본문 최적화**: 블로그 본문 하단에 해시태그가 중복 노출되던 문제를 해결하고, GPT 지침 수정을 통해 본문 내 과도한 홍보 문구를 차단하여 '정보성'을 강화했습니다.
    - **플랫폼별 로직 분리**: 블로그는 태그 전용 필드 사용, 밴드/카페는 본문 하단 삽입으로 플랫폼별 전송 방식을 완벽히 정립했습니다.
    - **로그인 가이드 적용**: 메인 UI 및 로그인 알림창에 "로그인 상태 유지 체크 필수" 안내 문구를 삽입하여 사용자 실수를 방지했습니다.
- **[2026-04-26] 플랫폼별 톤앤매너 최적화 및 사용자 설정 동기화**
    - **블로그 말투 개편**: 블로그를 '친근한 이웃' 느낌으로 전환하기 위해 모든 격식체(~합니다)를 배제하고 친근한 말투(**~해요/네요**)를 100% 적용했습니다.
    - **밴드/카페 균형**: 신뢰감과 친근함의 공존을 위해 격식체와 친근체를 **5:5 비율**로 섞어 작성하도록 지침을 고도화했습니다.
    - **고정 문구 수정**: AI 생성 본문뿐만 아니라, `user_settings.txt`의 **고정 첫 인사 문구**도 각 플랫폼의 새로운 톤에 맞춰 친근하게 수정 완료했습니다.

---

## 📅 2026-04-24 (세션 3)
### 🎖️ 주요 성과: 통합 감지 모드 및 스케줄러 안정화
- **[2026-04-24] 블로그 고정 태그 동기화 및 우선순위 수정 완료**
    - 블로그 포스팅 시 사용자 프로필 설정(`user_settings.txt`)에 저장된 **고정 태그 15개**를 정확히 로드하도록 경로를 수정했습니다.
    - 고정 태그를 AI 태그보다 **무조건 먼저** 배치하여 관장님의 브랜딩 태그가 강조되도록 보장했습니다.
- **플랫폼 통합 태그 시스템 구축**: 모든 경로에서 AI 태그가 무시되거나 반복되던 문제를 해결하고, [고정 태그 + AI 맞춤 태그 + 본문 키워드]가 조화롭게 섞이도록 개선했습니다.

---
*(과거 기록은 ARCHIVE.md로 이동되었습니다)*
# 🦁 현재 업무 진행 상황 (status.md)

## 📌 시스템 개요
- **대장(PM)**: Antigravity (전략 및 지침 관리)
- **지휘관(Coder)**: Antigravity (Python 핵심 로직 구현)
- **검수관(Tester)**: Antigravity (코드 안정성 및 동작 확인)
- **기록원(Recorder)**: Antigravity (history.md 및 status.md 최신화)

## 🎖️ 현재 진행 중인 미션
- [x] **브라우저 프로필 통합**: 모든 모듈이 단일 세션을 공유하여 로그인 유지력 강화
- [x] **블로그 본문 태그 삽입 차단 및 별도 필드 처리 고정**
- [x] **블로그 정보성 콘텐츠 강화 (홍보 문구 본문 노출 제한 로직 적용)**
- [x] **밴드/카페 포스팅 피드백 반영 및 안정화 완료**
- [x] **플랫폼별 톤앤매너 최적화**: 블로그(친근한 이웃 말투), 밴드/카페(5:5 혼합 말투) 적용 완료

## 🚀 최근 활성화된 기능
- ✅ **태그 동기화**: `user_settings.txt` 고정 태그(15개) 우선 반영 및 AI 태그 병합 완료.
- ✅ **게시글 구조 최적화**: 밴드/카페 [본문] -> [슬로건] -> [해시태그] 순서 적용 완료.
- ✅ **밴드 분량 최적화**: 모바일 가독성을 위해 밴드 포스팅 분량을 200~300자로 축소 완료.
- ✅ **저녁 포스팅 고도화**: 밴드 저녁 포스팅 시 '내일 날씨(기온/미세먼지)' 정보를 정확히 반영한 자연스러운 마무리 인사 구현 완료.
- ✅ **로그인 안정화**: 모든 모듈의 브라우저 프로필을 `naver_automation_profile`로 통합 완료.
- ✅ **사용자 가이드**: 로그인 시 "로그인 상태 유지" 체크 안내 UI 적용 완료.

## 🎖️ 최근 작업 결과 (2026-04-26)
- **[2단계] 지침 격리 및 외부화 (완료)**: 플랫폼별 독립 지침 파일을 생성하고 동적 로딩 로직을 구현했습니다.
    - `config/rules_common.txt`: 공통 금지어 및 품질 규칙.
    - `config/rules_blog.txt`: 블로그용 친근한 말투 지침.
    - `config/rules_band.txt`, `rules_cafe.txt`: 밴드/카페용 신뢰+친근 혼합 지침.
    - `AIHandler`에서 플랫폼에 따라 해당 파일을 자동으로 읽어오도록 수정 완료.
- **[진행 중] 3단계: 부정 제약(Negative Constraint) 강화**: AI의 고질적인 습관("잊지 마세요" 등)을 원천 차단하는 로직 강화.
- ✅ **플랫폼별 특성화**: 
    - **블로그**: 고정 태그 우선 + 본문 내 태그 제외 + 정보성 중심 + **친근한 이웃 말투(~해요/네요)**.
    - **밴드/카페**: AI 태그 우선 + 본문 내 태그 포함 + 긴밀한 소통 위주 + **신뢰/친근 혼합 말투(5:5)**.

---
*과거 히스토리는 [ARCHIVE.md](file:///Users/gm2hapkido/Desktop/라이온개발자/ARCHIVE.md)를 참조하십시오.*
# 블로그 가독성 및 카페 UI 개선 인수인계 보고서

## 1. 지금까지 완료된 작업
- **카페 UI 개선**: 드라이브 감지 설정(폴더 경로, 시작/중지 버튼)을 [외부 연동 설정] 구역으로 분리하여, 이미지 삽입 모드를 '자동'으로 설정해도 항상 보이도록 수정 완료.
- **글쓰기 지침 갱신**: `rules_blog.txt` 및 `rules_common.txt` 파일을 가독성 중심으로 수정. (1~2문장마다 줄바꿈, '첫째로' 등 나열어 뒤에 빈 줄 추가 등)

## 2. 새 채팅창에서 즉시 실행할 작업 (남은 과제)
- **가독성 엔진 필터 장착 (`modules/ai_handler.py`)**: 
    - AI가 생성한 텍스트에서 '첫째로,', '둘째로,', '마지막으로,' 키워드를 감지하여 앞뒤로 빈 줄(엔터 2번)을 자동 삽입하는 로직 추가.
    - 문단이 너무 길 경우 강제로 1~2문장 단위로 나누는 보정 필터 적용.
- **첫 문장 연결부 개선 (`blog_writer_app.py`)**: 
    - 관장님이 설정한 [인사말(첫 문장)]과 [AI 본문] 사이의 줄바꿈이 어색하게 끊기지 않고 자연스러운 흐름(2줄 띄우기 유지)을 갖도록 결합 로직 최적화.

## 3. 적용 대상
- 일반 포스팅, 드라이브 감지 포스팅, 스케줄러 포스팅, 예약 포스팅 전반에 통합 적용.

---
**관장님, 새 채팅창을 열고 "인수인계 보고서 확인하고 작업 마무리해줘"라고 말씀해 주세요!**


--- ARCHIVED DOCUMENTATION (2026-04-29 CLEANUP) ---

### Archiving: CURSOR_WINDOWS_SETUP.md
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

---

### Archiving: DEVELOPER_GUIDE.md
# 🚀 개발자 가이드 - 자동 업데이트 시스템

## 📋 개요

이 프로젝트는 **자동 업데이트 시스템**이 구축되어 있어, 개발자가 코드를 수정하고 GitHub에 push하면 사용자들이 자동으로 업데이트를 받을 수 있습니다.

## 🔄 자동 업데이트 워크플로우

### 1. 개발자 작업 흐름
```bash
# 1. 코드 수정
git add .
git commit -m "🔧 새로운 기능 추가"  # 일반 커밋 (PATCH 버전 증가)
git push origin main

# 2. 자동으로 실행되는 작업들:
# - GitHub Actions가 자동으로 버전 증가 (1.1.0 → 1.1.1)
# - version.json 파일 자동 업데이트
# - GitHub Release 자동 생성
# - 사용자들은 다음 프로그램 실행 시 업데이트 알림 받음
```

### 2. 버전 관리 규칙

커밋 메시지에 태그를 추가하여 버전 증가 유형을 지정할 수 있습니다:

- **PATCH 증가** (기본): 일반 커밋
  ```bash
  git commit -m "🐛 버그 수정"
  git commit -m "✨ 작은 기능 개선"
  ```

- **MINOR 증가**: `[MINOR]` 태그 추가
  ```bash
  git commit -m "[MINOR] ✨ 새로운 기능 추가"
  git commit -m "[MINOR] 🔧 UI 개선"
  ```

- **MAJOR 증가**: `[MAJOR]` 태그 추가
  ```bash
  git commit -m "[MAJOR] 💥 대규모 변경사항"
  git commit -m "[MAJOR] 🔄 전체 구조 변경"
  ```

### 3. 자동 업데이트 건너뛰기

특정 커밋에서 자동 버전 증가를 건너뛰려면:
```bash
git commit -m "📝 문서 업데이트 [skip-version]"
git commit -m "🔧 설정 파일 수정 [skip-version]"
```

## 🛠️ 개발 환경 설정

### 1. 개발자 모드 활성화
```bash
# 개발자 모드로 실행 (시리얼 인증 우회)
export DEVELOPER_MODE=true
export SKIP_SERIAL_AUTH=true
python blog_writer_app.py
```

### 2. 개발자 빌드 생성
```bash
# 개발자용 빌드 (시리얼 인증 없음)
python build_developer.py

# 배포용 빌드 (시리얼 인증 필요)
python build_release.py
```

## 📦 배포 프로세스

### 자동 배포 (권장)
1. 코드 수정 후 GitHub에 push
2. 자동으로 버전 증가 및 릴리스 생성
3. 사용자들이 자동으로 업데이트 알림 받음

### 수동 배포 (필요시)
```bash
# 1. 버전 수동 업데이트
# version.json 파일에서 버전 번호 수정

# 2. GitHub에 push
git add version.json
git commit -m "🔄 버전 업데이트: v1.2.0 [skip-version]"
git push origin main

# 3. GitHub Release 수동 생성 (선택사항)
```

## 🔍 업데이트 시스템 작동 방식

### 1. 사용자 관점
- 프로그램 시작 시 자동으로 업데이트 확인
- 새 버전 발견 시 알림 표시
- "지금 업데이트" / "나중에" / "이 버전 건너뛰기" 선택 가능
- 업데이트 시 모든 설정과 데이터 자동 보존
- 실패 시 자동으로 이전 버전으로 롤백

### 2. 기술적 구현
- **GitHub Actions**: 자동 버전 관리 및 릴리스
- **AutoUpdater 모듈**: 안전한 업데이트 프로세스
- **백업/복원 시스템**: 업데이트 실패 시 자동 롤백
- **사용자 친화적 UI**: 직관적인 업데이트 알림

## 🚨 주의사항

### 1. 성능 영향 최소화
- 업데이트 확인은 백그라운드에서 실행
- 네트워크 타임아웃 최적화 (8초)
- 빠른 네트워크 연결 확인

### 2. 안전성 보장
- 업데이트 전 자동 백업 생성
- 실패 시 자동 롤백
- 사용자 데이터 보존
- 단계별 오류 처리

### 3. 사용자 경험
- 비침습적 알림 (8초간 표시)
- 명확한 변경사항 표시
- 선택적 업데이트 (강제 없음)
- 버전 건너뛰기 기능

## 🔧 문제 해결

### 1. 자동 버전 증가가 작동하지 않는 경우
- GitHub Actions 워크플로우 상태 확인
- 커밋 메시지에 `[skip-version]` 태그가 있는지 확인
- GitHub 저장소 권한 확인

### 2. 사용자가 업데이트를 받지 못하는 경우
- 네트워크 연결 상태 확인
- GitHub 저장소 접근 가능 여부 확인
- version.json 파일 형식 확인

### 3. 업데이트 실패 시
- 자동 롤백 기능이 작동하는지 확인
- 백업 폴더 존재 여부 확인
- 로그 파일에서 상세 오류 확인

## 📊 모니터링

### 1. 업데이트 성공률 추적
- GitHub Actions 실행 상태 모니터링
- 사용자 피드백 수집
- 오류 로그 분석

### 2. 성능 모니터링
- 업데이트 확인 속도
- 다운로드 속도
- 백업/복원 시간

## 🎯 향후 개선 계획

1. **실시간 업데이트 알림**: 웹훅 기반 즉시 알림
2. **A/B 테스트**: 점진적 배포 시스템
3. **사용자 분석**: 업데이트 패턴 분석
4. **자동 테스트**: 업데이트 전 자동 검증

---

## 📞 지원

문제가 발생하거나 개선 제안이 있으시면 GitHub Issues를 통해 연락해주세요.

**Happy Coding! 🚀**

---

### Archiving: EXECUTION_GUIDE.md
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

---

### Archiving: Google_Drive_Setup_Guide.md
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

---

### Archiving: INSTALL.md
# 네이버 블로그 자동화 설치 안내

이 문서는 네이버 블로그 자동화 프로그램의 설치 및 사용 방법을 안내합니다.

## 시스템 요구사항

- macOS 11.0 이상
- Windows 10 이상 (64비트)
- 인터넷 연결
- Chrome 브라우저 (최신 버전 권장)

## 설치 방법

### 직접 실행파일 사용하기 (권장)

1. 제공된 `.app` 파일(macOS) 또는 `.exe` 파일(Windows)을 다운로드합니다.
2. 바탕화면이나 원하는 위치로 복사합니다.
3. 아이콘을 클릭하여 프로그램을 실행합니다.

### 소스코드에서 빌드하기

1. Python 3.9 이상이 설치되어 있어야 합니다.
2. 필요한 패키지를 설치합니다:
   ```
   pip install -r requirements.txt
   ```
3. 빌드 스크립트를 실행합니다:
   ```
   python build.py
   ```
4. 빌드 완료 후 `dist` 폴더에서 생성된 애플리케이션을 찾을 수 있습니다.

## 첫 실행 시 주의사항

1. macOS에서는 처음 실행 시 개발자 확인 경고가 표시될 수 있습니다.
   - 시스템 환경설정 > 보안 및 개인 정보 보호로 이동하여 "확인 없이 열기" 버튼을 클릭합니다.

2. Windows에서는 SmartScreen 경고가 표시될 수 있습니다.
   - "추가 정보" 클릭 후 "실행" 버튼을 클릭합니다.

3. 프로그램이 처음 실행될 때 Chrome 웹드라이버를 다운로드할 수 있습니다. 인터넷 연결이 필요합니다.

## 사용 방법

1. 프로그램 실행 후 설정 화면에서 네이버 블로그 계정 정보를 입력합니다.
2. 태권도장 정보와 기타 설정을 구성합니다.
3. "블로그 작성 시작" 버튼을 클릭하여 자동화를 시작합니다.

## 주의사항

- 프로그램 실행 중에는 Chrome 브라우저를 조작하지 마세요.
- 일부 네이버 보안 정책에 따라 로그인 과정에서 CAPTCHA나 추가 인증이 필요할 수 있습니다.
- 프로그램이 작동하는 동안 컴퓨터가 절전 모드로 전환되지 않도록 해주세요.

## 문제해결

문제가 발생하면 config 폴더의 로그 파일을 확인하거나 개발자에게 문의하세요. 
---

### Archiving: README.md
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
---

### Archiving: README_CROSS_PLATFORM.md
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
---

### Archiving: README_WINDOWS.md
# 🪟 Windows 환경 작업 가이드

## 🚀 빠른 시작 (3분 완료)

### 방법 A: 자동 메뉴 사용 (가장 쉬움)
```cmd
# 프로젝트 폴더에서 실행
QUICK_COMMANDS.bat
```
→ 메뉴에서 번호 선택하여 실행

### 방법 B: 단계별 실행
```cmd
# 1. 환경 설정
quick-start-windows.bat

# 2. Cursor 설정
# - Cursor 실행
# - File > Open Folder > 이 폴더 선택
# - PowerShell에서: .\mcp-setup\install-mcp-windows.ps1
# - Cursor 재시작

# 3. 프로그램 실행
.\venv\Scripts\activate
python blog_writer_app.py
```

## 📋 상세 가이드

- **실행 가이드**: `EXECUTION_GUIDE.md` ← **가장 상세한 실행 방법**
- **자동 메뉴**: `QUICK_COMMANDS.bat` ← **가장 쉬운 방법**
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

---

### Archiving: RELEASE_GUIDE_MAC.md
# 🍎 맥 사용자 실행 가이드

인터넷에서 다운로드한 앱 실행 시 "손상되었습니다" 메시지가 뜨는 경우 해결 방법:

1. **마우스 우클릭 활용**: 앱 아이콘에서 마우스 오른쪽 버튼을 누르고 **[열기]**를 선택하세요.
2. **터미널 명령어**: 터미널을 실행하고 아래 명령어를 입력하세요.
   

이것은 macOS의 보안 기능(Gatekeeper)에 의한 정상적인 차단이며, 앱의 결함이 아닙니다.
---

### Archiving: UPDATE_README.md
# 🔄 자동 업데이트 기능

블로그 자동화 프로그램에 안전한 자동 업데이트 기능이 추가되었습니다.

## ✨ 주요 기능

### 🔒 **데이터 보존**
- ✅ 시리얼 번호 (`serial_config.json`)
- ✅ 네이버 로그인 정보 (`naver_cookies.pkl`, `naver_session.json`)
- ✅ 사용자 설정 (`config.json`, `settings.json`, `user_data.json`)
- ✅ 모든 개인 데이터 안전 보존

### 🚀 **자동 업데이트**
- 프로그램 시작 시 자동으로 업데이트 확인
- 새 버전 발견 시 자동 다운로드 및 적용
- 백업 생성으로 안전한 업데이트
- 실패 시 자동 롤백

### 🛠️ **수동 업데이트**
업데이트가 필요한 경우 다음 방법으로 수동 실행 가능:

#### **Windows:**
```bash
update.bat
```

#### **macOS/Linux:**
```bash
./update.command
```

#### **Python 직접 실행:**
```bash
python update.py
```

## 📋 **업데이트 과정**

1. **백업 생성** - 현재 버전을 안전하게 백업
2. **데이터 보존** - 중요한 설정 파일들을 임시 저장
3. **새 버전 다운로드** - 깃허브에서 최신 코드 다운로드
4. **코드 업데이트** - 프로그램 파일만 교체
5. **데이터 복원** - 보존된 설정 파일들을 복원
6. **완료** - 업데이트된 프로그램 실행

## ⚠️ **주의사항**

### ✅ **안전한 것들:**
- 시리얼 번호는 절대 초기화되지 않음
- 로그인 정보 유지됨
- 모든 설정 보존됨
- 자동 백업으로 롤백 가능

### ❌ **업데이트 중 하지 말 것:**
- 프로그램 강제 종료
- 컴퓨터 종료
- 네트워크 연결 끊기

## 🔧 **문제 해결**

### **업데이트 실패 시:**
1. 인터넷 연결 확인
2. `update.py` 수동 실행
3. 백업 폴더에서 이전 버전 복원

### **백업 위치:**
```
블로그자동화/config/naver-blog-automation/backups/
```

### **로그 파일:**
```
블로그자동화/config/naver-blog-automation/auto_update.log
```

## 📞 **지원**

문제가 지속되면:
- 로그 파일 확인
- 백업에서 복원
- 개발자에게 문의

---

**🎉 이제 안전하고 편리한 자동 업데이트를 즐기세요!**

---

### Archiving: UPDATE_SUMMARY.md

### v1.2.126 (2026-04-16)
- 🚑 **[Hotfix]**: 맥/윈도우 앱 실행 불가 현상 (Syntax & Indentation Error) 긴급 수정
- 🛠️ **[Fix]**: 이웃소통 중단 버그 수정 + 내 댓글 중복 방지 추가
- 🐛 **[Fix]**: 광고글 스킵 로직 개선 및 interaction_count 데이터 불일치 수정
- ✅ **[New]**: 이웃 글 방문 시 내 댓글이 이미 있으면 자동 스킵 (중복 댓글 방지)

### v1.2.124 (2026-04-14)
- 🚀 **[Stability]**: 이웃소통 날씨언급 금지 + 광고글 필터링 + 댓글 잘림 방지
- 🚀 **[Stability]**: 시리얼 인증 안정화 및 서버 슬립 대응 개선
- 🛡️ **[Serial]**: 만료일 로컬 체크 추가 (서버 없이도 즉시 차단 가능)
- ⏰ **[Serial]**: 오프라인 허용 기간 7일 → 14일 연장 (안정성 강화)

### v1.2.122 (2026-04-10)
- 🚀 **[Persona]**: 이웃 소통 방문 유도 멘트 제거 및 지역 마케팅 중복 방지 강화
- 🛡️ **[Anti-Spam]**: '제 블로그에도 놀러오세요' 강제 추가 로직 전면 삭제
- 🛡️ **[Anti-Spam]**: 지역 마케팅 URL 정규화 로직 고도화 (PC/모바일/쿼리 주소 완벽 대응)
- ✨ **[Persona]**: 이웃 소통 예시 문구를 자연스러운 공감형 멘트로 교체
- 🛡️ **[Anti-Hallucination]**: 하드코딩 지명 삭제 및 사용자 설정 지역명 동적 연동
- 🛡️ **[Anti-Hallucination]**: 4월을 가을로 인식하던 계절감 오류 수정
- 🥋 **[Neutrality]**: 특정 종목(태권도/합기도) 하드코딩 삭제 → 설정 데이터 100% 참조
- 🏢 **[Neutrality]**: 기본 도장 상호명 '라이온태권도' → '라이온짐'으로 중립화

### v1.2.100 (2026-03-25)
- 🚀 **[Feature]**: 네이버 블로그 '링크' 및 '장소' 버튼 인식율 대폭 개선 (JS 검색 도입)
- 🔧 **[Improvement]**: 장소 검색 시 상호명 위주로 검색하여 정확도 향상
- ✨ **[New]**: 드라이브 자동 포스팅 'Double Check' (폴더 전체 스캔) 기능 추가
- 🔧 **[System]**: 오토 업데이트 런처 (Launcher) 추가 및 안정화
- 🔧 **[Reply]**: 답글 크롤러 개선 (알림 센터 소싱 방식 고도화)

... (생략된 내역은 version.json 참조)

### v1.2.68 (2026-02-06)
- **[Band] 포스팅 줄바꿈 문제 해결**: macOS 클립보드 복사 로직 개선 (Native pbcopy 우선 사용) 및 JS 텍스트 삽입 폴백 강화.
- **[Reply] 답글 생성 로직 개선**:
  - 텍스트 없는 이모티콘/사진 댓글에 대한 대응 능력 강화.
  - "좋은 하루 되세요" 등 반복적인 인사 문구 최소화.
- **[Map] 장소 검색 개선**: 네이버 블로그 스마트에디터 장소 검색 입력 필드 인식률 향상.
- **[System] 기타 버그 수정**: 빈 사진 폴더 처리 로직 확인.

---

### Archiving: WINDOWS_SETUP_GUIDE.md
# Windows 환경 설정 가이드

## 🚀 빠른 시작 (자동 설정)

### 1단계: USB에서 Windows로 복사
```
USB → D:\naver-blog-automation\ (또는 원하는 경로)
```

### 2단계: 자동 설정 실행
```cmd
cd D:\naver-blog-automation
python setup_cross_platform.py
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
python build_developer.py
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
   python build_release.py
   ```
   - 결과: `dist\블로그자동화\` 폴더
   - 시리얼 인증 필요
   - 빈 이미지 폴더 제공

### 설치 프로그램 생성
1. 터미널에서 다음 명령 실행:
   ```cmd
   python create_installer.py
   ```
2. `installer_output\블로그자동화_Setup_v1.5.0.exe` 생성 확인 (Inno Setup 자동 연동)

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
├── build_developer.py          # 개발자용 빌드
├── build_release.py            # 배포용 빌드
├── create_installer.py         # 인스톨러 생성 스크립트
├── setup_cross_platform.py     # 자동 설정 스크립트
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

---

### Archiving: 사용자_가이드.md
# 🎉 블로그 자동화 프로그램 사용자 가이드

## 📋 목차
1. [프로그램 소개](#프로그램-소개)
2. [시스템 요구사항](#시스템-요구사항)
3. [설치 방법](#설치-방법)
4. [첫 실행 설정](#첫-실행-설정)
5. [기본 사용법](#기본-사용법)
6. [문제 해결](#문제-해결)
7. [자주 묻는 질문](#자주-묻는-질문)

---

## 🚀 프로그램 소개

**블로그 자동화 프로그램**은 OpenAI GPT API를 활용하여 네이버 블로그에 자동으로 포스팅하는 프로그램입니다.

### ✨ 주요 기능
- 🤖 **AI 기반 콘텐츠 생성**: GPT API를 사용한 고품질 블로그 포스트 자동 생성
- 📝 **네이버 블로그 자동 포스팅**: 수동 작업 없이 자동으로 포스트 업로드
- 🖼️ **이미지 자동 업로드**: 포스트에 포함된 이미지 자동 업로드 및 최적화
- 🔐 **시리얼 인증 시스템**: 안전한 사용자 인증 및 라이선스 관리
- 🔄 **자동 업데이트**: 최신 버전으로 자동 업데이트
- 🌐 **Chrome 자동 관리**: Chrome 브라우저 및 ChromeDriver 자동 설치/관리

---

## 💻 시스템 요구사항

### 필수 요구사항
- **운영체제**: Windows 10 이상 (64비트)
- **메모리**: 최소 4GB RAM (권장: 8GB 이상)
- **저장공간**: 최소 500MB 여유 공간
- **인터넷 연결**: 안정적인 인터넷 연결 필수

### 소프트웨어 요구사항
- **Chrome 브라우저**: 최신 버전 (프로그램이 자동으로 확인 및 안내)
- **ChromeDriver**: 자동으로 다운로드 및 설치됨

---

## 📥 설치 방법

### 방법 1: 설치 프로그램 사용 (권장)
1. **설치 프로그램 다운로드**
   - GitHub Releases 페이지에서 `블로그자동화_설치프로그램_vX.X.X.exe` 다운로드
   
2. **설치 실행**
   - 다운로드한 설치 프로그램을 **관리자 권한**으로 실행
   - 설치 마법사의 안내에 따라 진행
   - Chrome 설치 여부 확인 및 안내 메시지 확인

3. **설치 완료**
   - 바탕화면 또는 시작 메뉴에서 프로그램 실행

### 방법 2: ZIP 파일 사용
1. **ZIP 파일 다운로드**
   - GitHub Releases 페이지에서 `블로그자동화-Windows-vX.X.X.zip` 다운로드

2. **압축 해제**
   - 다운로드한 ZIP 파일을 원하는 폴더에 압축 해제
   - 예: `C:\Program Files\블로그자동화\`

3. **실행 파일 실행**
   - 압축 해제된 폴더에서 `블로그자동화.exe` 실행

---

## ⚙️ 첫 실행 설정

### 1. Chrome 브라우저 확인
프로그램을 처음 실행하면 Chrome 브라우저 설치 여부를 자동으로 확인합니다.

- ✅ **Chrome이 설치된 경우**: 자동으로 ChromeDriver 설정 진행
- ❌ **Chrome이 없는 경우**: Chrome 설치 안내 메시지 표시

### 2. 시리얼 번호 입력
- 프로그램 실행 시 시리얼 번호 입력 창이 나타납니다
- 발급받은 시리얼 번호를 입력하세요
- 시리얼 번호가 없으면 개발자에게 문의하세요

### 3. OpenAI API 키 설정
- **API 키 입력**: OpenAI API 키를 입력하세요
- **API 키 발급 방법**:
  1. https://platform.openai.com 접속
  2. 계정 생성 또는 로그인
  3. API Keys 메뉴에서 새 키 생성
  4. 생성된 키를 복사하여 프로그램에 입력

---

## 📖 기본 사용법

### 1. 프로그램 실행
```
바탕화면 아이콘 더블클릭 → 프로그램 실행
```

### 2. 기본 설정
1. **시리얼 번호 입력** (최초 1회)
2. **OpenAI API 키 입력** (최초 1회)
3. **Chrome 환경 설정 확인** (자동 진행)

### 3. 블로그 포스팅
1. **포스트 주제 입력**: 작성하고 싶은 블로그 포스트의 주제 입력
2. **AI 생성 요청**: "포스트 생성" 버튼 클릭
3. **내용 검토**: AI가 생성한 내용을 검토하고 필요시 수정
4. **자동 포스팅**: "포스팅" 버튼 클릭하여 네이버 블로그에 자동 업로드

### 4. 이미지 관리
- 프로그램이 자동으로 이미지를 다운로드하고 최적화합니다
- 이미지는 `default_images` 폴더에 저장됩니다

---

## 🔧 문제 해결

### 일반적인 문제들

#### 1. Chrome 브라우저 관련 문제
**문제**: "Chrome이 설치되어 있지 않습니다" 오류
**해결책**:
1. https://www.google.com/chrome/ 에서 Chrome 다운로드 및 설치
2. Chrome 설치 후 프로그램 재실행

#### 2. ChromeDriver 관련 문제
**문제**: "ChromeDriver를 찾을 수 없습니다" 오류
**해결책**:
1. 프로그램이 자동으로 ChromeDriver를 다운로드합니다
2. 인터넷 연결을 확인하세요
3. 방화벽이 다운로드를 차단하지 않는지 확인하세요
4. 프로그램을 관리자 권한으로 실행해보세요

#### 3. OpenAI API 키 문제
**문제**: "API 키가 유효하지 않습니다" 오류
**해결책**:
1. API 키를 올바르게 복사했는지 확인
2. OpenAI 계정에 충분한 크레딧이 있는지 확인
3. API 키가 만료되지 않았는지 확인

#### 4. 네이버 블로그 로그인 문제
**문제**: "네이버 블로그에 로그인할 수 없습니다" 오류
**해결책**:
1. 네이버 계정으로 수동 로그인 후 쿠키 저장
2. 브라우저에서 자동 로그인 설정 확인
3. 2단계 인증이 설정된 경우 임시로 해제

### 로그 파일 확인
문제가 지속되면 `log.txt` 파일을 확인하세요:
```
프로그램 설치 폴더/log.txt
```

---

## ❓ 자주 묻는 질문

### Q1: 프로그램이 무료인가요?
A: 프로그램 자체는 무료이지만, OpenAI API 사용에 따른 비용이 발생할 수 있습니다.

### Q2: 어떤 블로그 플랫폼을 지원하나요?
A: 현재는 네이버 블로그만 지원합니다. 추후 다른 플랫폼 지원 예정입니다.

### Q3: 오프라인에서 사용할 수 있나요?
A: 아니요. 인터넷 연결이 필수입니다. (OpenAI API 호출 및 블로그 업로드)

### Q4: 생성된 포스트를 수정할 수 있나요?
A: 네, AI가 생성한 포스트는 포스팅 전에 자유롭게 수정할 수 있습니다.

### Q5: 시리얼 번호를 잊어버렸어요.
A: 개발자에게 문의하시면 시리얼 번호를 재발급해드립니다.

### Q6: 프로그램을 삭제하려면 어떻게 하나요?
A: 
- **설치 프로그램 사용 시**: 제어판 > 프로그램 제거에서 삭제
- **ZIP 파일 사용 시**: 설치 폴더를 직접 삭제

---

## 📞 지원 및 문의

### 기술 지원
- **GitHub Issues**: https://github.com/kwanwon/naver-blog-automation/issues
- **GitHub Discussions**: https://github.com/kwanwon/naver-blog-automation/discussions

### 버그 리포트
버그를 발견하셨다면 다음 정보와 함께 리포트해주세요:
- 운영체제 버전
- 프로그램 버전
- 오류 메시지
- 재현 단계
- `log.txt` 파일 (선택사항)

### 기능 요청
새로운 기능을 제안하고 싶으시다면 GitHub Discussions에서 아이디어를 공유해주세요.

---

## 📄 라이선스 및 면책 조항

이 프로그램은 교육 및 개인 사용 목적으로 제공됩니다. 상업적 사용은 별도 문의가 필요합니다.

**면책 조항**: 이 프로그램의 사용으로 인한 어떠한 손해에 대해서도 개발자는 책임지지 않습니다. 사용자는 자신의 책임 하에 프로그램을 사용해야 합니다.

---

**🎉 즐거운 블로깅 되세요!**

*마지막 업데이트: 2025년 1월*

---

### Archiving: 사용자_가이드_v2.md
# 🚀 블로그 자동화 프로그램 상세 가이드 (초보자용)

안녕하세요! 이 가이드는 프로그램 사용이 처음이신 분들을 위해 가장 어렵게 느끼시는 **API 키 발급**과 **주소 설정** 방법을 단계별로 설명해 드립니다.

---

## 🔑 1. API 키 발급 방법 (가장 중요한 부분!)

프로그램이 AI 글쓰기를 하려면 OpenAI, Gemini 등의 서비스에서 '열쇠(API 키)'를 받아와야 합니다.

### 🤖 OpenAI API 키 (GPT-4o 등 사용)

1. **[OpenAI Platform](https://platform.openai.com/)** 에 접속하여 로그인합니다.
2. 왼쪽 메뉴에서 **API Keys** 아이콘을 클릭합니다.
3. **+ Create new secret key** 버튼을 누릅니다.
4. 키 이름(예: MyBlogBot)을 입력하고 생성합니다.
5. **주의!** 키는 한 번만 보여주니 즉시 복사해서 프로그램의 [OpenAI API 키] 칸에 입력하세요.

### ♊ Gemini API 키 (무료 모델 사용 가능)

1. **[Google AI Studio](https://aistudio.google.com/app/apikey)** 에 접속합니다.
2. **Create API key** 버튼을 클릭합니다.
3. 프로젝트를 선택하거나 새로 만들어 키를 발급받습니다.
4. 발급된 키를 프로그램의 [Gemini API 키] 칸에 입력하세요.

### 🔍 Brave Search API 키 (뉴스/정보 검색용)

1. **[Brave Search API](https://brave.com/search/api/)** 에 접속하여 회원가입합니다.
2. Plans에서 Free Plan 또는 적절한 플랜을 선택합니다.
3. API Keys 메뉴에서 새로운 키를 생성하여 프로그램에 입력합니다.

### 🌦️ 기상청 API 키 (날씨 정보용)

1. **[공공데이터포털](https://www.data.go.kr/)** 에 접속하여 로그인합니다.
2. '단기예보'를 검색하여 **[기상청_단기예보 ((구)동네예보) 조회서비스]**를 찾습니다.
3. **활용신청** 버튼을 눌러 승인을 받습니다. (즉시 승인됨)
4. 마이페이지 > 데이터활용 > 활용신청 현황에서 **인증키(Encoding/Decoding)** 중 하나를 복사하여 프로그램의 [기상청 API 키] 칸에 입력합니다.

---

## 🌐 2. 밴드 & 카페 주소 넣는 법

### 💚 네이버 밴드 URL

- 밴드에 접속한 후, 게시글을 올릴 밴드의 메인 페이지 주소를 복사합니다.
- 예시: `https://band.us/band/12345678`
- 주소 뒤에 `/post`를 붙여도 되고, 밴드 번호까지만 넣어도 프로그램이 자동으로 인식합니다.

### ☕ 네이버 카페 URL 및 메뉴 ID

1. **카페 URL**: 카페의 메인 주소를 입력합니다.
   - 예시: `https://cafe.naver.com/mycafename`
2. **메뉴 ID (중요!)**: 
   - 카페에서 글을 올리고 싶은 **게시판**을 클릭합니다.
   - 브라우저 상단 주소창을 보면 `menuId=숫자` 부분이 있습니다.
   - 이 **숫자**만 복사해서 [메뉴 ID] 칸에 입력하세요.

---

## 💻 3. 프로그램 인터페이스 설명

- **[GPT 설정] 탭**: AI의 말투(페르소나)와 지침을 설정합니다. 어떤 성격의 블로거가 될지 정하는 곳입니다.
- **[사용자 설정] 탭**: 내 도장 이름, 주소, 연락처 등 기본 정보를 입력합니다.
- **[시간 설정] 탭**: 자동으로 글이 올라갈 시간대와 간격을 설정합니다.
- **[방문소통]**: 다른 이웃 블로그에 자동으로 방문하여 좋아요와 댓글을 남겨 소통 지수를 높입니다.

---

## 💡 팁
- API 키를 입력한 후에는 반드시 **[설정 저장]** 버튼을 눌러주세요.
- 프로그램 실행 시 나타나는 **체크리스트**를 꼭 확인하고 네이버 로그인을 먼저 완료해 주세요.

문제가 생기면 언제든 개발자에게 문의해 주세요!

---


### Archiving: debug_app.log (Old Log)
2026-04-24 14:04:20,682 - INFO - 버전 확인 URL: https://raw.githubusercontent.com/kwanwon/naver-blog-automation/main/version_mac.json
2026-04-24 14:04:20,682 - AutoUpdater - INFO - 버전 확인 URL: https://raw.githubusercontent.com/kwanwon/naver-blog-automation/main/version_mac.json
ENV 파일 경로: /Users/gm2hapkido/Desktop/라이온개발자/.env
🚀 앱 시작 버전 로드: /Users/gm2hapkido/Desktop/라이온개발자/version.json (v1.2.126)
✅ 현재 최신 버전(v1.2.126)입니다.
🌍 플랫폼 감지: Darwin (arm64)
💻 운영체제: macOS-15.7.3-arm64-arm-64bit-Mach-O
📝 스크립트 모드: /Users/gm2hapkido/Desktop/라이온개발자
2026-04-24 14:04:21,284 - modules.serial_auth - INFO - 현재 base_dir: /Users/gm2hapkido/Desktop/라이온개발자/modules
2026-04-24 14:04:21,284 - modules.serial_auth - INFO - 경로 1 시도: /Users/gm2hapkido/Desktop/라이온개발자/시리얼관리/serials.db
2026-04-24 14:04:21,284 - modules.serial_auth - INFO - ✅ 시리얼 DB 발견: /Users/gm2hapkido/Desktop/라이온개발자/시리얼관리/serials.db
📁 최종 기본 디렉토리: /Users/gm2hapkido/Desktop/라이온개발자
🔄 현재 작업 디렉토리: /Users/gm2hapkido/Desktop/라이온개발자
🔄 업데이트 확인 중...📁 디렉토리 확인/생성: /Users/gm2hapkido/.blog_automation/config

🔍 버전 파일 검색 경로: ['/Users/gm2hapkido/Desktop/라이온개발자/version.json', '/Users/gm2hapkido/Desktop/라이온개발자/version.json', '/Users/gm2hapkido/Desktop/라이온개발자/version.json']
✅ 버전 파일 로드 성공: /Users/gm2hapkido/Desktop/라이온개발자/version.json (v1.2.126)
2026-04-24 14:04:21,285 - INFO - 버전 확인 URL: https://raw.githubusercontent.com/kwanwon/naver-blog-automation/main/version_mac.json
2026-04-24 14:04:21,285 - AutoUpdater - INFO - 버전 확인 URL: https://raw.githubusercontent.com/kwanwon/naver-blog-automation/main/version_mac.json
📁 디렉토리 확인/생성: /Users/gm2hapkido/.blog_automation/drafts
📁 디렉토리 확인/생성: /Users/gm2hapkido/.blog_automation/settings
📁 디렉토리 확인/생성: /Users/gm2hapkido/.blog_automation/logs
📋 기본 디렉토리 내용: ['chrome_data', 'settings', 'temp', 'config', 'drafts', 'serial_config.json', 'logs', 'data']
GPT 설정 파일 로드 성공: /Users/gm2hapkido/.blog_automation/config/gpt_settings.txt
2026-04-24 14:04:21,337 - modules.gpt_handler - INFO - GPT 설정 파일에서 API 키를 로드했습니다.
✅ 현재 버전이 최신입니다.
2026-04-24 14:04:21,408 - modules.gpt_handler - INFO - OpenAI 클라이언트 초기화 성공 (new SDK)
커스텀 프롬프트 파일 로드 성공: /Users/gm2hapkido/Desktop/라이온개발자/config/custom_prompts.txt
2026-04-24 14:04:21,409 - modules.gpt_handler - INFO - 📊 [AI 사용량 체크] Flash: 0/990회 | Lite: 11/990회 (오늘 누적)
📂 AI 사용 로그 로드: 71건
🔄 자동 정리 스케줄러 시작됨 (매 6시간)🧹 12시간 이상 된 백업 정리 중...

   기준 시간: 2026-04-24 02:04:21
ℹ️ 삭제할 오래된 백업이 없습니다.
✅ 드라이브 자동 포스팅 시스템 초기화 완료
🔋 macOS 절전 모드 방지 활성화됨 (caffeinate 실행)
2026-04-24 14:04:22,131 - flet - INFO - Assets path configured: /Users/gm2hapkido/Desktop/라이온개발자/assets
2026-04-24 14:04:22,133 - flet - INFO - Starting up UDS server on /var/folders/yp/_8rr9xmn3x94hg1bcvzv5hq80000gn/T/AoSSArze4J
2026-04-24 14:04:22,133 - flet - INFO - Flet app has started...
2026-04-24 14:04:22,133 - flet - INFO - App URL: /var/folders/yp/_8rr9xmn3x94hg1bcvzv5hq80000gn/T/AoSSArze4J
2026-04-24 14:04:22,133 - flet_desktop - INFO - Starting Flet View app...
2026-04-24 14:04:22,134 - flet_desktop - INFO - Flet View found in: /Users/gm2hapkido/.flet/bin/flet-0.27.4
2026-04-24 14:04:22,414 - flet - INFO - App session started
2026-04-24 14:04:22,416 - modules.serial_auth - INFO - 로컬 만료일 체크: 유효 (만료: 2026-07-17)
2026-04-24 14:04:22,416 - modules.serial_auth - INFO - 서버 검증 시도 1/3 (타임아웃: 5초)
2026-04-24 14:04:22,702 - modules.serial_auth - INFO - 서버 검증 성공: 서버 인증 성공
2026-04-24 14:04:22,703 - modules.serial_auth - INFO - 설정 파일 저장 완료 (암호화 적용)
📡 디바이스 정보 업데이트 시작: ea920794...
2026-04-24 14:04:22,703 - modules.serial_auth - INFO - update_device_info_and_usage 호출: ea920794-39ca-458d-b2ad-4681b6a4aaa7
2026-04-24 14:04:22,758 - modules.serial_auth - INFO - 디바이스 정보 수집 완료: {'hostname': 'lionui-MacBookAir.local', 'ip_address': '127.0.0.1', 'system_manufacturer': 'Apple', 'os_name': 'Darwin', 'os_version': 'Darwin Kernel Version 24.6.0: Wed Nov  5 21:33:59 PST 2025; root:xnu-11417.140.69.705.2~1/RELEASE_ARM64_T8112', 'processor': 'Apple M2', 'registration_date': '2026-04-24 14:04:22', 'system_model': 'Mac14,15', 'total_memory': '8.00GB'}
   디바이스 정보: lionui-MacBookAir.local, unknown
2026-04-24 14:04:22,760 - modules.serial_auth - INFO - 같은 디바이스 시리얼 정리 시작 - 호스트: lionui-MacBookAir.local, 앱: 블로그자동화
2026-04-24 14:04:22,761 - modules.serial_auth - INFO - 보호 대상 시리얼: ea920794... (설정 파일)
2026-04-24 14:04:22,762 - modules.serial_auth - INFO - 정리할 같은 디바이스 시리얼 없음
2026-04-24 14:04:22,762 - modules.serial_auth - INFO - 로컬 DB 업데이트 시도: ea920794-39ca-458d-b2ad-4681b6a4aaa7
2026-04-24 14:04:22,763 - modules.serial_auth - INFO - 로컬 DB 업데이트 완료: ea920794-39ca-458d-b2ad-4681b6a4aaa7 (사용횟수: 170)
2026-04-24 14:04:22,763 - modules.serial_auth - INFO - 서버 업데이트 시도: ea920794-39ca-458d-b2ad-4681b6a4aaa7, 데이터: {'device_info': {'hostname': 'lionui-MacBookAir.local', 'ip_address': '127.0.0.1', 'system_manufacturer': 'Apple', 'os_name': 'Darwin', 'os_version': 'Darwin Kernel Version 24.6.0: Wed Nov  5 21:33:59 PST 2025; root:xnu-11417.140.69.705.2~1/RELEASE_ARM64_T8112', 'processor': 'Apple M2', 'registration_date': '2026-04-24 14:04:22', 'system_model': 'Mac14,15', 'total_memory': '8.00GB', 'app_name': '블로그자동화'}, 'activation_count': 170, 'status': '사용중', 'expiry_date': '2026-07-17'}
📡 [Startup] 디바이스 정보 업데이트 시도: ea920794-39ca-458d-b2ad-4681b6a4aaa7
📡 디바이스 정보 업데이트 시작: ea920794...
2026-04-24 14:04:23,291 - modules.serial_auth - INFO - update_device_info_and_usage 호출: ea920794-39ca-458d-b2ad-4681b6a4aaa7
2026-04-24 14:04:23,309 - modules.serial_auth - INFO - 디바이스 정보 수집 완료: {'hostname': 'lionui-MacBookAir.local', 'ip_address': '127.0.0.1', 'system_manufacturer': 'Apple', 'os_name': 'Darwin', 'os_version': 'Darwin Kernel Version 24.6.0: Wed Nov  5 21:33:59 PST 2025; root:xnu-11417.140.69.705.2~1/RELEASE_ARM64_T8112', 'processor': 'Apple M2', 'registration_date': '2026-04-24 14:04:23', 'system_model': 'Mac14,15', 'total_memory': '8.00GB'}
   디바이스 정보: lionui-MacBookAir.local, unknown
2026-04-24 14:04:23,310 - modules.serial_auth - INFO - 같은 디바이스 시리얼 정리 시작 - 호스트: lionui-MacBookAir.local, 앱: 블로그자동화
2026-04-24 14:04:23,310 - modules.serial_auth - INFO - 보호 대상 시리얼: ea920794... (설정 파일)
2026-04-24 14:04:23,310 - modules.serial_auth - INFO - 정리할 같은 디바이스 시리얼 없음
2026-04-24 14:04:23,310 - modules.serial_auth - INFO - 로컬 DB 업데이트 시도: ea920794-39ca-458d-b2ad-4681b6a4aaa7
2026-04-24 14:04:23,311 - modules.serial_auth - INFO - 로컬 DB 업데이트 완료: ea920794-39ca-458d-b2ad-4681b6a4aaa7 (사용횟수: 171)
2026-04-24 14:04:23,311 - modules.serial_auth - INFO - 서버 업데이트 시도: ea920794-39ca-458d-b2ad-4681b6a4aaa7, 데이터: {'device_info': {'hostname': 'lionui-MacBookAir.local', 'ip_address': '127.0.0.1', 'system_manufacturer': 'Apple', 'os_name': 'Darwin', 'os_version': 'Darwin Kernel Version 24.6.0: Wed Nov  5 21:33:59 PST 2025; root:xnu-11417.140.69.705.2~1/RELEASE_ARM64_T8112', 'processor': 'Apple M2', 'registration_date': '2026-04-24 14:04:23', 'system_model': 'Mac14,15', 'total_memory': '8.00GB', 'app_name': '블로그자동화'}, 'activation_count': 171, 'status': '사용중', 'expiry_date': '2026-07-17'}
   ✅ 서버 업데이트 성공!
2026-04-24 14:04:24,697 - modules.serial_auth - INFO - 서버 업데이트 성공
2026-04-24 14:04:24,727 - modules.serial_auth - INFO - 서버 검증 시도 1/3 (타임아웃: 5초)
   ✅ 서버 업데이트 성공!
2026-04-24 14:04:26,167 - modules.serial_auth - INFO - 서버 업데이트 성공
✅ [Startup] 디바이스 정보 서버 업데이트 완료
2026-04-24 14:04:26,359 - modules.serial_auth - INFO - 서버 검증 시도 1/3 (타임아웃: 5초)
📜 로그 뷰어 열기 요청됨
✅ 로그 뷰어 열기 성공 (page.open + update + threading polling)
🔍 버전 파일 검색 경로: ['/Users/gm2hapkido/Desktop/라이온개발자/version.json', '/Users/gm2hapkido/Desktop/라이온개발자/version.json', '/Users/gm2hapkido/Desktop/라이온개발자/version.json']
✅ 버전 파일 로드 성공: /Users/gm2hapkido/Desktop/라이온개발자/version.json (v1.2.126)
2026-04-24 14:05:37,194 - INFO - 버전 확인 URL: https://raw.githubusercontent.com/kwanwon/naver-blog-automation/main/version_mac.json
2026-04-24 14:05:37,194 - AutoUpdater - INFO - 버전 확인 URL: https://raw.githubusercontent.com/kwanwon/naver-blog-automation/main/version_mac.json
2026-04-24 14:09:26,649 - modules.serial_auth - INFO - 서버 검증 시도 1/3 (타임아웃: 5초)
🛑 중지 버튼 클릭됨!
  ✅ 스케줄러 상태 초기화됨
🔄 세션 유지 시스템 중지 요청됨
✅ 중지 UI 업데이트 완료
