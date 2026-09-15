from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader

from pdf_reme.domain.repositories.document_repository import (
    DocumentRepository,
)
from pdf_reme.infrastructure.database.models.document import (
    Document,
)
from pdf_reme.infrastructure.pdf.pdf_compression_service import (
    PdfCompressionResult,
    PdfCompressionService,
)
from pdf_reme.shared.paths.app_paths import AppPaths


@dataclass(frozen=True)
class CompressPdfResult:
    document: Document
    original_size: int
    compressed_size: int
    saved_bytes: int
    savings_percent: float
    level: str
    used_original_fallback: bool


class CompressPdfUseCase:
    def __init__(
        self,
        repository: DocumentRepository,
        compression_service: PdfCompressionService,
        paths: AppPaths,
    ) -> None:
        self.repository = repository
        self.compression_service = (
            compression_service
        )
        self.paths = paths

    def execute(
        self,
        input_path: str | Path,
        display_name: str,
        level: str = "balanced",
    ) -> CompressPdfResult:
        clean_name = self._validate_name(
            display_name
        )

        output_path = self._create_output_path(
            clean_name
        )

        generation_type = (
            f"pdf_compress_{level}"
        )

        try:
            compression_result = (
                self.compression_service.compress(
                    input_path=input_path,
                    output_path=output_path,
                    level=level,
                )
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
                generation_type=(
                    generation_type
                ),
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

            document = self.repository.add(
                document
            )

            return CompressPdfResult(
                document=document,
                original_size=(
                    compression_result
                    .original_size
                ),
                compressed_size=(
                    compression_result
                    .compressed_size
                ),
                saved_bytes=(
                    compression_result
                    .saved_bytes
                ),
                savings_percent=(
                    compression_result
                    .savings_percent
                ),
                level=level,
                used_original_fallback=(
                    compression_result
                    .used_original_fallback
                ),
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

        file_path = Path(file_name)

        return (
            self.paths.generated_dir
            / (
                f"{file_path.stem}_"
                f"{uuid4().hex[:8]}"
                f"{file_path.suffix}"
            )
        )