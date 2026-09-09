from pypdf import PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pdf_reme.shared.paths.app_paths as app_paths_module
from pdf_reme.application.services.duplicate_detection_service import (
    DuplicateDetectionService,
)
from pdf_reme.application.services.file_inspection_service import (
    FileInspectionService,
)
from pdf_reme.application.use_cases.import_document import (
    ImportDocumentUseCase,
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


def create_test_environment(tmp_path, monkeypatch):
    test_data_dir = tmp_path / "PDF-REME"

    monkeypatch.setattr(
        app_paths_module,
        "get_app_data_dir",
        lambda: test_data_dir,
    )

    paths = AppPaths()
    paths.ensure_directories()

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

    use_case = ImportDocumentUseCase(
        repository=repository,
        inspection_service=inspection_service,
        paths=paths,
    )

    return engine, session, repository, paths, use_case


def test_valid_pdf_is_imported_and_saved_to_database(
    tmp_path,
    monkeypatch,
):
    engine, session, repository, paths, use_case = (
        create_test_environment(tmp_path, monkeypatch)
    )

    source = tmp_path / "report.pdf"
    create_valid_pdf(source)

    result = use_case.execute(source)

    assert result.imported is True
    assert result.document is not None
    assert result.error is None

    document = result.document

    assert document.display_name == "report.pdf"
    assert document.original_path == str(source.resolve())
    assert document.document_type == "pdf"
    assert document.library_section == "imported"
    assert len(document.sha256) == 64

    stored_path = paths.imported_pdf_dir / "report.pdf"

    assert stored_path.exists()
    assert stored_path.read_bytes() == source.read_bytes()

    session.commit()

    saved_document = repository.get_by_id(document.id)

    assert saved_document is not None
    assert saved_document.stored_path == str(stored_path)

    session.close()
    engine.dispose()


def test_duplicate_pdf_is_not_imported_again(
    tmp_path,
    monkeypatch,
):
    engine, session, repository, paths, use_case = (
        create_test_environment(tmp_path, monkeypatch)
    )

    source = tmp_path / "duplicate.pdf"
    create_valid_pdf(source)

    first_result = use_case.execute(source)
    session.commit()

    second_result = use_case.execute(source)

    assert first_result.imported is True

    assert second_result.imported is False
    assert second_result.document is None
    assert second_result.duplicate_document is not None

    stored_files = list(paths.imported_pdf_dir.glob("*.pdf"))

    assert len(stored_files) == 1

    session.close()
    engine.dispose()


def test_invalid_pdf_is_not_copied_or_saved(
    tmp_path,
    monkeypatch,
):
    engine, session, repository, paths, use_case = (
        create_test_environment(tmp_path, monkeypatch)
    )

    source = tmp_path / "broken.pdf"
    source.write_bytes(b"not a real pdf")

    result = use_case.execute(source)

    assert result.imported is False
    assert result.document is None
    assert result.error is not None

    assert list(paths.imported_pdf_dir.iterdir()) == []
    assert repository.get_all() == []

    session.close()
    engine.dispose()


def test_original_file_is_preserved_after_import(
    tmp_path,
    monkeypatch,
):
    engine, session, _, _, use_case = (
        create_test_environment(tmp_path, monkeypatch)
    )

    source = tmp_path / "original.pdf"
    create_valid_pdf(source)

    original_content = source.read_bytes()

    result = use_case.execute(source)

    assert result.imported is True
    assert source.exists()
    assert source.read_bytes() == original_content

    session.close()
    engine.dispose()

def test_copied_file_is_removed_if_database_save_fails(
    tmp_path,
    monkeypatch,
):
    engine, session, repository, paths, use_case = (
        create_test_environment(tmp_path, monkeypatch)
    )

    source = tmp_path / "database-error.pdf"
    create_valid_pdf(source)

    def failing_add(document):
        raise RuntimeError("Simulated database failure")

    monkeypatch.setattr(
        repository,
        "add",
        failing_add,
    )

    try:
        use_case.execute(source)

        assert False, "RuntimeError bekleniyordu"

    except RuntimeError:
        pass

    stored_files = list(
        paths.imported_pdf_dir.glob("*.pdf")
    )

    assert stored_files == []

    # Kaynak dosya yine korunmalı.
    assert source.exists()

    session.close()
    engine.dispose()