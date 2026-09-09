import pytest

import pdf_reme.shared.paths.app_paths as app_paths_module
from pdf_reme.infrastructure.filesystem.library_path_resolver import (
    resolve_import_directory,
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


def test_pdf_resolves_to_pdf_directory(paths):
    result = resolve_import_directory("pdf", paths)
    assert result == paths.imported_pdf_dir


def test_word_resolves_to_word_directory(paths):
    result = resolve_import_directory("word", paths)
    assert result == paths.imported_word_dir


def test_powerpoint_resolves_to_powerpoint_directory(paths):
    result = resolve_import_directory("powerpoint", paths)
    assert result == paths.imported_powerpoint_dir


def test_image_resolves_to_images_directory(paths):
    result = resolve_import_directory("image", paths)
    assert result == paths.imported_images_dir


def test_unsupported_document_type_raises_value_error(paths):
    with pytest.raises(ValueError):
        resolve_import_directory("excel", paths)