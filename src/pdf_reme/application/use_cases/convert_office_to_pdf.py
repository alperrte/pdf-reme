from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader

from pdf_reme.domain.repositories.document_repository import (
    DocumentRepository,
)
from pdf_reme.infrastructure.conversion.office_to_pdf_service import (
    OfficeToPdfService,
)
from pdf_reme.infrastructure.database.models.document import (
    Document,
)
from pdf_reme.shared.paths.app_paths import AppPaths


class ConvertOfficeToPdfUseCase:
    WORD_EXTENSIONS = {
        ".doc",
        ".docx",
    }

    POWERPOINT_EXTENSIONS = {
        ".ppt",
        ".pptx",
    }

    EXCEL_EXTENSIONS = {
        ".xls",
        ".xlsx",
    }

    def __init__(
        self,
        repository: DocumentRepository,
        conversion_service: OfficeToPdfService,
        paths: AppPaths,
    ) -> None:
        self.repository = repository
        self.conversion_service = conversion_service
        self.paths = paths

    def execute(
        self,
        input_path: str | Path,
        display_name: str,
    ) -> Document:
        source_path = Path(input_path)

        clean_name = self._validate_name(
            display_name
        )

        output_path = self._create_output_path(
            clean_name
        )

        generation_type = (
            self._get_generation_type(
                source_path
            )
        )

        try:
            self.conversion_service.convert(
                input_path=source_path,
                output_path=output_path,
            )

            reader = PdfReader(
                str(output_path)
            )

            document = Document(
                display_name=output_path.name,
                stored_path=str(output_path),
                original_path=None,
                document_type="pdf",
                library_section="generated",
                generation_type=generation_type,
                sha256=sha256(
                    output_path.read_bytes()
                ).hexdigest(),
                file_size=(
                    output_path.stat().st_size
                ),
                page_count=len(reader.pages),
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

    def _get_generation_type(
        self,
        source_path: Path,
    ) -> str:
        extension = (
            source_path.suffix.lower()
        )

        if extension in self.WORD_EXTENSIONS:
            return "word_to_pdf"

        if (
            extension
            in self.POWERPOINT_EXTENSIONS
        ):
            return "powerpoint_to_pdf"

        if extension in self.EXCEL_EXTENSIONS:
            return "excel_to_pdf"

        raise ValueError(
            "Desteklenmeyen Office dosya türü."
        )

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

        requested_path = (
            self.paths.generated_dir
            / file_name
        )

        if not requested_path.exists():
            return requested_path

        file_path = Path(file_name)

        unique_name = (
            f"{file_path.stem}_"
            f"{uuid4().hex[:8]}"
            f"{file_path.suffix}"
        )

        return (
            self.paths.generated_dir
            / unique_name
        )