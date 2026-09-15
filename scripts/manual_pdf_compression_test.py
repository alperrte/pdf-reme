import sys
from pathlib import Path

PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(SRC_DIR),
    )

from pdf_reme.application.use_cases.compress_pdf import (
    CompressPdfUseCase,
)
from pdf_reme.infrastructure.database.connection import (
    SessionLocal,
)
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.pdf.pdf_compression_service import (
    PdfCompressionService,
)
from pdf_reme.shared.paths.app_paths import (
    AppPaths,
)


def mb(size: int) -> float:
    return round(
        size / 1024 / 1024,
        2,
    )


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Kullanım:"
        )
        print(
            'python scripts/'
            'manual_pdf_compression_test.py '
            '"C:\\Test\\test.pdf"'
        )
        raise SystemExit(1)

    source = Path(
        sys.argv[1]
    )

    if not source.exists():
        raise FileNotFoundError(source)

    source_before = source.read_bytes()

    paths = AppPaths()
    paths.ensure_directories()

    session = SessionLocal()

    try:
        repository = (
            SQLAlchemyDocumentRepository(
                session
            )
        )

        use_case = CompressPdfUseCase(
            repository,
            PdfCompressionService(),
            paths,
        )

        print(
            "=== PDF-REME PDF "
            "SIKIŞTIRMA TESTİ ==="
        )

        for level in (
            "light",
            "balanced",
            "strong",
        ):
            result = use_case.execute(
                input_path=source,
                display_name=(
                    f"manual-compress-"
                    f"{level}.pdf"
                ),
                level=level,
            )

            print()
            print(
                f"Seviye: {level}"
            )
            print(
                "Orijinal: "
                f"{mb(result.original_size)} MB"
            )
            print(
                "Yeni: "
                f"{mb(result.compressed_size)} MB"
            )
            print(
                "Kazanç: "
                f"%{result.savings_percent}"
            )
            print(
                "Kaynak fallback: "
                f"{result.used_original_fallback}"
            )
            print(
                "SONUÇ: BAŞARILI"
            )

        assert (
            source.read_bytes()
            == source_before
        )

        session.commit()

        print()
        print(
            "Kaynak PDF değişmedi: BAŞARILI"
        )

        print(
            "SONUÇ: GERÇEK PDF "
            "SIKIŞTIRMA TESTİ BAŞARILI"
        )

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()