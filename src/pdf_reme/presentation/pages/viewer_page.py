import qtawesome as qta

from PySide6.QtCore import Qt, Signal
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager
from pdf_reme.presentation.widgets.app_dialog import AppDialog

_ZOOM_STEP = 0.15
_ZOOM_MIN = 0.25
_ZOOM_MAX = 4.0


class ViewerPage(QWidget):
    open_library_requested = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._language_manager = get_language_manager()
        self._theme_manager = get_theme_manager()

        self._document = QPdfDocument(self)

        self._zoom_factor = 1.0

        self._setup_ui()
        self.retranslate_ui()
        self.apply_theme()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.setContentsMargins(42, 34, 42, 34)
        layout.setSpacing(0)

        self._stack = QStackedLayout()

        # =====================================================
        # EMPTY STATE
        # =====================================================

        empty_widget = QWidget()

        empty_layout = QVBoxLayout(empty_widget)

        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._empty_icon_label = QLabel()

        self._empty_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._empty_title_label = QLabel()

        self._empty_title_label.setObjectName("pageTitle")

        self._empty_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._empty_description_label = QLabel()

        self._empty_description_label.setObjectName("dashboardEmptyText")

        self._empty_description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._empty_open_library_button = QPushButton()

        self._empty_open_library_button.setObjectName("recentDocumentOpenButton")

        self._empty_open_library_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self._empty_open_library_button.clicked.connect(
            self.open_library_requested
        )

        empty_layout.addWidget(self._empty_icon_label)
        empty_layout.addSpacing(12)
        empty_layout.addWidget(self._empty_title_label)
        empty_layout.addWidget(self._empty_description_label)
        empty_layout.addSpacing(16)
        empty_layout.addWidget(
            self._empty_open_library_button,
            0,
            Qt.AlignmentFlag.AlignCenter,
        )

        # =====================================================
        # VIEWER CONTENT
        # =====================================================

        viewer_widget = QWidget()

        viewer_layout = QVBoxLayout(viewer_widget)

        viewer_layout.setContentsMargins(0, 0, 0, 0)

        viewer_layout.setSpacing(12)

        toolbar = QHBoxLayout()

        toolbar.setSpacing(10)

        self._file_name_label = QLabel()

        self._file_name_label.setObjectName("pageTitle")

        self._page_indicator_label = QLabel()

        self._page_indicator_label.setObjectName("documentCardMeta")

        self._zoom_out_button = QPushButton()

        self._zoom_out_button.setObjectName("documentCardIconButton")

        self._zoom_out_button.setFixedSize(34, 34)

        self._zoom_out_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self._zoom_out_button.clicked.connect(self._zoom_out)

        self._zoom_in_button = QPushButton()

        self._zoom_in_button.setObjectName("documentCardIconButton")

        self._zoom_in_button.setFixedSize(34, 34)

        self._zoom_in_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self._zoom_in_button.clicked.connect(self._zoom_in)

        toolbar.addWidget(self._file_name_label)
        toolbar.addStretch(1)
        toolbar.addWidget(self._page_indicator_label)
        toolbar.addWidget(self._zoom_out_button)
        toolbar.addWidget(self._zoom_in_button)

        self._pdf_view = QPdfView()

        self._pdf_view.setDocument(self._document)

        self._pdf_view.setPageMode(QPdfView.PageMode.MultiPage)

        self._pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)

        self._pdf_view.pageNavigator().currentPageChanged.connect(
            self._update_page_indicator
        )

        viewer_layout.addLayout(toolbar)
        viewer_layout.addWidget(self._pdf_view, 1)

        self._stack.addWidget(empty_widget)
        self._stack.addWidget(viewer_widget)

        layout.addLayout(self._stack)

    def retranslate_ui(self) -> None:
        self._empty_title_label.setText(
            self._language_manager.tr("viewer.empty_title")
        )

        self._empty_description_label.setText(
            self._language_manager.tr("viewer.empty_description")
        )

        self._empty_open_library_button.setText(
            self._language_manager.tr("viewer.open_library_button")
        )

    def apply_theme(self) -> None:
        self._empty_icon_label.setPixmap(
            qta.icon(
                "fa5s.file-pdf",
                color=self._theme_manager.accent_hex("red"),
            ).pixmap(64, 64)
        )

        self._zoom_out_button.setIcon(
            qta.icon(
                "fa5s.search-minus",
                color=self._theme_manager.icon_color(),
            )
        )

        self._zoom_in_button.setIcon(
            qta.icon(
                "fa5s.search-plus",
                color=self._theme_manager.icon_color(),
            )
        )

    def load_document(
        self,
        stored_path: str,
        display_name: str,
    ) -> None:
        error = self._document.load(stored_path)

        if error != QPdfDocument.Error.None_:
            AppDialog.inform(
                self,
                title=self._language_manager.tr("viewer.load_error_title"),
                body=self._language_manager.tr("viewer.load_error_body"),
                variant="danger",
                icon_name="fa5s.exclamation",
            )

            self._stack.setCurrentIndex(0)

            return

        self._file_name_label.setText(display_name)

        self._zoom_factor = 1.0

        self._pdf_view.setZoomFactor(self._zoom_factor)

        self._stack.setCurrentIndex(1)

        self._update_page_indicator()

    def _update_page_indicator(self, *_args) -> None:
        page_count = self._document.pageCount()

        navigator = self._pdf_view.pageNavigator()

        current_index = navigator.currentPage() if navigator is not None else 0

        self._page_indicator_label.setText(
            f"{current_index + 1} / {max(page_count, 1)}"
        )

    def _zoom_in(self) -> None:
        self._zoom_factor = min(_ZOOM_MAX, self._zoom_factor + _ZOOM_STEP)

        self._pdf_view.setZoomFactor(self._zoom_factor)

    def _zoom_out(self) -> None:
        self._zoom_factor = max(_ZOOM_MIN, self._zoom_factor - _ZOOM_STEP)

        self._pdf_view.setZoomFactor(self._zoom_factor)
