import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
import pdf_reme.infrastructure.database.session as session_module


class TrackingSession(Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.close_called = False

    def close(self):
        self.close_called = True
        super().close()


@pytest.fixture
def test_session_factory(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    TestSessionLocal = sessionmaker(
        bind=engine,
        class_=TrackingSession,
        autoflush=False,
        autocommit=False,
    )

    monkeypatch.setattr(
        session_module,
        "SessionLocal",
        TestSessionLocal,
    )

    yield TestSessionLocal

    engine.dispose()


def create_document(name: str, sha256: str) -> Document:
    return Document(
        display_name=name,
        stored_path=f"library/imported/{name}",
        original_path=f"C:/Users/test/Desktop/{name}",
        document_type="pdf",
        library_section="imported",
        sha256=sha256,
        file_size=1024,
        page_count=3,
    )


def test_session_scope_commits_successful_transaction(test_session_factory):
    document = create_document(
        "commit-test.pdf",
        "c" * 64,
    )

    with session_module.session_scope() as session:
        repository = SQLAlchemyDocumentRepository(session)
        repository.add(document)

        document_id = document.id

    verification_session = test_session_factory()

    saved_document = verification_session.get(
        Document,
        document_id,
    )

    assert saved_document is not None
    assert saved_document.display_name == "commit-test.pdf"

    verification_session.close()


def test_session_scope_rolls_back_failed_transaction(test_session_factory):
    document = create_document(
        "rollback-test.pdf",
        "d" * 64,
    )

    with pytest.raises(RuntimeError):
        with session_module.session_scope() as session:
            repository = SQLAlchemyDocumentRepository(session)
            repository.add(document)

            document_id = document.id

            raise RuntimeError("Test rollback")

    verification_session = test_session_factory()

    saved_document = verification_session.get(
        Document,
        document_id,
    )

    assert saved_document is None

    verification_session.close()


def test_session_scope_closes_session(test_session_factory):
    captured_session = None

    with session_module.session_scope() as session:
        captured_session = session

    assert captured_session is not None
    assert captured_session.close_called is True