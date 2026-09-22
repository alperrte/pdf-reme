import pytest

from pdf_reme.presentation.widgets.reorderable_list import move_item

ABCD = ["A", "B", "C", "D"]


@pytest.mark.parametrize(
    "source, slot, expected",
    [
        (3, 0, ["D", "A", "B", "C"]),  # sondakini başa
        (0, 4, ["B", "C", "D", "A"]),  # baştakini sona
        (0, 2, ["B", "A", "C", "D"]),  # aşağı: kaynak çıkınca slot kayar
        (2, 0, ["C", "A", "B", "D"]),  # yukarı
        (1, 1, ABCD),  # kendi üstüne
        (1, 2, ABCD),  # kendi hemen altına
        (2, 4, ["A", "B", "D", "C"]),
    ],
)
def test_move_item_slot_semantics(source, slot, expected):
    assert move_item(ABCD, source, slot) == expected


def test_move_item_does_not_mutate_input():
    items = list(ABCD)

    move_item(items, 3, 0)

    assert items == ABCD


@pytest.mark.parametrize("source", [-1, 4, 99])
def test_move_item_invalid_source_is_noop(source):
    assert move_item(ABCD, source, 0) == ABCD


def test_move_item_clamps_slot():
    assert move_item(ABCD, 0, 99) == ["B", "C", "D", "A"]
    assert move_item(ABCD, 3, -5) == ["D", "A", "B", "C"]


def test_move_item_drag_then_arrow_sequence():
    """A,B,C,D → sürükle → D,A,C,B → ok (B yukarı) → D,A,B,C."""
    order = move_item(ABCD, 3, 0)
    order = move_item(order, 2, 4)

    assert order == ["D", "A", "C", "B"]

    order[2], order[3] = order[3], order[2]

    assert order == ["D", "A", "B", "C"]
