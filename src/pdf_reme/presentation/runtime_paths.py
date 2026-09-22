import sys
from pathlib import Path


def application_root() -> Path:
    """Uygulamanın kök klasörü.

    Paketlenmiş (PyInstaller) ortamda `PDF-REME.exe`'nin bulunduğu klasör;
    geliştirmede proje kökü. Portable dağıtımda `runtime/` klasörü burada
    durur ve `_internal/` (uygulama dosyaları) ile mantıksal olarak ayrıdır.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parents[3]


def bundled_libreoffice_dir() -> Path | None:
    """Portable paketle gelen LibreOffice klasörü; yoksa None.

    Beklenen yerleşim: `<kök>/runtime/libreoffice/program/soffice.exe`.
    None dönerse `OfficeToPdfService` sistemde kurulu LibreOffice'i
    (standart konumlar, ardından PATH) arar.
    """
    runtime_dir = application_root() / "runtime" / "libreoffice"

    program_dir = runtime_dir / "program"

    for executable in ("soffice.exe", "soffice.com", "soffice"):
        if (program_dir / executable).is_file():
            return runtime_dir

    return None
