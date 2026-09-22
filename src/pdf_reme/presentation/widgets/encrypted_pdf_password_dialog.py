from pypdf import PdfReader

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pdf_reme.presentation.i18n import get_language_manager

_SHADOW_MARGIN = 26
_DIALOG_WIDTH = 420


class EncryptedPdfPasswordDialog(QDialog):
    """Şifreli bir PDF'i içe aktarmadan önce parolasını isteyen modal.

    Parola yalnızca `path`'teki dosyayı bellekte doğrulamak için kullanılır;
    diske, DB'ye, ayarlara ya da günlüklere hiçbir zaman yazılmaz. Yanlış
    parola girildiğinde diyalog kapanmaz, kullanıcı yeniden dener; [Vazgeç]
    ile o dosya atlanır.
    """

    def __init__(
        self,
        parent: QWidget | None,
        *,
        path: str,
        file_name: str,
    ) -> None:
        super().__init__(parent)

        self._language_manager = get_language_manager()
        self._path = path
        self._result_password: str | None = None

        self.setObjectName("appDialog")
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(_DIALOG_WIDTH + _SHADOW_MARGIN * 2)

        self._setup_ui(file_name)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self, file_name: str) -> None:
        tr = self._language_manager.tr

        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            _SHADOW_MARGIN, _SHADOW_MARGIN, _SHADOW_MARGIN, _SHADOW_MARGIN
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

        title_label = QLabel(tr("library.encrypted_dialog.title"))
        title_label.setObjectName("appDialogTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        body_label = QLabel(
            tr("library.encrypted_dialog.body").format(name=file_name)
        )
        body_label.setObjectName("appDialogBody")
        body_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addSpacing(8)
        layout.addWidget(body_label)
        layout.addSpacing(16)

        self._password = QLineEdit()
        self._password.setObjectName("opInput")
        self._password.setFixedHeight(38)
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText(
            tr("library.encrypted_dialog.placeholder")
        )
        self._password.textEdited.connect(self._on_text_edited)
        self._password.returnPressed.connect(self._on_confirm)

        layout.addWidget(self._password)
        layout.addSpacing(6)

        self._error_label = QLabel(tr("library.encrypted_dialog.wrong_password"))
        self._error_label.setObjectName("opWarning")
        self._error_label.setWordWrap(True)
        self._error_label.hide()

        layout.addWidget(self._error_label)
        layout.addSpacing(14)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        cancel_button = QPushButton(tr("dialog.cancel"))
        cancel_button.setObjectName("appDialogCancelButton")
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_button.clicked.connect(self.reject)

        self._confirm_button = QPushButton(
            tr("library.encrypted_dialog.confirm")
        )
        self._confirm_button.setObjectName("appDialogConfirmButton")
        self._confirm_button.setProperty("variant", "primary")
        self._confirm_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._confirm_button.clicked.connect(self._on_confirm)

        button_row.addWidget(cancel_button, 1)
        button_row.addWidget(self._confirm_button, 1)

        layout.addLayout(button_row)

        self._password.setFocus()

    # ------------------------------------------------------------------
    # Doğrulama
    # ------------------------------------------------------------------

    def _on_text_edited(self, _text: str) -> None:
        self._error_label.hide()

    def _on_confirm(self) -> None:
        password = self._password.text()

        if not password:
            return

        if self._verify(password):
            self._result_password = password
            self._password.clear()
            self.accept()
        else:
            self._error_label.show()
            self._password.selectAll()
            self._password.setFocus()

    def _verify(self, password: str) -> bool:
        try:
            reader = PdfReader(self._path)
            reader.decrypt(password)

            len(reader.pages)

        except Exception:
            return False

        return True

    def done(self, result: int) -> None:
        # Parola metnini pencere kapanır kapanmaz bellekten temizle.
        self._password.clear()

        super().done(result)

    def showEvent(self, event) -> None:
        super().showEvent(event)

        anchor = self.parentWidget()

        if anchor is not None:
            anchor = anchor.window()
            center = anchor.frameGeometry().center()

            geometry = self.frameGeometry()
            geometry.moveCenter(center)

            self.move(geometry.topLeft())

    # ------------------------------------------------------------------
    # Sonuç
    # ------------------------------------------------------------------

    @staticmethod
    def prompt(
        parent: QWidget | None,
        *,
        path: str,
        file_name: str,
    ) -> str | None:
        dialog = EncryptedPdfPasswordDialog(parent, path=path, file_name=file_name)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        return dialog._result_password
