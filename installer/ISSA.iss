#ifndef MyAppVersion
  #error MyAppVersion must be supplied by build_installer.ps1
#endif
#ifndef MyAppPublisher
  #define MyAppPublisher "ISSA"
#endif

#define MyAppName "ISSA Downloader"
#define MyAppExeName "ISSA.exe"

[Setup]
AppId={{D37B4D2F-4A23-45B2-9F01-7D2C52F09181}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\ISSA Downloader
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\assets\issa.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
OutputDir=..\dist-installer
OutputBaseFilename=ISSA-Setup
CloseApplications=yes
RestartApplications=no
ChangesAssociations=no
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist-app\ISSA\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
