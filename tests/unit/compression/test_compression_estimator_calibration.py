import random
from io import BytesIO

from PIL import Image

from pdf_reme.application.compression.options import (
    CompressionProfile,
    PdfCompressionOptions,
)
from pdf_reme.application.pdf_analysis import (
    PdfImageAnalysis,
)
from pdf_reme.infrastructure.pdf.pdf_compression_estimator import (
    PdfCompressionEstimator,
)


def _create_noisy_jpeg(
    width: int,
    height: int,
    quality: int,
) -> bytes:
    randomizer = random.Random(12345)

    raw_pixels = randomizer.randbytes(
        width * height * 3
    )

    image = Image.frombytes(
        "RGB",
        (width, height),
        raw_pixels,
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
    )

    image.close()

    return buffer.getvalue()


def _recompress_jpeg(
    source_bytes: bytes,
    width: int,
    height: int,
    quality: int,
) -> bytes:
    source_buffer = BytesIO(
        source_bytes
    )

    with Image.open(
        source_buffer
    ) as image:
        image = image.convert("RGB")

        resized = image.resize(
            (width, height),
            Image.Resampling.LANCZOS,
        )

        output = BytesIO()

        resized.save(
            output,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
        )

        resized.close()

        return output.getvalue()


def test_jpeg_estimate_contains_real_recompressed_size():
    original = _create_noisy_jpeg(
        width=1200,
        height=800,
        quality=95,
    )

    actual = _recompress_jpeg(
        source_bytes=original,
        width=600,
        height=400,
        quality=80,
    )

    image = PdfImageAnalysis(
        object_id="10 0 R",
        page_numbers=(1,),
        width_px=1200,
        height_px=800,
        stream_size_bytes=len(original),
        filters=("/DCTDecode",),
        color_space="/DeviceRGB",
        bits_per_component=8,
        has_smask=False,
        has_mask=False,
        is_image_mask=False,
        max_display_width_points=216.0,
        max_display_height_points=144.0,
        effective_dpi_x=400.0,
        effective_dpi_y=400.0,
    )

    options = PdfCompressionOptions(
        profile=CompressionProfile.CUSTOM,
        min_dpi=100,
        max_dpi=200,
        image_quality=80,
    )

    predicted_min, predicted_max = (
        PdfCompressionEstimator()
        ._estimate_image_size(
            image=image,
            options=options,
        )
    )

    assert predicted_min <= len(actual)
    assert len(actual) <= predicted_max

import pytest


@pytest.mark.parametrize(
    (
        "effective_dpi",
        "max_dpi",
        "source_quality",
        "target_quality",
    ),
    [
        (400.0, 200, 95, 80),
        (400.0, 150, 95, 70),
        (400.0, 300, 95, 85),
        (300.0, 150, 90, 60),
    ],
)
def test_jpeg_estimator_calibration_range(
    effective_dpi,
    max_dpi,
    source_quality,
    target_quality,
):
    source_width = 1200
    source_height = 800

    scale = max_dpi / effective_dpi

    target_width = round(
        source_width * scale
    )

    target_height = round(
        source_height * scale
    )

    original = _create_noisy_jpeg(
        width=source_width,
        height=source_height,
        quality=source_quality,
    )

    actual = _recompress_jpeg(
        source_bytes=original,
        width=target_width,
        height=target_height,
        quality=target_quality,
    )

    image = PdfImageAnalysis(
        object_id="20 0 R",
        page_numbers=(1,),
        width_px=source_width,
        height_px=source_height,
        stream_size_bytes=len(original),
        filters=("/DCTDecode",),
        color_space="/DeviceRGB",
        bits_per_component=8,
        has_smask=False,
        has_mask=False,
        is_image_mask=False,
        max_display_width_points=216.0,
        max_display_height_points=144.0,
        effective_dpi_x=effective_dpi,
        effective_dpi_y=effective_dpi,
    )

    options = PdfCompressionOptions(
        profile=CompressionProfile.CUSTOM,
        min_dpi=72,
        max_dpi=max_dpi,
        image_quality=target_quality,
    )

    predicted_min, predicted_max = (
        PdfCompressionEstimator()
        ._estimate_image_size(
            image=image,
            options=options,
        )
    )

    assert predicted_min <= len(actual)
    assert len(actual) <= predicted_max