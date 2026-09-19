import json

import pytest

from pdf_reme.presentation.update_checker import (
    STATUS_ERROR,
    STATUS_NO_RELEASE,
    STATUS_UP_TO_DATE,
    STATUS_UPDATE_AVAILABLE,
    interpret_response,
    is_newer,
    parse_version,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1.2.3", (1, 2, 3)),
        ("v1.2.3", (1, 2, 3)),
        ("V2.0", (2, 0)),
        ("1.4.0-beta.1", (1, 4, 0)),
        ("1.2.10", (1, 2, 10)),
        ("  v3  ", (3,)),
        ("", ()),
        ("abc", ()),
    ],
)
def test_parse_version(text, expected):
    assert parse_version(text) == expected


@pytest.mark.parametrize(
    ("tag", "current", "expected"),
    [
        ("v1.0.1", "1.0.0", True),
        ("1.1.0", "1.0.9", True),
        ("v2.0.0", "1.9.9", True),
        # Sayısal karşılaştırma: 1.2.10 > 1.2.9 (metinsel değil).
        ("1.2.10", "1.2.9", True),
        ("v1.0.0", "1.0.0", False),
        ("0.9.9", "1.0.0", False),
        ("1.0", "1.0.0", False),
        ("", "1.0.0", False),
        ("nightly", "1.0.0", False),
    ],
)
def test_is_newer(tag, current, expected):
    assert is_newer(tag, current) is expected


def _body(tag, url="https://github.com/o/r/releases/tag/x"):
    return json.dumps({"tag_name": tag, "html_url": url}).encode("utf-8")


def test_interpret_update_available():
    result = interpret_response(200, _body("v1.5.0"), current="1.0.0")

    assert result.status == STATUS_UPDATE_AVAILABLE
    assert result.version == "1.5.0"
    assert result.url == "https://github.com/o/r/releases/tag/x"


def test_interpret_up_to_date():
    result = interpret_response(200, _body("v1.0.0"), current="1.0.0")

    assert result.status == STATUS_UP_TO_DATE
    assert result.version == "1.0.0"


def test_interpret_falls_back_to_releases_page_without_html_url():
    body = json.dumps({"tag_name": "v3.0.0"}).encode("utf-8")

    result = interpret_response(200, body, current="1.0.0")

    assert result.status == STATUS_UPDATE_AVAILABLE
    assert result.url.startswith("https://github.com/")


def test_interpret_no_release_on_404():
    assert interpret_response(404, b"{}").status == STATUS_NO_RELEASE


@pytest.mark.parametrize("status_code", [None, 403, 500, 503])
def test_interpret_http_errors(status_code):
    assert interpret_response(status_code, b"{}").status == STATUS_ERROR


@pytest.mark.parametrize(
    "body",
    [b"", b"not json", b"[]", b"{}", json.dumps({"tag_name": None}).encode()],
)
def test_interpret_malformed_body(body):
    result = interpret_response(200, body, current="1.0.0")

    # Bozuk yanıt yeni sürüm gibi yorumlanmaz; hata ya da güncel sayılır.
    assert result.status in (STATUS_ERROR, STATUS_UP_TO_DATE)
    assert result.status != STATUS_UPDATE_AVAILABLE
