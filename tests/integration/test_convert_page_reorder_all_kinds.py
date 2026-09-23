"""Madde 14: Dönüştür sayfasındaki sürükle-bırak + ok-tuşu yeniden sıralama
artık yalnız "Görsel → PDF" türünde değil, TÜM dönüştürme türlerinde
(PDF → Görsel, Office → PDF) açık.

`test_ui_fix_pack_1.py`'deki `CONVERT` senaryosuyla aynı desen (subprocess,
offscreen Qt, sentetik PDF'ler) kullanılır; burada özellikle önceden
`images_to_pdf`'e kilitli olan `_rebuild_file_rows`/`_reorder_file` kapısının
kaldırıldığı doğrulanır.
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

from PySide6.QtCore import QCoreApplication, QMimeData, QPoint, QPointF, Qt
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

app = QApplication(sys.argv)

from pypdf import PdfWriter

from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.connection import engine
import pdf_reme.infrastructure.database.models.document  # noqa: F401

assert "pdfreme_test" in str(engine.url)
Base.metadata.create_all(bind=engine)

from pdf_reme.presentation import backend_gateway
from pdf_reme.presentation.widgets.app_dialog import AppDialog
from pdf_reme.presentation.widgets.reorderable_list import ROW_MIME
from pdf_reme.presentation.pages.convert_page import ConvertPage

files = data / "files"
files.mkdir(parents=True)

AppDialog.choose = staticmethod(lambda *a, **k: None)
AppDialog.inform = staticmethod(lambda *a, **k: None)


def pump(ms=200):
    end = time.time() + ms / 1000
    while time.time() < end:
        QCoreApplication.processEvents()
        time.sleep(0.005)


def make_pdf(name, pages=1):
    path = files / name
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=280)
    with path.open("wb") as handle:
        writer.write(handle)
    return str(path)


def make_office_stub(name):
    # Yalnız UI seviyesinde uzantıya bakılıyor (gerçek dönüştürme
    # tetiklenmiyor); içerik önemsiz.
    path = files / name
    path.write_bytes(b"stub office content")
    return str(path)


def row_text(page):
    names = []
    for row in page._file_list.rows:
        labels = {
            label.objectName(): label.text()
            for label in row.findChildren(QLabel)
        }
        names.append(labels["opFileName"])
    return names


def press_button(row, index):
    buttons = row.findChildren(QPushButton)
    buttons[index].click()
    pump(100)


def drop_on(page, source, slot):
    lst = page._file_list
    rows = lst.rows
    if slot >= len(rows):
        y = rows[-1].geometry().bottom() + 2
    else:
        y = rows[slot].geometry().top() + 1
    assert lst.slot_at(y) == slot, (slot, y, lst.slot_at(y))
    mime = QMimeData()
    mime.setData(ROW_MIME, str(source).encode("ascii"))
    args = (
        Qt.DropAction.MoveAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(lst, QDragEnterEvent(QPoint(20, y), *args))
    QApplication.sendEvent(lst, QDragMoveEvent(QPoint(20, y), *args))
    assert lst._drop_slot == slot, (lst._drop_slot, slot)
    event = QDropEvent(QPointF(20, y), *args)
    QApplication.sendEvent(lst, event)
    assert lst._drop_slot is None
    pump(150)
"""

# Senaryo 1: PDF → Görsel türünde birden fazla PDF eklenince sıralama
# (ok butonları + sürükle-bırak) artık etkin, önceden kind-gate nedeniyle
# kapalıydı.
SCENARIO_PDF_TO_IMAGES = r"""
paths = {k: make_pdf(f"{k}.pdf", pages=1) for k in "ABC"}

page = ConvertPage()
page.resize(1100, 760)
page.show()
pump(200)

page._add_paths([paths[k] for k in "ABC"])
pump(300)

assert page._kind() == "pdf_to_images", page._kind()
names = lambda: [Path(p).stem for p in page._paths]
assert names() == list("ABC"), names()

# Madde 14 öncesi: reorderable False olurdu (yalnız images_to_pdf).
assert page._file_list.reorderable

# Ok butonları çalışıyor.
press_button(page._file_list.rows[2], 0)  # C yukarı: A,C,B
assert names() == list("ACB"), names()

# Sürükle-bırak da çalışıyor.
drop_on(page, 0, 3)  # A sona: C,B,A
assert names() == list("CBA"), names()
assert row_text(page) == ["C.pdf", "B.pdf", "A.pdf"], row_text(page)

print("SCENARIO OK")
"""

# Senaryo 2: Office → PDF türünde de aynı şekilde sıralama etkin.
SCENARIO_OFFICE_TO_PDF = r"""
paths = {k: make_office_stub(f"{k}.docx") for k in "ABC"}

page = ConvertPage()
page.resize(1100, 760)
page.show()
pump(200)

page._add_paths([paths[k] for k in "ABC"])
pump(300)

assert page._kind() == "office_to_pdf", page._kind()
names = lambda: [Path(p).stem for p in page._paths]
assert names() == list("ABC"), names()

# Madde 14 öncesi: reorderable False olurdu (yalnız images_to_pdf).
assert page._file_list.reorderable

press_button(page._file_list.rows[0], 1)  # A aşağı: B,A,C
assert names() == list("BAC"), names()

drop_on(page, 2, 0)  # C başa: C,B,A
assert names() == list("CBA"), names()
assert row_text(page) == ["C.docx", "B.docx", "A.docx"], row_text(page)

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


def test_pdf_to_images_reorder_enabled(tmp_path):
    _run(SCENARIO_PDF_TO_IMAGES, tmp_path)


def test_office_to_pdf_reorder_enabled(tmp_path):
    _run(SCENARIO_OFFICE_TO_PDF, tmp_path)
