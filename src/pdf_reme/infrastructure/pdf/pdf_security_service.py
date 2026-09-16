from dataclasses import dataclass
from pathlib import Path

from pypdf import (
    PasswordType,
    PdfReader,
    PdfWriter,
)


@dataclass(frozen=True)
class PdfSecurityResult:
    output_path: Path
    page_count: int
    encrypted: bool


class PdfSecurityService:
    ENCRYPTION_ALGORITHM = "AES-256-R5"

    def encrypt(
        self,
        input_path: str | Path,
        output_path: str | Path,
        password: str,
        owner_password: str | None = None,
    ) -> PdfSecurityResult:
        source_path = Path(input_path)
        target_path = Path(output_path)

        self._validate_paths(
            source_path,
            target_path,
        )

        self._validate_password(password)

        reader = PdfReader(
            str(source_path)
        )

        if reader.is_encrypted:
            raise ValueError(
                "PDF zaten şifreli."
            )

        page_count = len(reader.pages)

        target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            writer = PdfWriter(
                clone_from=reader
            )

            writer.encrypt(
                user_password=password,
                owner_password=(
                    owner_password
                    if owner_password
                    else password
                ),
                algorithm=(
                    self.ENCRYPTION_ALGORITHM
                ),
            )

            with target_path.open(
                "wb"
            ) as file:
                writer.write(file)

            self._validate_encrypted_output(
                target_path,
                password,
                page_count,
            )

        except Exception:
            if target_path.exists():
                target_path.unlink()

            raise

        return PdfSecurityResult(
            output_path=target_path,
            page_count=page_count,
            encrypted=True,
        )

    def decrypt(
        self,
        input_path: str | Path,
        output_path: str | Path,
        password: str,
    ) -> PdfSecurityResult:
        source_path = Path(input_path)
        target_path = Path(output_path)

        self._validate_paths(
            source_path,
            target_path,
        )

        self._validate_password(password)

        reader = PdfReader(
            str(source_path)
        )

        if not reader.is_encrypted:
            raise ValueError(
                "PDF şifreli değil."
            )

        password_result = reader.decrypt(
            password
        )

        if (
            password_result
            == PasswordType.NOT_DECRYPTED
        ):
            raise ValueError(
                "PDF parolası yanlış."
            )

        page_count = len(reader.pages)

        target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            writer = PdfWriter(
                clone_from=reader
            )

            with target_path.open(
                "wb"
            ) as file:
                writer.write(file)

            self._validate_decrypted_output(
                target_path,
                page_count,
            )

        except Exception:
            if target_path.exists():
                target_path.unlink()

            raise

        return PdfSecurityResult(
            output_path=target_path,
            page_count=page_count,
            encrypted=False,
        )

    def _validate_paths(
        self,
        source_path: Path,
        output_path: Path,
    ) -> None:
        if not source_path.exists():
            raise FileNotFoundError(
                f"PDF bulunamadı: {source_path}"
            )

        if not source_path.is_file():
            raise ValueError(
                "Kaynak bir dosya olmalıdır."
            )

        if (
            source_path.suffix.lower()
            != ".pdf"
        ):
            raise ValueError(
                "Yalnızca PDF dosyaları "
                "işlenebilir."
            )

        if (
            output_path.suffix.lower()
            != ".pdf"
        ):
            raise ValueError(
                "Çıktı dosyası PDF olmalıdır."
            )

        if (
            source_path.resolve()
            == output_path.resolve()
        ):
            raise ValueError(
                "Kaynak PDF'nin üzerine "
                "yazılamaz."
            )

    def _validate_password(
        self,
        password: str,
    ) -> None:
        if not password:
            raise ValueError(
                "PDF parolası boş olamaz."
            )

        if not password.strip():
            raise ValueError(
                "PDF parolası yalnızca "
                "boşluklardan oluşamaz."
            )

    def _validate_encrypted_output(
        self,
        output_path: Path,
        password: str,
        expected_page_count: int,
    ) -> None:
        if (
            not output_path.exists()
            or output_path.stat().st_size == 0
        ):
            raise RuntimeError(
                "Şifreli PDF oluşturulamadı."
            )

        reader = PdfReader(
            str(output_path)
        )

        if not reader.is_encrypted:
            raise RuntimeError(
                "Oluşturulan PDF şifreli değil."
            )

        result = reader.decrypt(
            password
        )

        if result == PasswordType.NOT_DECRYPTED:
            raise RuntimeError(
                "Şifreli PDF doğrulanamadı."
            )

        if (
            len(reader.pages)
            != expected_page_count
        ):
            raise RuntimeError(
                "Şifreleme sonrasında "
                "sayfa sayısı değişti."
            )

    def _validate_decrypted_output(
        self,
        output_path: Path,
        expected_page_count: int,
    ) -> None:
        if (
            not output_path.exists()
            or output_path.stat().st_size == 0
        ):
            raise RuntimeError(
                "Kilidi açılmış PDF oluşturulamadı."
            )

        reader = PdfReader(
            str(output_path)
        )

        if reader.is_encrypted:
            raise RuntimeError(
                "PDF kilidi kaldırılamadı."
            )

        if (
            len(reader.pages)
            != expected_page_count
        ):
            raise RuntimeError(
                "Şifre çözme sonrasında "
                "sayfa sayısı değişti."
            )