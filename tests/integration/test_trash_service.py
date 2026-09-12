from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pdf_reme.application.services.trash_service import TrashService
from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.filesystem.trash_file_manager import (
    TrashFileManager,
)


def create_test_environment(tmp_path: Path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    TestSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = TestSession()

    repository = SQLAlchemyDocumentRepository(session)

    paths = SimpleNamespace(
        trash_dir=tmp_path / "trash",
    )

    file_manager = TrashFileManager(paths)

    service = TrashService(
        repository=repository,
        file_manager=file_manager,
    )

    return engine, session, repository, service


def create_document(file_path: Path) -> Document:
    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path.write_bytes(b"pdf-content")

    return Document(
        display_name=file_path.name,
        stored_path=str(file_path),
        original_path=str(file_path),
        document_type="pdf",
        library_section="imported",
        generation_type=None,
        sha256="a" * 64,
        file_size=file_path.stat().st_size,
        page_count=1,
        is_favorite=False,
        status="active",
    )


def test_move_to_trash_updates_file_and_document(tmp_path):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    source = (
        tmp_path
        / "library"
        / "imported"
        / "pdf"
        / "test.pdf"
    )

    document = create_document(source)

    repository.add(document)
    session.commit()

    document_id = document.id
    original_library_path = document.stored_path

    updated = service.move_to_trash(document_id)

    assert not source.exists()

    trash_path = Path(updated.stored_path)

    assert trash_path.exists()
    assert trash_path.parent == tmp_path / "trash"

    assert updated.status == "trashed"
    assert updated.deleted_at is not None
    assert updated.trashed_from_path == original_library_path
    assert updated.stored_path != original_library_path

    session.close()
    engine.dispose()


def test_move_to_trash_preserves_original_path(tmp_path):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    source = tmp_path / "library" / "test.pdf"

    document = create_document(source)

    original_path = document.original_path

    repository.add(document)
    session.commit()

    updated = service.move_to_trash(document.id)

    assert updated.original_path == original_path

    session.close()
    engine.dispose()


def test_move_to_trash_rejects_document_already_in_trash(tmp_path):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    source = tmp_path / "already-trashed.pdf"

    document = create_document(source)
    document.status = "trashed"

    repository.add(document)
    session.commit()

    with pytest.raises(
        ValueError,
        match="Belge zaten çöp kutusunda.",
    ):
        service.move_to_trash(document.id)

    assert source.exists()

    session.close()
    engine.dispose()


def test_move_to_trash_raises_when_document_not_found(tmp_path):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    with pytest.raises(
        ValueError,
        match="Belge bulunamadı.",
    ):
        service.move_to_trash("missing-document-id")

    session.close()
    engine.dispose()


def test_restore_moves_file_back_and_reactivates_document(tmp_path):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    source = (
        tmp_path
        / "library"
        / "imported"
        / "pdf"
        / "test.pdf"
    )

    document = create_document(source)

    repository.add(document)
    session.commit()

    document_id = document.id
    original_library_path = document.stored_path

    trashed = service.move_to_trash(document_id)

    trash_path = Path(trashed.stored_path)

    assert trash_path.exists()
    assert not source.exists()

    restored = service.restore(document_id)

    assert restored.status == "active"
    assert restored.deleted_at is None
    assert restored.trashed_from_path is None
    assert restored.stored_path == original_library_path

    assert Path(restored.stored_path).exists()
    assert not trash_path.exists()

    session.close()
    engine.dispose()


def test_restore_rejects_active_document(tmp_path):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    source = tmp_path / "library" / "active.pdf"

    document = create_document(source)

    repository.add(document)
    session.commit()

    with pytest.raises(
        ValueError,
        match="Belge çöp kutusunda değil.",
    ):
        service.restore(document.id)

    assert source.exists()

    session.close()
    engine.dispose()


def test_restore_rejects_document_without_previous_path(tmp_path):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()

    trash_file = trash_dir / "broken.pdf"
    trash_file.write_bytes(b"pdf-content")

    document = Document(
        display_name="broken.pdf",
        stored_path=str(trash_file),
        original_path="C:/source/broken.pdf",
        document_type="pdf",
        library_section="imported",
        generation_type=None,
        sha256="b" * 64,
        file_size=trash_file.stat().st_size,
        page_count=1,
        is_favorite=False,
        status="trashed",
        trashed_from_path=None,
    )

    repository.add(document)
    session.commit()

    with pytest.raises(
        ValueError,
        match="Belgenin önceki kütüphane yolu bulunamadı.",
    ):
        service.restore(document.id)

    assert trash_file.exists()

    session.close()
    engine.dispose()


def test_permanently_delete_removes_file_and_database_record(tmp_path):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    source = tmp_path / "library" / "delete-me.pdf"

    document = create_document(source)

    repository.add(document)
    session.commit()

    document_id = document.id

    trashed = service.move_to_trash(document_id)
    trash_path = Path(trashed.stored_path)

    service.permanently_delete(document_id)

    assert not trash_path.exists()
    assert repository.get_by_id(document_id) is None

    session.close()
    engine.dispose()


def test_permanently_delete_rejects_active_document(tmp_path):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    source = tmp_path / "library" / "active.pdf"

    document = create_document(source)

    repository.add(document)
    session.commit()

    document_id = document.id

    with pytest.raises(
        ValueError,
        match="Yalnızca çöp kutusundaki belgeler",
    ):
        service.permanently_delete(document_id)

    assert source.exists()
    assert repository.get_by_id(document_id) is not None

    session.close()
    engine.dispose()


def test_permanently_delete_raises_when_document_not_found(tmp_path):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    with pytest.raises(
        ValueError,
        match="Belge bulunamadı.",
    ):
        service.permanently_delete("missing-document-id")

    session.close()
    engine.dispose()


def test_permanently_delete_removes_database_record_when_file_missing(
    tmp_path,
):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    source = tmp_path / "library" / "manual-delete.pdf"

    document = create_document(source)

    repository.add(document)
    session.commit()

    document_id = document.id

    trashed = service.move_to_trash(document_id)
    trash_path = Path(trashed.stored_path)

    trash_path.unlink()

    service.permanently_delete(document_id)

    assert repository.get_by_id(document_id) is None

    session.close()
    engine.dispose()


def test_get_trashed_documents_returns_only_trashed_documents(tmp_path):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    first = create_document(
        tmp_path / "library" / "first.pdf"
    )
    second = create_document(
        tmp_path / "library" / "second.pdf"
    )
    active = create_document(
        tmp_path / "library" / "active.pdf"
    )

    repository.add(first)
    repository.add(second)
    repository.add(active)
    session.commit()

    first_trashed = service.move_to_trash(first.id)
    second_trashed = service.move_to_trash(second.id)

    first_trashed.deleted_at = datetime(2026, 9, 10, 12, 0, 0)
    second_trashed.deleted_at = datetime(2026, 9, 11, 12, 0, 0)

    repository.update(first_trashed)
    repository.update(second_trashed)
    session.commit()

    result = service.get_trashed_documents()

    assert len(result) == 2
    assert result[0].id == second.id
    assert result[1].id == first.id

    assert active.id not in [
        document.id
        for document in result
    ]

    session.close()
    engine.dispose()


def test_get_trashed_documents_returns_empty_when_trash_is_empty(
    tmp_path,
):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    active = create_document(
        tmp_path / "library" / "active.pdf"
    )

    repository.add(active)
    session.commit()

    result = service.get_trashed_documents()

    assert result == []

    session.close()
    engine.dispose()


def test_clear_trash_removes_all_trashed_documents(tmp_path):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    first = create_document(
        tmp_path / "library" / "first.pdf"
    )
    second = create_document(
        tmp_path / "library" / "second.pdf"
    )
    active = create_document(
        tmp_path / "library" / "active.pdf"
    )

    repository.add(first)
    repository.add(second)
    repository.add(active)
    session.commit()

    first_trashed = service.move_to_trash(first.id)
    second_trashed = service.move_to_trash(second.id)

    first_trash_path = Path(first_trashed.stored_path)
    second_trash_path = Path(second_trashed.stored_path)

    deleted_count = service.clear_trash()

    assert deleted_count == 2

    assert repository.get_by_id(first.id) is None
    assert repository.get_by_id(second.id) is None

    assert not first_trash_path.exists()
    assert not second_trash_path.exists()

    assert repository.get_by_id(active.id) is not None
    assert Path(active.stored_path).exists()

    session.close()
    engine.dispose()


def test_clear_trash_returns_zero_when_empty(tmp_path):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    deleted_count = service.clear_trash()

    assert deleted_count == 0

    session.close()
    engine.dispose()


def test_cleanup_expired_removes_old_and_keeps_recent_documents(
    tmp_path,
):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    now = datetime(2026, 9, 12, 12, 0, 0)

    old_document = create_document(
        tmp_path / "library" / "old.pdf"
    )
    recent_document = create_document(
        tmp_path / "library" / "recent.pdf"
    )

    repository.add(old_document)
    repository.add(recent_document)
    session.commit()

    old_trashed = service.move_to_trash(old_document.id)
    recent_trashed = service.move_to_trash(recent_document.id)

    old_trashed.deleted_at = now - timedelta(days=31)
    recent_trashed.deleted_at = now - timedelta(days=29)

    repository.update(old_trashed)
    repository.update(recent_trashed)
    session.commit()

    old_trash_path = Path(old_trashed.stored_path)
    recent_trash_path = Path(recent_trashed.stored_path)

    deleted_count = service.cleanup_expired(
        now=now
    )

    assert deleted_count == 1

    assert repository.get_by_id(old_document.id) is None
    assert not old_trash_path.exists()

    assert repository.get_by_id(recent_document.id) is not None
    assert recent_trash_path.exists()

    session.close()
    engine.dispose()


def test_cleanup_expired_removes_document_at_exact_30_day_boundary(
    tmp_path,
):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    now = datetime(2026, 9, 12, 12, 0, 0)

    document = create_document(
        tmp_path / "library" / "boundary.pdf"
    )

    repository.add(document)
    session.commit()

    trashed = service.move_to_trash(document.id)

    trashed.deleted_at = now - timedelta(days=30)

    repository.update(trashed)
    session.commit()

    trash_path = Path(trashed.stored_path)

    deleted_count = service.cleanup_expired(
        now=now
    )

    assert deleted_count == 1
    assert repository.get_by_id(document.id) is None
    assert not trash_path.exists()

    session.close()
    engine.dispose()


def test_cleanup_expired_ignores_document_without_deleted_at(
    tmp_path,
):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    now = datetime(2026, 9, 12, 12, 0, 0)

    document = create_document(
        tmp_path / "library" / "missing-date.pdf"
    )

    repository.add(document)
    session.commit()

    trashed = service.move_to_trash(document.id)

    trashed.deleted_at = None

    repository.update(trashed)
    session.commit()

    trash_path = Path(trashed.stored_path)

    deleted_count = service.cleanup_expired(
        now=now
    )

    assert deleted_count == 0
    assert repository.get_by_id(document.id) is not None
    assert trash_path.exists()

    session.close()
    engine.dispose()


def test_cleanup_expired_removes_db_record_if_file_was_manually_deleted(
    tmp_path,
):
    engine, session, repository, service = create_test_environment(
        tmp_path
    )

    now = datetime(2026, 9, 12, 12, 0, 0)

    document = create_document(
        tmp_path / "library" / "manual.pdf"
    )

    repository.add(document)
    session.commit()

    trashed = service.move_to_trash(document.id)

    trashed.deleted_at = now - timedelta(days=31)

    repository.update(trashed)
    session.commit()

    trash_path = Path(trashed.stored_path)

    trash_path.unlink()

    deleted_count = service.cleanup_expired(
        now=now
    )

    assert deleted_count == 1
    assert repository.get_by_id(document.id) is None

    session.close()
    engine.dispose()