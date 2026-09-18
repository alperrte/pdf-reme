from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


LIGHT_THEME = "light"
DARK_THEME = "dark"

DEFAULT_THEME = LIGHT_THEME

# Bu tokenlar app.qss içindeki [theme="dark"] bloğuyla elle senkron
# tutulur — QSS, Python sabitlerini okuyamadığı için tek kaynak
# burasıdır ama QSS'e otomatik yansımaz.
THEMES: dict[str, dict[str, str | dict[str, str]]] = {
    LIGHT_THEME: {
        "window_bg": "#F6F8FC",
        "content_bg": "#F7F9FC",
        "surface": "#FFFFFF",
        "sidebar_bg": "#FFFFFF",
        "text": "#172033",
        "muted_text": "#64748B",
        "border": "#E5EAF1",
        "icon_neutral": "#53637A",
        "accent_primary": "#2563EB",
        "accent_secondary": "#E53935",
        "shadow_color": "#17203314",
        "accents": {
            "red": "#E53935",
            "blue": "#2563EB",
            "purple": "#7C3AED",
            "green": "#10B981",
            "teal": "#0D9488",
            "sky": "#0EA5E9",
            "orange": "#E4572E",
        },
    },
    DARK_THEME: {
        "window_bg": "#0F1420",
        "content_bg": "#10141F",
        "surface": "#171D2C",
        "sidebar_bg": "#12141F",
        "text": "#E6EAF2",
        "muted_text": "#8A94A8",
        "border": "#232B3D",
        "icon_neutral": "#94A3B8",
        "accent_primary": "#3B82F6",
        "accent_secondary": "#F04438",
        "shadow_color": "#00000066",
        "accents": {
            "red": "#F04438",
            "blue": "#3B82F6",
            "purple": "#8B5CF6",
            "green": "#22C55E",
            "teal": "#2DD4BF",
            "sky": "#38BDF8",
            "orange": "#FB7A55",
        },
    },
}


class ThemeManager(QObject):
    theme_changed = Signal(str)

    def __init__(
        self,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self._settings = QSettings()

        self._current_theme = self._settings.value(
            "appearance/theme",
            DEFAULT_THEME,
        )

        if self._current_theme not in THEMES:
            self._current_theme = DEFAULT_THEME

    @property
    def current_theme(self) -> str:
        return self._current_theme

    @property
    def is_dark(self) -> bool:
        return self._current_theme == DARK_THEME

    def set_theme(
        self,
        theme: str,
    ) -> None:
        if theme not in THEMES:
            return

        if theme == self._current_theme:
            return

        self._current_theme = theme

        self._settings.setValue(
            "appearance/theme",
            theme,
        )

        self.theme_changed.emit(
            theme
        )

    def toggle_theme(self) -> None:
        other = (
            DARK_THEME
            if self._current_theme == LIGHT_THEME
            else LIGHT_THEME
        )

        self.set_theme(
            other
        )

    def tokens(self) -> dict[str, str | dict[str, str]]:
        return THEMES[self._current_theme]

    def icon_color(self) -> str:
        return str(
            self.tokens()["icon_neutral"]
        )

    def accent_hex(
        self,
        token: str,
    ) -> str:
        accents = self.tokens()["accents"]

        return accents.get(
            token,
            str(self.tokens()["accent_primary"]),
        )

    def shadow_color(self) -> str:
        return str(
            self.tokens()["shadow_color"]
        )

    def apply_palette(
        self,
        app: QApplication,
    ) -> None:
        """
        Windows'un sistem temasının Qt widget'larını istemeden
        koyulaştırmasını/aydınlatmasını önlemek için palette'i
        her zaman elle tanımlıyoruz.
        """

        tokens = self.tokens()

        palette = QPalette()

        palette.setColor(
            QPalette.ColorRole.Window,
            QColor(str(tokens["window_bg"])),
        )

        palette.setColor(
            QPalette.ColorRole.WindowText,
            QColor(str(tokens["text"])),
        )

        palette.setColor(
            QPalette.ColorRole.Base,
            QColor(str(tokens["surface"])),
        )

        palette.setColor(
            QPalette.ColorRole.AlternateBase,
            QColor(str(tokens["content_bg"])),
        )

        palette.setColor(
            QPalette.ColorRole.Text,
            QColor(str(tokens["text"])),
        )

        palette.setColor(
            QPalette.ColorRole.Button,
            QColor(str(tokens["surface"])),
        )

        palette.setColor(
            QPalette.ColorRole.ButtonText,
            QColor(str(tokens["text"])),
        )

        palette.setColor(
            QPalette.ColorRole.Highlight,
            QColor(str(tokens["accent_primary"])),
        )

        palette.setColor(
            QPalette.ColorRole.HighlightedText,
            QColor("#FFFFFF"),
        )

        app.setPalette(
            palette
        )


_theme_manager: ThemeManager | None = None


def get_theme_manager() -> ThemeManager:
    global _theme_manager

    if _theme_manager is None:
        _theme_manager = ThemeManager()

    return _theme_manager
