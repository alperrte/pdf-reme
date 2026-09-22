import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from pdf_reme.infrastructure.filesystem.trash_file_manager import (
    TrashFileManager,
    TrashIOError,
    _safe_move,
)


def _manager(tmp_path: Path) -> TrashFileManager:
    paths = SimpleNamespace(trash_dir=tmp_path / "trash")

    return TrashFileManager(paths)


def _make_pdf(path: Path, content: bytes = b"%PDF-1.4 fake content") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)

    return path


# ----------------------------------------------------------------------
# Üretilmiş bir PDF için normal çöp/geri yükleme akışı (kilit yok)
# ----------------------------------------------------------------------


def test_move_to_trash_then_restore_round_trip(tmp_path):
    manager = _manager(tmp_path)

    source = _make_pdf(
        tmp_path / "library" / "generated" / "output.pdf"
    )
    original_bytes = source.read_bytes()

    trash_path = manager.move_to_trash(source)

    assert not source.exists()
    assert trash_path.exists()
    assert trash_path.read_bytes() == original_bytes

    restore_path = tmp_path / "library" / "generated" / "output.pdf"

    restored_path = manager.restore_from_trash(trash_path, restore_path)

    assert not trash_path.exists()
    assert restored_path.exists()
    assert restored_path.read_bytes() == original_bytes


def test_move_to_trash_generates_unique_name_on_collision(tmp_path):
    manager = _manager(tmp_path)

    first_source = _make_pdf(tmp_path / "library" / "a" / "dup.pdf", b"a")
    second_source = _make_pdf(tmp_path / "library" / "b" / "dup.pdf", b"b")

    first_trash_path = manager.move_to_trash(first_source)
    second_trash_path = manager.move_to_trash(second_source)

    assert first_trash_path != second_trash_path
    assert first_trash_path.read_bytes() == b"a"
    assert second_trash_path.read_bytes() == b"b"


# ----------------------------------------------------------------------
# `_safe_move` — kilit simülasyonu (os.rename/os.replace geçici başarısız)
# ----------------------------------------------------------------------


def test_safe_move_falls_back_to_copy_when_replace_locked(
    tmp_path, monkeypatch
):
    source = _make_pdf(tmp_path / "source.pdf")
    target = tmp_path / "trash" / "source.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)

    real_replace = os.replace

    def flaky_replace(src, dst):
        raise PermissionError("dosya başka bir işlem tarafından kullanılıyor")

    monkeypatch.setattr(os, "replace", flaky_replace)
    monkeypatch.setattr(
        "pdf_reme.infrastructure.filesystem.trash_file_manager._MOVE_RETRY_DELAY_S",
        0,
    )

    _safe_move(source, target)

    assert not source.exists()
    assert target.exists()
    assert target.read_bytes() == b"%PDF-1.4 fake content"

    monkeypatch.setattr(os, "replace", real_replace)


def test_safe_move_raises_trash_io_error_and_rolls_back_when_source_locked(
    tmp_path, monkeypatch
):
    """Kopyalama başarılı olur ama kaynağın son `unlink`'i kilit yüzünden
    başarısız olursa: hedefteki kopya geri alınır (öksüz kopya bırakılmaz)
    ve `TrashIOError` fırlatılır."""

    source = _make_pdf(tmp_path / "locked-source.pdf")
    target = tmp_path / "trash" / "locked-source.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)

    def flaky_replace(src, dst):
        raise PermissionError("dosya kilitli")

    real_unlink = Path.unlink

    def selective_unlink(self, *args, **kwargs):
        # Yalnızca kaynağın silinmesini kilitli gibi başarısız kıl;
        # rollback'in hedefi geri alma işlemi (target.unlink) etkilenmez.
        if self == source:
            raise PermissionError("kaynak hâlâ kilitli")

        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(os, "replace", flaky_replace)
    monkeypatch.setattr(
        "pdf_reme.infrastructure.filesystem.trash_file_manager._MOVE_RETRY_DELAY_S",
        0,
    )
    monkeypatch.setattr(Path, "unlink", selective_unlink)

    with pytest.raises(TrashIOError):
        _safe_move(source, target)

    # Hedefteki (öksüz kalacak) kopya geri alınmış olmalı.
    assert not target.exists()
    # Kaynak (kilitli olduğu için) hâlâ yerinde durmalı.
    assert source.exists()


def test_safe_move_raises_trash_io_error_when_copy_fails(
    tmp_path, monkeypatch
):
    source = _make_pdf(tmp_path / "uncopyable.pdf")
    target = tmp_path / "trash" / "uncopyable.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)

    def flaky_replace(src, dst):
        raise PermissionError("dosya kilitli")

    def flaky_copy2(src, dst):
        raise OSError("disk dolu")

    monkeypatch.setattr(os, "replace", flaky_replace)
    monkeypatch.setattr(
        "pdf_reme.infrastructure.filesystem.trash_file_manager._MOVE_RETRY_DELAY_S",
        0,
    )
    monkeypatch.setattr(
        "pdf_reme.infrastructure.filesystem.trash_file_manager.shutil.copy2",
        flaky_copy2,
    )

    with pytest.raises(TrashIOError):
        _safe_move(source, target)

    assert source.exists()
    assert not target.exists()


# ----------------------------------------------------------------------
# Var olan güvenlik kontrolleri korunmuş mu
# ----------------------------------------------------------------------


def test_move_to_trash_rejects_missing_file(tmp_path):
    manager = _manager(tmp_path)

    with pytest.raises(FileNotFoundError):
        manager.move_to_trash(tmp_path / "missing.pdf")


def test_permanently_delete_still_rejects_paths_outside_trash_dir(tmp_path):
    manager = _manager(tmp_path)

    outside_file = _make_pdf(tmp_path / "outside" / "not-in-trash.pdf")

    with pytest.raises(ValueError):
        manager.permanently_delete(outside_file)

    assert outside_file.exists()
