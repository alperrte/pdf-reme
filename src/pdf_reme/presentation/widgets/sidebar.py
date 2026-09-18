from pathlib import Path

import qtawesome as qta

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager


FLAGS_DIR = (
    Path(__file__).resolve().parents[2]
    / "resources"
    / "images"
    / "flags"
)


class Sidebar(QFrame):
    page_requested = Signal(str)

    _ICON_SIZE = 34

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName(
            "sidebar"
        )

        self.setFixedWidth(
            250
        )

        self._language_manager = get_language_manager()

        self._theme_manager = get_theme_manager()

        self._buttons: dict[
            str,
            QPushButton,
        ] = {}

        self._nav_icons: dict[
            str,
            str,
        ] = {}

        self._section_labels: list[
            tuple[QLabel, str],
        ] = []

        self._flag_buttons: dict[
            str,
            QPushButton,
        ] = {}

        self._button_group = QButtonGroup(
            self
        )

        self._button_group.setExclusive(
            True
        )

        self._setup_ui()

        self._apply_shadow()

    def _setup_ui(
        self,
    ) -> None:
        root_layout = QVBoxLayout(
            self
        )

        root_layout.setContentsMargins(
            14,
            18,
            14,
            16,
        )

        root_layout.setSpacing(
            0
        )

        # =====================================================
        # BRAND
        # =====================================================

        brand = QWidget()

        brand.setObjectName(
            "sidebarBrand"
        )

        brand_layout = QHBoxLayout(
            brand
        )

        brand_layout.setContentsMargins(
            6,
            2,
            4,
            6,
        )

        brand_layout.setSpacing(
            10
        )

        logo_label = QLabel()

        logo_label.setObjectName(
            "sidebarLogo"
        )

        logo_path = (
            Path(__file__).resolve().parents[2]
            / "resources"
            / "images"
            / "sidebar-icon.png"
        )

        pixmap = QPixmap(
            str(logo_path)
        )

        if not pixmap.isNull():
            logo_label.setPixmap(
                pixmap.scaled(
                    self._ICON_SIZE,
                    self._ICON_SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        logo_label.setFixedSize(
            self._ICON_SIZE,
            self._ICON_SIZE,
        )

        brand_title = QLabel(
            "PDF-REME"
        )

        brand_title.setObjectName(
            "sidebarBrandTitle"
        )

        brand_layout.addWidget(
            logo_label
        )

        brand_layout.addWidget(
            brand_title
        )

        brand_layout.addStretch()

        root_layout.addWidget(
            brand
        )

        root_layout.addSpacing(
            17
        )

        # =====================================================
        # SCROLLABLE NAVIGATION
        # =====================================================

        scroll_area = QScrollArea()

        scroll_area.setObjectName(
            "sidebarScrollArea"
        )

        scroll_area.setWidgetResizable(
            True
        )

        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        scroll_area.setFrameShape(
            QFrame.Shape.NoFrame
        )

        navigation_widget = QWidget()

        navigation_widget.setObjectName(
            "sidebarNavigation"
        )

        navigation_layout = QVBoxLayout(
            navigation_widget
        )

        navigation_layout.setContentsMargins(
            0,
            0,
            0,
            8,
        )

        navigation_layout.setSpacing(
            3
        )

        # -----------------------------------------------------
        # GENEL
        # -----------------------------------------------------

        self._add_section_title(
            navigation_layout,
            "sidebar.section.general",
        )

        self._add_nav_button(
            layout=navigation_layout,
            key="dashboard",
            icon="fa5s.home",
        )

        # -----------------------------------------------------
        # KÜTÜPHANE
        # -----------------------------------------------------

        self._add_section_title(
            navigation_layout,
            "sidebar.section.library",
        )

        self._add_nav_button(
            layout=navigation_layout,
            key="library",
            icon="fa5s.folder",
        )

        self._add_nav_button(
            layout=navigation_layout,
            key="favorites",
            icon="fa5s.star",
        )

        self._add_nav_button(
            layout=navigation_layout,
            key="recent",
            icon="fa5s.history",
        )

        self._add_nav_button(
            layout=navigation_layout,
            key="trash",
            icon="fa5s.trash-alt",
        )

        # -----------------------------------------------------
        # PDF ARAÇLARI
        # -----------------------------------------------------

        self._add_section_title(
            navigation_layout,
            "sidebar.section.tools",
        )

        self._add_nav_button(
            layout=navigation_layout,
            key="viewer",
            icon="fa5s.eye",
        )

        self._add_nav_button(
            layout=navigation_layout,
            key="merge",
            icon="fa5s.object-group",
        )

        self._add_nav_button(
            layout=navigation_layout,
            key="split",
            icon="fa5s.cut",
        )

        self._add_nav_button(
            layout=navigation_layout,
            key="edit",
            icon="fa5s.edit",
        )

        self._add_nav_button(
            layout=navigation_layout,
            key="compress",
            icon="fa5s.compress-arrows-alt",
        )

        self._add_nav_button(
            layout=navigation_layout,
            key="security",
            icon="fa5s.lock",
        )

        # -----------------------------------------------------
        # DÖNÜŞTÜRME
        # -----------------------------------------------------

        self._add_section_title(
            navigation_layout,
            "sidebar.section.convert",
        )

        self._add_nav_button(
            layout=navigation_layout,
            key="convert",
            icon="fa5s.exchange-alt",
        )

        navigation_layout.addStretch()

        scroll_area.setWidget(
            navigation_widget
        )

        root_layout.addWidget(
            scroll_area,
            1,
        )

        # =====================================================
        # PINNED ALT BLOK (Ayarlar + Dil + Tema)
        # =====================================================

        divider = QFrame()

        divider.setObjectName(
            "sidebarDivider"
        )

        divider.setFixedHeight(
            1
        )

        root_layout.addSpacing(
            8
        )

        root_layout.addWidget(
            divider
        )

        root_layout.addSpacing(
            8
        )

        self._add_nav_button(
            layout=root_layout,
            key="settings",
            icon="fa5s.cog",
        )

        root_layout.addSpacing(
            8
        )

        controls_row = QHBoxLayout()

        controls_row.setContentsMargins(
            2,
            0,
            2,
            0,
        )

        controls_row.setSpacing(
            6
        )

        language_group = QButtonGroup(
            self
        )

        language_group.setExclusive(
            True
        )

        self._add_flag_button(
            layout=controls_row,
            group=language_group,
            language="tr",
            flag_file="tr.png",
            tooltip="Türkçe",
        )

        self._add_flag_button(
            layout=controls_row,
            group=language_group,
            language="en",
            flag_file="gb.png",
            tooltip="English",
        )

        controls_row.addStretch()

        self._theme_button = QPushButton()

        self._theme_button.setObjectName(
            "sidebarThemeButton"
        )

        self._theme_button.setFixedSize(
            34,
            34,
        )

        self._theme_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self._theme_button.setIconSize(
            QSize(
                16,
                16,
            )
        )

        self._theme_button.clicked.connect(
            self._theme_manager.toggle_theme
        )

        controls_row.addWidget(
            self._theme_button
        )

        root_layout.addLayout(
            controls_row
        )

        root_layout.addSpacing(
            10
        )

        # =====================================================
        # FOOTER
        # =====================================================

        self._footer = QLabel()

        self._footer.setObjectName(
            "sidebarFooter"
        )

        root_layout.addWidget(
            self._footer
        )

        self.retranslate_ui()

        self.set_active_page(
            "dashboard"
        )

    def _add_section_title(
        self,
        layout: QVBoxLayout,
        translation_key: str,
    ) -> None:
        layout.addSpacing(
            8
        )

        label = QLabel()

        label.setObjectName(
            "sidebarSectionTitle"
        )

        self._section_labels.append(
            (
                label,
                translation_key,
            )
        )

        layout.addWidget(
            label
        )

    def _add_nav_button(
        self,
        *,
        layout: QVBoxLayout,
        key: str,
        icon: str,
    ) -> None:
        button = QPushButton()

        button.setProperty(
            "navButton",
            True,
        )

        button.setCheckable(
            True
        )

        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        button.setMinimumHeight(
            40
        )

        button.setIconSize(
            QSize(
                17,
                17,
            )
        )

        button.clicked.connect(
            lambda checked=False, page=key:
                self._handle_page_click(
                    page
                )
        )

        self._button_group.addButton(
            button
        )

        self._buttons[
            key
        ] = button

        self._nav_icons[
            key
        ] = icon

        layout.addWidget(
            button
        )

    def _handle_page_click(
        self,
        page: str,
    ) -> None:
        self.set_active_page(
            page
        )

        self.page_requested.emit(
            page
        )

    def set_active_page(
        self,
        page: str,
    ) -> None:
        button = self._buttons.get(
            page
        )

        if button is None:
            return

        button.setChecked(
            True
        )

    def retranslate_ui(
        self,
    ) -> None:
        for label, translation_key in self._section_labels:
            label.setText(
                self._language_manager.tr(
                    translation_key
                )
            )

        for key, button in self._buttons.items():
            button.setText(
                self._language_manager.tr(
                    f"sidebar.nav.{key}"
                )
            )

        self._footer.setText(
            self._language_manager.tr(
                "sidebar.footer"
            )
        )

        self._refresh_theme_button()

    def apply_theme(
        self,
    ) -> None:
        icon_color = self._theme_manager.icon_color()

        for key, button in self._buttons.items():
            icon_name = self._nav_icons[key]

            button.setIcon(
                qta.icon(
                    icon_name,
                    color=icon_color,
                )
            )

        self._refresh_theme_button()

        self._apply_shadow()

    def _add_flag_button(
        self,
        *,
        layout: QHBoxLayout,
        group: QButtonGroup,
        language: str,
        flag_file: str,
        tooltip: str,
    ) -> None:
        button = QPushButton()

        button.setObjectName(
            "sidebarFlagButton"
        )

        button.setCheckable(
            True
        )

        button.setFixedSize(
            36,
            28,
        )

        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        button.setToolTip(
            tooltip
        )

        pixmap = QPixmap(
            str(
                FLAGS_DIR
                / flag_file
            )
        )

        if not pixmap.isNull():
            button.setIcon(
                pixmap.scaled(
                    20,
                    20,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

            button.setIconSize(
                QSize(
                    20,
                    14,
                )
            )

        button.clicked.connect(
            lambda checked=False, lang=language:
                self._language_manager.set_language(
                    lang
                )
        )

        group.addButton(
            button
        )

        self._flag_buttons[
            language
        ] = button

        layout.addWidget(
            button
        )

        if language == self._language_manager.current_language:
            button.setChecked(
                True
            )

    def _refresh_theme_button(
        self,
    ) -> None:
        is_dark = self._theme_manager.is_dark

        icon_name = (
            "fa5s.moon"
            if is_dark
            else "fa5s.sun"
        )

        icon_color = (
            "#93C5FD"
            if is_dark
            else "#F59E0B"
        )

        self._theme_button.setIcon(
            qta.icon(
                icon_name,
                color=icon_color,
            )
        )

        self._theme_button.setToolTip(
            self._language_manager.tr(
                "topbar.theme_tooltip"
            )
        )

    def _apply_shadow(
        self,
    ) -> None:
        shadow = QGraphicsDropShadowEffect(
            self
        )

        shadow.setBlurRadius(
            28
        )

        shadow.setXOffset(
            6
        )

        shadow.setYOffset(
            0
        )

        shadow.setColor(
            QColor(
                self._theme_manager.shadow_color()
            )
        )

        self.setGraphicsEffect(
            shadow
        )
