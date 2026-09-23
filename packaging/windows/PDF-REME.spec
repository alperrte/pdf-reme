# -*- mode: python ; coding: utf-8 -*-
#
# PDF-REME Windows paketleme tanımı (onedir + windowed).
#
# Proje kökünden çalıştırılır:
#   python -m PyInstaller --noconfirm --clean packaging/windows/PDF-REME.spec
#
# Tüm yollar bu spec dosyasının konumundan (SPECPATH) hesaplanır; böylece
# komut hangi klasörden çalıştırılırsa çalıştırılsın ve proje nereye
# taşınırsa taşınsın aynı sonucu verir.
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

# SPECPATH: PyInstaller'ın sağladığı, spec dosyasının bulunduğu klasör.
SPEC_DIR = Path(SPECPATH).resolve()
PROJECT_ROOT = SPEC_DIR.parents[1]
SRC_DIR = PROJECT_ROOT / "src"
PACKAGE_DIR = SRC_DIR / "pdf_reme"
RESOURCES_DIR = PACKAGE_DIR / "resources"
ENTRY_POINT = PROJECT_ROOT / "start_app.py"
APP_ICON = SPEC_DIR / "PDF-REME.ico"

# APP_VERSION tek gerçek kaynak: EXE surum bilgisi buradan uretilir, .spec
# icinde ayrica tekrarlanmaz.
sys.path.insert(0, str(SRC_DIR))
from pdf_reme.presentation.app_info import APP_VERSION  # noqa: E402

# Bu klasorler yalnizca README/GitHub gorselleri icindir; uygulama calisma
# zamaninda bunlara hic erismez (bkz. src/ genelinde grep dogrulamasi).
EXCLUDED_RESOURCE_DIRS = {
    RESOURCES_DIR / "images" / "app_images",
    RESOURCES_DIR / "images" / "git_images",
}


def _is_excluded(path: Path) -> bool:
    return any(excluded == path or excluded in path.parents for excluded in EXCLUDED_RESOURCE_DIRS)


def _collect_resource_datas():
    entries = []
    for path in sorted(RESOURCES_DIR.rglob("*")):
        if path.is_dir() or _is_excluded(path):
            continue
        rel_dir = path.parent.relative_to(RESOURCES_DIR)
        dest_dir = PurePosixPath("pdf_reme/resources") / rel_dir
        entries.append((str(path), str(dest_dir)))
    return entries


def _version_tuple(version: str) -> tuple:
    parts = [int(part) for part in version.split(".")]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


VERSION_TUPLE = _version_tuple(APP_VERSION)
BUILD_YEAR = datetime.now(timezone.utc).year

# Uygulama, kaynaklarına `Path(__file__)` üzerinden `pdf_reme/resources`
# olarak ulaşır (bkz. __main__.py, i18n.py, sidebar.py, splash_screen.py).
# Frozen ortamda da aynı göreli yerleşimin korunması için hedef bu olmalı;
# yalnızca GitHub/README'e özgü görsel klasörleri (app_images, git_images)
# dışarıda bırakılır.
datas = _collect_resource_datas()
binaries = []
hiddenimports = ["PySide6.QtPdf", "PySide6.QtPdfWidgets"]

for package in ("qtawesome", "pikepdf"):
    package_datas, package_binaries, package_hiddenimports = collect_all(
        package
    )
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

VERSION_INFO = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=VERSION_TUPLE,
        prodvers=VERSION_TUPLE,
        mask=0x3F,
        flags=0x0,
        OS=0x4,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",
                    [
                        StringStruct("CompanyName", "Alper Temiz"),
                        StringStruct("FileDescription", "PDF-REME"),
                        StringStruct("FileVersion", APP_VERSION),
                        StringStruct("InternalName", "PDF-REME"),
                        StringStruct(
                            "LegalCopyright",
                            f"Copyright © {BUILD_YEAR} Alper Temiz",
                        ),
                        StringStruct("OriginalFilename", "PDF-REME.exe"),
                        StringStruct("ProductName", "PDF-REME"),
                        StringStruct("ProductVersion", APP_VERSION),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)

a = Analysis(
    [str(ENTRY_POINT)],
    pathex=[str(SRC_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PDF-REME",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX Qt/PDF DLL'lerini bozabildiği için kapalı.
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(APP_ICON)],
    version=VERSION_INFO,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PDF-REME",
)
