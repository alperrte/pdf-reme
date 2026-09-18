from datetime import datetime

import qtawesome as qta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.presentation import backend_gateway
from pdf_reme.presentation.pages.document_list_page import DocumentListPage
from pdf_reme.presentation.widgets.selection_bar import BulkAction


class TrashPage(DocumentListPage):
    title_key = "sidebar.nav.trash"
    description_key = "placeholder.trash.description"
    empty_key = "trash.empty"
    card_variant = "trash"
    bulk_actions = [
        BulkAction("restore", "bulk.restore", "fa5s.undo"),
        BulkAction(
            "delete_forever",
            "bulk.delete_forever",
            "fa5s.trash",
            danger=True,
        ),
    ]

    def _fetch_documents(self) -> list[Document]:
        # deleted_at'e göre azalan (en yeni önce) sırada döner.
        return backend_gateway.fetch_trashed()

    def _card_date(self, document: Document) -> datetime | None:
        return document.deleted_at

    def _build_header_widgets(self, header_row: QHBoxLayout) -> None:
        self._clear_button = QPushButton()
        self._clear_button.setObjectName("dashboardTextButton")
        self._clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_button.clicked.connect(self._on_clear_trash)

        header_row.addWidget(
            self._clear_button,
            0,
            Qt.AlignmentFlag.AlignTop,
        )

    def _build_after_header(self, layout: QVBoxLayout) -> None:
        self._retention_label = QLabel()
        self._retention_label.setObjectName("dashboardEmptyText")

        layout.addWidget(self._retention_label)

    def retranslate_ui(self) -> None:
        super().retranslate_ui()

        self._clear_button.setText(
            self._language_manager.tr("trash.clear_all")
        )

        self._retention_label.setText(
            self._language_manager.tr("trash.retention_notice")
        )

    def apply_theme(self) -> None:
        super().apply_theme()

        self._clear_button.setIcon(
            qta.icon(
                "fa5s.trash-alt",
                color=self._theme_manager.icon_color(),
            )
        )

    def _after_filters_applied(self) -> None:
        self._clear_button.setEnabled(bool(self._all_documents))

    # ------------------------------------------------------------------
    # Onaylar
    # ------------------------------------------------------------------

    def _confirm_restore(self, documents: list[Document]) -> bool:
        return self._confirm(
            title_key="trash.restore_confirm_title",
            body=self._count_or_name_body(
                documents,
                single_key="trash.restore_confirm_body",
                bulk_key="trash.restore_bulk_body",
            ),
            confirm_key="trash.restore_confirm_button",
            variant="primary",
            icon_name="fa5s.undo",
        )

    def _confirm_delete_forever(self, documents: list[Document]) -> bool:
        if len(documents) == 1:
            body = self._language_manager.tr(
                "trash.delete_forever_confirm_body"
            )
        else:
            body = self._language_manager.tr(
                "trash.delete_forever_bulk_body"
            ).format(count=len(documents))

        return self._confirm(
            title_key="trash.delete_forever_confirm_title",
            body=body,
            confirm_key="trash.delete_forever_button",
            variant="danger",
            icon_name="fa5s.trash",
        )

    # ------------------------------------------------------------------
    # Tekil eylemler
    # ------------------------------------------------------------------

    def _on_restore_requested(self, document_id: str) -> None:
        document = self._document_by_id(document_id)

        if document is None or not self._confirm_restore([document]):
            return

        backend_gateway.restore_from_trash(document_id)
        self.refresh()

    def _on_delete_forever_requested(self, document_id: str) -> None:
        document = self._document_by_id(document_id)

        if document is None or not self._confirm_delete_forever([document]):
            return

        backend_gateway.permanently_delete(document_id)
        self.refresh()

    def _on_clear_trash(self) -> None:
        confirmed = self._confirm(
            title_key="trash.clear_confirm_title",
            body=self._language_manager.tr("trash.clear_confirm_body"),
            confirm_key="trash.clear_all",
            variant="danger",
            icon_name="fa5s.trash",
        )

        if not confirmed:
            return

        backend_gateway.clear_trash()
        self.refresh()

    # ------------------------------------------------------------------
    # Toplu eylemler
    # ------------------------------------------------------------------

    def _handle_bulk_action(
        self,
        key: str,
        documents: list[Document],
    ) -> bool:
        if key == "restore":
            if not self._confirm_restore(documents):
                return False

            for document in documents:
                backend_gateway.restore_from_trash(document.id)

            return True

        if key == "delete_forever":
            if not self._confirm_delete_forever(documents):
                return False

            for document in documents:
                backend_gateway.permanently_delete(document.id)

            return True

        return False
