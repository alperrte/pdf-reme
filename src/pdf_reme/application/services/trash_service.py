from datetime import datetime, timedelta

from pdf_reme.domain.repositories.document_repository import DocumentRepository
from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.infrastructure.filesystem.trash_file_manager import TrashFileManager


class TrashService:
    TRASH_RETENTION_DAYS = 30

    def __init__(
        self,
        repository: DocumentRepository,
        file_manager: TrashFileManager,
    ) -> None:
        self.repository = repository
        self.file_manager = file_manager

    def move_to_trash(self, document_id: str) -> Document:
        document = self.repository.get_by_id(document_id)

        if document is None:
            raise ValueError("Belge bulunamadı.")

        if document.status == "trashed":
            raise ValueError("Belge zaten çöp kutusunda.")

        if document.status != "active":
            raise ValueError(
                f"Belge çöp kutusuna taşınamaz. Durum: {document.status}"
            )

        previous_path = document.stored_path

        trash_path = self.file_manager.move_to_trash(
            previous_path
        )

        document.trashed_from_path = previous_path
        document.stored_path = str(trash_path)
        document.status = "trashed"
        document.deleted_at = datetime.now()

        return self.repository.update(document)

    def restore(self, document_id: str) -> Document:
        document = self.repository.get_by_id(document_id)

        if document is None:
            raise ValueError("Belge bulunamadı.")

        if document.status != "trashed":
            raise ValueError("Belge çöp kutusunda değil.")

        if not document.trashed_from_path:
            raise ValueError(
                "Belgenin önceki kütüphane yolu bulunamadı."
            )

        restored_path = self.file_manager.restore_from_trash(
            document.stored_path,
            document.trashed_from_path,
        )

        document.stored_path = str(restored_path)
        document.trashed_from_path = None
        document.status = "active"
        document.deleted_at = None

        return self.repository.update(document)

    def permanently_delete(self, document_id: str) -> None:
        document = self.repository.get_by_id(document_id)

        if document is None:
            raise ValueError("Belge bulunamadı.")

        if document.status != "trashed":
            raise ValueError(
                "Yalnızca çöp kutusundaki belgeler "
                "kalıcı olarak silinebilir."
            )

        self.file_manager.permanently_delete(
            document.stored_path
        )

        self.repository.delete(document_id)

    def get_trashed_documents(self) -> list[Document]:
        documents = [
            document
            for document in self.repository.get_all()
            if document.status == "trashed"
        ]

        documents.sort(
            key=lambda document: (
                document.deleted_at
                if document.deleted_at is not None
                else datetime.min
            ),
            reverse=True,
        )

        return documents

    def clear_trash(self) -> int:
        trashed_documents = self.get_trashed_documents()

        deleted_count = 0

        for document in trashed_documents:
            self.permanently_delete(document.id)
            deleted_count += 1

        return deleted_count

    def cleanup_expired(
        self,
        now: datetime | None = None,
    ) -> int:
        current_time = now or datetime.now()

        cutoff = current_time - timedelta(
            days=self.TRASH_RETENTION_DAYS
        )

        expired_documents = [
            document
            for document in self.get_trashed_documents()
            if document.deleted_at is not None
            and document.deleted_at <= cutoff
        ]

        deleted_count = 0

        for document in expired_documents:
            self.permanently_delete(document.id)
            deleted_count += 1

        return deleted_count