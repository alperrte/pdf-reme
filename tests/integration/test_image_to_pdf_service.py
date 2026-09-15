from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

from pdf_reme.infrastructure.conversion.image_to_pdf_service import (
    ImageToPdfService,
)


def create_image(
    path: Path,
    size: tuple[int, int],
    mode: str = "RGB",
) -> Path:
    image = Image.new(
        mode,
        size,
    )

    image.save(path)
    image.close()

    return path


def get_page_widths(
    pdf_path: Path,
) -> list[int]:
    reader = PdfReader(
        str(pdf_path)
    )

    return [
        round(
            float(page.mediabox.width)
        )
        for page in reader.pages
    ]


def test_single_image_creates_pdf(tmp_path):
    service = ImageToPdfService()

    image = create_image(
        tmp_path / "one.jpg",
        (101, 60),
    )

    output = tmp_path / "output.pdf"

    service.create(
        [image],
        output,
    )

    assert output.exists()
    assert len(
        PdfReader(str(output)).pages
    ) == 1


def test_multiple_images_preserve_order(tmp_path):
    service = ImageToPdfService()

    first = create_image(
        tmp_path / "first.jpg",
        (101, 60),
    )

    second = create_image(
        tmp_path / "second.png",
        (202, 60),
    )

    third = create_image(
        tmp_path / "third.jpeg",
        (303, 60),
    )

    output = tmp_path / "output.pdf"

    service.create(
        [
            third,
            first,
            second,
        ],
        output,
    )

    assert get_page_widths(
        output
    ) == [
        303,
        101,
        202,
    ]


def test_transparent_png_creates_pdf(tmp_path):
    service = ImageToPdfService()

    image = create_image(
        tmp_path / "transparent.png",
        (120, 80),
        mode="RGBA",
    )

    output = tmp_path / "output.pdf"

    service.create(
        [image],
        output,
    )

    assert output.exists()
    assert len(
        PdfReader(str(output)).pages
    ) == 1


def test_empty_image_list_is_rejected(tmp_path):
    service = ImageToPdfService()

    with pytest.raises(
        ValueError,
        match="en az bir görsel",
    ):
        service.create(
            [],
            tmp_path / "output.pdf",
        )


def test_missing_image_is_rejected(tmp_path):
    service = ImageToPdfService()

    with pytest.raises(
        FileNotFoundError,
    ):
        service.create(
            [tmp_path / "missing.jpg"],
            tmp_path / "output.pdf",
        )


def test_unsupported_extension_is_rejected(
    tmp_path,
):
    service = ImageToPdfService()

    source = tmp_path / "image.bmp"
    source.write_bytes(b"not-an-image")

    with pytest.raises(
        ValueError,
        match="JPG, JPEG ve PNG",
    ):
        service.create(
            [source],
            tmp_path / "output.pdf",
        )


def test_corrupt_image_is_rejected(tmp_path):
    service = ImageToPdfService()

    source = tmp_path / "broken.png"

    source.write_bytes(
        b"broken-image-data"
    )

    with pytest.raises(
        ValueError,
        match="Geçersiz veya bozuk",
    ):
        service.create(
            [source],
            tmp_path / "output.pdf",
        )


def test_output_must_be_pdf(tmp_path):
    service = ImageToPdfService()

    source = create_image(
        tmp_path / "image.jpg",
        (100, 100),
    )

    with pytest.raises(
        ValueError,
        match="PDF formatında",
    ):
        service.create(
            [source],
            tmp_path / "output.txt",
        )