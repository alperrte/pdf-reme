import pytest

from pdf_reme.application.services.page_edit_history import (
    PageEditHistory,
)


def test_history_starts_with_initial_state():
    history = PageEditHistory(
        "original.pdf"
    )

    assert history.current.file_path == "original.pdf"
    assert history.can_undo is False
    assert history.can_redo is False


def test_history_can_undo():
    history = PageEditHistory(
        "original.pdf"
    )

    history.push(
        "edit-1.pdf",
        "rotate",
    )

    state = history.undo()

    assert state.file_path == "original.pdf"


def test_history_can_redo():
    history = PageEditHistory(
        "original.pdf"
    )

    history.push(
        "edit-1.pdf",
        "rotate",
    )

    history.undo()

    state = history.redo()

    assert state.file_path == "edit-1.pdf"


def test_push_after_undo_clears_redo_history():
    history = PageEditHistory(
        "original.pdf"
    )

    history.push(
        "edit-1.pdf",
        "rotate",
    )

    history.push(
        "edit-2.pdf",
        "delete",
    )

    history.undo()

    history.push(
        "edit-3.pdf",
        "duplicate",
    )

    assert history.current.file_path == "edit-3.pdf"
    assert history.can_redo is False


def test_history_rejects_undo_at_initial_state():
    history = PageEditHistory(
        "original.pdf"
    )

    with pytest.raises(
        ValueError,
        match="Geri alınacak işlem",
    ):
        history.undo()


def test_history_rejects_redo_at_latest_state():
    history = PageEditHistory(
        "original.pdf"
    )

    with pytest.raises(
        ValueError,
        match="İleri alınacak işlem",
    ):
        history.redo()