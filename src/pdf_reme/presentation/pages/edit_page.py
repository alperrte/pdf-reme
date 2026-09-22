import logging
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import qtawesome as qta
import shiboken6

from PySide6.QtCore import QCoreApplication, QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation import backend_gateway
from pdf_reme.presentation.backend_gateway import (
    EditOperation,
    OperationError,
)
from pdf_reme.presentation.document_format import (
    format_document_meta,
    type_icon,
)
from pdf_reme.presentation.edit_page_labels import identity_label
from pdf_reme.presentation.edit_page_map import (
    PageIdentity,
    PageMap,
    apply_identity_step,
    build_page_map,
    initial_identities,
)
from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager
from pdf_reme.presentation.widgets.app_dialog import AppDialog, DialogItem
from pdf_reme.presentation.widgets.busy_overlay import BusyOverlay
from pdf_reme.presentation.widgets.file_drop_area import DropOverlay
from pdf_reme.presentation.widgets.page_scroll_view import PageScrollView
from pdf_reme.presentation.widgets.page_thumbnail_grid import (
    THUMB_HEIGHT,
    THUMB_WIDTH,
    PageThumbnailGrid,
    render_page_thumbnail,
)
from pdf_reme.presentation.widgets.pdf_page_select_dialog import (
    PdfPageSelectDialog,
)
from pdf_reme.presentation.widgets.pdf_picker_dialog import PdfPickerDialog
from pdf_reme.presentation.widgets.task_runner import TaskRunner

logger = logging.getLogger(__name__)

_THUMBS_PER_TICK = 4
_BUSY_DELAY_MS = 250
_STRIP_WIDTH = THUMB_WIDTH + 34
# `_finish_restore`'un şeridin gerçek yüksekliğinin beklenen değere
# ulaşmasını bekleme deneme sınırı (bkz. `_finish_restore`).
_MAX_RESTORE_ATTEMPTS = 6

# `_start_step` odak parametresi: verilmezse seçilecek ilk sayfa kullanılır.
_AUTO_FOCUS = -1


@dataclass(frozen=True)
class _StepRecord:
    """Bir düzenleme adımının bağlam bilgisi (undo/redo'da geri yüklenir)."""

    page_map: PageMap
    selection_before: frozenset[int]
    selection_after: frozenset[int]
    identities_before: tuple[PageIdentity, ...]
    identities_after: tuple[PageIdentity, ...]


def _local_pdf_from_mime(mime_data) -> str | None:
    if not mime_data.hasUrls():
        return None

    for url in mime_data.urls():
        if not url.isLocalFile():
            continue

        path = Path(url.toLocalFile())

        if path.is_file() and path.suffix.lower() == ".pdf":
            return str(path)

    return None


class EditPage(QWidget):
    """Mevcut bir PDF üzerinde çok işlemli sayfa düzenleme.

    İşlemler geçici bir çalışma klasöründe adım adım uygulanır; kaynak PDF'e
    dokunulmaz ve kütüphaneye yalnızca "Kaydet"te tek bir çıktı eklenir.
    """

    document_open_requested = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._language_manager = get_language_manager()
        self._theme_manager = get_theme_manager()

        self._source_path: str | None = None
        self._workspace: Path | None = None

        # states[0] kaynak, states[i] i. işlemden sonraki geçici PDF.
        self._states: list[str] = []
        self._ops: list[EditOperation] = []
        self._records: list[_StepRecord] = []
        self._cursor = 0

        self._page_count = 0
        self._selected: set[int] = set()
        self._anchor: int | None = None
        self._notice = ""
        self._page_identities: tuple[PageIdentity, ...] = ()

        self._pdf_document = QPdfDocument(self)
        self._render_queue: list[int] = []

        self._job: str | None = None
        self._pending_selection: set[int] = set()
        self._pending_operation: EditOperation | None = None
        self._pending_output = ""
        self._pending_notice = ""
        self._pending_focus: int | None = None
        self._pending_flash: tuple[int, ...] = ()
        self._pending_record: _StepRecord | None = None
        self._busy_text = ""

        # Yenileme sırasında (thumbnail'ler yeniden kurulurken) şeridin
        # konumu, yerleşim tamamlanmadan bozulmasın diye bastırılır.
        self._restoring = False
        self._restore_generation = 0

        self._runner = TaskRunner(self)
        self._runner.succeeded.connect(self._on_job_succeeded)
        self._runner.errored.connect(self._on_job_errored)

        self._busy_timer = QTimer(self)
        self._busy_timer.setSingleShot(True)
        self._busy_timer.timeout.connect(self._show_busy)

        self.setAcceptDrops(True)

        self._setup_ui()

        self._drop_overlay = DropOverlay(
            self,
            title_key="edit.drop_hint_title",
            body_key="edit.drop_hint_body",
        )
        self._busy_overlay = BusyOverlay(self)

        self.retranslate_ui()
        self.apply_theme()
        self._update_controls()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 34, 42, 34)
        layout.setSpacing(8)

        self._title_label = QLabel()
        self._title_label.setObjectName("pageTitle")

        self._description_label = QLabel()
        self._description_label.setObjectName("pageDescription")
        self._description_label.setWordWrap(True)

        layout.addWidget(self._title_label)
        layout.addWidget(self._description_label)
        layout.addSpacing(18)

        self._stack = QStackedLayout()
        self._stack.addWidget(self._build_empty_state())
        self._stack.addWidget(self._build_editor_state())

        layout.addLayout(self._stack, 1)

    def _build_empty_state(self) -> QWidget:
        page = QWidget()

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        zone = QFrame()
        zone.setObjectName("opDropZone")

        zone_layout = QVBoxLayout(zone)
        zone_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone_layout.setSpacing(10)

        self._empty_icon_label = QLabel()
        self._empty_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._empty_title_label = QLabel()
        self._empty_title_label.setObjectName("opDropZoneTitle")
        self._empty_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._empty_hint_label = QLabel()
        self._empty_hint_label.setObjectName("opDropZoneHint")
        self._empty_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_hint_label.setWordWrap(True)

        self._pick_button = QPushButton()
        self._pick_button.setObjectName("opPrimaryButton")
        self._pick_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pick_button.clicked.connect(self._on_pick_file)

        self._pick_library_button = QPushButton()
        self._pick_library_button.setObjectName("opSecondaryButton")
        self._pick_library_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pick_library_button.clicked.connect(self._on_pick_source)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        button_row.addStretch(1)
        button_row.addWidget(self._pick_button)
        button_row.addWidget(self._pick_library_button)
        button_row.addStretch(1)

        zone_layout.addStretch(1)
        zone_layout.addWidget(self._empty_icon_label)
        zone_layout.addWidget(self._empty_title_label)
        zone_layout.addWidget(self._empty_hint_label)
        zone_layout.addSpacing(8)
        zone_layout.addLayout(button_row)
        zone_layout.addStretch(1)

        page_layout.addWidget(zone, 1)

        return page

    def _build_editor_state(self) -> QWidget:
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Kaynak çubuğu: dosya bilgisi, kaynak değiştir, geri al / yinele
        source_row = QHBoxLayout()
        source_row.setSpacing(10)

        self._source_chip = QFrame()
        self._source_chip.setObjectName("editSourceChip")

        chip_layout = QHBoxLayout(self._source_chip)
        chip_layout.setContentsMargins(12, 6, 14, 6)
        chip_layout.setSpacing(8)

        self._source_icon_label = QLabel()
        self._source_name_label = QLabel()
        self._source_name_label.setObjectName("editSourceName")
        self._source_meta_label = QLabel()
        self._source_meta_label.setObjectName("opHint")

        chip_layout.addWidget(self._source_icon_label)
        chip_layout.addWidget(self._source_name_label)
        chip_layout.addWidget(self._source_meta_label)

        self._change_source_button = QPushButton()
        self._change_source_button.setObjectName("opSecondaryButton")
        self._change_source_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._change_source_button.clicked.connect(self._on_new)

        self._select_all_button = QPushButton()
        self._select_all_button.setObjectName("opSecondaryButton")
        self._select_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._select_all_button.clicked.connect(self._on_select_all)

        self._move_left_button = self._tool_button(lambda: self._move(-1))
        self._move_right_button = self._tool_button(lambda: self._move(1))

        self._undo_button = self._tool_button(self._on_undo)
        self._redo_button = self._tool_button(self._on_redo)

        source_row.addWidget(self._source_chip)
        source_row.addWidget(self._change_source_button)
        source_row.addStretch(1)
        source_row.addWidget(self._select_all_button)
        source_row.addWidget(self._move_left_button)
        source_row.addWidget(self._move_right_button)
        source_row.addSpacing(6)
        source_row.addWidget(self._undo_button)
        source_row.addWidget(self._redo_button)

        layout.addLayout(source_row)

        # Sayfa araçları
        tools_row = QHBoxLayout()
        tools_row.setSpacing(6)

        self._rotate_left_button = self._tool_button(
            lambda: self._rotate(-90)
        )
        self._rotate_right_button = self._tool_button(
            lambda: self._rotate(90)
        )
        self._delete_button = self._tool_button(self._delete, danger=True)
        self._duplicate_button = self._tool_button(self._duplicate)
        self._blank_button = self._tool_button(self._insert_blank)
        self._insert_button = self._tool_button(self._insert_from_pdf)

        for button in (
            self._rotate_left_button,
            self._rotate_right_button,
            self._delete_button,
            self._duplicate_button,
            self._blank_button,
            self._insert_button,
        ):
            tools_row.addWidget(button)

        tools_row.addStretch(1)

        layout.addLayout(tools_row)

        # Gövde: solda sayfa şeridi, sağda alt alta kaydırmalı büyük sayfalar
        body_row = QHBoxLayout()
        body_row.setSpacing(14)

        self._grid_scroll = QScrollArea()
        self._grid_scroll.setObjectName("editStripScroll")
        self._grid_scroll.setWidgetResizable(True)
        self._grid_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._grid_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._grid_scroll.setFixedWidth(_STRIP_WIDTH)

        self._grid = PageThumbnailGrid(single_column=True)
        self._grid.page_clicked.connect(self._on_strip_clicked)
        self._grid.page_dropped.connect(self._on_page_dropped)

        grid_holder = QWidget()
        grid_holder.setObjectName("editStripContent")

        self._grid_holder = grid_holder

        holder_layout = QVBoxLayout(grid_holder)
        holder_layout.setContentsMargins(4, 4, 4, 4)
        holder_layout.addWidget(self._grid)
        holder_layout.addStretch(1)

        self._grid_scroll.setWidget(grid_holder)

        viewer_column = QVBoxLayout()
        viewer_column.setSpacing(8)

        viewer_bar = QHBoxLayout()
        viewer_bar.setSpacing(6)

        self._page_indicator = QLabel()
        self._page_indicator.setObjectName("editPageIndicator")

        self._zoom_out_button = self._tool_button(lambda: self._view.zoom_out())
        self._zoom_in_button = self._tool_button(lambda: self._view.zoom_in())
        self._zoom_fit_button = self._tool_button(lambda: self._view.zoom_fit())

        viewer_bar.addWidget(self._page_indicator)
        viewer_bar.addStretch(1)
        viewer_bar.addWidget(self._zoom_out_button)
        viewer_bar.addWidget(self._zoom_in_button)
        viewer_bar.addWidget(self._zoom_fit_button)

        self._view = PageScrollView()
        self._view.page_clicked.connect(self._on_page_clicked)
        self._view.current_page_changed.connect(self._on_current_page_changed)

        viewer_column.addLayout(viewer_bar)
        viewer_column.addWidget(self._view, 1)

        body_row.addWidget(self._grid_scroll)
        body_row.addLayout(viewer_column, 1)

        layout.addLayout(body_row, 1)

        # Alt çubuk: durum + çıktı adı + Kaydet
        bottom_card = QFrame()
        bottom_card.setObjectName("opCard")

        bottom_layout = QHBoxLayout(bottom_card)
        bottom_layout.setContentsMargins(18, 12, 18, 12)
        bottom_layout.setSpacing(12)

        self._status_label = QLabel()
        self._status_label.setObjectName("opHint")

        self._name_input = QLineEdit()
        self._name_input.setObjectName("opInput")
        self._name_input.setFixedHeight(38)
        self._name_input.setMinimumWidth(240)

        self._save_button = QPushButton()
        self._save_button.setObjectName("opPrimaryButton")
        self._save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_button.clicked.connect(self._on_save_clicked)

        bottom_layout.addWidget(self._status_label, 1)
        bottom_layout.addWidget(self._name_input)
        bottom_layout.addWidget(self._save_button)

        layout.addWidget(bottom_card)

        return page

    def _tool_button(
        self,
        callback,
        *,
        danger: bool = False,
    ) -> QPushButton:
        button = QPushButton()
        button.setObjectName("editToolButton")
        button.setProperty("danger", danger)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(callback)

        return button

    # ------------------------------------------------------------------
    # i18n / tema
    # ------------------------------------------------------------------

    def retranslate_ui(self) -> None:
        tr = self._language_manager.tr

        self._title_label.setText(tr("sidebar.nav.edit"))
        self._description_label.setText(tr("edit.description"))

        self._empty_title_label.setText(tr("edit.empty_title"))
        self._empty_hint_label.setText(tr("edit.empty_hint"))
        self._pick_button.setText(tr("edit.pick_file"))
        self._pick_library_button.setText(tr("edit.pick_source"))
        self._change_source_button.setText(tr("edit.new"))

        self._set_tool_text(self._rotate_left_button, "edit.tool.rotate_left")
        self._set_tool_text(self._rotate_right_button, "edit.tool.rotate_right")
        self._set_tool_text(self._delete_button, "edit.tool.delete")
        self._set_tool_text(self._duplicate_button, "edit.tool.duplicate")
        self._set_tool_text(
            self._move_left_button, "edit.tool.move_up", icon_only=True
        )
        self._set_tool_text(
            self._move_right_button, "edit.tool.move_down", icon_only=True
        )
        self._set_tool_text(
            self._zoom_out_button, "edit.zoom.out", icon_only=True
        )
        self._set_tool_text(
            self._zoom_in_button, "edit.zoom.in", icon_only=True
        )
        self._set_tool_text(self._zoom_fit_button, "edit.zoom.fit")
        self._set_tool_text(self._blank_button, "edit.tool.blank")
        self._set_tool_text(self._insert_button, "edit.tool.insert")
        self._set_tool_text(self._undo_button, "edit.undo")
        self._set_tool_text(self._redo_button, "edit.redo")

        self._save_button.setText(tr("edit.save"))
        self._name_input.setPlaceholderText(tr("edit.name_placeholder"))

        if hasattr(self, "_drop_overlay"):
            self._drop_overlay.retranslate_ui()

        if hasattr(self, "_grid"):
            self._update_controls()

    def _set_tool_text(
        self,
        button: QPushButton,
        key: str,
        *,
        icon_only: bool = False,
    ) -> None:
        text = self._language_manager.tr(key)

        # Yazısı olan düğmede tooltip aynı metni tekrarlar; yalnızca
        # metinsiz (ikon) düğmelerde gösterilir.
        button.setToolTip(text if icon_only else "")
        button.setText("" if icon_only else text)

    def apply_theme(self) -> None:
        accent = self._theme_manager.accent_hex("blue")
        icon_color = self._theme_manager.icon_color()
        danger_color = self._theme_manager.accent_hex("red")

        self._empty_icon_label.setPixmap(
            qta.icon("fa5s.edit", color=accent).pixmap(44, 44)
        )
        self._source_icon_label.setPixmap(
            qta.icon(
                "fa5s.file-pdf",
                color=self._theme_manager.accent_hex("red"),
            ).pixmap(16, 16)
        )

        self._pick_button.setIcon(qta.icon("fa5s.folder-open", color="#FFFFFF"))
        self._pick_library_button.setIcon(qta.icon("fa5s.book", color=icon_color))
        self._save_button.setIcon(qta.icon("fa5s.save", color="#FFFFFF"))

        self._change_source_button.setIcon(
            qta.icon("fa5s.file-medical", color=icon_color)
        )
        self._select_all_button.setIcon(
            qta.icon("fa5s.check-double", color=icon_color)
        )

        icons = {
            self._rotate_left_button: "fa5s.undo-alt",
            self._rotate_right_button: "fa5s.redo-alt",
            self._duplicate_button: "fa5s.clone",
            self._move_left_button: "fa5s.arrow-up",
            self._move_right_button: "fa5s.arrow-down",
            self._zoom_out_button: "fa5s.search-minus",
            self._zoom_in_button: "fa5s.search-plus",
            self._zoom_fit_button: "fa5s.arrows-alt-h",
            self._blank_button: "fa5s.file",
            self._insert_button: "fa5s.file-import",
            self._undo_button: "fa5s.reply",
            self._redo_button: "fa5s.share",
        }

        for button, icon_name in icons.items():
            button.setIcon(qta.icon(icon_name, color=icon_color))

        self._delete_button.setIcon(
            qta.icon("fa5s.trash-alt", color=danger_color)
        )

        if hasattr(self, "_drop_overlay"):
            self._drop_overlay.apply_theme()

        if hasattr(self, "_busy_overlay"):
            self._busy_overlay.apply_theme()

    # ------------------------------------------------------------------
    # Kaynak seçimi
    # ------------------------------------------------------------------

    def _on_pick_file(self) -> None:
        if self._runner.is_running or not self._confirm_discard():
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            self._language_manager.tr("edit.open_dialog_title"),
            "",
            "PDF (*.pdf)",
        )

        if path:
            self._open_source(path)

    def _on_pick_source(self) -> None:
        if self._runner.is_running or not self._confirm_discard():
            return

        tr = self._language_manager.tr

        path = PdfPickerDialog.pick(
            self,
            documents=backend_gateway.fetch_library_documents(),
            title=tr("edit.picker_title"),
            body=tr("edit.picker_body"),
        )

        if path:
            self._open_source(path)

    def _on_new(self) -> None:
        if self._runner.is_running or not self._confirm_discard():
            return

        self._reset_editor()

    def _confirm_discard(self) -> bool:
        if not self._is_dirty():
            return True

        tr = self._language_manager.tr

        return AppDialog.ask(
            self,
            title=tr("edit.discard_title"),
            body=tr("edit.discard_body"),
            confirm_text=tr("edit.discard_confirm"),
            variant="danger",
            icon_name="fa5s.exclamation-triangle",
        )

    def _open_source(self, path: str) -> None:
        tr = self._language_manager.tr

        try:
            page_count = backend_gateway.read_pdf_page_count(path)

        except OperationError as error:
            self._show_error(error.reason)
            return

        self._reset_editor()

        self._workspace = backend_gateway.new_edit_workspace()
        self._source_path = path
        self._states = [path]
        self._ops = []
        self._records = []
        self._cursor = 0
        self._selected = set()
        self._page_identities = initial_identities(page_count)

        self._name_input.setText(f"{Path(path).stem}{tr('edit.name_suffix')}")

        self._stack.setCurrentIndex(1)

        self._load_current_state(keep_scroll=False, focus=1)

    def _release_document(self) -> None:
        # Qt, close() sonrası da nesne yok edilene kadar dosyayı kilitli tutar;
        # geçici klasörün silinebilmesi için belge yeniden oluşturulur.
        self._pdf_document.close()

        shiboken6.delete(self._pdf_document)

        self._pdf_document = QPdfDocument(self)

    def _reset_editor(self) -> None:
        self._render_queue.clear()

        self._view.clear()
        self._release_document()

        backend_gateway.discard_edit_workspace(self._workspace)

        self._workspace = None
        self._source_path = None
        self._states = []
        self._ops = []
        self._records = []
        self._cursor = 0
        self._page_count = 0
        self._selected = set()
        self._anchor = None
        self._notice = ""
        self._page_identities = ()

        self._grid.set_page_count(0)
        self._stack.setCurrentIndex(0)

        self._update_controls()

    def _is_dirty(self) -> bool:
        return self._cursor > 0

    # ------------------------------------------------------------------
    # Önizleme (küçük resimler)
    # ------------------------------------------------------------------

    def _load_current_state(
        self,
        *,
        keep_scroll: bool = True,
        focus: int | None = None,
        flash: tuple[int, ...] = (),
        anchor: tuple[int, float] | None = None,
    ) -> None:
        """Geçerli durumu yükler ve kullanıcının bağlamını geri getirir.

        `anchor`: büyük görünümün (sayfa no, sayfa içi oran) konumu; verilmezse
        piksel konumu korunur. `focus`: gizliyse görünür yapılacak sayfa.
        """
        self._render_queue.clear()
        self._pdf_document.close()

        error = self._pdf_document.load(self._states[self._cursor])

        if error != QPdfDocument.Error.None_:
            self._restoring = False
            self._page_count = 0
            self._grid.set_page_count(0)
            self._view.clear()
            self._update_controls()

            self._show_error("corrupt_pdf")
            return

        self._page_count = self._pdf_document.pageCount()

        self._selected = {
            page for page in self._selected if page <= self._page_count
        }

        strip_scroll = self._grid_scroll.verticalScrollBar().value()

        # Thumbnail'ler yeniden yaratılırken yerleşim henüz yapılmadığından
        # şerit konumu, yenileme bitene kadar (`_finish_restore`) bastırılır.
        self._restoring = True
        self._restore_generation += 1
        generation = self._restore_generation

        self._grid.set_page_count(self._page_count)
        self._grid.set_selection(self._selected)

        labels = self._identity_labels()
        self._grid.set_identities(labels)
        self._view.set_identities(labels)

        self._grid_scroll.verticalScrollBar().setValue(strip_scroll)

        self._view.set_selection(self._selected)
        self._view.set_document(
            self._pdf_document, keep_scroll=keep_scroll, anchor=anchor
        )

        self._render_queue = list(range(self._page_count))

        QTimer.singleShot(0, self._render_batch)

        if focus is not None:
            focus = min(max(1, focus), max(1, self._page_count))

            self._view.scroll_to(focus, only_if_hidden=True)

        if flash:
            self._view.flash(
                [page for page in flash if 1 <= page <= self._page_count]
            )

        self._update_controls()

        QTimer.singleShot(
            0,
            lambda: self._finish_restore(generation, strip_scroll, focus),
        )

    def _finish_restore(
        self,
        generation: int,
        strip_scroll: int,
        focus: int | None,
        attempt: int = 0,
    ) -> None:
        """Yeni thumbnail'ler yerleştikten sonra şerit konumunu geri getirir.

        Sayfa SAYISI değişen işlemlerde (sil/kopyala/boş-sayfa-ekle) şeridin
        gerçek içerik yüksekliği ve dolayısıyla kaydırma çubuğunun aralığı,
        `QGridLayout`'un yeniden yerleşimi tamamlanana kadar güncel olmayabilir
        — bu yüzden sabit tek seferlik bir gecikme yerine, gerçek yükseklik
        beklenen değere ulaşana kadar (üst sınırlı) yeniden denenir. Sayfa
        sayısı değişmeyen işlemlerde (döndür/sırala) beklenen yükseklik zaten
        ilk denemede karşılanır, bu yüzden onlarda gözle görülür bir gecikme
        olmaz.
        """
        if generation != self._restore_generation or not shiboken6.isValid(
            self
        ):
            return

        self._grid.layout().activate()
        self._grid_holder.layout().activate()

        QCoreApplication.sendPostedEvents(None, QEvent.Type.LayoutRequest)

        ready = self._grid.height() >= self._grid.expected_height()

        if not ready and attempt < _MAX_RESTORE_ATTEMPTS:
            QTimer.singleShot(
                0,
                lambda: self._finish_restore(
                    generation, strip_scroll, focus, attempt + 1
                ),
            )
            return

        self._restoring = False

        self._grid_scroll.verticalScrollBar().setValue(strip_scroll)

        if focus is not None:
            self._ensure_strip_visible(focus)

    def _render_batch(self) -> None:
        for _ in range(_THUMBS_PER_TICK):
            if not self._render_queue:
                return

            index = self._render_queue.pop(0)

            if index >= len(self._grid.thumbs):
                continue

            pixmap = render_page_thumbnail(self._pdf_document, index)

            if pixmap is not None:
                self._grid.thumbs[index].set_pixmap(pixmap)

        if self._render_queue:
            QTimer.singleShot(0, self._render_batch)

    # ------------------------------------------------------------------
    # Seçim
    # ------------------------------------------------------------------

    def _on_page_clicked(self, page_number: int, modifiers=None) -> None:
        """Düz tık: yalnızca bu sayfa. Ctrl: ekle/çıkar. Shift: aralık."""
        if self._runner.is_running:
            return

        if modifiers is None:
            modifiers = QGuiApplication.keyboardModifiers()

        ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)

        if shift and self._anchor is not None:
            low, high = sorted((self._anchor, page_number))
            selection = set(range(low, high + 1))

            if ctrl:
                selection |= self._selected

        elif ctrl:
            selection = set(self._selected)
            selection ^= {page_number}
            self._anchor = page_number

        else:
            selection = (
                set() if self._selected == {page_number} else {page_number}
            )
            self._anchor = page_number

        self._notice = ""
        self._apply_selection(selection)

    def _on_strip_clicked(self, page_number: int) -> None:
        self._on_page_clicked(page_number)

        if not self._runner.is_running:
            self._view.scroll_to(page_number)

    def _on_select_all(self) -> None:
        if len(self._selected) == self._page_count:
            selection = set()
        else:
            selection = set(range(1, self._page_count + 1))

        self._anchor = None
        self._notice = ""
        self._apply_selection(selection)

    def _apply_selection(self, selection: set[int]) -> None:
        self._selected = selection

        self._grid.set_selection(selection)
        self._view.set_selection(selection)

        self._update_controls()

    def _on_current_page_changed(self, page_number: int) -> None:
        self._ensure_strip_visible(page_number)
        self._update_page_indicator()

    def _ensure_strip_visible(self, page_number: int) -> None:
        if self._restoring:
            return

        thumbs = self._grid.thumbs

        if not 1 <= page_number <= len(thumbs):
            return

        offset = self._grid.expected_offset(page_number - 1)

        if offset is None:
            self._grid_scroll.ensureWidgetVisible(
                thumbs[page_number - 1], 0, 24
            )
            return

        # `ensureWidgetVisible`, hedef widget'ın GERÇEK `geometry()`'sine
        # bakar; şerit az önce yeniden kurulduysa bu değer henüz Qt tarafından
        # hesaplanmamış olabilir (bkz. `_finish_restore`). Konumu, layout'un
        # kendi zamanlamasına bağlı kalmadan burada analitik hesaplıyoruz.
        holder_margin_top = (
            self._grid_holder.layout().contentsMargins().top()
        )
        top = offset + holder_margin_top
        bottom = top + THUMB_HEIGHT
        margin = 24

        scrollbar = self._grid_scroll.verticalScrollBar()
        viewport_height = self._grid_scroll.viewport().height()
        value = scrollbar.value()

        if top - margin < value:
            scrollbar.setValue(max(0, top - margin))
        elif bottom + margin > value + viewport_height:
            scrollbar.setValue(bottom + margin - viewport_height)

    def _update_page_indicator(self) -> None:
        tr = self._language_manager.tr

        current = self._view.current_page

        self._page_indicator.setText(
            tr("edit.page_indicator").format(
                current=current, total=self._page_count
            )
            if current
            else ""
        )

    # ------------------------------------------------------------------
    # Düzenleme işlemleri (kuyruğa alınır)
    # ------------------------------------------------------------------

    def _selected_pages(self) -> list[int]:
        return sorted(self._selected)

    def _identity_labels(self) -> list[str]:
        tr = self._language_manager.tr

        return [
            identity_label(identity, position, tr)
            for position, identity in enumerate(
                self._page_identities, start=1
            )
        ]

    def _insertion_point(self) -> int:
        return max(self._selected) if self._selected else self._page_count

    def _count_notice(self, kind: str, pages: list[int]) -> str:
        tr = self._language_manager.tr

        if len(pages) == 1:
            return tr(f"edit.notice.{kind}_one").format(page=pages[0])

        return tr(f"edit.notice.{kind}_many").format(count=len(pages))

    def _rotate(self, degrees: int) -> None:
        if not self._selected:
            return

        pages = self._selected_pages()

        self._start_step(
            EditOperation(
                "rotate_pages",
                {
                    "page_numbers": pages,
                    "degrees": degrees,
                },
            ),
            keep_selection=set(self._selected),
            notice=self._count_notice(
                "rotate_right" if degrees > 0 else "rotate_left", pages
            ),
            focus=None,
            flash=tuple(pages),
        )

    def _delete(self) -> None:
        if not self._selected:
            return

        pages = self._selected_pages()

        self._start_step(
            EditOperation(
                "delete_pages",
                {"page_numbers": pages},
            ),
            notice=self._count_notice("delete", pages),
        )

    def _duplicate(self) -> None:
        if not self._selected:
            return

        pages = self._selected_pages()

        # Her kopya, kaynağının hemen ardına eklenir.
        copies = tuple(page + offset + 1 for offset, page in enumerate(pages))

        self._start_step(
            EditOperation(
                "duplicate_pages",
                {"page_numbers": pages},
            ),
            notice=self._count_notice("duplicate", pages),
            flash=copies,
        )

    def _insert_blank(self) -> None:
        after = self._insertion_point()

        self._start_step(
            EditOperation(
                "insert_blank_page",
                {"after_page": after},
            ),
            notice=self._language_manager.tr("edit.notice.blank").format(
                page=after + 1
            ),
            flash=(after + 1,),
        )

    def _insert_from_pdf(self) -> None:
        tr = self._language_manager.tr

        path = PdfPickerDialog.pick(
            self,
            documents=backend_gateway.fetch_library_documents(),
            title=tr("edit.insert_picker_title"),
            body=tr("edit.insert_picker_body"),
        )

        if not path:
            return

        try:
            backend_gateway.read_pdf_page_count(path)

        except OperationError as error:
            self._show_error(error.reason)
            return

        selected_page = max(self._selected) if self._selected else None

        choice = PdfPageSelectDialog.pick(
            self,
            path,
            target_page_count=self._page_count,
            selected_page=selected_page,
        )

        if choice is None:
            return

        pages, after = choice

        first = after + 1
        added = tuple(range(first, first + len(pages)))

        if len(pages) == 1:
            notice = tr("edit.notice.insert_one").format(page=first)
        else:
            notice = tr("edit.notice.insert_many").format(
                count=len(pages), first=added[0], last=added[-1]
            )

        self._start_step(
            EditOperation(
                "insert_pages",
                {
                    "insert_pdf_path": path,
                    "source_page_numbers": pages,
                    "after_page": after,
                },
            ),
            notice=notice,
            flash=added,
        )

    def _move(self, direction: int) -> None:
        if not self._selected:
            return

        order = list(range(1, self._page_count + 1))

        if direction < 0:
            indexes = range(1, len(order))
        else:
            indexes = range(len(order) - 2, -1, -1)

        for index in indexes:
            neighbour = index + direction

            if order[index] in self._selected and (
                order[neighbour] not in self._selected
            ):
                order[index], order[neighbour] = (
                    order[neighbour],
                    order[index],
                )

        self._apply_order(order, set(self._selected), notice_kind="moved")

    def _on_page_dropped(
        self,
        moved_page: int,
        target_page: int,
        after: bool,
    ) -> None:
        if self._runner.is_running:
            return

        moved = (
            sorted(self._selected)
            if moved_page in self._selected
            else [moved_page]
        )

        if target_page in moved:
            return

        remaining = [
            page
            for page in range(1, self._page_count + 1)
            if page not in moved
        ]

        position = remaining.index(target_page) + (1 if after else 0)

        order = remaining[:position] + moved + remaining[position:]

        self._apply_order(order, set(moved), notice_kind="moved")

    def _apply_order(
        self,
        order: list[int],
        moved_pages: set[int],
        *,
        notice_kind: str = "moved",
    ) -> None:
        if order == list(range(1, self._page_count + 1)):
            return

        # Seçim, taşınan sayfaları yeni konumlarında izler.
        new_selection = {
            position + 1
            for position, page in enumerate(order)
            if page in moved_pages
        }

        ordered = sorted(new_selection)

        self._start_step(
            EditOperation("reorder_pages", {"page_order": order}),
            keep_selection=new_selection,
            notice=self._count_notice(notice_kind, ordered),
            focus=ordered[0],
            flash=tuple(ordered),
        )

    # ------------------------------------------------------------------
    # Geri al / yinele
    # ------------------------------------------------------------------

    def _on_undo(self) -> None:
        if self._runner.is_running or self._cursor <= 0:
            return

        operation = self._ops[self._cursor - 1]
        record = self._records[self._cursor - 1]

        anchor = self._mapped_view_position(record.page_map.backward)

        self._cursor -= 1
        self._selected = set(record.selection_before)
        self._anchor = None
        self._notice = self._history_notice("undo", operation)
        self._page_identities = record.identities_before

        self._load_current_state(
            focus=min(self._selected) if self._selected else None,
            anchor=anchor,
        )

    def _on_redo(self) -> None:
        if self._runner.is_running or self._cursor >= len(self._ops):
            return

        operation = self._ops[self._cursor]
        record = self._records[self._cursor]

        anchor = self._mapped_view_position(record.page_map.forward)

        self._cursor += 1
        self._selected = set(record.selection_after)
        self._anchor = None
        self._notice = self._history_notice("redo", operation)
        self._page_identities = record.identities_after

        self._load_current_state(
            focus=min(self._selected) if self._selected else None,
            anchor=anchor,
        )

    def _mapped_view_position(self, convert) -> tuple[int, float] | None:
        """Büyük görünümün konumunu, sayfa kimliğiyle yeni duruma eşler."""
        if not self._page_count:
            return None

        page, fraction = self._view.scroll_position()

        return convert(page), fraction

    def _history_notice(self, kind: str, operation: EditOperation) -> str:
        tr = self._language_manager.tr

        return tr(f"edit.notice.{kind}").format(
            action=tr(f"edit.op.{operation.name}")
        )

    # ------------------------------------------------------------------
    # Arka plan işleri
    # ------------------------------------------------------------------

    def _start_step(
        self,
        operation: EditOperation,
        keep_selection: set[int] | None = None,
        *,
        notice: str = "",
        focus: int | None = _AUTO_FOCUS,
        flash: tuple[int, ...] = (),
    ) -> None:
        """İşlemi arka planda başlatır.

        `keep_selection` verilmezse işleme uygun seçim hesaplanır (silmede
        komşu sayfa, ekleme/çoğaltmada yeni sayfalar). `focus` verilmezse
        seçilecek ilk sayfa, `None` ise hiçbir sayfa görünür yapılmaz.
        """
        if self._workspace is None or self._runner.is_running:
            return

        page_map = build_page_map(
            operation.name, operation.args, self._page_count
        )
        identities_after = apply_identity_step(
            self._page_identities, operation.name, operation.args
        )

        if keep_selection is None:
            keep_selection = self._selection_after(operation, page_map)

        if focus == _AUTO_FOCUS:
            focus = min(keep_selection) if keep_selection else None

        input_path = self._states[self._cursor]
        output_path = str(
            self._workspace / f"step_{uuid4().hex[:10]}.pdf"
        )

        self._job = "step"
        self._pending_operation = operation
        self._pending_output = output_path
        self._pending_selection = set(keep_selection)
        self._pending_record = _StepRecord(
            page_map,
            frozenset(self._selected),
            frozenset(keep_selection),
            self._page_identities,
            identities_after,
        )
        self._pending_notice = notice
        self._pending_focus = focus
        self._pending_flash = flash

        self._runner.run(
            lambda: backend_gateway.apply_edit_step(
                input_path, operation, output_path
            )
        )

        self._busy_text = self._language_manager.tr("edit.busy.step")
        self._busy_timer.start(_BUSY_DELAY_MS)
        self._update_controls()

    def _selection_after(
        self,
        operation: EditOperation,
        page_map: PageMap,
    ) -> set[int]:
        if operation.name == "delete_pages":
            neighbour = page_map.neighbour_after_delete(
                set(operation.args["page_numbers"])
            )

            return {neighbour} if neighbour else set()

        return set(page_map.inserted)

    def _on_save_clicked(self) -> None:
        if self._cursor < 1 or self._runner.is_running:
            return

        name = self._name_input.text().strip()
        input_path = self._states[self._cursor - 1]
        operation = self._ops[self._cursor - 1]

        self._job = "save"

        self._runner.run(
            lambda: backend_gateway.save_edit_result(
                input_path, operation, name
            )
        )

        self._busy_text = self._language_manager.tr("edit.busy.save")
        self._busy_timer.start(_BUSY_DELAY_MS)
        self._update_controls()

    def _show_busy(self) -> None:
        if self._runner.is_running:
            self._busy_overlay.show_busy(self._busy_text)

    def _finish_job(self) -> str | None:
        self._busy_timer.stop()
        self._busy_overlay.hide_busy()

        job = self._job
        self._job = None

        return job

    def _on_job_succeeded(self, result) -> None:
        job = self._finish_job()

        if job == "step":
            self._commit_step(str(result))
        elif job == "save":
            self._on_saved(result)

    def _commit_step(self, output_path: str) -> None:
        # Geri alındıktan sonra yeni işlem yapılırsa yinele zinciri atılır.
        for stale in self._states[self._cursor + 1:]:
            Path(stale).unlink(missing_ok=True)

        del self._states[self._cursor + 1:]
        del self._ops[self._cursor:]
        del self._records[self._cursor:]

        record = self._pending_record

        anchor = self._mapped_view_position(record.page_map.forward)

        self._states.append(output_path)
        self._ops.append(self._pending_operation)
        self._records.append(record)
        self._cursor += 1

        self._selected = self._pending_selection
        self._anchor = None
        self._notice = self._pending_notice
        self._page_identities = record.identities_after

        self._load_current_state(
            focus=self._pending_focus,
            flash=self._pending_flash,
            anchor=anchor,
        )

    def _on_saved(self, document) -> None:
        tr = self._language_manager.tr

        icon_name, accent = type_icon(document.document_type)

        action = AppDialog.choose(
            self,
            title=tr("edit.result_title"),
            body=tr("edit.result_body"),
            confirm_text=tr("dialog.ok"),
            extra_actions=[
                ("reveal", tr("common.show_in_folder")),
                ("view", tr("edit.view")),
            ],
            variant="success",
            icon_name="fa5s.check",
            items=[
                DialogItem(
                    name=document.display_name,
                    detail=format_document_meta(
                        document, date=document.created_at
                    ),
                    icon_name=icon_name,
                    accent=accent,
                )
            ],
        )

        self._reset_editor()

        if action == "reveal":
            try:
                backend_gateway.reveal_in_folder(document.stored_path)

            except OperationError as error:
                self._show_error(error.reason)

        elif action == "view":
            self.document_open_requested.emit(document.id)

    def _on_job_errored(self, error) -> None:
        job = self._finish_job()

        if isinstance(error, OperationError):
            reason = error.reason
        else:
            logger.exception(
                "PDF düzenleme beklenmedik şekilde başarısız oldu.",
                exc_info=error,
            )
            reason = "unknown"

        if job == "step":
            # Kısmen yazılmış adım dosyası kalmasın.
            Path(self._pending_output).unlink(missing_ok=True)

        self._show_error(reason)
        self._update_controls()

    def _show_error(self, reason: str) -> None:
        tr = self._language_manager.tr

        AppDialog.inform(
            self,
            title=tr("edit.error_title"),
            body=tr(f"op.error.{reason}"),
            variant="danger",
            icon_name="fa5s.exclamation",
        )

    # ------------------------------------------------------------------
    # Denetimlerin durumu
    # ------------------------------------------------------------------

    def _update_controls(self) -> None:
        tr = self._language_manager.tr

        editing = bool(self._states)
        idle = not self._runner.is_running
        has_selection = bool(self._selected)

        for button in (
            self._rotate_left_button,
            self._rotate_right_button,
            self._delete_button,
            self._duplicate_button,
            self._move_left_button,
            self._move_right_button,
        ):
            button.setEnabled(editing and idle and has_selection)

        if has_selection:
            self._move_left_button.setEnabled(
                idle and self._left_movable()
            )
            self._move_right_button.setEnabled(
                idle and self._right_movable()
            )

        self._blank_button.setEnabled(editing and idle)
        self._insert_button.setEnabled(editing and idle)
        self._change_source_button.setEnabled(editing and idle)
        self._select_all_button.setEnabled(editing and idle)

        self._undo_button.setEnabled(idle and self._cursor > 0)
        self._redo_button.setEnabled(idle and self._cursor < len(self._ops))

        self._save_button.setEnabled(idle and self._cursor > 0)
        self._name_input.setEnabled(idle and editing)

        all_selected = (
            self._page_count > 0 and len(self._selected) == self._page_count
        )
        self._select_all_button.setText(
            tr("edit.clear_selection" if all_selected else "edit.select_all")
        )

        if editing:
            self._source_name_label.setText(Path(self._source_path).name)
            self._source_meta_label.setText(
                tr("document.meta.pages").format(count=self._page_count)
            )

        self._status_label.setText(self._status_text())

        self._zoom_out_button.setEnabled(editing)
        self._zoom_in_button.setEnabled(editing)
        self._zoom_fit_button.setEnabled(editing)

        self._update_page_indicator()

    def _left_movable(self) -> bool:
        # En az bir seçili sayfanın solunda seçili olmayan sayfa var mı.
        return any(
            page - 1 >= 1 and (page - 1) not in self._selected
            for page in self._selected
        )

    def _right_movable(self) -> bool:
        return any(
            page + 1 <= self._page_count
            and (page + 1) not in self._selected
            for page in self._selected
        )

    def _status_text(self) -> str:
        tr = self._language_manager.tr

        parts = []

        if self._notice:
            parts.append(self._notice)

        if self._selected:
            parts.append(
                tr("edit.status.selected").format(count=len(self._selected))
            )
        elif self._states and not self._notice:
            parts.append(tr("edit.status.hint"))

        if self._cursor > 0:
            parts.append(
                tr("edit.status.changes").format(count=self._cursor)
            )

        return "   •   ".join(parts)

    def shutdown(self) -> None:
        self._runner.wait()
        self._release_document()

        backend_gateway.discard_edit_workspace(self._workspace)

        self._workspace = None

    # ------------------------------------------------------------------
    # Sürükle-bırak (PDF dosyası)
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

        if hasattr(self, "_drop_overlay"):
            self._drop_overlay.setGeometry(self.rect())

        if hasattr(self, "_busy_overlay") and self._busy_overlay.isVisible():
            self._busy_overlay.setGeometry(self.rect())

    def dragEnterEvent(self, event) -> None:
        if not self._runner.is_running and _local_pdf_from_mime(
            event.mimeData()
        ):
            event.acceptProposedAction()

            self._drop_overlay.setGeometry(self.rect())
            self._drop_overlay.raise_()
            self._drop_overlay.show()

            return

        event.ignore()

    def dragMoveEvent(self, event) -> None:
        if not self._runner.is_running and _local_pdf_from_mime(
            event.mimeData()
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._drop_overlay.hide()

        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        self._drop_overlay.hide()

        path = _local_pdf_from_mime(event.mimeData())

        if not path:
            event.ignore()
            return

        event.acceptProposedAction()

        if self._confirm_discard():
            self._open_source(path)
