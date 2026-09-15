from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfReader, PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pdf_reme.application.use_cases.compress_pdf import (
    CompressPdfUseCase,
)
from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.pdf.pdf_compression_service import (
    PdfCompressionService,
)


def create_environment(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:"
    )

    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = Session()

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
        )
    )

    use_case = CompressPdfUseCase(
        repository,
        PdfCompressionService(),
        paths,
    )

    return (
        engine,
        session,
        repository,
        paths,
        use_case,
    )


def create_pdf(path):
    writer = PdfWriter()

    for _ in range(3):
        writer.add_blank_page(
            width=500,
            height=700,
        )

    with path.open("wb") as file:
        writer.write(file)

    return path


@pytest.mark.parametrize(
    (
        "level",
        "generation_type",
    ),
    [
        (
            "light",
            "pdf_compress_light",
        ),
        (
            "balanced",
            "pdf_compress_balanced",
        ),
        (
            "strong",
            "pdf_compress_strong",
        ),
    ],
)
def test_compression_creates_generated_document(
    tmp_path,
    level,
    generation_type,
):
    (
        engine,
        session,
        repository,
        paths,
        use_case,
    ) = create_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    result = use_case.execute(
        source,
        f"{level}.pdf",
        level=level,
    )

    assert (
        result.document.generation_type
        == generation_type
    )

    assert (
        result.document.library_section
        == "generated"
    )

    assert result.document.page_count == 3

    assert Path(
        result.document.stored_path
    ).exists()

    session.close()
    engine.dispose()


def test_extension_is_added(tmp_path):
    (
        engine,
        session,
        repository,
        paths,
        use_case,
    ) = create_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    result = use_case.execute(
        source,
        "compressed",
    )

    assert (
        result.document.display_name
        == "compressed.pdf"
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
    ) = create_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    first = use_case.execute(
        source,
        "compressed.pdf",
    )

    second = use_case.execute(
        source,
        "compressed.pdf",
    )

    assert (
        first.document.stored_path
        != second.document.stored_path
    )

    session.close()
    engine.dispose()


def test_path_traversal_is_rejected(
    tmp_path,
):
    (
        engine,
        session,
        repository,
        paths,
        use_case,
    ) = create_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    with pytest.raises(
        ValueError,
        match="klasör yolu",
    ):
        use_case.execute(
            source,
            "../outside.pdf",
        )

    session.close()
    engine.dispose()