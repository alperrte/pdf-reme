from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from pdf_reme.infrastructure.pdf.pdf_page_edit_service import (
    PdfPageEditService,
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


def get_page_widths(
    path: Path,
) -> list[int]:
    reader = PdfReader(str(path))

    return [
        int(float(page.mediabox.width))
        for page in reader.pages
    ]


def test_reorder_pages_applies_requested_order(tmp_path):
    service = PdfPageEditService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
            104,
            105,
        ],
    )

    output = (
        tmp_path
        / "generated"
        / "reordered.pdf"
    )

    result = service.reorder_pages(
        input_path=source,
        page_order=[
            5,
            1,
            3,
            2,
            4,
        ],
        output_path=output,
    )

    assert result == output
    assert output.exists()

    assert get_page_widths(output) == [
        105,
        101,
        103,
        102,
        104,
    ]


def test_reorder_pages_does_not_modify_source_pdf(tmp_path):
    service = PdfPageEditService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
        ],
    )

    source_before = source.read_bytes()

    output = tmp_path / "reordered.pdf"

    service.reorder_pages(
        input_path=source,
        page_order=[
            3,
            2,
            1,
        ],
        output_path=output,
    )

    assert source.read_bytes() == source_before


def test_reorder_pages_rejects_empty_order(tmp_path):
    service = PdfPageEditService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
        ],
    )

    with pytest.raises(
        ValueError,
        match="Sayfa sıralaması boş olamaz",
    ):
        service.reorder_pages(
            input_path=source,
            page_order=[],
            output_path=tmp_path / "output.pdf",
        )


def test_reorder_pages_rejects_missing_page(tmp_path):
    service = PdfPageEditService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
        ],
    )

    with pytest.raises(
        ValueError,
        match="tüm sayfaları tam olarak bir kez",
    ):
        service.reorder_pages(
            input_path=source,
            page_order=[
                1,
                2,
            ],
            output_path=tmp_path / "output.pdf",
        )


def test_reorder_pages_rejects_duplicate_page(tmp_path):
    service = PdfPageEditService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
        ],
    )

    with pytest.raises(
        ValueError,
        match="tüm sayfaları tam olarak bir kez",
    ):
        service.reorder_pages(
            input_path=source,
            page_order=[
                1,
                2,
                2,
            ],
            output_path=tmp_path / "output.pdf",
        )


def test_reorder_pages_rejects_output_same_as_source(tmp_path):
    service = PdfPageEditService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
        ],
    )

    with pytest.raises(
        ValueError,
        match="Çıktı dosyası kaynak PDF ile aynı olamaz",
    ):
        service.reorder_pages(
            input_path=source,
            page_order=[
                2,
                1,
            ],
            output_path=source,
        )

def test_swap_pages_exchanges_requested_pages(tmp_path):
    service = PdfPageEditService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
            104,
            105,
        ],
    )

    output = tmp_path / "swapped.pdf"

    result = service.swap_pages(
        input_path=source,
        first_page=2,
        second_page=5,
        output_path=output,
    )

    assert result == output
    assert output.exists()

    assert get_page_widths(output) == [
        101,
        105,
        103,
        104,
        102,
    ]


def test_swap_pages_does_not_modify_source_pdf(tmp_path):
    service = PdfPageEditService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
        ],
    )

    source_before = source.read_bytes()

    output = tmp_path / "swapped.pdf"

    service.swap_pages(
        input_path=source,
        first_page=1,
        second_page=3,
        output_path=output,
    )

    assert source.read_bytes() == source_before


def test_swap_pages_rejects_invalid_page_number(tmp_path):
    service = PdfPageEditService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
        ],
    )

    with pytest.raises(
        ValueError,
        match="Geçersiz sayfa numarası",
    ):
        service.swap_pages(
            input_path=source,
            first_page=1,
            second_page=4,
            output_path=tmp_path / "output.pdf",
        )


def test_swap_pages_rejects_same_page(tmp_path):
    service = PdfPageEditService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
        ],
    )

    with pytest.raises(
        ValueError,
        match="Yer değiştirilecek sayfalar farklı olmalıdır",
    ):
        service.swap_pages(
            input_path=source,
            first_page=2,
            second_page=2,
            output_path=tmp_path / "output.pdf",
        )

def test_delete_pages_removes_selected_pages(tmp_path):
    service = PdfPageEditService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
            104,
            105,
        ],
    )

    output = tmp_path / "deleted.pdf"

    result = service.delete_pages(
        input_path=source,
        page_numbers=[
            2,
            4,
        ],
        output_path=output,
    )

    assert result == output
    assert output.exists()

    assert get_page_widths(output) == [
        101,
        103,
        105,
    ]


def test_delete_pages_does_not_modify_source_pdf(tmp_path):
    service = PdfPageEditService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
        ],
    )

    source_before = source.read_bytes()

    output = tmp_path / "deleted.pdf"

    service.delete_pages(
        input_path=source,
        page_numbers=[2],
        output_path=output,
    )

    assert source.read_bytes() == source_before


def test_delete_pages_rejects_empty_selection(tmp_path):
    service = PdfPageEditService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
        ],
    )

    with pytest.raises(
        ValueError,
        match="Silinecek en az bir sayfa seçilmelidir",
    ):
        service.delete_pages(
            input_path=source,
            page_numbers=[],
            output_path=tmp_path / "output.pdf",
        )


def test_delete_pages_rejects_invalid_page_number(tmp_path):
    service = PdfPageEditService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
        ],
    )

    with pytest.raises(
        ValueError,
        match="Geçersiz sayfa numarası",
    ):
        service.delete_pages(
            input_path=source,
            page_numbers=[
                2,
                4,
            ],
            output_path=tmp_path / "output.pdf",
        )


def test_delete_pages_rejects_deleting_all_pages(tmp_path):
    service = PdfPageEditService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
        ],
    )

    with pytest.raises(
        ValueError,
        match="tüm sayfalar silinemez",
    ):
        service.delete_pages(
            input_path=source,
            page_numbers=[
                1,
                2,
                3,
            ],
            output_path=tmp_path / "output.pdf",
        )


def test_delete_pages_ignores_duplicate_page_numbers(tmp_path):
    service = PdfPageEditService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
            104,
        ],
    )

    output = tmp_path / "deleted.pdf"

    service.delete_pages(
        input_path=source,
        page_numbers=[
            2,
            2,
            4,
        ],
        output_path=output,
    )

    assert get_page_widths(output) == [
        101,
        103,
    ]