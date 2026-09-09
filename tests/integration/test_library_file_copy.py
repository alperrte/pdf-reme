import shutil

import pytest

import pdf_reme.shared.paths.app_paths as app_paths_module
from pdf_reme.infrastructure.filesystem.library_file_copy import (
    copy_file_to_library,
)
from pdf_reme.shared.paths.app_paths import AppPaths


@pytest.fixture
def paths(tmp_path, monkeypatch):
    test_data_dir = tmp_path / "PDF-REME"

    monkeypatch.setattr(
        app_paths_module,
        "get_app_data_dir",
        lambda: test_data_dir,
    )

    app_paths = AppPaths()
    app_paths.ensure_directories()

    return app_paths


def test_pdf_is_copied_to_imported_pdf_directory(tmp_path, paths):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"test pdf content")

    target = copy_file_to_library(
        source,
        "pdf",
        paths,
    )

    assert target.is_file()
    assert target.parent == paths.imported_pdf_dir
    assert target.name == "report.pdf"
    assert target.read_bytes() == source.read_bytes()


def test_source_file_is_not_modified(tmp_path, paths):
    source = tmp_path / "original.pdf"
    original_content = b"original source content"
    source.write_bytes(original_content)

    copy_file_to_library(
        source,
        "pdf",
        paths,
    )

    assert source.exists()
    assert source.read_bytes() == original_content


def test_existing_filename_is_not_overwritten(tmp_path, paths):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"new content")

    existing_target = paths.imported_pdf_dir / "report.pdf"
    existing_target.write_bytes(b"existing content")

    target = copy_file_to_library(
        source,
        "pdf",
        paths,
    )

    assert target != existing_target
    assert target.is_file()

    assert existing_target.read_bytes() == b"existing content"
    assert target.read_bytes() == b"new content"

    assert target.name.startswith("report_")
    assert target.suffix == ".pdf"


def test_missing_source_raises_file_not_found(paths):
    missing = paths.data_dir / "missing.pdf"

    with pytest.raises(FileNotFoundError):
        copy_file_to_library(
            missing,
            "pdf",
            paths,
        )


def test_partial_file_is_removed_when_copy_fails(
    tmp_path,
    paths,
    monkeypatch,
):
    source = tmp_path / "broken-copy.pdf"
    source.write_bytes(b"source content")

    def failing_copy(source_path, destination_path):
        destination_path.write_bytes(b"partial")
        raise OSError("Simulated copy failure")

    monkeypatch.setattr(
        shutil,
        "copy2",
        failing_copy,
    )

    with pytest.raises(OSError):
        copy_file_to_library(
            source,
            "pdf",
            paths,
        )

    part_files = list(
        paths.imported_pdf_dir.glob("*.part")
    )

    assert part_files == []