from PySide6.QtCore import QMimeData, QPoint, QSize, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QImage, QPainter, QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

PAGE_MIME = "application/x-pdfreme-page"

THUMB_WIDTH = 150
THUMB_HEIGHT = 208
IMAGE_BOX_WIDTH = 128
IMAGE_BOX_HEIGHT = 158
_GRID_SPACING = 14
_THUMB_RENDER_SCALE = 1.5


def render_page_thumbnail(
    document: QPdfDocument,
    index: int,
) -> QPixmap | None:
    """Sayfa küçük resim kutusuna sığacak şekilde çizilmiş pixmap (0 tabanlı)."""
    point_size = document.pagePointSize(index)

    if point_size.width() <= 0 or point_size.height() <= 0:
        return None

    scale = min(
        IMAGE_BOX_WIDTH / point_size.width(),
        IMAGE_BOX_HEIGHT / point_size.height(),
    )

    target = QSize(
        max(1, int(point_size.width() * scale * _THUMB_RENDER_SCALE)),
        max(1, int(point_size.height() * scale * _THUMB_RENDER_SCALE)),
    )

    rendered = document.render(index, target)

    if rendered.isNull():
        return None

    # Sayfa şeffaf çizilir; koyu temada okunaklı kalması için beyaza oturtulur.
    image = QImage(rendered.size(), QImage.Format.Format_RGB32)
    image.fill(QColor("white"))

    painter = QPainter(image)
    painter.drawImage(0, 0, rendered)
    painter.end()

    pixmap = QPixmap.fromImage(image)
    pixmap.setDevicePixelRatio(_THUMB_RENDER_SCALE)

    return pixmap


class PageThumbnail(QFrame):
    """Tek sayfanın küçük resmi; tıklayınca seçilir, sürüklenince taşınır."""

    clicked = Signal(int)

    def __init__(
        self,
        page_number: int,
        parent: QWidget | None = None,
        draggable: bool = True,
    ) -> None:
        super().__init__(parent)

        self.page_number = page_number
        self._draggable = draggable
        self._press_position: QPoint | None = None

        self.setObjectName("editThumb")
        self.setProperty("selected", False)
        self.setFixedSize(THUMB_WIDTH, THUMB_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(6)

        self._image_label = QLabel()
        self._image_label.setObjectName("editThumbImage")
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setFixedSize(IMAGE_BOX_WIDTH, IMAGE_BOX_HEIGHT)

        self._number_label = QLabel(str(page_number))
        self._number_label.setObjectName("editThumbNumber")
        self._number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._image_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._number_label)

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._image_label.setPixmap(pixmap)

    def set_selected(self, selected: bool) -> None:
        if bool(self.property("selected")) == selected:
            return

        self.setProperty("selected", selected)

        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_position = event.position().toPoint()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if (
            not self._draggable
            or self._press_position is None
            or not event.buttons() & Qt.MouseButton.LeftButton
        ):
            return

        distance = (
            event.position().toPoint() - self._press_position
        ).manhattanLength()

        if distance < QApplication.startDragDistance():
            return

        self._press_position = None

        mime = QMimeData()
        mime.setData(PAGE_MIME, str(self.page_number).encode("ascii"))

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(self.grab().scaledToWidth(90))
        drag.setHotSpot(QPoint(45, 20))
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event) -> None:
        if (
            self._press_position is not None
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self._press_position = None
            self.clicked.emit(self.page_number)

        super().mouseReleaseEvent(event)


class PageThumbnailGrid(QWidget):
    """Sayfa küçük resimlerini genişliğe göre satırlara dizer ve bırakma hedefidir."""

    page_clicked = Signal(int)
    page_dropped = Signal(int, int, bool)  # taşınan, hedef, hedefin sonrasına mı

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        single_column: bool = False,
        draggable: bool = True,
    ) -> None:
        super().__init__(parent)

        self._thumbs: list[PageThumbnail] = []
        self._columns = 0
        self._single_column = single_column
        self._draggable = draggable

        self.setAcceptDrops(draggable)

        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(2, 2, 2, 2)
        self._layout.setSpacing(_GRID_SPACING)
        self._layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

    @property
    def thumbs(self) -> list[PageThumbnail]:
        return self._thumbs

    def set_page_count(self, count: int) -> None:
        for thumb in self._thumbs:
            self._layout.removeWidget(thumb)
            thumb.deleteLater()

        self._thumbs = []

        for page_number in range(1, count + 1):
            thumb = PageThumbnail(page_number, self, self._draggable)
            thumb.clicked.connect(self.page_clicked)

            self._thumbs.append(thumb)

        self._columns = 0
        self.reflow(self.width())

    def set_selection(self, selected: set[int]) -> None:
        for thumb in self._thumbs:
            thumb.set_selected(thumb.page_number in selected)

    def columns_for_width(self, width: int) -> int:
        if self._single_column:
            return 1

        return max(
            1,
            (width + _GRID_SPACING) // (THUMB_WIDTH + _GRID_SPACING),
        )

    def reflow(self, width: int) -> None:
        columns = self.columns_for_width(width)

        if columns == self._columns and self._layout.count() == len(
            self._thumbs
        ):
            return

        self._columns = columns

        for thumb in self._thumbs:
            self._layout.removeWidget(thumb)

        for index, thumb in enumerate(self._thumbs):
            self._layout.addWidget(thumb, index // columns, index % columns)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

        self.reflow(event.size().width())

    # ------------------------------------------------------------------
    # Sürükle-bırak (sayfa sıralama)
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(PAGE_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(PAGE_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        mime = event.mimeData()

        if not mime.hasFormat(PAGE_MIME) or not self._thumbs:
            event.ignore()
            return

        moved_page = int(bytes(mime.data(PAGE_MIME)).decode("ascii"))

        position = event.position().toPoint()

        target = min(
            self._thumbs,
            key=lambda thumb: (
                (thumb.geometry().center() - position).manhattanLength()
            ),
        )

        if self._single_column:
            after = position.y() > target.geometry().center().y()
        else:
            after = position.x() > target.geometry().center().x()

        event.acceptProposedAction()

        self.page_dropped.emit(moved_page, target.page_number, after)
