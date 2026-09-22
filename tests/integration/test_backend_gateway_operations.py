"""Sunum katmanı gateway'inin dönüştürme/düzenleme akışları.

Gateway içe aktarılırken gerçek uygulama veri klasörünü ve veritabanını
oluşturduğundan senaryo, veri klasörü geçici dizine yönlendirilmiş ayrı bir
süreçte çalıştırılır.
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

from PIL import Image
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


def make_image(name):
    path = files / name
    Image.new("RGB", (40, 40), "red").save(path)
    return str(path)


def reason_of(action):
    try:
        action()
    except gw.OperationError as error:
        return error.reason
    raise AssertionError("OperationError bekleniyordu")


# --- tür algılama ---
assert gw.detect_convert_kind([]) == "empty"
assert gw.detect_convert_kind(["a.JPG", "b.png"]) == "images_to_pdf"
assert gw.detect_convert_kind(["a.pdf"]) == "pdf_to_images"
assert gw.detect_convert_kind(["a.docx", "b.XLSX"]) == "office_to_pdf"
assert gw.detect_convert_kind(["a.pdf", "b.jpg"]) == "mixed"
assert gw.detect_convert_kind(["a.txt"]) == "unsupported"
assert reason_of(
    lambda: gw.convert_files(gw.ConvertRequest(["a.pdf", "b.jpg"]))
) == "mixed"

# --- hata neden kodları ---
mapping = [
    (FileNotFoundError("LibreOffice bulunamadı"), "libreoffice_missing"),
    (FileNotFoundError("yok"), "not_found"),
    (TimeoutError("uzun"), "timeout"),
    (ValueError("PDF şifreli"), "encrypted"),
    (ValueError("Geçersiz dosya adı"), "invalid_name"),
    (ValueError("Tüm sayfalar silinemez"), "all_pages_deleted"),
    (ValueError("başka"), "invalid_input"),
    (RuntimeError("bozuk"), "conversion_failed"),
    (KeyError("x"), "unknown"),
]
for error, reason in mapping:
    assert gw._operation_error_from(error).reason == reason, (error, reason)

# --- sayfa sayısı / aralık ---
source = make_pdf("kaynak.pdf", 5)
assert gw.read_pdf_page_count(source) == 5
assert reason_of(lambda: gw.read_pdf_page_count(str(files / "yok.pdf"))) == "not_found"

bad = files / "bozuk.pdf"
bad.write_bytes(b"not a pdf")
assert reason_of(lambda: gw.read_pdf_page_count(str(bad))) == "corrupt_pdf"
assert gw.parse_page_selection("1-2, 5", 5) == [1, 2, 5]
assert reason_of(lambda: gw.parse_page_selection("99", 5)) == "invalid_range"

# --- görsel -> PDF ---
images = [make_image("a.jpg"), make_image("b.png")]
documents = gw.convert_files(gw.ConvertRequest(images, output_name="gorseller"))
assert len(documents) == 1 and documents[0].page_count == 2
assert str(data) in documents[0].stored_path

# --- Office -> PDF (LibreOffice yerine sahte servis) ---
class FakeOffice:
    def __init__(self, runtime_path=None):
        self.runtime_path = runtime_path

    def convert(self, input_path, output_path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        with output_path.open("wb") as handle:
            writer.write(handle)
        return output_path

gw.OfficeToPdfService = FakeOffice
word = files / "rapor.docx"
word.write_bytes(b"sahte")
documents = gw.convert_files(gw.ConvertRequest([str(word)]))
assert len(documents) == 1 and documents[0].display_name == "rapor.pdf"

# --- görsel -> PDF: A4 (varsayılan) ve "görsele göre" ---
wide = files / "genis.png"
Image.new("RGBA", (400, 100), (255, 0, 0, 0)).save(wide)  # şeffaf -> beyaz


def first_page_image(document):
    page = PdfReader(document.stored_path).pages[0]
    return page, page.images[0].image.convert("RGB")


a4_docs = gw.convert_files(
    gw.ConvertRequest([images[0], str(wide)], output_name="a4_modu")
)
reader = PdfReader(a4_docs[0].stored_path)
assert len(reader.pages) == 2
for page in reader.pages:
    width, height = float(page.mediabox.width), float(page.mediabox.height)
    ratio = max(width, height) / min(width, height)
    assert abs(ratio - 1.4142) < 0.01, ratio

_, portrait = first_page_image(a4_docs[0])
assert portrait.size[0] < portrait.size[1]
for corner in ((0, 0), (portrait.size[0] - 1, 0), (0, portrait.size[1] - 1)):
    assert portrait.getpixel(corner) == (255, 255, 255), corner
assert portrait.getpixel((portrait.size[0] // 2, portrait.size[1] // 2)) != (255, 255, 255)

# şeffaf görsel beyaz zeminde: hiçbir piksel siyah olmamalı
transparent_page = reader.pages[1].images[0].image.convert("RGB")
assert transparent_page.getpixel((transparent_page.size[0] // 2, transparent_page.size[1] // 2)) == (255, 255, 255)

original_docs = gw.convert_files(
    gw.ConvertRequest([images[0]], output_name="orijinal", page_mode="original")
)
page = PdfReader(original_docs[0].stored_path).pages[0]
assert abs(float(page.mediabox.width) - float(page.mediabox.height)) < 1

# --- ilerleme: monoton artar ve 100'de biter ---
reports = []
gw.convert_files(
    gw.ConvertRequest(images, output_name="ilerleme"),
    lambda percent, text: reports.append(percent),
)
assert reports and reports[-1] == 100
assert reports == sorted(reports), reports
assert all(0 <= value <= 100 for value in reports)

# --- Office: birden fazla dosya tek PDF'te birleşir / ayrı kalır ---
word2 = files / "ozet.docx"
word2.write_bytes(b"sahte")

separate = gw.convert_files(gw.ConvertRequest([str(word), str(word2)]))
assert len(separate) == 2

office_reports = []
combined = gw.convert_files(
    gw.ConvertRequest([str(word), str(word2)], output_name="birlesik", combine=True),
    lambda percent, text: office_reports.append(percent),
)
assert len(combined) == 1 and combined[0].page_count == 2
assert combined[0].display_name == "birlesik.pdf"
assert str(data) in combined[0].stored_path
assert office_reports[-1] == 100 and office_reports == sorted(office_reports)

# --- klasörde göster: gerçek Explorer açılmaz ---
launched = []


class FakePopen:
    def __init__(self, command, *args, **kwargs):
        launched.append(command)


gw.subprocess.Popen = FakePopen
gw.reveal_in_folder(combined[0].stored_path)
if sys.platform == "win32":
    assert len(launched) == 1 and "explorer /select" in launched[0]
    assert combined[0].stored_path in launched[0]
assert reason_of(lambda: gw.reveal_in_folder(str(files / "yok" / "x.pdf"))) == "not_found"

# --- düzenleme zinciri: tek çıktı, kaynak değişmez, ara dosyalar silinir ---
before = len(gw.fetch_library_documents())
source_size = Path(source).stat().st_size

workspace = gw.new_edit_workspace()
step1 = str(workspace / "1.pdf")
step2 = str(workspace / "2.pdf")

gw.apply_edit_step(
    source, gw.EditOperation("rotate_pages", {"page_numbers": [1], "degrees": 90}), step1
)
gw.apply_edit_step(
    step1, gw.EditOperation("delete_pages", {"page_numbers": [5]}), step2
)
assert PdfReader(step2).pages[0].get("/Rotate") == 90
assert len(PdfReader(step2).pages) == 4
assert len(gw.fetch_library_documents()) == before, "ara adımlar kütüphaneye girmemeli"

saved = gw.save_edit_result(
    step2,
    gw.EditOperation("duplicate_pages", {"page_numbers": [1]}),
    "sonuc",
)
assert saved.page_count == 5 and saved.display_name == "sonuc.pdf"
assert len(gw.fetch_library_documents()) == before + 1
assert Path(source).stat().st_size == source_size

gw.discard_edit_workspace(workspace)
assert not workspace.exists()

# --- düzenleme hataları ---
assert reason_of(
    lambda: gw.save_edit_result(
        source, gw.EditOperation("delete_pages", {"page_numbers": [1, 2, 3, 4, 5]}), "x"
    )
) == "all_pages_deleted"
assert reason_of(
    lambda: gw.save_edit_result(
        source, gw.EditOperation("duplicate_pages", {"page_numbers": [1]}), ""
    )
) == "invalid_name"
assert reason_of(
    lambda: gw.save_edit_result(source, gw.EditOperation("bilinmeyen"), "x")
) == "unknown"

print("SCENARIO OK")
"""


def test_gateway_convert_and_edit_flows(tmp_path):
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
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "SCENARIO OK" in result.stdout
