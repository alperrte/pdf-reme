import logging
from pathlib import Path

import qtawesome as qta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.infrastructure.filesystem.file_validation import (
    SUPPORTED_EXTENSIONS,
)
from pdf_reme.presentation import backend_gateway
from pdf_reme.presentation.document_format import (
    format_file_size,
    type_icon,
)
from pdf_reme.presentation.pages.document_list_page import DocumentListPage
from pdf_reme.presentation.widgets.app_dialog import AppDialog, DialogItem
from pdf_reme.presentation.widgets.file_drop_area import DropOverlay
from pdf_reme.presentation.widgets.selection_bar import BulkAction

logger = logging.getLogger(__name__)


def _file_dialog_filter() -> str:
    extensions = " ".join(
        f"*{extension}" for extension in SUPPORTED_EXTENSIONS
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


class LibraryPage(DocumentListPage):
    title_key = "sidebar.nav.library"
    description_key = "placeholder.library.description"
    empty_key = "library.empty"
    has_type_filter = True
    bulk_actions = [
        BulkAction("favorite", "bulk.favorite", "fa5s.star"),
        BulkAction("trash", "bulk.trash", "fa5s.trash-alt", danger=True),
    ]

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setAcceptDrops(True)

        self._drop_overlay = DropOverlay(self)

    def _fetch_documents(self) -> list[Document]:
        return backend_gateway.fetch_library_documents()

    def _build_header_widgets(self, header_row: QHBoxLayout) -> None:
        self._upload_button = QPushButton()
        self._upload_button.setObjectName("libraryUploadButton")
        self._upload_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._upload_button.clicked.connect(self._on_upload_clicked)

        header_row.addWidget(
            self._upload_button,
            0,
            Qt.AlignmentFlag.AlignTop,
        )

    def retranslate_ui(self) -> None:
        super().retranslate_ui()

        self._upload_button.setText(
            self._language_manager.tr("library.upload_button")
        )

        if hasattr(self, "_drop_overlay"):
            self._drop_overlay.retranslate_ui()

    def apply_theme(self) -> None:
        super().apply_theme()

        self._upload_button.setIcon(qta.icon("fa5s.upload", color="#FFFFFF"))

        if hasattr(self, "_drop_overlay"):
            self._drop_overlay.apply_theme()

    def _handle_bulk_action(
        self,
        key: str,
        documents: list[Document],
    ) -> bool:
        if key == "favorite":
            for document in documents:
                if not document.is_favorite:
                    backend_gateway.set_favorite(document.id, True)

            return True

        if key == "trash":
            return self._bulk_move_to_trash(documents)

        return False

    # ------------------------------------------------------------------
    # Yükleme (buton + sürükle-bırak)
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

        if hasattr(self, "_drop_overlay"):
            self._drop_overlay.setGeometry(self.rect())

    def dragEnterEvent(self, event) -> None:
        if _local_paths_from_mime(event.mimeData()):
            event.acceptProposedAction()

            self._drop_overlay.setGeometry(self.rect())
            self._drop_overlay.raise_()
            self._drop_overlay.show()

            return

        event.ignore()

    def dragMoveEvent(self, event) -> None:
        if _local_paths_from_mime(event.mimeData()):
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

        self._confirm_and_import(paths)

    def _is_supported(self, path: str) -> bool:
        return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

    def _dialog_item_for(self, path: str) -> DialogItem:
        file_path = Path(path)

        icon_name, accent = type_icon(
            SUPPORTED_EXTENSIONS.get(file_path.suffix.lower())
        )

        try:
            size_text = format_file_size(file_path.stat().st_size)
        except OSError:
            size_text = ""

        return DialogItem(
            name=file_path.name,
            detail=size_text,
            icon_name=icon_name,
            accent=accent,
        )

    def _confirm_and_import(self, paths: list[str]) -> None:
        supported = [path for path in paths if self._is_supported(path)]
        unsupported = [path for path in paths if not self._is_supported(path)]

        tr = self._language_manager.tr

        if not supported:
            AppDialog.inform(
                self,
                title=tr("library.upload_confirm_title"),
                body=tr("library.upload_none_supported_body"),
                variant="danger",
                icon_name="fa5s.ban",
            )
            return

        items = [self._dialog_item_for(path) for path in supported]

        items += [
            DialogItem(
                name=Path(path).name,
                detail=tr("library.upload_unsupported"),
                icon_name="fa5s.ban",
                accent="red",
            )
            for path in unsupported
        ]

        confirmed = AppDialog.ask(
            self,
            title=tr("library.upload_confirm_title"),
            body=tr("library.upload_confirm_body").format(
                count=len(supported)
            ),
            confirm_text=tr("library.upload_confirm_button"),
            variant="primary",
            icon_name="fa5s.cloud-upload-alt",
            items=items,
        )

        if not confirmed:
            return

        self._import_paths(supported)

    def _on_upload_clicked(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            self._language_manager.tr("library.upload_dialog_title"),
            "",
            _file_dialog_filter(),
        )

        if not paths:
            return

        self._import_paths(paths)

    def _import_paths(self, paths: list[str]) -> None:
        tr = self._language_manager.tr

        try:
            outcomes = backend_gateway.import_documents(paths)

        except Exception:
            logger.exception("Belge içe aktarma beklenmedik şekilde başarısız oldu.")

            AppDialog.inform(
                self,
                title=tr("library.upload_result_title"),
                body=tr("library.upload_reason.unknown"),
                variant="danger",
                icon_name="fa5s.exclamation",
            )
            return

        items: list[DialogItem] = []

        imported_count = 0
        duplicate_count = 0
        failed_count = 0

        for outcome in outcomes:
            if outcome.status == "imported":
                imported_count += 1
                detail = tr("library.upload_status_imported")
                icon_name, accent = "fa5s.check-circle", "green"

            elif outcome.status == "duplicate":
                duplicate_count += 1
                detail = self._duplicate_detail(outcome)
                icon_name, accent = "fa5s.clone", "blue"

            else:
                failed_count += 1
                detail = tr(
                    f"library.upload_reason.{outcome.reason}"
                )
                icon_name, accent = "fa5s.exclamation-circle", "red"

            items.append(
                DialogItem(
                    name=Path(outcome.path).name,
                    detail=detail,
                    icon_name=icon_name,
                    accent=accent,
                )
            )

        summary_lines = []

        if imported_count:
            summary_lines.append(
                tr("library.upload_summary_imported").format(
                    count=imported_count
                )
            )

        if duplicate_count:
            summary_lines.append(
                tr("library.upload_summary_duplicate").format(
                    count=duplicate_count
                )
            )

        if failed_count:
            summary_lines.append(
                tr("library.upload_summary_failed").format(
                    count=failed_count
                )
            )

        self.refresh()

        if imported_count:
            variant, icon_name = "success", "fa5s.check"
        elif failed_count:
            variant, icon_name = "danger", "fa5s.exclamation"
        else:
            variant, icon_name = "info", "fa5s.clone"

        AppDialog.inform(
            self,
            title=tr("library.upload_result_title"),
            body="\n".join(summary_lines),
            variant=variant,
            icon_name=icon_name,
            items=items,
        )

    def _duplicate_detail(self, outcome) -> str:
        tr = self._language_manager.tr

        if outcome.existing_trashed:
            return tr("library.upload_duplicate_trashed").format(
                name=outcome.existing_name or ""
            )

        if outcome.existing_name:
            return tr("library.upload_duplicate_named").format(
                name=outcome.existing_name
            )

        return tr("library.upload_status_duplicate")

