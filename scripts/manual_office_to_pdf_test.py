import sys
from pathlib import Path

PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

SRC_DIR = (
    PROJECT_ROOT / "src"
)

if str(SRC_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(SRC_DIR),
    )

from pypdf import PdfReader

from pdf_reme.application.use_cases.convert_office_to_pdf import (
    ConvertOfficeToPdfUseCase,
)
from pdf_reme.infrastructure.conversion.office_to_pdf_service import (
    OfficeToPdfService,
)
from pdf_reme.infrastructure.database.connection import (
    SessionLocal,
)
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.shared.paths.app_paths import (
    AppPaths,
)


def main() -> None:
    if len(sys.argv) != 4:
        print(
            "Kullanım:"
        )
        print(
            "python scripts/"
            "manual_office_to_pdf_test.py "
            '"test.docx" '
            '"test.pptx" '
            '"test.xlsx"'
        )
        raise SystemExit(1)

    source_paths = [
        Path(argument)
        for argument
        in sys.argv[1:]
    ]

    paths = AppPaths()
    paths.ensure_directories()

    session = SessionLocal()

    try:
        repository = (
            SQLAlchemyDocumentRepository(
                session
            )
        )

        service = OfficeToPdfService()

        use_case = (
            ConvertOfficeToPdfUseCase(
                repository=repository,
                conversion_service=service,
                paths=paths,
            )
        )

        print(
            "=== PDF-REME "
            "OFFICE → PDF TESTİ ==="
        )

        for source_path in source_paths:
            print()
            print(
                f"Kaynak: {source_path}"
            )

            if not source_path.exists():
                raise FileNotFoundError(
                    source_path
                )

            source_before = (
                source_path.read_bytes()
            )

            output_name = (
                "manual-"
                f"{source_path.stem}.pdf"
            )

            document = use_case.execute(
                input_path=source_path,
                display_name=output_name,
            )

            output_path = Path(
                document.stored_path
            )

            reader = PdfReader(
                str(output_path)
            )

            assert output_path.exists()
            assert len(reader.pages) > 0

            assert (
                source_path.read_bytes()
                == source_before
            )

            assert repository.get_by_id(
                document.id
            ) is not None

            print(
                "Çıktı: "
                f"{output_path}"
            )
            print(
                "Sayfa sayısı: "
                f"{len(reader.pages)}"
            )
            print(
                "Generation type: "
                f"{document.generation_type}"
            )
            print(
                "Kaynak değişmedi: BAŞARILI"
            )
            print(
                "DB kaydı: BAŞARILI"
            )
            print(
                "SONUÇ: BAŞARILI"
            )

        session.commit()

        print()
        print(
            "SONUÇ: GERÇEK "
            "OFFICE → PDF TESTİ BAŞARILI"
        )

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()