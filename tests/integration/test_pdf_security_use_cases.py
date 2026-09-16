from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfReader, PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pdf_reme.application.use_cases.decrypt_pdf import (
    DecryptPdfUseCase,
)
from pdf_reme.application.use_cases.encrypt_pdf import (
    EncryptPdfUseCase,
)
from pdf_reme.infrastructure.database.base import (
    Base,
)
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.pdf.pdf_security_service import (
    PdfSecurityService,
)


def create_environment(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:"
    )

    Base.metadata.create_all(
        bind=engine
    )

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

    service = PdfSecurityService()

    encrypt_use_case = EncryptPdfUseCase(
        repository,
        service,
        paths,
    )

    decrypt_use_case = DecryptPdfUseCase(
        repository,
        service,
        paths,
    )

    return (
        engine,
        session,
        repository,
        paths,
        encrypt_use_case,
        decrypt_use_case,
    )


def create_pdf(path):
    writer = PdfWriter()

    writer.add_blank_page(
        width=500,
        height=700,
    )

    writer.add_blank_page(
        width=500,
        height=700,
    )

    with path.open("wb") as file:
        writer.write(file)

    return path


def test_encrypt_creates_generated_document(
    tmp_path,
):
    (
        engine,
        session,
        repository,
        paths,
        encrypt_use_case,
        decrypt_use_case,
    ) = create_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    document = encrypt_use_case.execute(
        source,
        "locked.pdf",
        "secret123",
    )

    assert (
        document.generation_type
        == "pdf_encrypt"
    )

    assert (
        document.library_section
        == "generated"
    )

    assert document.page_count == 2

    assert PdfReader(
        document.stored_path
    ).is_encrypted

    session.close()
    engine.dispose()


def test_decrypt_creates_generated_document(
    tmp_path,
):
    (
        engine,
        session,
        repository,
        paths,
        encrypt_use_case,
        decrypt_use_case,
    ) = create_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    encrypted = encrypt_use_case.execute(
        source,
        "locked.pdf",
        "secret123",
    )

    unlocked = decrypt_use_case.execute(
        encrypted.stored_path,
        "unlocked.pdf",
        "secret123",
    )

    assert (
        unlocked.generation_type
        == "pdf_decrypt"
    )

    assert (
        PdfReader(
            unlocked.stored_path
        ).is_encrypted
        is False
    )

    assert unlocked.page_count == 2

    session.close()
    engine.dispose()


def test_extension_is_added(
    tmp_path,
):
    (
        engine,
        session,
        repository,
        paths,
        encrypt_use_case,
        decrypt_use_case,
    ) = create_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    document = encrypt_use_case.execute(
        source,
        "locked",
        "secret",
    )

    assert (
        document.display_name
        == "locked.pdf"
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
        encrypt_use_case,
        decrypt_use_case,
    ) = create_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    first = encrypt_use_case.execute(
        source,
        "locked.pdf",
        "secret",
    )

    second = encrypt_use_case.execute(
        source,
        "locked.pdf",
        "secret",
    )

    assert (
        first.stored_path
        != second.stored_path
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
        encrypt_use_case,
        decrypt_use_case,
    ) = create_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    with pytest.raises(
        ValueError,
        match="klasör yolu",
    ):
        encrypt_use_case.execute(
            source,
            "../locked.pdf",
            "secret",
        )

    session.close()
    engine.dispose()


def test_db_failure_removes_output(
    tmp_path,
    monkeypatch,
):
    (
        engine,
        session,
        repository,
        paths,
        encrypt_use_case,
        decrypt_use_case,
    ) = create_environment(tmp_path)

    source = create_pdf(
        tmp_path / "source.pdf"
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
        encrypt_use_case.execute(
            source,
            "db-error.pdf",
            "secret",
        )

    assert not (
        paths.generated_dir
        / "db-error.pdf"
    ).exists()

    session.close()
    engine.dispose()