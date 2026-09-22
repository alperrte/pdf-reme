; PDF-REME Windows kurulum tanimi (Inno Setup 6).
;
; Derleme (proje kokunden):
;   ISCC.exe packaging\windows\PDF-REME.iss
;
; Kaynak: build_portable.ps1'in urettigi portable klasoru
;   dist\PDF-REME-v<surum>-Portable  (PDF-REME.exe, _internal\, runtime\libreoffice\)
; Cikti: dist\installers\PDF-REME-v<surum>-Setup.exe
;
; Tum yollar bu dosyanin konumuna gore hesaplanir.
; Kullanici verisi Documents\PDF-REME altindadir; kurulum/kaldirma bu klasore
; dokunmaz (yalnizca kurulumun kopyaladigi dosyalar kaldirilir).

#define AppName "PDF-REME"
#define AppVersion "1.0.0"
#define AppPublisher "Alper Temiz"
#define AppExeName "PDF-REME.exe"
#define SourceRoot "..\..\dist\PDF-REME-v" + AppVersion + "-Portable"

[Setup]
; Sabit uygulama kimligi: guncelleme/kaldirma bu degere baglanir, degistirilmemeli.
AppId={{6F0B7C52-3D1A-4E0F-9B6A-8C2E5A41D7F3}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
; Akis: Hos Geldiniz > Kurulum Konumu > Ek Gorevler > Kuruluma Hazir > Kurulum > Tamamlandi
DisableProgramGroupPage=yes
DisableDirPage=no
DisableReadyPage=no
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=PDF-REME.ico
OutputDir=..\..\dist\installers
OutputBaseFilename=PDF-REME-v{#AppVersion}-Setup
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
CloseApplications=yes

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Yalnizca calisan dagitim icerigi: exe, _internal ve runtime\libreoffice.
Source: "{#SourceRoot}\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceRoot}\runtime\*"; DestDir: "{app}\runtime"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
