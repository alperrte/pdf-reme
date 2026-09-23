import qtawesome as qta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation import backend_gateway
from pdf_reme.presentation.pages.pdf_tool_page import PdfToolPage
from pdf_reme.presentation.widgets.reorderable_list import ReorderableRowList


class MergePage(PdfToolPage):
    KEY = "merge"
    MULTIPLE = True
    ICON = "fa5s.object-group"
    ACCENT = "blue"

    def _build_content(self) -> QWidget:
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Dosya listesi kartı
        card = QFrame()
        card.setObjectName("opCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)

        self._summary_label = QLabel()
        self._summary_label.setObjectName("opFieldLabel")

        self._add_button = QPushButton()
        self._add_button.setObjectName("opSecondaryButton")
        self._add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_button.clicked.connect(self._on_pick_file)

        self._library_button = QPushButton()
        self._library_button.setObjectName("opSecondaryButton")
        self._library_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._library_button.clicked.connect(self._on_pick_library)

        self._clear_button = QPushButton()
        self._clear_button.setObjectName("opSecondaryButton")
        self._clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_button.clicked.connect(self.clear_files)

        self._remove_selected_button = QPushButton()
        self._remove_selected_button.setObjectName("opSecondaryButton")
        self._remove_selected_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self._remove_selected_button.setEnabled(False)
        self._remove_selected_button.clicked.connect(
            self._on_remove_selected
        )

        header.addWidget(self._summary_label, 1)
        header.addWidget(self._remove_selected_button)
        header.addWidget(self._add_button)
        header.addWidget(self._library_button)
        header.addWidget(self._clear_button)

        card_layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setObjectName("dashboardScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self._file_list = ReorderableRowList()
        self._file_list.reordered.connect(self._reorder_file)

        scroll.setWidget(self._file_list)

        card_layout.addWidget(scroll, 1)

        self._hint_label = QLabel()
        self._hint_label.setObjectName("opHint")
        self._hint_label.setWordWrap(True)

        card_layout.addWidget(self._hint_label)

        layout.addWidget(card, 1)

        # Çıktı satırı
        output_row = QHBoxLayout()
        output_row.setSpacing(12)
        output_row.setAlignment(Qt.AlignmentFlag.AlignBottom)

        self._name_input = self._make_line_edit()
        self._name_input.textChanged.connect(self._update_action)

        name_field, self._name_caption = self._make_field(self._name_input)

        self._merge_button = QPushButton()
        self._merge_button.setObjectName("opPrimaryButton")
        self._merge_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._merge_button.clicked.connect(self._on_merge)

        output_row.addWidget(name_field, 1)
        output_row.addWidget(
            self._merge_button, 0, Qt.AlignmentFlag.AlignBottom
        )

        layout.addLayout(output_row)

        self._name_input.setText("birlestirilmis")

        return page

    # ------------------------------------------------------------------
    # Yenileme
    # ------------------------------------------------------------------

    def _refresh_content(self) -> None:
        tr = self._language_manager.tr

        count = len(self._paths)

        self._file_list.set_reorderable(
            count > 1 and not self._runner.is_running
        )
        self._file_list.set_rows(
            [
                self._build_file_row(
                    path,
                    index=index,
                    count=count,
                    movable=True,
                    selectable=True,
                )
                for index, path in enumerate(self._paths)
            ]
        )

        total_pages = sum(
            info.page_count or 0
            for info in (self._infos.get(path) for path in self._paths)
            if info is not None
        )

        self._summary_label.setText(
            tr("merge.summary").format(count=count, pages=total_pages)
        )

        self._hint_label.setText(
            tr("merge.need_two") if count < 2 else tr("merge.order_hint")
        )

        self._update_action()

    def _update_action(self) -> None:
        busy = self._runner.is_running

        self._merge_button.setEnabled(
            len(self._paths) >= 2
            and bool(self._name_input.text().strip())
            and not busy
        )

        for button in (
            self._add_button,
            self._library_button,
            self._clear_button,
        ):
            button.setEnabled(not busy)

        self._clear_button.setEnabled(bool(self._paths) and not busy)
        self._remove_selected_button.setEnabled(
            bool(self._selected_paths) and not busy
        )

    def _on_selection_changed(self) -> None:
        self._update_action()

    def _retranslate_content(self) -> None:
        tr = self._language_manager.tr

        self._add_button.setText(tr("tool.add_file"))
        self._library_button.setText(tr("tool.add_library"))
        self._clear_button.setText(tr("tool.clear"))
        self._remove_selected_button.setText(tr("tool.remove_selected"))
        self._name_caption.setText(tr("merge.output_name"))
        self._merge_button.setText(tr("merge.action"))

    def _apply_content_theme(self) -> None:
        icon_color = self._theme_manager.icon_color()

        self._add_button.setIcon(qta.icon("fa5s.plus", color=icon_color))
        self._library_button.setIcon(qta.icon("fa5s.book", color=icon_color))
        self._clear_button.setIcon(qta.icon("fa5s.times", color=icon_color))
        self._remove_selected_button.setIcon(
            qta.icon("fa5s.check-square", color=icon_color)
        )
        self._merge_button.setIcon(
            qta.icon("fa5s.object-group", color="#FFFFFF")
        )

    # ------------------------------------------------------------------
    # İşlem
    # ------------------------------------------------------------------

    def _on_merge(self) -> None:
        if len(self._paths) < 2 or self._runner.is_running:
            return

        tr = self._language_manager.tr

        paths = list(self._paths)
        name = self._name_input.text().strip()

        started = self._run_task(
            lambda: backend_gateway.merge_pdfs(paths, name),
            tr("merge.busy"),
        )

        if started:
            self._update_action()

    def _handle_result(self, document) -> None:
        tr = self._language_manager.tr

        count = len(self._paths)

        self._show_result(
            title=tr("merge.success_title"),
            body=tr("merge.success_body").format(
                count=count, pages=document.page_count or 0
            ),
            documents=[document],
            view_on_confirm=True,
        )

        self.clear_files()
        self._name_input.setText("birlestirilmis")

    def _handle_error_reason(self, reason: str) -> bool:
        self._update_action()

        return False
