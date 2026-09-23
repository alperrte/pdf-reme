import qtawesome as qta

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.presentation.document_format import (
    format_document_meta,
    type_icon,
)
from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager
from pdf_reme.presentation.widgets.selection_check import SelectionCheck

_SHADOW_MARGIN = 26
_DIALOG_WIDTH = 480
_ROW_HEIGHT = 58
_LIST_HEIGHT = 292


class PdfPickerDialog(QDialog):
    """Kütüphaneden belge seçtirir.

    Varsayılan: tek PDF (ya da bilgisayardan bir dosya). `multi=True`
    ile `types` içindeki türlerden birden çok belge seçilebilir.
    """

    def __init__(
        self,
        parent: QWidget | None,
        *,
        documents: list[Document],
        title: str,
        body: str,
        types: tuple[str, ...] = ("pdf",),
        multi: bool = False,
    ) -> None:
        super().__init__(parent)

        self._language_manager = get_language_manager()
        self._theme_manager = get_theme_manager()

        self._documents = [
            document
            for document in documents
            if document.document_type in types
        ]
        self._multi = multi
        self._selected_path: str | None = None
        self._selected_paths: list[str] = []
        self._row_checks: dict[str, SelectionCheck] = {}

        self.setObjectName("appDialog")
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(_DIALOG_WIDTH + _SHADOW_MARGIN * 2)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            _SHADOW_MARGIN,
            _SHADOW_MARGIN,
            _SHADOW_MARGIN,
            _SHADOW_MARGIN,
        )

        card = QFrame()
        card.setObjectName("appDialogCard")

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(46)
        shadow.setXOffset(0)
        shadow.setYOffset(14)
        shadow.setColor(QColor(0, 0, 0, 90))
        card.setGraphicsEffect(shadow)

        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(0)

        title_label = QLabel(title)
        title_label.setObjectName("appDialogTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)

        body_label = QLabel(body)
        body_label.setObjectName("appDialogBody")
        body_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addSpacing(8)
        layout.addWidget(body_label)
        layout.addSpacing(16)

        layout.addWidget(self._build_list())

        layout.addSpacing(16)

        tr = self._language_manager.tr

        # Çoklu seçimde bilgisayardan seçme sayfanın kendi düğmesindedir.
        computer_button = QPushButton(tr("picker.from_computer"))
        computer_button.setObjectName("pickerComputerButton")
        computer_button.setCursor(Qt.CursorShape.PointingHandCursor)
        computer_button.setIcon(
            qta.icon(
                "fa5s.folder-open",
                color=self._theme_manager.accent_hex("blue"),
            )
        )
        computer_button.clicked.connect(self._on_computer_clicked)

        if not self._multi:
            layout.addWidget(computer_button)
            layout.addSpacing(12)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        cancel_button = QPushButton(tr("dialog.cancel"))
        cancel_button.setObjectName("appDialogCancelButton")
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_button.clicked.connect(self.reject)

        self._confirm_button = QPushButton(
            tr("picker.multi_select" if self._multi else "picker.select")
        )
        self._confirm_button.setObjectName("appDialogConfirmButton")
        self._confirm_button.setProperty("variant", "primary")
        self._confirm_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._confirm_button.setEnabled(False)
        self._confirm_button.clicked.connect(self._on_confirm_clicked)

        button_row.addWidget(cancel_button, 1)
        button_row.addWidget(self._confirm_button, 1)

        layout.addLayout(button_row)

    def _build_list(self) -> QWidget:
        if not self._documents:
            empty_label = QLabel(
                self._language_manager.tr(
                    "picker.multi_empty" if self._multi else "picker.empty"
                )
            )
            empty_label.setObjectName("pickerEmptyText")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setWordWrap(True)
            empty_label.setFixedHeight(96)

            return empty_label

        self._list = QListWidget()
        self._list.setObjectName("pickerList")
        self._list.setFrameShape(QListWidget.Shape.NoFrame)
        self._list.setVerticalScrollMode(
            QListWidget.ScrollMode.ScrollPerPixel
        )
        self._list.setSpacing(4)

        if self._multi:
            self._list.setSelectionMode(
                QListWidget.SelectionMode.MultiSelection
            )
        self._list.setFixedHeight(
            min(
                len(self._documents) * (_ROW_HEIGHT + 4) + 6,
                _LIST_HEIGHT,
            )
        )

        for document in self._documents:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, document.stored_path)
            item.setSizeHint(QSize(0, _ROW_HEIGHT))

            self._list.addItem(item)
            self._list.setItemWidget(item, self._build_row(document))

        self._list.itemSelectionChanged.connect(self._on_selection_changed)

        if not self._multi:
            self._list.itemDoubleClicked.connect(
                lambda _item: self._on_confirm_clicked()
            )

        return self._list

    def _build_row(self, document: Document) -> QWidget:
        row = QFrame()
        row.setObjectName("pickerRow")
        row.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(12, 0, 12, 0)
        row_layout.setSpacing(12)

        if self._multi:
            check = SelectionCheck()
            check.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            row_layout.addWidget(check)
            self._row_checks[document.stored_path] = check

        icon_label = QLabel()
        icon_name, accent = type_icon(document.document_type)

        icon_label.setPixmap(
            qta.icon(
                icon_name,
                color=self._theme_manager.accent_hex(accent),
            ).pixmap(20, 20)
        )

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(1)

        name_label = QLabel(document.display_name)
        name_label.setObjectName("appDialogItemName")

        detail_label = QLabel(
            format_document_meta(document, date=document.created_at)
        )
        detail_label.setObjectName("appDialogItemDetail")

        text_column.addStretch(1)
        text_column.addWidget(name_label)
        text_column.addWidget(detail_label)
        text_column.addStretch(1)

        row_layout.addWidget(icon_label)
        row_layout.addLayout(text_column, 1)

        return row

    def _on_selection_changed(self) -> None:
        selected_items = self._list.selectedItems()
        count = len(selected_items)

        self._confirm_button.setEnabled(count > 0)

        if self._multi:
            tr = self._language_manager.tr

            self._confirm_button.setText(
                tr("picker.multi_confirm").format(count=count)
                if count
                else tr("picker.multi_select")
            )

            selected_paths = {
                item.data(Qt.ItemDataRole.UserRole)
                for item in selected_items
            }

            for row_index in range(self._list.count()):
                item = self._list.item(row_index)
                path = item.data(Qt.ItemDataRole.UserRole)
                is_selected = path in selected_paths

                check = self._row_checks.get(path)
                if check is not None:
                    check.setChecked(is_selected)

                row_widget = self._list.itemWidget(item)
                if row_widget is not None:
                    row_widget.setProperty("selected", is_selected)
                    row_widget.style().unpolish(row_widget)
                    row_widget.style().polish(row_widget)

    def _on_confirm_clicked(self) -> None:
        items = self._list.selectedItems()

        if not items:
            return

        # Seçim sırası listedeki sıraya göre.
        rows = sorted(self._list.row(item) for item in items)
        self._selected_paths = [
            self._list.item(row).data(Qt.ItemDataRole.UserRole)
            for row in rows
        ]
        self._selected_path = self._selected_paths[0]
        self.accept()

    def _on_computer_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._language_manager.tr("picker.computer_dialog_title"),
            "",
            "PDF (*.pdf)",
        )

        if not path:
            return

        self._selected_path = path
        self.accept()

    def showEvent(self, event) -> None:
        super().showEvent(event)

        anchor = self.parentWidget()

        if anchor is not None:
            anchor = anchor.window()
            center = anchor.frameGeometry().center()

            geometry = self.frameGeometry()
            geometry.moveCenter(center)

            self.move(geometry.topLeft())

    @staticmethod
    def pick(
        parent: QWidget | None,
        *,
        documents: list[Document],
        title: str,
        body: str,
    ) -> str | None:
        dialog = PdfPickerDialog(
            parent,
            documents=documents,
            title=title,
            body=body,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        return dialog._selected_path

    @staticmethod
    def pick_many(
        parent: QWidget | None,
        *,
        documents: list[Document],
        types: tuple[str, ...],
        title: str,
        body: str,
    ) -> list[str]:
        dialog = PdfPickerDialog(
            parent,
            documents=documents,
            title=title,
            body=body,
            types=types,
            multi=True,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return []

        return dialog._selected_paths


DocumentPickerDialog = PdfPickerDialog
