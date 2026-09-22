from pathlib import Path

import qtawesome as qta
from pypdf import PdfReader

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation import backend_gateway
from pdf_reme.presentation.pages.pdf_tool_page import PdfToolPage
from pdf_reme.presentation.widgets.app_dialog import AppDialog
from pdf_reme.presentation.widgets.option_check_box import OptionCheckBox

_ENCRYPT_INDEX = 0
_DECRYPT_INDEX = 1


class SecurityPage(PdfToolPage):
    """Şifreleme ve kilit açma tek sayfada; dosyanın durumuna göre form seçilir."""

    KEY = "security"
    MULTIPLE = False
    ICON = "fa5s.lock"
    ACCENT = "purple"
    ALLOW_ENCRYPTED = True

    def _init_state(self) -> None:
        self._file_row: QWidget | None = None
        self._eye_actions: list[tuple[QLineEdit, QAction]] = []
        self._running_encrypt = False
        self._pending_source_path: str | None = None
        self._pending_trash_library = False
        self._pending_remove_source = False

    def _build_content(self) -> QWidget:
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self._file_holder = QVBoxLayout()
        self._file_holder.setContentsMargins(0, 0, 0, 0)

        layout.addLayout(self._file_holder)

        # Algılanan durum rozeti
        self._kind_badge = QFrame()
        self._kind_badge.setObjectName("convertKindBadge")

        badge_layout = QHBoxLayout(self._kind_badge)
        badge_layout.setContentsMargins(12, 6, 14, 6)
        badge_layout.setSpacing(8)

        self._kind_icon_label = QLabel()
        self._kind_icon_label.setObjectName("convertKindIcon")

        self._kind_text_label = QLabel()
        self._kind_text_label.setObjectName("convertKindText")

        badge_layout.addWidget(self._kind_icon_label)
        badge_layout.addWidget(self._kind_text_label)

        badge_row = QHBoxLayout()
        badge_row.addWidget(self._kind_badge)
        badge_row.addStretch(1)

        layout.addLayout(badge_row)

        # Formlar
        card = QFrame()
        card.setObjectName("opCard")
        card.setMaximumWidth(600)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(0)

        self._form_stack = QStackedWidget()
        self._form_stack.addWidget(self._build_encrypt_form())
        self._form_stack.addWidget(self._build_decrypt_form())

        card_layout.addWidget(self._form_stack)

        card_row = QHBoxLayout()
        card_row.addWidget(card)
        card_row.addStretch(1)

        layout.addLayout(card_row)
        layout.addStretch(1)

        return page

    def _password_input(self) -> QLineEdit:
        edit = self._make_line_edit()
        edit.setEchoMode(QLineEdit.EchoMode.Password)

        action = QAction(edit)
        action.setCheckable(True)
        action.toggled.connect(
            lambda shown, target=edit: target.setEchoMode(
                QLineEdit.EchoMode.Normal
                if shown
                else QLineEdit.EchoMode.Password
            )
        )
        action.toggled.connect(lambda _shown: self._apply_eye_icons())

        edit.addAction(action, QLineEdit.ActionPosition.TrailingPosition)

        # `QAction`'ın kendisi `setCursor()` sunmaz; Qt'nin bu action için
        # oluşturduğu dahili buton gerçek bir widget'tır — imleç oraya uygulanır.
        for button in edit.findChildren(QToolButton):
            if action in button.actions():
                button.setCursor(Qt.CursorShape.PointingHandCursor)

        self._eye_actions.append((edit, action))

        return edit

    def _build_encrypt_form(self) -> QWidget:
        form = QWidget()

        column = QVBoxLayout(form)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(14)

        self._enc_password = self._password_input()
        self._enc_confirm = self._password_input()
        self._enc_owner = self._password_input()
        self._enc_name = self._make_line_edit()

        for edit in (
            self._enc_password,
            self._enc_confirm,
            self._enc_owner,
            self._enc_name,
        ):
            edit.textChanged.connect(self._update_action)

        password_field, self._enc_password_caption = self._make_field(
            self._enc_password
        )
        confirm_field, self._enc_confirm_caption = self._make_field(
            self._enc_confirm
        )
        owner_field, self._enc_owner_caption = self._make_field(
            self._enc_owner
        )
        name_field, self._enc_name_caption = self._make_field(self._enc_name)

        self._enc_owner_hint = QLabel()
        self._enc_owner_hint.setObjectName("opHint")
        self._enc_owner_hint.setWordWrap(True)

        self._enc_warning = QLabel()
        self._enc_warning.setObjectName("opWarning")
        self._enc_warning.setWordWrap(True)
        self._enc_warning.hide()

        self._enc_trash_library_check = OptionCheckBox()
        self._enc_trash_library_check.setChecked(True)

        self._enc_remove_source_check = OptionCheckBox()
        self._enc_remove_source_check.setChecked(True)

        self._enc_button = QPushButton()
        self._enc_button.setObjectName("opPrimaryButton")
        self._enc_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._enc_button.clicked.connect(self._on_encrypt)

        column.addWidget(password_field)
        column.addWidget(confirm_field)
        column.addWidget(self._enc_warning)
        column.addWidget(owner_field)
        column.addWidget(self._enc_owner_hint)
        column.addWidget(name_field)
        column.addWidget(self._enc_trash_library_check)
        column.addWidget(self._enc_remove_source_check)
        column.addWidget(self._enc_button, 0, Qt.AlignmentFlag.AlignRight)

        return form

    def _build_decrypt_form(self) -> QWidget:
        form = QWidget()

        column = QVBoxLayout(form)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(14)

        self._dec_password = self._password_input()
        self._dec_name = self._make_line_edit()

        for edit in (self._dec_password, self._dec_name):
            edit.textChanged.connect(self._update_action)

        self._dec_password.returnPressed.connect(self._on_decrypt)

        password_field, self._dec_password_caption = self._make_field(
            self._dec_password
        )
        name_field, self._dec_name_caption = self._make_field(self._dec_name)

        self._dec_button = QPushButton()
        self._dec_button.setObjectName("opPrimaryButton")
        self._dec_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dec_button.clicked.connect(self._on_decrypt)

        column.addWidget(password_field)
        column.addWidget(name_field)
        column.addWidget(self._dec_button, 0, Qt.AlignmentFlag.AlignRight)

        return form

    # ------------------------------------------------------------------
    # Durum
    # ------------------------------------------------------------------

    def _is_encrypted(self) -> bool:
        if not self._paths:
            return False

        info = self._infos.get(self._paths[0])

        return bool(info and info.encrypted)

    def _clear_passwords(self) -> None:
        for edit in (
            self._enc_password,
            self._enc_confirm,
            self._enc_owner,
            self._dec_password,
        ):
            edit.clear()

        for _edit, action in self._eye_actions:
            action.setChecked(False)

    def _on_files_changed(self) -> None:
        self._clear_passwords()

        if not self._paths:
            self._enc_name.clear()
            self._dec_name.clear()
            return

        stem = Path(self._paths[0]).stem

        self._enc_name.setText(f"{stem}_sifreli")
        self._dec_name.setText(f"{stem}_kilitsiz")

    def _refresh_content(self) -> None:
        tr = self._language_manager.tr

        if self._file_row is not None:
            self._file_holder.removeWidget(self._file_row)
            self._file_row.deleteLater()
            self._file_row = None

        if self._paths:
            self._file_row = self._build_file_row(self._paths[0])
            self._file_holder.addWidget(self._file_row)

        encrypted = self._is_encrypted()

        self._form_stack.setCurrentIndex(
            _DECRYPT_INDEX if encrypted else _ENCRYPT_INDEX
        )

        self._kind_badge.setProperty(
            "accentColor", "orange" if encrypted else "blue"
        )
        self._repolish(self._kind_badge)

        self._kind_icon_label.setPixmap(
            qta.icon(
                "fa5s.lock" if encrypted else "fa5s.lock-open",
                color=self._theme_manager.accent_hex(
                    "orange" if encrypted else "blue"
                ),
            ).pixmap(16, 16)
        )
        self._kind_text_label.setText(
            tr("security.badge.encrypted")
            if encrypted
            else tr("security.badge.plain")
        )

        self._update_action()

    def _update_action(self) -> None:
        busy = self._runner.is_running
        tr = self._language_manager.tr

        password = self._enc_password.text()
        confirm = self._enc_confirm.text()

        mismatch = bool(confirm) and password != confirm

        self._enc_warning.setText(tr("security.mismatch") if mismatch else "")
        self._enc_warning.setVisible(mismatch)

        self._enc_button.setEnabled(
            bool(self._paths)
            and not self._is_encrypted()
            and bool(password.strip())
            and password == confirm
            and bool(self._enc_name.text().strip())
            and not busy
        )

        self._dec_button.setEnabled(
            bool(self._paths)
            and self._is_encrypted()
            and bool(self._dec_password.text())
            and bool(self._dec_name.text().strip())
            and not busy
        )

    def _retranslate_content(self) -> None:
        tr = self._language_manager.tr

        self._enc_password_caption.setText(tr("security.password"))
        self._enc_confirm_caption.setText(tr("security.password_confirm"))
        self._enc_owner_caption.setText(tr("security.owner_password"))
        self._enc_owner_hint.setText(tr("security.owner_hint"))
        self._enc_name_caption.setText(tr("security.output_name"))
        self._enc_trash_library_check.setText(
            tr("security.cleanup_trash_library")
        )
        self._enc_remove_source_check.setText(
            tr("security.cleanup_remove_source")
        )
        self._enc_button.setText(tr("security.encrypt_action"))

        self._dec_password_caption.setText(tr("security.password_open"))
        self._dec_name_caption.setText(tr("security.output_name"))
        self._dec_button.setText(tr("security.decrypt_action"))

        for _edit, action in self._eye_actions:
            action.setToolTip(self._eye_tooltip(action))

        self._enc_owner.setPlaceholderText(tr("security.owner_placeholder"))

    def _eye_tooltip(self, action: QAction) -> str:
        tr = self._language_manager.tr

        return (
            tr("security.hide_password_action")
            if action.isChecked()
            else tr("security.show_password_action")
        )

    def _apply_eye_icons(self) -> None:
        color = self._theme_manager.icon_color()

        for _edit, action in self._eye_actions:
            action.setIcon(
                qta.icon(
                    "fa5s.eye-slash" if action.isChecked() else "fa5s.eye",
                    color=color,
                )
            )
            action.setToolTip(self._eye_tooltip(action))

    def _apply_content_theme(self) -> None:
        self._apply_eye_icons()

        self._enc_button.setIcon(qta.icon("fa5s.lock", color="#FFFFFF"))
        self._dec_button.setIcon(qta.icon("fa5s.lock-open", color="#FFFFFF"))

    # ------------------------------------------------------------------
    # İşlem
    # ------------------------------------------------------------------

    def _on_encrypt(self) -> None:
        if not self._enc_button.isEnabled():
            return

        tr = self._language_manager.tr

        path = self._paths[0]
        name = self._enc_name.text().strip()
        password = self._enc_password.text()
        owner = self._enc_owner.text()

        self._running_encrypt = True
        self._pending_source_path = path
        self._pending_trash_library = self._enc_trash_library_check.isChecked()
        self._pending_remove_source = self._enc_remove_source_check.isChecked()

        self._run_task(
            lambda: backend_gateway.encrypt_pdf(path, name, password, owner),
            tr("security.busy_encrypt"),
        )
        self._update_action()

    def _on_decrypt(self) -> None:
        if not self._dec_button.isEnabled():
            return

        tr = self._language_manager.tr

        path = self._paths[0]
        name = self._dec_name.text().strip()
        password = self._dec_password.text()

        self._running_encrypt = False

        self._run_task(
            lambda: backend_gateway.decrypt_pdf(path, name, password),
            tr("security.busy_decrypt"),
        )
        self._update_action()

    def _handle_result(self, document) -> None:
        tr = self._language_manager.tr

        # Parolalar iş biter bitmez temizlenir.
        self._clear_passwords()

        if self._running_encrypt:
            self._cleanup_after_encrypt(document)

            title = tr("security.encrypt_success_title")
            body = tr("security.encrypt_success_body")
        else:
            title = tr("security.decrypt_success_title")
            body = tr("security.decrypt_success_body")

        self._show_result(title=title, body=body, documents=[document])

        self.clear_files()

    def _cleanup_after_encrypt(self, document) -> None:
        """Şifreleme sonrası isteğe bağlı temizlik.

        Sıra zorunlu: (1) şifreli çıktı zaten üretildi (buraya gelindiyse
        `encrypt_pdf` başarılı demektir), (2) burada `PdfReader` ile açılabilirliği
        doğrulanır — doğrulama başarısız olursa hiçbir temizlik adımı çalışmaz,
        (3) ancak bundan sonra kütüphane kopyası çöpe taşınır ve/veya kaynak
        dosya (son bir onay istenerek) diskten kaldırılır.
        """
        tr = self._language_manager.tr

        source_path = self._pending_source_path
        trash_library = self._pending_trash_library
        remove_source = self._pending_remove_source

        self._pending_source_path = None
        self._pending_trash_library = False
        self._pending_remove_source = False

        if source_path is None or not (trash_library or remove_source):
            return

        try:
            PdfReader(document.stored_path)

        except Exception:
            # Şifreli çıktı doğrulanamadı; hiçbir temizlik adımı çalıştırılmaz.
            return

        if trash_library:
            library_document = backend_gateway.find_active_document_by_path(
                source_path
            )

            if library_document is not None:
                try:
                    backend_gateway.move_to_trash(library_document.id)

                except backend_gateway.OperationError as error:
                    AppDialog.inform(
                        self,
                        title=tr("trash.action_failed_title"),
                        body=tr(f"op.error.{error.reason}"),
                        variant="danger",
                    )

        if remove_source and not Path(source_path).exists():
            # Kaynak, kütüphane kopyasıyla birlikte zaten çöpe taşınmış
            # (aynı dosya) olabilir; bu durumda yapılacak ek bir şey yok.
            remove_source = False

        if remove_source:
            confirmed = AppDialog.ask(
                self,
                title=tr("security.remove_source_confirm_title"),
                body=tr("security.remove_source_confirm_body"),
                confirm_text=tr("security.remove_source_confirm_button"),
                variant="danger",
            )

            if not confirmed:
                return

            try:
                Path(source_path).unlink()

            except OSError:
                AppDialog.inform(
                    self,
                    title=tr("security.remove_source_failed_title"),
                    body=tr("security.remove_source_failed_body"),
                    variant="danger",
                )

    def _handle_error_reason(self, reason: str) -> bool:
        tr = self._language_manager.tr

        self._clear_passwords()

        if reason == "wrong_password":
            # Form açık kalır; kullanıcı parolayı yeniden girer.
            AppDialog.inform(
                self,
                title=tr("security.wrong_password_title"),
                body=tr("op.error.wrong_password"),
                variant="danger",
                icon_name="fa5s.exclamation",
            )

            self._dec_password.setFocus()

            return True

        return False
