from datetime import datetime, timedelta
from pathlib import Path

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
    root: Path,
    name: str,
    library_section: str = "imported",
    is_favorite: bool = False,
    last_opened_at: datetime | None = None,
    status: str = "active",
    create_file: bool = True,
) -> Document:
    """Sentetik bir belge kaydı üretir.

    `LibraryService` artık `stored_path`'in diskte gerçekten var olup
    olmadığını kontrol ettiğinden (uygulama dışından silinmiş/taşınmış
    dosyaları listelerden gizlemek için), `create_file=True` (varsayılan)
    `tmp_path` altında gerçek (boş) bir dosya oluşturur; `create_file=False`
    "silinmiş/taşınmış dosya" senaryosunu simüler -- kayıt DB'de "active"
    kalır ama fiziksel dosya hiç yazılmaz.
    """
    stored_path = root / library_section / name

    if create_file:
        stored_path.parent.mkdir(parents=True, exist_ok=True)
        stored_path.write_bytes(b"%PDF-1.4 sentetik test dosyasi")

    return Document(
        display_name=name,
        stored_path=str(stored_path),
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


def test_get_uploaded_documents(tmp_path):
    engine, session, repository, service = create_test_environment()

    repository.add(
        create_document(
            tmp_path,
            "uploaded.pdf",
            library_section="imported",
        )
    )

    repository.add(
        create_document(
            tmp_path,
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


def test_get_uploaded_documents_excludes_missing_file(tmp_path):
    # Madde: uygulama dışından silinmiş/taşınmış dosyalar (DB kaydı "active"
    # kalsa da) artık kütüphane listelerinde görünmez/seçilemez.
    engine, session, repository, service = create_test_environment()

    repository.add(
        create_document(
            tmp_path,
            "still-there.pdf",
            library_section="imported",
        )
    )

    repository.add(
        create_document(
            tmp_path,
            "deleted-externally.pdf",
            library_section="imported",
            create_file=False,
        )
    )

    session.commit()

    documents = service.get_uploaded_documents()

    assert len(documents) == 1
    assert documents[0].display_name == "still-there.pdf"

    session.close()
    engine.dispose()


def test_get_generated_documents(tmp_path):
    engine, session, repository, service = create_test_environment()

    repository.add(
        create_document(
            tmp_path,
            "uploaded.pdf",
            library_section="imported",
        )
    )

    repository.add(
        create_document(
            tmp_path,
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


def test_get_generated_documents_excludes_missing_file(tmp_path):
    engine, session, repository, service = create_test_environment()

    repository.add(
        create_document(
            tmp_path,
            "generated-missing.pdf",
            library_section="generated",
            create_file=False,
        )
    )

    session.commit()

    documents = service.get_generated_documents()

    assert documents == []

    session.close()
    engine.dispose()


def test_get_favorites_returns_only_active_favorites(tmp_path):
    engine, session, repository, service = create_test_environment()

    repository.add(
        create_document(
            tmp_path,
            "favorite.pdf",
            is_favorite=True,
        )
    )

    repository.add(
        create_document(
            tmp_path,
            "normal.pdf",
            is_favorite=False,
        )
    )

    repository.add(
        create_document(
            tmp_path,
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


def test_get_favorites_excludes_missing_file(tmp_path):
    engine, session, repository, service = create_test_environment()

    repository.add(
        create_document(
            tmp_path,
            "favorite-missing.pdf",
            is_favorite=True,
            create_file=False,
        )
    )

    session.commit()

    documents = service.get_favorites()

    assert documents == []

    session.close()
    engine.dispose()


def test_get_recent_documents_orders_by_last_opened_at(tmp_path):
    engine, session, repository, service = create_test_environment()

    now = datetime.now()

    repository.add(
        create_document(
            tmp_path,
            "old.pdf",
            last_opened_at=now - timedelta(days=3),
        )
    )

    repository.add(
        create_document(
            tmp_path,
            "newest.pdf",
            last_opened_at=now,
        )
    )

    repository.add(
        create_document(
            tmp_path,
            "middle.pdf",
            last_opened_at=now - timedelta(days=1),
        )
    )

    repository.add(
        create_document(
            tmp_path,
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


def test_get_recent_documents_excludes_missing_file(tmp_path):
    engine, session, repository, service = create_test_environment()

    now = datetime.now()

    repository.add(
        create_document(
            tmp_path,
            "recent-missing.pdf",
            last_opened_at=now,
            create_file=False,
        )
    )

    repository.add(
        create_document(
            tmp_path,
            "recent-present.pdf",
            last_opened_at=now - timedelta(minutes=1),
        )
    )

    session.commit()

    documents = service.get_recent_documents()

    assert [document.display_name for document in documents] == [
        "recent-present.pdf",
    ]

    session.close()
    engine.dispose()


def test_get_recent_documents_respects_limit(tmp_path):
    engine, session, repository, service = create_test_environment()

    now = datetime.now()

    for index in range(5):
        repository.add(
            create_document(
                tmp_path,
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

def test_toggle_favorite_changes_favorite_state(tmp_path):
    engine, session, repository, service = create_test_environment()

    document = create_document(
        tmp_path,
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


def test_mark_as_opened_updates_last_opened_at(tmp_path):
    engine, session, repository, service = create_test_environment()

    document = create_document(
        tmp_path,
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
