# 블로그 자동화 프로그램 설치 스크립트
# NSIS (Nullsoft Scriptable Install System) 사용

!define APP_NAME "블로그자동화"
!define APP_VERSION "1.5.0"
!define APP_PUBLISHER "라이온개발자"
!define APP_URL "https://github.com/kwanwon/naver-blog-automation"
!define APP_EXECUTABLE "블로그자동화.exe"

# 설치 프로그램 설정
Name "${APP_NAME}"
OutFile "블로그자동화_v1.5.0_Setup.exe"
InstallDir "$PROGRAMFILES\${APP_NAME}"
InstallDirRegKey HKLM "Software\${APP_NAME}" "Install_Dir"
RequestExecutionLevel admin

# 압축 설정
SetCompressor /SOLID lzma

# 아이콘 설정
Icon "icons\blog_automation_256x256.png"
UninstallIcon "icons\blog_automation_256x256.png"

# 설치 프로그램 정보
VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey "ProductName" "${APP_NAME}"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"
VIAddVersionKey "CompanyName" "${APP_PUBLISHER}"
VIAddVersionKey "FileDescription" "네이버 블로그 자동화 프로그램"
VIAddVersionKey "FileVersion" "${APP_VERSION}"

# 설치 페이지
Page directory
Page instfiles

# 제거 페이지
UninstPage uninstConfirm
UninstPage instfiles

# 설치 섹션
Section "Main Application" SecMain
    SetOutPath "$INSTDIR"
    
    # 메인 실행 파일
    File "dist\${APP_EXECUTABLE}"
    
    # 필요한 파일들
    File /r "dist\*"
    
    # 시작 메뉴 바로가기 생성
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXECUTABLE}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\제거.lnk" "$INSTDIR\Uninstall.exe"
    
    # 바탕화면 바로가기 생성
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXECUTABLE}"
    
    # 레지스트리 항목 생성
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "URLInfoAbout" "${APP_URL}"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoRepair" 1
    
    # 제거 프로그램 생성
    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

# 제거 섹션
Section "Uninstall"
    # 파일 삭제
    Delete "$INSTDIR\${APP_EXECUTABLE}"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r "$INSTDIR"
    
    # 바로가기 삭제
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\제거.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"
    
    # 레지스트리 항목 삭제
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
    DeleteRegKey HKLM "Software\${APP_NAME}"
SectionEnd
