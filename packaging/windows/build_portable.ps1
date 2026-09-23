<#
.SYNOPSIS
    PDF-REME Portable dagitimini (klasor + ZIP) uretir.

.DESCRIPTION
    dist\PDF-REME (PyInstaller onedir ciktisi) + runtime\libreoffice
    (resmi LibreOffice) -> dist\PDF-REME-v<surum>-Portable\ (kalici klasor)
    ve dist\PDF-REME-v<surum>-Portable.zip

    Portable klasoru varsayilan olarak SILINMEZ: Inno Setup (PDF-REME.iss)
    bu klasoru dogrudan kurulum kaynagi (SourceRoot) olarak kullanir, boylece
    Setup.exe ve Portable ZIP birebir ayni ikili dosya kumesinden uretilir.
    Klasoru temizlemek icin acikca -CleanStaging verin.

    ZIP acildiginda PDF-REME-v<surum>-Portable\ klasoru olusur:
        PDF-REME.exe
        _internal\            PyInstaller calisma dosyalari
        runtime\libreoffice\  Office -> PDF donusumu icin paketlenmis LibreOffice
        runtime\LIBREOFFICE-NOTICE.txt

    LibreOffice kaynagi (oncelik sirasi):
      1. -LibreOfficeSource  <klasor>   program\soffice.exe iceren LO klasoru
      2. -LibreOfficeMsi     <dosya>    resmi LibreOffice .msi (msiexec /a ile cikarilir)
      3. Standart Windows kurulum yolu (Program Files\LibreOffice)

    LibreOffice dosyalari degistirilmez; tek istisna, Python-UNO ile calisan
    dil bilgisi denetleyicileri (share\extensions\dict-*\Lightproof.*,
    pythonpath) pakete alinmaz: kurulu yolun disina kopyalanan LibreOffice'te
    Writer belgelerinin donusumunu kilitliyor. Sozluk dosyalari, lisans ve
    readme dosyalari korunur.

    Surum, src\pdf_reme\presentation\app_info.py::APP_VERSION degerinden
    okunur (tek gercek kaynak) ve packaging\windows\AppVersion.generated.iss
    dosyasina yazilir; PDF-REME.iss surumu bu dosyadan alir, boylece surum
    3 ayri yerde elle guncellenmez.

.PARAMETER Build
    Once PyInstaller ile dist\PDF-REME klasorunu yeniden uretir.

.PARAMETER CleanStaging
    ZIP olusturulduktan sonra dist\PDF-REME-v<surum>-Portable\ klasorunu siler.
    Varsayilan davranis DEGILDIR; Inno Setup bu klasoru kaynak olarak
    kullandigi icin normalde kalici tutulur.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File packaging\windows\build_portable.ps1 -Build
#>
[CmdletBinding()]
param(
    [switch]$Build,
    [string]$LibreOfficeSource,
    [string]$LibreOfficeMsi,
    [switch]$CleanStaging
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$SpecFile = Join-Path $PSScriptRoot 'PDF-REME.spec'
$DistDir = Join-Path $ProjectRoot 'dist'
$AppDist = Join-Path $DistDir 'PDF-REME'
$BuildRoot = Join-Path $ProjectRoot 'build\portable'

function Write-Step([string]$Message) {
    Write-Host ''
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-Robocopy {
    param([string]$Source, [string]$Target, [string[]]$Extra = @())
    $arguments = @($Source, $Target, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/R:2', '/W:1') + $Extra
    & robocopy @arguments | Out-Null
    # robocopy: 0-7 basarili, >=8 hata.
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy basarisiz (kod $LASTEXITCODE): $Source"
    }
    $global:LASTEXITCODE = 0
}

# --- Surum -----------------------------------------------------------------
$appInfo = Join-Path $ProjectRoot 'src\pdf_reme\presentation\app_info.py'
$versionMatch = Select-String -Path $appInfo -Pattern '^APP_VERSION\s*=\s*"([^"]+)"' | Select-Object -First 1
if (-not $versionMatch) { throw "APP_VERSION okunamadi: $appInfo" }
$Version = $versionMatch.Matches[0].Groups[1].Value
$PackageName = "PDF-REME-v$Version-Portable"
$Staging = Join-Path $DistDir $PackageName
$ZipPath = Join-Path $DistDir "$PackageName.zip"
Write-Host "Surum: $Version  ->  $PackageName"

# Inno Setup (PDF-REME.iss), AppVersion'i #include ile bu dosyadan okur;
# boylece surum yalnizca APP_VERSION'da degisir, .iss elle duzenlenmez.
$versionIssPath = Join-Path $PSScriptRoot 'AppVersion.generated.iss'
Set-Content -Path $versionIssPath -Value "#define AppVersion `"$Version`"" -Encoding UTF8
Write-Host "Surum dosyasi yazildi: $versionIssPath"

# --- 1) PyInstaller ciktisi ------------------------------------------------
if ($Build) {
    Write-Step 'PyInstaller ile uygulama derleniyor'
    $venvPython = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
    $python = if (Test-Path $venvPython) { $venvPython } else { 'python' }
    Push-Location $ProjectRoot
    try {
        & $python -m PyInstaller --noconfirm --clean $SpecFile
        if ($LASTEXITCODE -ne 0) { throw "PyInstaller basarisiz (kod $LASTEXITCODE)" }
    }
    finally { Pop-Location }
}

if (-not (Test-Path (Join-Path $AppDist 'PDF-REME.exe'))) {
    throw "dist\PDF-REME\PDF-REME.exe bulunamadi. Once -Build ile calistirin."
}

# --- 2) LibreOffice kaynagi ------------------------------------------------
Write-Step 'LibreOffice kaynagi belirleniyor'
$extractDir = $null
if ($LibreOfficeMsi) {
    if (-not (Test-Path $LibreOfficeMsi)) { throw "MSI bulunamadi: $LibreOfficeMsi" }
    $msiSignature = Get-AuthenticodeSignature $LibreOfficeMsi
    if ($msiSignature.Status -ne 'Valid') { throw "MSI imzasi gecersiz: $($msiSignature.Status)" }
    $extractDir = Join-Path $BuildRoot '_lo_msi_extract'
    if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
    New-Item -ItemType Directory -Force $extractDir | Out-Null
    $msi = (Resolve-Path $LibreOfficeMsi).Path
    $process = Start-Process msiexec -ArgumentList "/a `"$msi`" /qn TARGETDIR=`"$extractDir`"" -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "msiexec /a basarisiz (kod $($process.ExitCode))" }
    $LibreOfficeSource = $extractDir
}
elseif (-not $LibreOfficeSource) {
    $candidates = @(
        (Join-Path $env:ProgramFiles 'LibreOffice'),
        (Join-Path ${env:ProgramFiles(x86)} 'LibreOffice')
    )
    $LibreOfficeSource = $candidates | Where-Object { $_ -and (Test-Path (Join-Path $_ 'program\soffice.exe')) } | Select-Object -First 1
}
if (-not $LibreOfficeSource -or -not (Test-Path (Join-Path $LibreOfficeSource 'program\soffice.exe'))) {
    throw 'LibreOffice bulunamadi. -LibreOfficeSource veya -LibreOfficeMsi verin.'
}
$LibreOfficeSource = (Resolve-Path $LibreOfficeSource).Path
$sofficeExe = Join-Path $LibreOfficeSource 'program\soffice.exe'
$signature = Get-AuthenticodeSignature $sofficeExe
if ($signature.Status -ne 'Valid') { throw "soffice.exe imzasi gecersiz: $($signature.Status)" }
$loVersion = (Get-Item $sofficeExe).VersionInfo.ProductVersion
Write-Host "LibreOffice $loVersion  ($($signature.SignerCertificate.Subject))"

# --- 3) Temiz staging ------------------------------------------------------
Write-Step 'Staging klasoru hazirlaniyor'
if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force }
New-Item -ItemType Directory -Force $Staging | Out-Null
Invoke-Robocopy -Source $AppDist -Target $Staging -Extra @('/XD', '__pycache__')

# --- 4) LibreOffice runtime ------------------------------------------------
Write-Step 'LibreOffice runtime kopyalaniyor'
$runtimeRoot = Join-Path $Staging 'runtime'
$loTarget = Join-Path $runtimeRoot 'libreoffice'
New-Item -ItemType Directory -Force $loTarget | Out-Null
$excludeDirs = @('__pycache__')
$excludeFiles = @()
$extensionsDir = Join-Path $LibreOfficeSource 'share\extensions'
foreach ($extension in Get-ChildItem $extensionsDir -Directory -ErrorAction SilentlyContinue) {
    $lightproof = Join-Path $extension.FullName 'Lightproof.py'
    if (Test-Path $lightproof) {
        $excludeFiles += $lightproof
        $excludeFiles += (Join-Path $extension.FullName 'Lightproof.components')
        $excludeDirs += (Join-Path $extension.FullName 'pythonpath')
        Write-Host "Python-UNO dil denetleyicisi haric: $($extension.Name)"
    }
}
Invoke-Robocopy -Source $LibreOfficeSource -Target $loTarget -Extra (@('/XD') + $excludeDirs + @('/XF') + $excludeFiles)

$notice = @"
PDF-REME - paketlenmis LibreOffice
==================================
Bu klasor (runtime\libreoffice), PDF-REME'nin DOC/DOCX/PPT/PPTX/XLS/XLSX -> PDF
donusumu icin kullandigi, The Document Foundation'in resmi LibreOffice
dagitimindan alinmis kopyadir. LibreOffice, MPL 2.0 ve diger acik kaynak
lisanslari altindadir; lisans metinleri libreoffice\LICENSE.html,
libreoffice\license.txt, libreoffice\NOTICE ve libreoffice\readmes\ altindadir.

Surum   : $loVersion
Kaynak  : https://www.libreoffice.org/  (Authenticode imzasi: The Document Foundation)
Degisiklik: LibreOffice dosyalari degistirilmemistir. Tek fark: Python-UNO ile
calisan dil bilgisi denetleyicileri (share\extensions\dict-*\Lightproof.py,
Lightproof.components ve pythonpath\) pakete dahil edilmemistir; bu bilesenler
kurulu yolun disindaki kopyada belge donusumunu kilitledigi icin cikarilmistir.
Yazim denetimi sozlukleri yerinde durur.
"@
Set-Content -Path (Join-Path $runtimeRoot 'LIBREOFFICE-NOTICE.txt') -Value $notice -Encoding UTF8

if (-not (Test-Path (Join-Path $loTarget 'program\soffice.exe'))) { throw 'Kopyada soffice.exe yok.' }
foreach ($legal in @('LICENSE.html', 'license.txt', 'NOTICE')) {
    if (-not (Test-Path (Join-Path $loTarget $legal))) { throw "LibreOffice lisans dosyasi eksik: $legal" }
}

# --- 5) Kaynak sizintisi denetimi -----------------------------------------
Write-Step 'Icerik denetimi'
foreach ($forbidden in @('src', 'tests', '.git', 'venv', '.venv', 'packaging', 'alembic')) {
    if (Test-Path (Join-Path $Staging $forbidden)) { throw "Pakette olmamasi gereken klasor: $forbidden" }
}
$leakedSource = Get-ChildItem $Staging -Recurse -File -Filter '*.py' -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notlike "$loTarget*" -and $_.FullName -match '[\\/]pdf_reme[\\/]' }
if ($leakedSource) { throw "pdf_reme kaynak dosyasi pakette: $($leakedSource[0].FullName)" }
Write-Host 'Kaynak kod / test / gelistirme dosyasi bulunmadi.'

# --- 6) ZIP ----------------------------------------------------------------
Write-Step "ZIP olusturuluyor: $ZipPath"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
if (-not (Test-Path $DistDir)) { New-Item -ItemType Directory -Force $DistDir | Out-Null }
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

$stagingParent = (Split-Path $Staging -Parent).TrimEnd('\') + '\'
$archive = [System.IO.Compression.ZipFile]::Open($ZipPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($file in Get-ChildItem $Staging -Recurse -File -Force) {
        # ZIP standardi '/' ayiraci ister; Windows yolundaki '\' cevrilir.
        $entryName = $file.FullName.Substring($stagingParent.Length).Replace('\', '/')
        [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $archive, $file.FullName, $entryName, [System.IO.Compression.CompressionLevel]::Optimal)
    }
}
finally { $archive.Dispose() }

# MSI'dan cikarilan gecici dosyalar her zaman temizlenir (Portable klasoru
# ile karistirilmamali); Portable klasoru ise Inno Setup'in kaynagi oldugu
# icin varsayilan olarak KORUNUR, yalnizca -CleanStaging ile silinir.
if ($extractDir -and (Test-Path $extractDir)) { Remove-Item $extractDir -Recurse -Force }
if ($CleanStaging) {
    Remove-Item $Staging -Recurse -Force
}

$sizeMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Step 'Tamamlandi'
Write-Host "Portable klasor: $Staging$(if (-not $CleanStaging) { ' (korundu; Inno Setup kaynagi)' } else { ' (silindi, -CleanStaging)' })"
Write-Host "ZIP : $ZipPath"
Write-Host "Boyut: $sizeMb MB"
