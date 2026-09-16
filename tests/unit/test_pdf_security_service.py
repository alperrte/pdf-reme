from pathlib import Path

import pytest
from pypdf import (
    PasswordType,
    PdfReader,
    PdfWriter,
)

from pdf_reme.infrastructure.pdf.pdf_security_service import (
    PdfSecurityService,
)


def create_pdf(
    path: Path,
    pages: int = 3,
) -> Path:
    writer = PdfWriter()

    for _ in range(pages):
        writer.add_blank_page(
            width=500,
            height=700,
        )

    with path.open("wb") as file:
        writer.write(file)

    return path


def test_encrypt_creates_encrypted_pdf(
    tmp_path,
):
    service = PdfSecurityService()

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    output = (
        tmp_path / "encrypted.pdf"
    )

    result = service.encrypt(
        source,
        output,
        "secret123",
    )

    reader = PdfReader(
        str(output)
    )

    assert result.encrypted is True
    assert reader.is_encrypted

    assert (
        reader.decrypt("secret123")
        != PasswordType.NOT_DECRYPTED
    )

    assert len(reader.pages) == 3


def test_decrypt_creates_plain_pdf(
    tmp_path,
):
    service = PdfSecurityService()

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    encrypted = (
        tmp_path / "encrypted.pdf"
    )

    unlocked = (
        tmp_path / "unlocked.pdf"
    )

    service.encrypt(
        source,
        encrypted,
        "secret123",
    )

    result = service.decrypt(
        encrypted,
        unlocked,
        "secret123",
    )

    reader = PdfReader(
        str(unlocked)
    )

    assert result.encrypted is False
    assert reader.is_encrypted is False
    assert len(reader.pages) == 3


def test_wrong_password_is_rejected(
    tmp_path,
):
    service = PdfSecurityService()

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    encrypted = (
        tmp_path / "encrypted.pdf"
    )

    service.encrypt(
        source,
        encrypted,
        "correct-password",
    )

    with pytest.raises(
        ValueError,
        match="yanlış",
    ):
        service.decrypt(
            encrypted,
            tmp_path / "unlocked.pdf",
            "wrong-password",
        )


def test_encrypt_rejects_already_encrypted_pdf(
    tmp_path,
):
    service = PdfSecurityService()

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    encrypted = (
        tmp_path / "encrypted.pdf"
    )

    service.encrypt(
        source,
        encrypted,
        "secret",
    )

    with pytest.raises(
        ValueError,
        match="zaten şifreli",
    ):
        service.encrypt(
            encrypted,
            tmp_path / "second.pdf",
            "new-secret",
        )


def test_decrypt_rejects_plain_pdf(
    tmp_path,
):
    service = PdfSecurityService()

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    with pytest.raises(
        ValueError,
        match="şifreli değil",
    ):
        service.decrypt(
            source,
            tmp_path / "output.pdf",
            "secret",
        )


def test_missing_source_is_rejected(
    tmp_path,
):
    service = PdfSecurityService()

    with pytest.raises(
        FileNotFoundError,
    ):
        service.encrypt(
            tmp_path / "missing.pdf",
            tmp_path / "output.pdf",
            "secret",
        )


def test_non_pdf_is_rejected(
    tmp_path,
):
    service = PdfSecurityService()

    source = tmp_path / "file.txt"
    source.write_text("test")

    with pytest.raises(
        ValueError,
        match="Yalnızca PDF",
    ):
        service.encrypt(
            source,
            tmp_path / "output.pdf",
            "secret",
        )


def test_source_cannot_be_overwritten(
    tmp_path,
):
    service = PdfSecurityService()

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    with pytest.raises(
        ValueError,
        match="üzerine",
    ):
        service.encrypt(
            source,
            source,
            "secret",
        )


def test_blank_password_is_rejected(
    tmp_path,
):
    service = PdfSecurityService()

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    with pytest.raises(
        ValueError,
        match="boş",
    ):
        service.encrypt(
            source,
            tmp_path / "output.pdf",
            "   ",
        )


def test_output_must_be_pdf(
    tmp_path,
):
    service = PdfSecurityService()

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    with pytest.raises(
        ValueError,
        match="Çıktı dosyası PDF",
    ):
        service.encrypt(
            source,
            tmp_path / "output.txt",
            "secret",
        )