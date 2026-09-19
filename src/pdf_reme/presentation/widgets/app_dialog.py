from dataclasses import dataclass

import qtawesome as qta

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPainter
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

# Ana pencerenin üzerini örten yarı saydam arka plan; kartın dışına
# tıklamak pencereyi kapatır. (Tam saydam pikseller Windows'ta tıklamayı
# alta geçirdiği için alfa sıfır olamaz.)
_BACKDROP_ALPHA = 80

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
        extra_actions: list[tuple[str, str]] | None = None,
        confirm_action: str | None = None,
    ) -> None:
        super().__init__(parent)

        self._theme_manager = get_theme_manager()
        self._chosen_action: str | None = None
        self._confirm_action = confirm_action
        self._covers_parent = False

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

        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            _SHADOW_MARGIN,
            _SHADOW_MARGIN,
            _SHADOW_MARGIN,
            _SHADOW_MARGIN,
        )

        card = QFrame()
        card.setObjectName("appDialogCard")
        card.setFixedWidth(_DIALOG_WIDTH)
        self._card = card

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(46)
        shadow.setXOffset(0)
        shadow.setYOffset(14)
        shadow.setColor(QColor(0, 0, 0, 90))
        card.setGraphicsEffect(shadow)

        outer.addWidget(card, 0, Qt.AlignmentFlag.AlignCenter)

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

        if extra_actions:
            # Ek eylemler üst satırda; onay düğmesi altta tam genişlikte.
            extra_row = QHBoxLayout()
            extra_row.setSpacing(10)

            for action_key, action_text in extra_actions:
                extra_button = QPushButton(action_text)
                extra_button.setObjectName("appDialogCancelButton")
                extra_button.setCursor(Qt.CursorShape.PointingHandCursor)
                extra_button.clicked.connect(
                    lambda _=False, key=action_key: self._choose(key)
                )

                extra_row.addWidget(extra_button, 1)

            layout.addLayout(extra_row)
            layout.addSpacing(10)

        confirm_button = QPushButton(confirm_text)
        confirm_button.setObjectName("appDialogConfirmButton")
        confirm_button.setProperty("variant", self._variant)
        confirm_button.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_button.setDefault(True)
        confirm_button.clicked.connect(
            lambda: self._choose(self._confirm_action)
        )

        button_row.addWidget(confirm_button, 1)

        layout.addLayout(button_row)

        self._apply_theme()
        self._cover_parent()

    def _choose(
        self,
        action_key: str | None,
    ) -> None:
        self._chosen_action = action_key
        self.accept()

    @property
    def chosen_action(self) -> str | None:
        return self._chosen_action

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

    def _cover_parent(self) -> None:
        """Ana pencerenin istemci alanını örter; kart ortada kalır."""
        anchor = self.parentWidget()

        if anchor is None:
            self._covers_parent = False
            return

        anchor = anchor.window()

        self._covers_parent = True
        self.setGeometry(
            anchor.mapToGlobal(QPoint(0, 0)).x(),
            anchor.mapToGlobal(QPoint(0, 0)).y(),
            anchor.width(),
            anchor.height(),
        )

    def showEvent(self, event) -> None:
        super().showEvent(event)

        # Pencere taşınmış/yeniden boyutlanmış olabilir.
        self._cover_parent()

    def paintEvent(self, event) -> None:
        if not self._covers_parent:
            return

        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, _BACKDROP_ALPHA))

    def mousePressEvent(self, event) -> None:
        # Kartın dışındaki boşluğa tıklamak Esc ile aynıdır (iptal / kapat).
        if (
            self._covers_parent
            and event.button() == Qt.MouseButton.LeftButton
            and not self._card.geometry().contains(event.position().toPoint())
        ):
            self.reject()
            return

        super().mousePressEvent(event)

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

    @staticmethod
    def choose(
        parent: QWidget | None,
        *,
        title: str,
        body: str,
        confirm_text: str,
        extra_actions: list[tuple[str, str]],
        variant: str = "success",
        icon_name: str | None = None,
        items: list[DialogItem] | None = None,
        confirm_action: str | None = None,
    ) -> str | None:
        """Ek eylem düğmeli sonuç penceresi.

        Seçilen ek eylemin anahtarını döndürür. Onay düğmesi `confirm_action`
        anahtarını (verilmediyse None), kapatma (Esc) her zaman None döndürür.
        """

        dialog = AppDialog(
            parent,
            title=title,
            body=body,
            confirm_text=confirm_text,
            cancel_text=None,
            variant=variant,
            icon_name=icon_name,
            items=items,
            extra_actions=extra_actions,
            confirm_action=confirm_action,
        )

        dialog.exec()

        return dialog.chosen_action
