from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfReader, PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pdf_reme.application.use_cases.merge_pdfs import MergePdfsUseCase
from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.pdf.pdf_merge_service import PdfMergeService


def create_pdf(
    path: Path,
    page_widths: list[int],
) -> Path:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    writer = PdfWriter()

    for width in page_widths:
        writer.add_blank_page(
            width=width,
            height=842,
        )

    with path.open("wb") as file:
        writer.write(file)

    return path


def create_test_environment(tmp_path: Path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    TestSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = TestSession()

    repository = SQLAlchemyDocumentRepository(
        session
    )

    merge_service = PdfMergeService()

    paths = SimpleNamespace(
        generated_dir=tmp_path / "library" / "generated",
    )

    use_case = MergePdfsUseCase(
        repository=repository,
        merge_service=merge_service,
        paths=paths,
    )

    return (
        engine,
        session,
        repository,
        use_case,
        paths,
    )


def test_merge_creates_generated_document_with_correct_metadata(
    tmp_path,
):
    (
        engine,
        session,
        repository,
        use_case,
        paths,
    ) = create_test_environment(tmp_path)

    first = create_pdf(
        tmp_path / "sources" / "first.pdf",
        [101, 102],
    )

    second = create_pdf(
        tmp_path / "sources" / "second.pdf",
        [201],
    )

    document = use_case.execute(
        input_paths=[first, second],
        display_name="combined.pdf",
    )

    output_path = Path(document.stored_path)

    assert output_path.exists()
    assert output_path.parent == paths.generated_dir

    assert document.display_name == "combined.pdf"
    assert document.document_type == "pdf"
    assert document.library_section == "generated"
    assert document.generation_type == "merge"
    assert document.status == "active"
    assert document.original_path is None
    assert document.is_favorite is False

    assert document.page_count == 3
    assert document.file_size == output_path.stat().st_size

    expected_hash = sha256(
        output_path.read_bytes()
    ).hexdigest()

    assert document.sha256 == expected_hash

    saved = repository.get_by_id(document.id)

    assert saved is not None
    assert saved.id == document.id

    session.close()
    engine.dispose()


def test_merge_preserves_requested_pdf_order(tmp_path):
    (
        engine,
        session,
        repository,
        use_case,
        paths,
    ) = create_test_environment(tmp_path)

    first = create_pdf(
        tmp_path / "sources" / "first.pdf",
        [101],
    )

    second = create_pdf(
        tmp_path / "sources" / "second.pdf",
        [201],
    )

    third = create_pdf(
        tmp_path / "sources" / "third.pdf",
        [301],
    )

    document = use_case.execute(
        input_paths=[
            third,
            first,
            second,
        ],
        display_name="ordered.pdf",
    )

    reader = PdfReader(
        document.stored_path
    )

    widths = [
        int(float(page.mediabox.width))
        for page in reader.pages
    ]

    assert widths == [
        301,
        101,
        201,
    ]

    session.close()
    engine.dispose()


def test_merge_adds_pdf_extension_when_missing(tmp_path):
    (
        engine,
        session,
        repository,
        use_case,
        paths,
    ) = create_test_environment(tmp_path)

    first = create_pdf(
        tmp_path / "sources" / "first.pdf",
        [100],
    )

    second = create_pdf(
        tmp_path / "sources" / "second.pdf",
        [200],
    )

    document = use_case.execute(
        input_paths=[first, second],
        display_name="my-merged-document",
    )

    assert document.display_name == "my-merged-document.pdf"
    assert Path(document.stored_path).suffix.lower() == ".pdf"
    assert Path(document.stored_path).exists()

    session.close()
    engine.dispose()


def test_merge_does_not_overwrite_existing_generated_file(
    tmp_path,
):
    (
        engine,
        session,
        repository,
        use_case,
        paths,
    ) = create_test_environment(tmp_path)

    first = create_pdf(
        tmp_path / "sources" / "first.pdf",
        [100],
    )

    second = create_pdf(
        tmp_path / "sources" / "second.pdf",
        [200],
    )

    first_document = use_case.execute(
        input_paths=[first, second],
        display_name="merged.pdf",
    )

    first_output = Path(
        first_document.stored_path
    )

    first_bytes = first_output.read_bytes()

    second_document = use_case.execute(
        input_paths=[first, second],
        display_name="merged.pdf",
    )

    second_output = Path(
        second_document.stored_path
    )

    assert first_output.exists()
    assert second_output.exists()

    assert first_output != second_output

    assert first_output.name == "merged.pdf"
    assert second_output.name.startswith("merged_")
    assert second_output.suffix == ".pdf"

    assert first_output.read_bytes() == first_bytes

    session.close()
    engine.dispose()


def test_merge_rejects_empty_display_name(tmp_path):
    (
        engine,
        session,
        repository,
        use_case,
        paths,
    ) = create_test_environment(tmp_path)

    first = create_pdf(
        tmp_path / "sources" / "first.pdf",
        [100],
    )

    second = create_pdf(
        tmp_path / "sources" / "second.pdf",
        [200],
    )

    with pytest.raises(
        ValueError,
        match="dosya adı gereklidir",
    ):
        use_case.execute(
            input_paths=[first, second],
            display_name="   ",
        )

    assert not paths.generated_dir.exists()

    session.close()
    engine.dispose()


def test_merge_removes_generated_file_when_database_save_fails(
    tmp_path,
    monkeypatch,
):
    (
        engine,
        session,
        repository,
        use_case,
        paths,
    ) = create_test_environment(tmp_path)

    first = create_pdf(
        tmp_path / "sources" / "first.pdf",
        [100],
    )

    second = create_pdf(
        tmp_path / "sources" / "second.pdf",
        [200],
    )

    def failing_add(document):
        raise RuntimeError(
            "Simulated database failure"
        )

    monkeypatch.setattr(
        repository,
        "add",
        failing_add,
    )

    output_path = (
        paths.generated_dir
        / "database-error.pdf"
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated database failure",
    ):
        use_case.execute(
            input_paths=[first, second],
            display_name="database-error.pdf",
        )

    assert not output_path.exists()

    session.close()
    engine.dispose()

def test_merge_rejects_display_name_with_path_components(tmp_path):
    (
        engine,
        session,
        repository,
        use_case,
        paths,
    ) = create_test_environment(tmp_path)

    first = create_pdf(
        tmp_path / "sources" / "first.pdf",
        [100],
    )

    second = create_pdf(
        tmp_path / "sources" / "second.pdf",
        [200],
    )

    with pytest.raises(
        ValueError,
        match="Dosya adı klasör yolu içeremez",
    ):
        use_case.execute(
            input_paths=[first, second],
            display_name="../outside.pdf",
        )

    session.close()
    engine.dispose()