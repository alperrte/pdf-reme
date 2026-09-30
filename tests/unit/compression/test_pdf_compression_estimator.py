from pathlib import Path

from pdf_reme.application.compression.options import (
    CompressionProfile,
    PdfCompressionOptions,
)
from pdf_reme.application.pdf_analysis import (
    PdfAnalysisResult,
    PdfImageAnalysis,
)
from pdf_reme.infrastructure.pdf.pdf_compression_estimator import (
    PdfCompressionEstimator,
)


def _options(
    *,
    min_dpi=100,
    max_dpi=200,
    quality=80,
):
    return PdfCompressionOptions(
        profile=CompressionProfile.CUSTOM,
        min_dpi=min_dpi,
        max_dpi=max_dpi,
        image_quality=quality,
    )


def _image(
    *,
    stream_size=8_000_000,
    dpi=400.0,
    filters=("/DCTDecode",),
    has_smask=False,
    has_mask=False,
    is_image_mask=False,
):
    return PdfImageAnalysis(
        object_id="10 0 R",
        page_numbers=(1,),
        width_px=2000,
        height_px=1000,
        stream_size_bytes=stream_size,
        filters=filters,
        color_space="/DeviceRGB",
        bits_per_component=8,
        has_smask=has_smask,
        has_mask=has_mask,
        is_image_mask=is_image_mask,
        max_display_width_points=360.0,
        max_display_height_points=180.0,
        effective_dpi_x=dpi,
        effective_dpi_y=dpi,
    )


def _analysis(
    image=None,
    *,
    file_size=10_000_000,
):
    images = (
        (image,)
        if image is not None
        else ()
    )

    return PdfAnalysisResult(
        source_path=Path("test.pdf"),
        file_size_bytes=file_size,
        page_count=1,
        images=images,
        text_page_count=1,
        vector_page_count=0,
    )


def test_text_only_pdf_stays_close_to_original():
    analysis = _analysis()

    estimate = (
        PdfCompressionEstimator()
        .estimate(
            analysis,
            _options(),
        )
    )

    assert (
        estimate.estimated_min_size_bytes
        == analysis.file_size_bytes
    )

    assert (
        estimate.estimated_max_size_bytes
        == analysis.file_size_bytes
    )


def test_high_dpi_image_has_large_reduction_potential():
    image = _image(
        dpi=400.0
    )

    estimate = (
        PdfCompressionEstimator()
        .estimate(
            _analysis(image),
            _options(
                min_dpi=100,
                max_dpi=200,
                quality=80,
            ),
        )
    )

    assert (
        estimate.estimated_max_size_bytes
        < 6_000_000
    )


def test_high_dpi_estimate_is_smaller_than_low_dpi():
    estimator = (
        PdfCompressionEstimator()
    )

    high_dpi = estimator.estimate(
        _analysis(
            _image(dpi=400.0)
        ),
        _options(),
    )

    low_dpi = estimator.estimate(
        _analysis(
            _image(dpi=150.0)
        ),
        _options(),
    )

    assert (
        high_dpi.estimated_max_size_bytes
        < low_dpi.estimated_min_size_bytes
    )


def test_lower_quality_estimates_smaller_output():
    estimator = (
        PdfCompressionEstimator()
    )

    analysis = _analysis(
        _image(dpi=150.0)
    )

    high_quality = estimator.estimate(
        analysis,
        _options(
            quality=90
        ),
    )

    low_quality = estimator.estimate(
        analysis,
        _options(
            quality=60
        ),
    )

    assert (
        low_quality.estimated_midpoint_bytes
        < high_quality.estimated_midpoint_bytes
    )


def test_missing_dpi_does_not_apply_resize():
    image = _image(
        dpi=None
    )

    estimate = (
        PdfCompressionEstimator()
        .estimate(
            _analysis(image),
            _options(),
        )
    )

    assert (
        estimate.estimated_min_size_bytes
        > 0
    )

    assert (
        estimate.estimated_max_size_bytes
        <= 10_000_000
    )


def test_masked_image_is_not_assumed_compressible():
    image = _image(
        has_mask=True
    )

    analysis = _analysis(image)

    estimate = (
        PdfCompressionEstimator()
        .estimate(
            analysis,
            _options(),
        )
    )

    assert (
        estimate.estimated_min_size_bytes
        == analysis.file_size_bytes
    )

    assert (
        estimate.estimated_max_size_bytes
        == analysis.file_size_bytes
    )


def test_smask_image_is_estimated_conservatively():
    image = _image(
        has_smask=True
    )

    analysis = _analysis(image)

    estimate = (
        PdfCompressionEstimator()
        .estimate(
            analysis,
            _options(),
        )
    )

    assert (
        estimate.estimated_min_size_bytes
        == analysis.file_size_bytes
    )

    assert (
        estimate.estimated_max_size_bytes
        == analysis.file_size_bytes
    )


def test_flate_image_has_compression_potential():
    image = _image(
        dpi=150.0,
        filters=(
            "/FlateDecode",
        ),
    )

    estimate = (
        PdfCompressionEstimator()
        .estimate(
            _analysis(image),
            _options(
                quality=80
            ),
        )
    )

    assert (
        estimate.estimated_max_size_bytes
        < 10_000_000
    )