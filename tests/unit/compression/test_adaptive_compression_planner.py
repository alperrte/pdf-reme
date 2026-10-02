from pathlib import Path

from pdf_reme.application.compression.options import (
    CompressionProfile,
    PdfCompressionOptions,
)
from pdf_reme.application.compression.plan import (
    ImageCompressionAction,
)
from pdf_reme.application.compression.planner import (
    AdaptiveCompressionPlanner,
)
from pdf_reme.application.pdf_analysis import (
    PdfAnalysisResult,
    PdfImageAnalysis,
)


def _options():
    return PdfCompressionOptions(
        profile=CompressionProfile.CUSTOM,
        min_dpi=100,
        max_dpi=200,
        image_quality=80,
    )


def _image(
    *,
    object_id="10 0 R",
    width=2400,
    height=1600,
    dpi_x=400.0,
    dpi_y=400.0,
    has_smask=False,
    has_mask=False,
    is_image_mask=False,
):
    return PdfImageAnalysis(
        object_id=object_id,
        page_numbers=(1,),
        width_px=width,
        height_px=height,
        stream_size_bytes=1_000_000,
        filters=("/DCTDecode",),
        color_space="/DeviceRGB",
        bits_per_component=8,
        has_smask=has_smask,
        has_mask=has_mask,
        is_image_mask=is_image_mask,
        max_display_width_points=432.0,
        max_display_height_points=288.0,
        effective_dpi_x=dpi_x,
        effective_dpi_y=dpi_y,
    )


def _analysis(*images):
    return PdfAnalysisResult(
        source_path=Path("test.pdf"),
        file_size_bytes=5_000_000,
        page_count=1,
        images=tuple(images),
        text_page_count=1,
        vector_page_count=0,
    )


def test_high_dpi_image_is_downsampled():
    plan = AdaptiveCompressionPlanner().create_plan(
        _analysis(
            _image(
                dpi_x=400.0,
                dpi_y=400.0,
            )
        ),
        _options(),
    )

    image = plan.images[0]

    assert (
        image.action
        == ImageCompressionAction.DOWNSAMPLE
    )

    assert image.source_dpi == 400.0
    assert image.target_dpi == 200.0

    assert image.target_width_px == 1200
    assert image.target_height_px == 800

    assert image.target_quality == 80


def test_image_inside_dpi_limit_is_kept():
    plan = AdaptiveCompressionPlanner().create_plan(
        _analysis(
            _image(
                dpi_x=180.0,
                dpi_y=180.0,
            )
        ),
        _options(),
    )

    image = plan.images[0]

    assert (
        image.action
        == ImageCompressionAction.KEEP
    )

    assert image.target_width_px == 2400
    assert image.target_height_px == 1600

    assert (
        image.reason
        == "already_within_dpi_limit"
    )


def test_low_dpi_image_is_not_upscaled():
    plan = AdaptiveCompressionPlanner().create_plan(
        _analysis(
            _image(
                dpi_x=90.0,
                dpi_y=90.0,
            )
        ),
        _options(),
    )

    image = plan.images[0]

    assert (
        image.action
        == ImageCompressionAction.KEEP
    )

    assert image.target_width_px == 2400
    assert image.target_height_px == 1600

    assert image.target_dpi == 90.0


def test_missing_dpi_is_kept():
    plan = AdaptiveCompressionPlanner().create_plan(
        _analysis(
            _image(
                dpi_x=None,
                dpi_y=None,
            )
        ),
        _options(),
    )

    image = plan.images[0]

    assert (
        image.action
        == ImageCompressionAction.KEEP
    )

    assert (
        image.reason
        == "effective_dpi_unknown"
    )


def test_smask_image_is_kept():
    plan = AdaptiveCompressionPlanner().create_plan(
        _analysis(
            _image(
                has_smask=True,
            )
        ),
        _options(),
    )

    image = plan.images[0]

    assert (
        image.action
        == ImageCompressionAction.KEEP
    )

    assert (
        image.reason
        == "unsafe_mask_or_transparency"
    )


def test_asymmetric_dpi_uses_lower_axis():
    plan = AdaptiveCompressionPlanner().create_plan(
        _analysis(
            _image(
                dpi_x=400.0,
                dpi_y=180.0,
            )
        ),
        _options(),
    )

    image = plan.images[0]

    assert (
        image.action
        == ImageCompressionAction.KEEP
    )

    assert image.source_dpi == 180.0


def test_plan_contains_multiple_image_decisions():
    plan = AdaptiveCompressionPlanner().create_plan(
        _analysis(
            _image(
                object_id="10 0 R",
                dpi_x=400.0,
                dpi_y=400.0,
            ),
            _image(
                object_id="11 0 R",
                dpi_x=150.0,
                dpi_y=150.0,
            ),
        ),
        _options(),
    )

    assert plan.image_count == 2
    assert plan.changed_image_count == 1
    assert plan.downsampled_image_count == 1
    assert plan.kept_image_count == 1


def test_image_exactly_at_max_dpi_is_kept():
    plan = AdaptiveCompressionPlanner().create_plan(
        _analysis(
            _image(
                dpi_x=200.0,
                dpi_y=200.0,
            )
        ),
        _options(),
    )

    image = plan.images[0]

    assert image.action == ImageCompressionAction.KEEP
    assert image.source_dpi == 200.0
    assert image.target_dpi == 200.0
    assert image.target_quality is None


def test_image_just_above_max_dpi_is_downsampled():
    plan = AdaptiveCompressionPlanner().create_plan(
        _analysis(
            _image(
                dpi_x=201.0,
                dpi_y=201.0,
            )
        ),
        _options(),
    )

    image = plan.images[0]

    assert (
        image.action
        == ImageCompressionAction.DOWNSAMPLE
    )

    assert image.target_dpi == 200.0

    assert image.target_width_px < 2400
    assert image.target_height_px < 1600


def test_masked_image_is_kept():
    plan = AdaptiveCompressionPlanner().create_plan(
        _analysis(
            _image(
                has_mask=True,
            )
        ),
        _options(),
    )

    image = plan.images[0]

    assert image.action == ImageCompressionAction.KEEP

    assert (
        image.reason
        == "unsafe_mask_or_transparency"
    )


def test_image_mask_is_kept():
    plan = AdaptiveCompressionPlanner().create_plan(
        _analysis(
            _image(
                is_image_mask=True,
            )
        ),
        _options(),
    )

    image = plan.images[0]

    assert image.action == ImageCompressionAction.KEEP

    assert (
        image.reason
        == "unsafe_mask_or_transparency"
    )


def test_zero_width_image_is_kept():
    plan = AdaptiveCompressionPlanner().create_plan(
        _analysis(
            _image(
                width=0,
            )
        ),
        _options(),
    )

    image = plan.images[0]

    assert image.action == ImageCompressionAction.KEEP

    assert (
        image.reason
        == "invalid_image_dimensions"
    )


def test_negative_height_image_is_kept():
    plan = AdaptiveCompressionPlanner().create_plan(
        _analysis(
            _image(
                height=-1,
            )
        ),
        _options(),
    )

    image = plan.images[0]

    assert image.action == ImageCompressionAction.KEEP

    assert (
        image.reason
        == "invalid_image_dimensions"
    )


def test_extreme_downsample_never_produces_zero_pixels():
    plan = AdaptiveCompressionPlanner().create_plan(
        _analysis(
            _image(
                width=10,
                height=5,
                dpi_x=10_000.0,
                dpi_y=10_000.0,
            )
        ),
        _options(),
    )

    image = plan.images[0]

    assert (
        image.action
        == ImageCompressionAction.DOWNSAMPLE
    )

    assert image.target_width_px >= 1
    assert image.target_height_px >= 1


def test_planner_preserves_image_order():
    plan = AdaptiveCompressionPlanner().create_plan(
        _analysis(
            _image(
                object_id="30 0 R",
                dpi_x=500.0,
                dpi_y=500.0,
            ),
            _image(
                object_id="10 0 R",
                dpi_x=100.0,
                dpi_y=100.0,
            ),
            _image(
                object_id="20 0 R",
                dpi_x=300.0,
                dpi_y=300.0,
            ),
        ),
        _options(),
    )

    assert [
        image.object_id
        for image in plan.images
    ] == [
        "30 0 R",
        "10 0 R",
        "20 0 R",
    ]