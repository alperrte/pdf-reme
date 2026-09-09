from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)


def create_test_session():
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(bind=engine)

    TestSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    return TestSession()


def create_document() -> Document:
    return Document(
        display_name="test.pdf",
        stored_path="library/imported/test.pdf",
        original_path="C:/Users/test/Desktop/test.pdf",
        document_type="pdf",
        library_section="imported",
        sha256="a" * 64,
        file_size=1024,
        page_count=5,
    )


def test_add_and_get_document():
    session = create_test_session()
    repository = SQLAlchemyDocumentRepository(session)

    document = create_document()

    repository.add(document)
    session.commit()

    saved_document = repository.get_by_id(document.id)

    assert saved_document is not None
    assert saved_document.display_name == "test.pdf"
    assert saved_document.document_type == "pdf"
    assert saved_document.page_count == 5

    session.close()


def test_get_all_documents():
    session = create_test_session()
    repository = SQLAlchemyDocumentRepository(session)

    repository.add(create_document())

    second_document = create_document()
    second_document.display_name = "test-2.pdf"
    second_document.sha256 = "b" * 64

    repository.add(second_document)
    session.commit()

    documents = repository.get_all()

    assert len(documents) == 2

    session.close()


def test_update_document():
    session = create_test_session()
    repository = SQLAlchemyDocumentRepository(session)

    document = create_document()

    repository.add(document)
    session.commit()

    document.display_name = "updated.pdf"

    repository.update(document)
    session.commit()

    updated_document = repository.get_by_id(document.id)

    assert updated_document is not None
    assert updated_document.display_name == "updated.pdf"

    session.close()


def test_delete_document():
    session = create_test_session()
    repository = SQLAlchemyDocumentRepository(session)

    document = create_document()

    repository.add(document)
    session.commit()

    document_id = document.id

    deleted = repository.delete(document_id)
    session.commit()

    assert deleted is True
    assert repository.get_by_id(document_id) is None

    session.close()


def test_delete_missing_document_returns_false():
    session = create_test_session()
    repository = SQLAlchemyDocumentRepository(session)

    deleted = repository.delete("missing-document-id")

    assert deleted is False

    session.close()