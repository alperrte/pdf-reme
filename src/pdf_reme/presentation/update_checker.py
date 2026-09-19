import json
import re
from dataclasses import dataclass

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkReply,
    QNetworkRequest,
)

from pdf_reme.presentation.app_info import (
    APP_NAME,
    APP_VERSION,
    GITHUB_LATEST_API_URL,
    GITHUB_RELEASES_URL,
)

_TIMEOUT_MS = 8000

STATUS_UP_TO_DATE = "up_to_date"
STATUS_UPDATE_AVAILABLE = "update_available"
STATUS_NO_RELEASE = "no_release"
STATUS_ERROR = "error"


@dataclass(frozen=True)
class UpdateResult:
    status: str
    version: str = ""
    url: str = ""


def parse_version(text: str) -> tuple[int, ...]:
    """'v1.2.10' -> (1, 2, 10); '1.4.0-beta' -> (1, 4, 0)."""
    numbers: list[int] = []

    # Ön sürüm/derleme eki ('-beta.1', '+abc') sürüm sayılarına katılmaz.
    core = re.split(r"[-+]", text.strip().lstrip("vV"), maxsplit=1)[0]

    for part in core.split("."):
        match = re.match(r"\d+", part)

        if match is None:
            break

        numbers.append(int(match.group()))

    return tuple(numbers)


def is_newer(tag: str, current: str = APP_VERSION) -> bool:
    latest = parse_version(tag)

    if not latest:
        return False

    return latest > parse_version(current)


def interpret_response(
    status_code: int | None,
    body: bytes,
    current: str = APP_VERSION,
) -> UpdateResult:
    """GitHub 'releases/latest' yanıtını sonuca çevirir (ağ gerektirmez)."""
    if status_code == 404:
        return UpdateResult(STATUS_NO_RELEASE)

    if status_code != 200:
        return UpdateResult(STATUS_ERROR)

    try:
        payload = json.loads(body.decode("utf-8"))
        tag = str(payload["tag_name"])

    except (ValueError, KeyError, TypeError):
        return UpdateResult(STATUS_ERROR)

    url = payload.get("html_url") or GITHUB_RELEASES_URL

    if is_newer(tag, current):
        return UpdateResult(
            STATUS_UPDATE_AVAILABLE,
            version=tag.lstrip("vV"),
            url=str(url),
        )

    return UpdateResult(STATUS_UP_TO_DATE, version=tag.lstrip("vV"))


class UpdateChecker(QObject):
    """GitHub'daki son yayını sorgular.

    Yalnızca `check()` çağrıldığında (kullanıcı düğmesi ya da 'açılışta
    denetle' ayarı) tek bir GET isteği atılır; kullanıcıya dair veri
    gönderilmez.
    """

    finished = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        self._manager = QNetworkAccessManager(self)
        self._reply: QNetworkReply | None = None

    @property
    def is_running(self) -> bool:
        return self._reply is not None

    def check(self) -> None:
        if self._reply is not None:
            return

        request = QNetworkRequest(QUrl(GITHUB_LATEST_API_URL))
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setRawHeader(
            b"User-Agent", f"{APP_NAME}/{APP_VERSION}".encode()
        )
        request.setTransferTimeout(_TIMEOUT_MS)

        self._reply = self._manager.get(request)
        self._reply.finished.connect(self._on_finished)

    def _on_finished(self) -> None:
        reply, self._reply = self._reply, None

        if reply is None:
            return

        status_code = reply.attribute(
            QNetworkRequest.Attribute.HttpStatusCodeAttribute
        )

        if (
            reply.error() != QNetworkReply.NetworkError.NoError
            and status_code is None
        ):
            result = UpdateResult(STATUS_ERROR)
        else:
            result = interpret_response(
                status_code, bytes(reply.readAll())
            )

        reply.deleteLater()

        self.finished.emit(result)
