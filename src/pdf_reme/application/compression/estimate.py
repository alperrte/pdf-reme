from dataclasses import dataclass


@dataclass(frozen=True)
class PdfCompressionEstimate:
    original_size_bytes: int
    estimated_min_size_bytes: int
    estimated_max_size_bytes: int

    def __post_init__(self) -> None:
        if self.original_size_bytes <= 0:
            raise ValueError(
                "Orijinal dosya boyutu sıfırdan büyük olmalıdır."
            )

        if self.estimated_min_size_bytes <= 0:
            raise ValueError(
                "Minimum tahmini boyut sıfırdan büyük olmalıdır."
            )

        if self.estimated_max_size_bytes <= 0:
            raise ValueError(
                "Maximum tahmini boyut sıfırdan büyük olmalıdır."
            )

        if (
            self.estimated_min_size_bytes
            > self.estimated_max_size_bytes
        ):
            raise ValueError(
                "Minimum tahmini boyut, maximum tahmini "
                "boyuttan büyük olamaz."
            )

    @property
    def estimated_midpoint_bytes(self) -> int:
        return round(
            (
                self.estimated_min_size_bytes
                + self.estimated_max_size_bytes
            )
            / 2
        )

    @property
    def best_case_savings_percent(self) -> float:
        savings = (
            self.original_size_bytes
            - self.estimated_min_size_bytes
        )

        return round(
            max(
                0.0,
                savings / self.original_size_bytes * 100,
            ),
            2,
        )

    @property
    def worst_case_savings_percent(self) -> float:
        savings = (
            self.original_size_bytes
            - self.estimated_max_size_bytes
        )

        return round(
            max(
                0.0,
                savings / self.original_size_bytes * 100,
            ),
            2,
        )