; 블로그 자동화 프로그램 Windows 설치 프로그램
; Inno Setup 스크립트

#define MyAppName "블로그 자동화"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "라이온개발자"
#define MyAppURL "https://github.com/kwanwon/naver-blog-automation"
#define MyAppExeName "블로그자동화.exe"

[Setup]
; 기본 설정
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; 설치 폴더 설정
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

; 출력 파일 설정
OutputDir=dist
OutputBaseFilename=블로그자동화_설치프로그램_v{#MyAppVersion}
SetupIconFile=..\app_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; 시스템 요구사항
MinVersion=6.1sp1
PrivilegesRequired=admin

; 언어 설정
Language=Korean

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; 메인 실행 파일
Source: "..\dist\블로그자동화\블로그자동화.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\블로그자동화\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; 필수 라이브러리들
Source: "..\dist\블로그자동화\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; 설정 파일들
Source: "..\dist\블로그자동화\config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\블로그자동화\modules\*"; DestDir: "{app}\modules"; Flags: ignoreversion recursesubdirs createallsubdirs

; 이미지 파일들
Source: "..\dist\블로그자동화\default_images*\*"; DestDir: "{app}\default_images"; Flags: ignoreversion recursesubdirs createallsubdirs

; 기타 필수 파일들
Source: "..\dist\블로그자동화\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\블로그자동화\version.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\블로그자동화\배포_정보.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\app_icon.ico"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon; IconFilename: "{app}\app_icon.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

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
    MsgBox('설치가 완료되었습니다!' + #13#10 + 
           '프로그램을 사용하기 전에 Chrome 브라우저가 설치되어 있는지 확인해주세요.', 
           mbInformation, MB_OK);
  end;
end;
