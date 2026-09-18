from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.pages.dashboard_page import DashboardPage
from pdf_reme.presentation.theme import get_theme_manager
from pdf_reme.presentation.widgets.sidebar import Sidebar


# Sidebar'daki tüm V1 nav öğeleri için placeholder sayfalar.
# Başlık metni sidebar.nav.<key> çeviri anahtarıyla paylaşılır
# (ikisi de aynı metni gösterir), açıklama ise placeholder.<key>.description.
PLACEHOLDER_PAGE_KEYS = (
    "library",
    "favorites",
    "recent",
    "trash",
    "viewer",
    "merge",
    "split",
    "edit",
    "convert",
    "compress",
    "security",
    "settings",
)

_THEME_FADE_OUT_MS = 110
_THEME_FADE_IN_MS = 170


class MainWindow(QMainWindow):
    def __init__(
        self,
    ) -> None:
        super().__init__()

        self.setWindowTitle(
            "PDF-REME"
        )

        self.resize(
            1360,
            860,
        )

        self.setMinimumSize(
            1100,
            700,
        )

        self._language_manager = get_language_manager()

        self._theme_manager = get_theme_manager()

        self._pages: dict[
            str,
            QWidget,
        ] = {}

        self._placeholder_labels: dict[
            str,
            tuple[QLabel, QLabel],
        ] = {}

        self._theme_transition_animation: QPropertyAnimation | None = None

        self._theme_overlay: QWidget | None = None

        self._theme_overlay_effect: QGraphicsOpacityEffect | None = None

        self._setup_ui()
        self._setup_pages()
        self._connect_signals()

        self._apply_theme(
            self._theme_manager.current_theme
        )

        self.show_page(
            "dashboard"
        )

    def _setup_ui(
        self,
    ) -> None:
        root = QWidget()

        root.setObjectName(
            "appRoot"
        )

        self._root = root

        root_layout = QHBoxLayout(
            root
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

        # =====================================================
        # SIDEBAR
        # =====================================================

        self.sidebar = Sidebar()

        # =====================================================
        # CONTENT
        # =====================================================

        self.content_container = QFrame()

        self.content_container.setObjectName(
            "contentArea"
        )

        self.content_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        content_layout = QVBoxLayout(
            self.content_container
        )

        content_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        content_layout.setSpacing(
            0
        )

        self.page_stack = QStackedWidget()

        self.page_stack.setObjectName(
            "pageStack"
        )

        content_layout.addWidget(
            self.page_stack,
            1,
        )

        root_layout.addWidget(
            self.sidebar
        )

        root_layout.addWidget(
            self.content_container,
            1,
        )

        self.setCentralWidget(
            root
        )

        # Tema geçişi sırasında ekranı geçici olarak kaplayan,
        # tamamen opak bir örtü widget'ı. Pencerenin native
        # opaklığına (windowOpacity) hiç dokunmadığı için işletim
        # sistemi düzeyinde bir şeffaflaşma/masaüstünün görünmesi
        # riski taşımaz; kendi başına ayrı bir widget olduğundan
        # (içinde başka QGraphicsEffect'li alt widget barındırmaz)
        # sidebar/kartlardaki gölge efektleriyle de çakışmaz.
        self._theme_overlay = QWidget(root)

        self._theme_overlay.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground,
            True,
        )

        self._theme_overlay.hide()

        self._theme_overlay_effect = QGraphicsOpacityEffect(
            self._theme_overlay
        )

        self._theme_overlay_effect.setOpacity(
            0.0
        )

        self._theme_overlay.setGraphicsEffect(
            self._theme_overlay_effect
        )

    def _setup_pages(
        self,
    ) -> None:

        # =====================================================
        # REAL DASHBOARD
        # =====================================================

        dashboard_page = DashboardPage()

        dashboard_page.page_requested.connect(
            self.show_page
        )

        self._pages[
            "dashboard"
        ] = dashboard_page

        self.page_stack.addWidget(
            dashboard_page
        )

        # =====================================================
        # TEMPORARY PLACEHOLDER PAGES
        # =====================================================

        for key in PLACEHOLDER_PAGE_KEYS:
            page = self._create_placeholder_page(
                key
            )

            self._pages[
                key
            ] = page

            self.page_stack.addWidget(
                page
            )

    def _create_placeholder_page(
        self,
        key: str,
    ) -> QWidget:

        page = QWidget()

        page.setObjectName(
            "placeholderPage"
        )

        layout = QVBoxLayout(
            page
        )

        layout.setContentsMargins(
            42,
            34,
            42,
            34,
        )

        layout.setSpacing(
            8
        )

        title_label = QLabel()

        title_label.setObjectName(
            "pageTitle"
        )

        description_label = QLabel()

        description_label.setObjectName(
            "pageDescription"
        )

        description_label.setWordWrap(
            True
        )

        layout.addWidget(
            title_label
        )

        layout.addWidget(
            description_label
        )

        layout.addStretch()

        self._placeholder_labels[
            key
        ] = (
            title_label,
            description_label,
        )

        self._retranslate_placeholder(
            key
        )

        return page

    def _retranslate_placeholder(
        self,
        key: str,
    ) -> None:
        title_label, description_label = self._placeholder_labels[
            key
        ]

        title_label.setText(
            self._language_manager.tr(
                f"sidebar.nav.{key}"
            )
        )

        description_label.setText(
            self._language_manager.tr(
                f"placeholder.{key}.description"
            )
        )

    def _connect_signals(
        self,
    ) -> None:

        self.sidebar.page_requested.connect(
            self.show_page
        )

        self._language_manager.language_changed.connect(
            self._on_language_changed
        )

        self._theme_manager.theme_changed.connect(
            self._animate_theme_change
        )

    def show_page(
        self,
        page_key: str,
    ) -> None:

        page = self._pages.get(
            page_key
        )

        if page is None:
            return

        self.page_stack.setCurrentWidget(
            page
        )

        self.sidebar.set_active_page(
            page_key
        )

    def _on_language_changed(
        self,
        _language: str,
    ) -> None:
        self.sidebar.retranslate_ui()

        dashboard = self._pages.get(
            "dashboard"
        )

        if dashboard is not None:
            dashboard.retranslate_ui()

        for key in self._placeholder_labels:
            self._retranslate_placeholder(
                key
            )

    def _animate_theme_change(
        self,
        theme: str,
    ) -> None:
        if self._theme_transition_animation is not None:
            self._theme_transition_animation.stop()

        overlay = self._theme_overlay

        effect = self._theme_overlay_effect

        # Native pencere opaklığı (windowOpacity) yerine, kendi
        # üzerinde başka bir QGraphicsEffect barındırmayan, tamamen
        # opak bir Qt widget'ı ile ekranı geçici olarak örtüyoruz.
        # Bu örtü, işletim sistemi/kompozitör seviyesinde gerçek bir
        # şeffaflığa asla dönüşmez (masaüstü hiçbir zaman açığa
        # çıkamaz); ağır ve senkron QSS yeniden uygulaması, örtü tam
        # opak durumdayken (opacity=1.0) çalıştırılır, böylece bu iş
        # sırasında ekranda görünen tek şey düz bir renk olur.
        current_tokens = self._theme_manager.tokens()

        overlay.setStyleSheet(
            "background-color: "
            f"{current_tokens['window_bg']};"
        )

        overlay.setGeometry(
            self._root.rect()
        )

        overlay.raise_()

        overlay.show()

        fade_in = QPropertyAnimation(
            effect,
            b"opacity",
            self,
        )

        fade_in.setDuration(
            _THEME_FADE_OUT_MS
        )

        fade_in.setStartValue(
            0.0
        )

        fade_in.setEndValue(
            1.0
        )

        fade_in.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )

        def _apply_and_fade_out() -> None:
            self._apply_theme(
                theme
            )

            fade_out = QPropertyAnimation(
                effect,
                b"opacity",
                self,
            )

            fade_out.setDuration(
                _THEME_FADE_IN_MS
            )

            fade_out.setStartValue(
                1.0
            )

            fade_out.setEndValue(
                0.0
            )

            fade_out.setEasingCurve(
                QEasingCurve.Type.InCubic
            )

            fade_out.finished.connect(
                overlay.hide
            )

            fade_out.start()

            self._theme_transition_animation = fade_out

        fade_in.finished.connect(
            _apply_and_fade_out
        )

        fade_in.start()

        self._theme_transition_animation = fade_in

    def _apply_theme(
        self,
        theme: str,
    ) -> None:
        app = QApplication.instance()

        if app is not None:
            self._theme_manager.apply_palette(
                app
            )

        self._root.setProperty(
            "theme",
            theme,
        )

        if app is not None:
            # Dinamik property değişikliğinin tüm alt widget
            # ağacında yeniden değerlendirilmesini (repolish)
            # tetiklemenin en güvenilir yolu: aynı stylesheet'i
            # yeniden uygulamak.
            app.setStyleSheet(
                app.styleSheet()
            )

        self.sidebar.apply_theme()

        dashboard = self._pages.get(
            "dashboard"
        )

        if dashboard is not None:
            dashboard.apply_theme()
