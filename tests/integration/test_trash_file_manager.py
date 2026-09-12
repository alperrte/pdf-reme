from pathlib import Path
from types import SimpleNamespace

import pytest

from pdf_reme.infrastructure.filesystem.trash_file_manager import (
    TrashFileManager,
)


def create_manager(tmp_path: Path) -> TrashFileManager:
    trash_dir = tmp_path / "trash"

    paths = SimpleNamespace(
        trash_dir=trash_dir,
    )

    return TrashFileManager(paths)


def test_move_to_trash_moves_file(tmp_path):
    manager = create_manager(tmp_path)

    source = tmp_path / "test.pdf"
    source.write_bytes(b"pdf-content")

    target = manager.move_to_trash(source)

    assert not source.exists()
    assert target.exists()
    assert target.parent == tmp_path / "trash"
    assert target.name == "test.pdf"
    assert target.read_bytes() == b"pdf-content"


def test_move_to_trash_creates_trash_directory(tmp_path):
    manager = create_manager(tmp_path)

    source = tmp_path / "document.pdf"
    source.write_bytes(b"content")

    trash_dir = tmp_path / "trash"

    assert not trash_dir.exists()

    manager.move_to_trash(source)

    assert trash_dir.exists()
    assert trash_dir.is_dir()


def test_move_to_trash_does_not_overwrite_same_named_file(tmp_path):
    manager = create_manager(tmp_path)

    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()

    existing = trash_dir / "test.pdf"
    existing.write_bytes(b"old-content")

    source = tmp_path / "test.pdf"
    source.write_bytes(b"new-content")

    target = manager.move_to_trash(source)

    assert existing.read_bytes() == b"old-content"

    assert target.exists()
    assert target != existing
    assert target.name.startswith("test_")
    assert target.suffix == ".pdf"
    assert target.read_bytes() == b"new-content"


def test_move_to_trash_raises_for_missing_file(tmp_path):
    manager = create_manager(tmp_path)

    missing = tmp_path / "missing.pdf"

    with pytest.raises(FileNotFoundError):
        manager.move_to_trash(missing)


def test_move_to_trash_rejects_directory(tmp_path):
    manager = create_manager(tmp_path)

    directory = tmp_path / "folder"
    directory.mkdir()

    with pytest.raises(ValueError):
        manager.move_to_trash(directory)

def test_restore_from_trash_restores_file_to_original_location(tmp_path):
    manager = create_manager(tmp_path)

    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()

    trash_file = trash_dir / "test.pdf"
    trash_file.write_bytes(b"pdf-content")

    restore_path = (
        tmp_path
        / "library"
        / "imported"
        / "pdf"
        / "test.pdf"
    )

    restored = manager.restore_from_trash(
        trash_file,
        restore_path,
    )

    assert not trash_file.exists()
    assert restored.exists()
    assert restored == restore_path
    assert restored.read_bytes() == b"pdf-content"


def test_restore_from_trash_creates_missing_parent_directories(tmp_path):
    manager = create_manager(tmp_path)

    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()

    trash_file = trash_dir / "document.pdf"
    trash_file.write_bytes(b"content")

    restore_path = (
        tmp_path
        / "library"
        / "imported"
        / "pdf"
        / "document.pdf"
    )

    manager.restore_from_trash(
        trash_file,
        restore_path,
    )

    assert restore_path.parent.exists()
    assert restore_path.exists()


def test_restore_from_trash_does_not_overwrite_existing_file(tmp_path):
    manager = create_manager(tmp_path)

    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()

    trash_file = trash_dir / "test.pdf"
    trash_file.write_bytes(b"trash-content")

    restore_dir = (
        tmp_path
        / "library"
        / "imported"
        / "pdf"
    )
    restore_dir.mkdir(parents=True)

    existing = restore_dir / "test.pdf"
    existing.write_bytes(b"existing-content")

    restored = manager.restore_from_trash(
        trash_file,
        existing,
    )

    assert existing.read_bytes() == b"existing-content"

    assert restored.exists()
    assert restored != existing
    assert restored.name.startswith("test_")
    assert restored.suffix == ".pdf"
    assert restored.read_bytes() == b"trash-content"


def test_restore_from_trash_raises_for_missing_file(tmp_path):
    manager = create_manager(tmp_path)

    missing = tmp_path / "trash" / "missing.pdf"
    restore_path = tmp_path / "library" / "missing.pdf"

    with pytest.raises(FileNotFoundError):
        manager.restore_from_trash(
            missing,
            restore_path,
        )


def test_restore_from_trash_rejects_directory(tmp_path):
    manager = create_manager(tmp_path)

    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()

    directory = trash_dir / "folder"
    directory.mkdir()

    restore_path = tmp_path / "library" / "folder"

    with pytest.raises(ValueError):
        manager.restore_from_trash(
            directory,
            restore_path,
        )

def test_permanently_delete_removes_file_from_trash(tmp_path):
    manager = create_manager(tmp_path)

    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()

    trash_file = trash_dir / "delete-me.pdf"
    trash_file.write_bytes(b"pdf-content")

    result = manager.permanently_delete(trash_file)

    assert result is True
    assert not trash_file.exists()


def test_permanently_delete_returns_false_when_file_missing(tmp_path):
    manager = create_manager(tmp_path)

    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()

    missing_file = trash_dir / "missing.pdf"

    result = manager.permanently_delete(missing_file)

    assert result is False


def test_permanently_delete_rejects_file_outside_trash(tmp_path):
    manager = create_manager(tmp_path)

    outside_file = tmp_path / "library" / "important.pdf"
    outside_file.parent.mkdir(parents=True)
    outside_file.write_bytes(b"important-content")

    with pytest.raises(
        ValueError,
        match="Yalnızca PDF-REME çöp kutusundaki dosyalar",
    ):
        manager.permanently_delete(outside_file)

    assert outside_file.exists()


def test_permanently_delete_rejects_directory(tmp_path):
    manager = create_manager(tmp_path)

    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()

    directory = trash_dir / "folder"
    directory.mkdir()

    with pytest.raises(
        ValueError,
        match="Yalnızca dosyalar kalıcı olarak silinebilir",
    ):
        manager.permanently_delete(directory)

    assert directory.exists()