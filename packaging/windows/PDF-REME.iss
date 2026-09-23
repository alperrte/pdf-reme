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
;
; AppVersion, build_portable.ps1'in src\pdf_reme\presentation\app_info.py::
; APP_VERSION'dan uretip yazdigi AppVersion.generated.iss dosyasindan gelir;
; boylece surum burada elle tekrarlanmaz. Once build_portable.ps1 calistirin.

; NOT: FileExists/DirExists (ISPP), #include'in aksine, ISCC'nin CALISTIRILDIGI
; dizine (cwd) gore degil -- burada SourcePath (bu .iss dosyasinin kendi
; klasoru) ile mutlak yola cevrilerek kontrol ediliyor; boylece ISCC proje
; kokunden de, packaging\windows icinden de calistirilsa ayni sonucu verir.
#if FileExists(SourcePath + "AppVersion.generated.iss")
  #include SourcePath + "AppVersion.generated.iss"
#else
  #error "AppVersion.generated.iss bulunamadi. Once build_portable.ps1 calistirip Portable paketini uretin (surum APP_VERSION'dan otomatik alinir)."
#endif

#define AppName "PDF-REME"
#define AppPublisher "Alper Temiz"
#define AppExeName "PDF-REME.exe"
#define SourceRoot SourcePath + "..\..\dist\PDF-REME-v" + AppVersion + "-Portable"

#if !DirExists(SourceRoot)
  #error "Portable kaynak klasoru bulunamadi. Once build_portable.ps1 -Build calistirip Portable paketini uretin."
#endif

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
; Akis: Hos Geldiniz > Ozellikler > Kurulum Konumu > Ek Gorevler > Kuruluma Hazir > Kurulum > Tamamlandi
DisableProgramGroupPage=yes
DisableDirPage=no
DisableReadyPage=no
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=PDF-REME.ico
WizardImageFile=assets\wizard-image.bmp
WizardSmallImageFile=assets\wizard-small-image.bmp
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

[Messages]
turkish.WelcomeLabel2=PDF-REME — PDF belgelerini görüntülemek, düzenlemek, birleştirmek, bölmek, dönüştürmek, sıkıştırmak ve korumak için yerel çalışan masaüstü PDF aracı.%n%nKuruluma devam etmek için İleri'yi tıklayın.
english.WelcomeLabel2=PDF-REME is a local desktop tool for viewing, editing, merging, splitting, converting, compressing and protecting PDF documents.%n%nClick Next to continue.
turkish.FinishedLabel=PDF-REME başarıyla kuruldu.
english.FinishedLabel=PDF-REME has been successfully installed.

[CustomMessages]
turkish.FeaturesPageCaption=PDF-REME ile neler yapabilirsiniz?
turkish.FeaturesPageSubCaption=Kuruluma devam etmeden önce öne çıkan özelliklere göz atın.
turkish.FeaturesPageBody=• PDF görüntüleme ve sayfa düzenleme%n• PDF birleştirme ve bölme%n• Görsel ve Office belgelerini PDF'ye dönüştürme%n• PDF sıkıştırma%n• Parola ile koruma ve şifre kaldırma%n• Yerel kütüphane (dosyalarınız cihazınızda kalır)%n• Türkçe / İngilizce dil desteği%n• Açık / Koyu tema
english.FeaturesPageCaption=What can you do with PDF-REME?
english.FeaturesPageSubCaption=A quick look at the main features before you continue.
english.FeaturesPageBody=• View PDFs and edit pages%n• Merge and split PDFs%n• Convert images and Office documents to PDF%n• Compress PDFs%n• Password-protect PDFs and remove passwords%n• Local library (your files stay on your device)%n• Turkish / English language support%n• Light / Dark theme

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

[Code]
procedure InitializeWizard();
var
  FeaturesPage: TWizardPage;
  Body: TNewStaticText;
begin
  FeaturesPage := CreateCustomPage(wpWelcome,
    CustomMessage('FeaturesPageCaption'),
    CustomMessage('FeaturesPageSubCaption'));

  Body := TNewStaticText.Create(WizardForm);
  Body.Parent := FeaturesPage.Surface;
  Body.AutoSize := False;
  Body.WordWrap := True;
  Body.Left := 0;
  Body.Top := 0;
  Body.Width := FeaturesPage.SurfaceWidth;
  Body.Height := FeaturesPage.SurfaceHeight;
  Body.Caption := CustomMessage('FeaturesPageBody');
end;
