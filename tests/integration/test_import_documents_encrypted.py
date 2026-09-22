"""Şifreli PDF içe aktarma (Item 6): `backend_gateway.import_documents`
seviyesinde parolasız/doğru parolalı/yanlış parolalı senaryolar.

Gateway içe aktarılırken gerçek uygulama veri klasörünü ve veritabanını
oluşturduğundan senaryo, veri klasörü geçici dizine yönlendirilmiş ayrı bir
süreçte çalıştırılır -- `test_backend_gateway_operations.py` ile aynı desen.
"""

import os
import subprocess
import sys
from pathlib import Path

SCENARIO = r"""
import os
import sys
from pathlib import Path

import pdf_reme.shared.paths.app_paths as app_paths

data = Path(os.environ["PDFREME_TEST_DATA"])
app_paths.get_app_data_dir = lambda: data

from pypdf import PdfWriter

from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.connection import engine
import pdf_reme.infrastructure.database.models.document  # noqa: F401

assert "pdfreme_test" in str(engine.url)
Base.metadata.create_all(bind=engine)

from pdf_reme.presentation import backend_gateway as gw

files = data / "files"
files.mkdir(parents=True)


def make_encrypted_pdf(name, password="gizli-123"):
    path = files / name
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=280)
    writer.encrypt(user_password=password, owner_password=password)
    with path.open("wb") as handle:
        writer.write(handle)
    return str(path)


# 1) Parolasız: içe aktarma başarısız, ayrı "encrypted" nedeniyle.
locked1 = make_encrypted_pdf("locked1.pdf")
outcomes = gw.import_documents([locked1])
assert outcomes[0].status == "failed"
assert outcomes[0].reason == "encrypted"
assert gw.fetch_library_documents() == []

# 2) Doğru parola: normal şekilde içe aktarılır, orijinal şifreli bayt-bayt
#    kopyalanır (parola hiçbir yere yazılmaz, yalnızca bu çağrı için verilir).
locked2 = make_encrypted_pdf("locked2.pdf", password="dogru-parola")
outcomes = gw.import_documents(
    [locked2], passwords={locked2: "dogru-parola"}
)
assert outcomes[0].status == "imported"

library_docs = gw.fetch_library_documents()
assert len(library_docs) == 1
assert Path(library_docs[0].stored_path).read_bytes() == Path(locked2).read_bytes()

# 3) Yanlış parola: içe aktarma yine başarısız olur.
locked3 = make_encrypted_pdf("locked3.pdf", password="dogru-parola")
outcomes = gw.import_documents(
    [locked3], passwords={locked3: "yanlis-parola"}
)
assert outcomes[0].status == "failed"
assert len(gw.fetch_library_documents()) == 1  # yalnızca 2. adımdaki eklendi

print("SCENARIO OK")
"""


def test_import_documents_handles_encrypted_pdfs(tmp_path):
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
        [sys.executable, "-c", SCENARIO],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "SCENARIO OK" in result.stdout
