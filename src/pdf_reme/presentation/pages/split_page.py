from pathlib import Path

import qtawesome as qta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation import app_settings, backend_gateway
from pdf_reme.presentation.backend_gateway import OperationError
from pdf_reme.presentation.pages.pdf_tool_page import PdfToolPage
from pdf_reme.presentation.widgets.option_check_box import OptionCheckBox
from pdf_reme.presentation.widgets.pdf_thumbnail_panel import (
    PdfThumbnailPanel,
)

_MODES = ("pages", "parts")


def _format_page_ranges(pages: set[int]) -> str:
    """{1,2,3,5} -> '1-3, 5'"""
    ranges: list[str] = []
    ordered = sorted(pages)
    index = 0

    while index < len(ordered):
        start = end = ordered[index]

        while index + 1 < len(ordered) and ordered[index + 1] == end + 1:
            index += 1
            end = ordered[index]

        ranges.append(str(start) if start == end else f"{start}-{end}")
        index += 1

    return ", ".join(ranges)


class SplitPage(PdfToolPage):
    KEY = "split"
    MULTIPLE = False
    ICON = "fa5s.cut"
    ACCENT = "green"

    def _init_state(self) -> None:
        self._file_row: QWidget | None = None
        self._selected: set[int] = set()
        self._syncing = False

    def _build_content(self) -> QWidget:
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self._file_holder = QVBoxLayout()
        self._file_holder.setContentsMargins(0, 0, 0, 0)

        layout.addLayout(self._file_holder)

        body = QHBoxLayout()
        body.setSpacing(14)

        # Sayfa küçük resimleri
        thumb_card = QFrame()
        thumb_card.setObjectName("opCard")

        thumb_layout = QVBoxLayout(thumb_card)
        thumb_layout.setContentsMargins(14, 14, 14, 14)
        thumb_layout.setSpacing(8)

        self._thumb_hint = QLabel()
        self._thumb_hint.setObjectName("opHint")
        self._thumb_hint.setWordWrap(True)

        self._thumbs = PdfThumbnailPanel()
        self._thumbs.page_clicked.connect(self._on_thumb_clicked)

        thumb_layout.addWidget(self._thumb_hint)
        thumb_layout.addWidget(self._thumbs, 1)

        body.addWidget(thumb_card, 1)

        # Seçenekler
        options = QFrame()
        options.setObjectName("opCard")
        options.setFixedWidth(340)

        options_layout = QVBoxLayout(options)
        options_layout.setContentsMargins(20, 18, 20, 18)
        options_layout.setSpacing(14)

        mode_field, self._mode_caption, self._mode_buttons = (
            self._make_segment(_MODES)
        )

        for button in self._mode_buttons.values():
            button.clicked.connect(self._on_mode_changed)

        options_layout.addWidget(mode_field)

        self._mode_stack = QStackedWidget()
        self._mode_stack.addWidget(self._build_pages_option())
        self._mode_stack.addWidget(self._build_parts_option())

        options_layout.addWidget(self._mode_stack)

        self._name_input = self._make_line_edit()
        self._name_input.textChanged.connect(self._update_action)

        name_field, self._name_caption = self._make_field(self._name_input)

        options_layout.addWidget(name_field)

        self._warning_label = QLabel()
        self._warning_label.setObjectName("opWarning")
        self._warning_label.setWordWrap(True)
        self._warning_label.hide()

        options_layout.addWidget(self._warning_label)
        options_layout.addStretch(1)

        self._split_button = QPushButton()
        self._split_button.setObjectName("opPrimaryButton")
        self._split_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._split_button.clicked.connect(self._on_split)

        options_layout.addWidget(self._split_button)

        body.addWidget(options)

        layout.addLayout(body, 1)

        return page

    def _build_pages_option(self) -> QWidget:
        holder = QWidget()

        column = QVBoxLayout(holder)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)

        self._pages_input = self._make_line_edit()
        self._pages_input.textChanged.connect(self._on_expression_changed)

        field, self._pages_caption = self._make_field(self._pages_input)

        self._pages_hint = QLabel()
        self._pages_hint.setObjectName("opHint")
        self._pages_hint.setWordWrap(True)

        self._keep_rest_check = OptionCheckBox()
        self._keep_rest_check.setChecked(app_settings.split_keep_rest())
        self._keep_rest_check.toggled.connect(self._on_keep_rest_toggled)

        column.addWidget(field)
        column.addWidget(self._pages_hint)
        column.addWidget(self._keep_rest_check)

        return holder

    def _build_parts_option(self) -> QWidget:
        holder = QWidget()

        column = QVBoxLayout(holder)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)

        self._parts_spin = QSpinBox()
        self._parts_spin.setObjectName("opInput")
        self._parts_spin.setFixedHeight(38)
        self._parts_spin.setRange(2, 2)
        self._parts_spin.valueChanged.connect(self._update_hints)

        field, self._parts_caption = self._make_field(self._parts_spin)

        self._parts_hint = QLabel()
        self._parts_hint.setObjectName("opHint")
        self._parts_hint.setWordWrap(True)

        column.addWidget(field)
        column.addWidget(self._parts_hint)

        return holder

    # ------------------------------------------------------------------
    # Durum
    # ------------------------------------------------------------------

    def _mode(self) -> str:
        for key, button in self._mode_buttons.items():
            if button.isChecked():
                return key

        return "pages"

    def _page_total(self) -> int:
        if not self._paths:
            return 0

        info = self._infos.get(self._paths[0])

        return (info.page_count or 0) if info is not None else 0

    def _current_expression(self) -> str:
        return self._pages_input.text()

    def _on_files_changed(self) -> None:
        self._selected = set()

        self._pages_input.clear()
        self._keep_rest_check.setChecked(app_settings.split_keep_rest())

        if self._paths:
            path = self._paths[0]
            total = self._page_total()

            self._thumbs.load(path)

            self._parts_spin.setRange(2, max(2, total))
            self._parts_spin.setValue(min(2, max(2, total)))
            self._name_input.setText(Path(path).stem)
        else:
            self._thumbs.clear()
            self._name_input.clear()

        self._thumbs.set_selection(self._selected)

    def _on_mode_changed(self) -> None:
        mode = self._mode()

        self._mode_stack.setCurrentIndex(_MODES.index(mode))
        self._sync_selection_from_text()
        self._update_hints()
        self._update_action()

    def apply_defaults(self) -> None:
        """Ayarlar'daki 'kalan sayfaları da ayır' varsayılanını uygular."""
        self._keep_rest_check.setChecked(app_settings.split_keep_rest())

    def _on_keep_rest_toggled(self) -> None:
        self._update_hints()

    def _on_expression_changed(self) -> None:
        if self._syncing:
            return

        self._sync_selection_from_text()
        self._update_hints()
        self._update_action()

    def _on_thumb_clicked(self, page_number: int) -> None:
        # Küçük resimle seçim yalnız "Sayfa Seç" modunda anlamlı.
        if self._mode() != "pages" or self._runner.is_running:
            return

        if page_number in self._selected:
            self._selected.discard(page_number)
        else:
            self._selected.add(page_number)

        self._syncing = True
        try:
            self._pages_input.setText(_format_page_ranges(self._selected))
        finally:
            self._syncing = False

        self._thumbs.set_selection(self._selected)
        self._update_hints()
        self._update_action()

    def _sync_selection_from_text(self) -> None:
        mode = self._mode()
        total = self._page_total()
        selected: set[int] = set()

        if total and mode == "pages":
            try:
                selected = set(
                    backend_gateway.parse_page_selection(
                        self._pages_input.text(), total
                    )
                )

            except OperationError:
                selected = set()

        self._selected = selected
        self._thumbs.set_selection(selected)

    def _validation_error(self) -> str | None:
        """Etkin moda göre geçersizlik gerekçesi; geçerliyse None."""
        tr = self._language_manager.tr

        total = self._page_total()

        if self._mode() != "pages":
            return None

        text = self._current_expression().strip()

        if not text:
            return None

        try:
            backend_gateway.parse_page_selection(text, total)

        except OperationError:
            return tr("split.invalid_range").format(total=total)

        return None

    def _update_hints(self) -> None:
        tr = self._language_manager.tr

        total = self._page_total()
        mode = self._mode()

        self._thumb_hint.setText(
            tr("split.thumb_hint_pages")
            if mode == "pages"
            else tr("split.thumb_hint_readonly")
        )

        selected_count = len(self._selected)
        rest_count = total - selected_count

        pages_hint = tr("split.pages_hint").format(
            count=selected_count, total=total
        )

        if selected_count:
            if self._keep_rest_check.isChecked() and rest_count > 0:
                pages_hint += "\n" + tr("split.rest_hint_two").format(
                    count=selected_count, rest=rest_count
                )
            else:
                pages_hint += "\n" + tr("split.rest_hint_one").format(
                    count=selected_count
                )

        self._pages_hint.setText(pages_hint)

        parts = self._parts_spin.value()

        if total >= 2 and parts >= 2:
            base, remainder = divmod(total, parts)
            sizes = [
                str(base + 1 if index < remainder else base)
                for index in range(min(parts, 8))
            ]

            summary = " + ".join(sizes)

            if parts > 8:
                summary += " + …"

            self._parts_hint.setText(
                tr("split.parts_hint").format(count=parts, sizes=summary)
            )
        else:
            self._parts_hint.setText("")

        error = self._validation_error()

        self._warning_label.setText(error or "")
        self._warning_label.setVisible(bool(error))

    def _refresh_content(self) -> None:
        if self._file_row is not None:
            self._file_holder.removeWidget(self._file_row)
            self._file_row.deleteLater()
            self._file_row = None

        if self._paths:
            self._file_row = self._build_file_row(self._paths[0])
            self._file_holder.addWidget(self._file_row)

        self._mode_stack.setCurrentIndex(_MODES.index(self._mode()))
        self._update_hints()
        self._update_action()

    def _update_action(self) -> None:
        busy = self._runner.is_running
        mode = self._mode()

        ready = bool(self._paths) and bool(self._name_input.text().strip())

        if mode == "pages":
            ready = ready and bool(self._selected)

        self._split_button.setEnabled(ready and not busy)

    def _retranslate_content(self) -> None:
        tr = self._language_manager.tr

        self._mode_caption.setText(tr("split.mode"))

        for key, button in self._mode_buttons.items():
            button.setText(tr(f"split.mode.{key}"))

        self._pages_caption.setText(tr("split.pages_label"))
        self._pages_input.setPlaceholderText(tr("split.pages_placeholder"))
        self._parts_caption.setText(tr("split.parts_label"))
        self._keep_rest_check.setText(tr("split.keep_rest"))
        self._name_caption.setText(tr("split.output_name"))
        self._split_button.setText(tr("split.action"))

    def _apply_content_theme(self) -> None:
        self._split_button.setIcon(qta.icon("fa5s.cut", color="#FFFFFF"))

    # ------------------------------------------------------------------
    # İşlem
    # ------------------------------------------------------------------

    def _on_split(self) -> None:
        if not self._paths or self._runner.is_running:
            return

        tr = self._language_manager.tr

        request = backend_gateway.SplitRequest(
            path=self._paths[0],
            mode=self._mode(),
            name=self._name_input.text().strip(),
            expression=self._current_expression(),
            part_count=self._parts_spin.value(),
            keep_rest=self._keep_rest_check.isChecked(),
        )

        self._run_task(
            lambda: backend_gateway.split_pdf(request),
            tr("split.busy"),
        )
        self._update_action()

    def _handle_result(self, documents) -> None:
        tr = self._language_manager.tr

        count = len(documents)

        self._show_result(
            title=tr("split.success_title"),
            body=tr("split.success_body").format(count=count),
            documents=documents,
        )

        self.clear_files()

    def _handle_error_reason(self, reason: str) -> bool:
        self._update_action()

        return False
