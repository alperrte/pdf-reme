import math
import random

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QVariantAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget


_DURATION_MS = 2600

# Güneşin sidebar'daki tema butonuna oturduğunda ulaştığı yarıçap.
_DOCK_RADIUS = 9.0

_SUN_RADIUS = 34.0
_MOON_RADIUS = 30.0
_RAY_COUNT = 12
_STAR_COUNT = 42
_CLOUD_COUNT = 8


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _lerp(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount


def _ease_in_out(value: float) -> float:
    return QEasingCurve(QEasingCurve.Type.InOutSine).valueForProgress(
        _clamp01(value)
    )


def _ease_out(value: float) -> float:
    return QEasingCurve(QEasingCurve.Type.OutCubic).valueForProgress(
        _clamp01(value)
    )


def _ease_in(value: float) -> float:
    return QEasingCurve(QEasingCurve.Type.InQuad).valueForProgress(
        _clamp01(value)
    )


class ThemeTransitionOverlay(QWidget):
    """Tema değişirken eski ve yeni arayüzün anlık görüntüsünü karıştırır.

    Koyu -> açık: güneş sağdan sola bir yay çizerek doğar, ışığı dairesel
    olarak yayılır, sonra küçülerek sidebar'daki tema butonuna oturur.
    Açık -> koyu: ay tema butonundan çıkıp yarım daire çizer, gece
    dairesel olarak yayılır ve ay ekranın sağ altından aşağı düşer. Ağır QSS yeniden uygulaması animasyon
    başlamadan önce yapılır; animasyon sadece iki resmi çizer.
    """

    finished = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self._old = QPixmap()
        self._new = QPixmap()
        self._to_dark = False
        self._target: QPointF | None = None
        self._progress = 0.0

        rng = random.Random(7)

        self._stars = [
            (
                rng.random(),
                rng.random() * 0.7,
                rng.uniform(1.0, 2.2),
                rng.random() * math.tau,
            )
            for _ in range(_STAR_COUNT)
        ]

        # Bulutlar: (x, y, ölçek, hız, yumru sayısı ofsetleri)
        cloud_rng = random.Random(21)

        self._clouds = [
            (
                (index + cloud_rng.uniform(0.0, 0.8)) / _CLOUD_COUNT,
                cloud_rng.uniform(0.02, 0.2),
                cloud_rng.uniform(0.9, 1.5),
                cloud_rng.uniform(0.6, 1.4),
                self._cloud_puffs(cloud_rng),
            )
            for index in range(_CLOUD_COUNT)
        ]

        self._animation = QVariantAnimation(self)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setDuration(_DURATION_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.Linear)
        self._animation.valueChanged.connect(self._on_value_changed)
        self._animation.finished.connect(self._on_finished)

        self.hide()

    @staticmethod
    def _cloud_puffs(rng: random.Random) -> list[tuple[float, float, float]]:
        """Düz tabanlı, ortası kabarık yassı bulut: (dx, dy, yarıçap)."""
        count = 6
        puffs = []

        for index in range(count):
            spot = (index - (count - 1) / 2) / ((count - 1) / 2)  # -1..1
            bulge = 1.0 - abs(spot) ** 1.6

            puffs.append(
                (
                    spot * 2.3 + rng.uniform(-0.15, 0.15),
                    -0.55 * bulge + rng.uniform(-0.08, 0.08),
                    0.55 + 0.5 * bulge + rng.uniform(0.0, 0.12),
                )
            )

        return puffs

    @property
    def is_running(self) -> bool:
        return self._animation.state() == QVariantAnimation.State.Running

    def start(
        self,
        old_frame: QPixmap,
        new_frame: QPixmap,
        *,
        to_dark: bool,
        target: QPointF | None = None,
    ) -> None:
        self._animation.stop()

        self._old = old_frame
        self._new = new_frame
        self._to_dark = to_dark
        self._target = target
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
        self._old = QPixmap()
        self._new = QPixmap()

    # ------------------------------------------------------------------
    # Gökyüzü geometrisi
    # ------------------------------------------------------------------

    def _dock_point(self) -> QPointF:
        if self._target is not None:
            return self._target

        return QPointF(self.width() * 0.08, self.height() * 0.92)

    def _sunrise_state(self, t: float):
        """(merkez, ölçek, ışık yayılımı)"""
        width, height = self.width(), self.height()

        def arc(u: float) -> QPointF:
            # Sağ altta ufuktan çıkar, sola doğru yay çizer.
            return QPointF(
                _lerp(width * 0.9, width * 0.1, u),
                height + _SUN_RADIUS - height * 0.86 * math.sin(math.pi * u),
            )

        split = 0.7
        handoff = 0.78

        if t < split:
            center = arc(handoff * (t / split))
            scale = 1.0
        else:
            d = _ease_out((t - split) / (1.0 - split))

            start = arc(handoff)
            dock = self._dock_point()

            # Yayın sonundan tema butonuna küçülerek iner.
            center = QPointF(
                _lerp(start.x(), dock.x(), d),
                _lerp(start.y(), dock.y(), d),
            )
            scale = _lerp(1.0, _DOCK_RADIUS / _SUN_RADIUS, d)

        return center, scale, _ease_in_out(t / 0.84)

    def _sunset_state(self, t: float):
        """(ay merkezi, ay ölçeği, yayılım)"""
        width, height = self.width(), self.height()

        dock = self._dock_point()
        exit_point = QPointF(width * 0.92, height + _MOON_RADIUS + 24)

        # Sidebar'daki butondan çıkıp yarım daire çizerek ekranın
        # sağ altından aşağı düşer.
        u = _ease_in_out((t - 0.1) / 0.9)

        mid_y = (dock.y() + exit_point.y()) / 2
        rise = mid_y - height * 0.14

        moon_center = QPointF(
            _lerp(dock.x(), exit_point.x(), u),
            _lerp(dock.y(), exit_point.y(), u) - rise * math.sin(math.pi * u),
        )

        moon_scale = _lerp(
            _DOCK_RADIUS / _MOON_RADIUS,
            1.0,
            _ease_out(u / 0.3),
        )

        reveal = _ease_in_out((t - 0.12) / 0.8)

        return moon_center, moon_scale, reveal

    # ------------------------------------------------------------------
    # Çizim
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        if self._old.isNull() or self._new.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        painter.drawPixmap(self.rect(), self._old)

        t = self._progress

        diagonal = math.hypot(self.width(), self.height()) * 1.1

        if self._to_dark:
            moon, moon_scale, reveal = self._sunset_state(t)

            self._paint_dusk(painter, t)
            self._paint_reveal(painter, moon, diagonal * reveal, moon=True)
            self._paint_stars(painter, moon, diagonal * reveal, t)

            self._paint_moon(
                painter,
                moon,
                alpha=_clamp01((t - 0.1) / 0.06),
                scale=moon_scale,
            )

        else:
            sun, scale, reveal = self._sunrise_state(t)

            self._paint_reveal(painter, sun, diagonal * reveal, moon=False)
            self._paint_clouds(painter, sun, diagonal * reveal, t)
            self._paint_dawn(painter, t)

            # Sonda buton ikonuna yumuşakça karışır.
            self._paint_sun(
                painter,
                sun,
                alpha=1.0 - _clamp01((t - 0.93) / 0.07),
                scale=scale,
            )

        painter.end()

    def _paint_reveal(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        *,
        moon: bool,
    ) -> None:
        if radius < 1:
            return

        painter.save()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._new))
        painter.drawEllipse(center, radius, radius)

        # Kenarda yumuşak bir ışık halkası: sert çizgi görünmesin.
        glow = 22.0
        outer = radius + glow

        gradient = QRadialGradient(center, outer)

        edge = (
            QColor(170, 195, 255, 70)
            if moon
            else QColor(255, 214, 140, 90)
        )
        clear = QColor(edge.red(), edge.green(), edge.blue(), 0)

        gradient.setColorAt(0.0, clear)
        gradient.setColorAt(max(0.0, (radius - glow * 0.6) / outer), clear)
        gradient.setColorAt(radius / outer, edge)
        gradient.setColorAt(1.0, clear)

        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(center, outer, outer)

        painter.restore()

    def _paint_dusk(self, painter: QPainter, t: float) -> None:
        strength = math.sin(math.pi * _clamp01(t / 0.62))

        if strength <= 0:
            return

        painter.fillRect(
            self.rect(),
            QColor(255, 110, 60, int(58 * strength)),
        )

    def _paint_dawn(self, painter: QPainter, t: float) -> None:
        strength = math.sin(math.pi * _clamp01(t))

        if strength <= 0:
            return

        painter.fillRect(
            self.rect(),
            QColor(255, 196, 120, int(34 * strength)),
        )

    def _paint_clouds(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        t: float,
    ) -> None:
        if radius < 1:
            return

        # Işık yayılırken belirir, güneş inerken dağılır.
        fade = _clamp01(t / 0.2) * (1.0 - _clamp01((t - 0.62) / 0.3))

        if fade <= 0:
            return

        width, height = self.width(), self.height()

        painter.save()

        clip = QPainterPath()
        clip.addEllipse(center, radius, radius)
        painter.setClipPath(clip)

        painter.setPen(Qt.PenStyle.NoPen)

        for x, y, size, speed, puffs in self._clouds:
            # Sağdan sola, güneşle aynı yönde yavaşça süzülür.
            drift = (x - t * 0.35 * speed) % 1.25 - 0.125

            # Ekranın üstünden aşağı süzülüp yerine oturur.
            enter = (1.0 - _ease_out(t / 0.4)) * height * 0.25

            base = QPointF(drift * width, y * height - enter)
            unit = 40.0 * size

            # Önce alt gölge, sonra beyaz gövde: açık zeminde de görünsün.
            for layer in range(2):
                for dx, dy, grow in puffs:
                    puff_center = QPointF(
                        base.x() + dx * unit,
                        base.y() + dy * unit + (unit * 0.22 if layer == 0 else 0.0),
                    )
                    puff_radius = unit * grow

                    gradient = QRadialGradient(puff_center, puff_radius)

                    if layer == 0:
                        gradient.setColorAt(0.0, QColor(96, 126, 186, int(140 * fade)))
                        gradient.setColorAt(1.0, QColor(96, 126, 186, 0))
                    else:
                        gradient.setColorAt(0.0, QColor(255, 255, 255, int(250 * fade)))
                        gradient.setColorAt(0.55, QColor(212, 226, 250, int(235 * fade)))
                        gradient.setColorAt(1.0, QColor(196, 214, 244, 0))

                    painter.setBrush(QBrush(gradient))
                    painter.drawEllipse(puff_center, puff_radius, puff_radius)

        painter.restore()

    def _paint_stars(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        t: float,
    ) -> None:
        if radius < 1:
            return

        fade = 1.0 - _clamp01((t - 0.84) / 0.16)

        if fade <= 0:
            return

        painter.save()

        clip = QPainterPath()
        clip.addEllipse(center, radius, radius)
        painter.setClipPath(clip)

        painter.setPen(Qt.PenStyle.NoPen)

        for x, y, size, phase in self._stars:
            twinkle = 0.55 + 0.45 * math.sin(t * 9.0 + phase)

            painter.setBrush(QColor(255, 255, 255, int(210 * twinkle * fade)))
            painter.drawEllipse(
                QPointF(x * self.width(), y * self.height()),
                size,
                size,
            )

        painter.restore()

    def _paint_sun(
        self,
        painter: QPainter,
        center: QPointF,
        *,
        alpha: float,
        scale: float = 1.0,
    ) -> None:
        painter.save()
        painter.translate(center)
        painter.scale(scale, scale)
        center = QPointF(0.0, 0.0)

        painter.setPen(Qt.PenStyle.NoPen)

        halo_radius = _SUN_RADIUS * 3.4
        halo = QRadialGradient(center, halo_radius)
        halo.setColorAt(0.0, QColor(255, 214, 90, int(150 * alpha)))
        halo.setColorAt(0.4, QColor(255, 170, 60, int(55 * alpha)))
        halo.setColorAt(1.0, QColor(255, 150, 40, 0))

        painter.setBrush(QBrush(halo))
        painter.drawEllipse(center, halo_radius, halo_radius)

        # Işınlar yavaşça döner.
        painter.setPen(
            QPen(
                QColor(255, 196, 64, int(230 * alpha)),
                3.2,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        )

        spin = self._progress * math.tau * 0.6

        for index in range(_RAY_COUNT):
            angle = spin + index * math.tau / _RAY_COUNT

            cos, sin = math.cos(angle), math.sin(angle)

            painter.drawLine(
                QPointF(
                    center.x() + cos * _SUN_RADIUS * 1.35,
                    center.y() + sin * _SUN_RADIUS * 1.35,
                ),
                QPointF(
                    center.x() + cos * _SUN_RADIUS * 1.75,
                    center.y() + sin * _SUN_RADIUS * 1.75,
                ),
            )

        painter.setPen(Qt.PenStyle.NoPen)

        core = QRadialGradient(
            QPointF(center.x() - 8, center.y() - 8),
            _SUN_RADIUS * 1.3,
        )
        core.setColorAt(0.0, QColor(255, 244, 170, int(255 * alpha)))
        core.setColorAt(0.6, QColor(255, 200, 60, int(255 * alpha)))
        core.setColorAt(1.0, QColor(255, 150, 30, int(255 * alpha)))

        painter.setBrush(QBrush(core))
        painter.drawEllipse(center, _SUN_RADIUS, _SUN_RADIUS)

        painter.restore()

    def _paint_moon(
        self,
        painter: QPainter,
        center: QPointF,
        *,
        alpha: float,
        scale: float = 1.0,
    ) -> None:
        if alpha <= 0:
            return

        painter.save()
        painter.translate(center)
        painter.scale(scale, scale)
        center = QPointF(0.0, 0.0)

        painter.setPen(Qt.PenStyle.NoPen)

        halo_radius = _MOON_RADIUS * 3.6
        halo = QRadialGradient(center, halo_radius)
        halo.setColorAt(0.0, QColor(190, 210, 255, int(120 * alpha)))
        halo.setColorAt(0.45, QColor(140, 170, 255, int(40 * alpha)))
        halo.setColorAt(1.0, QColor(120, 150, 255, 0))

        painter.setBrush(QBrush(halo))
        painter.drawEllipse(center, halo_radius, halo_radius)

        disc = QPainterPath()
        disc.addEllipse(center, _MOON_RADIUS, _MOON_RADIUS)

        bite = QPainterPath()
        bite.addEllipse(
            QPointF(
                center.x() + _MOON_RADIUS * 0.55,
                center.y() - _MOON_RADIUS * 0.25,
            ),
            _MOON_RADIUS * 0.88,
            _MOON_RADIUS * 0.88,
        )

        crescent = disc.subtracted(bite)

        body = QRadialGradient(
            QPointF(center.x() - 10, center.y() + 4),
            _MOON_RADIUS * 1.4,
        )
        body.setColorAt(0.0, QColor(250, 250, 240, int(255 * alpha)))
        body.setColorAt(1.0, QColor(205, 218, 245, int(255 * alpha)))

        painter.setBrush(QBrush(body))
        painter.drawPath(crescent)

        painter.restore()
