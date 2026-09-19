import qtawesome as qta
import shiboken6

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager
from pdf_reme.presentation.widgets.page_thumbnail_grid import (
    THUMB_HEIGHT,
    PageThumbnailGrid,
    render_page_thumbnail,
)

_SHADOW_MARGIN = 26
_DIALOG_WIDTH = 720
_GRID_HEIGHT = 340
_GRID_COLUMNS = 4
_THUMBS_PER_TICK = 4


class PdfPageSelectDialog(QDialog):
    """Eklenecek PDF'in sayfalarını gösterir; seçilenleri ya da tümünü ekletir.

    Sonuç: (sayfa numaraları, hedef PDF'te hangi sayfadan sonra eklenecek).
    """

    def __init__(
        self,
        parent: QWidget | None,
        *,
        path: str,
        target_page_count: int,
        selected_page: int | None,
    ) -> None:
        super().__init__(parent)

        self._language_manager = get_language_manager()
        self._theme_manager = get_theme_manager()

        self._target_page_count = target_page_count
        self._selected_page = selected_page

        self._pages: set[int] = set()
        self._page_count = 0
        self._render_queue: list[int] = []

        self._result_pages: list[int] = []
        self._result_after = target_page_count

        self._document = QPdfDocument(self)
        self._document.load(path)

        self.setObjectName("appDialog")
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(_DIALOG_WIDTH + _SHADOW_MARGIN * 2)

        self._setup_ui()

        self._page_count = self._document.pageCount()
        self._grid.set_page_count(self._page_count)

        # Az sayfalı PDF'lerde boş alan bırakmamak için yükseklik sayfaya uyar.
        rows = -(-self._page_count // _GRID_COLUMNS)
        self._scroll.setFixedHeight(
            min(_GRID_HEIGHT, max(1, rows) * (THUMB_HEIGHT + 14) + 8)
        )

        self._render_queue = list(range(self._page_count))
        QTimer.singleShot(0, self._render_batch)

        self._update_controls()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        tr = self._language_manager.tr

        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            _SHADOW_MARGIN,
            _SHADOW_MARGIN,
            _SHADOW_MARGIN,
            _SHADOW_MARGIN,
        )

        card = QFrame()
        card.setObjectName("appDialogCard")

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(46)
        shadow.setXOffset(0)
        shadow.setYOffset(14)
        shadow.setColor(QColor(0, 0, 0, 90))
        card.setGraphicsEffect(shadow)

        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(0)

        title_label = QLabel(tr("edit.insert_dialog.title"))
        title_label.setObjectName("appDialogTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        body_label = QLabel(tr("edit.insert_dialog.body"))
        body_label.setObjectName("appDialogBody")
        body_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addSpacing(8)
        layout.addWidget(body_label)
        layout.addSpacing(14)

        # Seçim çubuğu
        select_row = QHBoxLayout()
        select_row.setSpacing(10)

        self._select_all_button = QPushButton()
        self._select_all_button.setObjectName("opSecondaryButton")
        self._select_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._select_all_button.setIcon(
            qta.icon(
                "fa5s.check-double",
                color=self._theme_manager.icon_color(),
            )
        )
        self._select_all_button.clicked.connect(self._on_select_all)

        self._count_label = QLabel()
        self._count_label.setObjectName("opHint")

        select_row.addWidget(self._select_all_button)
        select_row.addWidget(self._count_label, 1)

        layout.addLayout(select_row)
        layout.addSpacing(10)

        # Sayfa küçük resimleri
        scroll = QScrollArea()
        scroll.setObjectName("dashboardScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setFixedHeight(_GRID_HEIGHT)

        self._scroll = scroll

        self._grid = PageThumbnailGrid(draggable=False)
        self._grid.page_clicked.connect(self._on_page_clicked)

        holder = QWidget()
        holder.setObjectName("dashboardContent")

        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 4, 4, 0)
        holder_layout.addWidget(self._grid)
        holder_layout.addStretch(1)

        scroll.setWidget(holder)

        layout.addWidget(scroll)
        layout.addSpacing(14)

        # Ekleme konumu
        position_label = QLabel(tr("edit.insert_dialog.position"))
        position_label.setObjectName("opFieldLabel")

        layout.addWidget(position_label)
        layout.addSpacing(6)

        self._position_buttons: dict[str, QPushButton] = {}

        group = QButtonGroup(self)
        group.setExclusive(True)

        position_row = QHBoxLayout()
        position_row.setSpacing(0)

        options: list[tuple[str, str]] = []

        if self._selected_page:
            options.append(
                (
                    "after",
                    tr("edit.insert_dialog.after_page").format(
                        page=self._selected_page
                    ),
                )
            )

        options.append(("start", tr("edit.insert_dialog.at_start")))
        options.append(("end", tr("edit.insert_dialog.at_end")))

        for position, (key, text) in enumerate(options):
            button = QPushButton(text)
            button.setObjectName("opSegment")

            if position == 0:
                segment = "first"
            elif position == len(options) - 1:
                segment = "last"
            else:
                segment = "middle"

            button.setProperty("segmentPosition", segment)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

            group.addButton(button)
            position_row.addWidget(button)

            self._position_buttons[key] = button

        position_row.addStretch(1)

        default_key = "after" if self._selected_page else "end"
        self._position_buttons[default_key].setChecked(True)

        layout.addLayout(position_row)
        layout.addSpacing(18)

        # Düğmeler
        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        cancel_button = QPushButton(tr("dialog.cancel"))
        cancel_button.setObjectName("appDialogCancelButton")
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_button.clicked.connect(self.reject)

        self._add_all_button = QPushButton()
        self._add_all_button.setObjectName("appDialogCancelButton")
        self._add_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_all_button.clicked.connect(self._on_add_all)

        self._add_selected_button = QPushButton()
        self._add_selected_button.setObjectName("appDialogConfirmButton")
        self._add_selected_button.setProperty("variant", "primary")
        self._add_selected_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_selected_button.clicked.connect(self._on_add_selected)

        button_row.addWidget(cancel_button, 1)
        button_row.addWidget(self._add_all_button, 1)
        button_row.addWidget(self._add_selected_button, 1)

        layout.addLayout(button_row)

    # ------------------------------------------------------------------
    # Küçük resimler
    # ------------------------------------------------------------------

    def _render_batch(self) -> None:
        if not shiboken6.isValid(self._document):
            return

        for _ in range(_THUMBS_PER_TICK):
            if not self._render_queue:
                return

            index = self._render_queue.pop(0)

            if index >= len(self._grid.thumbs):
                continue

            pixmap = render_page_thumbnail(self._document, index)

            if pixmap is not None:
                self._grid.thumbs[index].set_pixmap(pixmap)

        if self._render_queue:
            QTimer.singleShot(0, self._render_batch)

    # ------------------------------------------------------------------
    # Seçim
    # ------------------------------------------------------------------

    def _on_page_clicked(self, page_number: int) -> None:
        if page_number in self._pages:
            self._pages.discard(page_number)
        else:
            self._pages.add(page_number)

        self._grid.set_selection(self._pages)
        self._update_controls()

    def _on_select_all(self) -> None:
        if len(self._pages) == self._page_count:
            self._pages = set()
        else:
            self._pages = set(range(1, self._page_count + 1))

        self._grid.set_selection(self._pages)
        self._update_controls()

    def _update_controls(self) -> None:
        tr = self._language_manager.tr

        selected = len(self._pages)

        self._count_label.setText(
            tr("edit.insert_dialog.selected").format(
                count=selected, total=self._page_count
            )
            if selected
            else tr("edit.insert_dialog.hint")
        )

        self._select_all_button.setText(
            tr(
                "edit.clear_selection"
                if self._page_count and selected == self._page_count
                else "edit.select_all"
            )
        )
        self._select_all_button.setEnabled(self._page_count > 0)

        self._add_all_button.setText(
            tr("edit.insert_dialog.add_all").format(count=self._page_count)
        )
        self._add_all_button.setEnabled(self._page_count > 0)

        self._add_selected_button.setText(
            tr("edit.insert_dialog.add_selected").format(count=selected)
            if selected
            else tr("edit.insert_dialog.add_selected_empty")
        )
        self._add_selected_button.setEnabled(selected > 0)

    # ------------------------------------------------------------------
    # Sonuç
    # ------------------------------------------------------------------

    def _after_page(self) -> int:
        if self._position_buttons.get("after") and (
            self._position_buttons["after"].isChecked()
        ):
            return self._selected_page

        if self._position_buttons["start"].isChecked():
            return 0

        return self._target_page_count

    def _on_add_all(self) -> None:
        self._result_pages = list(range(1, self._page_count + 1))
        self._result_after = self._after_page()

        self.accept()

    def _on_add_selected(self) -> None:
        if not self._pages:
            return

        self._result_pages = sorted(self._pages)
        self._result_after = self._after_page()

        self.accept()

    def done(self, result: int) -> None:
        self._render_queue.clear()

        # Qt, close() sonrası da nesne yok edilene kadar dosyayı kilitli tutar.
        if shiboken6.isValid(self._document):
            self._document.close()

            shiboken6.delete(self._document)

        super().done(result)

    def showEvent(self, event) -> None:
        super().showEvent(event)

        anchor = self.parentWidget()

        if anchor is not None:
            anchor = anchor.window()
            center = anchor.frameGeometry().center()

            geometry = self.frameGeometry()
            geometry.moveCenter(center)

            self.move(geometry.topLeft())

    @staticmethod
    def pick(
        parent: QWidget | None,
        path: str,
        *,
        target_page_count: int,
        selected_page: int | None = None,
    ) -> tuple[list[int], int] | None:
        dialog = PdfPageSelectDialog(
            parent,
            path=path,
            target_page_count=target_page_count,
            selected_page=selected_page,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        return dialog._result_pages, dialog._result_after
