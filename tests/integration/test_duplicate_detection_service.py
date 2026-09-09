from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pdf_reme.application.services.duplicate_detection_service import (
    DuplicateDetectionService,
)
from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.filesystem.file_hash import calculate_sha256


def create_test_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    TestSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    return engine, TestSession()


def test_existing_file_is_detected_as_duplicate(tmp_path):
    engine, session = create_test_session()
    repository = SQLAlchemyDocumentRepository(session)

    existing_file = tmp_path / "existing.pdf"
    existing_file.write_bytes(b"same file content")

    file_hash = calculate_sha256(existing_file)

    document = Document(
        display_name="existing.pdf",
        stored_path="library/imported/existing.pdf",
        original_path=str(existing_file),
        document_type="pdf",
        library_section="imported",
        sha256=file_hash,
        file_size=existing_file.stat().st_size,
        page_count=1,
    )

    repository.add(document)
    session.commit()

    service = DuplicateDetectionService(repository)

    calculated_hash, duplicate = service.find_duplicate(existing_file)

    assert calculated_hash == file_hash
    assert duplicate is not None
    assert duplicate.id == document.id

    session.close()
    engine.dispose()


def test_new_file_is_not_detected_as_duplicate(tmp_path):
    engine, session = create_test_session()
    repository = SQLAlchemyDocumentRepository(session)

    new_file = tmp_path / "new.pdf"
    new_file.write_bytes(b"completely new content")

    service = DuplicateDetectionService(repository)

    calculated_hash, duplicate = service.find_duplicate(new_file)

    assert len(calculated_hash) == 64
    assert duplicate is None

    session.close()
    engine.dispose()


def test_different_filename_same_content_is_duplicate(tmp_path):
    engine, session = create_test_session()
    repository = SQLAlchemyDocumentRepository(session)

    first_file = tmp_path / "first.pdf"
    second_file = tmp_path / "renamed.pdf"

    content = b"identical binary content"

    first_file.write_bytes(content)
    second_file.write_bytes(content)

    file_hash = calculate_sha256(first_file)

    document = Document(
        display_name="first.pdf",
        stored_path="library/imported/first.pdf",
        original_path=str(first_file),
        document_type="pdf",
        library_section="imported",
        sha256=file_hash,
        file_size=first_file.stat().st_size,
        page_count=1,
    )

    repository.add(document)
    session.commit()

    service = DuplicateDetectionService(repository)

    second_hash, duplicate = service.find_duplicate(second_file)

    assert second_hash == file_hash
    assert duplicate is not None
    assert duplicate.id == document.id

    session.close()
    engine.dispose()