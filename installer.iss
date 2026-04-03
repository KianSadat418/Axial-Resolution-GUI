; Inno Setup Script for Axial Resolution GUI
;
; Build the PyInstaller dist first, then compile this script with Inno Setup.

[Setup]
AppName=Axial Resolution GUI
AppVersion=2.0.0
AppPublisher=Axial Resolution Team
DefaultDirName={autopf}\AxialResolution
DefaultGroupName=Axial Resolution
OutputDir=installer_output
OutputBaseFilename=AxialResolution_Setup_2.0.0
Compression=lzma2
SolidCompression=yes
SetupIconFile=assets\app_icon.ico
UninstallDisplayIcon={app}\AxialResolution.exe
WizardStyle=modern
PrivilegesRequired=lowest

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\AxialResolution\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Axial Resolution GUI"; Filename: "{app}\AxialResolution.exe"
Name: "{group}\Uninstall Axial Resolution"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Axial Resolution GUI"; Filename: "{app}\AxialResolution.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AxialResolution.exe"; Description: "Launch Axial Resolution GUI"; Flags: nowait postinstall skipifsilent
