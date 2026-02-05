; 블로그 자동화 프로그램 Windows 설치 프로그램
; Inno Setup 스크립트 - GitHub Actions 빌드용

#define MyAppName "블로그 자동화"
#define MyAppVersion GetEnv('APP_VERSION')
#if MyAppVersion == ""
#define MyAppVersion "1.2.0"
#endif
#define MyAppPublisher "라이온개발자"
#define MyAppURL "https://github.com/kwanwon/naver-blog-automation"
#define MyAppExeName "BlogApp.exe"

[Setup]
; 기본 설정
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; 설치 폴더 설정
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

; 출력 파일 설정
OutputDir=..\output
OutputBaseFilename=BlogAutomation_Setup_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; 시스템 요구사항
MinVersion=6.1sp1
PrivilegesRequired=admin

; 언어 설정
ShowLanguageDialog=yes

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; flet pack 빌드 결과물 - BlogAutomation_Windows_App 폴더 전체
Source: "..\dist\BlogAutomation_Windows_App\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "manual_chrome_profile_*;*.log;__pycache__"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\assets\icon.ico"; WorkingDir: "{app}"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon; IconFilename: "{app}\assets\icon.ico"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\*.log"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
// 설치 후 Chrome 설치 확인 및 안내
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  
  if CurPageID = wpSelectTasks then
  begin
    // Chrome 설치 여부 확인
    if not RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\Google\Chrome') then
    begin
      if MsgBox('Chrome 브라우저가 설치되어 있지 않습니다.' + #13#10 + 
                '블로그 자동화 프로그램을 사용하려면 Chrome 브라우저가 필요합니다.' + #13#10 + 
                '설치를 계속하시겠습니까?', mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
      end
      else
      begin
        MsgBox('설치 완료 후 Chrome을 설치해주세요: https://www.google.com/chrome/', mbInformation, MB_OK);
      end;
    end;
  end;
end;

// 설치 완료 후 안내 메시지
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    MsgBox('블로그 자동화 설치가 완료되었습니다!' + #13#10 + #13#10 +
           '※ 프로그램 사용을 위해 다음 사항을 확인해주세요:' + #13#10 +
           '  1. Chrome 브라우저 설치' + #13#10 +
           '  2. 시리얼 번호 준비', 
           mbInformation, MB_OK);
  end;
end;
