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
    QScrollArea,
    QSpinBox,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.infrastructure.filesystem.file_validation import (
    SUPPORTED_EXTENSIONS,
)
from pdf_reme.presentation import backend_gateway
from pdf_reme.presentation.backend_gateway import (
    CONVERT_SUPPORTED_EXTENSIONS,
    ConvertRequest,
    OperationError,
)
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
from pdf_reme.presentation.widgets.task_runner import TaskRunner

logger = logging.getLogger(__name__)

# Algılanan tür -> rozet aksan rengi
_KIND_ACCENTS = {
    "images_to_pdf": "sky",
    "pdf_to_images": "red",
    "office_to_pdf": "blue",
    "mixed": "orange",
    "unsupported": "orange",
}

_KIND_ICONS = {
    "images_to_pdf": "fa5s.file-image",
    "pdf_to_images": "fa5s.file-pdf",
    "office_to_pdf": "fa5s.file-word",
    "mixed": "fa5s.exclamation-triangle",
    "unsupported": "fa5s.exclamation-triangle",
}

_CONVERTIBLE_KINDS = ("images_to_pdf", "pdf_to_images", "office_to_pdf")

_EXTENSION_TYPES = dict(SUPPORTED_EXTENSIONS)

_LIBRARY_TYPES = ("pdf", "image", "word", "powerpoint", "excel")


def _dialog_filter() -> str:
    extensions = " ".join(
        f"*{extension}" for extension in sorted(CONVERT_SUPPORTED_EXTENSIONS)
    )
    return f"{extensions} ({extensions})"


def _local_paths_from_mime(mime_data) -> list[str]:
    if not mime_data.hasUrls():
        return []

    return [
        url.toLocalFile()
        for url in mime_data.urls()
        if url.isLocalFile() and Path(url.toLocalFile()).is_file()
    ]


class ConvertPage(QWidget):
    """Dosya türünü otomatik algılayan tek dönüştürme sayfası.

    JPG/PNG → PDF, PDF → JPG ve Word/PowerPoint/Excel → PDF.
    """

    page_requested = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._language_manager = get_language_manager()
        self._theme_manager = get_theme_manager()

        self._paths: list[str] = []
        self._pdf_error: str | None = None
        self._pdf_page_count: int | None = None

        self._runner = TaskRunner(self)
        self._runner.succeeded.connect(self._on_succeeded)
        self._runner.errored.connect(self._on_errored)
        self._runner.progressed.connect(self._on_progressed)

        self.setAcceptDrops(True)

        self._setup_ui()

        self._drop_overlay = DropOverlay(
            self,
            title_key="convert.drop_hint_title",
            body_key="convert.drop_hint_body",
        )
        self._busy_overlay = BusyOverlay(self)

        self.retranslate_ui()
        self.apply_theme()
        self._refresh()

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
        self._stack.addWidget(self._build_files_state())

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
        self._pick_button.clicked.connect(self._on_pick_clicked)

        zone_layout.addStretch(1)
        zone_layout.addWidget(self._drop_icon_label)
        zone_layout.addWidget(self._drop_title_label)
        zone_layout.addWidget(self._drop_hint_label)
        zone_layout.addSpacing(8)

        self._pick_library_button = QPushButton()
        self._pick_library_button.setObjectName("opSecondaryButton")
        self._pick_library_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pick_library_button.clicked.connect(
            self._on_pick_library_clicked
        )

        pick_row = QHBoxLayout()
        pick_row.setSpacing(10)
        pick_row.addStretch(1)
        pick_row.addWidget(self._pick_button)
        pick_row.addWidget(self._pick_library_button)
        pick_row.addStretch(1)

        zone_layout.addLayout(pick_row)
        zone_layout.addStretch(1)

        page_layout.addWidget(self._drop_zone, 1)

        return page

    def _build_files_state(self) -> QWidget:
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Algılanan tür rozeti + araç düğmeleri
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self._kind_badge = QFrame()
        self._kind_badge.setObjectName("convertKindBadge")

        badge_layout = QHBoxLayout(self._kind_badge)
        badge_layout.setContentsMargins(12, 6, 14, 6)
        badge_layout.setSpacing(8)

        self._kind_icon_label = QLabel()
        self._kind_icon_label.setObjectName("convertKindIcon")

        self._kind_text_label = QLabel()
        self._kind_text_label.setObjectName("convertKindText")

        badge_layout.addWidget(self._kind_icon_label)
        badge_layout.addWidget(self._kind_text_label)

        self._kind_hint_label = QLabel()
        self._kind_hint_label.setObjectName("opHint")
        self._kind_hint_label.setWordWrap(True)

        self._add_button = QPushButton()
        self._add_button.setObjectName("opSecondaryButton")
        self._add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_button.clicked.connect(self._on_pick_clicked)

        self._library_button = QPushButton()
        self._library_button.setObjectName("opSecondaryButton")
        self._library_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._library_button.clicked.connect(self._on_pick_library_clicked)

        self._clear_button = QPushButton()
        self._clear_button.setObjectName("opSecondaryButton")
        self._clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_button.clicked.connect(self._on_clear_clicked)

        top_row.addWidget(self._kind_badge, 0)
        top_row.addWidget(self._kind_hint_label, 1)
        top_row.addWidget(self._add_button)
        top_row.addWidget(self._library_button)
        top_row.addWidget(self._clear_button)

        layout.addLayout(top_row)

        # Dosya listesi
        self._files_scroll = QScrollArea()
        self._files_scroll.setObjectName("dashboardScrollArea")
        self._files_scroll.setWidgetResizable(True)
        self._files_scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        files_content = QWidget()
        files_content.setObjectName("dashboardContent")

        self._files_layout = QVBoxLayout(files_content)
        self._files_layout.setContentsMargins(0, 0, 4, 0)
        self._files_layout.setSpacing(8)
        self._files_layout.addStretch(1)

        self._files_scroll.setWidget(files_content)

        layout.addWidget(self._files_scroll, 1)

        # Seçenekler
        self._options_card = QFrame()
        self._options_card.setObjectName("opCard")

        options_layout = QVBoxLayout(self._options_card)
        options_layout.setContentsMargins(18, 16, 18, 16)
        options_layout.setSpacing(12)

        self._warning_label = QLabel()
        self._warning_label.setObjectName("opWarning")
        self._warning_label.setWordWrap(True)

        options_layout.addWidget(self._warning_label)

        fields_row = QHBoxLayout()
        fields_row.setSpacing(14)

        self._name_field = self._build_field(
            self._make_line_edit(), "_name_caption"
        )
        self._name_input: QLineEdit = self._name_field[1]

        self._range_field = self._build_field(
            self._make_line_edit(), "_range_caption"
        )
        self._range_input: QLineEdit = self._range_field[1]

        self._dpi_spin = self._make_spin(72, 600, 150, " DPI")
        self._dpi_field = self._build_field(self._dpi_spin, "_dpi_caption")

        self._quality_spin = self._make_spin(1, 100, 90, " %")
        self._quality_field = self._build_field(
            self._quality_spin, "_quality_caption"
        )

        fields_row.addWidget(self._name_field[0], 3)
        fields_row.addWidget(self._range_field[0], 3)
        fields_row.addWidget(self._dpi_field[0], 2)
        fields_row.addWidget(self._quality_field[0], 2)

        options_layout.addLayout(fields_row)

        self._combine_field, self._combine_buttons = self._build_segment_field(
            "_combine_caption", ("separate", "single")
        )
        self._page_mode_field, self._page_mode_buttons = (
            self._build_segment_field("_page_mode_caption", ("a4", "original"))
        )

        for buttons in (self._combine_buttons, self._page_mode_buttons):
            for button in buttons.values():
                button.clicked.connect(self._refresh)

        segments_row = QHBoxLayout()
        segments_row.setSpacing(24)
        segments_row.addWidget(self._combine_field)
        segments_row.addWidget(self._page_mode_field)
        segments_row.addStretch(1)

        options_layout.addLayout(segments_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self._summary_label = QLabel()
        self._summary_label.setObjectName("opHint")

        self._convert_button = QPushButton()
        self._convert_button.setObjectName("opPrimaryButton")
        self._convert_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._convert_button.clicked.connect(self._on_convert_clicked)

        action_row.addWidget(self._summary_label, 1)
        action_row.addWidget(self._convert_button)

        options_layout.addLayout(action_row)

        layout.addWidget(self._options_card)

        return page

    def _build_segment_field(
        self,
        caption_attribute: str,
        keys: tuple[str, str],
    ) -> tuple[QWidget, dict[str, QPushButton]]:
        container = QWidget()

        column = QVBoxLayout(container)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)

        caption = QLabel()
        caption.setObjectName("opFieldLabel")

        setattr(self, caption_attribute, caption)

        group = QButtonGroup(container)
        group.setExclusive(True)

        segment_row = QHBoxLayout()
        segment_row.setSpacing(0)

        buttons: dict[str, QPushButton] = {}

        for position, key in enumerate(keys):
            button = QPushButton()
            button.setObjectName("opSegment")
            button.setProperty(
                "segmentPosition", "first" if position == 0 else "last"
            )
            button.setCheckable(True)
            button.setChecked(position == 0)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

            group.addButton(button)
            segment_row.addWidget(button)

            buttons[key] = button

        column.addWidget(caption)
        column.addLayout(segment_row)

        return container, buttons

    def _make_line_edit(self) -> QLineEdit:
        edit = QLineEdit()
        edit.setObjectName("opInput")
        edit.setFixedHeight(38)

        return edit

    def _make_spin(
        self,
        minimum: int,
        maximum: int,
        value: int,
        suffix: str,
    ) -> QSpinBox:
        spin = QSpinBox()
        spin.setObjectName("opInput")
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSuffix(suffix)
        spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        spin.setFixedHeight(38)

        return spin

    def _build_field(
        self,
        editor: QWidget,
        caption_attribute: str,
    ) -> tuple[QWidget, QWidget]:
        container = QWidget()

        column = QVBoxLayout(container)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)

        caption = QLabel()
        caption.setObjectName("opFieldLabel")

        setattr(self, caption_attribute, caption)

        column.addWidget(caption)
        column.addWidget(editor)

        return container, editor

    # ------------------------------------------------------------------
    # i18n / tema
    # ------------------------------------------------------------------

    def retranslate_ui(self) -> None:
        tr = self._language_manager.tr

        self._title_label.setText(tr("sidebar.nav.convert"))
        self._description_label.setText(tr("convert.description"))

        self._drop_title_label.setText(tr("convert.drop_title"))
        self._drop_hint_label.setText(tr("convert.drop_hint"))
        self._pick_button.setText(tr("convert.pick_files"))
        self._pick_library_button.setText(tr("convert.pick_library"))
        self._library_button.setText(tr("convert.pick_library"))

        self._add_button.setText(tr("convert.add_files"))
        self._clear_button.setText(tr("convert.clear"))
        self._convert_button.setText(tr("convert.run"))

        self._name_caption.setText(tr("convert.field.name"))
        self._range_caption.setText(tr("convert.field.range"))
        self._dpi_caption.setText(tr("convert.field.dpi"))
        self._quality_caption.setText(tr("convert.field.quality"))

        self._combine_caption.setText(tr("convert.combine.caption"))
        self._combine_buttons["separate"].setText(
            tr("convert.combine.separate")
        )
        self._combine_buttons["single"].setText(tr("convert.combine.single"))

        self._page_mode_caption.setText(tr("convert.page_mode.caption"))
        self._page_mode_buttons["a4"].setText(tr("convert.page_mode.a4"))
        self._page_mode_buttons["original"].setText(
            tr("convert.page_mode.original")
        )

        if hasattr(self, "_drop_overlay"):
            self._drop_overlay.retranslate_ui()

        if hasattr(self, "_paths"):
            self._refresh()

    def apply_theme(self) -> None:
        self._drop_icon_label.setPixmap(
            qta.icon(
                "fa5s.exchange-alt",
                color=self._theme_manager.accent_hex("blue"),
            ).pixmap(44, 44)
        )

        self._pick_button.setIcon(qta.icon("fa5s.folder-open", color="#FFFFFF"))
        self._convert_button.setIcon(qta.icon("fa5s.sync-alt", color="#FFFFFF"))

        icon_color = self._theme_manager.icon_color()

        self._add_button.setIcon(qta.icon("fa5s.plus", color=icon_color))
        self._library_button.setIcon(qta.icon("fa5s.book", color=icon_color))
        self._pick_library_button.setIcon(
            qta.icon("fa5s.book", color=icon_color)
        )
        self._clear_button.setIcon(qta.icon("fa5s.times", color=icon_color))

        if hasattr(self, "_drop_overlay"):
            self._drop_overlay.apply_theme()

        if hasattr(self, "_busy_overlay"):
            self._busy_overlay.apply_theme()

        if hasattr(self, "_paths"):
            self._refresh()

    # ------------------------------------------------------------------
    # Durum / görünüm
    # ------------------------------------------------------------------

    def _kind(self) -> str:
        return backend_gateway.detect_convert_kind(self._paths)

    def _refresh(self) -> None:
        tr = self._language_manager.tr

        if not self._paths:
            self._stack.setCurrentIndex(0)
            return

        self._stack.setCurrentIndex(1)

        kind = self._kind()
        single = len(self._paths) == 1

        self._refresh_pdf_info(kind, single)
        self._rebuild_file_rows(kind)

        # Rozet
        self._kind_badge.setProperty(
            "accentColor",
            _KIND_ACCENTS.get(kind, "orange"),
        )
        self._repolish(self._kind_badge)

        self._kind_icon_label.setPixmap(
            qta.icon(
                _KIND_ICONS.get(kind, "fa5s.exclamation-triangle"),
                color=self._theme_manager.accent_hex(
                    _KIND_ACCENTS.get(kind, "orange")
                ),
            ).pixmap(16, 16)
        )
        self._kind_text_label.setText(tr(f"convert.kind.{kind}"))
        self._kind_hint_label.setText(tr(f"convert.kind_hint.{kind}"))

        # Seçenekler: türe göre görünür alanlar
        convertible = kind in _CONVERTIBLE_KINDS

        images = kind == "images_to_pdf"
        office_multi = kind == "office_to_pdf" and not single
        combine = self._combine_selected(kind)

        name_editable = convertible and (single or images or combine)

        self._name_field[0].setVisible(convertible)
        self._name_input.setEnabled(name_editable)
        self._name_input.setPlaceholderText(
            self._default_name(kind)
            if name_editable or not convertible
            else tr("convert.name_each_own")
        )

        self._combine_field.setVisible(office_multi)
        self._page_mode_field.setVisible(images)

        if office_multi and combine:
            self._kind_hint_label.setText(
                tr("convert.kind_hint.office_to_pdf_single")
            )

        pdf_to_images = kind == "pdf_to_images"

        self._range_field[0].setVisible(pdf_to_images)
        self._dpi_field[0].setVisible(pdf_to_images)
        self._quality_field[0].setVisible(pdf_to_images)
        self._range_input.setEnabled(single)

        if pdf_to_images and single and self._pdf_page_count:
            self._range_input.setPlaceholderText(
                tr("convert.range_placeholder_count").format(
                    count=self._pdf_page_count
                )
            )
        else:
            self._range_input.setPlaceholderText(
                tr("convert.range_placeholder")
            )

        self._name_caption.setText(
            tr(
                "convert.field.name_images"
                if pdf_to_images
                else "convert.field.name"
            )
        )

        # Uyarı satırı
        warning = self._warning_text(kind)

        self._warning_label.setText(warning)
        self._warning_label.setVisible(bool(warning))

        can_convert = (
            convertible
            and self._pdf_error is None
            and not self._runner.is_running
        )
        self._convert_button.setEnabled(can_convert)

        self._summary_label.setText(
            tr("convert.summary").format(count=len(self._paths))
        )

    def _combine_selected(self, kind: str) -> bool:
        return (
            kind == "office_to_pdf"
            and len(self._paths) > 1
            and self._combine_buttons["single"].isChecked()
        )

    def _default_name(self, kind: str) -> str:
        if not self._paths:
            return ""

        stem = Path(self._paths[0]).stem
        tr = self._language_manager.tr

        if kind == "images_to_pdf" and len(self._paths) > 1:
            return tr("convert.default_name_images")

        if self._combine_selected(kind):
            return tr("convert.default_name_combined")

        return stem

    def _warning_text(self, kind: str) -> str:
        tr = self._language_manager.tr

        if kind in ("mixed", "unsupported"):
            return tr(f"op.error.{kind}")

        if self._pdf_error is not None:
            return tr(f"op.error.{self._pdf_error}")

        return ""

    def _refresh_pdf_info(self, kind: str, single: bool) -> None:
        self._pdf_error = None
        self._pdf_page_count = None

        if kind != "pdf_to_images":
            return

        # Şifreli/bozuk PDF'i dönüştürmeden önce göster.
        for path in self._paths:
            try:
                count = backend_gateway.read_pdf_page_count(path)

            except OperationError as error:
                self._pdf_error = error.reason
                return

            if single:
                self._pdf_page_count = count

    def _rebuild_file_rows(self, kind: str) -> None:
        while self._files_layout.count() > 1:
            item = self._files_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        reorderable = kind == "images_to_pdf" and len(self._paths) > 1

        for index, path in enumerate(self._paths):
            self._files_layout.insertWidget(
                index,
                self._build_file_row(index, path, reorderable),
            )

    def _build_file_row(
        self,
        index: int,
        path: str,
        reorderable: bool,
    ) -> QWidget:
        file_path = Path(path)

        icon_name, accent = type_icon(
            _EXTENSION_TYPES.get(file_path.suffix.lower())
        )

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

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(1)

        name_label = QLabel(file_path.name)
        name_label.setObjectName("opFileName")

        try:
            size_text = format_file_size(file_path.stat().st_size)
        except OSError:
            size_text = ""

        detail_label = QLabel(
            f"{index + 1}.  {size_text}" if reorderable else size_text
        )
        detail_label.setObjectName("opFileDetail")

        text_column.addStretch(1)
        text_column.addWidget(name_label)
        text_column.addWidget(detail_label)
        text_column.addStretch(1)

        row_layout.addWidget(icon_label)
        row_layout.addLayout(text_column, 1)

        if reorderable:
            up_button = self._icon_button(
                "fa5s.chevron-up",
                lambda: self._move_file(index, -1),
                enabled=index > 0,
            )
            down_button = self._icon_button(
                "fa5s.chevron-down",
                lambda: self._move_file(index, 1),
                enabled=index < len(self._paths) - 1,
            )

            row_layout.addWidget(up_button)
            row_layout.addWidget(down_button)

        row_layout.addWidget(
            self._icon_button(
                "fa5s.times",
                lambda: self._remove_file(index),
            )
        )

        return row

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

    # ------------------------------------------------------------------
    # Dosya ekleme / çıkarma
    # ------------------------------------------------------------------

    def _on_pick_clicked(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            self._language_manager.tr("convert.dialog_title"),
            "",
            _dialog_filter(),
        )

        if paths:
            self._add_paths(paths)

    def _on_pick_library_clicked(self) -> None:
        if self._runner.is_running:
            return

        tr = self._language_manager.tr

        paths = PdfPickerDialog.pick_many(
            self,
            documents=backend_gateway.fetch_library_documents(),
            types=_LIBRARY_TYPES,
            title=tr("convert.library_title"),
            body=tr("convert.library_body"),
        )

        if paths:
            self._add_paths(paths)

    def _add_paths(self, paths: list[str]) -> None:
        if self._runner.is_running:
            return

        supported: list[str] = []
        rejected: list[str] = []

        for path in paths:
            if Path(path).suffix.lower() in CONVERT_SUPPORTED_EXTENSIONS:
                if path not in self._paths and path not in supported:
                    supported.append(path)
            else:
                rejected.append(path)

        if rejected:
            tr = self._language_manager.tr

            AppDialog.inform(
                self,
                title=tr("convert.rejected_title"),
                body=tr("convert.rejected_body"),
                variant="danger",
                icon_name="fa5s.ban",
                items=[
                    DialogItem(
                        name=Path(path).name,
                        detail=tr("library.upload_unsupported"),
                        icon_name="fa5s.ban",
                        accent="red",
                    )
                    for path in rejected
                ],
            )

        if supported:
            self._paths.extend(supported)
            self._refresh()

    def _remove_file(self, index: int) -> None:
        if 0 <= index < len(self._paths):
            del self._paths[index]
            self._refresh()

    def _move_file(self, index: int, offset: int) -> None:
        target = index + offset

        if 0 <= target < len(self._paths):
            self._paths[index], self._paths[target] = (
                self._paths[target],
                self._paths[index],
            )
            self._refresh()

    def _on_clear_clicked(self) -> None:
        if self._runner.is_running:
            return

        self._paths.clear()
        self._name_input.clear()
        self._range_input.clear()
        self._refresh()

    # ------------------------------------------------------------------
    # Dönüştürme
    # ------------------------------------------------------------------

    def _on_convert_clicked(self) -> None:
        kind = self._kind()

        if kind not in _CONVERTIBLE_KINDS:
            return

        paths = list(self._paths)
        output_name = (
            self._name_input.text().strip()
            if self._name_input.isEnabled()
            else ""
        )
        range_text = (
            self._range_input.text().strip()
            if kind == "pdf_to_images" and len(paths) == 1
            else ""
        )
        dpi = self._dpi_spin.value()
        quality = self._quality_spin.value()

        combine = self._combine_selected(kind)
        page_mode = (
            "a4" if self._page_mode_buttons["a4"].isChecked() else "original"
        )

        if not output_name and (kind == "images_to_pdf" or combine):
            output_name = self._default_name(kind)

        def task(report):
            page_numbers = None

            if range_text:
                total = backend_gateway.read_pdf_page_count(paths[0])
                page_numbers = backend_gateway.parse_page_selection(
                    range_text, total
                )

            return backend_gateway.convert_files(
                ConvertRequest(
                    paths=paths,
                    output_name=output_name,
                    page_numbers=page_numbers,
                    dpi=dpi,
                    quality=quality,
                    combine=combine,
                    page_mode=page_mode,
                ),
                report,
            )

        if self._runner.run(task, progress=True):
            self._busy_overlay.show_busy(
                self._language_manager.tr(f"convert.busy.{kind}"),
                with_progress=True,
            )
            self._convert_button.setEnabled(False)

    def _on_progressed(self, percent: int, text: str) -> None:
        self._busy_overlay.set_progress(percent, text)

    def _on_succeeded(self, documents) -> None:
        self._busy_overlay.hide_busy()

        tr = self._language_manager.tr

        items = []

        for document in documents:
            icon_name, accent = type_icon(document.document_type)

            items.append(
                DialogItem(
                    name=document.display_name,
                    detail=format_document_meta(
                        document, date=document.created_at
                    ),
                    icon_name=icon_name,
                    accent=accent,
                )
            )

        action = AppDialog.choose(
            self,
            title=tr("convert.result_title"),
            body=tr("convert.result_body").format(count=len(documents)),
            confirm_text=tr("dialog.ok"),
            extra_actions=[
                ("reveal", tr("common.show_in_folder")),
                ("library", tr("convert.show_in_library")),
            ],
            variant="success",
            icon_name="fa5s.check",
            items=items,
        )

        self._paths.clear()
        self._name_input.clear()
        self._range_input.clear()
        self._refresh()

        if action == "reveal":
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

    def _on_errored(self, error) -> None:
        self._busy_overlay.hide_busy()

        tr = self._language_manager.tr

        if isinstance(error, OperationError):
            reason = error.reason
        else:
            logger.exception(
                "Dönüştürme beklenmedik şekilde başarısız oldu.",
                exc_info=error,
            )
            reason = "unknown"

        AppDialog.inform(
            self,
            title=tr("convert.error_title"),
            body=tr(f"op.error.{reason}"),
            variant="danger",
            icon_name="fa5s.exclamation",
        )

        self._refresh()

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

    def dragEnterEvent(self, event) -> None:
        if not self._runner.is_running and _local_paths_from_mime(
            event.mimeData()
        ):
            event.acceptProposedAction()

            self._drop_overlay.setGeometry(self.rect())
            self._drop_overlay.raise_()
            self._drop_overlay.show()

            return

        event.ignore()

    def dragMoveEvent(self, event) -> None:
        if not self._runner.is_running and _local_paths_from_mime(
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

        paths = _local_paths_from_mime(event.mimeData())

        if not paths:
            event.ignore()
            return

        event.acceptProposedAction()

        self._add_paths(paths)
