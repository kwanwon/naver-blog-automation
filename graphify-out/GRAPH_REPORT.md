# Graph Report - .  (2026-06-01)

## Corpus Check
- Large corpus: 423 files · ~10,840,721 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder, or use --no-semantic to run AST-only.

## Summary
- 619 nodes · 919 edges · 69 communities (51 shown, 18 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 34 edges (avg confidence: 0.68)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Component 0|Component 0]]
- [[_COMMUNITY_Component 1|Component 1]]
- [[_COMMUNITY_Component 2|Component 2]]
- [[_COMMUNITY_Component 3|Component 3]]
- [[_COMMUNITY_Component 4|Component 4]]
- [[_COMMUNITY_Component 5|Component 5]]
- [[_COMMUNITY_Component 6|Component 6]]
- [[_COMMUNITY_Component 7|Component 7]]
- [[_COMMUNITY_Component 8|Component 8]]
- [[_COMMUNITY_Component 9|Component 9]]
- [[_COMMUNITY_Component 10|Component 10]]
- [[_COMMUNITY_Component 11|Component 11]]
- [[_COMMUNITY_Component 12|Component 12]]
- [[_COMMUNITY_Component 13|Component 13]]
- [[_COMMUNITY_Component 14|Component 14]]
- [[_COMMUNITY_Component 15|Component 15]]
- [[_COMMUNITY_Component 16|Component 16]]
- [[_COMMUNITY_Component 17|Component 17]]
- [[_COMMUNITY_Component 18|Component 18]]
- [[_COMMUNITY_Component 19|Component 19]]
- [[_COMMUNITY_Component 20|Component 20]]
- [[_COMMUNITY_Component 21|Component 21]]
- [[_COMMUNITY_Component 22|Component 22]]
- [[_COMMUNITY_Component 23|Component 23]]
- [[_COMMUNITY_Component 24|Component 24]]
- [[_COMMUNITY_Component 25|Component 25]]
- [[_COMMUNITY_Component 26|Component 26]]
- [[_COMMUNITY_Component 27|Component 27]]
- [[_COMMUNITY_Component 28|Component 28]]
- [[_COMMUNITY_Component 29|Component 29]]
- [[_COMMUNITY_Component 30|Component 30]]
- [[_COMMUNITY_Component 31|Component 31]]
- [[_COMMUNITY_Component 32|Component 32]]
- [[_COMMUNITY_Component 33|Component 33]]
- [[_COMMUNITY_Component 34|Component 34]]
- [[_COMMUNITY_Component 35|Component 35]]
- [[_COMMUNITY_Component 36|Component 36]]
- [[_COMMUNITY_Component 38|Component 38]]
- [[_COMMUNITY_Component 39|Component 39]]
- [[_COMMUNITY_Component 40|Component 40]]
- [[_COMMUNITY_Component 47|Component 47]]
- [[_COMMUNITY_Component 48|Component 48]]
- [[_COMMUNITY_Component 49|Component 49]]

## God Nodes (most connected - your core abstractions)
1. `BlogWriterApp` - 139 edges
2. `NaverBlogImageInserter` - 28 edges
3. `NaverBlogAutomation` - 27 edges
4. `ImageFolderManager` - 23 edges
5. `NaverBlogCommentReply` - 22 edges
6. `NaverBlogPostFinisher` - 21 edges
7. `NaverBandCommentReply` - 20 edges
8. `ImprovedNaverBlogAuto` - 16 edges
9. `CrossPlatformSetup` - 16 edges
10. `ManualSessionHelper` - 14 edges

## Surprising Connections (you probably didn't know these)
- `NaverBlogImageInserter` --uses--> `ImageFolderManager`  [INFERRED]
  naver_blog_auto_image.py → folder_manager.py
- `BlogWriterApp` --uses--> `ImageFolderManager`  [INFERRED]
  blog_writer_app.py → folder_manager.py
- `NaverBlogAutomation` --uses--> `NaverBlogPostFinisher`  [INFERRED]
  naver_blog_auto.py → naver_blog_post_finisher.py
- `BlogWriterApp` --uses--> `NaverBlogPostFinisher`  [INFERRED]
  blog_writer_app.py → naver_blog_post_finisher.py
- `simulate_startup_update()` --calls--> `BlogWriterApp`  [INFERRED]
  simulate_startup.py → blog_writer_app.py

## Communities (69 total, 18 thin omitted)

### Community 0 - "Component 0"
Cohesion: 0.07
Nodes (21): get_date_folder(), NaverBlogImageInserter, 폴더에서 이미지와 동영상 파일 목록을 가져와 분류합니다., 본문 내용에 이미지와 동영상 삽입 (통합 제어), 앱이 번들되었을 때와 그렇지 않을 때 모두 리소스 경로를 올바르게 가져옵니다., 단일 미디어 삽입 (타입 자동 판별 등 처리), 이미지 삽입 과정에서 발생하는 팝업 처리, input[type=file]의 click()을 가로채서 Finder가 열리지 않게 설정 (+13 more)

### Community 1 - "Component 1"
Cohesion: 0.06
Nodes (16): 활동 시간 업데이트 (작업 시작/종료 시 호출), 백그라운드 댓글 모니터링 시작 (다른 작업과 독립적), 자동 포스팅 실행 - 전송 버튼만 클릭, 현재 시간(또는 예약 시간) 기반으로 task_type 자동 판별                  - morning: ~12시 (오전) → 날씨, 브라우저 드라이버를 가져오거나 새로 생성, 자동 포스팅 실행 - 전송 버튼만 클릭, 주제(title)를 기반으로 스마트 이미지 폴더 매칭을 수행합니다.            매칭되는 폴더가 없거나 이미지가 없는 경우, get_ne, 지역 마케팅 타겟 발굴 버튼 클릭 핸들러 (+8 more)

### Community 2 - "Component 2"
Cohesion: 0.06
Nodes (5): BlogWriterApp, 세션 유지 시스템 시작 - 30분 비활성 시 네이버 홈 방문, 블로그용 실시간 드라이브 감시 시작/중지, 로컬 이미지 폴더를 스캔하고 AI 키워드를 자동 학습시킵니다., simulate_startup_update()

### Community 3 - "Component 3"
Cohesion: 0.09
Nodes (12): NaverBlogCommentReply, 네이버 블로그 댓글 자동 답글 모듈 - 블로그 홈(https://section.blog.naver.com/)에서 알림을 확인하고 답글을 작성합니, 네이버 GNB 알림(종 모양) 버튼 찾기, 알림 항목이 이미 읽은(클릭한) 것인지 판단, [Click-and-Capture 방식]         모바일 알림 센터에서 블로그 관련 알림을 직접 클릭하여 URL을 수집합니다., 새 창에서 댓글 URL을 열고 답글 작성 후 닫음                  🆕 URL에서 블로그 주인을 확인하여:         - 내 블, 🆕 1회만 답글 작성 로직 (내 댓글에 대한 답글용)                  남의 글에서 내 댓글에 누군가 답글을 달았을 때:, 실제 답글 작성 로직 (Iframe 내부) (+4 more)

### Community 4 - "Component 4"
Cohesion: 0.09
Nodes (16): NaverBlogPostFinisher, 앱 설정에서 최종 발행 자동 완료 설정 읽기, 블로그 예약 발행 시간 설정                  Args:             reservation_time: 예약 시간 (문자열,, 앱이 번들되었을 때와 그렇지 않을 때 모두 리소스 경로를 올바르게 가져옵니다., 최종 발행 버튼 클릭 (녹색 발행 버튼), 최종 발행 버튼 클릭 (녹색 발행 버튼) - 예약 포함 (Robust Version), 링크 입력창에 URL 입력 (확인 버튼 클릭은 별도 처리), 블로그 포스트에 푸터를 추가합니다:         1. 줄바꿈으로 공간 확보         2. 카카오톡 오픈채팅 링크 추가         3. (+8 more)

### Community 5 - "Component 5"
Cohesion: 0.1
Nodes (9): NaverBlogAutomation, 이미지 삽입 위치를 계산하는 메서드 - 첫 이미지는 100자 이후 문장 끝, 이후 200자 간격으로 문장 끝에 이미지 삽입, macOS에서 ChromeDriver 권한 수정, webdriver_manager 캐시 디렉터리 정리, WDM 캐시에 버전별 1개만 남기고 나머지 정리, 설치된 Chrome 브라우저의 메이저 버전 확인, 앱이 번들되었을 때와 그렇지 않을 때 모두 리소스 경로를 올바르게 가져옵니다., 클립보드 권한 요청 팝업 자동 처리 - 강화된 버전 (+1 more)

### Community 6 - "Component 6"
Cohesion: 0.13
Nodes (8): ImageFolderManager, 폴더명으로 전체 경로 반환 ('블로그사진폴더' 우선 탐색 및 macOS 자모음 정규화 처리), Load AI folder keyword mapping rules from JSON., Save AI folder keyword mapping rules to JSON., Scan and return all subfolders containing image files, excluding system folders., Calculate initial match priority based on folder names (Gym specific)., Scan Gym image folders and extract associated keywords via AI learning., Analyze post title & body to select the best matching image folder.

### Community 7 - "Component 7"
Cohesion: 0.13
Nodes (8): NaverBandCommentReply, 게시글 URL 수집 (댓글이 있는 것만), 댓글 영역으로 스크롤 - 모든 댓글 로드, 현재 페이지에서 댓글 처리 - 답글쓰기 버튼 사용, 네이버 밴드 댓글 자동 답글 시스템     - 게시글의 댓글을 읽고 AI로 답글 작성     - 운영자/관장 댓글은 스킵     - 이미 답글, 이미 내(관장/운영자) 답글이 있는지 확인                  🔧 개선: 멘션과 관계없이 바로 다음에 운영자 답글이 있으면 스킵, 스팸인지 확인 (🔧 개선: 신청 문맥이면 스팸 아님), 답글 작성 - 답글쓰기 버튼 클릭 → 입력 → 전송

### Community 8 - "Component 8"
Cohesion: 0.1
Nodes (8): 🆕 크로스 플랫폼: 절전 모드 방지 시작, 앱 시작 시 백그라운드에서 디바이스 정보 및 사용 횟수 업데이트, 사용자 데이터 디렉토리 반환 (Delegates to utils.path_utils), 저장된 주제 목록에서 순차적으로 주제 선택 (플랫폼별), AI 자동 답글 처리 로직 (상담 관리 탭)         context: 'MY_POST' (내 글에 달린 댓글) or 'REPLY_TO_ME, 블로그 드라이브 감지 시 자동 포스팅 실행, 카페 드라이브 감지 시 자동 포스팅 실행, Debug NDJSON 로그를 로컬 파일로 남깁니다.

### Community 9 - "Component 9"
Cohesion: 0.09
Nodes (5): 댓글 자동 답글 기능 (알림센터 기반 - NaverBlogCommentReply 모듈 사용), 특정 텍스트필드를 위한 폴더 선택기 열기, 사용자 가이드 다이얼로그 표시 (앱 내부에서 단계별 안내 + 사이트 이동 버튼), 폴더 선택기 열기 (macOS: osascript 사용, 크로스 플랫폼 지원), 상위 폴더 스캔하여 하위 폴더 목록 표시

### Community 11 - "Component 11"
Cohesion: 0.23
Nodes (3): CrossPlatformSetup, main(), 플랫폼별 가상 환경 활성화 명령어 반환

### Community 12 - "Component 12"
Cohesion: 0.24
Nodes (4): main(), ManualSessionHelper, 드라이버 실행권한 복구 (실패는 무시)., wdm 캐시 강제 삭제 (손상/버전 불일치 시 재설치 유도).

### Community 13 - "Component 13"
Cohesion: 0.15
Nodes (7): 현재 이미지 폴더 인덱스를 로드합니다., 현재 이미지 폴더 인덱스를 저장합니다., 사용된 이미지 폴더 이력을 로드합니다., 사용된 이미지 폴더 이력을 저장합니다., 특정 폴더를 사용된 목록에 추가합니다., 현재 상태에서 업로드할 이미지 파일 경로 리스트를 반환합니다., 다음 이미지 폴더 경로를 반환하고 인덱스를 업데이트합니다.            이미 사용된 폴더는 건너뛰고 다음 폴더를 선택합니다.

### Community 14 - "Component 14"
Cohesion: 0.18
Nodes (7): NaverCafeCommentReply, 네이버 카페 댓글 자동 답글 모듈 - 네이버 알림 센터(https://m.notify.naver.com/)에서 카페 관련 알림을 확인하고 답글을, 새 창에서 카페 게시글을 열고 답글을 작성합니다., 카페 게시글 내의 미답변 댓글을 찾아 답글을 작성합니다., GPT를 이용한 답글 생성 (gpt_handler 연동), 알림 센터에서 모든 미답변 카페 댓글을 수집하고 AI 답글을 작성합니다.         스케줄러에서 주로 호출됩니다., 네이버 알림 센터에서 카페 댓글/답글 알림을 수집합니다.         반환 형식: [{'url': str, 'type': 'my_post' |

### Community 16 - "Component 16"
Cohesion: 0.24
Nodes (6): ChromeDriverAutoFixer, main(), 모든 ChromeDriver 자동 수정, 모든 ChromeDriver 파일 찾기, macOS ChromeDriver 보안 속성 및 권한 수정, 손상된 WebDriverManager 캐시 정리

### Community 18 - "Component 18"
Cohesion: 0.22
Nodes (8): changelog, min_requirements, os, python, preserved_files, release_date, updated_at, version

### Community 19 - "Component 19"
Cohesion: 0.22
Nodes (8): changelog, min_requirements, os, python, preserved_files, release_date, updated_at, version

### Community 20 - "Component 20"
Cohesion: 0.22
Nodes (8): changelog, min_requirements, os, python, preserved_files, release_date, updated_at, version

### Community 21 - "Component 21"
Cohesion: 0.5
Nodes (7): download_chromedriver(), fix_chromedriver_permissions(), fix_existing_chromedrivers(), get_chrome_version(), main(), 기존 ChromeDriver들 권한 수정, run_command()

### Community 24 - "Component 24"
Cohesion: 0.46
Nodes (7): check_environment(), detect_platform(), main(), print_header(), run_application(), setup_chromedriver(), setup_virtual_environment()

### Community 27 - "Component 27"
Cohesion: 0.33
Nodes (5): current_url, found_indicators, login_confirmed, login_time, user_agent

### Community 28 - "Component 28"
Cohesion: 0.47
Nodes (5): create_chrome_policy_file(), main(), Chrome 정책 파일을 생성하여 클립보드 권한을 강제로 허용, Chrome 브라우저의 클립보드 권한을 자동으로 허용하도록 설정, setup_chrome_clipboard_permissions()

### Community 29 - "Component 29"
Cohesion: 0.67
Nodes (5): check_requirements(), create_dmg(), create_installer_directory(), main(), run_command()

### Community 34 - "Component 34"
Cohesion: 0.7
Nodes (4): get_current_version(), main(), run_command(), update_version_file()

### Community 36 - "Component 36"
Cohesion: 0.67
Nodes (3): create_release_config_templates(), main(), 배포용 기본 설정 템플릿을 생성합니다.

## Knowledge Gaps
- **26 isolated node(s):** `version`, `updated_at`, `release_date`, `changelog`, `python` (+21 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BlogWriterApp` connect `Component 2` to `Component 0`, `Component 1`, `Component 3`, `Component 4`, `Component 5`, `Component 6`, `Component 7`, `Component 8`, `Component 9`, `Component 12`, `Component 13`, `Component 17`, `Component 22`, `Component 25`, `Component 26`, `Component 31`, `Component 32`, `Component 33`, `Component 38`, `Component 39`, `Component 47`, `Component 48`, `Component 49`?**
  _High betweenness centrality (0.351) - this node is a cross-community bridge._
- **Why does `NaverBlogImageInserter` connect `Component 0` to `Component 1`, `Component 2`, `Component 5`, `Component 6`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Why does `NaverBlogPostFinisher` connect `Component 4` to `Component 1`, `Component 2`, `Component 5`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `BlogWriterApp` (e.g. with `NaverBandAutomation` and `NaverBandCommentReply`) actually correct?**
  _`BlogWriterApp` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `NaverBlogImageInserter` (e.g. with `NaverBlogAutomation` and `ImageFolderManager`) actually correct?**
  _`NaverBlogImageInserter` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `NaverBlogAutomation` (e.g. with `NaverBlogImageInserter` and `NaverBlogPostFinisher`) actually correct?**
  _`NaverBlogAutomation` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `ImageFolderManager` (e.g. with `NaverBlogImageInserter` and `BlogWriterApp`) actually correct?**
  _`ImageFolderManager` has 4 INFERRED edges - model-reasoned connections that need verification._