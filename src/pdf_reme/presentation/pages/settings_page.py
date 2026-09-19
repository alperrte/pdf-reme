import logging

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation import app_settings, backend_gateway
from pdf_reme.presentation.app_info import APP_VERSION, GITHUB_URL
from pdf_reme.presentation.backend_gateway import OperationError
from pdf_reme.presentation.document_format import format_file_size
from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager
from pdf_reme.presentation.update_checker import (
    STATUS_NO_RELEASE,
    STATUS_UP_TO_DATE,
    STATUS_UPDATE_AVAILABLE,
    UpdateChecker,
    UpdateResult,
)
from pdf_reme.presentation.widgets.app_dialog import AppDialog
from pdf_reme.presentation.widgets.option_check_box import OptionCheckBox

logger = logging.getLogger(__name__)

_THEMES = ("light", "dark")
_LANGUAGES = ("tr", "en")
_LEVELS = app_settings.COMPRESS_LEVELS

_CONTENT_MAX_WIDTH = 820


class SettingsPage(QWidget):
    """Görünüm, varsayılanlar, depolama/bakım ve güncelleme ayarları."""

    # Araç sayfalarının varsayılanlarını yeniden okuması için.
    defaults_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._language_manager = get_language_manager()
        self._theme_manager = get_theme_manager()

        self._update_url = ""
        self._silent_check = False
        self._last_update_result: UpdateResult | None = None

        self._checker = UpdateChecker(self)
        self._checker.finished.connect(self._on_update_result)

        self._setup_ui()

        self._theme_manager.theme_changed.connect(self._sync_appearance)
        self._language_manager.language_changed.connect(
            self._sync_appearance
        )

        self._load_values()
        self.retranslate_ui()
        self.apply_theme()

    # ------------------------------------------------------------------
    # Arayüz
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 34, 42, 0)
        layout.setSpacing(8)

        self._title_label = QLabel()
        self._title_label.setObjectName("pageTitle")

        self._description_label = QLabel()
        self._description_label.setObjectName("pageDescription")
        self._description_label.setWordWrap(True)

        layout.addWidget(self._title_label)
        layout.addWidget(self._description_label)
        layout.addSpacing(14)

        scroll = QScrollArea()
        scroll.setObjectName("dashboardScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        content = QWidget()
        content.setObjectName("dashboardContent")

        outer = QHBoxLayout(content)
        outer.setContentsMargins(0, 0, 12, 34)

        column_holder = QWidget()
        column_holder.setMaximumWidth(_CONTENT_MAX_WIDTH)

        column = QVBoxLayout(column_holder)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(14)

        column.addWidget(self._build_appearance_card())
        column.addWidget(self._build_defaults_card())
        column.addWidget(self._build_storage_card())
        column.addWidget(self._build_about_card())
        column.addStretch(1)

        outer.addWidget(column_holder, 1)
        outer.addStretch(0)

        scroll.setWidget(content)

        layout.addWidget(scroll, 1)

    def _card(self, title_attr: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("opCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 18, 22, 20)
        card_layout.setSpacing(14)

        title = QLabel()
        title.setObjectName("settingsSectionTitle")

        setattr(self, title_attr, title)

        card_layout.addWidget(title)

        return card, card_layout

    def _caption(self) -> QLabel:
        label = QLabel()
        label.setObjectName("opFieldLabel")

        return label

    def _hint(self) -> QLabel:
        label = QLabel()
        label.setObjectName("opHint")
        label.setWordWrap(True)

        return label

    def _button(self, callback) -> QPushButton:
        button = QPushButton()
        button.setObjectName("opSecondaryButton")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(callback)

        return button

    def _segment(
        self,
        keys: tuple[str, ...],
        callback,
    ) -> tuple[QWidget, QLabel, dict[str, QPushButton]]:
        container = QWidget()

        column = QVBoxLayout(container)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)

        caption = self._caption()

        group = QButtonGroup(container)
        group.setExclusive(True)

        row = QHBoxLayout()
        row.setSpacing(0)

        buttons: dict[str, QPushButton] = {}

        for position, key in enumerate(keys):
            button = QPushButton()
            button.setObjectName("opSegment")

            if position == 0:
                segment = "first"
            elif position == len(keys) - 1:
                segment = "last"
            else:
                segment = "middle"

            button.setProperty("segmentPosition", segment)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _=False, value=key: callback(value)
            )

            group.addButton(button)
            row.addWidget(button)

            buttons[key] = button

        row.addStretch(1)

        column.addWidget(caption)
        column.addLayout(row)

        return container, caption, buttons

    def _build_appearance_card(self) -> QFrame:
        card, layout = self._card("_appearance_title")

        row = QHBoxLayout()
        row.setSpacing(32)

        theme_field, self._theme_caption, self._theme_buttons = (
            self._segment(_THEMES, self._on_theme_chosen)
        )
        language_field, self._language_caption, self._language_buttons = (
            self._segment(_LANGUAGES, self._on_language_chosen)
        )

        row.addWidget(theme_field)
        row.addWidget(language_field)
        row.addStretch(1)

        layout.addLayout(row)

        self._animation_check = OptionCheckBox()
        self._animation_check.toggled.connect(
            app_settings.set_startup_animation
        )

        self._theme_animation_check = OptionCheckBox()
        self._theme_animation_check.toggled.connect(
            app_settings.set_theme_animation
        )

        self._language_animation_check = OptionCheckBox()
        self._language_animation_check.toggled.connect(
            app_settings.set_language_animation
        )

        layout.addWidget(self._animation_check)
        layout.addWidget(self._theme_animation_check)
        layout.addWidget(self._language_animation_check)

        return card

    def _build_defaults_card(self) -> QFrame:
        card, layout = self._card("_defaults_title")

        level_field, self._level_caption, self._level_buttons = (
            self._segment(_LEVELS, self._on_level_chosen)
        )

        layout.addWidget(level_field)

        self._keep_rest_check = OptionCheckBox()
        self._keep_rest_check.toggled.connect(self._on_keep_rest_toggled)

        layout.addWidget(self._keep_rest_check)

        return card

    def _build_storage_card(self) -> QFrame:
        card, layout = self._card("_storage_title")

        self._data_caption = self._caption()

        self._data_path_label = QLabel()
        self._data_path_label.setObjectName("settingsValue")
        self._data_path_label.setWordWrap(True)
        self._data_path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._open_data_button = self._button(self._on_open_data_folder)

        path_row = QHBoxLayout()
        path_row.setSpacing(12)
        path_row.addWidget(self._data_path_label, 1)
        path_row.addWidget(self._open_data_button, 0)

        layout.addWidget(self._data_caption)
        layout.addLayout(path_row)

        self._library_label = self._hint()
        self._trash_label = self._hint()
        self._temp_label = self._hint()

        summary = QVBoxLayout()
        summary.setSpacing(4)
        summary.addWidget(self._library_label)
        summary.addWidget(self._trash_label)
        summary.addWidget(self._temp_label)

        layout.addLayout(summary)

        self._clear_trash_button = self._button(self._on_clear_trash)
        self._clear_temp_button = self._button(self._on_clear_temp)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addWidget(self._clear_trash_button)
        buttons.addWidget(self._clear_temp_button)
        buttons.addStretch(1)

        layout.addLayout(buttons)

        self._storage_status = self._hint()
        self._storage_status.hide()

        layout.addWidget(self._storage_status)

        return card

    def _build_about_card(self) -> QFrame:
        card, layout = self._card("_about_title")

        self._version_label = QLabel()
        self._version_label.setObjectName("settingsValue")

        layout.addWidget(self._version_label)

        self._check_button = QPushButton()
        self._check_button.setObjectName("opPrimaryButton")
        self._check_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._check_button.clicked.connect(self._on_check_clicked)

        self._download_button = self._button(self._on_open_download)
        self._download_button.hide()

        update_row = QHBoxLayout()
        update_row.setSpacing(10)
        update_row.addWidget(self._check_button)
        update_row.addWidget(self._download_button)
        update_row.addStretch(1)

        layout.addLayout(update_row)

        self._update_status = self._hint()
        self._update_status.hide()

        layout.addWidget(self._update_status)

        self._auto_update_check = OptionCheckBox()
        self._auto_update_check.toggled.connect(
            app_settings.set_auto_update_check
        )

        self._auto_update_hint = self._hint()

        layout.addWidget(self._auto_update_check)
        layout.addWidget(self._auto_update_hint)

        self._open_logs_button = self._button(self._on_open_logs)
        self._open_github_button = self._button(self._on_open_github)

        links = QHBoxLayout()
        links.setSpacing(10)
        links.addWidget(self._open_logs_button)
        links.addWidget(self._open_github_button)
        links.addStretch(1)

        layout.addLayout(links)

        return card

    # ------------------------------------------------------------------
    # Değerler / senkron
    # ------------------------------------------------------------------

    def _load_values(self) -> None:
        self._animation_check.setChecked(app_settings.startup_animation())
        self._theme_animation_check.setChecked(app_settings.theme_animation())
        self._language_animation_check.setChecked(
            app_settings.language_animation()
        )
        self._keep_rest_check.setChecked(app_settings.split_keep_rest())
        self._auto_update_check.setChecked(app_settings.auto_update_check())

        self._level_buttons[app_settings.default_compress_level()].setChecked(
            True
        )

        self._sync_appearance()

    def _sync_appearance(self, *_args) -> None:
        """Kenar çubuğundaki tema/dil düğmeleri de değişimi tetikleyebilir."""
        theme = self._theme_manager.current_theme
        language = self._language_manager.current_language

        if theme in self._theme_buttons:
            self._theme_buttons[theme].setChecked(True)

        if language in self._language_buttons:
            self._language_buttons[language].setChecked(True)

    def refresh(self) -> None:
        """Sayfa her açıldığında depolama özetini tazeler."""
        tr = self._language_manager.tr

        try:
            summary = backend_gateway.storage_summary()

        except Exception:
            logger.exception("Depolama özeti alınamadı")
            return

        self._data_path_label.setText(summary.data_dir)
        self._logs_dir = summary.logs_dir

        self._library_label.setText(
            tr("settings.storage_library").format(
                files=summary.library_files,
                size=format_file_size(summary.library_bytes),
            )
        )
        self._trash_label.setText(
            tr("settings.storage_trash").format(count=summary.trash_count)
        )
        self._temp_label.setText(
            tr("settings.storage_temp").format(
                size=format_file_size(summary.temp_bytes)
            )
        )

        self._clear_trash_button.setEnabled(summary.trash_count > 0)
        self._clear_temp_button.setEnabled(summary.temp_bytes > 0)

    # ------------------------------------------------------------------
    # Kullanıcı eylemleri
    # ------------------------------------------------------------------

    def _on_theme_chosen(self, theme: str) -> None:
        self._theme_manager.set_theme(theme)

    def _on_language_chosen(self, language: str) -> None:
        self._language_manager.set_language(language)

    def _on_level_chosen(self, level: str) -> None:
        app_settings.set_default_compress_level(level)
        self.defaults_changed.emit()

    def _on_keep_rest_toggled(self, enabled: bool) -> None:
        app_settings.set_split_keep_rest(enabled)
        self.defaults_changed.emit()

    def _show_storage_status(self, text: str) -> None:
        self._storage_status.setText(text)
        self._storage_status.show()

    def _on_open_data_folder(self) -> None:
        self._open_folder(self._data_path_label.text())

    def _on_open_logs(self) -> None:
        self._open_folder(getattr(self, "_logs_dir", ""))

    def _open_folder(self, path: str) -> None:
        tr = self._language_manager.tr

        try:
            backend_gateway.open_folder(path)

        except OperationError:
            AppDialog.inform(
                self,
                title=tr("op.error.reveal_failed_title"),
                body=tr("op.error.reveal_failed"),
                variant="danger",
            )

    def _on_clear_trash(self) -> None:
        tr = self._language_manager.tr

        confirmed = AppDialog.ask(
            self,
            title=tr("trash.clear_confirm_title"),
            body=tr("trash.clear_confirm_body"),
            confirm_text=tr("settings.clear_trash"),
            variant="danger",
        )

        if not confirmed:
            return

        try:
            count = backend_gateway.clear_trash()

        except Exception:
            logger.exception("Çöp kutusu boşaltılamadı")
            self._show_action_failed()
            return

        self._show_storage_status(
            tr("settings.clear_trash_done").format(count=count)
        )
        self.refresh()

    def _on_clear_temp(self) -> None:
        tr = self._language_manager.tr

        try:
            freed = backend_gateway.clear_temp_files()

        except Exception:
            logger.exception("Geçici dosyalar temizlenemedi")
            self._show_action_failed()
            return

        self._show_storage_status(
            tr("settings.clear_temp_done").format(
                size=format_file_size(freed)
            )
        )
        self.refresh()

    def _show_action_failed(self) -> None:
        tr = self._language_manager.tr

        AppDialog.inform(
            self,
            title=tr("settings.action_failed_title"),
            body=tr("op.error.unknown"),
            variant="danger",
        )

    def _on_open_github(self) -> None:
        QDesktopServices.openUrl(QUrl(GITHUB_URL))

    def _on_open_download(self) -> None:
        if self._update_url:
            QDesktopServices.openUrl(QUrl(self._update_url))

    # ------------------------------------------------------------------
    # Güncelleme denetimi
    # ------------------------------------------------------------------

    def _on_check_clicked(self) -> None:
        self._start_check(silent=False)

    def run_startup_check(self) -> None:
        """'Açılışta denetle' açıksa sessizce sorgular; yalnız yeni sürümde uyarır."""
        if app_settings.auto_update_check():
            self._start_check(silent=True)

    def _start_check(self, *, silent: bool) -> None:
        if self._checker.is_running:
            return

        tr = self._language_manager.tr

        self._silent_check = silent
        self._last_update_result = None

        if not silent:
            self._check_button.setEnabled(False)
            self._download_button.hide()
            self._update_status.setText(tr("settings.checking"))
            self._update_status.show()

        self._checker.check()

    def _on_update_result(self, result: UpdateResult) -> None:
        self._last_update_result = result
        self._check_button.setEnabled(True)

        if self._silent_check:
            self._silent_check = False

            if result.status == STATUS_UPDATE_AVAILABLE:
                self._prompt_update(result)

            return

        self._show_update_result(result)

    def _show_update_result(self, result: UpdateResult) -> None:
        tr = self._language_manager.tr

        self._update_url = result.url
        self._download_button.setVisible(
            result.status == STATUS_UPDATE_AVAILABLE
        )

        if result.status == STATUS_UPDATE_AVAILABLE:
            text = tr("settings.update_available").format(
                version=result.version
            )
        elif result.status == STATUS_UP_TO_DATE:
            text = tr("settings.update_up_to_date").format(
                version=result.version
            )
        elif result.status == STATUS_NO_RELEASE:
            text = tr("settings.update_no_release")
        else:
            text = tr("settings.update_error")

        self._update_status.setText(text)
        self._update_status.show()

    def _prompt_update(self, result: UpdateResult) -> None:
        tr = self._language_manager.tr

        self._show_update_result(result)

        opened = AppDialog.ask(
            self,
            title=tr("settings.update_available").format(
                version=result.version
            ),
            body=tr("settings.version").format(version=APP_VERSION),
            confirm_text=tr("settings.update_download"),
            cancel_text=tr("settings.update_later"),
            variant="info",
            icon_name="fa5s.download",
        )

        if opened:
            self._on_open_download()

    # ------------------------------------------------------------------
    # Çeviri / tema
    # ------------------------------------------------------------------

    def retranslate_ui(self) -> None:
        tr = self._language_manager.tr

        self._title_label.setText(tr("sidebar.nav.settings"))
        self._description_label.setText(tr("settings.description"))

        self._appearance_title.setText(tr("settings.section.appearance"))
        self._theme_caption.setText(tr("settings.theme"))
        self._language_caption.setText(tr("settings.language"))

        for key, button in self._theme_buttons.items():
            button.setText(tr(f"settings.theme.{key}"))

        for key, button in self._language_buttons.items():
            button.setText(tr(f"settings.language.{key}"))

        self._animation_check.setText(tr("settings.startup_animation"))
        self._theme_animation_check.setText(tr("settings.theme_animation"))
        self._language_animation_check.setText(
            tr("settings.language_animation")
        )

        self._defaults_title.setText(tr("settings.section.defaults"))
        self._level_caption.setText(tr("settings.default_compress"))

        for key, button in self._level_buttons.items():
            button.setText(tr(f"compress.level.{key}"))

        self._keep_rest_check.setText(tr("settings.default_split_keep_rest"))

        self._storage_title.setText(tr("settings.section.storage"))
        self._data_caption.setText(tr("settings.data_folder"))
        self._open_data_button.setText(tr("settings.open_folder"))
        self._clear_trash_button.setText(tr("settings.clear_trash"))
        self._clear_temp_button.setText(tr("settings.clear_temp"))
        self._storage_status.hide()

        self._about_title.setText(tr("settings.section.about"))
        self._version_label.setText(
            tr("settings.version").format(version=APP_VERSION)
        )
        self._check_button.setText(tr("settings.check_updates"))
        self._download_button.setText(tr("settings.update_download"))
        self._auto_update_check.setText(tr("settings.auto_update"))
        self._auto_update_hint.setText(tr("settings.auto_update_hint"))
        self._open_logs_button.setText(tr("settings.open_logs"))
        self._open_github_button.setText(tr("settings.open_github"))

        if self._last_update_result is not None and not (
            self._checker.is_running
        ):
            self._show_update_result(self._last_update_result)
        else:
            self._update_status.hide()

        self.refresh()

    def apply_theme(self) -> None:
        # Bu sayfada tema rengine bağlı ikon yok; QSS `#appRoot[theme]` ile
        # değişir. Arayüz sözleşmesi için (MainWindow döngüsü) korunur.
        pass

    def shutdown(self) -> None:
        pass
