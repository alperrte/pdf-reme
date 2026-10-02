from dataclasses import dataclass
from enum import Enum


class ImageCompressionAction(str, Enum):
    KEEP = "keep"
    RECOMPRESS = "recompress"
    DOWNSAMPLE = "downsample"


@dataclass(frozen=True)
class ImageCompressionPlan:
    object_id: str
    action: ImageCompressionAction

    source_width_px: int
    source_height_px: int

    target_width_px: int
    target_height_px: int

    source_dpi: float | None
    target_dpi: float | None

    target_quality: int | None

    reason: str

    @property
    def changes_image(self) -> bool:
        return self.action != ImageCompressionAction.KEEP

    @property
    def resizes_image(self) -> bool:
        return self.action == ImageCompressionAction.DOWNSAMPLE


@dataclass(frozen=True)
class PdfCompressionPlan:
    images: tuple[ImageCompressionPlan, ...]

    @property
    def image_count(self) -> int:
        return len(self.images)

    @property
    def changed_image_count(self) -> int:
        return sum(
            1
            for image in self.images
            if image.changes_image
        )

    @property
    def downsampled_image_count(self) -> int:
        return sum(
            1
            for image in self.images
            if image.resizes_image
        )

    @property
    def kept_image_count(self) -> int:
        return sum(
            1
            for image in self.images
            if image.action == ImageCompressionAction.KEEP
        )