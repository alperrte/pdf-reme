import sys
import tempfile
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pypdf import PdfReader, PdfWriter

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

        page_edit_service = PdfPageEditService()

        use_case = EditPdfPagesUseCase(
            repository=repository,
            page_edit_service=page_edit_service,
            paths=paths,
        )

        test_id = uuid4().hex[:8]

        print("=== PDF-REME GERÇEK PDF SAYFA DÜZENLEME TESTİ ===")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            source = temp_path / "source.pdf"

            create_pdf(
                source,
                [
                    101,
                    102,
                    103,
                    104,
                    105,
                ],
            )

            source_before = source.read_bytes()

            print()
            print("Kaynak PDF oluşturuldu.")
            print(f"Sayfa sırası: {get_page_widths(source)}")

            # 1. REORDER
            reordered = use_case.reorder_pages(
                input_path=source,
                page_order=[
                    5,
                    1,
                    3,
                    2,
                    4,
                ],
                display_name=f"manual-reorder-{test_id}.pdf",
            )

            reordered_path = Path(
                reordered.stored_path
            )

            reordered_widths = get_page_widths(
                reordered_path
            )

            print()
            print("1. Sayfa sıralama:")
            print(f"Çıktı: {reordered_path}")
            print(
                f"Yeni sıra: {reordered_widths}"
            )

            assert reordered_widths == [
                105,
                101,
                103,
                102,
                104,
            ]

            # 2. SWAP
            swapped = use_case.swap_pages(
                input_path=source,
                first_page=2,
                second_page=5,
                display_name=f"manual-swap-{test_id}.pdf",
            )

            swapped_path = Path(
                swapped.stored_path
            )

            swapped_widths = get_page_widths(
                swapped_path
            )

            print()
            print("2. Sayfa yer değiştirme:")
            print(f"Çıktı: {swapped_path}")
            print(
                f"Yeni sıra: {swapped_widths}"
            )

            assert swapped_widths == [
                101,
                105,
                103,
                104,
                102,
            ]

            # 3. DELETE
            deleted = use_case.delete_pages(
                input_path=source,
                page_numbers=[
                    2,
                    4,
                ],
                display_name=f"manual-delete-{test_id}.pdf",
            )

            deleted_path = Path(
                deleted.stored_path
            )

            deleted_widths = get_page_widths(
                deleted_path
            )

            print()
            print("3. Sayfa silme:")
            print(f"Çıktı: {deleted_path}")
            print(
                f"Kalan sayfalar: {deleted_widths}"
            )

            assert deleted_widths == [
                101,
                103,
                105,
            ]

            # Kaynak PDF değişmemeli.
            assert source.read_bytes() == source_before

            # DB kayıtları oluşmuş olmalı.
            assert repository.get_by_id(
                reordered.id
            ) is not None

            assert repository.get_by_id(
                swapped.id
            ) is not None

            assert repository.get_by_id(
                deleted.id
            ) is not None

            assert reordered.generation_type == "page_reorder"
            assert swapped.generation_type == "page_swap"
            assert deleted.generation_type == "page_delete"

            session.commit()

            print()
            print("Kaynak PDF değişmedi: BAŞARILI")
            print("Generated DB kayıtları: BAŞARILI")

            print()
            print(
                "SONUÇ: GERÇEK PDF SAYFA DÜZENLEME TESTİ BAŞARILI"
            )

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()