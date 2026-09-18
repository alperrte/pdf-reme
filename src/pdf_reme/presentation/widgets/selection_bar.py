from dataclasses import dataclass

import qtawesome as qta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager
from pdf_reme.presentation.widgets.selection_check import SelectionCheck


@dataclass(frozen=True)
class BulkAction:
    key: str
    label_key: str
    icon_name: str
    danger: bool = False


class SelectionBar(QFrame):
    """Toplu seçim modunda listenin üstünde görünen araç çubuğu."""

    select_all_toggled = Signal(bool)
    action_triggered = Signal(str)

    def __init__(
        self,
        actions: list[BulkAction],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._language_manager = get_language_manager()
        self._theme_manager = get_theme_manager()

        self._actions = actions
        self._action_buttons: dict[str, QPushButton] = {}
        self._selected_count = 0

        self.setObjectName("selectionBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 10, 8)
        layout.setSpacing(10)

        self._select_all_check = SelectionCheck()
        self._select_all_check.clicked.connect(
            lambda: self.select_all_toggled.emit(
                self._select_all_check.isChecked()
            )
        )

        self._select_all_label = QPushButton()
        self._select_all_label.setObjectName("selectionBarLabelButton")
        self._select_all_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._select_all_label.setFlat(True)
        self._select_all_label.clicked.connect(self._on_label_clicked)

        self._count_label = QLabel()
        self._count_label.setObjectName("selectionBarCount")

        layout.addWidget(self._select_all_check)
        layout.addWidget(self._select_all_label)
        layout.addWidget(self._count_label)
        layout.addStretch(1)

        for action in actions:
            button = QPushButton()
            button.setObjectName("selectionBarActionButton")
            button.setProperty("danger", action.danger)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, key=action.key: (
                    self.action_triggered.emit(key)
                )
            )

            self._action_buttons[action.key] = button

            layout.addWidget(button)

        self.retranslate_ui()
        self.apply_theme()
        self.set_counts(0, 0)

    def _on_label_clicked(self) -> None:
        self._select_all_check.setChecked(
            not self._select_all_check.isChecked()
        )

        self.select_all_toggled.emit(self._select_all_check.isChecked())

    def set_counts(
        self,
        selected: int,
        total: int,
    ) -> None:
        self._selected_count = selected

        self._select_all_check.setChecked(total > 0 and selected == total)
        self._select_all_check.setEnabled(total > 0)
        self._select_all_label.setEnabled(total > 0)

        self._count_label.setText(
            self._language_manager.tr("selection.count").format(
                count=selected
            )
        )

        for button in self._action_buttons.values():
            button.setEnabled(selected > 0)

    def retranslate_ui(self) -> None:
        self._select_all_label.setText(
            self._language_manager.tr("selection.select_all")
        )

        for action in self._actions:
            self._action_buttons[action.key].setText(
                self._language_manager.tr(action.label_key)
            )

        self._count_label.setText(
            self._language_manager.tr("selection.count").format(
                count=self._selected_count
            )
        )

    def apply_theme(self) -> None:
        self._select_all_check.apply_theme()

        for action in self._actions:
            color = (
                "#E5484D"
                if action.danger
                else self._theme_manager.accent_hex("blue")
            )

            self._action_buttons[action.key].setIcon(
                qta.icon(action.icon_name, color=color)
            )
