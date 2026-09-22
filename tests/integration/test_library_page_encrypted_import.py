"""Şifreli PDF içe aktarma (Item 6): `LibraryPage._import_paths` seviyesinde
doğru parola / yanlış parola / iptal ve karma parti senaryoları.

`EncryptedPdfPasswordDialog.prompt` gerçek bir modal `exec()` çalıştırır;
offscreen ortamında hiçbir etkileşim onu kapatmayacağından, kullanıcının
diyalogda yapacağı seçim burada bir sahte (`staticmethod`) ile simüle edilir
-- diyaloğun kendi iç mantığı (yanlış parola sonrası yeniden deneme, parola
doğrulama) ayrı olarak `EncryptedPdfPasswordDialog` üzerinde doğrudan test
edilir (bkz. `test_encrypted_pdf_password_dialog.py`). `test_ui_fix_pack_1.py`
ile aynı desen: sunum katmanı gateway'i içe aktarılırken gerçek uygulama veri
klasörünü/veritabanını oluşturduğundan senaryo, veri klasörü geçici dizine
yönlendirilmiş ayrı bir süreçte (offscreen Qt) çalışır.
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

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from pypdf import PdfWriter

from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.connection import engine
import pdf_reme.infrastructure.database.models.document  # noqa: F401

assert "pdfreme_test" in str(engine.url)
Base.metadata.create_all(bind=engine)

from pdf_reme.presentation import backend_gateway
from pdf_reme.presentation.widgets.app_dialog import AppDialog
from pdf_reme.presentation.widgets.encrypted_pdf_password_dialog import (
    EncryptedPdfPasswordDialog,
)
from pdf_reme.presentation.pages.library_page import LibraryPage

files = data / "files"
files.mkdir(parents=True)

# Bilgilendirme diyalogları (sonuç özeti vb.) gerçek bir modal `exec()`
# çalıştırır; offscreen ortamında hiçbir etkileşim onu kapatmayacağından
# testi sonsuza dek bloklar -- `test_security_page_cleanup.py` ile aynı ders.
AppDialog.ask = staticmethod(lambda *a, **k: True)
AppDialog.inform = staticmethod(lambda *a, **k: None)
AppDialog.choose = staticmethod(lambda *a, **k: None)


def pump(ms=200):
    end = time.time() + ms / 1000
    while time.time() < end:
        QCoreApplication.processEvents()
        time.sleep(0.005)


def make_plain_pdf(name):
    path = files / name
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=280)
    with path.open("wb") as handle:
        writer.write(handle)
    return str(path)


def make_encrypted_pdf(name, password="gizli-123"):
    path = files / name
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=280)
    writer.encrypt(user_password=password, owner_password=password)
    with path.open("wb") as handle:
        writer.write(handle)
    return str(path)
"""

# Senaryo 1: tek şifreli dosya, kullanıcı doğru parolayı girer -> içe aktarılır.
SCENARIO_CORRECT_PASSWORD = r"""
locked = make_encrypted_pdf("locked.pdf", password="dogru-parola")

EncryptedPdfPasswordDialog.prompt = staticmethod(
    lambda parent, *, path, file_name: "dogru-parola"
)

page = LibraryPage()
page._import_paths([locked])
pump()

library_docs = backend_gateway.fetch_library_documents()
assert len(library_docs) == 1
assert library_docs[0].display_name == "locked.pdf"

print("SCENARIO OK")
"""

# Senaryo 2: kullanıcı parola diyaloğunu iptal eder -> dosya tamamen atlanır,
# içe aktarma denenmez bile.
SCENARIO_CANCELLED = r"""
locked = make_encrypted_pdf("cancelled.pdf", password="dogru-parola")

EncryptedPdfPasswordDialog.prompt = staticmethod(
    lambda parent, *, path, file_name: None
)

page = LibraryPage()
page._import_paths([locked])
pump()

assert backend_gateway.fetch_library_documents() == []

print("SCENARIO OK")
"""

# Senaryo 3: karma parti -- bir düz PDF + bir şifreli PDF (doğru parolayla) ->
# ikisi de içe aktarılır; parola eşlemesi yalnızca doğru yola uygulanır.
SCENARIO_MIXED_BATCH = r"""
plain = make_plain_pdf("plain.pdf")
locked = make_encrypted_pdf("locked-mixed.pdf", password="dogru-parola")

EncryptedPdfPasswordDialog.prompt = staticmethod(
    lambda parent, *, path, file_name: "dogru-parola"
)

page = LibraryPage()
page._import_paths([plain, locked])
pump()

library_docs = backend_gateway.fetch_library_documents()
names = sorted(doc.display_name for doc in library_docs)
assert names == ["locked-mixed.pdf", "plain.pdf"]

print("SCENARIO OK")
"""


def _run(scenario: str, tmp_path: Path) -> None:
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
        [sys.executable, "-c", PREAMBLE + scenario],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "SCENARIO OK" in result.stdout


def test_import_with_correct_password_succeeds(tmp_path):
    _run(SCENARIO_CORRECT_PASSWORD, tmp_path)


def test_import_cancelled_password_dialog_skips_file(tmp_path):
    _run(SCENARIO_CANCELLED, tmp_path)


def test_import_mixed_batch_plain_and_encrypted(tmp_path):
    _run(SCENARIO_MIXED_BATCH, tmp_path)
