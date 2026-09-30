from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PdfImageAnalysis:
    object_id: str
    page_numbers: tuple[int, ...]

    width_px: int
    height_px: int
    stream_size_bytes: int

    filters: tuple[str, ...]
    color_space: str | None
    bits_per_component: int | None

    has_smask: bool
    has_mask: bool
    is_image_mask: bool

    max_display_width_points: float | None = None
    max_display_height_points: float | None = None

    effective_dpi_x: float | None = None
    effective_dpi_y: float | None = None


@dataclass(frozen=True)
class PdfAnalysisResult:
    source_path: Path
    file_size_bytes: int
    page_count: int

    images: tuple[PdfImageAnalysis, ...]

    text_page_count: int
    vector_page_count: int

    @property
    def image_count(self) -> int:
        return len(self.images)

    @property
    def total_image_stream_bytes(self) -> int:
        return sum(
            image.stream_size_bytes
            for image in self.images
        )

    @property
    def contains_text(self) -> bool:
        return self.text_page_count > 0

    @property
    def contains_vector_graphics(self) -> bool:
        return self.vector_page_count > 0