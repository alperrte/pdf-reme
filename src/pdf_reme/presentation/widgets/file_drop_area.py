import qtawesome as qta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager


class DropOverlay(QFrame):
    """Sürükleme sırasında sayfanın üstünde görünen "bırakın" katmanı."""

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._language_manager = get_language_manager()
        self._theme_manager = get_theme_manager()

        self.setObjectName("dropOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title_label = QLabel()
        self._title_label.setObjectName("dropOverlayTitle")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._body_label = QLabel()
        self._body_label.setObjectName("dropOverlayBody")
        self._body_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._icon_label)
        layout.addWidget(self._title_label)
        layout.addWidget(self._body_label)

        self.retranslate_ui()
        self.apply_theme()

    def retranslate_ui(self) -> None:
        self._title_label.setText(
            self._language_manager.tr("library.drop_hint_title")
        )
        self._body_label.setText(
            self._language_manager.tr("library.drop_hint_body")
        )

    def apply_theme(self) -> None:
        self._icon_label.setPixmap(
            qta.icon(
                "fa5s.cloud-upload-alt",
                color=self._theme_manager.accent_hex("blue"),
            ).pixmap(44, 44)
        )
