from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager

_SPINNER_SIZE = 44
_SPINNER_STEP_DEGREES = 30


class _Spinner(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._angle = 0
        self._color = QColor("#2563EB")

        self.setFixedSize(_SPINNER_SIZE, _SPINNER_SIZE)

        self._timer = QTimer(self)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._advance)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _advance(self) -> None:
        self._angle = (self._angle + _SPINNER_STEP_DEGREES) % 360
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(self._color, 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        rect = QRectF(4, 4, self.width() - 8, self.height() - 8)

        # Qt açıları 1/16 derece; saat yönünde dönen 100° yay.
        painter.drawArc(rect, -self._angle * 16, -100 * 16)

        faded = QColor(self._color)
        faded.setAlpha(50)
        pen.setColor(faded)
        painter.setPen(pen)
        painter.drawArc(rect, (-self._angle - 100) * 16, -260 * 16)


class BusyOverlay(QFrame):
    """Arka plan işi sürerken sayfayı kilitleyen dönen gösterge katmanı."""

    def __init__(
        self,
        parent: QWidget,
    ) -> None:
        super().__init__(parent)

        self._theme_manager = get_theme_manager()

        self.setObjectName("busyOverlay")
        self.hide()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(14)

        self._spinner = _Spinner()

        self._label = QLabel()
        self._label.setObjectName("busyOverlayLabel")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("busyProgress")
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedSize(280, 8)
        self._progress_bar.hide()

        self._percent_label = QLabel("%0")
        self._percent_label.setObjectName("busyProgressLabel")
        self._percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._percent_label.hide()

        self._detail_label = QLabel()
        self._detail_label.setObjectName("busyOverlayDetail")
        self._detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_label.hide()

        layout.addWidget(self._spinner, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._label)
        layout.addWidget(self._progress_bar, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._percent_label)
        layout.addWidget(self._detail_label)

        self.apply_theme()

    def show_busy(self, text: str, with_progress: bool = False) -> None:
        self._label.setText(text)

        self._progress_bar.setValue(0)
        self._percent_label.setText("%0")
        self._detail_label.setText("")
        self._progress_bar.setVisible(with_progress)
        self._percent_label.setVisible(with_progress)
        self._detail_label.setVisible(False)

        self.setGeometry(self.parentWidget().rect())
        self.raise_()
        self.show()
        self._spinner.start()

    def set_progress(self, percent: int, text: str = "") -> None:
        percent = max(0, min(100, int(percent)))

        self._progress_bar.setValue(percent)
        self._percent_label.setText(
            get_language_manager().tr("common.percent").format(value=percent)
        )

        self._detail_label.setText(text)
        self._detail_label.setVisible(bool(text))

    def hide_busy(self) -> None:
        self._spinner.stop()
        self.hide()

    def apply_theme(self) -> None:
        self._spinner.set_color(self._theme_manager.accent_hex("blue"))

    def mousePressEvent(self, event) -> None:
        # Çalışırken alttaki sayfaya tıklama geçmesin.
        event.accept()

    def keyPressEvent(self, event) -> None:
        event.accept()
