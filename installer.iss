; ZAIA Prepare Personal - Inno Setup script (no logo)
; AppVersion must match zaia/version.py APP_VER and update.json (MakeRelease.py checks this)
[Setup]
AppId={{B4F0C2A1-6C0E-4C9B-9B1E-5A1D7E2F0A11}
AppName=ZAIA Prepare Personal
AppVersion=0.9.0
AppPublisher=ZAIA
DefaultDirName={autopf}\ZAIA Prepare Personal
DefaultGroupName=ZAIA Prepare Personal
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=ZAIA_Prepare_Personal_Setup_0.9.0
SetupIconFile=assets\logo.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayName=ZAIA Prepare Personal

[Files]
Source: "dist\ZAIA Prepare Personal\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\ZAIA Prepare Personal"; Filename: "{app}\ZAIA Prepare Personal.exe"
Name: "{autodesktop}\ZAIA Prepare Personal"; Filename: "{app}\ZAIA Prepare Personal.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\ZAIA Prepare Personal.exe"; Description: "Launch ZAIA Prepare Personal"; Flags: nowait postinstall skipifsilent
