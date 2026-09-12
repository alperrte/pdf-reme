from datetime import datetime

from pdf_reme.domain.repositories.document_repository import (
    DocumentRepository,
)
from pdf_reme.infrastructure.database.models.document import Document


class LibraryService:
    def __init__(self, repository: DocumentRepository) -> None:
        self.repository = repository

    def get_uploaded_documents(self) -> list[Document]:
        return [
            document
            for document in self.repository.get_all()
            if document.library_section == "imported"
            and document.status == "active"
        ]

    def get_generated_documents(self) -> list[Document]:
        return [
            document
            for document in self.repository.get_all()
            if document.library_section == "generated"
            and document.status == "active"
        ]

    def get_favorites(self) -> list[Document]:
        return [
            document
            for document in self.repository.get_all()
            if document.is_favorite
            and document.status == "active"
        ]

    def get_recent_documents(
        self,
        limit: int = 10,
    ) -> list[Document]:
        documents = [
            document
            for document in self.repository.get_all()
            if document.last_opened_at is not None
            and document.status == "active"
        ]

        documents.sort(
            key=lambda document: document.last_opened_at,
            reverse=True,
        )

        return documents[:limit]

    def toggle_favorite(self, document_id: str) -> Document:
        document = self.repository.get_by_id(document_id)

        if document is None:
            raise ValueError("Belge bulunamadı.")

        document.is_favorite = not document.is_favorite

        return self.repository.update(document)


    def mark_as_opened(self, document_id: str) -> Document:
                document = self.repository.get_by_id(document_id)

                if document is None:
                    raise ValueError("Belge bulunamadı.")

                document.last_opened_at = datetime.now()

                return self.repository.update(document)