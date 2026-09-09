from pathlib import Path

from pdf_reme.domain.repositories.document_repository import DocumentRepository
from pdf_reme.infrastructure.filesystem.file_hash import calculate_sha256


class DuplicateDetectionService:
    def __init__(self, repository: DocumentRepository) -> None:
        self.repository = repository

    def find_duplicate(self, file_path: str | Path):
        sha256 = calculate_sha256(file_path)

        existing_document = self.repository.get_by_sha256(sha256)

        return sha256, existing_document