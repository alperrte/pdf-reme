from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QCheckBox, QStyle, QStyleOptionButton


class OptionCheckBox(QCheckBox):
    """QSS'te resim kullanmadan onay işareti çizen işaret kutusu.

    Kutu görünümü app.qss'teki `#opCheckBox::indicator` kurallarından gelir;
    işaret (✓) burada, seçiliyken kutunun üzerine çizilir.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setObjectName("opCheckBox")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        if not self.isChecked():
            return

        option = QStyleOptionButton()
        self.initStyleOption(option)

        box = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator, option, self
        )

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(
            QColor("#FFFFFF" if self.isEnabled() else "#DDE3EC"),
            2.0,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)

        x, y = box.x(), box.y()
        w, h = box.width(), box.height()

        painter.drawPolyline(
            [
                QPointF(x + w * 0.27, y + h * 0.53),
                QPointF(x + w * 0.44, y + h * 0.70),
                QPointF(x + w * 0.74, y + h * 0.32),
            ]
        )

        painter.end()
