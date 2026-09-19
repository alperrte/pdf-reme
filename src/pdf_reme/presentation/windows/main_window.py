from PySide6.QtCore import (
    QPointF,
    QTimer,
    QUrl,
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation import app_settings, backend_gateway
from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.pages.dashboard_page import DashboardPage
from pdf_reme.presentation.pages.convert_page import ConvertPage
from pdf_reme.presentation.pages.edit_page import EditPage
from pdf_reme.presentation.pages.favorites_page import FavoritesPage
from pdf_reme.presentation.pages.compress_page import CompressPage
from pdf_reme.presentation.pages.library_page import LibraryPage
from pdf_reme.presentation.pages.merge_page import MergePage
from pdf_reme.presentation.pages.recent_page import RecentPage
from pdf_reme.presentation.pages.security_page import SecurityPage
from pdf_reme.presentation.pages.settings_page import SettingsPage
from pdf_reme.presentation.pages.split_page import SplitPage
from pdf_reme.presentation.pages.trash_page import TrashPage
from pdf_reme.presentation.pages.viewer_page import ViewerPage
from pdf_reme.presentation.theme import get_theme_manager
from pdf_reme.presentation.widgets.sidebar import Sidebar
from pdf_reme.presentation.widgets.language_transition import (
    LanguageTransitionOverlay,
)
from pdf_reme.presentation.widgets.theme_transition import (
    ThemeTransitionOverlay,
)


# Sidebar'daki, henüz gerçek arayüzü olmayan V1 nav öğeleri için
# placeholder sayfalar. Başlık metni sidebar.nav.<key> çeviri
# anahtarıyla paylaşılır (ikisi de aynı metni gösterir), açıklama
# ise placeholder.<key>.description.
# Ortak PdfToolPage iskeletini kullanan PDF araç sayfaları.
TOOL_PAGES = (
    ("merge", MergePage),
    ("split", SplitPage),
    ("compress", CompressPage),
    ("security", SecurityPage),
)

TOOL_PAGE_KEYS = tuple(key for key, _page_class in TOOL_PAGES)

PLACEHOLDER_PAGE_KEYS: tuple[str, ...] = ()

# refresh() metoduna sahip, her show_page() çağrısında
# kendini güncel backend verisiyle tazeleyen sayfalar.
REFRESHABLE_PAGE_KEYS = (
    "dashboard",
    "library",
    "favorites",
    "recent",
    "trash",
    "settings",
)


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

        self._theme_overlay: ThemeTransitionOverlay | None = None
        self._language_overlay: LanguageTransitionOverlay | None = None
        self._shown_language = self._language_manager.current_language
        self._startup_tasks_scheduled = False

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

        # Tema geçişinde güneş/ay animasyonunu oynatan örtü.
        self._theme_overlay = ThemeTransitionOverlay(root)

        # Dil değişiminde bulanıklaşıp bayrak çeviren örtü.
        self._language_overlay = LanguageTransitionOverlay(root)

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

        dashboard_page.document_open_requested.connect(
            self._open_document
        )

        self._pages[
            "dashboard"
        ] = dashboard_page

        self.page_stack.addWidget(
            dashboard_page
        )

        # =====================================================
        # KÜTÜPHANE + FAVORİLER + SON KULLANILANLAR + ÇÖP KUTUSU
        # =====================================================

        library_page = LibraryPage()
        library_page.document_open_requested.connect(self._open_document)
        self._pages["library"] = library_page
        self.page_stack.addWidget(library_page)

        favorites_page = FavoritesPage()
        favorites_page.document_open_requested.connect(self._open_document)
        self._pages["favorites"] = favorites_page
        self.page_stack.addWidget(favorites_page)

        recent_page = RecentPage()
        recent_page.document_open_requested.connect(self._open_document)
        self._pages["recent"] = recent_page
        self.page_stack.addWidget(recent_page)

        trash_page = TrashPage()
        self._pages["trash"] = trash_page
        self.page_stack.addWidget(trash_page)

        # =====================================================
        # PDF GÖRÜNTÜLEYİCİ
        # =====================================================

        viewer_page = ViewerPage()
        viewer_page.open_library_requested.connect(
            lambda: self.show_page("library")
        )
        self._pages["viewer"] = viewer_page
        self.page_stack.addWidget(viewer_page)

        # =====================================================
        # PDF DÜZENLE + PDF DÖNÜŞTÜR
        # =====================================================

        edit_page = EditPage()
        edit_page.document_open_requested.connect(self._open_document)
        self._pages["edit"] = edit_page
        self.page_stack.addWidget(edit_page)

        convert_page = ConvertPage()
        convert_page.page_requested.connect(self.show_page)
        self._pages["convert"] = convert_page
        self.page_stack.addWidget(convert_page)

        # =====================================================
        # PDF BİRLEŞTİR + BÖL + SIKIŞTIR + ŞİFRELEME
        # =====================================================

        for key, page_class in TOOL_PAGES:
            tool_page = page_class()
            tool_page.page_requested.connect(self.show_page)
            tool_page.document_open_requested.connect(self._open_document)
            self._pages[key] = tool_page
            self.page_stack.addWidget(tool_page)

        # =====================================================
        # AYARLAR
        # =====================================================

        settings_page = SettingsPage()
        settings_page.defaults_changed.connect(self._apply_tool_defaults)
        self._pages["settings"] = settings_page
        self.page_stack.addWidget(settings_page)

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

    def closeEvent(self, event) -> None:
        # Arka plan işi sürerken pencere kapanırsa iş parçacığı yarıda kalmasın;
        # düzenleme çalışma klasörü de temizlensin.
        for key in ("edit", "convert", *TOOL_PAGE_KEYS, "settings"):
            self._pages[key].shutdown()

        super().closeEvent(event)

    def _apply_tool_defaults(self) -> None:
        """Ayarlar'daki varsayılanlar değişince ilgili araç sayfalarını günceller."""
        self._pages["compress"].apply_defaults()
        self._pages["split"].apply_defaults()

    def showEvent(self, event) -> None:
        super().showEvent(event)

        # Sessiz güncelleme denetimi (ayar açıksa) ilk gösterimden sonra bir kez.
        if not self._startup_tasks_scheduled:
            self._startup_tasks_scheduled = True

            QTimer.singleShot(
                1500,
                self._pages["settings"].run_startup_check,
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

        if page_key in REFRESHABLE_PAGE_KEYS:
            page.refresh()

    def _open_document(
        self,
        document_id: str,
    ) -> None:
        document = backend_gateway.mark_as_opened(document_id)

        if document.document_type == "pdf":
            self._pages["viewer"].load_document(
                document.stored_path,
                document.display_name,
            )

            self.show_page("viewer")
        else:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(document.stored_path)
            )

    def _on_language_changed(
        self,
        language: str,
    ) -> None:
        previous = self._shown_language
        self._shown_language = language

        overlay = self._language_overlay

        if overlay.is_running:
            overlay.stop()

        # Geçiş sırasında tema örtüsü açıksa onu bitir.
        if self._theme_overlay.is_running:
            self._theme_overlay.stop()

        # Pencere görünmüyorsa ya da animasyon Ayarlar'dan kapatıldıysa
        # animasyonsuz uygula.
        if not self.isVisible() or not app_settings.language_animation():
            self._apply_language()
            return

        old_frame = self._root.grab()

        overlay.hide()

        self._apply_language()

        QApplication.sendPostedEvents()

        new_frame = self._root.grab()

        overlay.start(
            old_frame,
            new_frame,
            old_language=previous,
            new_language=language,
        )

    def _apply_language(
        self,
    ) -> None:
        self.sidebar.retranslate_ui()

        dashboard = self._pages.get(
            "dashboard"
        )

        if dashboard is not None:
            dashboard.retranslate_ui()

        for key in (
            "library",
            "favorites",
            "recent",
            "trash",
            "viewer",
            "edit",
            "convert",
            *TOOL_PAGE_KEYS,
            "settings",
        ):
            self._pages[key].retranslate_ui()

        for key in self._placeholder_labels:
            self._retranslate_placeholder(
                key
            )

    def _animate_theme_change(
        self,
        theme: str,
    ) -> None:
        overlay = self._theme_overlay

        if overlay.is_running:
            overlay.stop()

        if self._language_overlay.is_running:
            self._language_overlay.stop()

        # Pencere görünmüyorsa (ör. başlangıç) ya da animasyon Ayarlar'dan
        # kapatıldıysa animasyonsuz uygula.
        if not self.isVisible() or not app_settings.theme_animation():
            self._apply_theme(theme)
            return

        # Eski görüntüyü al, temayı (ağır QSS yenilemesi) ekran
        # donmadan uygula, yeni görüntüyü al; animasyon sadece bu iki
        # resmi karıştırır.
        old_frame = self._root.grab()

        overlay.setGeometry(self._root.rect())
        overlay.hide()

        self._apply_theme(theme)

        QApplication.sendPostedEvents()

        new_frame = self._root.grab()

        theme_button = self.sidebar.theme_button

        overlay.start(
            old_frame,
            new_frame,
            to_dark=theme == "dark",
            target=QPointF(
                theme_button.mapTo(
                    self._root,
                    theme_button.rect().center(),
                )
            ),
        )

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

        for key in (
            "library",
            "favorites",
            "recent",
            "trash",
            "viewer",
            "edit",
            "convert",
            *TOOL_PAGE_KEYS,
            "settings",
        ):
            self._pages[key].apply_theme()
