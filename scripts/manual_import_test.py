import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pdf_reme.application.services.import_document_service import (
    ImportDocumentService,
)
from pdf_reme.shared.paths.app_paths import AppPaths


def main():
    if len(sys.argv) != 2:
        print("Kullanım: python scripts/manual_import_test.py <dosya_yolu>")
        return 1

    source_path = Path(sys.argv[1])

    paths = AppPaths()
    paths.ensure_directories()

    service = ImportDocumentService(paths)
    result = service.import_document(source_path)

    if result.imported:
        print("IMPORT BAŞARILI")
        print(f"Kaynak: {source_path}")
        print(f"Kütüphane: {paths.imported_pdf_dir}")
        return 0

    if result.duplicate_document is not None:
        print("DUPLICATE: Dosya daha önce içe aktarılmış.")
        return 0

    print(f"IMPORT BAŞARISIZ: {result.error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())