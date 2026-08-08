#define MyAppName "Downloader"
#define MyAppVersion "1.0.0-beta.1"
#define MyAppPublisher "ForintX"
#define MyAppURL "https://muhammetburakakkas.com"
#define MyAppExeName "downloader.exe"

[Setup]
AppId={{3D43EEDB-515F-4B51-96AB-28A35BD687F1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\Downloader
DefaultGroupName=Downloader
AllowNoIcons=yes
OutputDir=..\..\dist
OutputBaseFilename=Downloader-1.0.0-beta.1-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile=..\..\..\LICENSE

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü simgesi oluştur"; GroupDescription: "Ek simgeler:"

[Files]
Source: "..\..\build\windows\x64\runner\Release\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} uygulamasını başlat"; Flags: nowait postinstall skipifsilent
