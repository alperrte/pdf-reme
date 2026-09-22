from datetime import datetime

import qtawesome as qta

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.presentation import backend_gateway
from pdf_reme.presentation.document_format import format_document_meta
from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager
from pdf_reme.presentation.widgets.app_dialog import AppDialog
from pdf_reme.presentation.widgets.document_card import DocumentCard
from pdf_reme.presentation.widgets.list_toolbar import (
    SearchInput,
    SortOrderCombo,
    TypeFilterBar,
)
from pdf_reme.presentation.widgets.selection_bar import (
    BulkAction,
    SelectionBar,
)


class DocumentListPage(QWidget):
    """Kütüphane / Favoriler / Son Kullanılanlar / Çöp Kutusu ortak iskeleti.

    Arama, sıralama, tür filtresi (isteğe bağlı), kart listesi ve toplu
    seçim modu burada yaşar; alt sınıflar sadece veriyi getirir ve
    sayfaya özgü işlemleri (toplu eylemler, onaylar) tanımlar.
    """

    document_open_requested = Signal(str)

    title_key = ""
    description_key = ""
    empty_key = ""
    card_variant = "library"
    has_type_filter = False
    bulk_actions: list[BulkAction] = []

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._language_manager = get_language_manager()
        self._theme_manager = get_theme_manager()

        self._cards: list[DocumentCard] = []
        self._all_documents: list[Document] = []

        self._selection_mode = False
        self._selected_ids: set[str] = set()

        self._setup_ui()
        self.retranslate_ui()
        self.apply_theme()

    # ------------------------------------------------------------------
    # Alt sınıfların özelleştirme noktaları
    # ------------------------------------------------------------------

    def _fetch_documents(self) -> list[Document]:
        raise NotImplementedError

    def _card_date(self, document: Document) -> datetime | None:
        return document.created_at

    def _description_text(self) -> str:
        return self._language_manager.tr(self.description_key)

    def _build_header_widgets(self, header_row: QHBoxLayout) -> None:
        """Başlığın sağına (yükle / boşalt gibi) buton eklemek için."""

    def _build_after_header(self, layout: QVBoxLayout) -> None:
        """Başlık ile araç çubuğu arasına ek satır koymak için."""

    def _handle_bulk_action(
        self,
        key: str,
        documents: list[Document],
    ) -> bool:
        """Toplu eylemi uygular; gerçekleştiyse True döner."""

        return False

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.setContentsMargins(42, 34, 42, 34)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        title_column = QVBoxLayout()
        title_column.setSpacing(8)

        self._title_label = QLabel()
        self._title_label.setObjectName("pageTitle")

        self._description_label = QLabel()
        self._description_label.setObjectName("pageDescription")
        self._description_label.setWordWrap(True)

        title_column.addWidget(self._title_label)
        title_column.addWidget(self._description_label)

        header_row.addLayout(title_column, 1)

        self._build_header_widgets(header_row)

        layout.addLayout(header_row)

        self._build_after_header(layout)

        layout.addSpacing(16)

        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(10)

        self._search_input = SearchInput()
        self._search_input.setFixedHeight(38)
        self._search_input.textChanged.connect(self._apply_filters)

        toolbar_row.addWidget(self._search_input, 1)

        self._sort_combo = SortOrderCombo()
        self._sort_combo.sort_changed.connect(self._apply_filters)

        toolbar_row.addWidget(self._sort_combo)

        self._selection_toggle = QPushButton()
        self._selection_toggle.setObjectName("selectionToggleButton")
        self._selection_toggle.setCheckable(True)
        self._selection_toggle.setFixedHeight(38)
        self._selection_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._selection_toggle.toggled.connect(self._set_selection_mode)

        toolbar_row.addWidget(self._selection_toggle)

        layout.addLayout(toolbar_row)

        self._type_filter_bar: TypeFilterBar | None = None

        if self.has_type_filter:
            layout.addSpacing(10)

            self._type_filter_bar = TypeFilterBar()
            self._type_filter_bar.filter_changed.connect(self._apply_filters)

            layout.addWidget(self._type_filter_bar)

        self._selection_bar = SelectionBar(self.bulk_actions)
        self._selection_bar.setVisible(False)
        self._selection_bar.select_all_toggled.connect(
            self._on_select_all_toggled
        )
        self._selection_bar.action_triggered.connect(
            self._on_bulk_action_triggered
        )

        layout.addSpacing(4)
        layout.addWidget(self._selection_bar)
        layout.addSpacing(8)

        self._scroll_area = QScrollArea()
        self._scroll_area.setObjectName("dashboardScrollArea")
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        self._content_widget = QWidget()
        self._content_widget.setObjectName("dashboardContent")

        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 4, 0)
        self._content_layout.setSpacing(10)

        self._empty_label = QLabel()
        self._empty_label.setObjectName("dashboardEmptyText")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)

        self._content_layout.addWidget(self._empty_label)
        self._content_layout.addStretch(1)

        self._scroll_area.setWidget(self._content_widget)

        layout.addWidget(self._scroll_area, 1)

    def retranslate_ui(self) -> None:
        self._title_label.setText(
            self._language_manager.tr(self.title_key)
        )

        self._description_label.setText(self._description_text())

        self._selection_toggle.setText(
            self._language_manager.tr(
                "common.select_mode_done"
                if self._selection_mode
                else "common.select_mode"
            )
        )

        self._update_empty_text()

        self._search_input.retranslate_ui()
        self._sort_combo.retranslate_ui()
        self._selection_bar.retranslate_ui()

        if self._type_filter_bar is not None:
            self._type_filter_bar.retranslate_ui()

        self._update_selection_bar()

        for card in self._cards:
            card.retranslate_ui()

    def apply_theme(self) -> None:
        self._search_input.apply_theme()
        self._sort_combo.apply_theme()
        self._selection_bar.apply_theme()

        if self._type_filter_bar is not None:
            self._type_filter_bar.apply_theme()

        self._selection_toggle.setIcon(
            qta.icon(
                "fa5s.check-square" if self._selection_mode else "fa5.check-square",
                color=(
                    self._theme_manager.accent_hex("blue")
                    if self._selection_mode
                    else self._theme_manager.icon_color()
                ),
            )
        )

        for card in self._cards:
            card.apply_theme()

    # ------------------------------------------------------------------
    # Veri / filtreleme
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        scroll_bar = self._scroll_area.verticalScrollBar()
        scroll_value = scroll_bar.value()

        self._all_documents = self._fetch_documents()

        existing_ids = {document.id for document in self._all_documents}
        self._selected_ids &= existing_ids

        self._description_label.setText(self._description_text())

        self._apply_filters()

        self._restore_scroll(scroll_value)

    def _restore_scroll(self, value: int) -> None:
        # Kartlar silinip yeniden kurulurken odaktaki düğme (yıldız / çöp)
        # yok olur; QScrollArea odağı bir sonraki widget'a taşıyıp onu
        # görünür kılmak için listeyi en alta kaydırıyordu. Kaydırma
        # konumunu, yerleşim hesaplandıktan sonra geri yüklüyoruz.
        scroll_bar = self._scroll_area.verticalScrollBar()

        def restore() -> None:
            scroll_bar.setValue(min(value, scroll_bar.maximum()))

        restore()

        QTimer.singleShot(0, restore)
        QTimer.singleShot(60, restore)

    def _apply_filters(self) -> None:
        query = self._search_input.text().strip().lower()

        documents = self._all_documents

        if self._type_filter_bar is not None:
            selected_type = self._type_filter_bar.selected_type

            if selected_type is not None:
                documents = [
                    document
                    for document in documents
                    if document.document_type == selected_type
                ]

        if query:
            documents = [
                document
                for document in documents
                if query in document.display_name.lower()
            ]

        # _fetch_documents() en yeni önce döner; artan seçilince ters çevir.
        if self._sort_combo.is_ascending:
            documents = list(reversed(documents))

        for card in self._cards:
            card.setParent(None)
            card.deleteLater()

        self._cards.clear()

        self._empty_label.setVisible(not documents)
        self._update_empty_text()

        for document in documents:
            card = DocumentCard(
                document,
                format_document_meta(
                    document,
                    date=self._card_date(document),
                ),
                variant=self.card_variant,
            )

            card.open_requested.connect(self.document_open_requested)
            card.favorite_toggled.connect(self._on_favorite_toggled)
            card.trash_requested.connect(self._on_trash_requested)
            card.restore_requested.connect(self._on_restore_requested)
            card.delete_forever_requested.connect(
                self._on_delete_forever_requested
            )
            card.reveal_requested.connect(self._on_reveal_requested)
            card.selection_toggled.connect(self._on_card_selection_toggled)

            card.set_selection_mode(self._selection_mode)
            card.set_selected(document.id in self._selected_ids)

            self._content_layout.insertWidget(
                self._content_layout.count() - 1,
                card,
            )

            self._cards.append(card)

        self._after_filters_applied()
        self._update_selection_bar()

    def _after_filters_applied(self) -> None:
        """Alt sınıfların kart listesi kurulduktan sonra çalışacak kancası."""

    def _update_empty_text(self) -> None:
        key = (
            self.empty_key
            if not self._all_documents
            else "common.no_results"
        )

        self._empty_label.setText(self._language_manager.tr(key))

    def _document_by_id(self, document_id: str) -> Document | None:
        for document in self._all_documents:
            if document.id == document_id:
                return document

        return None

    # ------------------------------------------------------------------
    # Toplu seçim
    # ------------------------------------------------------------------

    def _visible_ids(self) -> list[str]:
        return [card.document_id for card in self._cards]

    def _set_selection_mode(self, enabled: bool) -> None:
        self._selection_mode = enabled

        if not enabled:
            self._selected_ids.clear()

        self._selection_bar.setVisible(enabled)

        for card in self._cards:
            card.set_selection_mode(enabled)

        self.retranslate_ui()
        self.apply_theme()

    def _on_card_selection_toggled(
        self,
        document_id: str,
        selected: bool,
    ) -> None:
        if selected:
            self._selected_ids.add(document_id)
        else:
            self._selected_ids.discard(document_id)

        self._update_selection_bar()

    def _on_select_all_toggled(self, checked: bool) -> None:
        visible_ids = set(self._visible_ids())

        if checked:
            self._selected_ids |= visible_ids
        else:
            self._selected_ids -= visible_ids

        for card in self._cards:
            card.set_selected(card.document_id in self._selected_ids)

        self._update_selection_bar()

    def _update_selection_bar(self) -> None:
        visible_ids = self._visible_ids()

        selected = sum(
            1 for document_id in visible_ids
            if document_id in self._selected_ids
        )

        self._selection_bar.set_counts(selected, len(visible_ids))

    def _selected_documents(self) -> list[Document]:
        return [
            document
            for document in self._all_documents
            if document.id in self._selected_ids
        ]

    def _on_bulk_action_triggered(self, key: str) -> None:
        documents = self._selected_documents()

        if not documents:
            return

        if self._handle_bulk_action(key, documents):
            self._selected_ids.clear()
            self.refresh()

    # ------------------------------------------------------------------
    # Ortak kart eylemleri
    # ------------------------------------------------------------------

    def _on_favorite_toggled(self, document_id: str) -> None:
        backend_gateway.toggle_favorite(document_id)
        self.refresh()

    def _on_reveal_requested(self, document_id: str) -> None:
        document = self._document_by_id(document_id)

        if document is None:
            return

        try:
            backend_gateway.reveal_in_folder(document.stored_path)

        except backend_gateway.OperationError:
            language_manager = get_language_manager()

            AppDialog.inform(
                self.window(),
                title=language_manager.tr("op.error.reveal_failed_title"),
                body=language_manager.tr("op.error.reveal_failed"),
                variant="danger",
            )

    def _on_trash_requested(self, document_id: str) -> None:
        document = self._document_by_id(document_id)

        if document is None:
            return

        if not self._confirm_move_to_trash([document]):
            return

        try:
            backend_gateway.move_to_trash(document_id)

        except backend_gateway.OperationError as error:
            self.refresh()
            self._show_action_error(error)
            return

        self.refresh()

    def _show_action_error(self, error: "backend_gateway.OperationError") -> None:
        language_manager = self._language_manager

        AppDialog.inform(
            self.window(),
            title=language_manager.tr("trash.action_failed_title"),
            body=language_manager.tr(f"op.error.{error.reason}"),
            variant="danger",
        )

    def _on_restore_requested(self, document_id: str) -> None:
        """Yalnızca çöp kutusu sayfasında anlamlı."""

    def _on_delete_forever_requested(self, document_id: str) -> None:
        """Yalnızca çöp kutusu sayfasında anlamlı."""

    def _confirm(
        self,
        *,
        title_key: str,
        body: str,
        confirm_key: str,
        variant: str = "primary",
        icon_name: str | None = None,
    ) -> bool:
        return AppDialog.ask(
            self,
            title=self._language_manager.tr(title_key),
            body=body,
            confirm_text=self._language_manager.tr(confirm_key),
            variant=variant,
            icon_name=icon_name,
        )

    def _count_or_name_body(
        self,
        documents: list[Document],
        *,
        single_key: str,
        bulk_key: str,
    ) -> str:
        if len(documents) == 1:
            return self._language_manager.tr(single_key).format(
                name=documents[0].display_name
            )

        return self._language_manager.tr(bulk_key).format(
            count=len(documents)
        )

    def _confirm_move_to_trash(self, documents: list[Document]) -> bool:
        return self._confirm(
            title_key="trash.move_confirm_title",
            body=self._count_or_name_body(
                documents,
                single_key="trash.move_confirm_body",
                bulk_key="trash.move_bulk_body",
            ),
            confirm_key="trash.move_confirm_button",
            variant="danger",
            icon_name="fa5s.trash-alt",
        )

    def _bulk_move_to_trash(self, documents: list[Document]) -> bool:
        if not self._confirm_move_to_trash(documents):
            return False

        failed = 0

        for document in documents:
            try:
                backend_gateway.move_to_trash(document.id)

            except backend_gateway.OperationError:
                failed += 1

        if failed:
            self._show_bulk_action_error(
                "trash.move_bulk_failed_body",
                failed=failed,
                total=len(documents),
            )

        return True

    def _show_bulk_action_error(
        self,
        body_key: str,
        *,
        failed: int,
        total: int,
    ) -> None:
        language_manager = self._language_manager

        AppDialog.inform(
            self.window(),
            title=language_manager.tr("trash.action_failed_title"),
            body=language_manager.tr(body_key).format(
                failed=failed, total=total
            ),
            variant="danger",
        )
