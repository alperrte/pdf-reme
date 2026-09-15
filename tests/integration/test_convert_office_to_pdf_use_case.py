from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pdf_reme.application.use_cases.convert_office_to_pdf import (
    ConvertOfficeToPdfUseCase,
)
from pdf_reme.infrastructure.database.base import (
    Base,
)
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)


class FakeOfficeToPdfService:
    def convert(
        self,
        input_path,
        output_path,
    ):
        output_path = Path(
            output_path
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        writer = PdfWriter()

        writer.add_blank_page(
            width=100,
            height=100,
        )

        with output_path.open(
            "wb"
        ) as file:
            writer.write(file)

        return output_path


def create_environment(
    tmp_path,
):
    engine = create_engine(
        "sqlite:///:memory:"
    )

    Base.metadata.create_all(
        bind=engine
    )

    TestSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = TestSession()

    repository = (
        SQLAlchemyDocumentRepository(
            session
        )
    )

    paths = SimpleNamespace(
        generated_dir=(
            tmp_path
            / "library"
            / "generated"
        ),
    )

    use_case = (
        ConvertOfficeToPdfUseCase(
            repository=repository,
            conversion_service=(
                FakeOfficeToPdfService()
            ),
            paths=paths,
        )
    )

    return (
        engine,
        session,
        repository,
        paths,
        use_case,
    )


def create_source(
    path: Path,
) -> Path:
    path.write_bytes(
        b"office-file"
    )

    return path


@pytest.mark.parametrize(
    (
        "extension",
        "expected_type",
    ),
    [
        (
            ".docx",
            "word_to_pdf",
        ),
        (
            ".pptx",
            "powerpoint_to_pdf",
        ),
        (
            ".xlsx",
            "excel_to_pdf",
        ),
    ],
)
def test_office_conversion_creates_generated_document(
    tmp_path,
    extension,
    expected_type,
):
    (
        engine,
        session,
        repository,
        paths,
        use_case,
    ) = create_environment(
        tmp_path
    )

    source = create_source(
        tmp_path
        / f"source{extension}"
    )

    document = use_case.execute(
        source,
        "converted.pdf",
    )

    assert (
        document.generation_type
        == expected_type
    )

    assert (
        document.library_section
        == "generated"
    )

    assert (
        document.document_type
        == "pdf"
    )

    assert document.page_count == 1

    assert (
        document.original_path
        is None
    )

    assert Path(
        document.stored_path
    ).exists()

    assert repository.get_by_id(
        document.id
    ) is not None

    session.close()
    engine.dispose()


def test_pdf_extension_is_added(
    tmp_path,
):
    (
        engine,
        session,
        repository,
        paths,
        use_case,
    ) = create_environment(
        tmp_path
    )

    source = create_source(
        tmp_path / "source.docx"
    )

    document = use_case.execute(
        source,
        "converted",
    )

    assert (
        document.display_name
        == "converted.pdf"
    )

    session.close()
    engine.dispose()


def test_same_name_does_not_overwrite(
    tmp_path,
):
    (
        engine,
        session,
        repository,
        paths,
        use_case,
    ) = create_environment(
        tmp_path
    )

    source = create_source(
        tmp_path / "source.docx"
    )

    first = use_case.execute(
        source,
        "converted.pdf",
    )

    second = use_case.execute(
        source,
        "converted.pdf",
    )

    assert (
        first.stored_path
        != second.stored_path
    )

    assert Path(
        first.stored_path
    ).exists()

    assert Path(
        second.stored_path
    ).exists()

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
def test_path_components_are_rejected(
    tmp_path,
    bad_name,
):
    (
        engine,
        session,
        repository,
        paths,
        use_case,
    ) = create_environment(
        tmp_path
    )

    source = create_source(
        tmp_path / "source.docx"
    )

    with pytest.raises(
        ValueError,
        match="klasör yolu",
    ):
        use_case.execute(
            source,
            bad_name,
        )

    session.close()
    engine.dispose()


def test_output_is_removed_when_db_fails(
    tmp_path,
    monkeypatch,
):
    (
        engine,
        session,
        repository,
        paths,
        use_case,
    ) = create_environment(
        tmp_path
    )

    source = create_source(
        tmp_path / "source.xlsx"
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

    with pytest.raises(
        RuntimeError,
        match="Simulated",
    ):
        use_case.execute(
            source,
            "db-error.pdf",
        )

    assert not (
        paths.generated_dir
        / "db-error.pdf"
    ).exists()

    session.close()
    engine.dispose()