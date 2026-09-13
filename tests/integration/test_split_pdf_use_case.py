from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfReader, PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pdf_reme.application.services.page_selection_parser import (
    PageSelectionParser,
)
from pdf_reme.application.use_cases.split_pdf import SplitPdfUseCase
from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.pdf.pdf_split_service import (
    PdfSplitService,
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


def get_page_widths(path: Path) -> list[int]:
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

    split_service = PdfSplitService()
    parser = PageSelectionParser()

    paths = SimpleNamespace(
        generated_dir=tmp_path / "library" / "generated",
    )

    use_case = SplitPdfUseCase(
        repository=repository,
        split_service=split_service,
        parser=parser,
        paths=paths,
    )

    return (
        engine,
        session,
        repository,
        use_case,
        paths,
    )


def test_extract_selected_pages_creates_generated_document(
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
        [101, 102, 103, 104, 105],
    )

    document = use_case.extract_selected_pages(
        input_path=source,
        page_expression="5,2,4",
        display_name="selected.pdf",
    )

    output_path = Path(document.stored_path)

    assert output_path.exists()
    assert output_path.parent == paths.generated_dir

    assert get_page_widths(output_path) == [
        105,
        102,
        104,
    ]

    assert document.display_name == "selected.pdf"
    assert document.library_section == "generated"
    assert document.generation_type == "split_extract"
    assert document.document_type == "pdf"
    assert document.status == "active"
    assert document.page_count == 3
    assert document.file_size == output_path.stat().st_size
    assert document.sha256
    assert document.original_path is None

    assert repository.get_by_id(
        document.id
    ) is not None

    session.close()
    engine.dispose()


def test_extract_selected_pages_adds_pdf_extension(
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
        [101, 102, 103],
    )

    document = use_case.extract_selected_pages(
        input_path=source,
        page_expression="1,3",
        display_name="selected-pages",
    )

    assert document.display_name == "selected-pages.pdf"
    assert Path(document.stored_path).suffix.lower() == ".pdf"

    session.close()
    engine.dispose()


def test_extract_selected_pages_does_not_overwrite_existing_output(
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
        [101, 102, 103],
    )

    first = use_case.extract_selected_pages(
        input_path=source,
        page_expression="1",
        display_name="selected.pdf",
    )

    first_path = Path(first.stored_path)
    first_bytes = first_path.read_bytes()

    second = use_case.extract_selected_pages(
        input_path=source,
        page_expression="2",
        display_name="selected.pdf",
    )

    second_path = Path(second.stored_path)

    assert first_path.exists()
    assert second_path.exists()

    assert first_path != second_path
    assert first_path.name == "selected.pdf"
    assert second_path.name.startswith("selected_")
    assert second_path.suffix == ".pdf"

    assert first_path.read_bytes() == first_bytes

    session.close()
    engine.dispose()


def test_split_into_four_parts_creates_four_generated_documents(
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
            105,
            106,
            107,
            108,
            109,
            110,
        ],
    )

    documents = use_case.split_into_parts(
        input_path=source,
        part_count=4,
        base_name="quarter",
    )

    assert len(documents) == 4

    assert [
        document.page_count
        for document in documents
    ] == [
        3,
        3,
        2,
        2,
    ]

    all_widths = []

    for document in documents:
        output_path = Path(document.stored_path)

        assert output_path.exists()
        assert output_path.parent == paths.generated_dir

        assert document.library_section == "generated"
        assert document.generation_type == "split_parts"
        assert document.status == "active"
        assert document.sha256

        all_widths.extend(
            get_page_widths(output_path)
        )

        assert repository.get_by_id(
            document.id
        ) is not None

    assert all_widths == [
        101,
        102,
        103,
        104,
        105,
        106,
        107,
        108,
        109,
        110,
    ]

    session.close()
    engine.dispose()


def test_split_by_groups_creates_generated_documents(
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
            105,
            106,
        ],
    )

    documents = use_case.split_by_groups(
        input_path=source,
        page_groups=[
            [1, 3],
            [2, 5, 6],
            [4],
        ],
        base_name="custom",
    )

    assert len(documents) == 3

    assert get_page_widths(
        Path(documents[0].stored_path)
    ) == [
        101,
        103,
    ]

    assert get_page_widths(
        Path(documents[1].stored_path)
    ) == [
        102,
        105,
        106,
    ]

    assert get_page_widths(
        Path(documents[2].stored_path)
    ) == [
        104,
    ]

    for document in documents:
        assert document.library_section == "generated"
        assert document.generation_type == "split_groups"
        assert document.status == "active"

    session.close()
    engine.dispose()


def test_split_into_parts_uses_unique_base_name_when_outputs_exist(
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

    first_documents = use_case.split_into_parts(
        input_path=source,
        part_count=2,
        base_name="report",
    )

    second_documents = use_case.split_into_parts(
        input_path=source,
        part_count=2,
        base_name="report",
    )

    first_paths = {
        Path(document.stored_path)
        for document in first_documents
    }

    second_paths = {
        Path(document.stored_path)
        for document in second_documents
    }

    assert first_paths.isdisjoint(
        second_paths
    )

    for path in first_paths:
        assert path.exists()

    for path in second_paths:
        assert path.exists()

    session.close()
    engine.dispose()


@pytest.mark.parametrize(
    "bad_name",
    [
        "../outside",
        "..\\outside",
        "folder/output",
        "folder\\output",
    ],
)
def test_split_rejects_base_name_with_path_components(
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
        [101, 102],
    )

    with pytest.raises(
        ValueError,
        match="Çıktı adı klasör yolu içeremez",
    ):
        use_case.split_into_parts(
            input_path=source,
            part_count=2,
            base_name=bad_name,
        )

    session.close()
    engine.dispose()


def test_split_cleans_outputs_when_database_save_fails(
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
            104,
        ],
    )

    original_add = repository.add

    call_count = 0

    def failing_add(document):
        nonlocal call_count

        call_count += 1

        if call_count == 2:
            raise RuntimeError(
                "Simulated database failure"
            )

        return original_add(document)

    monkeypatch.setattr(
        repository,
        "add",
        failing_add,
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated database failure",
    ):
        use_case.split_into_parts(
            input_path=source,
            part_count=2,
            base_name="db-error",
        )

    generated_pdfs = list(
        paths.generated_dir.glob("*.pdf")
    )

    assert generated_pdfs == []

    session.close()
    engine.dispose()