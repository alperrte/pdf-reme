"""UI Fix Pack 1: PDF Düzenle bağlam koruma, Dönüştür/Birleştir sürükle-bırak.

Sunum katmanı gateway'i içe aktarılırken gerçek uygulama veri klasörünü ve
veritabanını oluşturduğundan senaryolar, veri klasörü geçici dizine
yönlendirilmiş ayrı bir süreçte (offscreen Qt), yalnızca sentetik PDF/PNG'lerle
çalıştırılır.

Not: offscreen ortamında işletim sistemi düzeyinde `QDrag.exec` sürülemez.
Sürükleme başlatma gerçek fare olaylarıyla, bırakma ise özel MIME'lı gerçek bir
`QDropEvent` ile widget'a gönderilerek sınanır.
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

from PySide6.QtCore import (
    QCoreApplication, QEvent, QMimeData, QPoint, QPointF, Qt,
)
from PySide6.QtGui import (
    QColor, QDragEnterEvent, QDragMoveEvent, QDropEvent, QImage, QMouseEvent,
)
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

app = QApplication(sys.argv)

from pypdf import PdfReader, PdfWriter

from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.connection import engine
import pdf_reme.infrastructure.database.models.document  # noqa: F401

assert "pdfreme_test" in str(engine.url)
Base.metadata.create_all(bind=engine)

from pdf_reme.presentation import backend_gateway
from pdf_reme.presentation.widgets.app_dialog import AppDialog
from pdf_reme.presentation.widgets.reorderable_list import ROW_MIME

files = data / "files"
files.mkdir(parents=True)

# Modal sonuç/uyarı pencereleri testi bloklamasın.
AppDialog.choose = staticmethod(lambda *a, **k: None)
AppDialog.inform = staticmethod(lambda *a, **k: None)


def pump(ms=300):
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
    assert not runner.is_running, "işlem zaman aşımına uğradı"


def make_pdf(name, pages, width=200, height=280):
    path = files / name
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=width, height=height)
    with path.open("wb") as handle:
        writer.write(handle)
    return str(path)


def make_png(name, width, height=200):
    path = files / name
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor("#336699"))
    assert image.save(str(path))
    return str(path)


def row_text(page):
    # Satırların ekrandaki (UI) dosya adı sırası.
    names = []
    for row in page._file_list.rows:
        labels = {label.objectName(): label.text() for label in row.findChildren(QLabel)}
        names.append(labels["opFileName"])
    return names


def press_button(row, index):
    # Satırdaki düğmeler: [yukarı, aşağı, sil] (taşınabilirse) ya da [sil].
    buttons = row.findChildren(QPushButton)
    buttons[index].click()
    pump(100)


def drop_on(page, source, slot):
    # Liste bileşenine, ekleme aralığı `slot` olacak konumda gerçek bir bırakma
    # olayı gönderir (özel MIME'lı QDropEvent).
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
    # Gerçek sürüklemedeki olay sırası: enter → move → drop.
    QApplication.sendEvent(lst, QDragEnterEvent(QPoint(20, y), *args))
    QApplication.sendEvent(lst, QDragMoveEvent(QPoint(20, y), *args))
    assert lst._drop_slot == slot, (lst._drop_slot, slot)  # ekleme çizgisi
    event = QDropEvent(QPointF(20, y), *args)
    QApplication.sendEvent(lst, event)
    assert lst._drop_slot is None  # bırakınca çizgi temizlenir
    pump(150)
"""

CONVERT = r"""
from pdf_reme.presentation.pages.convert_page import ConvertPage

widths = {"A": 100, "B": 200, "C": 300, "D": 400}
paths = {k: make_png(f"{k}.png", w) for k, w in widths.items()}

page = ConvertPage()
page.resize(1100, 760)
page.show()
pump(200)

payloads = []
real_convert = backend_gateway.convert_files
results = []


def spy(request, report=None):
    payloads.append(list(request.paths))
    docs = real_convert(request, report)
    results.extend(docs)
    return docs


backend_gateway.convert_files = spy

page._add_paths([paths[k] for k in "ABCD"])
pump(300)

names = lambda: [Path(p).stem for p in page._paths]
assert names() == list("ABCD"), names()
assert row_text(page) == [f"{k}.png" for k in "ABCD"], row_text(page)
assert page._file_list.reorderable

# --- sürükleme başlatma: gerçek fare olayları ile -----------------------
started = []
page._file_list._start_drag = lambda row, origin: started.append(
    page._file_list.rows.index(row)
)
row = page._file_list.rows[2]


def mouse(kind, pos, buttons):
    return QMouseEvent(
        kind, QPointF(pos), QPointF(row.mapToGlobal(pos)),
        Qt.MouseButton.LeftButton, buttons, Qt.KeyboardModifier.NoModifier,
    )


# Küçük hareket sürükleme sayılmaz.
QApplication.sendEvent(row, mouse(QEvent.Type.MouseButtonPress, QPoint(60, 20), Qt.MouseButton.LeftButton))
QApplication.sendEvent(row, mouse(QEvent.Type.MouseMove, QPoint(61, 21), Qt.MouseButton.LeftButton))
assert started == [], started
QApplication.sendEvent(row, mouse(QEvent.Type.MouseButtonRelease, QPoint(61, 21), Qt.MouseButton.NoButton))
# Eşik aşılınca sürükleme başlar (ilk satır gövdesinden).
QApplication.sendEvent(row, mouse(QEvent.Type.MouseButtonPress, QPoint(60, 20), Qt.MouseButton.LeftButton))
QApplication.sendEvent(row, mouse(QEvent.Type.MouseMove, QPoint(60, 60), Qt.MouseButton.LeftButton))
assert started == [2], started
# Etiket (çocuk widget) üzerinden basılıp sürüklenince de başlar.
label = row.findChildren(QLabel)[1]
started.clear()
lpos = QPoint(4, 4)
QApplication.sendEvent(label, QMouseEvent(
    QEvent.Type.MouseButtonPress, QPointF(lpos), QPointF(label.mapToGlobal(lpos)),
    Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
QApplication.sendEvent(label, QMouseEvent(
    QEvent.Type.MouseMove, QPointF(4, 44), QPointF(label.mapToGlobal(QPoint(4, 44))),
    Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
assert started == [2], started

# --- bırakma: A,B,C,D → D,A,B,C → D,A,C,B ---------------------------------
drop_on(page, 3, 0)
assert names() == list("DABC"), names()
assert row_text(page) == [f"{k}.png" for k in "DABC"], row_text(page)

drop_on(page, 2, 4)
assert names() == list("DACB"), names()
assert row_text(page) == [f"{k}.png" for k in "DACB"], row_text(page)

# Kendi üstüne / hemen altına bırakmak sırayı değiştirmez.
drop_on(page, 1, 1)
drop_on(page, 1, 2)
assert names() == list("DACB"), names()

# --- oklar aynı sıra üzerinde çalışır --------------------------------------
# Satır düğmeleri: [yukarı, aşağı, sil]. B (3. indeks) yukarı → D,A,B,C.
press_button(page._file_list.rows[3], 0)
assert names() == list("DABC"), names()
assert row_text(page) == [f"{k}.png" for k in "DABC"], row_text(page)
# D (0. indeks) aşağı → A,D,B,C.
press_button(page._file_list.rows[0], 1)
assert names() == list("ADBC"), names()
# Ok durumları yeni sıradan: ilk satırın yukarı, son satırın aşağı düğmesi kapalı.
first, last = page._file_list.rows[0], page._file_list.rows[-1]
assert not first.findChildren(QPushButton)[0].isEnabled()
assert not last.findChildren(QPushButton)[1].isEnabled()
# Numara etiketleri yeni sıraya göre.
details = [
    [l.text() for l in r.findChildren(QLabel) if l.objectName() == "opFileDetail"][0]
    for r in page._file_list.rows
]
assert [d.split(".")[0] for d in details] == ["1", "2", "3", "4"], details

# Sürükle → tekrar ok: sıra tek kaynaktan (`_paths`) yürür.
drop_on(page, 0, 4)   # A sona → D,B,C,A
assert names() == list("DBCA"), names()
press_button(page._file_list.rows[3], 0)  # A yukarı → D,B,A,C
assert names() == list("DBAC"), names()
expected = list("DBAC")

# --- dönüştürme yükü UI sırasıyla aynı -----------------------------------
page._page_mode_buttons["original"].setChecked(True)
page._on_convert_clicked()
wait_idle(page._runner)

assert len(payloads) == 1, payloads
assert [Path(p).stem for p in payloads[0]] == expected, payloads
assert len(results) == 1

reader = PdfReader(results[0].stored_path)
out_widths = [float(p.mediabox.width) / float(p.mediabox.height) for p in reader.pages]
want = [widths[k] / 200 for k in expected]
assert len(out_widths) == 4
for got, exp in zip(out_widths, want):
    assert abs(got - exp) < 0.02, (out_widths, want)

# Madde 14: başarılı dönüştürme sonrası `_paths` temizlenir; PDF → Görsel
# türünde birden fazla dosya eklenince sıralama artık açık (yalnız
# images_to_pdf'e özel değil).
page._add_paths([make_pdf("x.pdf", 1), make_pdf("y.pdf", 1)])
pump(200)
assert page._kind() == "pdf_to_images", page._kind()
assert page._file_list.reorderable
page.shutdown() if hasattr(page, "shutdown") else None
print("SCENARIO OK")
"""

MERGE = r"""
from pdf_reme.presentation.pages.merge_page import MergePage

counts = {"A": 1, "B": 2, "C": 3, "D": 4}
widths = {"A": 100, "B": 110, "C": 120, "D": 130}
paths = {k: make_pdf(f"{k}.pdf", counts[k], width=widths[k]) for k in "ABCD"}

page = MergePage()
page.resize(1100, 760)
page.show()
pump(200)

calls = []
real_merge = backend_gateway.merge_pdfs
outputs = []


def spy(paths_, name):
    calls.append(list(paths_))
    document = real_merge(paths_, name)
    outputs.append(document)
    return document


backend_gateway.merge_pdfs = spy

page._add_paths([paths[k] for k in "ABCD"])
pump(500)

names = lambda: [Path(p).stem for p in page._paths]
assert names() == list("ABCD"), names()
assert row_text(page) == [f"{k}.pdf" for k in "ABCD"], row_text(page)
assert page._file_list.reorderable

summary = page._summary_label.text()
assert "10" in summary and "4" in summary, summary  # 4 dosya, 10 sayfa


def details():
    return [
        [l.text() for l in r.findChildren(QLabel) if l.objectName() == "opFileDetail"][0]
        for r in page._file_list.rows
    ]


strip_no = lambda text: text.split('.', 1)[1].strip()  # baştaki sıra no'yu at
before = {n: strip_no(d) for n, d in zip(row_text(page), details())}

# --- sürükle: A,B,C,D → D,A,C,B ------------------------------------------
drop_on(page, 3, 0)
drop_on(page, 2, 4)
assert names() == list("DACB"), names()
assert row_text(page) == [f"{k}.pdf" for k in "DACB"], row_text(page)

# Meta (sayfa sayısı vb.) ve toplam sayfa satırlarla birlikte taşındı.
after = {n: strip_no(d) for n, d in zip(row_text(page), details())}
assert after == before, (before, after)
assert page._summary_label.text() == summary

# Her satırın sil düğmesi kendi dosyasını siler (indeks doğru yeniden bağlandı).
# --- oklar: B (3. satır) yukarı → D,A,B,C ----------------------------------
press_button(page._file_list.rows[3], 0)
assert names() == list("DABC"), names()
press_button(page._file_list.rows[0], 1)  # D aşağı → A,D,B,C
assert names() == list("ADBC"), names()
assert row_text(page) == [f"{k}.pdf" for k in "ADBC"], row_text(page)

# Sürükle → ok → sürükle: sıra tek kaynaktan yürür.
drop_on(page, 1, 4)   # D sona → A,B,C,D
assert names() == list("ABCD"), names()
drop_on(page, 3, 1)   # D → A,D,B,C
press_button(page._file_list.rows[2], 0)  # B yukarı → A,B,D,C
assert names() == list("ABDC"), names()
expected = list("ABDC")

# Sil düğmesi (son düğme) doğru dosyayı çıkarır, sıra bozulmaz; sonra geri ekle.
press_button(page._file_list.rows[2], 2)  # D sil
assert names() == list("ABC"), names()
assert "D" not in {Path(p).stem for p in page._infos}
assert "6" in page._summary_label.text()
page._add_paths([paths["D"]])
pump(500)
assert names() == list("ABCD"), names()
# Yeni sırayı belirle: D sürükle → A,B,D,C
drop_on(page, 3, 2)
assert names() == list("ABDC"), names()

# --- birleştirme: backend'e UI sırası gider -------------------------------
page._name_input.setText("out")
page._on_merge()
wait_idle(page._runner)
assert len(calls) == 1, calls
assert [Path(p).stem for p in calls[0]] == expected, calls

reader = PdfReader(outputs[0].stored_path)
seq = [round(float(p.mediabox.width)) for p in reader.pages]
want = []
for k in expected:
    want += [widths[k]] * counts[k]
assert seq == want, (seq, want)
assert len(reader.pages) == 10
print("SCENARIO OK")
"""

EDIT = r"""
from pdf_reme.presentation.backend_gateway import EditOperation
from pdf_reme.presentation.pages.edit_page import EditPage

page = EditPage()
page.resize(1300, 800)
page.show()
pump(200)

source = make_pdf("ten.pdf", 10)
page._open_source(source)
pump(800)


def strip():
    return page._grid_scroll.verticalScrollBar().value()


def view_page():
    return page._view.current_page


page._on_page_clicked(7)
page._view.scroll_to(7)
pump(300)
bar = page._grid_scroll.verticalScrollBar()
bar.setValue(bar.maximum())
pump(200)

start_strip = strip()
assert start_strip > 0, start_strip
assert page._page_count == 10
assert view_page() >= 6, view_page()


def step(action, count, tag):
    action()
    pump(1200)
    assert page._page_count == count, (tag, page._page_count)
    assert strip() > 0, f"{tag}: şerit başa atladı"
    assert view_page() > 1, f"{tag}: büyük görünüm başa atladı ({view_page()})"


# Döndür: bağlam tamamen aynı kalır.
step(lambda: page._rotate(90), 10, "rotate")
assert strip() == start_strip, (strip(), start_strip)
assert page._selected == {7}, page._selected

# Çoğalt: kopya seçilir ve görünür kalır.
step(page._duplicate, 11, "duplicate")
assert page._selected == {8}, page._selected

# Boş sayfa ekle: yeni sayfa seçilir.
step(page._insert_blank, 12, "blank")
assert page._selected == {9}, page._selected

# Sil: sonraki sayfa seçilir (silinen yerine gelen).
step(page._delete, 11, "delete")
assert page._selected == {9}, page._selected

# Geri al: silinen sayfa geri gelir ve seçili olur.
step(page._on_undo, 12, "undo")
assert page._selected == {9}, page._selected

# Yinele: tekrar silinir, komşu seçili.
step(page._on_redo, 11, "redo")
assert page._selected == {9}, page._selected

# PDF'ten sayfa ekle (iletişim kutusu yerine doğrudan işlem).
other = make_pdf("other.pdf", 3)
page._start_step(
    EditOperation(
        "insert_pages",
        {"insert_pdf_path": other, "source_page_numbers": [1, 2], "after_page": 8},
    )
)
pump(1200)
assert page._page_count == 13
assert strip() > 0 and view_page() > 1
assert page._selected == {9, 10}, page._selected

# Sıralama: seçili sayfaları taşı.
page._selected = {9, 10}
page._move(1)
pump(1200)
assert page._page_count == 13
assert strip() > 0 and view_page() > 1, (strip(), view_page())

# Son sayfayı sil: seçim önceki sayfaya gider.
page._on_page_clicked(13)
pump(200)
page._delete()
pump(1200)
assert page._page_count == 12
assert page._selected == {12}, page._selected
assert strip() > 0

# Geri al → silinen son sayfa geri gelir.
page._on_undo()
pump(800)
assert page._page_count == 13
assert page._selected == {13}, page._selected
assert strip() > 0 and view_page() > 1

page.shutdown()
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
        timeout=300,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "SCENARIO OK" in result.stdout


def test_convert_drag_and_arrows_share_one_order(tmp_path):
    _run(CONVERT, tmp_path)


def test_merge_drag_and_arrows_share_one_order(tmp_path):
    _run(MERGE, tmp_path)


def test_edit_operations_keep_scroll_and_selection_context(tmp_path):
    _run(EDIT, tmp_path)
