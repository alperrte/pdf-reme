import sys
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pypdf import PdfWriter

from pdf_reme.application.services.trash_service import TrashService
from pdf_reme.infrastructure.database.connection import SessionLocal
from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.filesystem.trash_file_manager import (
    TrashFileManager,
)
from pdf_reme.shared.paths.app_paths import AppPaths


def main() -> None:
    paths = AppPaths()
    paths.ensure_directories()

    test_file = (
        paths.imported_pdf_dir
        / f"trash-manual-{uuid4().hex[:8]}.pdf"
    )

    writer = PdfWriter()
    writer.add_blank_page(
        width=595,
        height=842,
    )

    with test_file.open("wb") as file:
        writer.write(file)

    file_hash = sha256(
        test_file.read_bytes()
    ).hexdigest()

    print("=== PDF-REME ÇÖP KUTUSU GERÇEK DOSYA TESTİ ===")
    print(f"Oluşturulan test PDF: {test_file}")

    session = SessionLocal()

    try:
        repository = SQLAlchemyDocumentRepository(
            session
        )

        file_manager = TrashFileManager(
            paths
        )

        service = TrashService(
            repository=repository,
            file_manager=file_manager,
        )

        document = Document(
            display_name=test_file.name,
            stored_path=str(test_file),
            original_path=str(test_file),
            document_type="pdf",
            library_section="imported",
            generation_type=None,
            sha256=file_hash,
            file_size=test_file.stat().st_size,
            page_count=1,
            is_favorite=False,
            status="active",
        )

        repository.add(document)
        session.flush()

        document_id = document.id

        print()
        print("1. Kütüphane kaydı oluşturuldu.")
        print(f"Document ID: {document_id}")

        trashed = service.move_to_trash(
            document_id
        )

        trash_path = Path(
            trashed.stored_path
        )

        print()
        print("2. Dosya çöp kutusuna taşındı.")
        print(f"Trash yolu: {trash_path}")
        print(f"Dosya mevcut: {trash_path.exists()}")

        restored = service.restore(
            document_id
        )

        restored_path = Path(
            restored.stored_path
        )

        print()
        print("3. Dosya geri yüklendi.")
        print(f"Restore yolu: {restored_path}")
        print(f"Dosya mevcut: {restored_path.exists()}")

        trashed_again = service.move_to_trash(
            document_id
        )

        second_trash_path = Path(
            trashed_again.stored_path
        )

        print()
        print("4. Dosya tekrar çöp kutusuna taşındı.")
        print(f"Trash yolu: {second_trash_path}")

        service.permanently_delete(
            document_id
        )

        print()
        print("5. Dosya kalıcı olarak silindi.")

        assert not second_trash_path.exists()
        assert repository.get_by_id(document_id) is None

        session.commit()

        print()
        print("SONUÇ: GERÇEK DOSYA TESTİ BAŞARILI")

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()