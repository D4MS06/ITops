#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

#define MyAppName "NetworkMonitoringProject"
#define MyAppPublisher "D4MS06"
#define MyAppURL "https://github.com/D4MS06/NetworkMonitoringProject"
#define MyAppExeName "NetworkMonitoringProject.exe"

[Setup]
AppId={{6A7504A9-7D7A-4E45-8EB2-1E383BE32B6A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=output
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\NetworkMonitoringProject\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\monitoring\storage\devices.json"; DestDir: "{localappdata}\NetworkMonitoringProject\data"; DestName: "devices.json"; Flags: onlyifdoesntexist uninsneveruninstall

[Dirs]
Name: "{localappdata}\NetworkMonitoringProject"
Name: "{localappdata}\NetworkMonitoringProject\data"
Name: "{localappdata}\NetworkMonitoringProject\logs"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
