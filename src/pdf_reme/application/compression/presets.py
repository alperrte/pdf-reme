from pdf_reme.application.compression.options import (
    CompressionProfile,
    PdfCompressionOptions,
)

_PRESETS = {
    CompressionProfile.LIGHT: PdfCompressionOptions(
        profile=CompressionProfile.LIGHT,
        min_dpi=200,
        max_dpi=300,
        image_quality=88,
        allow_raster_fallback=False,
    ),
    CompressionProfile.BALANCED: PdfCompressionOptions(
        profile=CompressionProfile.BALANCED,
        min_dpi=120,
        max_dpi=200,
        image_quality=78,
        allow_raster_fallback=False,
    ),
    CompressionProfile.STRONG: PdfCompressionOptions(
        profile=CompressionProfile.STRONG,
        min_dpi=72,
        max_dpi=150,
        image_quality=60,
        allow_raster_fallback=False,
    ),
}


def get_preset_options(
    profile: CompressionProfile,
) -> PdfCompressionOptions:
    if profile == CompressionProfile.CUSTOM:
        raise ValueError(
            "Custom profil için ayarlar kullanıcı tarafından verilmelidir."
        )

    try:
        return _PRESETS[profile]
    except KeyError as exc:
        raise ValueError(
            f"Desteklenmeyen sıkıştırma profili: {profile}"
        ) from exc