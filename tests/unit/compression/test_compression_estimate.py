import pytest

from pdf_reme.application.compression.estimate import (
    PdfCompressionEstimate,
)


def test_estimate_stores_size_range():
    estimate = PdfCompressionEstimate(
        original_size_bytes=30_000_000,
        estimated_min_size_bytes=8_000_000,
        estimated_max_size_bytes=10_000_000,
    )

    assert estimate.original_size_bytes == 30_000_000
    assert estimate.estimated_min_size_bytes == 8_000_000
    assert estimate.estimated_max_size_bytes == 10_000_000


def test_estimated_midpoint_is_calculated():
    estimate = PdfCompressionEstimate(
        original_size_bytes=30_000_000,
        estimated_min_size_bytes=8_000_000,
        estimated_max_size_bytes=10_000_000,
    )

    assert estimate.estimated_midpoint_bytes == 9_000_000


def test_savings_range_is_calculated():
    estimate = PdfCompressionEstimate(
        original_size_bytes=20_000_000,
        estimated_min_size_bytes=5_000_000,
        estimated_max_size_bytes=10_000_000,
    )

    assert estimate.best_case_savings_percent == 75.0
    assert estimate.worst_case_savings_percent == 50.0


def test_estimate_can_be_larger_than_original():
    estimate = PdfCompressionEstimate(
        original_size_bytes=1_000_000,
        estimated_min_size_bytes=1_100_000,
        estimated_max_size_bytes=1_300_000,
    )

    assert estimate.best_case_savings_percent == 0.0
    assert estimate.worst_case_savings_percent == 0.0


@pytest.mark.parametrize(
    (
        "original_size",
        "minimum",
        "maximum",
    ),
    [
        (0, 100, 200),
        (1000, 0, 200),
        (1000, 100, 0),
        (1000, 500, 400),
    ],
)
def test_invalid_estimate_values_are_rejected(
    original_size,
    minimum,
    maximum,
):
    with pytest.raises(ValueError):
        PdfCompressionEstimate(
            original_size_bytes=original_size,
            estimated_min_size_bytes=minimum,
            estimated_max_size_bytes=maximum,
        )