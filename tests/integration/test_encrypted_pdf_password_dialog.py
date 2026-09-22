"""`EncryptedPdfPasswordDialog`'un kendi iç mantığı (Item 6): yanlış parola
girildiğinde diyalog kapanmadan hata gösterir ve yeniden denemeye izin verir;
doğru parola kabul edilir; parola hiçbir yere yazılmadan yalnızca bellekte
doğrulanır.

Bu dosya `library_page.py` seviyesindeki akışı DEĞİL, diyaloğun kendisini
test eder (`test_library_page_encrypted_import.py`, diyaloğu bir sahteyle
değiştirerek `LibraryPage._import_paths` akışını test eder). `dialog.exec()`
gerçek bir modal event loop başlatacağından hiç çağrılmaz; `_on_confirm()`
doğrudan çağrılarak diyaloğun dahili davranışı sınanır -- `test_ui_fix_pack_1.py`
ile aynı offscreen-subprocess desen.
"""

import os
import subprocess
import sys
from pathlib import Path

SCENARIO = r"""
import sys

from pypdf import PdfWriter

from PySide6.QtWidgets import QApplication, QDialog

app = QApplication(sys.argv)

from pdf_reme.presentation.widgets.encrypted_pdf_password_dialog import (
    EncryptedPdfPasswordDialog,
)

path = "locked.pdf"

writer = PdfWriter()
writer.add_blank_page(width=200, height=280)
writer.encrypt(user_password="dogru-parola", owner_password="dogru-parola")

with open(path, "wb") as handle:
    writer.write(handle)

dialog = EncryptedPdfPasswordDialog(None, path=path, file_name="locked.pdf")
dialog.show()  # exec() değil -- modal event loop'a girmeden görünürlüğü test eder.

# Başlangıçta hata etiketi gizli.
assert not dialog._error_label.isVisible()

# Yanlış parola: diyalog kapanmaz, hata gösterilir, parola alanı temizlenmez
# (kullanıcı düzeltebilsin diye seçili kalır) ama sonuç henüz belirlenmemiştir.
dialog._password.setText("yanlis-parola")
dialog._on_confirm()

assert dialog._error_label.isVisible()
assert dialog._result_password is None
assert dialog.result() != QDialog.DialogCode.Accepted

# Hata etiketi, kullanıcı yeniden yazmaya başlayınca gizlenir.
dialog._on_text_edited("y")
assert not dialog._error_label.isVisible()

# Doğru parola: kabul edilir, parola bellekte döndürülür.
dialog._password.setText("dogru-parola")
dialog._on_confirm()

assert dialog._result_password == "dogru-parola"
assert dialog.result() == QDialog.DialogCode.Accepted

# `done()` sonrası parola alanı bellekten temizlenir (ekranda kalmaz).
assert dialog._password.text() == ""

# İptal senaryosu: ayrı bir diyalogda [Vazgeç] sonucu None döner.
cancel_dialog = EncryptedPdfPasswordDialog(
    None, path=path, file_name="locked.pdf"
)
cancel_dialog.show()
cancel_dialog.reject()

assert cancel_dialog.result() == QDialog.DialogCode.Rejected

print("SCENARIO OK")
"""


def test_encrypted_pdf_password_dialog_wrong_then_correct_password(tmp_path):
    src_dir = Path(__file__).resolve().parents[2] / "src"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_dir)
    env["PYTHONIOENCODING"] = "utf-8"
    env["QT_QPA_PLATFORM"] = "offscreen"

    result = subprocess.run(
        [sys.executable, "-c", SCENARIO],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "SCENARIO OK" in result.stdout
