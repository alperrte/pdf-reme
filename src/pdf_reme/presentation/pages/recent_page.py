from datetime import datetime

from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.presentation import backend_gateway
from pdf_reme.presentation.pages.document_list_page import DocumentListPage
from pdf_reme.presentation.widgets.selection_bar import BulkAction

_RECENT_LIMIT = 50


class RecentPage(DocumentListPage):
    title_key = "sidebar.nav.recent"
    description_key = "placeholder.recent.description"
    empty_key = "recent.empty"
    bulk_actions = [
        BulkAction("favorite", "bulk.favorite", "fa5s.star"),
        BulkAction("trash", "bulk.trash", "fa5s.trash-alt", danger=True),
    ]

    def _fetch_documents(self) -> list[Document]:
        # last_opened_at'e göre azalan (en yeni önce) sırada döner.
        return backend_gateway.fetch_recent(limit=_RECENT_LIMIT)

    def _card_date(self, document: Document) -> datetime | None:
        return document.last_opened_at

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
