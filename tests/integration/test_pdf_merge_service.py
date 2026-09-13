from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from pdf_reme.infrastructure.pdf.pdf_merge_service import PdfMergeService


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


def create_encrypted_pdf(
    path: Path,
) -> Path:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    writer = PdfWriter()

    writer.add_blank_page(
        width=500,
        height=842,
    )

    writer.encrypt("secret")

    with path.open("wb") as file:
        writer.write(file)

    return path


def test_merge_combines_pdfs_in_given_order(tmp_path):
    service = PdfMergeService()

    first = create_pdf(
        tmp_path / "first.pdf",
        [101, 102],
    )

    second = create_pdf(
        tmp_path / "second.pdf",
        [201],
    )

    third = create_pdf(
        tmp_path / "third.pdf",
        [301, 302],
    )

    output = tmp_path / "generated" / "merged.pdf"

    result = service.merge(
        [
            third,
            first,
            second,
        ],
        output,
    )

    assert result == output
    assert output.exists()

    reader = PdfReader(str(output))

    widths = [
        int(float(page.mediabox.width))
        for page in reader.pages
    ]

    assert widths == [
        301,
        302,
        101,
        102,
        201,
    ]


def test_merge_does_not_modify_source_files(tmp_path):
    service = PdfMergeService()

    first = create_pdf(
        tmp_path / "first.pdf",
        [100],
    )

    second = create_pdf(
        tmp_path / "second.pdf",
        [200],
    )

    first_before = first.read_bytes()
    second_before = second.read_bytes()

    output = tmp_path / "merged.pdf"

    service.merge(
        [first, second],
        output,
    )

    assert first.read_bytes() == first_before
    assert second.read_bytes() == second_before


def test_merge_requires_at_least_two_pdfs(tmp_path):
    service = PdfMergeService()

    first = create_pdf(
        tmp_path / "first.pdf",
        [100],
    )

    with pytest.raises(
        ValueError,
        match="en az iki dosya",
    ):
        service.merge(
            [first],
            tmp_path / "merged.pdf",
        )


def test_merge_rejects_missing_pdf(tmp_path):
    service = PdfMergeService()

    first = create_pdf(
        tmp_path / "first.pdf",
        [100],
    )

    missing = tmp_path / "missing.pdf"

    with pytest.raises(
        FileNotFoundError,
        match="Birleştirilecek PDF bulunamadı",
    ):
        service.merge(
            [first, missing],
            tmp_path / "merged.pdf",
        )


def test_merge_rejects_non_pdf_file(tmp_path):
    service = PdfMergeService()

    first = create_pdf(
        tmp_path / "first.pdf",
        [100],
    )

    text_file = tmp_path / "notes.txt"
    text_file.write_text(
        "PDF değil",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Yalnızca PDF dosyaları",
    ):
        service.merge(
            [first, text_file],
            tmp_path / "merged.pdf",
        )


def test_merge_rejects_output_path_that_is_source_pdf(tmp_path):
    service = PdfMergeService()

    first = create_pdf(
        tmp_path / "first.pdf",
        [100],
    )

    second = create_pdf(
        tmp_path / "second.pdf",
        [200],
    )

    with pytest.raises(
        ValueError,
        match="Çıktı dosyası kaynak PDF",
    ):
        service.merge(
            [first, second],
            first,
        )


def test_merge_rejects_encrypted_pdf_and_removes_partial_output(
    tmp_path,
):
    service = PdfMergeService()

    first = create_pdf(
        tmp_path / "first.pdf",
        [100],
    )

    encrypted = create_encrypted_pdf(
        tmp_path / "encrypted.pdf",
    )

    output = tmp_path / "generated" / "merged.pdf"

    with pytest.raises(
        ValueError,
        match="Şifreli PDF birleştirilemez",
    ):
        service.merge(
            [first, encrypted],
            output,
        )

    assert not output.exists()