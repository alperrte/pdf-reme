import pytest
from pypdf import PdfWriter
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import pdf_reme.infrastructure.database.session as session_module
import pdf_reme.shared.paths.app_paths as app_paths_module

from pdf_reme.application.services.import_document_service import (
    ImportDocumentService,
)
from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.shared.paths.app_paths import AppPaths


def create_valid_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)

    with path.open("wb") as file:
        writer.write(file)


@pytest.fixture
def environment(tmp_path, monkeypatch):
    test_data_dir = tmp_path / "PDF-REME"

    monkeypatch.setattr(
        app_paths_module,
        "get_app_data_dir",
        lambda: test_data_dir,
    )

    paths = AppPaths()
    paths.ensure_directories()

    database_path = tmp_path / "import_service.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    engine = create_engine(database_url)
    Base.metadata.create_all(bind=engine)

    TestSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        session_module,
        "SessionLocal",
        TestSessionLocal,
    )

    yield paths, engine, TestSessionLocal

    engine.dispose()


def test_import_service_commits_document(
    tmp_path,
    environment,
):
    paths, _, TestSessionLocal = environment

    source = tmp_path / "report.pdf"
    create_valid_pdf(source)

    service = ImportDocumentService(paths)

    result = service.import_document(source)

    assert result.imported is True
    assert result.document is not None

    verification_session = TestSessionLocal()

    documents = list(
        verification_session.scalars(
            select(Document)
        ).all()
    )

    assert len(documents) == 1

    saved_document = documents[0]

    assert saved_document.display_name == "report.pdf"
    assert saved_document.original_path == str(source.resolve())
    assert saved_document.library_section == "imported"

    stored_path = paths.imported_pdf_dir / "report.pdf"

    assert stored_path.exists()

    verification_session.close()


def test_duplicate_import_does_not_create_second_record(
    tmp_path,
    environment,
):
    paths, _, TestSessionLocal = environment

    source = tmp_path / "duplicate.pdf"
    create_valid_pdf(source)

    service = ImportDocumentService(paths)

    first_result = service.import_document(source)
    second_result = service.import_document(source)

    assert first_result.imported is True
    assert second_result.imported is False
    assert second_result.duplicate_document is not None

    verification_session = TestSessionLocal()

    documents = list(
        verification_session.scalars(
            select(Document)
        ).all()
    )

    assert len(documents) == 1
    assert len(list(paths.imported_pdf_dir.glob("*.pdf"))) == 1

    verification_session.close()


def test_database_failure_rolls_back_and_removes_copied_file(
    tmp_path,
    environment,
    monkeypatch,
):
    paths, _, TestSessionLocal = environment

    source = tmp_path / "failure.pdf"
    create_valid_pdf(source)

    def failing_add(self, document):
        raise RuntimeError("Simulated database failure")

    monkeypatch.setattr(
        SQLAlchemyDocumentRepository,
        "add",
        failing_add,
    )

    service = ImportDocumentService(paths)

    with pytest.raises(RuntimeError):
        service.import_document(source)

    verification_session = TestSessionLocal()

    documents = list(
        verification_session.scalars(
            select(Document)
        ).all()
    )

    assert documents == []
    assert list(paths.imported_pdf_dir.glob("*.pdf")) == []

    # Kaynak dosyaya dokunulmadı.
    assert source.exists()

    verification_session.close()