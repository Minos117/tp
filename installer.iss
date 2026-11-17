; ZAIA Prepare Personal - Inno Setup script (no logo)
; AppVersion must match zaia/version.py APP_VER and update.json (MakeRelease.py checks this)
[Setup]
AppId={{B4F0C2A1-6C0E-4C9B-9B1E-5A1D7E2F0A11}
AppName=ZAIA Prepare Personal
AppVersion=1.0.2
AppPublisher=ZAIA
DefaultDirName={autopf}\ZAIA Prepare Personal
DefaultGroupName=ZAIA Prepare Personal
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=ZAIA_Prepare_Personal_Setup_1.0.2
SetupIconFile=assets\logo.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayName=ZAIA Prepare Personal
UninstallDisplayIcon={app}\logo.ico

[Files]
Source: "dist\ZAIA Prepare Personal\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "assets\logo.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\ZAIA Prepare Personal"; Filename: "{app}\ZAIA Prepare Personal.exe"; IconFilename: "{app}\logo.ico"
Name: "{autodesktop}\ZAIA Prepare Personal"; Filename: "{app}\ZAIA Prepare Personal.exe"; IconFilename: "{app}\logo.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"

[Run]
Filename: "{sys}\ie4uinit.exe"; Parameters: "-show"; Flags: runhidden skipifdoesntexist
Filename: "{app}\ZAIA Prepare Personal.exe"; Description: "Launch ZAIA Prepare Personal"; Flags: nowait postinstall skipifsilent
