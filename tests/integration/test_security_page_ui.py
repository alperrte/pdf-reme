"""Şifreleme sayfası: göz ikonu imleci/tooltip'i ve parolanın toggle sırasında
asla değişmediğini doğrular.

`test_ui_fix_pack_1.py` ile aynı desen: sunum katmanı gateway'i içe aktarılırken
gerçek uygulama veri klasörünü/veritabanını oluşturduğundan senaryo, veri
klasörü geçici dizine yönlendirilmiş ayrı bir süreçte (offscreen Qt) çalışır.
"""

import os
import subprocess
import sys
from pathlib import Path

PREAMBLE = r"""
import os
import sys
import time
from pathlib import Path

import pdf_reme.shared.paths.app_paths as app_paths

data = Path(os.environ["PDFREME_TEST_DATA"])
app_paths.get_app_data_dir = lambda: data

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLineEdit, QToolButton

app = QApplication(sys.argv)

from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.connection import engine
import pdf_reme.infrastructure.database.models.document  # noqa: F401

assert "pdfreme_test" in str(engine.url)
Base.metadata.create_all(bind=engine)

from pdf_reme.presentation.pages.security_page import SecurityPage


def eye_button(edit: QLineEdit, action) -> QToolButton:
    for button in edit.findChildren(QToolButton):
        if action in button.actions():
            return button
    raise AssertionError("Göz ikonu için dahili QToolButton bulunamadı.")
"""

SCENARIO = r"""
page = SecurityPage()
page.resize(900, 700)
page.show()
page._apply_content_theme()
pump = lambda: app.processEvents()
pump()

edit, action = page._eye_actions[0]

button = eye_button(edit, action)
assert button.cursor().shape() == Qt.CursorShape.PointingHandCursor

edit.setText("gizli-parola-123")

# Başlangıçta parola gizli: tooltip "göster" olmalı.
assert not action.isChecked()
assert action.toolTip() == page._language_manager.tr("security.show_password_action")
assert edit.echoMode() == QLineEdit.EchoMode.Password

# Göster'e bas: echoMode değişir, tooltip "gizle" olur, DEĞER DEĞİŞMEZ.
action.trigger()
pump()

assert action.isChecked()
assert edit.echoMode() == QLineEdit.EchoMode.Normal
assert action.toolTip() == page._language_manager.tr("security.hide_password_action")
assert edit.text() == "gizli-parola-123"

# Tekrar bas: gizliye döner, değer yine değişmez.
action.trigger()
pump()

assert not action.isChecked()
assert edit.echoMode() == QLineEdit.EchoMode.Password
assert action.toolTip() == page._language_manager.tr("security.show_password_action")
assert edit.text() == "gizli-parola-123"

print("SCENARIO OK")
"""


def test_security_eye_action_cursor_tooltip_and_value_preserved(tmp_path):
    src_dir = Path(__file__).resolve().parents[2] / "src"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_dir)
    env["PDFREME_TEST_DATA"] = str(tmp_path / "pdfreme_test_data")
    env["PDF_REME_DATABASE_URL"] = (
        f"sqlite:///{(tmp_path / 'pdfreme_test.db').as_posix()}"
    )
    env["PYTHONIOENCODING"] = "utf-8"
    env["QT_QPA_PLATFORM"] = "offscreen"

    result = subprocess.run(
        [sys.executable, "-c", PREAMBLE + SCENARIO],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "SCENARIO OK" in result.stdout
