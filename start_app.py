import ctypes
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


if sys.platform == "win32":
    APP_ID = "PDF-REME.DesktopApp"

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        APP_ID
    )


from pdf_reme.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main())