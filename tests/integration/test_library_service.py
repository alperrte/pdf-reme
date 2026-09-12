from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pdf_reme.application.services.library_service import LibraryService
from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)


def create_test_environment():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    TestSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = TestSession()
    repository = SQLAlchemyDocumentRepository(session)
    service = LibraryService(repository)

    return engine, session, repository, service


def create_document(
    name: str,
    library_section: str = "imported",
    is_favorite: bool = False,
    last_opened_at: datetime | None = None,
    status: str = "active",
) -> Document:
    return Document(
        display_name=name,
        stored_path=f"library/{library_section}/{name}",
        original_path=f"C:/source/{name}",
        document_type="pdf",
        library_section=library_section,
        generation_type=None,
        sha256=(name * 64)[:64],
        file_size=1024,
        page_count=1,
        is_favorite=is_favorite,
        last_opened_at=last_opened_at,
        status=status,
    )


def test_get_uploaded_documents():
    engine, session, repository, service = create_test_environment()

    repository.add(
        create_document(
            "uploaded.pdf",
            library_section="imported",
        )
    )

    repository.add(
        create_document(
            "generated.pdf",
            library_section="generated",
        )
    )

    session.commit()

    documents = service.get_uploaded_documents()

    assert len(documents) == 1
    assert documents[0].display_name == "uploaded.pdf"

    session.close()
    engine.dispose()


def test_get_generated_documents():
    engine, session, repository, service = create_test_environment()

    repository.add(
        create_document(
            "uploaded.pdf",
            library_section="imported",
        )
    )

    repository.add(
        create_document(
            "generated.pdf",
            library_section="generated",
        )
    )

    session.commit()

    documents = service.get_generated_documents()

    assert len(documents) == 1
    assert documents[0].display_name == "generated.pdf"

    session.close()
    engine.dispose()


def test_get_favorites_returns_only_active_favorites():
    engine, session, repository, service = create_test_environment()

    repository.add(
        create_document(
            "favorite.pdf",
            is_favorite=True,
        )
    )

    repository.add(
        create_document(
            "normal.pdf",
            is_favorite=False,
        )
    )

    repository.add(
        create_document(
            "trashed-favorite.pdf",
            is_favorite=True,
            status="trashed",
        )
    )

    session.commit()

    documents = service.get_favorites()

    assert len(documents) == 1
    assert documents[0].display_name == "favorite.pdf"

    session.close()
    engine.dispose()


def test_get_recent_documents_orders_by_last_opened_at():
    engine, session, repository, service = create_test_environment()

    now = datetime.now()

    repository.add(
        create_document(
            "old.pdf",
            last_opened_at=now - timedelta(days=3),
        )
    )

    repository.add(
        create_document(
            "newest.pdf",
            last_opened_at=now,
        )
    )

    repository.add(
        create_document(
            "middle.pdf",
            last_opened_at=now - timedelta(days=1),
        )
    )

    repository.add(
        create_document(
            "never-opened.pdf",
            last_opened_at=None,
        )
    )

    session.commit()

    documents = service.get_recent_documents()

    assert [document.display_name for document in documents] == [
        "newest.pdf",
        "middle.pdf",
        "old.pdf",
    ]

    session.close()
    engine.dispose()


def test_get_recent_documents_respects_limit():
    engine, session, repository, service = create_test_environment()

    now = datetime.now()

    for index in range(5):
        repository.add(
            create_document(
                f"document-{index}.pdf",
                last_opened_at=now - timedelta(minutes=index),
            )
        )

    session.commit()

    documents = service.get_recent_documents(limit=2)

    assert len(documents) == 2
    assert documents[0].display_name == "document-0.pdf"
    assert documents[1].display_name == "document-1.pdf"

    session.close()
    engine.dispose()

def test_toggle_favorite_changes_favorite_state():
    engine, session, repository, service = create_test_environment()

    document = create_document(
        "favorite-toggle.pdf",
        is_favorite=False,
    )

    repository.add(document)
    session.commit()

    document_id = document.id

    updated_document = service.toggle_favorite(document_id)

    assert updated_document.is_favorite is True

    updated_document = service.toggle_favorite(document_id)

    assert updated_document.is_favorite is False

    session.close()
    engine.dispose()


def test_toggle_favorite_raises_error_when_document_not_found():
    engine, session, repository, service = create_test_environment()

    try:
        service.toggle_favorite("missing-document-id")
        assert False, "ValueError bekleniyordu."
    except ValueError as error:
        assert str(error) == "Belge bulunamadı."

    session.close()
    engine.dispose()


def test_mark_as_opened_updates_last_opened_at():
    engine, session, repository, service = create_test_environment()

    document = create_document(
        "opened.pdf",
        last_opened_at=None,
    )

    repository.add(document)
    session.commit()

    document_id = document.id

    assert document.last_opened_at is None

    updated_document = service.mark_as_opened(document_id)

    assert updated_document.last_opened_at is not None
    assert isinstance(updated_document.last_opened_at, datetime)

    session.close()
    engine.dispose()


def test_mark_as_opened_raises_error_when_document_not_found():
    engine, session, repository, service = create_test_environment()

    try:
        service.mark_as_opened("missing-document-id")
        assert False, "ValueError bekleniyordu."
    except ValueError as error:
        assert str(error) == "Belge bulunamadı."

    session.close()
    engine.dispose()