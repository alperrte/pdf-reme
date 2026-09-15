import sys
import tempfile
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pypdf import PdfReader, PdfWriter

from pdf_reme.application.services.page_edit_history import (
    PageEditHistory,
)
from pdf_reme.application.use_cases.edit_pdf_pages import (
    EditPdfPagesUseCase,
)
from pdf_reme.infrastructure.database.connection import SessionLocal
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.pdf.pdf_page_edit_service import (
    PdfPageEditService,
)
from pdf_reme.shared.paths.app_paths import AppPaths


def create_pdf(
    path: Path,
    page_widths: list[int],
) -> None:
    writer = PdfWriter()

    for width in page_widths:
        writer.add_blank_page(
            width=width,
            height=842,
        )

    with path.open("wb") as file:
        writer.write(file)


def get_page_widths(
    path: Path,
) -> list[int]:
    reader = PdfReader(str(path))

    return [
        int(float(page.mediabox.width))
        for page in reader.pages
    ]


def main() -> None:
    paths = AppPaths()
    paths.ensure_directories()

    session = SessionLocal()

    try:
        repository = SQLAlchemyDocumentRepository(
            session
        )

        use_case = EditPdfPagesUseCase(
            repository=repository,
            page_edit_service=PdfPageEditService(),
            paths=paths,
        )

        test_id = uuid4().hex[:8]

        print(
            "=== PDF-REME GÜN 11 GERÇEK "
            "SAYFA DÜZENLEME TESTİ ==="
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            source = temp_path / "source.pdf"
            insert_source = temp_path / "insert-source.pdf"

            create_pdf(
                source,
                [101, 102, 103, 104],
            )

            create_pdf(
                insert_source,
                [201, 202, 203],
            )

            source_before = source.read_bytes()
            insert_before = insert_source.read_bytes()

            print()
            print(
                f"Kaynak PDF: {get_page_widths(source)}"
            )
            print(
                "Eklenecek PDF: "
                f"{get_page_widths(insert_source)}"
            )

            # 1. ROTATE
            rotated = use_case.rotate_pages(
                input_path=source,
                page_numbers=[2, 4],
                degrees=90,
                display_name=(
                    f"manual-rotate-{test_id}.pdf"
                ),
            )

            rotated_path = Path(
                rotated.stored_path
            )

            rotated_reader = PdfReader(
                str(rotated_path)
            )

            rotations = [
                page.rotation
                for page in rotated_reader.pages
            ]

            assert rotations == [
                0,
                90,
                0,
                90,
            ]

            print()
            print("1. Sayfa döndürme:")
            print(f"Rotation değerleri: {rotations}")
            print("SONUÇ: BAŞARILI")

            # 2. DUPLICATE
            duplicated = use_case.duplicate_pages(
                input_path=source,
                page_numbers=[2, 4],
                display_name=(
                    f"manual-duplicate-{test_id}.pdf"
                ),
            )

            duplicated_path = Path(
                duplicated.stored_path
            )

            duplicated_widths = get_page_widths(
                duplicated_path
            )

            assert duplicated_widths == [
                101,
                102,
                102,
                103,
                104,
                104,
            ]

            print()
            print("2. Sayfa çoğaltma:")
            print(
                f"Yeni sıra: {duplicated_widths}"
            )
            print("SONUÇ: BAŞARILI")

            # 3. INSERT FROM ANOTHER PDF
            inserted = use_case.insert_pages(
                input_path=source,
                insert_pdf_path=insert_source,
                source_page_numbers=[3, 1],
                after_page=2,
                display_name=(
                    f"manual-insert-{test_id}.pdf"
                ),
            )

            inserted_path = Path(
                inserted.stored_path
            )

            inserted_widths = get_page_widths(
                inserted_path
            )

            assert inserted_widths == [
                101,
                102,
                203,
                201,
                103,
                104,
            ]

            print()
            print(
                "3. Başka PDF'den sayfa ekleme:"
            )
            print(
                f"Yeni sıra: {inserted_widths}"
            )
            print("SONUÇ: BAŞARILI")

            # 4. BLANK PAGE
            blank = use_case.insert_blank_page(
                input_path=source,
                after_page=2,
                display_name=(
                    f"manual-blank-{test_id}.pdf"
                ),
            )

            blank_path = Path(
                blank.stored_path
            )

            blank_reader = PdfReader(
                str(blank_path)
            )

            assert len(blank_reader.pages) == 5

            print()
            print("4. Boş sayfa ekleme:")
            print(
                f"Yeni sayfa sayısı: "
                f"{len(blank_reader.pages)}"
            )
            print("SONUÇ: BAŞARILI")

            # 5. UNDO / REDO HISTORY
            history = PageEditHistory(source)

            history.push(
                rotated_path,
                "rotate",
            )

            history.push(
                duplicated_path,
                "duplicate",
            )

            undo_state = history.undo()

            assert (
                Path(undo_state.file_path)
                == rotated_path
            )

            redo_state = history.redo()

            assert (
                Path(redo_state.file_path)
                == duplicated_path
            )

            print()
            print("5. Undo / Redo geçmişi:")
            print(
                f"Undo → "
                f"{Path(undo_state.file_path).name}"
            )
            print(
                f"Redo → "
                f"{Path(redo_state.file_path).name}"
            )
            print("SONUÇ: BAŞARILI")

            # Kaynaklar değişmemeli.
            assert source.read_bytes() == source_before
            assert (
                insert_source.read_bytes()
                == insert_before
            )

            # DB kayıtları doğrulansın.
            documents = [
                rotated,
                duplicated,
                inserted,
                blank,
            ]

            for document in documents:
                assert repository.get_by_id(
                    document.id
                ) is not None

            assert (
                rotated.generation_type
                == "page_rotate"
            )
            assert (
                duplicated.generation_type
                == "page_duplicate"
            )
            assert (
                inserted.generation_type
                == "page_insert"
            )
            assert (
                blank.generation_type
                == "page_blank_insert"
            )

            session.commit()

            print()
            print(
                "Kaynak PDF'ler değişmedi: BAŞARILI"
            )
            print(
                "Generated DB kayıtları: BAŞARILI"
            )

            print()
            print(
                "SONUÇ: PDF "
                "SAYFA DÜZENLEME TESTİ BAŞARILI"
            )

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()