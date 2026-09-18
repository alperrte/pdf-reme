import qtawesome as qta

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation import backend_gateway
from pdf_reme.presentation.document_format import (
    format_document_meta,
    type_icon,
)
from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager
from pdf_reme.presentation.thumbnails import image_thumbnail


_RECENT_PANEL_LIMIT = 5

CARD_SHADOW_BLUR_REST = 26
CARD_SHADOW_BLUR_HOVER = 42
CARD_SHADOW_Y_REST = 8
CARD_SHADOW_Y_HOVER = 14

PANEL_SHADOW_BLUR = 24
PANEL_SHADOW_Y = 6


class DashboardActionCard(QFrame):
    clicked = Signal(str)

    def __init__(
        self,
        *,
        key: str,
        title_key: str,
        description_key: str,
        icon_name: str,
        accent: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._key = key

        self._title_key = title_key

        self._description_key = description_key

        self._icon_name = icon_name

        self._accent = accent

        self._language_manager = get_language_manager()

        self._theme_manager = get_theme_manager()

        self.setObjectName(
            "dashboardActionCard"
        )

        self.setProperty(
            "accentColor",
            accent,
        )

        self._setup_ui()

        self.retranslate_ui()

        self._apply_shadow(
            hovered=False
        )

    def _setup_ui(
        self,
    ) -> None:
        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            20,
            20,
            20,
            18,
        )

        layout.setSpacing(
            10
        )

        icon_container = QFrame()

        icon_container.setObjectName(
            "dashboardActionIconContainer"
        )

        icon_container.setProperty(
            "accentColor",
            self._accent,
        )

        icon_container.setFixedSize(
            48,
            48,
        )

        icon_layout = QVBoxLayout(
            icon_container
        )

        icon_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self._icon_label = QLabel()

        self._icon_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        icon_layout.addWidget(
            self._icon_label
        )

        self._title_label = QLabel()

        self._title_label.setObjectName(
            "dashboardActionTitle"
        )

        self._description_label = QLabel()

        self._description_label.setObjectName(
            "dashboardActionDescription"
        )

        self._description_label.setWordWrap(
            True
        )

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        layout.addWidget(
            icon_container
        )

        layout.addWidget(
            self._title_label
        )

        layout.addWidget(
            self._description_label
        )

        layout.addStretch()

    def retranslate_ui(
        self,
    ) -> None:
        self._title_label.setText(
            self._language_manager.tr(
                self._title_key
            )
        )

        self._description_label.setText(
            self._language_manager.tr(
                self._description_key
            )
        )

    def apply_theme(
        self,
    ) -> None:
        self._icon_label.setPixmap(
            qta.icon(
                self._icon_name,
                color=self._theme_manager.accent_hex(
                    self._accent
                ),
            ).pixmap(
                26,
                26,
            )
        )

        self._apply_shadow(
            hovered=False
        )

    def _apply_shadow(
        self,
        *,
        hovered: bool,
    ) -> None:
        shadow = QGraphicsDropShadowEffect(
            self
        )

        shadow.setBlurRadius(
            CARD_SHADOW_BLUR_HOVER
            if hovered
            else CARD_SHADOW_BLUR_REST
        )

        shadow.setXOffset(
            0
        )

        shadow.setYOffset(
            CARD_SHADOW_Y_HOVER
            if hovered
            else CARD_SHADOW_Y_REST
        )

        shadow.setColor(
            QColor(
                self._theme_manager.shadow_color()
            )
        )

        self.setGraphicsEffect(
            shadow
        )

    def mousePressEvent(
        self,
        event,
    ) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(
                self._key
            )

        super().mousePressEvent(
            event
        )

    def enterEvent(
        self,
        event,
    ) -> None:
        self._apply_shadow(
            hovered=True
        )

        super().enterEvent(
            event
        )

    def leaveEvent(
        self,
        event,
    ) -> None:
        self._apply_shadow(
            hovered=False
        )

        super().leaveEvent(
            event
        )


class RecentDocumentRow(QFrame):
    open_requested = Signal()

    def __init__(
        self,
        *,
        file_name: str,
        meta_text: str,
        icon_name: str = "fa5s.file-pdf",
        icon_accent: str = "red",
        image_path: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._language_manager = get_language_manager()

        self._theme_manager = get_theme_manager()

        self._thumbnail = (
            image_thumbnail(image_path, 40, 8, self.devicePixelRatioF())
            if image_path
            else None
        )

        self._icon_name = icon_name

        self._icon_accent = icon_accent

        self.setObjectName(
            "recentDocumentRow"
        )

        layout = QHBoxLayout(self)

        layout.setContentsMargins(
            16,
            12,
            16,
            12,
        )

        layout.setSpacing(
            12
        )

        self._icon_label = QLabel()

        text_container = QWidget()

        text_layout = QVBoxLayout(
            text_container
        )

        text_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        text_layout.setSpacing(
            2
        )

        file_name_label = QLabel(
            file_name
        )

        file_name_label.setObjectName(
            "recentDocumentName"
        )

        meta_label = QLabel(
            meta_text
        )

        meta_label.setObjectName(
            "recentDocumentMeta"
        )

        text_layout.addWidget(
            file_name_label
        )

        text_layout.addWidget(
            meta_label
        )

        layout.addWidget(
            self._icon_label
        )

        layout.addWidget(
            text_container,
            1,
        )

        # Satırın tamamı tıklanabilir; ayrı bir "Aç" butonu yok.
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.retranslate_ui()

        self.apply_theme()

    def retranslate_ui(
        self,
    ) -> None:
        pass

    def mouseReleaseEvent(
        self,
        event,
    ) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            self.open_requested.emit()

        super().mouseReleaseEvent(event)

    def apply_theme(
        self,
    ) -> None:
        if self._thumbnail is not None:
            self._icon_label.setPixmap(self._thumbnail)

            return

        self._icon_label.setPixmap(
            qta.icon(
                self._icon_name,
                color=self._theme_manager.accent_hex(
                    self._icon_accent
                ),
            ).pixmap(
                24,
                24,
            )
        )


class DashboardPage(QWidget):
    page_requested = Signal(str)
    document_open_requested = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._language_manager = get_language_manager()

        self._theme_manager = get_theme_manager()

        self._cards: list[DashboardActionCard] = []

        self._tool_buttons: list[
            tuple[QPushButton, str, str],
        ] = []

        self._recent_rows: list[RecentDocumentRow] = []

        self.setObjectName(
            "dashboardPage"
        )

        self._setup_ui()

        self.retranslate_ui()

        self.apply_theme()

    def _setup_ui(
        self,
    ) -> None:
        root_layout = QVBoxLayout(
            self
        )

        root_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        root_layout.setSpacing(
            0
        )

        scroll_area = QScrollArea()

        scroll_area.setObjectName(
            "dashboardScrollArea"
        )

        scroll_area.setWidgetResizable(
            True
        )

        scroll_area.setFrameShape(
            QFrame.Shape.NoFrame
        )

        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        content = QWidget()

        content.setObjectName(
            "dashboardContent"
        )

        content_layout = QVBoxLayout(
            content
        )

        content_layout.setContentsMargins(
            40,
            32,
            40,
            36,
        )

        content_layout.setSpacing(
            26
        )

        # =====================================================
        # HEADER
        # =====================================================

        header_layout = QHBoxLayout()

        header_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        header_text_layout = QVBoxLayout()

        header_text_layout.setSpacing(
            4
        )

        self._title_label = QLabel()

        self._title_label.setObjectName(
            "dashboardTitle"
        )

        self._subtitle_label = QLabel()

        self._subtitle_label.setObjectName(
            "dashboardSubtitle"
        )

        header_text_layout.addWidget(
            self._title_label
        )

        header_text_layout.addWidget(
            self._subtitle_label
        )

        header_layout.addLayout(
            header_text_layout
        )

        header_layout.addStretch()

        content_layout.addLayout(
            header_layout
        )

        # =====================================================
        # QUICK ACTIONS
        # =====================================================

        self._quick_title_label = QLabel()

        self._quick_title_label.setObjectName(
            "dashboardSectionTitle"
        )

        content_layout.addWidget(
            self._quick_title_label
        )

        cards_layout = QGridLayout()

        cards_layout.setHorizontalSpacing(
            16
        )

        cards_layout.setVerticalSpacing(
            16
        )

        cards = [
            {
                "key": "merge",
                "title_key": "dashboard.card.merge.title",
                "description_key": "dashboard.card.merge.description",
                "icon": "fa5s.object-group",
                "accent": "red",
            },
            {
                "key": "convert",
                "title_key": "dashboard.card.convert.title",
                "description_key": "dashboard.card.convert.description",
                "icon": "fa5s.exchange-alt",
                "accent": "blue",
            },
            {
                "key": "compress",
                "title_key": "dashboard.card.compress.title",
                "description_key": "dashboard.card.compress.description",
                "icon": "fa5s.compress-arrows-alt",
                "accent": "purple",
            },
            {
                "key": "split",
                "title_key": "dashboard.card.split.title",
                "description_key": "dashboard.card.split.description",
                "icon": "fa5s.cut",
                "accent": "green",
            },
            {
                "key": "security",
                "title_key": "dashboard.card.security.title",
                "description_key": "dashboard.card.security.description",
                "icon": "fa5s.lock",
                "accent": "teal",
            },
        ]

        for index, card_data in enumerate(
            cards
        ):
            card = DashboardActionCard(
                key=card_data["key"],
                title_key=card_data["title_key"],
                description_key=card_data["description_key"],
                icon_name=card_data["icon"],
                accent=card_data["accent"],
            )

            card.clicked.connect(
                self.page_requested.emit
            )

            self._cards.append(
                card
            )

            cards_layout.addWidget(
                card,
                0,
                index,
            )

            cards_layout.setColumnStretch(
                index,
                1,
            )

        content_layout.addLayout(
            cards_layout
        )

        # =====================================================
        # LOWER AREA
        # =====================================================

        lower_layout = QHBoxLayout()

        lower_layout.setSpacing(
            18
        )

        # -----------------------------------------------------
        # RECENT DOCUMENTS
        # -----------------------------------------------------

        self._recent_panel = QFrame()

        self._recent_panel.setObjectName(
            "dashboardPanel"
        )

        recent_layout = QVBoxLayout(
            self._recent_panel
        )

        self._recent_layout = recent_layout

        recent_layout.setContentsMargins(
            20,
            18,
            20,
            20,
        )

        recent_layout.setSpacing(
            12
        )

        recent_header = QHBoxLayout()

        self._recent_title_label = QLabel()

        self._recent_title_label.setObjectName(
            "dashboardPanelTitle"
        )

        self._show_all_button = QPushButton()

        self._show_all_button.setObjectName(
            "dashboardTextButton"
        )

        self._show_all_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self._show_all_button.clicked.connect(
            lambda:
                self.page_requested.emit(
                    "recent"
                )
        )

        recent_header.addWidget(
            self._recent_title_label
        )

        recent_header.addStretch()

        recent_header.addWidget(
            self._show_all_button
        )

        recent_layout.addLayout(
            recent_header
        )

        self._empty_recent_label = QLabel()

        self._empty_recent_label.setObjectName(
            "dashboardEmptyText"
        )

        self._empty_recent_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self._empty_recent_label.setMinimumHeight(
            110
        )

        recent_layout.addWidget(
            self._empty_recent_label
        )

        # -----------------------------------------------------
        # QUICK LINKS
        # -----------------------------------------------------

        self._tools_panel = QFrame()

        self._tools_panel.setObjectName(
            "dashboardPanel"
        )

        tools_layout = QVBoxLayout(
            self._tools_panel
        )

        tools_layout.setContentsMargins(
            20,
            18,
            20,
            20,
        )

        tools_layout.setSpacing(
            10
        )

        self._tools_title_label = QLabel()

        self._tools_title_label.setObjectName(
            "dashboardPanelTitle"
        )

        tools_layout.addWidget(
            self._tools_title_label
        )

        tool_definitions = [
            (
                "viewer",
                "fa5s.eye",
            ),
            (
                "edit",
                "fa5s.edit",
            ),
            (
                "favorites",
                "fa5s.star",
            ),
            (
                "trash",
                "fa5s.trash-alt",
            ),
        ]

        for (
            key,
            icon_name,
        ) in tool_definitions:
            button = QPushButton()

            button.setObjectName(
                "dashboardToolButton"
            )

            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            button.clicked.connect(
                lambda checked=False, page=key:
                    self.page_requested.emit(
                        page
                    )
            )

            self._tool_buttons.append(
                (
                    button,
                    key,
                    icon_name,
                )
            )

            tools_layout.addWidget(
                button
            )

        tools_layout.addStretch()

        lower_layout.addWidget(
            self._recent_panel,
            2,
        )

        lower_layout.addWidget(
            self._tools_panel,
            1,
        )

        content_layout.addLayout(
            lower_layout
        )

        content_layout.addStretch()

        scroll_area.setWidget(
            content
        )

        root_layout.addWidget(
            scroll_area
        )

    def retranslate_ui(
        self,
    ) -> None:
        self._title_label.setText(
            self._language_manager.tr(
                "dashboard.title"
            )
        )

        self._subtitle_label.setText(
            self._language_manager.tr(
                "dashboard.subtitle"
            )
        )

        self._quick_title_label.setText(
            self._language_manager.tr(
                "dashboard.section.quick_actions"
            )
        )

        self._recent_title_label.setText(
            self._language_manager.tr(
                "dashboard.panel.recent.title"
            )
        )

        self._show_all_button.setText(
            self._language_manager.tr(
                "dashboard.panel.recent.show_all"
            )
        )

        self._empty_recent_label.setText(
            self._language_manager.tr(
                "dashboard.panel.recent.empty"
            )
        )

        self._tools_title_label.setText(
            self._language_manager.tr(
                "dashboard.panel.tools.title"
            )
        )

        for button, key, _icon_name in self._tool_buttons:
            button.setText(
                self._language_manager.tr(
                    f"sidebar.nav.{key}"
                )
            )

        for card in self._cards:
            card.retranslate_ui()

    def apply_theme(
        self,
    ) -> None:
        icon_color = self._theme_manager.icon_color()

        for button, _key, icon_name in self._tool_buttons:
            button.setIcon(
                qta.icon(
                    icon_name,
                    color=icon_color,
                )
            )

        for card in self._cards:
            card.apply_theme()

        self._apply_panel_shadow(
            self._recent_panel
        )

        self._apply_panel_shadow(
            self._tools_panel
        )

    def _apply_panel_shadow(
        self,
        panel: QFrame,
    ) -> None:
        shadow = QGraphicsDropShadowEffect(
            panel
        )

        shadow.setBlurRadius(
            PANEL_SHADOW_BLUR
        )

        shadow.setXOffset(
            0
        )

        shadow.setYOffset(
            PANEL_SHADOW_Y
        )

        shadow.setColor(
            QColor(
                self._theme_manager.shadow_color()
            )
        )

        panel.setGraphicsEffect(
            shadow
        )

    def refresh(self) -> None:
        for row in self._recent_rows:
            row.setParent(None)
            row.deleteLater()

        self._recent_rows.clear()

        documents = backend_gateway.fetch_recent(
            limit=_RECENT_PANEL_LIMIT
        )

        self._empty_recent_label.setVisible(not documents)

        for document in documents:
            icon_name, icon_accent = type_icon(document.document_type)

            row = RecentDocumentRow(
                file_name=document.display_name,
                meta_text=format_document_meta(
                    document,
                    date=document.last_opened_at,
                ),
                icon_name=icon_name,
                icon_accent=icon_accent,
                image_path=(
                    document.stored_path
                    if document.document_type == "image"
                    else None
                ),
            )

            row.open_requested.connect(
                lambda document_id=document.id:
                    self.document_open_requested.emit(
                        document_id
                    )
            )

            self._recent_layout.addWidget(row)

            self._recent_rows.append(row)
