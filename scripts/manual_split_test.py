import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pypdf import PdfReader, PdfWriter

from pdf_reme.application.services.page_selection_parser import (
    PageSelectionParser,
)
from pdf_reme.application.use_cases.split_pdf import SplitPdfUseCase
from pdf_reme.infrastructure.database.connection import SessionLocal
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.pdf.pdf_split_service import PdfSplitService
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


def get_widths(path: Path) -> list[int]:
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

        service = PdfSplitService()
        parser = PageSelectionParser()

        use_case = SplitPdfUseCase(
            repository=repository,
            split_service=service,
            parser=parser,
            paths=paths,
        )

        print("=== PDF-REME GERÇEK PDF SPLIT TESTİ ===")

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
                    106,
                    107,
                    108,
                    109,
                    110,
                ],
            )

            print()
            print(f"Kaynak PDF: {source}")
            print("Toplam sayfa: 10")

            selected = use_case.extract_selected_pages(
                input_path=source,
                page_expression="2,5,8-10",
                display_name="manual-split-selected.pdf",
            )

            selected_path = Path(
                selected.stored_path
            )

            selected_widths = get_widths(
                selected_path
            )

            print()
            print("1. Seçili sayfa çıkarma:")
            print(f"Çıktı: {selected_path}")
            print(
                f"Sayfa sırası: {selected_widths}"
            )

            assert selected_widths == [
                102,
                105,
                108,
                109,
                110,
            ]

            parts = use_case.split_into_parts(
                input_path=source,
                part_count=4,
                base_name="manual-split-quarter",
            )

            part_counts = [
                document.page_count
                for document in parts
            ]

            print()
            print("2. Dört parçaya bölme:")
            print(
                f"Parça sayfa adetleri: {part_counts}"
            )

            assert part_counts == [
                3,
                3,
                2,
                2,
            ]

            all_widths = []

            for document in parts:
                all_widths.extend(
                    get_widths(
                        Path(document.stored_path)
                    )
                )

            print(
                f"Tüm sayfalar: {all_widths}"
            )

            assert all_widths == [
                101,
                102,
                103,
                104,
                105,
                106,
                107,
                108,
                109,
                110,
            ]

            groups = use_case.split_by_groups(
                input_path=source,
                page_groups=[
                    [1, 3],
                    [5, 7, 9],
                    [10],
                ],
                base_name="manual-split-groups",
            )

            print()
            print("3. Özel sayfa grupları:")

            for index, document in enumerate(
                groups,
                start=1,
            ):
                output_path = Path(
                    document.stored_path
                )

                print(
                    f"Grup {index}: "
                    f"{get_widths(output_path)}"
                )

            session.commit()

            print()
            print(
                "SONUÇ: GERÇEK PDF SPLIT TESTİ BAŞARILI"
            )

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()