"""Madde 13: "Kütüphaneden Ekle" penceresinde Shift/Ctrl olmadan çoklu seçim.

`PdfPickerDialog` çoklu modda artık `QListWidget.MultiSelection` kullanıyor
(eskiden `ExtendedSelection` -- Ctrl/Shift zorunluydu) ve her satırın solunda
seçim durumunu yansıtan bir `SelectionCheck` gösteriyor.

`test_ui_fix_pack_1.py` ile aynı desen (subprocess, offscreen Qt, sentetik
PDF'ler, izole veri klasörü/veritabanı).
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

from PySide6.QtCore import QCoreApplication, QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from pypdf import PdfWriter

from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.connection import engine
import pdf_reme.infrastructure.database.models.document  # noqa: F401

assert "pdfreme_test" in str(engine.url)
Base.metadata.create_all(bind=engine)

from pdf_reme.presentation import backend_gateway
from pdf_reme.presentation.widgets.pdf_picker_dialog import PdfPickerDialog

files = data / "files"
files.mkdir(parents=True)


def pump(ms=150):
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


def click_item(list_widget, row_index):
    # Modifier'siz sol tik: gercek fare olayi, MultiSelection toggle'lar.
    item = list_widget.item(row_index)
    pos = list_widget.visualItemRect(item).center()
    viewport = list_widget.viewport()
    global_pos = viewport.mapToGlobal(pos)

    press = QMouseEvent(
        QEvent.Type.MouseButtonPress, QPointF(pos), QPointF(global_pos),
        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    release = QMouseEvent(
        QEvent.Type.MouseButtonRelease, QPointF(pos), QPointF(global_pos),
        Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(viewport, press)
    QApplication.sendEvent(viewport, release)
    pump(50)
"""

SCENARIO = r"""
paths = [make_pdf(f"{k}.pdf", pages) for k, pages in zip("ABC", (1, 2, 3))]
outcomes = backend_gateway.import_documents(paths)
assert all(o.status == "imported" for o in outcomes), outcomes

documents = backend_gateway.fetch_library_documents()
assert len(documents) == 3

dialog = PdfPickerDialog(
    None,
    documents=documents,
    title="Başlık",
    body="Gövde",
    types=("pdf",),
    multi=True,
)
dialog.show()
pump(150)

assert not dialog._confirm_button.isEnabled()

# Shift/Ctrl olmadan iki ayrı satıra tıklamak ikisini de seçili bırakır.
click_item(dialog._list, 0)
click_item(dialog._list, 1)

assert len(dialog._list.selectedItems()) == 2, len(dialog._list.selectedItems())
assert dialog._confirm_button.isEnabled()
assert "2" in dialog._confirm_button.text(), dialog._confirm_button.text()

selected_paths = {
    dialog._list.item(i).data(Qt.ItemDataRole.UserRole)
    for i in range(dialog._list.count())
    if dialog._list.item(i).isSelected()
}
assert len(selected_paths) == 2

# Checkbox görünümü seçim durumunu yansıtıyor.
for document in documents:
    check = dialog._row_checks[document.stored_path]
    assert check.isChecked() == (document.stored_path in selected_paths), (
        document.stored_path
    )

# Aynı satıra tekrar tıklamak seçimi kaldırır (toggle).
click_item(dialog._list, 0)
assert len(dialog._list.selectedItems()) == 1

dialog._on_confirm_clicked()
assert len(dialog._selected_paths) == 1, dialog._selected_paths

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


def test_picker_dialog_multiselect_without_modifiers(tmp_path):
    _run(SCENARIO, tmp_path)
