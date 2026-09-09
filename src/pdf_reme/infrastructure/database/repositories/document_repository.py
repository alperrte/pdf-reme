from sqlalchemy import select
from sqlalchemy.orm import Session

from pdf_reme.domain.repositories.document_repository import DocumentRepository
from pdf_reme.infrastructure.database.models.document import Document


class SQLAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, document_id: str) -> Document | None:
        return self.session.get(Document, document_id)

    def get_all(self) -> list[Document]:
        statement = select(Document).order_by(Document.created_at.desc())
        return list(self.session.scalars(statement).all())

    def add(self, document: Document) -> Document:
        self.session.add(document)
        self.session.flush()
        return document

    def update(self, document: Document) -> Document:
        updated_document = self.session.merge(document)
        self.session.flush()
        return updated_document

    def delete(self, document_id: str) -> bool:
        document = self.get_by_id(document_id)

        if document is None:
            return False

        self.session.delete(document)
        self.session.flush()

        return True