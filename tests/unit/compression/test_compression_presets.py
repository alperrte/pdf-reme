import pytest

from pdf_reme.application.compression.options import (
    CompressionProfile,
)
from pdf_reme.application.compression.presets import (
    get_preset_options,
)


@pytest.mark.parametrize(
    (
        "profile",
        "min_dpi",
        "max_dpi",
        "quality",
    ),
    [
        (
            CompressionProfile.LIGHT,
            200,
            300,
            88,
        ),
        (
            CompressionProfile.BALANCED,
            120,
            200,
            78,
        ),
        (
            CompressionProfile.STRONG,
            72,
            150,
            60,
        ),
    ],
)
def test_preset_values(
    profile,
    min_dpi,
    max_dpi,
    quality,
):
    options = get_preset_options(profile)

    assert options.profile == profile
    assert options.min_dpi == min_dpi
    assert options.max_dpi == max_dpi
    assert options.image_quality == quality
    assert options.target_size_bytes is None
    assert options.allow_raster_fallback is False


def test_custom_profile_has_no_fixed_preset():
    with pytest.raises(
        ValueError,
        match="Custom profil",
    ):
        get_preset_options(
            CompressionProfile.CUSTOM
        )