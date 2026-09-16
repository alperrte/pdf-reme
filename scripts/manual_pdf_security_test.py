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

from pypdf import (
    PasswordType,
    PdfReader,
)

from pdf_reme.application.use_cases.decrypt_pdf import (
    DecryptPdfUseCase,
)
from pdf_reme.application.use_cases.encrypt_pdf import (
    EncryptPdfUseCase,
)
from pdf_reme.infrastructure.database.connection import (
    SessionLocal,
)
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.pdf.pdf_security_service import (
    PdfSecurityService,
)
from pdf_reme.shared.paths.app_paths import (
    AppPaths,
)


PASSWORD = "PDF-REME-123"


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Kullanım:"
        )
        print(
            'python scripts/'
            'manual_pdf_security_test.py '
            '"C:\\Test\\test.pdf"'
        )
        raise SystemExit(1)

    source = Path(
        sys.argv[1]
    )

    if not source.exists():
        raise FileNotFoundError(
            source
        )

    source_before = (
        source.read_bytes()
    )

    original_reader = PdfReader(
        str(source)
    )

    original_page_count = len(
        original_reader.pages
    )

    paths = AppPaths()
    paths.ensure_directories()

    session = SessionLocal()

    try:
        repository = (
            SQLAlchemyDocumentRepository(
                session
            )
        )

        service = PdfSecurityService()

        encrypt_use_case = EncryptPdfUseCase(
            repository,
            service,
            paths,
        )

        decrypt_use_case = DecryptPdfUseCase(
            repository,
            service,
            paths,
        )

        print(
            "=== PDF-REME PDF "
            "GÜVENLİK TESTİ ==="
        )

        encrypted_document = (
            encrypt_use_case.execute(
                input_path=source,
                display_name=(
                    "manual-locked.pdf"
                ),
                password=PASSWORD,
            )
        )

        encrypted_path = Path(
            encrypted_document.stored_path
        )

        encrypted_reader = PdfReader(
            str(encrypted_path)
        )

        assert encrypted_reader.is_encrypted

        wrong_result = (
            encrypted_reader.decrypt(
                "wrong-password"
            )
        )

        assert (
            wrong_result
            == PasswordType.NOT_DECRYPTED
        )

        encrypted_reader = PdfReader(
            str(encrypted_path)
        )

        correct_result = (
            encrypted_reader.decrypt(
                PASSWORD
            )
        )

        assert (
            correct_result
            != PasswordType.NOT_DECRYPTED
        )

        assert (
            len(encrypted_reader.pages)
            == original_page_count
        )

        print()
        print(
            "PDF şifreleme: BAŞARILI"
        )
        print(
            "Yanlış parola reddedildi: "
            "BAŞARILI"
        )
        print(
            "Doğru parola kabul edildi: "
            "BAŞARILI"
        )

        unlocked_document = (
            decrypt_use_case.execute(
                input_path=encrypted_path,
                display_name=(
                    "manual-unlocked.pdf"
                ),
                password=PASSWORD,
            )
        )

        unlocked_path = Path(
            unlocked_document.stored_path
        )

        unlocked_reader = PdfReader(
            str(unlocked_path)
        )

        assert not unlocked_reader.is_encrypted

        assert (
            len(unlocked_reader.pages)
            == original_page_count
        )

        assert (
            source.read_bytes()
            == source_before
        )

        print()
        print(
            "PDF kilit kaldırma: BAŞARILI"
        )
        print(
            "Sayfa sayısı korundu: BAŞARILI"
        )
        print(
            "Kaynak PDF değişmedi: BAŞARILI"
        )
        print(
            "Generated DB kayıtları: BAŞARILI"
        )

        session.commit()

        print()
        print(
            "SONUÇ: GERÇEK PDF "
            "GÜVENLİK TESTİ BAŞARILI"
        )

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()