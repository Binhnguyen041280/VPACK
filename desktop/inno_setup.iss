; VPACK Windows Installer Script
; Inno Setup 6+
; https://jrsoftware.org/isinfo.php

#define MyAppName "VPACK"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "VPACK Team"
#define MyAppURL "https://github.com/vpack"
#define MyAppExeName "VPACK.exe"

[Setup]
; App info
AppId={{A8F7B5C3-1234-5678-9ABC-DEF012345678}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Install directories
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}

; Output
OutputDir=dist\installer
OutputBaseFilename=VPACK-{#MyAppVersion}-Windows-Setup
SetupIconFile=resources\icon.ico

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Privileges
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Appearance
WizardStyle=modern
DisableProgramGroupPage=yes

; Uninstall
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Start with Windows"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main executable
Source: "dist\VPACK\VPACK.exe"; DestDir: "{app}"; Flags: ignoreversion

; Backend
Source: "dist\VPACK\backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs createallsubdirs

; Frontend
Source: "dist\VPACK\frontend\*"; DestDir: "{app}\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs

; Resources
Source: "dist\VPACK\resources\*"; DestDir: "{app}\resources"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists(ExpandConstant('{src}\dist\VPACK\resources'))

; Additional DLLs if needed
Source: "dist\VPACK\*.dll"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; Startup
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
; Run after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up data directory
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}"

[Code]
// Check if app is running before uninstall
function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;

  // Try to close running instance
  if Exec('taskkill', '/F /IM VPACK.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    Sleep(1000); // Wait for process to close
  end;
end;

// Create data directories after install
procedure CurStepChanged(CurStep: TSetupStep);
var
  DataDir: String;
begin
  if CurStep = ssPostInstall then
  begin
    DataDir := ExpandConstant('{localappdata}\{#MyAppName}');

    // Create directories
    ForceDirectories(DataDir + '\database');
    ForceDirectories(DataDir + '\logs');
    ForceDirectories(DataDir + '\output');
    ForceDirectories(DataDir + '\sessions');
    ForceDirectories(DataDir + '\input');
  end;
end;
