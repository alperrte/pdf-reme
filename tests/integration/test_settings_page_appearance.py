"""Madde 7-10: `SettingsPage` görünüm kartının, kenar çubuğu (çalışma zamanı)
tema/dil geçişinden ETKİLENMEDEN yalnızca kalıcı başlangıç varsayılanını
gösterdiğini ve bu sayfadan yapılan seçimin yalnızca kalıcı varsayılanı
değiştirip çalışma zamanı yöneticilerine dokunmadığını doğrular. Ayrıca
"Bir sonraki açılışta uygulanacaktır." bilgi etiketinin TR/EN çevirisini
doğru gösterdiğini kontrol eder.

`backend_gateway.storage_summary()` gerçek uygulama veri klasörünü/DB'sini
kullandığından (bkz. `test_library_page_encrypted_import.py`'deki aynı ders),
senaryo veri klasörü ve DB'si geçici dizine yönlendirilmiş ayrı bir süreçte
(offscreen Qt) çalışır -- gerçek kullanıcı verisine ASLA dokunulmaz.
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

from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

# QSettings'i gerçek Windows kayıt defterinden tmp'ye yönlendir -- aksi
# halde `app_settings`/`get_theme_manager`/`get_language_manager` gerçek
# kullanıcı ayarlarını okuyup yazar (bkz. test_app_settings.py fixture'ı).
settings_dir = data / "settings"
settings_dir.mkdir(parents=True, exist_ok=True)
QCoreApplication.setOrganizationName("pdfreme_test")
QCoreApplication.setApplicationName("pdfreme_test")
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(
    QSettings.Format.IniFormat,
    QSettings.Scope.UserScope,
    str(settings_dir),
)
assert str(settings_dir).replace("\\", "/").lower() in (
    QSettings().fileName().replace("\\", "/").lower()
)

from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.connection import engine
import pdf_reme.infrastructure.database.models.document  # noqa: F401

assert "pdfreme_test" in str(engine.url)
Base.metadata.create_all(bind=engine)

from pdf_reme.presentation import app_settings
from pdf_reme.presentation.i18n import get_language_manager
from pdf_reme.presentation.theme import get_theme_manager
from pdf_reme.presentation.pages.settings_page import SettingsPage


def pump(ms=200):
    end = time.time() + ms / 1000
    while time.time() < end:
        QCoreApplication.processEvents()
        time.sleep(0.005)
"""

# Senaryo 1: kalıcı başlangıç varsayılanı EN/koyu iken kenar çubuğundan
# TR/açık'a anlık geçilir -- Ayarlar sayfası hâlâ EN/koyu göstermelidir
# (kenar çubuğu çalışma zamanı yöneticisini değiştirir, kalıcı varsayılanı
# değil), sayfa yeniden ziyaret edilse (refresh) bile.
SCENARIO_SIDEBAR_DOES_NOT_AFFECT_SETTINGS_VIEW = r"""
app_settings.set_startup_language("en")
app_settings.set_startup_theme("dark")

page = SettingsPage()
pump()

assert page._theme_buttons["dark"].isChecked()
assert page._language_buttons["en"].isChecked()

# Kenar çubuğu anlık geçişi (gerçek uygulamada sidebar toggle'ın yaptığı).
get_theme_manager().set_theme("light")
get_language_manager().set_language("tr")
pump()

# Ayarlar sayfası hâlâ kalıcı başlangıç varsayılanını (EN/koyu) göstermeli.
assert page._theme_buttons["dark"].isChecked()
assert page._language_buttons["en"].isChecked()
assert app_settings.startup_theme() == "dark"
assert app_settings.startup_language() == "en"

# Sayfa yeniden ziyaret edilse (refresh) bile aynı kalır.
page.refresh()
pump()
assert page._theme_buttons["dark"].isChecked()
assert page._language_buttons["en"].isChecked()

print("SCENARIO OK")
"""

# Senaryo 2: Ayarlar sayfasından tema/dil seçimi yalnızca kalıcı başlangıç
# varsayılanını değiştirir; o an mevcut çalışma zamanı yöneticilerinin
# değerine (kenar çubuğunun daha önce anlık geçirdiği değere) dokunmaz.
SCENARIO_SETTINGS_CHOICE_ONLY_PERSISTS_STARTUP_DEFAULT = r"""
app_settings.set_startup_language("tr")
app_settings.set_startup_theme("light")

# Kenar çubuğu önceden farklı bir çalışma zamanı değerine geçmiş olsun.
get_theme_manager().set_theme("dark")
get_language_manager().set_language("en")

page = SettingsPage()
pump()

# Ayarlar sayfasından kenar çubuğunun ayarladığından FARKLI bir seçim
# yapılır -- bu, _on_theme_chosen/_on_language_chosen'ın yanlışlıkla
# çalışma zamanı yöneticisine de yazmadığını ayırt edilebilir kılar.
page._on_theme_chosen("light")
page._on_language_chosen("tr")
pump()

assert app_settings.startup_theme() == "light"
assert app_settings.startup_language() == "tr"

# Çalışma zamanı yöneticileri, Ayarlar sayfasındaki tıklamadan ETKİLENMEMELİ
# -- kenar çubuğunun ayarladığı "dark"/"en" değerinde kalmalı, bu da Ayarlar
# sayfasının onlara hiç dokunmadığını (yalnızca app_settings'e yazdığını)
# kanıtlıyor.
assert get_theme_manager().current_theme == "dark"
assert get_language_manager().current_language == "en"

print("SCENARIO OK")
"""

# Senaryo 3: "Bir sonraki açılışta uygulanacaktır." bilgi etiketi TR/EN
# çevirisini doğru gösterir.
SCENARIO_RESTART_NOTICE_LABEL = r"""
page = SettingsPage()
pump()

assert page._appearance_restart_notice.text() == "Bir sonraki açılışta uygulanacaktır."

get_language_manager().set_language("en")
page.retranslate_ui()
pump()

assert page._appearance_restart_notice.text() == "Applies on the next launch."

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


def test_sidebar_runtime_switch_does_not_affect_settings_page_view(tmp_path):
    _run(SCENARIO_SIDEBAR_DOES_NOT_AFFECT_SETTINGS_VIEW, tmp_path)


def test_settings_page_choice_only_persists_startup_default(tmp_path):
    _run(SCENARIO_SETTINGS_CHOICE_ONLY_PERSISTS_STARTUP_DEFAULT, tmp_path)


def test_restart_notice_label_translates(tmp_path):
    _run(SCENARIO_RESTART_NOTICE_LABEL, tmp_path)
