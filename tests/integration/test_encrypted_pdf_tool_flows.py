"""Madde 12: şifreli PDF'lerde parola desteği -- Birleştir, Düzenle, Görüntüleyici.

`EncryptedPdfPasswordDialog.prompt` gerçek bir modal `exec()` çalıştırır;
offscreen ortamında hiçbir etkileşim onu kapatmayacağından, kullanıcının
diyalogda yapacağı seçim burada bir sahte (`staticmethod`) ile simüle edilir
(`test_library_page_encrypted_import.py` ile aynı desen). Diyaloğun kendi
parola-doğrulama/yeniden-deneme mantığı ayrıca `test_encrypted_pdf_password_
dialog.py`'de doğrudan test edildiğinden, burada yalnız `resolve()`'a doğru
parola ya da iptal (None) döndüğü varsayılır -- dialog zaten yalnız
doğrulanmış bir parolayla kapanır.
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

from pypdf import PdfReader, PdfWriter

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

files = data / "files"
files.mkdir(parents=True)

AppDialog.ask = staticmethod(lambda *a, **k: True)
AppDialog.inform = staticmethod(lambda *a, **k: None)
AppDialog.choose = staticmethod(lambda *a, **k: None)


def pump(ms=200):
    end = time.time() + ms / 1000
    while time.time() < end:
        QCoreApplication.processEvents()
        time.sleep(0.005)


def wait_idle(runner, timeout=60):
    end = time.time() + timeout
    while runner.is_running and time.time() < end:
        QCoreApplication.processEvents()
        time.sleep(0.01)
    pump(150)
    assert not runner.is_running, "islem zaman asimina ugradi"


def make_pdf(name, pages=1, width=200, height=280):
    path = files / name
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=width, height=height)
    with path.open("wb") as handle:
        writer.write(handle)
    return str(path)


def make_encrypted_pdf(name, pages=1, password="gizli-123", width=200, height=280):
    path = files / name
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=width, height=height)
    writer.encrypt(user_password=password, owner_password=password)
    with path.open("wb") as handle:
        writer.write(handle)
    return str(path)
"""

# Senaryo 1: Birlestir'e duz + sifreli dosya eklenir, dogru parola girilir ->
# sifreli dosya duz gecici bir kopyaya cozumlenir ve birlestirme basariyla
# tamamlanir (sonuc PDF'inde toplam sayfa sayisi dogru).
MERGE_CORRECT_PASSWORD = r"""
from pdf_reme.presentation.pages.merge_page import MergePage

plain = make_pdf("plain.pdf", pages=2)
locked = make_encrypted_pdf("locked.pdf", pages=3, password="dogru-parola")

EncryptedPdfPasswordDialog.prompt = staticmethod(
    lambda parent, *, path, file_name: "dogru-parola"
)

page = MergePage()
page.resize(1000, 700)
page.show()
pump(200)

page._add_paths([plain, locked])
pump(300)

assert len(page._paths) == 2, page._paths
# Sifreli dosyanin cozumlenmis yolu artik orijinal (hala sifreli) yol degil.
resolved_locked = page._paths[1]
assert resolved_locked != locked, resolved_locked
assert Path(resolved_locked).exists()
assert not PdfReader(resolved_locked).is_encrypted

page._name_input.setText("birlesik")
page._on_merge()
wait_idle(page._runner)

documents = backend_gateway.fetch_library_documents()
assert len(documents) == 1, documents
merged = PdfReader(documents[0].stored_path)
assert len(merged.pages) == 5, len(merged.pages)

# clear_files() (basari sonrasi otomatik) cozumleyicinin ürettigi geçici
# kopyayi da temizler.
assert not Path(resolved_locked).exists()

print("SCENARIO OK")
"""

# Senaryo 2: Birlestir'e sifreli dosya eklenir ama kullanici parola
# diyalogunu iptal eder -> dosya sessizce atlanir (reddedilenler listesine
# girmez), listeye eklenmez.
MERGE_CANCEL_SKIPS = r"""
from pdf_reme.presentation.pages.merge_page import MergePage

plain = make_pdf("plain2.pdf", pages=1)
locked = make_encrypted_pdf("locked2.pdf", pages=1, password="dogru-parola")

EncryptedPdfPasswordDialog.prompt = staticmethod(
    lambda parent, *, path, file_name: None
)

rejected_calls = []
AppDialog.inform = staticmethod(
    lambda *a, **k: rejected_calls.append(k.get("items"))
)

page = MergePage()
page.resize(1000, 700)
page.show()
pump(200)

page._add_paths([plain, locked])
pump(300)

assert page._paths == [plain], page._paths
# Iptal sessiz atlamadir -- reddedilenler diyalogu HIC gosterilmemis olmali.
assert rejected_calls == [], rejected_calls

print("SCENARIO OK")
"""

# Senaryo 3: Duzenle'de sifreli bir kaynak dogru parolayla acilir; sayfa
# sayisi dogru okunur. Ardindan _on_new() cagrilinca cozumleyicinin urettigi
# gecici duz kopya diskten silinir (temp sizintisi yok).
EDIT_OPEN_ENCRYPTED_SUCCESS = r"""
from pdf_reme.presentation.pages.edit_page import EditPage

locked = make_encrypted_pdf("edit_locked.pdf", pages=6, password="acsifre")

EncryptedPdfPasswordDialog.prompt = staticmethod(
    lambda parent, *, path, file_name: "acsifre"
)

page = EditPage()
page.resize(1300, 800)
page.show()
pump(200)

page._open_source(locked)
pump(500)

assert page._stack.currentIndex() == 1
assert page._page_count == 6, page._page_count
assert page._source_path != locked
resolved_source = page._source_path
assert Path(resolved_source).exists()

page._on_new()
pump(200)

assert page._stack.currentIndex() == 0
assert not Path(resolved_source).exists()

page.shutdown()
print("SCENARIO OK")
"""

# Senaryo 4: Duzenle'de sifreli kaynak secilir ama parola iptal edilir ->
# tum islem iptal edilir, editor bos durumda kalir (once acilmis bir belge
# yoksa hicbir sey degismez, cokme olmaz).
EDIT_OPEN_ENCRYPTED_CANCEL = r"""
from pdf_reme.presentation.pages.edit_page import EditPage

locked = make_encrypted_pdf("edit_cancel.pdf", pages=2, password="acsifre")

EncryptedPdfPasswordDialog.prompt = staticmethod(
    lambda parent, *, path, file_name: None
)

page = EditPage()
page.resize(1300, 800)
page.show()
pump(200)

page._open_source(locked)
pump(200)

assert page._stack.currentIndex() == 0
assert page._source_path is None
assert page._states == []

page.shutdown()
print("SCENARIO OK")
"""

# Senaryo 5: Donustur'e sifreli bir PDF dogru parolayla eklenir -> duz
# gecici kopyaya cozumlenir, PDF -> Gorsel donusumu sayfa basina bir gorsel
# ureterek basariyla tamamlanir.
CONVERT_ENCRYPTED_PDF_TO_IMAGES = r"""
from pdf_reme.presentation.pages.convert_page import ConvertPage

locked = make_encrypted_pdf("convert_locked.pdf", pages=3, password="donustur")

EncryptedPdfPasswordDialog.prompt = staticmethod(
    lambda parent, *, path, file_name: "donustur"
)

page = ConvertPage()
page.resize(1100, 760)
page.show()
pump(200)

page._add_paths([locked])
pump(300)

assert len(page._paths) == 1, page._paths
resolved = page._paths[0]
assert resolved != locked, resolved
assert not PdfReader(resolved).is_encrypted
assert page._kind() == "pdf_to_images", page._kind()

payloads = []
real_convert = backend_gateway.convert_files


def spy(request, report=None):
    payloads.append(list(request.paths))
    return real_convert(request, report)


backend_gateway.convert_files = spy

page._on_convert_clicked()
wait_idle(page._runner)

assert len(payloads) == 1, payloads
# Backend'e giden yol sifreli orijinal degil, cozumlenmis duz kopyadir.
assert payloads[0] == [resolved], payloads

documents = backend_gateway.fetch_library_documents()
assert len(documents) == 3, documents
# Basari sonrasi cozumleyicinin gecici kopyasi da temizlenir.
assert not Path(resolved).exists()

print("SCENARIO OK")
"""

# Senaryo 6: Donustur'e sifreli PDF eklenirken parola iptal edilir -> dosya
# sessizce atlanir, listeye eklenmez, reddedilenler diyalogu gosterilmez.
CONVERT_ENCRYPTED_CANCEL_SKIPS = r"""
from pdf_reme.presentation.pages.convert_page import ConvertPage

locked = make_encrypted_pdf("convert_cancel.pdf", pages=1, password="donustur")

EncryptedPdfPasswordDialog.prompt = staticmethod(
    lambda parent, *, path, file_name: None
)

rejected_calls = []
AppDialog.inform = staticmethod(
    lambda *a, **k: rejected_calls.append(k.get("items"))
)

page = ConvertPage()
page.resize(1100, 760)
page.show()
pump(200)

page._add_paths([locked])
pump(300)

assert page._paths == [], page._paths
assert rejected_calls == [], rejected_calls

print("SCENARIO OK")
"""

# Senaryo 7: Goruntuleyici sifreli bir belgeyi dogru parolayla yukler.
VIEWER_LOAD_ENCRYPTED_SUCCESS = r"""
from PySide6.QtPdf import QPdfDocument
from pdf_reme.presentation.pages.viewer_page import ViewerPage

locked = make_encrypted_pdf("view_locked.pdf", pages=4, password="goruntule")

EncryptedPdfPasswordDialog.prompt = staticmethod(
    lambda parent, *, path, file_name: "goruntule"
)

page = ViewerPage()
page.resize(1000, 700)
page.show()
pump(200)

page.load_document(locked, "view_locked.pdf")
pump(500)

assert page._stack.currentIndex() == 1
assert page._document.status() == QPdfDocument.Status.Ready, page._document.status()
assert page._document.pageCount() == 4, page._document.pageCount()

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


def test_merge_encrypted_file_with_correct_password(tmp_path):
    _run(MERGE_CORRECT_PASSWORD, tmp_path)


def test_merge_encrypted_file_cancel_skips_silently(tmp_path):
    _run(MERGE_CANCEL_SKIPS, tmp_path)


def test_edit_open_encrypted_source_success_and_cleanup(tmp_path):
    _run(EDIT_OPEN_ENCRYPTED_SUCCESS, tmp_path)


def test_edit_open_encrypted_source_cancel_leaves_state_unchanged(tmp_path):
    _run(EDIT_OPEN_ENCRYPTED_CANCEL, tmp_path)


def test_convert_encrypted_pdf_to_images_with_correct_password(tmp_path):
    _run(CONVERT_ENCRYPTED_PDF_TO_IMAGES, tmp_path)


def test_convert_encrypted_file_cancel_skips_silently(tmp_path):
    _run(CONVERT_ENCRYPTED_CANCEL_SKIPS, tmp_path)


def test_viewer_loads_encrypted_document_with_correct_password(tmp_path):
    _run(VIEWER_LOAD_ENCRYPTED_SUCCESS, tmp_path)
