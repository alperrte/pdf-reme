from pdf_reme.presentation.edit_page_map import build_page_map


def test_rotate_is_identity():
    page_map = build_page_map("rotate_pages", {"page_numbers": [3]}, 10)

    assert page_map.new_count == 10
    assert [page_map.forward(p) for p in range(1, 11)] == list(range(1, 11))
    assert [page_map.backward(p) for p in range(1, 11)] == list(range(1, 11))
    assert page_map.inserted == ()


def test_delete_selects_next_page_else_previous():
    page_map = build_page_map("delete_pages", {"page_numbers": [7]}, 10)

    assert page_map.new_count == 9
    assert page_map.neighbour_after_delete({7}) == 7  # eski 8 → yeni 7
    assert page_map.forward(6) == 6
    assert page_map.forward(8) == 7

    last = build_page_map("delete_pages", {"page_numbers": [10]}, 10)

    assert last.neighbour_after_delete({10}) == 9  # sonraki yok → önceki


def test_delete_multiple_uses_neighbour_after_last_deleted():
    page_map = build_page_map("delete_pages", {"page_numbers": [3, 4]}, 10)

    assert page_map.new_count == 8
    assert page_map.neighbour_after_delete({3, 4}) == 3  # eski 5 → yeni 3

    tail = build_page_map("delete_pages", {"page_numbers": [9, 10]}, 10)

    assert tail.neighbour_after_delete({9, 10}) == 8


def test_delete_undo_maps_back_to_surviving_neighbour():
    page_map = build_page_map("delete_pages", {"page_numbers": [7]}, 10)

    assert page_map.backward(6) == 6
    assert page_map.backward(7) == 8


def test_duplicate_puts_copy_after_source():
    page_map = build_page_map("duplicate_pages", {"page_numbers": [2, 5]}, 6)

    assert page_map.new_count == 8
    assert page_map.inserted == (3, 7)
    assert [page_map.forward(p) for p in range(1, 7)] == [1, 2, 4, 5, 6, 8]
    assert page_map.backward(3) == 3  # kopya → sonraki asıl sayfa (eski 3)
    assert page_map.backward(7) == 6


def test_insert_blank_page():
    page_map = build_page_map("insert_blank_page", {"after_page": 3}, 5)

    assert page_map.new_count == 6
    assert page_map.inserted == (4,)
    assert [page_map.forward(p) for p in range(1, 6)] == [1, 2, 3, 5, 6]
    assert page_map.backward(4) == 4  # eklenen → sonraki sağ kalan (eski 4)


def test_insert_pages_uses_source_count():
    page_map = build_page_map(
        "insert_pages",
        {
            "insert_pdf_path": "x.pdf",
            "source_page_numbers": [1, 2, 3],
            "after_page": 0,
        },
        4,
    )

    assert page_map.new_count == 7
    assert page_map.inserted == (1, 2, 3)
    assert page_map.forward(1) == 4


def test_insert_at_end_undo_falls_back_to_previous_page():
    page_map = build_page_map("insert_blank_page", {"after_page": 5}, 5)

    assert page_map.inserted == (6,)
    assert page_map.backward(6) == 5


def test_reorder_tracks_pages_to_new_positions():
    page_map = build_page_map("reorder_pages", {"page_order": [3, 1, 2]}, 3)

    assert page_map.forward(3) == 1
    assert page_map.forward(1) == 2
    assert page_map.backward(1) == 3
