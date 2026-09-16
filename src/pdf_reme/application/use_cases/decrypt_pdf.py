from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from pdf_reme.domain.repositories.document_repository import (
    DocumentRepository,
)
from pdf_reme.infrastructure.database.models.document import (
    Document,
)
from pdf_reme.infrastructure.pdf.pdf_security_service import (
    PdfSecurityService,
)
from pdf_reme.shared.paths.app_paths import (
    AppPaths,
)


class DecryptPdfUseCase:
    def __init__(
        self,
        repository: DocumentRepository,
        security_service: PdfSecurityService,
        paths: AppPaths,
    ) -> None:
        self.repository = repository
        self.security_service = security_service
        self.paths = paths

    def execute(
        self,
        input_path: str | Path,
        display_name: str,
        password: str,
    ) -> Document:
        clean_name = self._validate_name(
            display_name
        )

        output_path = self._create_output_path(
            clean_name
        )

        try:
            result = self.security_service.decrypt(
                input_path=input_path,
                output_path=output_path,
                password=password,
            )

            document = Document(
                display_name=output_path.name,
                stored_path=str(output_path),
                original_path=None,
                document_type="pdf",
                library_section="generated",
                generation_type="pdf_decrypt",
                sha256=sha256(
                    output_path.read_bytes()
                ).hexdigest(),
                file_size=(
                    output_path.stat().st_size
                ),
                page_count=result.page_count,
                is_favorite=False,
                status="active",
            )

            return self.repository.add(
                document
            )

        except Exception:
            if output_path.exists():
                output_path.unlink()

            raise

    def _validate_name(
        self,
        display_name: str,
    ) -> str:
        clean_name = display_name.strip()

        if not clean_name:
            raise ValueError(
                "Çıktı dosya adı gereklidir."
            )

        if (
            "/" in clean_name
            or "\\" in clean_name
            or Path(clean_name).name
            != clean_name
        ):
            raise ValueError(
                "Dosya adı klasör yolu içeremez."
            )

        if not clean_name.lower().endswith(
            ".pdf"
        ):
            clean_name += ".pdf"

        return clean_name

    def _create_output_path(
        self,
        file_name: str,
    ) -> Path:
        self.paths.generated_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        requested = (
            self.paths.generated_dir
            / file_name
        )

        if not requested.exists():
            return requested

        path = Path(file_name)

        return (
            self.paths.generated_dir
            / (
                f"{path.stem}_"
                f"{uuid4().hex[:8]}"
                f"{path.suffix}"
            )
        )