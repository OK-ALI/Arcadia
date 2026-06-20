#define MyAppName "Arcadia Core"
#define MyAppExeName "Arcadia.exe"
#define MyAppVersion "0.3.3.3"
#define MyAppPublisher "Arcadia"
#define MyAppUserModelID "OKALI.ArcadiaCore"
#define MySourceDir "..\..\dist\Arcadia"

[Setup]
AppId={{D5E9E9D0-B407-4F6F-9BC7-5CE9E3F6E879}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://arcadia.local
AppSupportURL=https://arcadia.local
AppUpdatesURL=https://arcadia.local
DefaultDirName={autopf}\Arcadia\Arcadia Core
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\installer-output
OutputBaseFilename=ArcadiaCoreSetup
SetupIconFile=..\..\assets\icons\arcadia.ico
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Arcadia Core - A Gaming Universe
VersionInfoProductName={#MyAppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
SetupLogging=yes
CloseApplications=yes
CloseApplicationsFilter={#MyAppExeName}
RestartApplications=no

[Files]
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; AppUserModelID: "{#MyAppUserModelID}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; AppUserModelID: "{#MyAppUserModelID}"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/IM ""{#MyAppExeName}"" /T /F"; Flags: runhidden; RunOnceId: "StopArcadiaCore"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\*"
Type: dirifempty; Name: "{app}"
Type: dirifempty; Name: "{autopf}\Arcadia"

[Registry]
Root: HKCU; Subkey: "Software\Classes\arcadia"; ValueType: string; ValueName: ""; ValueData: "URL:Arcadia Protocol"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\arcadia"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\arcadia\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey

[Code]
procedure StopArcadiaIfRunning();
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM "{#MyAppExeName}" /T /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    StopArcadiaIfRunning();
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{localappdata}\Arcadia Core');
    if DirExists(DataDir) then
    begin
      if MsgBox(
        'Do you also want to remove Arcadia Core local app data?' + #13#10 + #13#10 +
        'This removes settings, download state, resume data, My Library metadata, cached artwork, and logs stored under:' + #13#10 +
        DataDir + #13#10 + #13#10 +
        'Downloaded games outside this folder are not removed.',
        mbConfirmation,
        MB_YESNO
      ) = IDYES then
      begin
        DelTree(DataDir, True, True, True);
      end;
    end;
  end;
end;
