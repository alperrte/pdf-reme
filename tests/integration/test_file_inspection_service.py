from pypdf import PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pdf_reme.application.services.duplicate_detection_service import (
    DuplicateDetectionService,
)
from pdf_reme.application.services.file_inspection_service import (
    FileInspectionService,
)
from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.filesystem.file_hash import calculate_sha256


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
    duplicate_service = DuplicateDetectionService(repository)
    inspection_service = FileInspectionService(duplicate_service)

    return engine, session, repository, inspection_service


def create_valid_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)

    with path.open("wb") as file:
        writer.write(file)


def test_valid_new_file_is_inspected_successfully(tmp_path):
    engine, session, _, service = create_test_environment()

    pdf_path = tmp_path / "new.pdf"
    create_valid_pdf(pdf_path)

    result = service.inspect(pdf_path)

    assert result.is_valid is True
    assert result.is_duplicate is False
    assert result.validation.document_type == "pdf"
    assert result.sha256 is not None
    assert len(result.sha256) == 64
    assert result.duplicate_document is None

    session.close()
    engine.dispose()


def test_existing_file_is_detected_as_duplicate(tmp_path):
    engine, session, repository, service = create_test_environment()

    pdf_path = tmp_path / "existing.pdf"
    create_valid_pdf(pdf_path)

    file_hash = calculate_sha256(pdf_path)

    document = Document(
        display_name="existing.pdf",
        stored_path="library/imported/existing.pdf",
        original_path=str(pdf_path),
        document_type="pdf",
        library_section="imported",
        sha256=file_hash,
        file_size=pdf_path.stat().st_size,
        page_count=1,
    )

    repository.add(document)
    session.commit()

    result = service.inspect(pdf_path)

    assert result.is_valid is True
    assert result.is_duplicate is True
    assert result.sha256 == file_hash
    assert result.duplicate_document is not None
    assert result.duplicate_document.id == document.id

    session.close()
    engine.dispose()


def test_corrupted_pdf_stops_before_hash_and_duplicate_check(tmp_path):
    engine, session, _, service = create_test_environment()

    pdf_path = tmp_path / "corrupted.pdf"
    pdf_path.write_bytes(b"not a valid pdf")

    result = service.inspect(pdf_path)

    assert result.is_valid is False
    assert result.is_duplicate is False
    assert result.sha256 is None
    assert result.duplicate_document is None
    assert result.validation.error is not None

    session.close()
    engine.dispose()


def test_unsupported_file_is_rejected(tmp_path):
    engine, session, _, service = create_test_environment()

    file_path = tmp_path / "unsupported.xlsx"
    file_path.write_bytes(b"dummy")

    result = service.inspect(file_path)

    assert result.is_valid is False
    assert result.is_duplicate is False
    assert result.sha256 is None
    assert result.duplicate_document is None
    assert result.validation.error == "Desteklenmeyen dosya türü."

    session.close()
    engine.dispose()