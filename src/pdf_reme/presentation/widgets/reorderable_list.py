from PySide6.QtCore import QMimeData, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QDrag, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation.theme import get_theme_manager

ROW_MIME = "application/x-pdfreme-list-row"

_ROW_SPACING = 8
_INDICATOR_HEIGHT = 3
_AUTOSCROLL_EDGE = 36
_AUTOSCROLL_STEP = 14
_AUTOSCROLL_INTERVAL_MS = 30


def move_item(items: list, source: int, slot: int) -> list:
    """`source` indeksindeki öğeyi `slot` ekleme aralığına taşıyan yeni liste.

    `slot`, öğeler arasındaki boşluğun numarasıdır (0 = en başa, len = en
    sona); kaynak listeden çıkarılmadan önceki sıralamaya göre verilir.
    """
    result = list(items)

    if not 0 <= source < len(result):
        return result

    slot = min(max(0, slot), len(result))

    item = result.pop(source)

    if slot > source:
        slot -= 1

    result.insert(slot, item)

    return result


class ReorderableRowList(QWidget):
    """Alt alta satırlardan oluşan, sürükle-bırak ile sıralanabilen liste.

    Satırlar sayfalarca kurulur (`set_rows`); satır tasarımına dokunulmaz,
    yalnızca gövdesinden tutulup sürüklenebilir yapılır (satırdaki düğmeler
    kendi tıklamalarını korur). Sıralamanın tek doğruluk kaynağı sayfanın kendi
    listesidir: bu bileşen yalnız `reordered(kaynak, aralık)` bildirir; sayfa
    listeyi `move_item` ile günceller ve satırları yeniden kurar.
    """

    reordered = Signal(int, int)  # kaynak indeks, ekleme aralığı (0..n)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setObjectName("dashboardContent")
        self.setAcceptDrops(True)

        self._rows: list[QWidget] = []
        self._reorderable = False
        self._drop_slot: int | None = None
        self._press: tuple[QWidget, QPoint] | None = None
        self._autoscroll = 0

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 4, 0)
        self._layout.setSpacing(_ROW_SPACING)
        self._layout.addStretch(1)

        self._autoscroll_timer = QTimer(self)
        self._autoscroll_timer.setInterval(_AUTOSCROLL_INTERVAL_MS)
        self._autoscroll_timer.timeout.connect(self._on_autoscroll)

    @property
    def rows(self) -> list[QWidget]:
        return self._rows

    @property
    def reorderable(self) -> bool:
        return self._reorderable

    def set_reorderable(self, reorderable: bool) -> None:
        self._reorderable = reorderable

        self._apply_row_cursors()

    def set_rows(self, rows: list[QWidget]) -> None:
        """Satırları yeniler; liste kaydırma konumu korunur."""
        bar = self._scroll_bar()
        scroll = bar.value() if bar is not None else 0

        for row in self._rows:
            row.removeEventFilter(self)

            self._layout.removeWidget(row)

            row.hide()
            row.deleteLater()

        self._rows = list(rows)
        self._press = None

        for index, row in enumerate(self._rows):
            row.installEventFilter(self)

            self._layout.insertWidget(index, row)

        self._apply_row_cursors()

        if bar is not None:
            bar.setValue(scroll)

            QTimer.singleShot(0, lambda: bar.setValue(scroll))

    # ------------------------------------------------------------------
    # Sürükleme başlatma
    # ------------------------------------------------------------------

    def _apply_row_cursors(self) -> None:
        for row in self._rows:
            if self._reorderable:
                row.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                row.unsetCursor()

    def eventFilter(self, watched, event) -> bool:
        if not self._reorderable or watched not in self._rows:
            return False

        kind = event.type()

        if kind == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self._press = (watched, event.position().toPoint())

        elif kind == event.Type.MouseButtonRelease:
            self._press = None

        elif kind == event.Type.MouseMove and self._press is not None:
            row, origin = self._press

            if (
                row is watched
                and event.buttons() & Qt.MouseButton.LeftButton
                and (event.position().toPoint() - origin).manhattanLength()
                >= QApplication.startDragDistance()
            ):
                self._press = None
                self._start_drag(row, origin)

        return False

    def _start_drag(self, row: QWidget, origin: QPoint) -> None:
        index = self._rows.index(row)

        mime = QMimeData()
        mime.setData(ROW_MIME, str(index).encode("ascii"))

        drag = QDrag(row)
        drag.setMimeData(mime)
        drag.setPixmap(row.grab())
        drag.setHotSpot(origin)

        drag.exec(Qt.DropAction.MoveAction)

        self._set_drop_slot(None)
        self._set_autoscroll(0)

    # ------------------------------------------------------------------
    # Bırakma hedefi
    # ------------------------------------------------------------------

    def _dragged_index(self, mime: QMimeData) -> int | None:
        if not self._reorderable or not mime.hasFormat(ROW_MIME):
            return None

        try:
            index = int(bytes(mime.data(ROW_MIME)).decode("ascii"))

        except ValueError:
            return None

        return index if 0 <= index < len(self._rows) else None

    def slot_at(self, y: int) -> int:
        """`y` (bileşen koordinatı) konumuna en yakın ekleme aralığı."""
        for index, row in enumerate(self._rows):
            if y < row.geometry().center().y():
                return index

        return len(self._rows)

    def dragEnterEvent(self, event) -> None:
        if self._dragged_index(event.mimeData()) is None:
            event.ignore()
            return

        event.acceptProposedAction()

        self._track(event.position().toPoint())

    def dragMoveEvent(self, event) -> None:
        if self._dragged_index(event.mimeData()) is None:
            event.ignore()
            return

        event.acceptProposedAction()

        self._track(event.position().toPoint())

    def dragLeaveEvent(self, event) -> None:
        self._set_drop_slot(None)
        self._set_autoscroll(0)

        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        source = self._dragged_index(event.mimeData())

        slot = self.slot_at(event.position().toPoint().y())

        self._set_drop_slot(None)
        self._set_autoscroll(0)

        if source is None:
            event.ignore()
            return

        event.acceptProposedAction()

        if slot not in (source, source + 1):
            self.reordered.emit(source, slot)

    def _track(self, position: QPoint) -> None:
        self._set_drop_slot(self.slot_at(position.y()))

        area = self._scroll_area()

        if area is None:
            return

        y = self.mapTo(area.viewport(), position).y()
        height = area.viewport().height()

        if y < _AUTOSCROLL_EDGE:
            self._set_autoscroll(-_AUTOSCROLL_STEP)
        elif y > height - _AUTOSCROLL_EDGE:
            self._set_autoscroll(_AUTOSCROLL_STEP)
        else:
            self._set_autoscroll(0)

    # ------------------------------------------------------------------
    # Ekleme çizgisi + otomatik kaydırma
    # ------------------------------------------------------------------

    def _set_drop_slot(self, slot: int | None) -> None:
        if slot != self._drop_slot:
            self._drop_slot = slot
            self.update()

    def _indicator_y(self, slot: int) -> int:
        if not self._rows:
            return 0

        if slot <= 0:
            return self._rows[0].geometry().top() - _ROW_SPACING // 2

        if slot >= len(self._rows):
            return self._rows[-1].geometry().bottom() + _ROW_SPACING // 2

        return (
            self._rows[slot - 1].geometry().bottom()
            + self._rows[slot].geometry().top()
        ) // 2

    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        if self._drop_slot is None or not self._rows:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(get_theme_manager().accent_hex("blue")))

        painter.drawRoundedRect(
            0,
            self._indicator_y(self._drop_slot) - _INDICATOR_HEIGHT // 2,
            max(0, self.width() - 4),
            _INDICATOR_HEIGHT,
            _INDICATOR_HEIGHT / 2,
            _INDICATOR_HEIGHT / 2,
        )

        painter.end()

    def _scroll_area(self) -> QScrollArea | None:
        widget = self.parentWidget()

        while widget is not None:
            if isinstance(widget, QScrollArea):
                return widget

            widget = widget.parentWidget()

        return None

    def _scroll_bar(self):
        area = self._scroll_area()

        return area.verticalScrollBar() if area is not None else None

    def _set_autoscroll(self, step: int) -> None:
        self._autoscroll = step

        if step and not self._autoscroll_timer.isActive():
            self._autoscroll_timer.start()
        elif not step:
            self._autoscroll_timer.stop()

    def _on_autoscroll(self) -> None:
        bar = self._scroll_bar()

        if bar is None or not self._autoscroll:
            self._autoscroll_timer.stop()
            return

        bar.setValue(bar.value() + self._autoscroll)
