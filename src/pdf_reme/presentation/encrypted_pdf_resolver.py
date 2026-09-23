"""Şifreli PDF'leri araçlara vermeden önce parola isteyip düz kopyaya çeviren yardımcı."""

from pathlib import Path

from PySide6.QtWidgets import QWidget

from pdf_reme.presentation import backend_gateway
from pdf_reme.presentation.widgets.encrypted_pdf_password_dialog import (
    EncryptedPdfPasswordDialog,
)


class EncryptedPdfResolver:
    """Şifreli dosyaları parola isteyip düz geçici kopyaya çözümler; sonuçları önbelleğe alır."""

    def __init__(self, parent: QWidget) -> None:
        self._parent = parent
        self._cache: dict[str, str] = {}
        self._produced: list[Path] = []

    def resolve(self, path: str) -> str | None:
        cached = self._cache.get(path)
        if cached is not None:
            return cached

        info = backend_gateway.inspect_pdf(path)
        if not info.encrypted:
            return path

        password = EncryptedPdfPasswordDialog.prompt(
            self._parent, path=path, file_name=Path(path).name
        )
        if password is None:
            return None

        resolved = backend_gateway.resolve_encrypted_copy(path, password)
        resolved_str = str(resolved)
        self._cache[path] = resolved_str
        self._produced.append(resolved)

        return resolved_str

    def clear(self) -> None:
        for produced_path in self._produced:
            backend_gateway.discard_encrypted_copy(produced_path)

        self._produced.clear()
        self._cache.clear()
