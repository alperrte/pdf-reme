import pytest

from pdf_reme.application.compression.options import (
    CompressionProfile,
    PdfCompressionOptions,
)


def test_valid_custom_options():
    options = PdfCompressionOptions(
        profile=CompressionProfile.CUSTOM,
        min_dpi=100,
        max_dpi=200,
        image_quality=80,
        target_size_bytes=10 * 1024 * 1024,
        allow_raster_fallback=True,
    )

    assert options.profile == CompressionProfile.CUSTOM
    assert options.min_dpi == 100
    assert options.max_dpi == 200
    assert options.image_quality == 80
    assert options.target_size_bytes == 10 * 1024 * 1024
    assert options.allow_raster_fallback is True


def test_target_size_is_optional():
    options = PdfCompressionOptions(
        profile=CompressionProfile.BALANCED,
        min_dpi=120,
        max_dpi=200,
        image_quality=80,
    )

    assert options.target_size_bytes is None
    assert options.allow_raster_fallback is False


def test_min_dpi_cannot_exceed_max_dpi():
    with pytest.raises(ValueError, match="Minimum DPI"):
        PdfCompressionOptions(
            profile=CompressionProfile.CUSTOM,
            min_dpi=250,
            max_dpi=150,
            image_quality=80,
        )


@pytest.mark.parametrize(
    "quality",
    [0, 9, 101, 200],
)
def test_invalid_image_quality_is_rejected(quality):
    with pytest.raises(ValueError, match="Görsel kalitesi"):
        PdfCompressionOptions(
            profile=CompressionProfile.CUSTOM,
            min_dpi=100,
            max_dpi=200,
            image_quality=quality,
        )


@pytest.mark.parametrize(
    "min_dpi,max_dpi",
    [
        (35, 200),
        (100, 601),
    ],
)
def test_invalid_dpi_is_rejected(min_dpi, max_dpi):
    with pytest.raises(ValueError):
        PdfCompressionOptions(
            profile=CompressionProfile.CUSTOM,
            min_dpi=min_dpi,
            max_dpi=max_dpi,
            image_quality=80,
        )


def test_invalid_target_size_is_rejected():
    with pytest.raises(ValueError, match="Hedef dosya boyutu"):
        PdfCompressionOptions(
            profile=CompressionProfile.CUSTOM,
            min_dpi=100,
            max_dpi=200,
            image_quality=80,
            target_size_bytes=0,
        )