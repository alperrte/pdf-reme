from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from pdf_reme.infrastructure.pdf.pdf_compression_service import (
    PdfCompressionService,
)


def create_pdf(
    path: Path,
    page_count: int = 3,
) -> Path:
    writer = PdfWriter()

    for index in range(page_count):
        writer.add_blank_page(
            width=500 + index,
            height=700,
        )

    with path.open("wb") as file:
        writer.write(file)

    return path


def test_missing_pdf_is_rejected(tmp_path):
    service = PdfCompressionService()

    with pytest.raises(
        FileNotFoundError,
    ):
        service.compress(
            tmp_path / "missing.pdf",
            tmp_path / "out.pdf",
        )


def test_non_pdf_is_rejected(tmp_path):
    service = PdfCompressionService()

    source = tmp_path / "file.txt"
    source.write_text("test")

    with pytest.raises(
        ValueError,
        match="Yalnızca PDF",
    ):
        service.compress(
            source,
            tmp_path / "out.pdf",
        )


def test_output_must_be_pdf(tmp_path):
    service = PdfCompressionService()

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    with pytest.raises(
        ValueError,
        match="Çıktı dosyası PDF",
    ):
        service.compress(
            source,
            tmp_path / "out.txt",
        )


def test_source_cannot_be_overwritten(
    tmp_path,
):
    service = PdfCompressionService()

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    with pytest.raises(
        ValueError,
        match="üzerine",
    ):
        service.compress(
            source,
            source,
        )


def test_invalid_level_is_rejected(
    tmp_path,
):
    service = PdfCompressionService()

    source = create_pdf(
        tmp_path / "source.pdf"
    )

    with pytest.raises(
        ValueError,
        match="light, balanced",
    ):
        service.compress(
            source,
            tmp_path / "out.pdf",
            level="maximum",
        )


def test_encrypted_pdf_is_rejected(
    tmp_path,
):
    service = PdfCompressionService()

    source = tmp_path / "encrypted.pdf"

    writer = PdfWriter()
    writer.add_blank_page(
        width=100,
        height=100,
    )
    writer.encrypt("secret")

    with source.open("wb") as file:
        writer.write(file)

    with pytest.raises(
        ValueError,
        match="Şifreli PDF",
    ):
        service.compress(
            source,
            tmp_path / "out.pdf",
        )


@pytest.mark.parametrize(
    "level",
    [
        "light",
        "balanced",
        "strong",
    ],
)
def test_compression_modes_create_valid_pdf(
    tmp_path,
    level,
):
    service = PdfCompressionService()

    source = create_pdf(
        tmp_path / "source.pdf",
        page_count=4,
    )

    output = (
        tmp_path / f"{level}.pdf"
    )

    result = service.compress(
        source,
        output,
        level=level,
    )

    assert output.exists()
    assert result.output_path == output
    assert result.level == level

    assert len(
        PdfReader(str(output)).pages
    ) == 4


def test_output_is_never_larger_than_source(
    tmp_path,
):
    service = PdfCompressionService()

    source = create_pdf(
        tmp_path / "source.pdf",
        page_count=2,
    )

    output = tmp_path / "output.pdf"

    service.compress(
        source,
        output,
        level="strong",
    )

    assert (
        output.stat().st_size
        <= source.stat().st_size
    )