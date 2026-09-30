from dataclasses import dataclass
from enum import Enum


class CompressionProfile(str, Enum):
    LIGHT = "light"
    BALANCED = "balanced"
    STRONG = "strong"
    CUSTOM = "custom"


@dataclass(frozen=True)
class PdfCompressionOptions:
    profile: CompressionProfile
    min_dpi: int
    max_dpi: int
    image_quality: int
    target_size_bytes: int | None = None
    allow_raster_fallback: bool = False

    def __post_init__(self) -> None:
        if not 36 <= self.min_dpi <= 600:
            raise ValueError(
                "Minimum DPI 36 ile 600 arasında olmalıdır."
            )

        if not 36 <= self.max_dpi <= 600:
            raise ValueError(
                "Maximum DPI 36 ile 600 arasında olmalıdır."
            )

        if self.min_dpi > self.max_dpi:
            raise ValueError(
                "Minimum DPI, maximum DPI değerinden büyük olamaz."
            )

        if not 10 <= self.image_quality <= 100:
            raise ValueError(
                "Görsel kalitesi 10 ile 100 arasında olmalıdır."
            )

        if (
            self.target_size_bytes is not None
            and self.target_size_bytes <= 0
        ):
            raise ValueError(
                "Hedef dosya boyutu sıfırdan büyük olmalıdır."
            )