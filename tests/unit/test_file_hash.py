import hashlib

import pytest

from pdf_reme.infrastructure.filesystem.file_hash import calculate_sha256


def test_calculate_sha256_returns_correct_hash(tmp_path):
    test_file = tmp_path / "sample.txt"
    content = b"PDF-REME test file"

    test_file.write_bytes(content)

    expected_hash = hashlib.sha256(content).hexdigest()
    calculated_hash = calculate_sha256(test_file)

    assert calculated_hash == expected_hash
    assert len(calculated_hash) == 64


def test_same_content_produces_same_hash(tmp_path):
    first_file = tmp_path / "first.pdf"
    second_file = tmp_path / "second.pdf"

    content = b"same pdf content"

    first_file.write_bytes(content)
    second_file.write_bytes(content)

    first_hash = calculate_sha256(first_file)
    second_hash = calculate_sha256(second_file)

    assert first_hash == second_hash


def test_different_content_produces_different_hash(tmp_path):
    first_file = tmp_path / "first.pdf"
    second_file = tmp_path / "second.pdf"

    first_file.write_bytes(b"first content")
    second_file.write_bytes(b"second content")

    first_hash = calculate_sha256(first_file)
    second_hash = calculate_sha256(second_file)

    assert first_hash != second_hash


def test_large_file_is_hashed_in_chunks(tmp_path):
    test_file = tmp_path / "large.pdf"

    content = b"A" * (3 * 1024 * 1024)
    test_file.write_bytes(content)

    calculated_hash = calculate_sha256(
        test_file,
        chunk_size=1024 * 1024,
    )

    expected_hash = hashlib.sha256(content).hexdigest()

    assert calculated_hash == expected_hash


def test_missing_file_raises_file_not_found(tmp_path):
    missing_file = tmp_path / "missing.pdf"

    with pytest.raises(FileNotFoundError):
        calculate_sha256(missing_file)