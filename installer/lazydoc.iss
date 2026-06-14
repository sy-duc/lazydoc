#define MyAppVersion "1.0.0"

[Setup]
AppId={{5E0D86BF-98FF-41DA-BE11-DF38E77C0626}
AppName=LazyDoc
AppVersion={#MyAppVersion}
AppPublisher=LazyDoc
DefaultDirName={localappdata}\Programs\LazyDoc
DefaultGroupName=LazyDoc
DisableProgramGroupPage=yes
SourceDir=..
OutputDir=dist-installer
OutputBaseFilename=LazyDocSetup-{#MyAppVersion}
SetupIconFile=favicon.ico
UninstallDisplayIcon={app}\LazyDoc.exe
PrivilegesRequired=lowest
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "dist\LazyDoc\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Tasks]
Name: "desktopicon"; Description: "Tạo shortcut ngoài Desktop"; GroupDescription: "Tùy chọn:"

[Icons]
Name: "{autoprograms}\LazyDoc"; Filename: "{app}\LazyDoc.exe"; IconFilename: "{app}\LazyDoc.exe"
Name: "{autodesktop}\LazyDoc"; Filename: "{app}\LazyDoc.exe"; IconFilename: "{app}\LazyDoc.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\LazyDoc.exe"; Description: "Mở LazyDoc"; Flags: nowait postinstall skipifsilent
