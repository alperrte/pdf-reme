import math

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QRectF,
    QVariantAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

from pdf_reme.presentation.widgets.sidebar import FLAGS_DIR


_DURATION_MS = 2400

_FLAG_FILES = {
    "tr": "tr.png",
    "en": "gb.png",
}

_LANGUAGE_NAMES = {
    "tr": "Türkçe",
    "en": "English",
}

_CARD_WIDTH = 150.0
_CARD_HEIGHT = 100.0

# Bulanıklık seviyeleri: küçültme çarpanları (keskin, orta, güçlü).
_BLUR_SCALES = (4, 14)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _ease_in_out(value: float) -> float:
    return QEasingCurve(QEasingCurve.Type.InOutSine).valueForProgress(
        _clamp01(value)
    )


def _ease_out_back(value: float) -> float:
    return QEasingCurve(QEasingCurve.Type.OutBack).valueForProgress(
        _clamp01(value)
    )


class LanguageTransitionOverlay(QWidget):
    """Dil değişirken arka planı bulanıklaştırıp bayrakları çevirir.

    Eski arayüz yavaşça bulanıklaşır, ortada eski bayrak kartı yeni
    bayrağa döner ve bulanıklık çözülürken yeni dildeki arayüz belirir.
    Metin yenileme animasyondan önce yapılır; animasyon sadece
    anlık görüntüleri çizer.
    """

    finished = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self._old_levels: list[QPixmap] = []
        self._new_levels: list[QPixmap] = []
        self._old_flag = QPixmap()
        self._new_flag = QPixmap()
        self._new_name = ""
        self._progress = 0.0

        self._animation = QVariantAnimation(self)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setDuration(_DURATION_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.Linear)
        self._animation.valueChanged.connect(self._on_value_changed)
        self._animation.finished.connect(self._on_finished)

        self.hide()

    @property
    def is_running(self) -> bool:
        return self._animation.state() == QVariantAnimation.State.Running

    def start(
        self,
        old_frame: QPixmap,
        new_frame: QPixmap,
        *,
        old_language: str,
        new_language: str,
    ) -> None:
        self._animation.stop()

        self._old_levels = self._build_levels(old_frame)
        self._new_levels = self._build_levels(new_frame)

        self._old_flag = self._load_flag(old_language)
        self._new_flag = self._load_flag(new_language)
        self._new_name = _LANGUAGE_NAMES.get(new_language, new_language)

        self._progress = 0.0

        self.setGeometry(self.parentWidget().rect())
        self.raise_()
        self.show()

        self._animation.start()

    def stop(self) -> None:
        self._animation.stop()
        self._release()

    def _on_value_changed(self, value) -> None:
        self._progress = float(value)
        self.update()

    def _on_finished(self) -> None:
        self._release()
        self.finished.emit()

    def _release(self) -> None:
        self.hide()
        self._old_levels = []
        self._new_levels = []

    @staticmethod
    def _load_flag(language: str) -> QPixmap:
        return QPixmap(str(FLAGS_DIR / _FLAG_FILES.get(language, "")))

    @staticmethod
    def _build_levels(frame: QPixmap) -> list[QPixmap]:
        """[keskin, orta bulanık, güçlü bulanık] - küçültüp büyüterek."""
        levels = [frame]

        for divisor in _BLUR_SCALES:
            levels.append(
                frame.scaled(
                    max(1, frame.width() // divisor),
                    max(1, frame.height() // divisor),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        return levels

    # ------------------------------------------------------------------
    # Çizim
    # ------------------------------------------------------------------

    def _draw_blurred(
        self,
        painter: QPainter,
        levels: list[QPixmap],
        blur: float,
        opacity: float = 1.0,
    ) -> None:
        """blur 0 -> keskin, 1 -> güçlü bulanık."""
        if opacity <= 0 or not levels:
            return

        position = _clamp01(blur) * (len(levels) - 1)
        index = min(int(position), len(levels) - 2)
        amount = position - index

        rect = self.rect()

        painter.setOpacity(opacity)
        painter.drawPixmap(rect, levels[index])

        painter.setOpacity(opacity * amount)
        painter.drawPixmap(rect, levels[index + 1])

        painter.setOpacity(1.0)

    def paintEvent(self, event) -> None:
        if not self._old_levels or not self._new_levels:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        t = self._progress

        if t < 0.3:
            blur = _ease_in_out(t / 0.3)

            self._draw_blurred(painter, self._old_levels, blur)

        elif t < 0.7:
            mix = _ease_in_out((t - 0.3) / 0.4)

            self._draw_blurred(painter, self._old_levels, 1.0)
            self._draw_blurred(painter, self._new_levels, 1.0, mix)

        else:
            blur = 1.0 - _ease_in_out((t - 0.7) / 0.3)

            self._draw_blurred(painter, self._new_levels, blur)

        # Bulanıklık yoğunken bayrak öne çıksın diye hafif karartma.
        veil = math.sin(math.pi * _clamp01((t - 0.05) / 0.9))

        if veil > 0:
            painter.fillRect(self.rect(), QColor(8, 12, 28, int(70 * veil)))

        self._paint_flag_card(painter, t)

        painter.end()

    def _paint_flag_card(self, painter: QPainter, t: float) -> None:
        appear = _ease_out_back((t - 0.14) / 0.24)
        vanish = 1.0 - _ease_in_out((t - 0.78) / 0.2)

        visibility = min(1.0, appear) * vanish

        if visibility <= 0.01:
            return

        flip = _ease_in_out((t - 0.36) / 0.3)

        angle = math.pi * flip
        squash = abs(math.cos(angle))
        pop = 1.0 + 0.1 * math.sin(angle)

        scale = max(0.01, appear) * (0.5 + 0.5 * vanish) * pop

        showing_new = flip >= 0.5
        flag = self._new_flag if showing_new else self._old_flag

        center = QPointF(self.width() / 2, self.height() / 2 - 18)

        painter.save()
        painter.setOpacity(_clamp01(visibility))

        # Yumuşak gölge
        shadow_radius = _CARD_WIDTH * scale * 0.95
        shadow = QRadialGradient(
            QPointF(center.x(), center.y() + 34 * scale), shadow_radius
        )
        shadow.setColorAt(0.0, QColor(0, 0, 0, 90))
        shadow.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(shadow))
        painter.drawEllipse(
            QPointF(center.x(), center.y() + 34 * scale),
            shadow_radius,
            shadow_radius * 0.4,
        )

        painter.translate(center)
        painter.scale(scale * max(0.02, squash), scale)

        card = QRectF(
            -_CARD_WIDTH / 2, -_CARD_HEIGHT / 2, _CARD_WIDTH, _CARD_HEIGHT
        )

        clip = QPainterPath()
        clip.addRoundedRect(card, 16, 16)

        painter.setClipPath(clip)
        painter.fillRect(card, QColor(255, 255, 255))

        if not flag.isNull():
            painter.drawPixmap(
                card.toRect(),
                flag.scaled(
                    card.toRect().size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                ),
            )

        painter.setClipping(False)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, 230), 3.0))
        painter.drawRoundedRect(card, 16, 16)

        painter.restore()

        # Yeni dilin adı, çevirme bitince belirir.
        name_alpha = _clamp01((t - 0.6) / 0.14) * vanish

        if name_alpha > 0.01:
            painter.save()

            font = QFont(painter.font())
            font.setPixelSize(20)
            font.setBold(True)
            painter.setFont(font)

            text_rect = QRectF(
                0,
                center.y() + _CARD_HEIGHT / 2 + 24,
                self.width(),
                34,
            )

            painter.setPen(QColor(0, 0, 0, int(110 * name_alpha)))
            painter.drawText(
                text_rect.translated(0, 2),
                int(Qt.AlignmentFlag.AlignHCenter),
                self._new_name,
            )

            painter.setPen(QColor(255, 255, 255, int(255 * name_alpha)))
            painter.drawText(
                text_rect,
                int(Qt.AlignmentFlag.AlignHCenter),
                self._new_name,
            )

            painter.restore()
