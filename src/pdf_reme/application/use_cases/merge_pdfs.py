from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader

from pdf_reme.domain.repositories.document_repository import DocumentRepository
from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.infrastructure.pdf.pdf_merge_service import PdfMergeService
from pdf_reme.shared.paths.app_paths import AppPaths


class MergePdfsUseCase:
    def __init__(
        self,
        repository: DocumentRepository,
        merge_service: PdfMergeService,
        paths: AppPaths,
    ) -> None:
        self.repository = repository
        self.merge_service = merge_service
        self.paths = paths

    def execute(
        self,
        input_paths: list[str | Path],
        display_name: str,
    ) -> Document:
        clean_name = display_name.strip()

        if not clean_name:
            raise ValueError(
                "Birleştirilmiş PDF için dosya adı gereklidir."
            )

        if (
            "/" in clean_name
            or "\\" in clean_name
            or Path(clean_name).name != clean_name
        ):
            raise ValueError(
                "Dosya adı klasör yolu içeremez."
            )
        if not clean_name.lower().endswith(".pdf"):
            clean_name += ".pdf"

        self.paths.generated_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = self._create_output_path(
            clean_name
        )

        try:
            self.merge_service.merge(
                input_paths=input_paths,
                output_path=output_path,
            )

            file_bytes = output_path.read_bytes()

            file_hash = sha256(
                file_bytes
            ).hexdigest()

            reader = PdfReader(
                str(output_path)
            )

            document = Document(
                display_name=clean_name,
                stored_path=str(output_path),
                original_path=None,
                document_type="pdf",
                library_section="generated",
                generation_type="merge",
                sha256=file_hash,
                file_size=output_path.stat().st_size,
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

    def _create_output_path(
        self,
        file_name: str,
    ) -> Path:
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

    