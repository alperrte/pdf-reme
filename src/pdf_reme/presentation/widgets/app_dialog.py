from dataclasses import dataclass

import qtawesome as qta

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager


_SHADOW_MARGIN = 26
_DIALOG_WIDTH = 440
_ITEMS_MAX_HEIGHT = 230

# variant -> (ikon, tema aksan rengi)
_VARIANT_ICONS = {
    "primary": ("fa5s.question", "blue"),
    "danger": ("fa5s.trash-alt", "red"),
    "info": ("fa5s.info", "blue"),
    "success": ("fa5s.check", "green"),
}


@dataclass(frozen=True)
class DialogItem:
    name: str
    detail: str = ""
    icon_name: str = "fa5s.file"
    accent: str = "blue"


class AppDialog(QDialog):
    """PDF-REME'ye özel onay / bilgi penceresi (QMessageBox yerine)."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        title: str,
        body: str,
        confirm_text: str,
        cancel_text: str | None = None,
        variant: str = "primary",
        icon_name: str | None = None,
        items: list[DialogItem] | None = None,
    ) -> None:
        super().__init__(parent)

        self._theme_manager = get_theme_manager()

        self._variant = variant if variant in _VARIANT_ICONS else "primary"
        self._icon_name = icon_name or _VARIANT_ICONS[self._variant][0]

        self.setObjectName("appDialog")
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(_DIALOG_WIDTH + _SHADOW_MARGIN * 2)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            _SHADOW_MARGIN,
            _SHADOW_MARGIN,
            _SHADOW_MARGIN,
            _SHADOW_MARGIN,
        )

        card = QFrame()
        card.setObjectName("appDialogCard")

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(46)
        shadow.setXOffset(0)
        shadow.setYOffset(14)
        shadow.setColor(QColor(0, 0, 0, 90))
        card.setGraphicsEffect(shadow)

        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(0)

        self._icon_bubble = QFrame()
        self._icon_bubble.setObjectName("appDialogIconBubble")
        self._icon_bubble.setProperty(
            "accentColor",
            _VARIANT_ICONS[self._variant][1],
        )
        self._icon_bubble.setFixedSize(52, 52)

        bubble_layout = QVBoxLayout(self._icon_bubble)
        bubble_layout.setContentsMargins(0, 0, 0, 0)

        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bubble_layout.addWidget(self._icon_label)

        layout.addWidget(
            self._icon_bubble,
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )
        layout.addSpacing(16)

        title_label = QLabel(title)
        title_label.setObjectName("appDialogTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)

        body_label = QLabel(body)
        body_label.setObjectName("appDialogBody")
        body_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addSpacing(8)
        layout.addWidget(body_label)

        if items:
            layout.addSpacing(16)
            layout.addWidget(self._build_items(items))

        layout.addSpacing(24)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        if cancel_text:
            cancel_button = QPushButton(cancel_text)
            cancel_button.setObjectName("appDialogCancelButton")
            cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
            cancel_button.clicked.connect(self.reject)

            button_row.addWidget(cancel_button, 1)

        confirm_button = QPushButton(confirm_text)
        confirm_button.setObjectName("appDialogConfirmButton")
        confirm_button.setProperty("variant", self._variant)
        confirm_button.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_button.setDefault(True)
        confirm_button.clicked.connect(self.accept)

        button_row.addWidget(confirm_button, 1)

        layout.addLayout(button_row)

        self._apply_theme()

    def _build_items(
        self,
        items: list[DialogItem],
    ) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("appDialogItemsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        container.setObjectName("appDialogItemsContainer")

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 4, 0)
        container_layout.setSpacing(6)

        for item in items:
            container_layout.addWidget(self._build_item_row(item))

        container_layout.addStretch(1)

        scroll.setWidget(container)

        # Az öğede liste içeriği kadar, çok öğede sabit yükseklikte kaydırılır.
        row_height = 52 + 6
        scroll.setFixedHeight(
            min(len(items) * row_height + 2, _ITEMS_MAX_HEIGHT)
        )

        return scroll

    def _build_item_row(
        self,
        item: DialogItem,
    ) -> QWidget:
        row = QFrame()
        row.setObjectName("appDialogItemRow")
        row.setFixedHeight(52)

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(12, 0, 12, 0)
        row_layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setPixmap(
            qta.icon(
                item.icon_name,
                color=self._theme_manager.accent_hex(item.accent),
            ).pixmap(20, 20)
        )

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(1)

        name_label = QLabel(item.name)
        name_label.setObjectName("appDialogItemName")

        text_column.addStretch(1)
        text_column.addWidget(name_label)

        if item.detail:
            detail_label = QLabel(item.detail)
            detail_label.setObjectName("appDialogItemDetail")
            text_column.addWidget(detail_label)

        text_column.addStretch(1)

        row_layout.addWidget(icon_label)
        row_layout.addLayout(text_column, 1)

        return row

    def _apply_theme(self) -> None:
        accent = _VARIANT_ICONS[self._variant][1]

        self._icon_label.setPixmap(
            qta.icon(
                self._icon_name,
                color=self._theme_manager.accent_hex(accent),
            ).pixmap(22, 22)
        )

    def showEvent(self, event) -> None:
        super().showEvent(event)

        # Ana pencerenin ortasına hizala.
        anchor = self.parentWidget()

        if anchor is not None:
            anchor = anchor.window()
            center = anchor.frameGeometry().center()

            geometry = self.frameGeometry()
            geometry.moveCenter(center)

            self.move(geometry.topLeft())

    @staticmethod
    def ask(
        parent: QWidget | None,
        *,
        title: str,
        body: str,
        confirm_text: str,
        cancel_text: str | None = None,
        variant: str = "primary",
        icon_name: str | None = None,
        items: list[DialogItem] | None = None,
    ) -> bool:
        language_manager = get_language_manager()

        dialog = AppDialog(
            parent,
            title=title,
            body=body,
            confirm_text=confirm_text,
            cancel_text=cancel_text or language_manager.tr("dialog.cancel"),
            variant=variant,
            icon_name=icon_name,
            items=items,
        )

        return dialog.exec() == QDialog.DialogCode.Accepted

    @staticmethod
    def inform(
        parent: QWidget | None,
        *,
        title: str,
        body: str,
        variant: str = "info",
        icon_name: str | None = None,
        items: list[DialogItem] | None = None,
    ) -> None:
        language_manager = get_language_manager()

        dialog = AppDialog(
            parent,
            title=title,
            body=body,
            confirm_text=language_manager.tr("dialog.ok"),
            cancel_text=None,
            variant=variant,
            icon_name=icon_name,
            items=items,
        )

        dialog.exec()
