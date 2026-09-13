import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pypdf import PdfReader, PdfWriter

from pdf_reme.application.use_cases.merge_pdfs import MergePdfsUseCase
from pdf_reme.infrastructure.database.connection import SessionLocal
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.pdf.pdf_merge_service import PdfMergeService
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


def main() -> None:
    paths = AppPaths()
    paths.ensure_directories()

    session = SessionLocal()

    try:
        repository = SQLAlchemyDocumentRepository(
            session
        )

        merge_service = PdfMergeService()

        use_case = MergePdfsUseCase(
            repository=repository,
            merge_service=merge_service,
            paths=paths,
        )

        print("=== PDF-REME GERÇEK PDF MERGE TESTİ ===")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            first = temp_path / "first.pdf"
            second = temp_path / "second.pdf"

            create_pdf(
                first,
                [101, 102],
            )

            create_pdf(
                second,
                [201],
            )

            print()
            print("Kaynak PDF'ler oluşturuldu:")
            print(f"1. {first}")
            print(f"2. {second}")

            print()
            print(
                "Birleştirme sırası: "
                "second.pdf -> first.pdf"
            )

            document = use_case.execute(
                input_paths=[
                    second,
                    first,
                ],
                display_name="manual-merge-test.pdf",
            )

            session.flush()

            output_path = Path(
                document.stored_path
            )

            reader = PdfReader(
                str(output_path)
            )

            widths = [
                int(float(page.mediabox.width))
                for page in reader.pages
            ]

            print()
            print("Üretilen PDF:")
            print(output_path)

            print()
            print(f"Sayfa sayısı: {document.page_count}")
            print(f"Dosya boyutu: {document.file_size} byte")
            print(f"SHA-256: {document.sha256}")

            print()
            print(f"Sayfa sırası kontrolü: {widths}")

            assert output_path.exists()
            assert document.library_section == "generated"
            assert document.generation_type == "merge"
            assert document.status == "active"
            assert document.page_count == 3

            assert widths == [
                201,
                101,
                102,
            ]

            assert repository.get_by_id(
                document.id
            ) is not None

            session.commit()

            print()
            print("SONUÇ: GERÇEK PDF MERGE TESTİ BAŞARILI")

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()