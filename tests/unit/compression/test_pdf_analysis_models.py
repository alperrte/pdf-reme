from pathlib import Path

from pdf_reme.application.pdf_analysis import (
    PdfAnalysisResult,
    PdfImageAnalysis,
)


def test_pdf_image_analysis_stores_image_metadata():
    image = PdfImageAnalysis(
        object_id="12 0 R",
        page_numbers=(1, 3),
        width_px=3000,
        height_px=2000,
        stream_size_bytes=2_500_000,
        filters=("/DCTDecode",),
        color_space="/DeviceRGB",
        bits_per_component=8,
        has_smask=False,
        has_mask=False,
        is_image_mask=False,
        max_display_width_points=720.0,
        max_display_height_points=480.0,
        effective_dpi_x=300.0,
        effective_dpi_y=300.0,
    )

    assert image.object_id == "12 0 R"
    assert image.page_numbers == (1, 3)
    assert image.width_px == 3000
    assert image.height_px == 2000
    assert image.stream_size_bytes == 2_500_000
    assert image.effective_dpi_x == 300.0
    assert image.effective_dpi_y == 300.0


def test_pdf_analysis_calculates_summary_values():
    first = PdfImageAnalysis(
        object_id="10 0 R",
        page_numbers=(1,),
        width_px=1000,
        height_px=800,
        stream_size_bytes=500_000,
        filters=("/DCTDecode",),
        color_space="/DeviceRGB",
        bits_per_component=8,
        has_smask=False,
        has_mask=False,
        is_image_mask=False,
    )

    second = PdfImageAnalysis(
        object_id="11 0 R",
        page_numbers=(2,),
        width_px=2000,
        height_px=1600,
        stream_size_bytes=1_500_000,
        filters=("/FlateDecode",),
        color_space="/DeviceRGB",
        bits_per_component=8,
        has_smask=False,
        has_mask=False,
        is_image_mask=False,
    )

    result = PdfAnalysisResult(
        source_path=Path("sample.pdf"),
        file_size_bytes=5_000_000,
        page_count=3,
        images=(first, second),
        text_page_count=2,
        vector_page_count=1,
    )

    assert result.image_count == 2
    assert result.total_image_stream_bytes == 2_000_000
    assert result.contains_text is True
    assert result.contains_vector_graphics is True


def test_empty_analysis_has_zero_images():
    result = PdfAnalysisResult(
        source_path=Path("text_only.pdf"),
        file_size_bytes=1000,
        page_count=1,
        images=(),
        text_page_count=1,
        vector_page_count=0,
    )

    assert result.image_count == 0
    assert result.total_image_stream_bytes == 0
    assert result.contains_text is True
    assert result.contains_vector_graphics is False