from pathlib import Path

from pdf_reme.application.services.duplicate_detection_service import (
    DuplicateDetectionService,
)
from pdf_reme.application.services.file_inspection_service import (
    FileInspectionService,
)
from pdf_reme.application.use_cases.import_document import (
    ImportDocumentResult,
    ImportDocumentUseCase,
)
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.database.session import session_scope
from pdf_reme.shared.paths.app_paths import AppPaths


class ImportDocumentService:
    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths

    def import_document(
        self,
        source_path: str | Path,
    ) -> ImportDocumentResult:
        with session_scope() as session:
            repository = SQLAlchemyDocumentRepository(session)

            duplicate_service = DuplicateDetectionService(
                repository
            )

            inspection_service = FileInspectionService(
                duplicate_service
            )

            use_case = ImportDocumentUseCase(
                repository=repository,
                inspection_service=inspection_service,
                paths=self.paths,
            )

            return use_case.execute(source_path)