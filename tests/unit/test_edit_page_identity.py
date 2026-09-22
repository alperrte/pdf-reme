from pdf_reme.presentation.edit_page_labels import identity_label
from pdf_reme.presentation.edit_page_map import (
    PageIdentity,
    apply_identity_step,
    initial_identities,
)


def _tr(key: str) -> str:
    table = {
        "edit.identity.original": "Orijinal: {page}",
        "edit.identity.blank": "Yeni Sayfa",
        "edit.identity.inserted": "Kaynak PDF Sayfa {page}",
        "edit.identity.duplicate": "Kopya: Sayfa {page}",
    }

    return table[key]


def test_initial_identities_are_original_and_match_position():
    identities = initial_identities(3)

    assert identities == (
        PageIdentity("original", original_page=1),
        PageIdentity("original", original_page=2),
        PageIdentity("original", original_page=3),
    )

    # Kaymamış orijinal sayfada ikinci satır boş (gürültü yok).
    for position, identity in enumerate(identities, start=1):
        assert identity_label(identity, position, _tr) == ""


def test_rotate_does_not_change_identities():
    identities = initial_identities(4)

    result = apply_identity_step(identities, "rotate_pages", {"page_numbers": [2]})

    assert result == identities


def test_delete_drops_identities_of_deleted_pages():
    identities = initial_identities(5)

    result = apply_identity_step(
        identities, "delete_pages", {"page_numbers": [2, 4]}
    )

    assert [identity.original_page for identity in result] == [1, 3, 5]

    # Kalan sayfaların yeni konumu eski orijinal numarasından kaymış;
    # ikinci satır artık "Orijinal: N" göstermeli.
    assert identity_label(result[1], 2, _tr) == "Orijinal: 3"
    assert identity_label(result[2], 3, _tr) == "Orijinal: 5"


def test_duplicate_inserts_copy_with_nearest_source_position():
    identities = initial_identities(3)

    result = apply_identity_step(
        identities, "duplicate_pages", {"page_numbers": [2]}
    )

    assert [identity.kind for identity in result] == [
        "original",
        "original",
        "duplicate",
        "original",
    ]
    assert result[2].source_display_page == 2
    assert identity_label(result[2], 3, _tr) == "Kopya: Sayfa 2"


def test_duplicate_of_duplicate_points_to_nearest_source_not_root():
    identities = initial_identities(2)

    step1 = apply_identity_step(
        identities, "duplicate_pages", {"page_numbers": [1]}
    )
    # step1: [original(1), duplicate(source=1), original(2)]
    assert step1[1].kind == "duplicate"
    assert step1[1].source_display_page == 1

    step2 = apply_identity_step(
        step1, "duplicate_pages", {"page_numbers": [2]}
    )
    # Kopyanın kopyası: en yakın kaynak (adım anındaki pozisyon = 2), köke
    # (orijinal 1) değil.
    assert step2[2].kind == "duplicate"
    assert step2[2].source_display_page == 2


def test_insert_blank_page_between_originals():
    identities = initial_identities(3)

    result = apply_identity_step(
        identities, "insert_blank_page", {"after_page": 1}
    )

    assert [identity.kind for identity in result] == [
        "original",
        "blank",
        "original",
        "original",
    ]
    assert identity_label(result[1], 2, _tr) == "Yeni Sayfa"


def test_insert_pages_labels_source_pdf_page_numbers():
    identities = initial_identities(2)

    result = apply_identity_step(
        identities,
        "insert_pages",
        {
            "insert_pdf_path": "x.pdf",
            "source_page_numbers": [3, 1],
            "after_page": 0,
        },
    )

    assert [identity.kind for identity in result] == [
        "inserted",
        "inserted",
        "original",
        "original",
    ]
    assert result[0].source_pdf_page == 1
    assert result[1].source_pdf_page == 3
    assert identity_label(result[0], 1, _tr) == "Kaynak PDF Sayfa 1"


def test_reorder_carries_identities_to_new_positions():
    identities = initial_identities(3)

    result = apply_identity_step(
        identities, "reorder_pages", {"page_order": [3, 1, 2]}
    )

    assert [identity.original_page for identity in result] == [3, 1, 2]

    # Sıralama sonrası orijinal 1, artık 2. konumda -> "Orijinal: 1" gösterir.
    assert identity_label(result[1], 2, _tr) == "Orijinal: 1"
    # Orijinal 3, hâlâ 1. konumda kalmadığı için etiketlenir.
    assert identity_label(result[0], 1, _tr) == "Orijinal: 3"
