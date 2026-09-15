from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pdf_reme.application.use_cases.convert_images_to_pdf import (
    ConvertImagesToPdfUseCase,
)
from pdf_reme.application.use_cases.convert_pdf_to_images import (
    ConvertPdfToImagesUseCase,
)
from pdf_reme.infrastructure.conversion.image_to_pdf_service import (
    ImageToPdfService,
)
from pdf_reme.infrastructure.conversion.pdf_to_image_service import (
    PdfToImageService,
)
from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)


def create_environment(tmp_path):
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

    return (
        engine,
        session,
        repository,
        paths,
    )


def create_image(
    path: Path,
    size: tuple[int, int],
) -> Path:
    image = Image.new(
        "RGB",
        size,
    )

    image.save(path)
    image.close()

    return path


def create_pdf(
    path: Path,
    count: int,
) -> Path:
    writer = PdfWriter()

    for index in range(count):
        writer.add_blank_page(
            width=72 + index,
            height=100,
        )

    with path.open("wb") as file:
        writer.write(file)

    return path


def test_images_to_pdf_creates_document(
    tmp_path,
):
    (
        engine,
        session,
        repository,
        paths,
    ) = create_environment(tmp_path)

    first = create_image(
        tmp_path / "1.jpg",
        (101, 60),
    )

    second = create_image(
        tmp_path / "2.png",
        (202, 60),
    )

    use_case = ConvertImagesToPdfUseCase(
        repository,
        ImageToPdfService(),
        paths,
    )

    document = use_case.execute(
        [
            first,
            second,
        ],
        "images.pdf",
    )

    assert document.generation_type == (
        "images_to_pdf"
    )

    assert document.page_count == 2
    assert document.document_type == "pdf"
    assert Path(
        document.stored_path
    ).exists()

    session.close()
    engine.dispose()


def test_images_to_pdf_adds_extension(
    tmp_path,
):
    (
        engine,
        session,
        repository,
        paths,
    ) = create_environment(tmp_path)

    source = create_image(
        tmp_path / "image.jpg",
        (100, 100),
    )

    use_case = ConvertImagesToPdfUseCase(
        repository,
        ImageToPdfService(),
        paths,
    )

    document = use_case.execute(
        [source],
        "converted",
    )

    assert document.display_name == (
        "converted.pdf"
    )

    session.close()
    engine.dispose()


def test_images_to_pdf_rejects_path_name(
    tmp_path,
):
    (
        engine,
        session,
        repository,
        paths,
    ) = create_environment(tmp_path)

    source = create_image(
        tmp_path / "image.jpg",
        (100, 100),
    )

    use_case = ConvertImagesToPdfUseCase(
        repository,
        ImageToPdfService(),
        paths,
    )

    with pytest.raises(
        ValueError,
        match="klasör yolu",
    ):
        use_case.execute(
            [source],
            "../outside.pdf",
        )

    session.close()
    engine.dispose()


def test_pdf_to_jpg_creates_generated_documents(
    tmp_path,
):
    (
        engine,
        session,
        repository,
        paths,
    ) = create_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf",
        2,
    )

    use_case = ConvertPdfToImagesUseCase(
        repository,
        PdfToImageService(),
        paths,
    )

    documents = use_case.execute(
        source,
        "pages",
        dpi=72,
    )

    assert len(documents) == 2

    assert all(
        document.generation_type
        == "pdf_to_jpg"
        for document in documents
    )

    assert all(
        document.document_type
        == "image"
        for document in documents
    )

    assert all(
        Path(
            document.stored_path
        ).exists()
        for document in documents
    )

    session.close()
    engine.dispose()


def test_images_to_pdf_cleans_output_on_db_failure(
    tmp_path,
    monkeypatch,
):
    (
        engine,
        session,
        repository,
        paths,
    ) = create_environment(tmp_path)

    source = create_image(
        tmp_path / "image.jpg",
        (100, 100),
    )

    use_case = ConvertImagesToPdfUseCase(
        repository,
        ImageToPdfService(),
        paths,
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
            [source],
            "db-error.pdf",
        )

    assert not (
        paths.generated_dir
        / "db-error.pdf"
    ).exists()

    session.close()
    engine.dispose()


def test_pdf_to_jpg_cleans_files_on_db_failure(
    tmp_path,
    monkeypatch,
):
    (
        engine,
        session,
        repository,
        paths,
    ) = create_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf",
        2,
    )

    use_case = ConvertPdfToImagesUseCase(
        repository,
        PdfToImageService(),
        paths,
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
            "db-error",
            dpi=72,
        )

    assert list(
        paths.generated_dir.glob(
            "db-error_page_*.jpg"
        )
    ) == []

    session.close()
    engine.dispose()