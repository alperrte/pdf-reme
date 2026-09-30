from io import BytesIO

import pikepdf
import pytest

from PIL import Image
from pikepdf import (
    Dictionary,
    Name,
    Pdf,
    Stream,
)

from pdf_reme.infrastructure.pdf.pdf_analysis_service import (
    PdfAnalysisService,
)


def _create_test_pdf(path):
    pdf = Pdf.new()

    image = Image.new(
        "RGB",
        (400, 300),
        (120, 150, 180),
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="JPEG",
        quality=90,
    )

    image_stream = Stream(
        pdf,
        buffer.getvalue(),
    )

    image_stream.Type = Name.XObject
    image_stream.Subtype = Name.Image
    image_stream.Width = 400
    image_stream.Height = 300
    image_stream.ColorSpace = Name.DeviceRGB
    image_stream.BitsPerComponent = 8
    image_stream.Filter = Name.DCTDecode

    image_ref = pdf.make_indirect(
        image_stream
    )

    font = pdf.make_indirect(
        Dictionary(
            Type=Name.Font,
            Subtype=Name.Type1,
            BaseFont=Name.Helvetica,
        )
    )

    # Page 1:
    # text + aynı image
    resources_1 = Dictionary(
        XObject=Dictionary(),
        Font=Dictionary(),
    )

    resources_1.XObject[
        Name("/Im1")
    ] = image_ref

    resources_1.Font[
        Name("/F1")
    ] = font

    page_1 = Dictionary(
        Type=Name.Page,
        MediaBox=[0, 0, 600, 800],
        Resources=resources_1,
        Contents=pdf.make_stream(
            b"BT /F1 12 Tf "
            b"40 700 Td "
            b"(PDF-REME) Tj ET "
            b"q 200 0 0 150 "
            b"20 400 cm /Im1 Do Q"
        ),
    )

    pdf.pages.append(
        pikepdf.Page(page_1)
    )

    # Page 2:
    # vector + aynı image
    resources_2 = Dictionary(
        XObject=Dictionary(),
    )

    resources_2.XObject[
        Name("/Im1")
    ] = image_ref

    page_2 = Dictionary(
        Type=Name.Page,
        MediaBox=[0, 0, 600, 800],
        Resources=resources_2,
        Contents=pdf.make_stream(
            b"10 10 100 100 re S "
            b"q 150 0 0 112.5 "
            b"20 300 cm /Im1 Do Q"
        ),
    )

    pdf.pages.append(
        pikepdf.Page(page_2)
    )

    pdf.save(path)

    buffer.close()
    image.close()

    return path


def test_analyzer_reads_basic_pdf_information(
    tmp_path,
):
    source = _create_test_pdf(
        tmp_path / "analysis.pdf"
    )

    result = PdfAnalysisService().analyze(
        source
    )

    assert result.source_path == source
    assert result.file_size_bytes > 0
    assert result.page_count == 2

    assert result.text_page_count == 1
    assert result.vector_page_count == 1

    assert result.contains_text is True
    assert result.contains_vector_graphics is True


def test_shared_image_is_counted_once(
    tmp_path,
):
    source = _create_test_pdf(
        tmp_path / "shared.pdf"
    )

    result = PdfAnalysisService().analyze(
        source
    )

    assert result.image_count == 1

    image = result.images[0]

    assert image.page_numbers == (1, 2)
    assert image.width_px == 400
    assert image.height_px == 300

    assert image.stream_size_bytes > 0

    assert image.filters == (
        "/DCTDecode",
    )

    assert (
        image.color_space
        == "/DeviceRGB"
    )

    assert image.bits_per_component == 8

    assert image.has_smask is False
    assert image.has_mask is False
    assert image.is_image_mask is False


def test_image_stream_bytes_are_not_double_counted(
    tmp_path,
):
    source = _create_test_pdf(
        tmp_path / "streams.pdf"
    )

    result = PdfAnalysisService().analyze(
        source
    )

    assert result.image_count == 1

    assert (
        result.total_image_stream_bytes
        == result.images[0].stream_size_bytes
    )


def test_missing_pdf_is_rejected(
    tmp_path,
):
    with pytest.raises(
        FileNotFoundError
    ):
        PdfAnalysisService().analyze(
            tmp_path / "missing.pdf"
        )


def test_non_pdf_is_rejected(
    tmp_path,
):
    source = tmp_path / "test.txt"
    source.write_text("hello")

    with pytest.raises(
        ValueError,
        match="Yalnızca PDF",
    ):
        PdfAnalysisService().analyze(
            source
        )


def test_effective_dpi_uses_largest_display_size(
    tmp_path,
):
    source = _create_test_pdf(
        tmp_path / "dpi.pdf"
    )

    result = PdfAnalysisService().analyze(
        source
    )

    image = result.images[0]

    assert image.max_display_width_points == pytest.approx(
        200.0
    )

    assert image.max_display_height_points == pytest.approx(
        150.0
    )

    assert image.effective_dpi_x == pytest.approx(
        144.0
    )

    assert image.effective_dpi_y == pytest.approx(
        144.0
    )

def test_matrix_multiplication_preserves_nested_scaling():
    service = PdfAnalysisService()

    first = (
        2.0,
        0.0,
        0.0,
        2.0,
        0.0,
        0.0,
    )

    second = (
        100.0,
        0.0,
        0.0,
        75.0,
        10.0,
        20.0,
    )

    result = service._multiply_matrices(
        first,
        second,
    )

    assert result[0] == pytest.approx(200.0)
    assert result[3] == pytest.approx(150.0)

    assert result[4] == pytest.approx(20.0)
    assert result[5] == pytest.approx(40.0)