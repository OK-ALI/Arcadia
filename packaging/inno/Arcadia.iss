#define MyAppName "Arcadia Core"
#define MyAppExeName "Arcadia.exe"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Arcadia"
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

[Files]
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
