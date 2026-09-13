from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from pdf_reme.infrastructure.pdf.pdf_split_service import (
    PdfSplitService,
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


def get_page_widths(path: Path) -> list[int]:
    reader = PdfReader(str(path))

    return [
        int(float(page.mediabox.width))
        for page in reader.pages
    ]


def test_extract_pages_creates_pdf_with_selected_pages_in_given_order(
    tmp_path,
):
    service = PdfSplitService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [101, 102, 103, 104, 105],
    )

    output = tmp_path / "generated" / "selected.pdf"

    result = service.extract_pages(
        input_path=source,
        page_numbers=[5, 2, 4],
        output_path=output,
    )

    assert result == output
    assert output.exists()

    assert get_page_widths(output) == [
        105,
        102,
        104,
    ]


def test_extract_pages_does_not_modify_source_pdf(tmp_path):
    service = PdfSplitService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [101, 102, 103],
    )

    source_before = source.read_bytes()

    output = tmp_path / "selected.pdf"

    service.extract_pages(
        input_path=source,
        page_numbers=[1, 3],
        output_path=output,
    )

    assert source.read_bytes() == source_before


def test_extract_pages_rejects_empty_page_selection(tmp_path):
    service = PdfSplitService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [101, 102],
    )

    with pytest.raises(
        ValueError,
        match="En az bir sayfa seçilmelidir",
    ):
        service.extract_pages(
            input_path=source,
            page_numbers=[],
            output_path=tmp_path / "output.pdf",
        )


def test_extract_pages_rejects_invalid_page_number(tmp_path):
    service = PdfSplitService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [101, 102, 103],
    )

    with pytest.raises(
        ValueError,
        match="Geçersiz sayfa numarası",
    ):
        service.extract_pages(
            input_path=source,
            page_numbers=[1, 4],
            output_path=tmp_path / "output.pdf",
        )


def test_split_into_two_parts_preserves_all_pages(tmp_path):
    service = PdfSplitService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
            104,
            105,
            106,
        ],
    )

    outputs = service.split_into_parts(
        input_path=source,
        part_count=2,
        output_dir=tmp_path / "generated",
        base_name="half",
    )

    assert len(outputs) == 2

    assert get_page_widths(outputs[0]) == [
        101,
        102,
        103,
    ]

    assert get_page_widths(outputs[1]) == [
        104,
        105,
        106,
    ]


def test_split_into_four_parts_does_not_lose_pages_when_uneven(
    tmp_path,
):
    service = PdfSplitService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
            104,
            105,
            106,
            107,
            108,
            109,
            110,
        ],
    )

    outputs = service.split_into_parts(
        input_path=source,
        part_count=4,
        output_dir=tmp_path / "generated",
        base_name="quarter",
    )

    assert len(outputs) == 4

    page_counts = [
        len(PdfReader(str(path)).pages)
        for path in outputs
    ]

    assert page_counts == [
        3,
        3,
        2,
        2,
    ]

    all_widths = []

    for output in outputs:
        all_widths.extend(
            get_page_widths(output)
        )

    assert all_widths == [
        101,
        102,
        103,
        104,
        105,
        106,
        107,
        108,
        109,
        110,
    ]


def test_split_into_parts_rejects_part_count_larger_than_page_count(
    tmp_path,
):
    service = PdfSplitService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [101, 102, 103],
    )

    with pytest.raises(
        ValueError,
        match="Parça sayısı toplam sayfa sayısından büyük olamaz",
    ):
        service.split_into_parts(
            input_path=source,
            part_count=4,
            output_dir=tmp_path / "generated",
        )


def test_split_by_groups_creates_separate_pdfs(tmp_path):
    service = PdfSplitService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [
            101,
            102,
            103,
            104,
            105,
            106,
        ],
    )

    outputs = service.split_by_groups(
        input_path=source,
        page_groups=[
            [1, 3],
            [2, 5, 6],
            [4],
        ],
        output_dir=tmp_path / "generated",
        base_name="custom",
    )

    assert len(outputs) == 3

    assert get_page_widths(outputs[0]) == [
        101,
        103,
    ]

    assert get_page_widths(outputs[1]) == [
        102,
        105,
        106,
    ]

    assert get_page_widths(outputs[2]) == [
        104,
    ]


def test_split_by_groups_removes_created_outputs_when_later_group_fails(
    tmp_path,
):
    service = PdfSplitService()

    source = create_pdf(
        tmp_path / "source.pdf",
        [101, 102, 103],
    )

    output_dir = tmp_path / "generated"

    with pytest.raises(
        ValueError,
        match="Geçersiz sayfa numarası",
    ):
        service.split_by_groups(
            input_path=source,
            page_groups=[
                [1],
                [99],
            ],
            output_dir=output_dir,
            base_name="cleanup",
        )

    first_output = (
        output_dir
        / "cleanup_group_1.pdf"
    )

    assert not first_output.exists()


def test_split_rejects_non_pdf_source(tmp_path):
    service = PdfSplitService()

    source = tmp_path / "notes.txt"
    source.write_text(
        "PDF değil",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Yalnızca PDF dosyaları bölünebilir",
    ):
        service.extract_pages(
            input_path=source,
            page_numbers=[1],
            output_path=tmp_path / "output.pdf",
        )