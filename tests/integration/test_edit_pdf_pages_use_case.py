from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfReader, PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pdf_reme.application.use_cases.edit_pdf_pages import (
    EditPdfPagesUseCase,
)
from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.pdf.pdf_page_edit_service import (
    PdfPageEditService,
)


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


def get_page_widths(
    path: Path,
) -> list[int]:
    reader = PdfReader(str(path))

    return [
        int(float(page.mediabox.width))
        for page in reader.pages
    ]


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

    page_edit_service = PdfPageEditService()

    paths = SimpleNamespace(
        generated_dir=tmp_path / "library" / "generated",
    )

    use_case = EditPdfPagesUseCase(
        repository=repository,
        page_edit_service=page_edit_service,
        paths=paths,
    )

    return (
        engine,
        session,
        repository,
        use_case,
        paths,
    )


def test_reorder_pages_creates_generated_document_with_metadata(
    tmp_path,
):
    (
        engine,
        session,
        repository,
        use_case,
        paths,
    ) = create_test_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
            104,
        ],
    )

    document = use_case.reorder_pages(
        input_path=source,
        page_order=[
            4,
            1,
            3,
            2,
        ],
        display_name="reordered.pdf",
    )

    output_path = Path(
        document.stored_path
    )

    assert output_path.exists()
    assert output_path.parent == paths.generated_dir

    assert get_page_widths(output_path) == [
        104,
        101,
        103,
        102,
    ]

    assert document.display_name == "reordered.pdf"
    assert document.document_type == "pdf"
    assert document.library_section == "generated"
    assert document.generation_type == "page_reorder"
    assert document.status == "active"
    assert document.original_path is None
    assert document.is_favorite is False
    assert document.page_count == 4
    assert document.file_size == output_path.stat().st_size

    expected_hash = sha256(
        output_path.read_bytes()
    ).hexdigest()

    assert document.sha256 == expected_hash

    assert repository.get_by_id(
        document.id
    ) is not None

    session.close()
    engine.dispose()


def test_swap_pages_creates_generated_document(tmp_path):
    (
        engine,
        session,
        repository,
        use_case,
        paths,
    ) = create_test_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
            104,
        ],
    )

    document = use_case.swap_pages(
        input_path=source,
        first_page=1,
        second_page=4,
        display_name="swapped.pdf",
    )

    output_path = Path(
        document.stored_path
    )

    assert get_page_widths(output_path) == [
        104,
        102,
        103,
        101,
    ]

    assert document.generation_type == "page_swap"
    assert document.library_section == "generated"
    assert document.page_count == 4

    assert repository.get_by_id(
        document.id
    ) is not None

    session.close()
    engine.dispose()


def test_delete_pages_creates_generated_document(tmp_path):
    (
        engine,
        session,
        repository,
        use_case,
        paths,
    ) = create_test_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
            104,
            105,
        ],
    )

    document = use_case.delete_pages(
        input_path=source,
        page_numbers=[
            2,
            4,
        ],
        display_name="deleted.pdf",
    )

    output_path = Path(
        document.stored_path
    )

    assert get_page_widths(output_path) == [
        101,
        103,
        105,
    ]

    assert document.generation_type == "page_delete"
    assert document.library_section == "generated"
    assert document.page_count == 3

    assert repository.get_by_id(
        document.id
    ) is not None

    session.close()
    engine.dispose()


def test_edit_does_not_overwrite_existing_generated_file(
    tmp_path,
):
    (
        engine,
        session,
        repository,
        use_case,
        paths,
    ) = create_test_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
        ],
    )

    first = use_case.reorder_pages(
        input_path=source,
        page_order=[
            3,
            2,
            1,
        ],
        display_name="edited.pdf",
    )

    first_path = Path(
        first.stored_path
    )

    first_bytes = first_path.read_bytes()

    second = use_case.swap_pages(
        input_path=source,
        first_page=1,
        second_page=2,
        display_name="edited.pdf",
    )

    second_path = Path(
        second.stored_path
    )

    assert first_path.exists()
    assert second_path.exists()

    assert first_path != second_path

    assert first_path.name == "edited.pdf"
    assert second_path.name.startswith(
        "edited_"
    )
    assert second_path.suffix == ".pdf"

    assert first_path.read_bytes() == first_bytes

    session.close()
    engine.dispose()


def test_edit_adds_pdf_extension_when_missing(tmp_path):
    (
        engine,
        session,
        repository,
        use_case,
        paths,
    ) = create_test_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
        ],
    )

    document = use_case.swap_pages(
        input_path=source,
        first_page=1,
        second_page=2,
        display_name="edited-document",
    )

    assert document.display_name == "edited-document.pdf"
    assert Path(
        document.stored_path
    ).suffix.lower() == ".pdf"

    session.close()
    engine.dispose()


def test_edit_rejects_empty_display_name(tmp_path):
    (
        engine,
        session,
        repository,
        use_case,
        paths,
    ) = create_test_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
        ],
    )

    with pytest.raises(
        ValueError,
        match="Çıktı dosya adı gereklidir",
    ):
        use_case.swap_pages(
            input_path=source,
            first_page=1,
            second_page=2,
            display_name="   ",
        )

    assert not paths.generated_dir.exists()

    session.close()
    engine.dispose()


@pytest.mark.parametrize(
    "bad_name",
    [
        "../outside.pdf",
        "..\\outside.pdf",
        "folder/output.pdf",
        "folder\\output.pdf",
    ],
)
def test_edit_rejects_display_name_with_path_components(
    tmp_path,
    bad_name,
):
    (
        engine,
        session,
        repository,
        use_case,
        paths,
    ) = create_test_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
        ],
    )

    with pytest.raises(
        ValueError,
        match="Dosya adı klasör yolu içeremez",
    ):
        use_case.swap_pages(
            input_path=source,
            first_page=1,
            second_page=2,
            display_name=bad_name,
        )

    session.close()
    engine.dispose()


def test_edit_removes_output_when_database_save_fails(
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

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
        ],
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
        use_case.reorder_pages(
            input_path=source,
            page_order=[
                3,
                2,
                1,
            ],
            display_name="database-error.pdf",
        )

    assert not output_path.exists()

    session.close()
    engine.dispose()