from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfWriter

from pdf_reme.infrastructure.conversion.pdf_to_image_service import (
    PdfToImageService,
)


def create_pdf(
    path: Path,
    page_sizes: list[
        tuple[int, int]
    ],
) -> Path:
    writer = PdfWriter()

    for width, height in page_sizes:
        writer.add_blank_page(
            width=width,
            height=height,
        )

    with path.open("wb") as file:
        writer.write(file)

    return path


def test_convert_all_pages_to_jpg(tmp_path):
    service = PdfToImageService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            (72, 100),
            (144, 100),
            (216, 100),
        ],
    )

    outputs = service.convert_to_jpg(
        source,
        tmp_path / "images",
        "converted",
        dpi=72,
    )

    assert len(outputs) == 3

    assert [
        path.name
        for path in outputs
    ] == [
        "converted_page_1.jpg",
        "converted_page_2.jpg",
        "converted_page_3.jpg",
    ]


def test_selected_pages_preserve_order(tmp_path):
    service = PdfToImageService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            (72, 100),
            (144, 100),
            (216, 100),
        ],
    )

    outputs = service.convert_to_jpg(
        source,
        tmp_path / "images",
        "selected",
        page_numbers=[
            3,
            1,
        ],
        dpi=72,
    )

    assert [
        path.name
        for path in outputs
    ] == [
        "selected_page_3.jpg",
        "selected_page_1.jpg",
    ]


def test_dpi_controls_output_size(tmp_path):
    service = PdfToImageService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            (72, 144),
        ],
    )

    outputs = service.convert_to_jpg(
        source,
        tmp_path / "images",
        "dpi-test",
        dpi=144,
    )

    with Image.open(outputs[0]) as image:
        assert image.size == (
            144,
            288,
        )


def test_missing_pdf_is_rejected(tmp_path):
    service = PdfToImageService()

    with pytest.raises(
        FileNotFoundError,
    ):
        service.convert_to_jpg(
            tmp_path / "missing.pdf",
            tmp_path / "images",
            "test",
        )


def test_non_pdf_is_rejected(tmp_path):
    service = PdfToImageService()

    source = tmp_path / "file.txt"
    source.write_text(
        "not pdf",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Yalnızca PDF",
    ):
        service.convert_to_jpg(
            source,
            tmp_path / "images",
            "test",
        )


def test_encrypted_pdf_is_rejected(tmp_path):
    service = PdfToImageService()

    source = tmp_path / "encrypted.pdf"

    writer = PdfWriter()
    writer.add_blank_page(
        width=72,
        height=72,
    )

    writer.encrypt(
        "secret"
    )

    with source.open("wb") as file:
        writer.write(file)

    with pytest.raises(
        ValueError,
        match="Şifreli PDF",
    ):
        service.convert_to_jpg(
            source,
            tmp_path / "images",
            "test",
        )


def test_invalid_page_is_rejected(tmp_path):
    service = PdfToImageService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            (72, 72),
            (72, 72),
        ],
    )

    with pytest.raises(
        ValueError,
        match="Geçersiz sayfa",
    ):
        service.convert_to_jpg(
            source,
            tmp_path / "images",
            "test",
            page_numbers=[3],
        )


def test_partial_outputs_are_removed_on_failure(
    tmp_path,
    monkeypatch,
):
    service = PdfToImageService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            (72, 72),
            (72, 72),
        ],
    )

    call_count = 0

    original_save = service._save_image

    def failing_save(
        image,
        output_path,
        quality,
    ):
        nonlocal call_count

        call_count += 1

        if call_count == 2:
            raise RuntimeError(
                "Simulated image save failure"
            )

        original_save(
            image,
            output_path,
            quality,
        )

    monkeypatch.setattr(
        service,
        "_save_image",
        failing_save,
    )

    output_dir = (
        tmp_path / "images"
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated",
    ):
        service.convert_to_jpg(
            source,
            output_dir,
            "test",
            dpi=72,
        )

    assert list(
        output_dir.glob("*.jpg")
    ) == []