from dataclasses import dataclass
from pathlib import Path

from pdf_reme.application.services.file_inspection_service import (
    FileInspectionService,
)
from pdf_reme.domain.repositories.document_repository import (
    DocumentRepository,
)
from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.infrastructure.filesystem.library_file_copy import (
    copy_file_to_library,
)
from pdf_reme.shared.paths.app_paths import AppPaths


@dataclass(frozen=True)
class ImportDocumentResult:
    imported: bool
    document: Document | None
    duplicate_document: Document | None
    error: str | None = None


class ImportDocumentUseCase:
    def __init__(
        self,
        repository: DocumentRepository,
        inspection_service: FileInspectionService,
        paths: AppPaths,
    ) -> None:
        self.repository = repository
        self.inspection_service = inspection_service
        self.paths = paths

    def execute(
        self,
        source_path: str | Path,
    ) -> ImportDocumentResult:
        source = Path(source_path)

        inspection = self.inspection_service.inspect(source)

        if not inspection.is_valid:
            return ImportDocumentResult(
                imported=False,
                document=None,
                duplicate_document=None,
                error=inspection.validation.error,
            )

        if inspection.is_duplicate:
            return ImportDocumentResult(
                imported=False,
                document=None,
                duplicate_document=inspection.duplicate_document,
                error=None,
            )

        copied_path = copy_file_to_library(
            source_path=source,
            document_type=inspection.validation.document_type,
            paths=self.paths,
        )

        try:
            document = Document(
                display_name=source.name,
                stored_path=str(copied_path),
                original_path=str(source.resolve()),
                document_type=inspection.validation.document_type,
                library_section="imported",
                generation_type=None,
                sha256=inspection.sha256,
                file_size=copied_path.stat().st_size,
                page_count=None,
            )

            self.repository.add(document)

        except Exception:
            if copied_path.exists():
                copied_path.unlink()

            raise

        return ImportDocumentResult(
            imported=True,
            document=document,
            duplicate_document=None,
            error=None,
        )