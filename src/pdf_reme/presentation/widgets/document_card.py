import qtawesome as qta

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.presentation.document_format import type_icon
from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager
from pdf_reme.presentation.thumbnails import image_thumbnail
from pdf_reme.presentation.widgets.selection_check import SelectionCheck


CARD_SHADOW_BLUR_REST = 20
CARD_SHADOW_BLUR_HOVER = 34
CARD_SHADOW_Y_REST = 4
CARD_SHADOW_Y_HOVER = 10

_FAVORITE_COLOR = "#F5A623"

_ICON_BOX_SIZE = 48
_THUMBNAIL_BOX_SIZE = 64
_ICON_BOX_RADIUS = 12


class DocumentCard(QFrame):
    open_requested = Signal(str)
    selection_toggled = Signal(str, bool)
    favorite_toggled = Signal(str)
    trash_requested = Signal(str)
    restore_requested = Signal(str)
    delete_forever_requested = Signal(str)

    def __init__(
        self,
        document: Document,
        meta_text: str,
        variant: str = "library",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._document_id = document.id
        self._display_name = document.display_name
        self._meta_text = meta_text
        self._is_favorite = document.is_favorite
        self._variant = variant
        self._selection_mode = False

        self._icon_name, self._icon_accent = type_icon(
            document.document_type
        )

        self._image_path = (
            document.stored_path
            if document.document_type == "image"
            else None
        )

        self._language_manager = get_language_manager()
        self._theme_manager = get_theme_manager()

        self.setObjectName("documentCard")

        self._setup_ui()
        self.retranslate_ui()
        self.apply_theme()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)

        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        self._selection_check = SelectionCheck()

        self._selection_check.setVisible(False)

        self._selection_check.clicked.connect(
            lambda: self._set_selected_from_user(
                self._selection_check.isChecked()
            )
        )

        layout.addWidget(self._selection_check)

        self._thumbnail = None

        if self._image_path:
            self._thumbnail = image_thumbnail(
                self._image_path,
                _THUMBNAIL_BOX_SIZE,
                _ICON_BOX_RADIUS,
                self.devicePixelRatioF(),
            )

        box_size = (
            _THUMBNAIL_BOX_SIZE
            if self._thumbnail is not None
            else _ICON_BOX_SIZE
        )

        icon_container = QFrame()

        icon_container.setObjectName("dashboardActionIconContainer")

        icon_container.setProperty("accentColor", self._icon_accent)

        icon_container.setFixedSize(box_size, box_size)

        icon_layout = QVBoxLayout(icon_container)

        icon_layout.setContentsMargins(0, 0, 0, 0)

        self._icon_label = QLabel()

        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_layout.addWidget(self._icon_label)

        text_container = QWidget()

        text_layout = QVBoxLayout(text_container)

        text_layout.setContentsMargins(0, 0, 0, 0)

        text_layout.setSpacing(3)

        self._title_label = QLabel(self._display_name)

        self._title_label.setObjectName("documentCardTitle")

        self._title_label.setWordWrap(True)

        self._meta_label = QLabel(self._meta_text)

        self._meta_label.setObjectName("documentCardMeta")

        text_layout.addWidget(self._title_label)

        text_layout.addWidget(self._meta_label)

        button_row = QHBoxLayout()

        button_row.setSpacing(6)

        if self._variant == "trash":
            self._restore_button = QPushButton()

            self._restore_button.setObjectName("recentDocumentOpenButton")

            self._restore_button.setCursor(Qt.CursorShape.PointingHandCursor)

            self._restore_button.clicked.connect(
                lambda: self.restore_requested.emit(self._document_id)
            )

            self._delete_forever_button = QPushButton()

            self._delete_forever_button.setObjectName("documentCardIconButton")

            self._delete_forever_button.setProperty("danger", True)

            self._delete_forever_button.setFixedSize(34, 34)

            self._delete_forever_button.setCursor(Qt.CursorShape.PointingHandCursor)

            self._delete_forever_button.clicked.connect(
                lambda: self.delete_forever_requested.emit(self._document_id)
            )

            button_row.addWidget(self._restore_button)
            button_row.addWidget(self._delete_forever_button)
        else:
            self._favorite_button = QPushButton()

            self._favorite_button.setObjectName("documentCardIconButton")

            self._favorite_button.setFixedSize(34, 34)

            self._favorite_button.setCursor(Qt.CursorShape.PointingHandCursor)

            self._favorite_button.clicked.connect(
                lambda: self.favorite_toggled.emit(self._document_id)
            )

            self._trash_button = QPushButton()

            self._trash_button.setObjectName("documentCardIconButton")

            self._trash_button.setFixedSize(34, 34)

            self._trash_button.setCursor(Qt.CursorShape.PointingHandCursor)

            self._trash_button.clicked.connect(
                lambda: self.trash_requested.emit(self._document_id)
            )

            button_row.addWidget(self._favorite_button)
            button_row.addWidget(self._trash_button)

        self._actions_widget = QWidget()

        button_row.setContentsMargins(0, 0, 0, 0)

        self._actions_widget.setLayout(button_row)

        layout.addWidget(icon_container)
        layout.addWidget(text_container, 1)
        layout.addWidget(self._actions_widget)

        self._update_cursor()

    def retranslate_ui(self) -> None:
        if self._variant == "trash":
            self._restore_button.setText(
                self._language_manager.tr("document.action.restore")
            )

            self._delete_forever_button.setToolTip(
                self._language_manager.tr("document.action.delete_forever")
            )
        else:
            self._favorite_button.setToolTip(
                self._language_manager.tr(
                    "document.action.unfavorite"
                    if self._is_favorite
                    else "document.action.favorite"
                )
            )

            self._trash_button.setToolTip(
                self._language_manager.tr("document.action.trash")
            )

    def apply_theme(self) -> None:
        self._selection_check.apply_theme()

        if self._thumbnail is not None:
            self._icon_label.setPixmap(self._thumbnail)
        else:
            self._icon_label.setPixmap(
                qta.icon(
                    self._icon_name,
                    color=self._theme_manager.accent_hex(self._icon_accent),
                ).pixmap(24, 24)
            )

        if self._variant == "trash":
            self._delete_forever_button.setIcon(
                qta.icon("fa5s.trash", color="#E5484D")
            )

            self._restore_button.setIcon(
                qta.icon(
                    "fa5s.undo",
                    color=self._theme_manager.accent_hex("blue"),
                )
            )
        else:
            self._favorite_button.setIcon(
                qta.icon(
                    "fa5s.star" if self._is_favorite else "fa5.star",
                    color=(
                        _FAVORITE_COLOR
                        if self._is_favorite
                        else self._theme_manager.icon_color()
                    ),
                )
            )

            self._trash_button.setIcon(
                qta.icon(
                    "fa5s.trash-alt",
                    color=self._theme_manager.icon_color(),
                )
            )

        self._apply_shadow(hovered=False)

    @property
    def document_id(self) -> str:
        return self._document_id

    @property
    def is_selected(self) -> bool:
        return self._selection_check.isChecked()

    def set_selection_mode(self, enabled: bool) -> None:
        self._selection_mode = enabled

        self._selection_check.setVisible(enabled)
        self._actions_widget.setVisible(not enabled)

        if not enabled:
            self.set_selected(False)

        self._update_cursor()

    def set_selected(self, selected: bool) -> None:
        self._selection_check.setChecked(selected)

        self.setProperty("selected", selected)

        self.style().unpolish(self)
        self.style().polish(self)

    def _set_selected_from_user(self, selected: bool) -> None:
        self.set_selected(selected)

        self.selection_toggled.emit(self._document_id, selected)

    def _is_clickable(self) -> bool:
        return self._selection_mode or self._variant != "trash"

    def _update_cursor(self) -> None:
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if self._is_clickable()
            else Qt.CursorShape.ArrowCursor
        )

    def mouseReleaseEvent(self, event) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            if self._selection_mode:
                self._set_selected_from_user(not self.is_selected)
            elif self._variant != "trash":
                self.open_requested.emit(self._document_id)

        super().mouseReleaseEvent(event)

    def _apply_shadow(self, *, hovered: bool) -> None:
        shadow = QGraphicsDropShadowEffect(self)

        shadow.setBlurRadius(
            CARD_SHADOW_BLUR_HOVER if hovered else CARD_SHADOW_BLUR_REST
        )

        shadow.setXOffset(0)

        shadow.setYOffset(CARD_SHADOW_Y_HOVER if hovered else CARD_SHADOW_Y_REST)

        shadow.setColor(QColor(self._theme_manager.shadow_color()))

        self.setGraphicsEffect(shadow)

    def enterEvent(self, event) -> None:
        self._apply_shadow(hovered=True)

        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._apply_shadow(hovered=False)

        super().leaveEvent(event)
