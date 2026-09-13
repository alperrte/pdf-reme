import pytest

from pdf_reme.application.services.page_selection_parser import (
    PageSelectionParser,
)


def test_parse_single_pages():
    parser = PageSelectionParser()

    result = parser.parse(
        "2,5,9",
        total_pages=10,
    )

    assert result == [2, 5, 9]


def test_parse_page_ranges():
    parser = PageSelectionParser()

    result = parser.parse(
        "2,5,8-12,37",
        total_pages=100,
    )

    assert result == [
        2,
        5,
        8,
        9,
        10,
        11,
        12,
        37,
    ]


def test_parse_removes_duplicates_preserving_order():
    parser = PageSelectionParser()

    result = parser.parse(
        "2,2,3,2,4",
        total_pages=10,
    )

    assert result == [2, 3, 4]


def test_parse_accepts_spaces():
    parser = PageSelectionParser()

    result = parser.parse(
        " 2 , 5 , 8 - 10 ",
        total_pages=20,
    )

    assert result == [
        2,
        5,
        8,
        9,
        10,
    ]


def test_parse_rejects_empty_expression():
    parser = PageSelectionParser()

    with pytest.raises(
        ValueError,
        match="Sayfa seçimi boş bırakılamaz",
    ):
        parser.parse(
            "   ",
            total_pages=10,
        )


def test_parse_rejects_zero_page():
    parser = PageSelectionParser()

    with pytest.raises(
        ValueError,
        match="Sayfa numarası 1 veya daha büyük",
    ):
        parser.parse(
            "0",
            total_pages=10,
        )


def test_parse_rejects_page_above_document_limit():
    parser = PageSelectionParser()

    with pytest.raises(
        ValueError,
        match="belge sınırını aşıyor",
    ):
        parser.parse(
            "11",
            total_pages=10,
        )


def test_parse_rejects_reverse_range():
    parser = PageSelectionParser()

    with pytest.raises(
        ValueError,
        match="başlangıcı bitişten büyük olamaz",
    ):
        parser.parse(
            "8-5",
            total_pages=10,
        )


def test_parse_rejects_invalid_text():
    parser = PageSelectionParser()

    with pytest.raises(
        ValueError,
        match="Geçersiz sayfa numarası",
    ):
        parser.parse(
            "abc",
            total_pages=10,
        )


def test_parse_rejects_invalid_range_format():
    parser = PageSelectionParser()

    with pytest.raises(
        ValueError,
        match="Geçersiz sayfa aralığı",
    ):
        parser.parse(
            "1--4",
            total_pages=10,
        )


def test_parse_rejects_empty_part():
    parser = PageSelectionParser()

    with pytest.raises(
        ValueError,
        match="Geçersiz sayfa seçim ifadesi",
    ):
        parser.parse(
            "1,,3",
            total_pages=10,
        )


def test_parse_rejects_invalid_total_pages():
    parser = PageSelectionParser()

    with pytest.raises(
        ValueError,
        match="Toplam sayfa sayısı sıfırdan büyük",
    ):
        parser.parse(
            "1",
            total_pages=0,
        )