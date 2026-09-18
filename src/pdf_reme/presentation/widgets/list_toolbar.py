import time

import qtawesome as qta

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation.document_format import TYPE_ICON_MAP
from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager


# document_type -> (çeviri anahtarı, qtawesome ikonu, tema aksan rengi)
# İkon/renk eşlemesi DocumentCard ile ortak (document_format.TYPE_ICON_MAP).
_TYPE_FILTER_DEFS = [
    (
        document_type,
        f"filter.type.{document_type}",
        TYPE_ICON_MAP[document_type][0],
        TYPE_ICON_MAP[document_type][1],
    )
    for document_type in ("pdf", "word", "powerpoint", "excel", "image")
]

_POPUP_SHADOW_MARGIN = 14


class SearchInput(QLineEdit):
    def __init__(
        self,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._language_manager = get_language_manager()
        self._theme_manager = get_theme_manager()

        self.setObjectName("pageSearchInput")
        self.setClearButtonEnabled(True)

        # Dosya sürükleyip bırakma sayfa düzeyinde işlenir; QLineEdit
        # varsayılan olarak drop kabul edip olayı yutmasın.
        self.setAcceptDrops(False)

        self._search_action = self.addAction(
            qta.icon("fa5s.search", color=self._theme_manager.icon_color()),
            QLineEdit.ActionPosition.LeadingPosition,
        )

        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setPlaceholderText(
            self._language_manager.tr("common.search_placeholder")
        )

    def apply_theme(self) -> None:
        self._search_action.setIcon(
            qta.icon("fa5s.search", color=self._theme_manager.icon_color())
        )


class _DropdownPopup(QFrame):
    item_chosen = Signal(int)
    closed = Signal()

    def __init__(
        self,
        parent: QWidget,
    ) -> None:
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            _POPUP_SHADOW_MARGIN,
            _POPUP_SHADOW_MARGIN - 6,
            _POPUP_SHADOW_MARGIN,
            _POPUP_SHADOW_MARGIN + 2,
        )

        self._panel = QFrame()
        self._panel.setObjectName("dropdownPanel")

        shadow = QGraphicsDropShadowEffect(self._panel)
        shadow.setBlurRadius(28)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 70))
        self._panel.setGraphicsEffect(shadow)

        outer.addWidget(self._panel)

        self._panel_layout = QVBoxLayout(self._panel)
        self._panel_layout.setContentsMargins(6, 6, 6, 6)
        self._panel_layout.setSpacing(2)

        self._buttons: list[QPushButton] = []

    def set_items(
        self,
        labels: list[str],
        current_index: int,
        check_icon,
        blank_icon,
    ) -> None:
        while self._buttons:
            button = self._buttons.pop()
            self._panel_layout.removeWidget(button)
            button.deleteLater()

        for index, label in enumerate(labels):
            button = QPushButton(label)
            button.setObjectName("dropdownItem")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setProperty("selected", index == current_index)
            button.setIcon(check_icon if index == current_index else blank_icon)
            button.clicked.connect(
                lambda _checked=False, i=index: self._choose(i)
            )

            self._panel_layout.addWidget(button)
            self._buttons.append(button)

    def _choose(self, index: int) -> None:
        self.hide()
        self.item_chosen.emit(index)

    def hideEvent(self, event) -> None:
        self.closed.emit()
        super().hideEvent(event)


class SortOrderCombo(QPushButton):
    """Modern açılır menülü sıralama seçici (En yeni önce / En eski önce)."""

    sort_changed = Signal()

    _KEYS = ("desc", "asc")
    _LABEL_KEYS = ("sort.newest_first", "sort.oldest_first")

    def __init__(
        self,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._language_manager = get_language_manager()
        self._theme_manager = get_theme_manager()

        self._index = 0
        self._popup_closed_at = 0.0

        self.setObjectName("pageSortCombo")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(38)
        self.setMinimumWidth(170)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        self._icon_label = QLabel()
        self._text_label = QLabel()
        self._text_label.setObjectName("pageSortComboText")
        self._chevron_label = QLabel()

        for label in (self._icon_label, self._text_label, self._chevron_label):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        layout.addWidget(self._icon_label)
        layout.addWidget(self._text_label, 1)
        layout.addWidget(self._chevron_label)

        self._popup = _DropdownPopup(self)
        self._popup.item_chosen.connect(self._on_item_chosen)
        self._popup.closed.connect(self._on_popup_closed)

        self.clicked.connect(self._toggle_popup)

        self.retranslate_ui()
        self.apply_theme()

    @property
    def is_ascending(self) -> bool:
        return self._KEYS[self._index] == "asc"

    def retranslate_ui(self) -> None:
        self._text_label.setText(
            self._language_manager.tr(self._LABEL_KEYS[self._index])
        )

    def apply_theme(self) -> None:
        muted = self._theme_manager.icon_color()

        self._icon_label.setPixmap(
            qta.icon(
                "fa5s.sort-amount-up"
                if self.is_ascending
                else "fa5s.sort-amount-down",
                color=muted,
            ).pixmap(14, 14)
        )

        self._chevron_label.setPixmap(
            qta.icon("fa5s.chevron-down", color=muted).pixmap(10, 10)
        )

    def _toggle_popup(self) -> None:
        # Popup dışına tıklamak popup'ı kapatır; aynı tıklama butona da
        # ulaştığı için hemen yeniden açılmasını engelle.
        if time.monotonic() - self._popup_closed_at < 0.25:
            return

        labels = [
            self._language_manager.tr(key) for key in self._LABEL_KEYS
        ]

        self._popup.set_items(
            labels,
            self._index,
            qta.icon("fa5s.check", color=self._theme_manager.accent_hex("blue")),
            qta.icon("fa5s.check", color="#00000000"),
        )

        self._popup.setFixedWidth(
            max(self.width(), 200) + _POPUP_SHADOW_MARGIN * 2
        )
        self._popup.adjustSize()

        origin = self.mapToGlobal(QPoint(0, self.height()))

        self._popup.move(
            origin.x() + self.width() - self._popup.width() + _POPUP_SHADOW_MARGIN,
            origin.y() - 6,
        )

        self._popup.show()

    def hideEvent(self, event) -> None:
        self._popup.hide()
        super().hideEvent(event)

    def _on_popup_closed(self) -> None:
        self._popup_closed_at = time.monotonic()

    def _on_item_chosen(self, index: int) -> None:
        if index == self._index:
            return

        self._index = index

        self.retranslate_ui()
        self.apply_theme()

        self.sort_changed.emit()


class TypeFilterBar(QWidget):
    filter_changed = Signal()

    def __init__(
        self,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._language_manager = get_language_manager()
        self._theme_manager = get_theme_manager()

        self._buttons: dict[str | None, QPushButton] = {}
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._add_chip(layout, None, "filter.type.all", "fa5s.th-large", None)

        for document_type, label_key, icon_name, accent in _TYPE_FILTER_DEFS:
            self._add_chip(layout, document_type, label_key, icon_name, accent)

        layout.addStretch(1)

        self.retranslate_ui()
        self.apply_theme()

    def _add_chip(
        self,
        layout: QHBoxLayout,
        document_type: str | None,
        label_key: str,
        icon_name: str,
        accent: str | None,
    ) -> None:
        button = QPushButton()

        button.setObjectName("typeFilterChip")
        button.setProperty("accentColor", accent or "neutral")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        button.clicked.connect(lambda _checked=False: self.filter_changed.emit())

        self._button_group.addButton(button)
        self._buttons[document_type] = button

        layout.addWidget(button)

        if document_type is None:
            button.setChecked(True)

    def retranslate_ui(self) -> None:
        self._buttons[None].setText(self._language_manager.tr("filter.type.all"))

        for document_type, label_key, _icon_name, _accent in _TYPE_FILTER_DEFS:
            self._buttons[document_type].setText(
                self._language_manager.tr(label_key)
            )

    def apply_theme(self) -> None:
        self._buttons[None].setIcon(
            qta.icon("fa5s.th-large", color=self._theme_manager.icon_color())
        )

        for document_type, _label_key, icon_name, accent in _TYPE_FILTER_DEFS:
            self._buttons[document_type].setIcon(
                qta.icon(icon_name, color=self._theme_manager.accent_hex(accent))
            )

    @property
    def selected_type(self) -> str | None:
        for document_type, button in self._buttons.items():
            if button.isChecked():
                return document_type

        return None
