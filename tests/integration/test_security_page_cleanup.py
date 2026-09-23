"""Şifreleme sonrası temizlik seçenekleri (Item 5): kütüphane kopyasını çöpe
taşıma ve kaynak dosyayı diskten kaldırma.

`test_ui_fix_pack_1.py` ile aynı desen: sunum katmanı gateway'i içe
aktarılırken gerçek uygulama veri klasörünü/veritabanını oluşturduğundan
senaryo, veri klasörü geçici dizine yönlendirilmiş ayrı bir süreçte
(offscreen Qt) çalışır.
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
from pdf_reme.presentation.pages.security_page import SecurityPage

files = data / "files"
files.mkdir(parents=True)

# İşlem sonucu diyaloğu (`AppDialog.choose`) gerçek bir modal `exec()`
# çalıştırır; offscreen ortamında hiçbir etkileşim onu kapatmayacağından
# testi sonsuza dek bloklar -- `test_ui_fix_pack_1.py` ile aynı desen.
AppDialog.choose = staticmethod(lambda *a, **k: None)


def pump(ms=300):
    end = time.time() + ms / 1000
    while time.time() < end:
        QCoreApplication.processEvents()
        time.sleep(0.005)


def wait_idle(page, timeout=60):
    end = time.time() + timeout
    while page._runner.is_running and time.time() < end:
        QCoreApplication.processEvents()
        time.sleep(0.01)
    pump(150)
    assert not page._runner.is_running, "işlem zaman aşımına uğradı"


def make_pdf(name):
    path = files / name
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=280)
    with path.open("wb") as handle:
        writer.write(handle)
    return str(path)
"""

# Senaryo 1: her iki kutu da işaretli (varsayılan) -> kütüphane kopyası çöpe
# taşınır, kaynak dosya diskten kaldırılır (aynı dosya olduğu için tek adımda).
SCENARIO_BOTH_DEFAULT = r"""
source = make_pdf("plain.pdf")

outcomes = backend_gateway.import_documents([source])
assert outcomes[0].status == "imported"

library_docs = backend_gateway.fetch_library_documents()
assert len(library_docs) == 1
imported = library_docs[0]
stored_path = imported.stored_path
assert Path(stored_path).exists()

# Onay istenen tüm diyaloglar otomatik "Evet" der.
AppDialog.ask = staticmethod(lambda *a, **k: True)
AppDialog.inform = staticmethod(lambda *a, **k: None)

page = SecurityPage()
page.resize(900, 700)
page.show()
page._add_paths([stored_path])
pump(200)

assert page._enc_trash_library_check.isChecked()
assert page._enc_remove_source_check.isChecked()

page._enc_password.setText("gizli-123")
page._enc_confirm.setText("gizli-123")
page._enc_name.setText("plain_sifreli")
pump(100)

assert page._enc_button.isEnabled()
page._enc_button.click()

wait_idle(page)

# Kütüphanedeki orijinal kopya artık çöpte.
refreshed = backend_gateway.fetch_library_documents()
assert all(doc.id != imported.id for doc in refreshed)

trashed = backend_gateway.fetch_trashed()
assert any(doc.id == imported.id for doc in trashed)

# Kaynak dosya (kütüphane kopyasıyla aynı fiziksel dosyaydı) artık yerinde değil.
assert not Path(stored_path).exists()

# Yeni şifreli dosya kütüphanede.
assert any(doc.id != imported.id for doc in refreshed)

print("SCENARIO OK")
"""

# Senaryo 2: yalnızca "kaynağı kaldır" işaretli, kütüphane kopyasını taşıma
# işaretsiz -> kütüphane kaydı DOKUNULMAZ, yalnız kaynak dosya (onaylanınca)
# diskten kaldırılır.
SCENARIO_REMOVE_SOURCE_ONLY = r"""
source = make_pdf("only-source.pdf")

outcomes = backend_gateway.import_documents([source])
assert outcomes[0].status == "imported"

library_docs = backend_gateway.fetch_library_documents()
imported = library_docs[0]
stored_path = imported.stored_path

AppDialog.ask = staticmethod(lambda *a, **k: True)
AppDialog.inform = staticmethod(lambda *a, **k: None)

page = SecurityPage()
page.resize(900, 700)
page.show()
page._add_paths([stored_path])
pump(200)

page._enc_trash_library_check.setChecked(False)
page._enc_remove_source_check.setChecked(True)

page._enc_password.setText("gizli-123")
page._enc_confirm.setText("gizli-123")
page._enc_name.setText("only_source_sifreli")
pump(100)

page._enc_button.click()
wait_idle(page)

refreshed = backend_gateway.fetch_library_documents()
# Kütüphane kaydı taşınmadı/silinmedi (DB'de hâlâ "active"), ama fiziksel
# dosyası kaldırıldığından artık kütüphane listesinde GÖRÜNMEZ -- silinmiş/
# taşınmış dosyaların seçilebilir gibi görünmesi düzeltildi (LibraryService
# artık stored_path'in diskte var olup olmadığını kontrol ediyor).
assert all(doc.id != imported.id for doc in refreshed)

trashed = backend_gateway.fetch_trashed()
assert all(doc.id != imported.id for doc in trashed)

assert not Path(stored_path).exists()

from pdf_reme.infrastructure.database.models.document import (
    Document as DocumentModel,
)
from sqlalchemy.orm import Session

with Session(engine) as db_session:
    row = db_session.get(DocumentModel, imported.id)
    assert row is not None
    assert row.status == "active"

print("SCENARIO OK")
"""

# Senaryo 3: her iki kutu da işaretsiz -> hiçbir temizlik yapılmaz.
SCENARIO_NO_CLEANUP = r"""
source = make_pdf("keep-both.pdf")

outcomes = backend_gateway.import_documents([source])
assert outcomes[0].status == "imported"

library_docs = backend_gateway.fetch_library_documents()
imported = library_docs[0]
stored_path = imported.stored_path

AppDialog.ask = staticmethod(lambda *a, **k: (_ for _ in ()).throw(
    AssertionError("Onay diyaloğu hiç açılmamalıydı.")
))
AppDialog.inform = staticmethod(lambda *a, **k: None)

page = SecurityPage()
page.resize(900, 700)
page.show()
page._add_paths([stored_path])
pump(200)

page._enc_trash_library_check.setChecked(False)
page._enc_remove_source_check.setChecked(False)

page._enc_password.setText("gizli-123")
page._enc_confirm.setText("gizli-123")
page._enc_name.setText("keep_both_sifreli")
pump(100)

page._enc_button.click()
wait_idle(page)

refreshed = backend_gateway.fetch_library_documents()
assert any(doc.id == imported.id for doc in refreshed)

trashed = backend_gateway.fetch_trashed()
assert all(doc.id != imported.id for doc in trashed)

assert Path(stored_path).exists()

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
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "SCENARIO OK" in result.stdout


def test_encrypt_cleanup_trashes_library_copy_and_removes_source_by_default(
    tmp_path,
):
    _run(SCENARIO_BOTH_DEFAULT, tmp_path)


def test_encrypt_cleanup_remove_source_only_leaves_library_copy(tmp_path):
    _run(SCENARIO_REMOVE_SOURCE_ONLY, tmp_path)


def test_encrypt_cleanup_does_nothing_when_both_unchecked(tmp_path):
    _run(SCENARIO_NO_CLEANUP, tmp_path)
