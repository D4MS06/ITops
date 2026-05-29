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
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
SetupIconFile=..\monitoring\assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
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

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\_internal\scripts\runtime\install_mariadb_service.ps1"" -DbHost ""127.0.0.1"" -DbPort ""3306"" -DbName ""IT_DB"" -DbUser ""IT_DB_MVL"" -DbPassword ""Villeneuve@06!"" -RootPassword ""Villeneuve@06!"""; Flags: runhidden waituntilterminated
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\_internal\scripts\runtime\install_caddy_service.ps1"" -PublicHost ""monitoring.mvl"" -BackendHost ""127.0.0.1"" -BackendPort ""8000"""; Flags: runhidden waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallRun]
Filename: "sc.exe"; Parameters: "stop NetworkMonitoringMariaDB"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "StopNetworkMonitoringMariaDB"
Filename: "sc.exe"; Parameters: "delete NetworkMonitoringMariaDB"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "DeleteNetworkMonitoringMariaDB"
Filename: "sc.exe"; Parameters: "stop NetworkMonitoringCaddy"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "StopNetworkMonitoringCaddy"
Filename: "sc.exe"; Parameters: "delete NetworkMonitoringCaddy"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "DeleteNetworkMonitoringCaddy"

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\NetworkMonitoringProject"
Type: filesandordirs; Name: "{commonappdata}\NetworkMonitoringProject\mariadb"
Type: filesandordirs; Name: "{commonappdata}\NetworkMonitoringProject\caddy"
Type: files; Name: "{%USERPROFILE}\.network_monitor_settings.json"
