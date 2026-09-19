import shiboken6

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from pdf_reme.presentation.widgets.page_thumbnail_grid import (
    PageThumbnailGrid,
    render_page_thumbnail,
)

_THUMBS_PER_TICK = 4


class PdfThumbnailPanel(QScrollArea):
    """Bir PDF'in sayfa küçük resimlerini kaydırılabilir ızgarada gösterir.

    Küçük resimler tembel (4'lü gruplar hâlinde) çizilir; sayfa tıklaması
    `page_clicked` ile bildirilir, seçim `set_selection` ile dışarıdan verilir.
    """

    page_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._document: QPdfDocument | None = None
        self._render_queue: list[int] = []
        self._generation = 0

        self.setObjectName("dashboardScrollArea")
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._grid = PageThumbnailGrid(draggable=False)
        self._grid.page_clicked.connect(self.page_clicked)

        holder = QWidget()
        holder.setObjectName("dashboardContent")

        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 4, 4, 0)
        holder_layout.addWidget(self._grid)
        holder_layout.addStretch(1)

        self.setWidget(holder)

    @property
    def page_count(self) -> int:
        return len(self._grid.thumbs)

    def load(self, path: str) -> int:
        """PDF'i yükler, küçük resim çizimini başlatır; sayfa sayısını döner."""
        self.clear()

        document = QPdfDocument(self)
        document.load(path)

        self._document = document

        count = document.pageCount()

        self._grid.set_page_count(max(count, 0))
        self._render_queue = list(range(max(count, 0)))

        generation = self._generation
        QTimer.singleShot(0, lambda: self._render_batch(generation))

        return max(count, 0)

    def clear(self) -> None:
        """Belgeyi kapatır; Windows'ta dosya kilidinin çözülmesi için siler."""
        self._generation += 1
        self._render_queue.clear()

        self._grid.set_page_count(0)

        document = self._document
        self._document = None

        if document is not None and shiboken6.isValid(document):
            document.close()

            shiboken6.delete(document)

    def set_selection(self, pages: set[int]) -> None:
        self._grid.set_selection(pages)

    def _render_batch(self, generation: int) -> None:
        document = self._document

        if (
            generation != self._generation
            or document is None
            or not shiboken6.isValid(document)
        ):
            return

        for _ in range(_THUMBS_PER_TICK):
            if not self._render_queue:
                return

            index = self._render_queue.pop(0)

            if index >= len(self._grid.thumbs):
                continue

            pixmap = render_page_thumbnail(document, index)

            if pixmap is not None:
                self._grid.thumbs[index].set_pixmap(pixmap)

        if self._render_queue:
            QTimer.singleShot(0, lambda: self._render_batch(generation))
