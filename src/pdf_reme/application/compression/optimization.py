from dataclasses import dataclass


@dataclass(frozen=True)
class ImageOptimizationResult:
    data: bytes

    original_size_bytes: int
    optimized_size_bytes: int

    original_width_px: int
    original_height_px: int

    output_width_px: int
    output_height_px: int

    changed: bool
    resized: bool

    @property
    def saved_bytes(self) -> int:
        return max(
            0,
            self.original_size_bytes
            - self.optimized_size_bytes,
        )

    @property
    def savings_percent(self) -> float:
        if self.original_size_bytes <= 0:
            return 0.0

        return round(
            (
                self.saved_bytes
                / self.original_size_bytes
            )
            * 100,
            2,
        )