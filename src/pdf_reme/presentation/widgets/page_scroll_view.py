from bisect import bisect_right

import shiboken6

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

_MARGIN = 22
_SPACING = 20
_LABEL_HEIGHT = 22
_LABEL_GAP = 4
_IDENTITY_HEIGHT = 16

_MIN_ZOOM = 0.4
_MAX_ZOOM = 3.0
_ZOOM_STEP = 1.25

_MAX_FIT_WIDTH = 900
_MAX_RENDER_WIDTH = 2400
_RENDERS_PER_TICK = 2
_MAX_CACHED_PAGES = 10
_FLASH_MS = 900
_DEFAULT_PAGE_SIZE = (595.0, 842.0)


class PageSlot(QWidget):
    """Kaydırmalı görünümde tek sayfa: beyaz çerçeve + altında sayfa numarası."""

    clicked = Signal(int)

    def __init__(
        self,
        page_number: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.page_number = page_number

        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(_LABEL_GAP)

        self._frame = QLabel()
        self._frame.setObjectName("pageViewFrame")
        self._frame.setProperty("selected", False)
        self._frame.setProperty("flash", False)
        self._frame.setScaledContents(True)

        self._number = QLabel(str(page_number))
        self._number.setObjectName("pageViewNumber")
        self._number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._number.setFixedHeight(_LABEL_HEIGHT)

        self._identity = QLabel()
        self._identity.setObjectName("pageViewIdentity")
        self._identity.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._identity.setFixedHeight(_IDENTITY_HEIGHT)

        layout.addWidget(self._frame)
        layout.addWidget(self._number)
        layout.addWidget(self._identity)

    def set_identity_text(self, text: str) -> None:
        """Orijinal sayfa kimliği ikinci satırı; boşsa görünmez metin kalır
        (gürültü yok), ama yükseklik hesaplarını basit tutmak için satır
        yeri her sayfada aynı sabit boyutta ayrılır."""
        self._identity.setText(text)

    def set_page_size(self, width: int, height: int) -> None:
        self._frame.setFixedSize(width, height)
        self.setFixedSize(
            width,
            height
            + _LABEL_GAP
            + _LABEL_HEIGHT
            + _LABEL_GAP
            + _IDENTITY_HEIGHT,
        )

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._frame.setPixmap(pixmap)

    def has_pixmap(self) -> bool:
        return not self._frame.pixmap().isNull()

    def set_selected(self, selected: bool) -> None:
        self._set_frame_flag("selected", selected)

    def set_flash(self, flash: bool) -> None:
        self._set_frame_flag("flash", flash)

    def _set_frame_flag(self, name: str, value: bool) -> None:
        if bool(self._frame.property(name)) == value:
            return

        self._frame.setProperty(name, value)

        self._frame.style().unpolish(self._frame)
        self._frame.style().polish(self._frame)

    def mouseReleaseEvent(self, event) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            self.clicked.emit(self.page_number)

        super().mouseReleaseEvent(event)


class PageScrollView(QScrollArea):
    """PDF sayfalarını Acrobat gibi alt alta gösteren kaydırmalı görünüm.

    Yalnızca görünür alana yakın sayfalar çizilir; diğerleri beyaz çerçevedir.
    Zoom 1.0, "genişliğe sığdır" anlamına gelir.
    """

    page_clicked = Signal(int)
    current_page_changed = Signal(int)
    zoom_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setObjectName("pageScrollArea")
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setWidgetResizable(False)
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self._content = QWidget()
        self._content.setObjectName("pageScrollContent")
        self.setWidget(self._content)

        self._document: QPdfDocument | None = None
        self._slots: list[PageSlot] = []
        self._point_sizes: list[tuple[float, float]] = []
        self._offsets: list[int] = []
        self._rendered: dict[int, int] = {}
        self._selected: set[int] = set()
        self._identities: list[str] = []
        self._zoom = 1.0
        self._current = 0
        # `_apply_scroll`'un gecikmeli (`singleShot`) tekrarlarının, aradan
        # yeni bir `set_document`/`scroll_to` çağrısı geçtikten SONRA ateşleyip
        # eski hedefe geri sarmasını önlemek için kendi kendine yeten bir jeton.
        self._scroll_generation = 0

        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(0)
        self._render_timer.timeout.connect(self._render_tick)

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(60)
        self._resize_timer.timeout.connect(self._on_resized)

        self.verticalScrollBar().valueChanged.connect(self._on_scrolled)

    # ------------------------------------------------------------------
    # Genel arayüz
    # ------------------------------------------------------------------

    @property
    def zoom(self) -> float:
        return self._zoom

    @property
    def current_page(self) -> int:
        return self._current + 1 if self._slots else 0

    @property
    def page_count(self) -> int:
        return len(self._slots)

    def set_document(
        self,
        document: QPdfDocument | None,
        *,
        keep_scroll: bool = False,
        anchor: tuple[int, float] | None = None,
    ) -> None:
        """`anchor` = (sayfa no, sayfa içi oran); verilirse konum piksel
        yerine sayfa kimliğiyle (`scroll_position` çıktısı) geri yüklenir."""
        previous_scroll = self.verticalScrollBar().value()

        # Önceki durumdan kalmış gecikmeli `_apply_scroll` tekrarları artık
        # geçersiz; bu belge/durum için yeni bir nesil başlatılır.
        self._scroll_generation += 1

        self._document = document
        self._clear_slots()

        count = document.pageCount() if document is not None else 0

        for index in range(count):
            size = document.pagePointSize(index)

            if size.width() <= 0 or size.height() <= 0:
                self._point_sizes.append(_DEFAULT_PAGE_SIZE)
            else:
                self._point_sizes.append((size.width(), size.height()))

            slot = PageSlot(index + 1, self._content)
            slot.clicked.connect(self.page_clicked)
            slot.set_selected(index + 1 in self._selected)
            slot.show()

            self._slots.append(slot)
            self._apply_identity(slot)

        self._current = min(self._current, max(0, count - 1))

        self._relayout()

        if anchor is not None:
            self._restore_anchor((max(0, anchor[0] - 1), anchor[1]))
        else:
            self.verticalScrollBar().setValue(
                previous_scroll if keep_scroll else 0
            )

            if not keep_scroll:
                self._current = 0

        self._update_current()
        self._schedule_render()

    def scroll_position(self) -> tuple[int, float]:
        """Görünümün üst kenarındaki sayfa (1 tabanlı) + sayfa içi oran."""
        index, fraction = self._anchor()

        return index + 1, fraction

    def clear(self) -> None:
        self.set_document(None)

    def set_selection(self, selected: set[int]) -> None:
        self._selected = set(selected)

        for slot in self._slots:
            slot.set_selected(slot.page_number in self._selected)

    def set_identities(self, labels: list[str]) -> None:
        """`labels[i]`: (i+1). sayfanın ikinci satır metni (boş = gösterme).

        `set_document` slot'ları yeniden yarattığı için (`set_selection` ile
        aynı desen), değer burada saklanır ve slot oluşturulurken uygulanır.
        """
        self._identities = list(labels)

        for slot in self._slots:
            self._apply_identity(slot)

    def scroll_to(self, page: int, *, only_if_hidden: bool = False) -> None:
        index = page - 1

        if not 0 <= index < len(self._slots):
            return

        top = self._offsets[index]
        height = self._slots[index].height()

        value = self.verticalScrollBar().value()
        viewport_height = self.viewport().height()

        if only_if_hidden and (
            top >= value and top + height <= value + viewport_height
        ):
            return

        self._scroll_generation += 1
        self._apply_scroll(
            max(0, top - _MARGIN // 2), tries=3, generation=self._scroll_generation
        )

    def flash(self, pages) -> None:
        slots = [
            self._slots[page - 1]
            for page in pages
            if 1 <= page <= len(self._slots)
        ]

        for slot in slots:
            slot.set_flash(True)

        def clear_flash() -> None:
            for slot in slots:
                if shiboken6.isValid(slot):
                    slot.set_flash(False)

        QTimer.singleShot(_FLASH_MS, clear_flash)

    def zoom_in(self) -> None:
        self.set_zoom(self._zoom * _ZOOM_STEP)

    def zoom_out(self) -> None:
        self.set_zoom(self._zoom / _ZOOM_STEP)

    def zoom_fit(self) -> None:
        self.set_zoom(1.0)

    def set_zoom(self, zoom: float) -> None:
        zoom = min(_MAX_ZOOM, max(_MIN_ZOOM, zoom))

        if abs(zoom - self._zoom) < 1e-6:
            return

        self._zoom = zoom
        self._relayout_keeping_position()

        self.zoom_changed.emit(self._zoom)

    # ------------------------------------------------------------------
    # Yerleşim
    # ------------------------------------------------------------------

    def _apply_identity(self, slot: PageSlot) -> None:
        index = slot.page_number - 1

        slot.set_identity_text(
            self._identities[index] if index < len(self._identities) else ""
        )

    def _clear_slots(self) -> None:
        for slot in self._slots:
            slot.hide()
            slot.setParent(None)
            slot.deleteLater()

        self._slots = []
        self._point_sizes = []
        self._offsets = []
        self._rendered = {}

    def _fit_width(self) -> int:
        available = self.viewport().width() - 2 * _MARGIN

        return max(160, min(available, _MAX_FIT_WIDTH))

    def _relayout(self) -> None:
        viewport = self.viewport().size()

        if not self._slots:
            self._offsets = []
            self._content.resize(viewport)
            return

        max_point_width = max(width for width, _ in self._point_sizes) or 1.0
        fit = self._fit_width() * self._zoom

        y = _MARGIN
        widest = 0
        offsets: list[int] = []

        for slot, (point_width, point_height) in zip(
            self._slots, self._point_sizes
        ):
            width = max(48, round(fit * point_width / max_point_width))
            height = max(48, round(width * point_height / point_width))

            slot.set_page_size(width, height)

            offsets.append(y)
            widest = max(widest, width)

            y += slot.height() + _SPACING

        self._offsets = offsets

        content_width = max(viewport.width(), widest + 2 * _MARGIN)
        content_height = max(y - _SPACING + _MARGIN, viewport.height())

        self._content.resize(content_width, content_height)

        for slot, offset in zip(self._slots, offsets):
            slot.move((content_width - slot.width()) // 2, offset)

    def _anchor(self) -> tuple[int, float]:
        if not self._slots:
            return 0, 0.0

        value = self.verticalScrollBar().value()
        index = max(
            0, bisect_right(self._offsets, value + _SPACING // 2) - 1
        )

        height = max(1, self._slots[index].height())

        return index, (value - self._offsets[index]) / height

    def _restore_anchor(self, anchor: tuple[int, float]) -> None:
        index, fraction = anchor

        if not self._slots:
            return

        index = min(index, len(self._slots) - 1)

        self.verticalScrollBar().setValue(
            round(
                self._offsets[index]
                + fraction * self._slots[index].height()
            )
        )

    def _relayout_keeping_position(self) -> None:
        anchor = self._anchor()

        self._relayout()
        self._restore_anchor(anchor)

        self._update_current()
        self._schedule_render()

    def _apply_scroll(self, target: int, tries: int, generation: int) -> None:
        if generation != self._scroll_generation:
            return

        bar = self.verticalScrollBar()
        bar.setValue(target)

        if bar.value() != target and tries > 0:
            QTimer.singleShot(
                30,
                lambda: shiboken6.isValid(self)
                and self._apply_scroll(target, tries - 1, generation),
            )

    def _on_resized(self) -> None:
        if self._slots:
            self._relayout_keeping_position()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

        self._resize_timer.start()

    def showEvent(self, event) -> None:
        super().showEvent(event)

        self._resize_timer.start()

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()

            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()

            event.accept()
            return

        super().wheelEvent(event)

    # ------------------------------------------------------------------
    # Geçerli sayfa + tembel çizim
    # ------------------------------------------------------------------

    def _on_scrolled(self, _value: int) -> None:
        self._update_current()
        self._schedule_render()

    def _update_current(self) -> None:
        if not self._slots:
            return

        center = (
            self.verticalScrollBar().value() + self.viewport().height() // 2
        )

        index = max(
            0,
            min(
                len(self._slots) - 1,
                bisect_right(self._offsets, center) - 1,
            ),
        )

        if index != self._current:
            self._current = index
            self.current_page_changed.emit(index + 1)

    def _schedule_render(self) -> None:
        if not self._render_timer.isActive():
            self._render_timer.start()

    def _target_width(self, index: int) -> int:
        dpr = self.devicePixelRatioF()

        return min(
            _MAX_RENDER_WIDTH,
            max(1, round(self._slots[index].width() * dpr)),
        )

    def _render_tick(self) -> None:
        document = self._document

        if (
            document is None
            or not shiboken6.isValid(document)
            or not self._slots
        ):
            return

        bar = self.verticalScrollBar()
        viewport_height = self.viewport().height()

        near_top = bar.value() - viewport_height
        near_bottom = bar.value() + 2 * viewport_height
        center = bar.value() + viewport_height // 2

        pending = []

        for index, slot in enumerate(self._slots):
            top = self._offsets[index]
            bottom = top + slot.height()

            if bottom < near_top or top > near_bottom:
                continue

            if self._rendered.get(index) != self._target_width(index):
                distance = abs((top + bottom) // 2 - center)
                pending.append((distance, index))

        pending.sort()

        for _, index in pending[:_RENDERS_PER_TICK]:
            self._render_page(document, index)

        self._evict(center, viewport_height)

        if len(pending) > _RENDERS_PER_TICK:
            self._schedule_render()

    def _render_page(self, document: QPdfDocument, index: int) -> None:
        width = self._target_width(index)

        point_width, point_height = self._point_sizes[index]
        height = max(1, round(width * point_height / point_width))

        image = document.render(index, QSize(width, height))

        if image.isNull():
            self._rendered[index] = width
            return

        self._slots[index].set_pixmap(QPixmap.fromImage(image))

        self._rendered[index] = width

    def _evict(self, center: int, viewport_height: int) -> None:
        keep = 3 * viewport_height

        def distance(index: int) -> int:
            slot = self._slots[index]

            return abs(self._offsets[index] + slot.height() // 2 - center)

        for index in [
            index for index in self._rendered if distance(index) > keep
        ]:
            self._slots[index].set_pixmap(QPixmap())
            del self._rendered[index]

        while len(self._rendered) > _MAX_CACHED_PAGES:
            farthest = max(self._rendered, key=distance)

            self._slots[farthest].set_pixmap(QPixmap())
            del self._rendered[farthest]
