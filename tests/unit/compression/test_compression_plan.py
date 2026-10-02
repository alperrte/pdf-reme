from pdf_reme.application.compression.plan import (
    ImageCompressionAction,
    ImageCompressionPlan,
    PdfCompressionPlan,
)


def test_keep_plan_does_not_change_image():
    image = ImageCompressionPlan(
        object_id="10 0 R",
        action=ImageCompressionAction.KEEP,
        source_width_px=1200,
        source_height_px=800,
        target_width_px=1200,
        target_height_px=800,
        source_dpi=150.0,
        target_dpi=150.0,
        target_quality=None,
        reason="already_within_dpi_range",
    )

    assert image.changes_image is False
    assert image.resizes_image is False


def test_recompress_plan_changes_without_resizing():
    image = ImageCompressionPlan(
        object_id="11 0 R",
        action=ImageCompressionAction.RECOMPRESS,
        source_width_px=1200,
        source_height_px=800,
        target_width_px=1200,
        target_height_px=800,
        source_dpi=150.0,
        target_dpi=150.0,
        target_quality=80,
        reason="quality_optimization",
    )

    assert image.changes_image is True
    assert image.resizes_image is False


def test_downsample_plan_changes_and_resizes_image():
    image = ImageCompressionPlan(
        object_id="12 0 R",
        action=ImageCompressionAction.DOWNSAMPLE,
        source_width_px=2400,
        source_height_px=1600,
        target_width_px=1200,
        target_height_px=800,
        source_dpi=400.0,
        target_dpi=200.0,
        target_quality=80,
        reason="effective_dpi_above_maximum",
    )

    assert image.changes_image is True
    assert image.resizes_image is True


def test_pdf_plan_calculates_summary_counts():
    plan = PdfCompressionPlan(
        images=(
            ImageCompressionPlan(
                object_id="10 0 R",
                action=ImageCompressionAction.KEEP,
                source_width_px=100,
                source_height_px=100,
                target_width_px=100,
                target_height_px=100,
                source_dpi=100.0,
                target_dpi=100.0,
                target_quality=None,
                reason="keep",
            ),
            ImageCompressionPlan(
                object_id="11 0 R",
                action=ImageCompressionAction.RECOMPRESS,
                source_width_px=200,
                source_height_px=200,
                target_width_px=200,
                target_height_px=200,
                source_dpi=150.0,
                target_dpi=150.0,
                target_quality=80,
                reason="recompress",
            ),
            ImageCompressionPlan(
                object_id="12 0 R",
                action=ImageCompressionAction.DOWNSAMPLE,
                source_width_px=400,
                source_height_px=400,
                target_width_px=200,
                target_height_px=200,
                source_dpi=400.0,
                target_dpi=200.0,
                target_quality=70,
                reason="downsample",
            ),
        )
    )

    assert plan.image_count == 3
    assert plan.changed_image_count == 2
    assert plan.downsampled_image_count == 1
    assert plan.kept_image_count == 1