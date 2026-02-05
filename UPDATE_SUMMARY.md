# 업데이트 요약 (v1.2.60)

## 크로스 플랫폼 호환성 개선

### 변경 사항

#### 4. Windows 실행 오류 수정 (v1.2.60)
- **바로가기 수정**: `BlogAutomation.exe`가 응답하지 않는 문제로 인해 `BlogApp.exe`를 직접 실행하도록 변경
- **Chrome 프로필 경로**: `Program Files` 쓰기 권한 문제 해결 -> `AppData/Local` 사용
- **Chrome 옵션**: Windows에서 호환되지 않는 `/dev/null` 옵션 제거

#### 1. 설정 파일 경로 표준화
- **이전**: `base_dir`에 저장 (빌드 환경에서 문제 발생 가능)
- **이후**: `_get_app_data_dir()` 사용
  - Windows: `%LOCALAPPDATA%\BlogAutomation\`
  - macOS: `~/.blog_automation/`

#### 2. 밴드 URL 우선순위 수정
- **이전**: `task.data`에 저장된 과거 URL 우선 사용 (스케줄러 버그)
- **이후**: 현재 설정된 `self.settings['band_url']` 우선 사용

#### 3. GPT Handler 개선
- 로그 파일 및 설정 파일 경로 크로스 플랫폼 지원
- 권한 문제 해결 (빌드된 앱에서도 정상 작동)

## macOS 환경 안내

### 최초 실행 시 권한 요청
macOS에서 최초 실행 시 다음 권한 팝업이 나타날 수 있습니다:
1. **Accessibility 권한** - 자동 타이핑을 위해 필요
2. **파일 접근 권한** - 이미지 업로드를 위해 필요

이 권한은 한 번만 승인하면 됩니다.

### Gatekeeper 경고
앱 실행 시 "확인되지 않은 개발자" 경고가 나타나면:
```bash
xattr -cr /Applications/BlogAutomation_Mac.app
```

## 테스트 완료 항목
- [x] Windows 환경 테스트
- [x] 네이버 로그인
- [x] 블로그 포스팅
- [x] 카페 포스팅
- [x] 밴드 포스팅
- [x] 설정 저장/로드
- [x] GPT 콘텐츠 생성

## 다음 버전 예정
- macOS 환경 최종 테스트
- 성능 최적화
