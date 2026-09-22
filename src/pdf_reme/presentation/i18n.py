import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal


TRANSLATIONS_DIR = (
    Path(__file__).resolve().parents[1]
    / "resources"
    / "translations"
)

SUPPORTED_LANGUAGES = (
    "tr",
    "en",
)

DEFAULT_LANGUAGE = "tr"


class LanguageManager(QObject):
    language_changed = Signal(str)

    def __init__(
        self,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self._translations: dict[
            str,
            dict[str, str],
        ] = {}

        for language in SUPPORTED_LANGUAGES:
            self._translations[language] = self._load_language_file(
                language
            )

        # Başlangıç değeri kalıcı "başlangıç varsayılanı"ndan okunur (bkz.
        # app_settings.startup_language); döngüsel içe aktarmadan kaçınmak
        # için burada, kullanım anında (fonksiyon içinde) içe aktarılır --
        # app_settings.py da geçerlilik denetimi için bu modülü içe aktarır.
        from pdf_reme.presentation import app_settings

        self._current_language = app_settings.startup_language()

    @staticmethod
    def _load_language_file(
        language: str,
    ) -> dict[str, str]:
        file_path = (
            TRANSLATIONS_DIR
            / f"{language}.json"
        )

        if not file_path.exists():
            print(
                f"UYARI: Çeviri dosyası bulunamadı: {file_path}"
            )

            return {}

        return json.loads(
            file_path.read_text(
                encoding="utf-8"
            )
        )

    @property
    def current_language(self) -> str:
        return self._current_language

    def set_language(
        self,
        language: str,
    ) -> None:
        """Yalnızca bu çalışma zamanı örneğini değiştirir (kenar çubuğu
        anlık geçişi); kalıcı başlangıç varsayılanını ETKİLEMEZ -- onu
        değiştirmek için `app_settings.set_startup_language` kullanılır
        (bkz. `settings_page.py::_on_language_chosen`)."""

        if language not in SUPPORTED_LANGUAGES:
            return

        if language == self._current_language:
            return

        self._current_language = language

        self.language_changed.emit(
            language
        )

    def toggle_language(self) -> None:
        other = (
            "en"
            if self._current_language == "tr"
            else "tr"
        )

        self.set_language(
            other
        )

    def tr(
        self,
        key: str,
    ) -> str:
        table = self._translations.get(
            self._current_language,
            {},
        )

        value = table.get(
            key
        )

        if value is not None:
            return value

        # Geliştirme sırasında eksik anahtarları fark etmek için
        # sessizce boş dönmek yerine anahtarı geri veriyoruz.
        return key


_language_manager: LanguageManager | None = None


def get_language_manager() -> LanguageManager:
    global _language_manager

    if _language_manager is None:
        _language_manager = LanguageManager()

    return _language_manager
