from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.presentation import backend_gateway
from pdf_reme.presentation.pages.document_list_page import DocumentListPage
from pdf_reme.presentation.widgets.selection_bar import BulkAction


class FavoritesPage(DocumentListPage):
    title_key = "sidebar.nav.favorites"
    description_key = "placeholder.favorites.description"
    empty_key = "favorites.empty"
    has_type_filter = True
    bulk_actions = [
        BulkAction("unfavorite", "bulk.unfavorite", "fa5s.star"),
        BulkAction("trash", "bulk.trash", "fa5s.trash-alt", danger=True),
    ]

    def _fetch_documents(self) -> list[Document]:
        # En son favorilenen en üstte (backend_gateway.fetch_favorites).
        return backend_gateway.fetch_favorites()

    def _description_text(self) -> str:
        return self._language_manager.tr(
            "placeholder.favorites.description"
            if self._all_documents
            else "favorites.no_favorites"
        )

    def _on_favorite_toggled(self, document_id: str) -> None:
        document = self._document_by_id(document_id)

        if document is None:
            return

        if not self._confirm_unfavorite([document]):
            return

        backend_gateway.set_favorite(document_id, False)
        self.refresh()

    def _confirm_unfavorite(self, documents: list[Document]) -> bool:
        return self._confirm(
            title_key="favorites.unfavorite_confirm_title",
            body=self._count_or_name_body(
                documents,
                single_key="favorites.unfavorite_confirm_body",
                bulk_key="favorites.unfavorite_bulk_body",
            ),
            confirm_key="favorites.unfavorite_confirm_button",
            variant="primary",
            icon_name="fa5s.star",
        )

    def _handle_bulk_action(
        self,
        key: str,
        documents: list[Document],
    ) -> bool:
        if key == "unfavorite":
            if not self._confirm_unfavorite(documents):
                return False

            for document in documents:
                backend_gateway.set_favorite(document.id, False)

            return True

        if key == "trash":
            return self._bulk_move_to_trash(documents)

        return False
