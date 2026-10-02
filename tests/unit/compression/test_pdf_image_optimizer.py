from io import BytesIO
import random

import pytest
from PIL import Image

from pdf_reme.application.compression.plan import (
    ImageCompressionAction,
    ImageCompressionPlan,
)
from pdf_reme.infrastructure.pdf.pdf_image_optimizer import (
    PdfImageOptimizer,
)

from pdf_reme.application.compression.optimization import (
    ImageOptimizationResult,
)

def _jpeg_bytes(
    width=1200,
    height=800,
    quality=95,
):
    randomizer = random.Random(12345)

    pixels = randomizer.randbytes(
        width * height * 3
    )

    image = Image.frombytes(
        "RGB",
        (width, height),
        pixels,
    )

    output = BytesIO()

    image.save(
        output,
        format="JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
    )

    image.close()

    return output.getvalue()


def _plan(
    *,
    action,
    source_width=1200,
    source_height=800,
    target_width=1200,
    target_height=800,
    quality=80,
):
    return ImageCompressionPlan(
        object_id="10 0 R",
        action=action,
        source_width_px=source_width,
        source_height_px=source_height,
        target_width_px=target_width,
        target_height_px=target_height,
        source_dpi=400.0,
        target_dpi=200.0,
        target_quality=quality,
        reason="test",
    )


def test_keep_returns_original_bytes():
    source = _jpeg_bytes()

    result = PdfImageOptimizer().optimize_jpeg(
        source,
        _plan(
            action=ImageCompressionAction.KEEP,
            quality=None,
        ),
    )

    assert result.data == source
    assert result.changed is False
    assert result.resized is False
    assert result.saved_bytes == 0


def test_downsample_reduces_dimensions():
    source = _jpeg_bytes()

    result = PdfImageOptimizer().optimize_jpeg(
        source,
        _plan(
            action=ImageCompressionAction.DOWNSAMPLE,
            target_width=600,
            target_height=400,
            quality=80,
        ),
    )

    assert result.changed is True
    assert result.resized is True

    assert result.output_width_px == 600
    assert result.output_height_px == 400

    assert (
        result.optimized_size_bytes
        < result.original_size_bytes
    )


def test_recompress_keeps_pixel_dimensions():
    source = _jpeg_bytes(
        quality=95
    )

    result = PdfImageOptimizer().optimize_jpeg(
        source,
        _plan(
            action=ImageCompressionAction.RECOMPRESS,
            quality=60,
        ),
    )

    assert result.output_width_px == 1200
    assert result.output_height_px == 800

    assert result.resized is False
    assert result.changed is True

    assert (
        result.optimized_size_bytes
        < result.original_size_bytes
    )


def test_output_is_valid_jpeg():
    source = _jpeg_bytes()

    result = PdfImageOptimizer().optimize_jpeg(
        source,
        _plan(
            action=ImageCompressionAction.DOWNSAMPLE,
            target_width=600,
            target_height=400,
        ),
    )

    with Image.open(
        BytesIO(result.data)
    ) as image:
        assert image.format == "JPEG"
        assert image.size == (600, 400)


def test_source_dimension_mismatch_is_rejected():
    source = _jpeg_bytes(
        width=1200,
        height=800,
    )

    plan = _plan(
        action=ImageCompressionAction.DOWNSAMPLE,
        source_width=1000,
        source_height=800,
        target_width=500,
        target_height=400,
    )

    with pytest.raises(
        ValueError,
        match="kaynak görsel boyutu",
    ):
        PdfImageOptimizer().optimize_jpeg(
            source,
            plan,
        )


def test_empty_source_is_rejected():
    with pytest.raises(
        ValueError,
        match="boş olamaz",
    ):
        PdfImageOptimizer().optimize_jpeg(
            b"",
            _plan(
                action=ImageCompressionAction.KEEP,
            ),
        )


def test_changing_image_requires_quality():
    source = _jpeg_bytes()

    plan = _plan(
        action=ImageCompressionAction.DOWNSAMPLE,
        target_width=600,
        target_height=400,
        quality=None,
    )

    with pytest.raises(
        ValueError,
        match="hedef kalite",
    ):
        PdfImageOptimizer().optimize_jpeg(
            source,
            plan,
        )

def _jpeg_bytes_for_mode(
    mode: str,
    width: int = 400,
    height: int = 300,
    quality: int = 95,
) -> bytes:
    randomizer = random.Random(54321)

    channel_count = {
        "L": 1,
        "RGB": 3,
        "CMYK": 4,
    }[mode]

    pixels = randomizer.randbytes(
        width * height * channel_count
    )

    image = Image.frombytes(
        mode,
        (width, height),
        pixels,
    )

    output = BytesIO()

    image.save(
        output,
        format="JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
    )

    image.close()

    return output.getvalue()


def test_grayscale_jpeg_can_be_optimized():
    source = _jpeg_bytes_for_mode(
        "L",
    )

    plan = _plan(
        action=ImageCompressionAction.RECOMPRESS,
        source_width=400,
        source_height=300,
        target_width=400,
        target_height=300,
        quality=60,
    )

    result = PdfImageOptimizer().optimize_jpeg(
        source,
        plan,
    )

    assert result.output_width_px == 400
    assert result.output_height_px == 300

    with Image.open(
        BytesIO(result.data)
    ) as image:
        assert image.format == "JPEG"


def test_cmyk_jpeg_can_be_optimized():
    source = _jpeg_bytes_for_mode(
        "CMYK",
    )

    plan = _plan(
        action=ImageCompressionAction.RECOMPRESS,
        source_width=400,
        source_height=300,
        target_width=400,
        target_height=300,
        quality=60,
    )

    result = PdfImageOptimizer().optimize_jpeg(
        source,
        plan,
    )

    assert result.output_width_px == 400
    assert result.output_height_px == 300

    with Image.open(
        BytesIO(result.data)
    ) as image:
        assert image.format == "JPEG"


def test_larger_optimized_output_falls_back_to_source(
    monkeypatch,
):
    source = _jpeg_bytes(
        width=400,
        height=300,
        quality=80,
    )

    optimizer = PdfImageOptimizer()

    monkeypatch.setattr(
        optimizer,
        "_encode_jpeg",
        lambda image, quality: (
            b"x" * (len(source) + 100)
        ),
    )

    result = optimizer.optimize_jpeg(
        source,
        _plan(
            action=ImageCompressionAction.RECOMPRESS,
            source_width=400,
            source_height=300,
            target_width=400,
            target_height=300,
            quality=80,
        ),
    )

    assert result.data == source
    assert result.changed is False
    assert result.resized is False
    assert result.saved_bytes == 0
    assert result.optimized_size_bytes == len(source)


def test_savings_percent_is_calculated():

    result = ImageOptimizationResult(
        data=b"x" * 600,
        original_size_bytes=1000,
        optimized_size_bytes=600,
        original_width_px=100,
        original_height_px=100,
        output_width_px=80,
        output_height_px=80,
        changed=True,
        resized=True,
    )

    assert result.saved_bytes == 400
    assert result.savings_percent == 40.0


def test_savings_never_becomes_negative():

    result = ImageOptimizationResult(
        data=b"x" * 1200,
        original_size_bytes=1000,
        optimized_size_bytes=1200,
        original_width_px=100,
        original_height_px=100,
        output_width_px=100,
        output_height_px=100,
        changed=False,
        resized=False,
    )

    assert result.saved_bytes == 0
    assert result.savings_percent == 0.0