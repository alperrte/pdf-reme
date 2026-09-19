from pathlib import Path

import qtawesome as qta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation import app_settings, backend_gateway
from pdf_reme.presentation.document_format import format_file_size
from pdf_reme.presentation.pages.pdf_tool_page import PdfToolPage
from pdf_reme.presentation.widgets.app_dialog import AppDialog

_LEVELS = ("light", "balanced", "strong")


class CompressPage(PdfToolPage):
    KEY = "compress"
    MULTIPLE = False
    ICON = "fa5s.compress-arrows-alt"
    ACCENT = "orange"

    def _build_content(self) -> QWidget:
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Dosya satırı
        self._file_holder = QVBoxLayout()
        self._file_holder.setContentsMargins(0, 0, 0, 0)
        self._file_row: QWidget | None = None

        layout.addLayout(self._file_holder)

        # Seçenek kartı
        card = QFrame()
        card.setObjectName("opCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(14)

        level_field, self._level_caption, self._level_buttons = (
            self._make_segment(_LEVELS)
        )

        for key, button in self._level_buttons.items():
            button.clicked.connect(self._on_level_changed)

        self._level_buttons[app_settings.default_compress_level()].setChecked(
            True
        )

        self._level_hint = QLabel()
        self._level_hint.setObjectName("opHint")
        self._level_hint.setWordWrap(True)

        self._level_warning = QLabel()
        self._level_warning.setObjectName("opWarning")
        self._level_warning.setWordWrap(True)

        self._name_input = self._make_line_edit()
        self._name_input.textChanged.connect(self._update_action)

        name_field, self._name_caption = self._make_field(self._name_input)

        card_layout.addWidget(level_field)
        card_layout.addWidget(self._level_hint)
        card_layout.addWidget(self._level_warning)
        card_layout.addWidget(name_field)

        layout.addWidget(card)
        layout.addStretch(1)

        # Eylem satırı
        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        action_row.addStretch(1)

        self._compress_button = QPushButton()
        self._compress_button.setObjectName("opPrimaryButton")
        self._compress_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._compress_button.clicked.connect(self._on_compress)

        action_row.addWidget(self._compress_button)

        layout.addLayout(action_row)

        return page

    # ------------------------------------------------------------------

    def _level(self) -> str:
        for key, button in self._level_buttons.items():
            if button.isChecked():
                return key

        return "balanced"

    def apply_defaults(self) -> None:
        """Ayarlar'daki varsayılan sıkıştırma seviyesini uygular."""
        self._level_buttons[app_settings.default_compress_level()].setChecked(
            True
        )
        self._update_level_texts()

    def _on_level_changed(self) -> None:
        self._update_level_texts()

    def _update_level_texts(self) -> None:
        tr = self._language_manager.tr

        level = self._level()

        self._level_hint.setText(tr(f"compress.level_hint.{level}"))
        self._level_warning.setText(tr("compress.strong_warning"))
        self._level_warning.setVisible(level == "strong")

    def _on_files_changed(self) -> None:
        if self._paths:
            stem = Path(self._paths[0]).stem
            self._name_input.setText(f"{stem}_sikistirilmis")
        else:
            self._name_input.clear()
            self.apply_defaults()

    def _refresh_content(self) -> None:
        if self._file_row is not None:
            self._file_holder.removeWidget(self._file_row)
            self._file_row.deleteLater()
            self._file_row = None

        if self._paths:
            self._file_row = self._build_file_row(self._paths[0])
            self._file_holder.addWidget(self._file_row)

        self._update_level_texts()
        self._update_action()

    def _update_action(self) -> None:
        busy = self._runner.is_running

        self._compress_button.setEnabled(
            bool(self._paths)
            and bool(self._name_input.text().strip())
            and not busy
        )

    def _retranslate_content(self) -> None:
        tr = self._language_manager.tr

        self._level_caption.setText(tr("compress.level"))

        for key, button in self._level_buttons.items():
            button.setText(tr(f"compress.level.{key}"))

        self._name_caption.setText(tr("compress.output_name"))
        self._compress_button.setText(tr("compress.action"))

    def _apply_content_theme(self) -> None:
        self._compress_button.setIcon(
            qta.icon("fa5s.compress-arrows-alt", color="#FFFFFF")
        )

    # ------------------------------------------------------------------

    def _on_compress(self) -> None:
        if not self._paths or self._runner.is_running:
            return

        tr = self._language_manager.tr

        path = self._paths[0]
        name = self._name_input.text().strip()
        level = self._level()

        def task(report):
            return backend_gateway.compress_pdf(path, name, level, report)

        self._run_task(task, tr("compress.busy"), with_progress=True)
        self._update_action()

    def _handle_result(self, result) -> None:
        tr = self._language_manager.tr

        before = format_file_size(result.original_size)
        after = format_file_size(result.compressed_size)

        if result.used_original_fallback:
            self._show_result(
                title=tr("compress.no_gain_title"),
                body=tr("compress.no_gain_body").format(size=before),
                documents=[result.document],
                variant="info",
                icon_name="fa5s.info",
                view_on_confirm=True,
            )
        else:
            self._show_result(
                title=tr("compress.success_title"),
                body=tr("compress.success_body").format(
                    before=before,
                    after=after,
                    percent=round(result.savings_percent),
                ),
                documents=[result.document],
                view_on_confirm=True,
            )

        self.clear_files()
