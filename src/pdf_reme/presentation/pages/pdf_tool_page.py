import logging
from pathlib import Path

import qtawesome as qta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation import backend_gateway
from pdf_reme.presentation.backend_gateway import OperationError, PdfInfo
from pdf_reme.presentation.document_format import (
    format_document_meta,
    format_file_size,
    type_icon,
)
from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager
from pdf_reme.presentation.widgets.app_dialog import AppDialog, DialogItem
from pdf_reme.presentation.widgets.busy_overlay import BusyOverlay
from pdf_reme.presentation.widgets.file_drop_area import DropOverlay
from pdf_reme.presentation.widgets.pdf_picker_dialog import PdfPickerDialog
from pdf_reme.presentation.widgets.reorderable_list import move_item
from pdf_reme.presentation.widgets.task_runner import TaskRunner

logger = logging.getLogger(__name__)


def _local_pdf_paths_from_mime(mime_data) -> list[str]:
    if not mime_data.hasUrls():
        return []

    return [
        url.toLocalFile()
        for url in mime_data.urls()
        if url.isLocalFile() and Path(url.toLocalFile()).is_file()
    ]


class PdfToolPage(QWidget):
    """Birleştir / Böl / Sıkıştır / Şifreleme sayfalarının ortak iskeleti.

    Boş ekran (Dosya Seç + Kütüphaneden Seç), sürükle-bırak, arka plan
    işi + meşgul katmanı, hata ve sonuç diyalogları burada; her araç yalnız
    kendi seçenek alanlarını (`_build_content`) ve işlemini yazar.

    Alt sınıf çeviri anahtarları: `{KEY}.description`, `{KEY}.drop_title`,
    `{KEY}.drop_hint`, `{KEY}.error_title`; başlık `sidebar.nav.{KEY}`.
    """

    page_requested = Signal(str)
    document_open_requested = Signal(str)

    KEY = ""
    MULTIPLE = False
    ICON = "fa5s.file-pdf"
    ACCENT = "blue"
    # Şifreli PDF'in seçilmesine izin verilir mi (yalnız Şifreleme sayfası).
    ALLOW_ENCRYPTED = False

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._language_manager = get_language_manager()
        self._theme_manager = get_theme_manager()

        self._paths: list[str] = []
        self._infos: dict[str, PdfInfo] = {}

        self._runner = TaskRunner(self)
        self._runner.succeeded.connect(self._on_succeeded)
        self._runner.errored.connect(self._on_errored)
        self._runner.progressed.connect(self._on_progressed)

        self.setAcceptDrops(True)

        self._init_state()
        self._setup_shell()

        self._drop_overlay = DropOverlay(
            self,
            title_key="tool.drop_overlay_title",
            body_key=(
                "tool.drop_overlay_body_multi"
                if self.MULTIPLE
                else "tool.drop_overlay_body_single"
            ),
        )
        self._busy_overlay = BusyOverlay(self)

        self.retranslate_ui()
        self.apply_theme()

    # ------------------------------------------------------------------
    # Alt sınıf kancaları
    # ------------------------------------------------------------------

    def _init_state(self) -> None:
        """Alt sınıf durumu; arayüz kurulmadan önce çağrılır."""

    def _build_content(self) -> QWidget:
        raise NotImplementedError

    def _refresh_content(self) -> None:
        """Dosya listesi/seçenekler değiştiğinde içeriği tazeler."""

    def _retranslate_content(self) -> None:
        """Alt sınıfa özgü metinleri çevirir."""

    def _apply_content_theme(self) -> None:
        """Alt sınıfa özgü ikonları tema rengiyle yeniler."""

    def _on_files_changed(self) -> None:
        """Seçili dosya kümesi değişti (ekleme/çıkarma/temizleme)."""

    def _handle_result(self, result) -> None:
        raise NotImplementedError

    def _handle_error_reason(self, reason: str) -> bool:
        """Özel hata işleme; True dönerse genel hata diyaloğu gösterilmez."""
        return False

    # ------------------------------------------------------------------
    # Kabuk
    # ------------------------------------------------------------------

    def _setup_shell(self) -> None:
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
        self._stack.addWidget(self._build_content())

        layout.addLayout(self._stack, 1)

    def _build_empty_state(self) -> QWidget:
        page = QWidget()

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        self._drop_zone = QFrame()
        self._drop_zone.setObjectName("opDropZone")

        zone_layout = QVBoxLayout(self._drop_zone)
        zone_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone_layout.setSpacing(10)

        self._drop_icon_label = QLabel()
        self._drop_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._drop_title_label = QLabel()
        self._drop_title_label.setObjectName("opDropZoneTitle")
        self._drop_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._drop_hint_label = QLabel()
        self._drop_hint_label.setObjectName("opDropZoneHint")
        self._drop_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_hint_label.setWordWrap(True)

        self._pick_button = QPushButton()
        self._pick_button.setObjectName("opPrimaryButton")
        self._pick_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pick_button.clicked.connect(self._on_pick_file)

        self._pick_library_button = QPushButton()
        self._pick_library_button.setObjectName("opSecondaryButton")
        self._pick_library_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pick_library_button.clicked.connect(self._on_pick_library)

        pick_row = QHBoxLayout()
        pick_row.setSpacing(10)
        pick_row.addStretch(1)
        pick_row.addWidget(self._pick_button)
        pick_row.addWidget(self._pick_library_button)
        pick_row.addStretch(1)

        zone_layout.addStretch(1)
        zone_layout.addWidget(self._drop_icon_label)
        zone_layout.addWidget(self._drop_title_label)
        zone_layout.addWidget(self._drop_hint_label)
        zone_layout.addSpacing(8)
        zone_layout.addLayout(pick_row)
        zone_layout.addStretch(1)

        page_layout.addWidget(self._drop_zone, 1)

        return page

    # ------------------------------------------------------------------
    # Ortak yapı taşları (alt sınıflar kullanır)
    # ------------------------------------------------------------------

    def _make_line_edit(self) -> QLineEdit:
        edit = QLineEdit()
        edit.setObjectName("opInput")
        edit.setFixedHeight(38)

        return edit

    def _make_field(self, editor: QWidget) -> tuple[QWidget, QLabel]:
        """Başlıklı alan; (kapsayıcı, başlık etiketi) döner."""
        container = QWidget()

        column = QVBoxLayout(container)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)

        caption = QLabel()
        caption.setObjectName("opFieldLabel")

        column.addWidget(caption)
        column.addWidget(editor)

        return container, caption

    def _make_segment(
        self,
        keys: tuple[str, ...],
    ) -> tuple[QWidget, QLabel, dict[str, QPushButton]]:
        """Segment kontrolü; (kapsayıcı, başlık, {anahtar: düğme}) döner."""
        container = QWidget()

        column = QVBoxLayout(container)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)

        caption = QLabel()
        caption.setObjectName("opFieldLabel")

        group = QButtonGroup(container)
        group.setExclusive(True)

        segment_row = QHBoxLayout()
        segment_row.setSpacing(0)

        buttons: dict[str, QPushButton] = {}

        for position, key in enumerate(keys):
            button = QPushButton()
            button.setObjectName("opSegment")

            if position == 0:
                segment = "first"
            elif position == len(keys) - 1:
                segment = "last"
            else:
                segment = "middle"

            button.setProperty("segmentPosition", segment)
            button.setCheckable(True)
            button.setChecked(position == 0)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

            group.addButton(button)
            segment_row.addWidget(button)

            buttons[key] = button

        segment_row.addStretch(1)

        column.addWidget(caption)
        column.addLayout(segment_row)

        return container, caption, buttons

    def _icon_button(
        self,
        icon_name: str,
        callback,
        *,
        enabled: bool = True,
    ) -> QPushButton:
        button = QPushButton()
        button.setObjectName("opIconButton")
        button.setFixedSize(30, 30)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setIcon(
            qta.icon(icon_name, color=self._theme_manager.icon_color())
        )
        button.setEnabled(enabled)
        button.clicked.connect(callback)

        return button

    def _repolish(self, widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _info_text(self, path: str) -> str:
        """Satır ayrıntısı: '12 sayfa · 1.2 MB' ya da 'Şifreli · 1.2 MB'."""
        tr = self._language_manager.tr
        info = self._infos.get(path)

        if info is None:
            return ""

        size = format_file_size(info.size)

        if info.encrypted:
            return f"{tr('tool.encrypted_label')}  •  {size}"

        return f"{tr('document.meta.pages').format(count=info.page_count)}  •  {size}"

    def _build_file_row(
        self,
        path: str,
        *,
        index: int = 0,
        count: int = 1,
        movable: bool = False,
        on_remove=None,
    ) -> QWidget:
        icon_name, accent = type_icon("pdf")

        row = QFrame()
        row.setObjectName("opFileRow")
        row.setFixedHeight(56)

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(14, 0, 10, 0)
        row_layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setPixmap(
            qta.icon(
                icon_name,
                color=self._theme_manager.accent_hex(accent),
            ).pixmap(22, 22)
        )

        name_label = QLabel(Path(path).name)
        name_label.setObjectName("opFileName")

        detail = self._info_text(path)

        detail_label = QLabel(
            f"{index + 1}.  {detail}" if movable else detail
        )
        detail_label.setObjectName("opFileDetail")

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(1)
        text_column.addStretch(1)
        text_column.addWidget(name_label)
        text_column.addWidget(detail_label)
        text_column.addStretch(1)

        row_layout.addWidget(icon_label)
        row_layout.addLayout(text_column, 1)

        if movable:
            row_layout.addWidget(
                self._icon_button(
                    "fa5s.chevron-up",
                    lambda: self._move_file(index, -1),
                    enabled=index > 0,
                )
            )
            row_layout.addWidget(
                self._icon_button(
                    "fa5s.chevron-down",
                    lambda: self._move_file(index, 1),
                    enabled=index < count - 1,
                )
            )

        row_layout.addWidget(
            self._icon_button(
                "fa5s.times",
                on_remove or (lambda: self._remove_file(index)),
            )
        )

        return row

    # ------------------------------------------------------------------
    # i18n / tema
    # ------------------------------------------------------------------

    def retranslate_ui(self) -> None:
        tr = self._language_manager.tr

        self._title_label.setText(tr(f"sidebar.nav.{self.KEY}"))
        self._description_label.setText(tr(f"{self.KEY}.description"))

        self._drop_title_label.setText(tr(f"{self.KEY}.drop_title"))
        self._drop_hint_label.setText(tr(f"{self.KEY}.drop_hint"))
        self._pick_button.setText(tr("tool.pick_file"))
        self._pick_library_button.setText(tr("tool.pick_library"))

        if hasattr(self, "_drop_overlay"):
            self._drop_overlay.retranslate_ui()

        self._retranslate_content()
        self._refresh()

    def apply_theme(self) -> None:
        self._drop_icon_label.setPixmap(
            qta.icon(
                self.ICON,
                color=self._theme_manager.accent_hex(self.ACCENT),
            ).pixmap(44, 44)
        )

        self._pick_button.setIcon(qta.icon("fa5s.folder-open", color="#FFFFFF"))
        self._pick_library_button.setIcon(
            qta.icon("fa5s.book", color=self._theme_manager.icon_color())
        )

        if hasattr(self, "_drop_overlay"):
            self._drop_overlay.apply_theme()

        if hasattr(self, "_busy_overlay"):
            self._busy_overlay.apply_theme()

        self._apply_content_theme()
        self._refresh()

    def _refresh(self) -> None:
        self._stack.setCurrentIndex(1 if self._paths else 0)
        self._refresh_content()

    # ------------------------------------------------------------------
    # Dosya seçme / ekleme
    # ------------------------------------------------------------------

    def _on_pick_file(self) -> None:
        if self._runner.is_running:
            return

        title = self._language_manager.tr("tool.dialog_title")

        if self.MULTIPLE:
            paths, _ = QFileDialog.getOpenFileNames(
                self, title, "", "PDF (*.pdf)"
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, title, "", "PDF (*.pdf)"
            )
            paths = [path] if path else []

        if paths:
            self._add_paths(paths)

    def _on_pick_library(self) -> None:
        if self._runner.is_running:
            return

        tr = self._language_manager.tr
        documents = backend_gateway.fetch_library_documents()

        if self.MULTIPLE:
            paths = PdfPickerDialog.pick_many(
                self,
                documents=documents,
                types=("pdf",),
                title=tr("tool.library_title_multi"),
                body=tr("tool.library_body_multi"),
            )
        else:
            path = PdfPickerDialog.pick(
                self,
                documents=documents,
                title=tr("tool.library_title"),
                body=tr("tool.library_body"),
            )
            paths = [path] if path else []

        if paths:
            self._add_paths(paths)

    def _add_paths(self, paths: list[str]) -> None:
        if self._runner.is_running:
            return

        tr = self._language_manager.tr

        accepted: list[str] = []
        rejected: list[DialogItem] = []

        for path in paths:
            if path in self._paths or path in accepted:
                continue

            reason = self._reject_reason(path)

            if reason is None:
                accepted.append(path)
            else:
                rejected.append(
                    DialogItem(
                        name=Path(path).name,
                        detail=reason,
                        icon_name="fa5s.ban",
                        accent="red",
                    )
                )

        if rejected:
            AppDialog.inform(
                self,
                title=tr("tool.rejected_title"),
                body=tr("tool.rejected_body"),
                variant="danger",
                icon_name="fa5s.ban",
                items=rejected,
            )

        if not accepted:
            return

        if self.MULTIPLE:
            self._paths.extend(accepted)
        else:
            self._paths = [accepted[0]]

            self._infos = {
                key: value
                for key, value in self._infos.items()
                if key == accepted[0]
            }

        self._on_files_changed()
        self._refresh()

    def _reject_reason(self, path: str) -> str | None:
        """Dosya kabul edilmezse kullanıcıya gösterilecek gerekçe."""
        tr = self._language_manager.tr

        if Path(path).suffix.lower() != ".pdf":
            return tr("library.upload_unsupported")

        try:
            info = backend_gateway.inspect_pdf(path)

        except OperationError as error:
            return tr(f"op.error.{error.reason}")

        if info.encrypted and not self.ALLOW_ENCRYPTED:
            return tr(f"tool.reject.encrypted.{self.KEY}")

        self._infos[path] = info

        return None

    def _remove_file(self, index: int) -> None:
        if self._runner.is_running:
            return

        if 0 <= index < len(self._paths):
            self._infos.pop(self._paths[index], None)
            del self._paths[index]

            self._on_files_changed()
            self._refresh()

    def _move_file(self, index: int, offset: int) -> None:
        target = index + offset

        if 0 <= target < len(self._paths):
            self._paths[index], self._paths[target] = (
                self._paths[target],
                self._paths[index],
            )
            self._refresh()

    def _reorder_file(self, source: int, slot: int) -> None:
        """Sürükle-bırak: `_paths` okların kullandığı aynı listedir."""
        if self._runner.is_running:
            return

        self._paths[:] = move_item(self._paths, source, slot)
        self._refresh()

    def clear_files(self) -> None:
        self._paths.clear()
        self._infos.clear()

        self._on_files_changed()
        self._refresh()

    # ------------------------------------------------------------------
    # Arka plan işi, hata, sonuç
    # ------------------------------------------------------------------

    def _run_task(
        self,
        task,
        busy_text: str,
        *,
        with_progress: bool = False,
    ) -> bool:
        if not self._runner.run(task, progress=with_progress):
            return False

        self._busy_overlay.show_busy(busy_text, with_progress=with_progress)
        self._refresh()

        return True

    def _on_progressed(self, percent: int, text: str) -> None:
        self._busy_overlay.set_progress(percent, text)

    def _on_succeeded(self, result) -> None:
        self._busy_overlay.hide_busy()

        self._handle_result(result)

    def _on_errored(self, error) -> None:
        self._busy_overlay.hide_busy()

        if isinstance(error, OperationError):
            reason = error.reason
        else:
            logger.error(
                "%s işlemi beklenmedik şekilde başarısız oldu: %s",
                self.KEY,
                type(error).__name__,
            )
            reason = "unknown"

        if not self._handle_error_reason(reason):
            tr = self._language_manager.tr

            AppDialog.inform(
                self,
                title=tr(f"{self.KEY}.error_title"),
                body=tr(f"op.error.{reason}"),
                variant="danger",
                icon_name="fa5s.exclamation",
            )

        self._refresh()

    def _show_result(
        self,
        *,
        title: str,
        body: str,
        documents,
        variant: str = "success",
        icon_name: str = "fa5s.check",
        view_on_confirm: bool = False,
    ) -> None:
        tr = self._language_manager.tr

        items = []

        for document in documents:
            item_icon, accent = type_icon(document.document_type)

            items.append(
                DialogItem(
                    name=document.display_name,
                    detail=format_document_meta(
                        document, date=document.created_at
                    ),
                    icon_name=item_icon,
                    accent=accent,
                )
            )

        action = AppDialog.choose(
            self,
            title=title,
            body=body,
            confirm_text=tr("edit.view" if view_on_confirm else "dialog.ok"),
            extra_actions=[
                ("reveal", tr("common.show_in_folder")),
                ("library", tr("convert.show_in_library")),
            ],
            variant=variant,
            icon_name=icon_name,
            items=items,
            confirm_action="view" if view_on_confirm else None,
        )

        if action == "view":
            self.document_open_requested.emit(documents[0].id)
        elif action == "reveal":
            self._reveal(documents[0].stored_path)
        elif action == "library":
            self.page_requested.emit("library")

    def _reveal(self, path: str) -> None:
        try:
            backend_gateway.reveal_in_folder(path)

        except OperationError:
            tr = self._language_manager.tr

            AppDialog.inform(
                self,
                title=tr("op.error.reveal_failed_title"),
                body=tr("op.error.reveal_failed"),
                variant="danger",
            )

    def shutdown(self) -> None:
        self._runner.wait()

    # ------------------------------------------------------------------
    # Sürükle-bırak
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

        if hasattr(self, "_drop_overlay"):
            self._drop_overlay.setGeometry(self.rect())

        if hasattr(self, "_busy_overlay") and self._busy_overlay.isVisible():
            self._busy_overlay.setGeometry(self.rect())

    def _can_accept_drop(self, mime_data) -> bool:
        return not self._runner.is_running and bool(
            _local_pdf_paths_from_mime(mime_data)
        )

    def dragEnterEvent(self, event) -> None:
        if self._can_accept_drop(event.mimeData()):
            event.acceptProposedAction()

            self._drop_overlay.setGeometry(self.rect())
            self._drop_overlay.raise_()
            self._drop_overlay.show()

            return

        event.ignore()

    def dragMoveEvent(self, event) -> None:
        if self._can_accept_drop(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._drop_overlay.hide()

        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        self._drop_overlay.hide()

        paths = _local_pdf_paths_from_mime(event.mimeData())

        if not paths:
            event.ignore()
            return

        event.acceptProposedAction()

        self._add_paths(paths)
