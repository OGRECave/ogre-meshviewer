; Inno Setup script for the Windows release of OgreMeshViewer.
;
; Build the portable package first (from the repository root):
;   ./create_win_package.sh
; Then compile this script, preferably through the Inno build helper:
;   ./inno/create_win_installer.sh

#ifndef MyAppVersion
  #define MyAppVersion "26.11"
#endif

#ifndef SourceDir
  #define SourceDir "..\winpkg\ogre-meshviewer_" + MyAppVersion + "-win64"
#endif

#define MyAppName "OgreMeshViewer"
#define MyAppPublisher "OGRECave"
#define MyAppURL "https://github.com/OGRECave/ogre-meshviewer"
#define MyAppExeName "ogre-meshviewer.bat"
#define MyAppId "{{A58340C2-42B4-4F03-B182-DFE153FD165E}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
AppCopyright=Copyright (C) 2018 Pavel Rojtberg
DefaultDirName={autopf}\OgreMeshViewer
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
#if VER >= EncodeVer(6,3,0)
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
#else
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
#endif
MinVersion=10.0
OutputDir=..\winpkg
OutputBaseFilename=ogre-meshviewer_{#MyAppVersion}-win64-setup
SetupIconFile=ogre-meshviewer.ico
UninstallDisplayIcon={app}\ogre-meshviewer.ico
LicenseFile=..\LICENSE
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=yes
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "fileassoc"; Description: "Associate .mesh and .scene files with {#MyAppName}"; GroupDescription: "Shell integration"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__,*.pyc,*.pyo,*.pdb"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\ogre-meshviewer.ico"; Comment: "View Ogre meshes and scenes"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\ogre-meshviewer.ico"; Comment: "View Ogre meshes and scenes"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\OgreMeshViewer.mesh"; ValueType: string; ValueName: ""; ValueData: "Ogre Mesh"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\OgreMeshViewer.mesh\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\ogre-meshviewer.ico"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\OgreMeshViewer.mesh\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\.mesh"; ValueType: string; ValueName: ""; ValueData: "OgreMeshViewer.mesh"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\OgreMeshViewer.scene"; ValueType: string; ValueName: ""; ValueData: "Ogre Scene"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\OgreMeshViewer.scene\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\ogre-meshviewer.ico"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\OgreMeshViewer.scene\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\.scene"; ValueType: string; ValueName: ""; ValueData: "OgreMeshViewer.scene"; Flags: uninsdeletevalue; Tasks: fileassoc

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: shellexec nowait postinstall skipifsilent
