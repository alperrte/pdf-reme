from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractButton, QWidget

from pdf_reme.presentation.theme import DARK_THEME, get_theme_manager


class SelectionCheck(QAbstractButton):
    """Modern, yuvarlatılmış köşeli onay kutusu (kart / toplu seçim için)."""

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._theme_manager = get_theme_manager()

        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(22, 22)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def apply_theme(self) -> None:
        self.update()

    def paintEvent(self, _event) -> None:
        dark = self._theme_manager.current_theme == DARK_THEME

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        box = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)

        if self.isChecked():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(
                QColor(self._theme_manager.accent_hex("blue"))
            )
            painter.drawRoundedRect(box, 6, 6)

            tick = QPainterPath()
            tick.moveTo(box.left() + box.width() * 0.26, box.center().y() + 0.5)
            tick.lineTo(box.left() + box.width() * 0.44, box.top() + box.height() * 0.68)
            tick.lineTo(box.left() + box.width() * 0.76, box.top() + box.height() * 0.32)

            pen = QPen(QColor("#FFFFFF"), 2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(tick)

            return

        border = QColor("#3A4560" if dark else "#C4CEDC")

        if self.underMouse():
            border = QColor(self._theme_manager.accent_hex("blue"))

        painter.setPen(QPen(border, 1.6))
        painter.setBrush(QColor("#171D2C" if dark else "#FFFFFF"))
        painter.drawRoundedRect(box, 6, 6)

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)
