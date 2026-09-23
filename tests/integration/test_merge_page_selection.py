"""Madde 13: Birleştir sayfasının kendi dosya listesinde checkbox ile toplu
seçim ("Seçilenleri Kaldır").

Seçim path-keyed tutulur; sürükle-bırakla yeniden sıralama sonrası doğru
dosyaya yapışık kalmalı. `test_ui_fix_pack_1.py` ile aynı desen (subprocess,
offscreen Qt, sentetik PDF'ler, izole veri klasörü/veritabanı).
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
from pdf_reme.presentation.widgets.reorderable_list import ROW_MIME
from pdf_reme.presentation.widgets.selection_check import SelectionCheck
from pdf_reme.presentation.pages.merge_page import MergePage

files = data / "files"
files.mkdir(parents=True)

AppDialog.choose = staticmethod(lambda *a, **k: None)
AppDialog.inform = staticmethod(lambda *a, **k: None)


def pump(ms=150):
    end = time.time() + ms / 1000
    while time.time() < end:
        QCoreApplication.processEvents()
        time.sleep(0.005)


def make_pdf(name):
    path = files / name
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=280)
    with path.open("wb") as handle:
        writer.write(handle)
    return str(path)


def checkbox(row):
    return row.findChildren(SelectionCheck)[0]


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

SCENARIO = r"""
paths = {k: make_pdf(f"{k}.pdf") for k in "ABC"}

page = MergePage()
page.resize(1000, 700)
page.show()
pump(200)

page._add_paths([paths[k] for k in "ABC"])
pump(300)

names = lambda: [Path(p).stem for p in page._paths]
assert names() == list("ABC"), names()

assert not page._remove_selected_button.isEnabled()

# Shift/Ctrl olmadan checkbox ile seçim: A'yı seç.
checkbox(page._file_list.rows[0]).click()
pump(100)
assert page._selected_paths == {paths["A"]}, page._selected_paths
assert page._remove_selected_button.isEnabled()
assert page._file_list.rows[0].property("selected") is True

# Sürükle-bırakla yeniden sırala: A,B,C -> B,C,A. Seçim path'e yapışık kalmalı.
drop_on(page, 0, 3)
assert names() == list("BCA"), names()
assert page._selected_paths == {paths["A"]}, page._selected_paths
last_row = page._file_list.rows[-1]
assert checkbox(last_row).isChecked()
assert last_row.property("selected") is True
assert not checkbox(page._file_list.rows[0]).isChecked()

# İkinci dosyayı da seç (B, şimdi 0. sırada).
checkbox(page._file_list.rows[0]).click()
pump(100)
assert page._selected_paths == {paths["A"], paths["B"]}, page._selected_paths

# "Seçilenleri Kaldır": yalnızca seçili dosyalar gider, diğerinin sırası korunur.
page._on_remove_selected()
pump(150)
assert names() == list("C"), names()
assert page._selected_paths == set(), page._selected_paths
assert not page._remove_selected_button.isEnabled()

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


def test_merge_page_checkbox_selection_and_remove_selected(tmp_path):
    _run(SCENARIO, tmp_path)
