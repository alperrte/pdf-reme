import pdf_reme.shared.paths.app_paths as app_paths_module
from pdf_reme.shared.paths.app_paths import AppPaths


def test_imported_library_directories_are_created(tmp_path, monkeypatch):
    test_data_dir = tmp_path / "PDF-REME"

    monkeypatch.setattr(
        app_paths_module,
        "get_app_data_dir",
        lambda: test_data_dir,
    )

    paths = AppPaths()
    paths.ensure_directories()

    assert paths.imported_pdf_dir.is_dir()
    assert paths.imported_word_dir.is_dir()
    assert paths.imported_powerpoint_dir.is_dir()
    assert paths.imported_images_dir.is_dir()