"""Sunum katmanı gateway'inin Birleştir / Böl / Sıkıştır / Şifreleme akışları.

Gateway içe aktarılırken gerçek uygulama veri klasörünü ve veritabanını
oluşturduğundan senaryo, veri klasörü geçici dizine yönlendirilmiş ayrı bir
süreçte, yalnızca sentetik PDF'lerle çalıştırılır.
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

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from pypdf import PdfReader, PdfWriter

from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.connection import engine
import pdf_reme.infrastructure.database.models.document  # noqa: F401

assert str(data) in str(engine.url) or "pdfreme_test" in str(engine.url)
Base.metadata.create_all(bind=engine)

from pdf_reme.presentation import backend_gateway as gw

files = data / "files"
files.mkdir(parents=True)


def make_pdf(name, pages):
    path = files / name
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=100)
    with path.open("wb") as handle:
        writer.write(handle)
    return str(path)


def reason_of(action):
    try:
        action()
    except gw.OperationError as error:
        return error.reason
    raise AssertionError("OperationError bekleniyordu")


def count_of(document):
    return len(PdfReader(document.stored_path).pages)


def in_tmp(document):
    assert str(data) in document.stored_path, document.stored_path


a = make_pdf("a.pdf", 3)
b = make_pdf("b.pdf", 4)
c = make_pdf("c.pdf", 9)

bad = files / "bozuk.pdf"
bad.write_bytes(b"not a pdf")

# --- inspect_pdf ---
info = gw.inspect_pdf(a)
assert info.page_count == 3 and info.encrypted is False and info.size > 0
assert reason_of(lambda: gw.inspect_pdf(str(files / "yok.pdf"))) == "not_found"
assert reason_of(lambda: gw.inspect_pdf(str(bad))) == "corrupt_pdf"

# --- hata neden kodları ---
mapping = [
    (ValueError("PDF zaten şifreli."), "already_encrypted"),
    (ValueError("PDF şifreli değil."), "not_encrypted"),
    (ValueError("PDF parolası yanlış."), "wrong_password"),
    (ValueError("Şifreli PDF birleştirilemez"), "encrypted"),
]
for error, reason in mapping:
    assert gw._operation_error_from(error).reason == reason, (error, reason)

# --- birleştir ---
merged = gw.merge_pdfs([a, b, c], "birlesik")
in_tmp(merged)
assert count_of(merged) == 16 and merged.display_name == "birlesik.pdf"
assert reason_of(lambda: gw.merge_pdfs([a], "tek")) == "merge_needs_two"
assert reason_of(lambda: gw.merge_pdfs([a, b], "  ")) == "invalid_name"
assert reason_of(lambda: gw.merge_pdfs([a, str(bad)], "x")) in (
    "corrupt_pdf",
    "conversion_failed",
    "invalid_input",
)

# --- böl: sayfa seç (seçili + kalan = 2 PDF) ---
docs = gw.split_pdf(gw.SplitRequest(c, "pages", "secim", expression="1,3,5"))
assert [count_of(d) for d in docs] == [3, 6], [count_of(d) for d in docs]
assert [d.display_name for d in docs] == ["secim_secili.pdf", "secim_kalan.pdf"]
for document in docs:
    in_tmp(document)

# Kalan sayfalar seçilenlerin tümlemesidir (sıra korunur).
selected_pdf = PdfReader(docs[0].stored_path)
rest_pdf = PdfReader(docs[1].stored_path)
assert len(selected_pdf.pages) + len(rest_pdf.pages) == 9

# Tik kapalı: yalnız seçili sayfalar tek PDF olur.
docs = gw.split_pdf(
    gw.SplitRequest(c, "pages", "yalniz", expression="2-4, 7", keep_rest=False)
)
assert len(docs) == 1 and count_of(docs[0]) == 4 and docs[0].display_name == "yalniz.pdf"
in_tmp(docs[0])

# Tüm sayfalar seçiliyse kalan yoktur: tek PDF.
docs = gw.split_pdf(gw.SplitRequest(c, "pages", "hepsi", expression="1-9"))
assert len(docs) == 1 and count_of(docs[0]) == 9 and docs[0].display_name == "hepsi.pdf"

assert reason_of(
    lambda: gw.split_pdf(gw.SplitRequest(c, "pages", "x", expression="1-99"))
) == "invalid_range"

# İkinci çıktı üretilemezse ilk çıktı da geri alınır.
before = {d.display_name for d in gw.fetch_library_documents()}
original_extract = gw.SplitPdfUseCase.extract_selected_pages
calls = []


def flaky_extract(self, *args, **kwargs):
    calls.append(1)
    if len(calls) == 2:
        raise ValueError("ikinci cikti basarisiz")
    return original_extract(self, *args, **kwargs)


gw.SplitPdfUseCase.extract_selected_pages = flaky_extract
try:
    assert reason_of(
        lambda: gw.split_pdf(gw.SplitRequest(c, "pages", "yarim", expression="1,3"))
    ) is not None
finally:
    gw.SplitPdfUseCase.extract_selected_pages = original_extract
assert len(calls) == 2
after = {d.display_name for d in gw.fetch_library_documents()}
assert after == before, after ^ before

# --- böl: eşit parçalar (kalan ilk parçalara dağılır) ---
docs = gw.split_pdf(gw.SplitRequest(c, "parts", "parca", part_count=4))
assert [count_of(d) for d in docs] == [3, 2, 2, 2]
for document in docs:
    in_tmp(document)
for bad_count in (1, 10, 0):
    assert reason_of(
        lambda: gw.split_pdf(gw.SplitRequest(c, "parts", "x", part_count=bad_count))
    ) == "invalid_parts", bad_count

# Gruplar modu kaldırıldı.
assert reason_of(
    lambda: gw.split_pdf(gw.SplitRequest(c, "groups", "x", expression="1-3; 4-6"))
) == "invalid_input"
assert not hasattr(gw, "parse_page_groups")
assert reason_of(
    lambda: gw.split_pdf(gw.SplitRequest(c, "bilinmeyen", "x"))
) == "invalid_input"

# --- sıkıştır ---
for level in ("light", "balanced", "strong"):
    reports = []
    result = gw.compress_pdf(
        c, f"kucuk_{level}", level, lambda percent, text: reports.append(percent)
    )
    in_tmp(result.document)
    assert result.level == level
    assert result.saved_bytes >= 0
    assert result.original_size == Path(c).stat().st_size
    assert result.compressed_size <= result.original_size
    assert count_of(result.document) == 9
    assert reports and reports[-1] == 100 and reports == sorted(reports), reports
assert reason_of(lambda: gw.compress_pdf(c, "x", "ultra")) in (
    "invalid_input",
    "conversion_failed",
)

# --- depolama özeti ve geçici dosya temizliği ---
from pdf_reme.shared.paths.app_paths import AppPaths

summary = gw.storage_summary()
assert Path(summary.data_dir) == data
assert summary.library_files > 0 and summary.library_bytes > 0
assert summary.trash_count == 0

paths = AppPaths()
paths.temp_dir.mkdir(parents=True, exist_ok=True)
paths.cache_dir.mkdir(parents=True, exist_ok=True)
junk_file = paths.temp_dir / "pdfreme_junk.bin"
junk_file.write_bytes(b"x" * 4096)
junk_dir = paths.cache_dir / "pdfreme_junk_dir"
junk_dir.mkdir()
(junk_dir / "a.bin").write_bytes(b"y" * 1000)
assert gw.storage_summary().temp_bytes >= 5096

# Varsayılan yaş eşiği: yeni dosyalar korunur.
assert gw.clear_temp_files() == 0
assert junk_file.exists() and junk_dir.exists()

freed = gw.clear_temp_files(min_age_seconds=0)
assert freed >= 5096, freed
assert not junk_file.exists() and not junk_dir.exists()
assert Path(summary.data_dir).exists()

# Kütüphane dosyalarına dokunulmaz.
assert gw.storage_summary().library_files == summary.library_files

assert reason_of(lambda: gw.open_folder(str(data / "yok_klasor"))) == "not_found"

# --- şifrele -> incele -> kilidi aç ---
encrypted = gw.encrypt_pdf(a, "gizli", "parola123")
in_tmp(encrypted)
enc_info = gw.inspect_pdf(encrypted.stored_path)
assert enc_info.encrypted is True and enc_info.page_count is None

assert reason_of(lambda: gw.encrypt_pdf(encrypted.stored_path, "x", "p")) == "already_encrypted"
assert reason_of(lambda: gw.encrypt_pdf(a, "x", "   ")) == "invalid_password"
assert reason_of(lambda: gw.encrypt_pdf(a, "x", "")) == "invalid_password"
assert reason_of(lambda: gw.decrypt_pdf(a, "x", "p")) == "not_encrypted"
assert reason_of(
    lambda: gw.decrypt_pdf(encrypted.stored_path, "yanlis", "baska")
) == "wrong_password"

# Şifreliler birleştirilemez / bölünemez / sıkıştırılamaz
assert reason_of(lambda: gw.merge_pdfs([encrypted.stored_path, a], "m")) == "encrypted"
assert reason_of(
    lambda: gw.split_pdf(
        gw.SplitRequest(encrypted.stored_path, "parts", "x", part_count=2)
    )
) in ("encrypted", "corrupt_pdf")
assert reason_of(lambda: gw.compress_pdf(encrypted.stored_path, "x", "light")) == "encrypted"

# Sahip parolası ayrı verilebilir
owned = gw.encrypt_pdf(b, "sahipli", "kullanici1", "sahip1")
assert gw.inspect_pdf(owned.stored_path).encrypted is True

decrypted = gw.decrypt_pdf(encrypted.stored_path, "acik", "parola123")
in_tmp(decrypted)
dec_info = gw.inspect_pdf(decrypted.stored_path)
assert dec_info.encrypted is False and dec_info.page_count == 3

# Parola hata metnine sızmaz
try:
    gw.decrypt_pdf(encrypted.stored_path, "sizinti", "cok-gizli-parola")
except gw.OperationError as error:
    assert "cok-gizli-parola" not in str(error)
    assert "cok-gizli-parola" not in repr(error)

print("SCENARIO OK")
"""


def test_gateway_merge_split_compress_security_flows(tmp_path):
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
        timeout=300,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "SCENARIO OK" in result.stdout
