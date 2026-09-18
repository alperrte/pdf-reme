from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QKeyEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager


LOGO_PATH = (
    Path(__file__).resolve().parents[2]
    / "resources"
    / "images"
    / "pdf-reme-icon.png"
)

WORD_ITEMS = (
    ("splash.word.read", "blue"),
    ("splash.word.edit", "red"),
    ("splash.word.merge", "purple"),
    ("splash.word.easily", "green"),
)

_CARD_WIDTH = 440
_CARD_HEIGHT = 300
_CARD_MARGIN = 40

_LOGO_FADE_DELAY_MS = 150
_LOGO_FADE_MS = 480

_WORDS_START_DELAY_MS = 750
_WORD_STAGGER_MS = 320
_WORD_DROP_MS = 420
_WORD_DROP_OFFSET = 22

_TOTAL_DURATION_MS = 2800


class SplashScreen(QWidget):
    finished = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

        self.setFixedSize(
            _CARD_WIDTH,
            _CARD_HEIGHT,
        )

        self._language_manager = get_language_manager()

        self._theme_manager = get_theme_manager()

        self._timers: list[QTimer] = []

        self._animations: list[QPropertyAnimation] = []

        self._word_labels: list[QLabel] = []

        self._word_effects: list[QGraphicsOpacityEffect] = []

        self._word_final_rects: list[QRect] = []

        self._is_finished = False

        self._sequence_started = False

        self._setup_ui()

        self._center_on_screen()

    def _setup_ui(
        self,
    ) -> None:
        root_layout = QVBoxLayout(self)

        root_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self._card = QFrame()

        self._card.setObjectName(
            "splashCard"
        )

        tokens = self._theme_manager.tokens()

        self._card.setStyleSheet(
            "#splashCard {"
            f"background-color: {tokens['surface']};"
            f"border: 1px solid {tokens['border']};"
            "border-radius: 22px;"
            "}"
        )

        card_layout = QVBoxLayout(
            self._card
        )

        card_layout.setContentsMargins(
            _CARD_MARGIN,
            _CARD_MARGIN,
            _CARD_MARGIN,
            _CARD_MARGIN,
        )

        card_layout.setSpacing(
            0
        )

        card_layout.addStretch(1)

        self._logo_label = QLabel()

        self._logo_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        pixmap = QPixmap(
            str(LOGO_PATH)
        )

        if not pixmap.isNull():
            self._logo_label.setPixmap(
                pixmap.scaled(
                    88,
                    88,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        self._logo_label.setFixedHeight(
            88
        )

        self._logo_effect = QGraphicsOpacityEffect(
            self._logo_label
        )

        self._logo_effect.setOpacity(
            0.0
        )

        self._logo_label.setGraphicsEffect(
            self._logo_effect
        )

        card_layout.addWidget(
            self._logo_label
        )

        card_layout.addSpacing(
            14
        )

        self._title_label = QLabel(
            "PDF-REME"
        )

        self._title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self._title_label.setStyleSheet(
            f"color: {tokens['text']};"
            "font-family: 'Plus Jakarta Sans';"
            "font-size: 22px;"
            "font-weight: 700;"
            "background: transparent;"
        )

        self._title_effect = QGraphicsOpacityEffect(
            self._title_label
        )

        self._title_effect.setOpacity(
            0.0
        )

        self._title_label.setGraphicsEffect(
            self._title_effect
        )

        card_layout.addWidget(
            self._title_label
        )

        card_layout.addSpacing(
            30
        )

        self._words_container = QWidget()

        self._words_container.setFixedHeight(
            24
        )

        card_layout.addWidget(
            self._words_container
        )

        card_layout.addStretch(1)

        self._build_word_labels()

        root_layout.addWidget(
            self._card
        )

    def _build_word_labels(
        self,
    ) -> None:
        container_width = (
            _CARD_WIDTH
            - (_CARD_MARGIN * 2)
        )

        spacing = 16

        widths: list[int] = []

        for key, accent in WORD_ITEMS:
            label = QLabel(
                self._words_container
            )

            label.setText(
                self._language_manager.tr(key)
            )

            color = self._theme_manager.accent_hex(
                accent
            )

            label.setStyleSheet(
                f"color: {color};"
                "font-family: 'Plus Jakarta Sans SemiBold';"
                "font-size: 13px;"
                "background: transparent;"
            )

            label.adjustSize()

            effect = QGraphicsOpacityEffect(
                label
            )

            effect.setOpacity(
                0.0
            )

            label.setGraphicsEffect(
                effect
            )

            self._word_labels.append(
                label
            )

            self._word_effects.append(
                effect
            )

            widths.append(
                label.width()
            )

        total_width = sum(widths) + spacing * (len(widths) - 1)

        x = max(
            0,
            (container_width - total_width) // 2,
        )

        for label in self._word_labels:
            final_rect = QRect(
                x,
                0,
                label.width(),
                label.height(),
            )

            self._word_final_rects.append(
                final_rect
            )

            start_rect = QRect(
                final_rect.x(),
                final_rect.y() - _WORD_DROP_OFFSET,
                final_rect.width(),
                final_rect.height(),
            )

            label.setGeometry(
                start_rect
            )

            x += label.width() + spacing

    def _center_on_screen(
        self,
    ) -> None:
        screen = QApplication.primaryScreen()

        if screen is None:
            return

        screen_geometry = screen.availableGeometry()

        x = screen_geometry.center().x() - self.width() // 2
        y = screen_geometry.center().y() - self.height() // 2

        self.move(
            x,
            y,
        )

    def showEvent(
        self,
        event,
    ) -> None:
        super().showEvent(event)

        if not self._sequence_started:
            self._sequence_started = True

            self._start_sequence()

    def _start_sequence(
        self,
    ) -> None:
        self._schedule(
            _LOGO_FADE_DELAY_MS,
            lambda: self._fade_in(self._logo_effect),
        )

        self._schedule(
            _LOGO_FADE_DELAY_MS,
            lambda: self._fade_in(self._title_effect),
        )

        for index, (label, effect, final_rect) in enumerate(
            zip(
                self._word_labels,
                self._word_effects,
                self._word_final_rects,
            )
        ):
            delay = _WORDS_START_DELAY_MS + index * _WORD_STAGGER_MS

            self._schedule(
                delay,
                lambda l=label, e=effect, r=final_rect: self._drop_word(
                    l,
                    e,
                    r,
                ),
            )

        self._schedule(
            _TOTAL_DURATION_MS,
            self._finish,
        )

    def _fade_in(
        self,
        effect: QGraphicsOpacityEffect,
    ) -> None:
        animation = QPropertyAnimation(
            effect,
            b"opacity",
            self,
        )

        animation.setDuration(
            _LOGO_FADE_MS
        )

        animation.setStartValue(
            0.0
        )

        animation.setEndValue(
            1.0
        )

        animation.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )

        animation.start()

        self._animations.append(
            animation
        )

    def _drop_word(
        self,
        label: QLabel,
        effect: QGraphicsOpacityEffect,
        final_rect: QRect,
    ) -> None:
        start_rect = QRect(
            final_rect.x(),
            final_rect.y() - _WORD_DROP_OFFSET,
            final_rect.width(),
            final_rect.height(),
        )

        label.setGeometry(
            start_rect
        )

        geometry_animation = QPropertyAnimation(
            label,
            b"geometry",
            self,
        )

        geometry_animation.setDuration(
            _WORD_DROP_MS
        )

        geometry_animation.setStartValue(
            start_rect
        )

        geometry_animation.setEndValue(
            final_rect
        )

        geometry_animation.setEasingCurve(
            QEasingCurve.Type.OutBack
        )

        geometry_animation.start()

        opacity_animation = QPropertyAnimation(
            effect,
            b"opacity",
            self,
        )

        opacity_animation.setDuration(
            _WORD_DROP_MS
        )

        opacity_animation.setStartValue(
            0.0
        )

        opacity_animation.setEndValue(
            1.0
        )

        opacity_animation.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )

        opacity_animation.start()

        self._animations.append(
            geometry_animation
        )

        self._animations.append(
            opacity_animation
        )

    def _schedule(
        self,
        delay_ms: int,
        callback,
    ) -> None:
        timer = QTimer(
            self
        )

        timer.setSingleShot(
            True
        )

        timer.timeout.connect(
            callback
        )

        timer.start(
            delay_ms
        )

        self._timers.append(
            timer
        )

    def _finish(
        self,
    ) -> None:
        if self._is_finished:
            return

        self._is_finished = True

        for timer in self._timers:
            timer.stop()

        for animation in self._animations:
            animation.stop()

        self.finished.emit()

    def mousePressEvent(
        self,
        event: QMouseEvent,
    ) -> None:
        self._finish()

        super().mousePressEvent(
            event
        )

    def keyPressEvent(
        self,
        event: QKeyEvent,
    ) -> None:
        self._finish()

        super().keyPressEvent(
            event
        )
