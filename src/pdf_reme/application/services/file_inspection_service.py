from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pdf_reme.application.services.duplicate_detection_service import (
    DuplicateDetectionService,
)
from pdf_reme.infrastructure.filesystem.file_validation import (
    FileValidationResult,
    validate_file,
)


@dataclass(frozen=True)
class FileInspectionResult:
    validation: FileValidationResult
    sha256: str | None
    duplicate_document: Any | None

    @property
    def is_valid(self) -> bool:
        return self.validation.is_valid

    @property
    def is_duplicate(self) -> bool:
        return self.duplicate_document is not None


class FileInspectionService:
    def __init__(
        self,
        duplicate_detection_service: DuplicateDetectionService,
    ) -> None:
        self.duplicate_detection_service = duplicate_detection_service

    def inspect(self, file_path: str | Path) -> FileInspectionResult:
        validation = validate_file(file_path)

        if not validation.is_valid:
            return FileInspectionResult(
                validation=validation,
                sha256=None,
                duplicate_document=None,
            )

        sha256, duplicate_document = (
            self.duplicate_detection_service.find_duplicate(file_path)
        )

        return FileInspectionResult(
            validation=validation,
            sha256=sha256,
            duplicate_document=duplicate_document,
        )