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
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

# SPECPATH: PyInstaller'ın sağladığı, spec dosyasının bulunduğu klasör.
PROJECT_ROOT = Path(SPECPATH).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
PACKAGE_DIR = SRC_DIR / "pdf_reme"
RESOURCES_DIR = PACKAGE_DIR / "resources"
ENTRY_POINT = PROJECT_ROOT / "start_app.py"
APP_ICON = RESOURCES_DIR / "images" / "icon.png"

# Uygulama, kaynaklarına `Path(__file__)` üzerinden `pdf_reme/resources`
# olarak ulaşır (bkz. __main__.py, i18n.py, sidebar.py, splash_screen.py).
# Frozen ortamda da aynı göreli yerleşimin korunması için hedef bu olmalı.
datas = [(str(RESOURCES_DIR), "pdf_reme/resources")]
binaries = []
hiddenimports = ["PySide6.QtPdf", "PySide6.QtPdfWidgets"]

for package in ("qtawesome", "pikepdf"):
    package_datas, package_binaries, package_hiddenimports = collect_all(
        package
    )
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports


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
