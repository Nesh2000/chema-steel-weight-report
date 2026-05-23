; ============================================================
;  Chema Steel Weight Report — Inno Setup Installer Script
;  Compile with: ISCC.exe installer.iss
; ============================================================

[Setup]
AppName=Chema Steel Weight Report
AppVersion=2.0
AppPublisher=Chema Steel and Hardware Ltd
AppPublisherURL=
AppSupportURL=
AppUpdatesURL=
; Install the exe/runtime into Program Files
DefaultDirName={autopf}\Chema Steel Weight Report
DefaultGroupName=Chema Steel Weight Report
; Output installer file
OutputDir=installer_output
OutputBaseFilename=ChemaSteelWeightReport_Setup_v2.0
; Compression
Compression=lzma2
SolidCompression=yes
; Appearance
WizardStyle=modern
; Require admin so we can write to Program Files and ProgramData
PrivilegesRequired=admin
; Show the app's exe icon in Add/Remove Programs
UninstallDisplayIcon={app}\ChemaSteelWeightReport.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &Desktop shortcut"; \
    GroupDescription: "Additional icons:"; Flags: checked

[Files]
; --- Application executable and runtime ---
; Everything PyInstaller put in dist\ChemaSteelWeightReport\
Source: "dist\ChemaSteelWeightReport\*"; \
    DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

; --- Persistent data files → ProgramData (writable by all users) ---
; Initial database (pre-populated with 297 products)
Source: "data\steel_calculator.db"; \
    DestDir: "{commonappdata}\ChemaSteelWeightReport\data"; \
    Flags: ignoreversion onlyifdoesntexist

; Company logo
Source: "data\chema_logo.jpeg"; \
    DestDir: "{commonappdata}\ChemaSteelWeightReport\data"; \
    Flags: ignoreversion

[Dirs]
; Ensure the data folder exists in ProgramData
Name: "{commonappdata}\ChemaSteelWeightReport\data"

[Icons]
; Start Menu shortcut
Name: "{group}\Chema Steel Weight Report"; \
    Filename: "{app}\ChemaSteelWeightReport.exe"

; Start Menu uninstall entry
Name: "{group}\Uninstall Chema Steel Weight Report"; \
    Filename: "{uninstallexe}"

; Desktop shortcut (only if user chose this task)
Name: "{autodesktop}\Chema Steel Weight Report"; \
    Filename: "{app}\ChemaSteelWeightReport.exe"; \
    Tasks: desktopicon

[Run]
; Offer to launch the app after installation
Filename: "{app}\ChemaSteelWeightReport.exe"; \
    Description: "Launch Chema Steel Weight Report now"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove ProgramData folder when the user uninstalls
Type: filesandordirs; Name: "{commonappdata}\ChemaSteelWeightReport"
