"""Madde 7-10: `LanguageManager`/`ThemeManager`'ın çalışma zamanı (kenar
çubuğu anlık geçişi) davranışının, `app_settings`'in kalıcı başlangıç
varsayılanını ASLA etkilemediğini doğrular -- ve tersi: `app_settings`
üzerinden yapılan kalıcı değişikliğin, zaten var olan bir yönetici
örneğinin çalışma zamanı değerini etkilemediğini doğrular. QSettings gerçek
kayıt defteri yerine tmp'ye yönlendirilir (bkz. `test_app_settings.py`).
"""

import pytest
from PySide6.QtCore import QCoreApplication, QSettings

from pdf_reme.presentation import app_settings
from pdf_reme.presentation.i18n import LanguageManager
from pdf_reme.presentation.theme import ThemeManager


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path):
    old_org = QCoreApplication.organizationName()
    old_app = QCoreApplication.applicationName()
    old_format = QSettings.defaultFormat()

    QCoreApplication.setOrganizationName("pdfreme_test")
    QCoreApplication.setApplicationName("pdfreme_test")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path),
    )

    settings_file = QSettings().fileName().replace("\\", "/").lower()
    assert str(tmp_path).replace("\\", "/").lower() in settings_file

    yield

    QSettings().sync()
    QSettings.setDefaultFormat(old_format)
    QCoreApplication.setOrganizationName(old_org)
    QCoreApplication.setApplicationName(old_app)


def test_language_manager_reads_startup_default_on_init():
    app_settings.set_startup_language("en")

    manager = LanguageManager()

    assert manager.current_language == "en"


def test_theme_manager_reads_startup_default_on_init():
    app_settings.set_startup_theme("dark")

    manager = ThemeManager()

    assert manager.current_theme == "dark"


def test_language_manager_set_language_does_not_persist():
    app_settings.set_startup_language("tr")

    manager = LanguageManager()
    manager.set_language("en")

    assert manager.current_language == "en"
    # Kenar çubuğu anlık geçişi, kalıcı başlangıç varsayılanını değiştirmez.
    assert app_settings.startup_language() == "tr"


def test_theme_manager_set_theme_does_not_persist():
    app_settings.set_startup_theme("light")

    manager = ThemeManager()
    manager.set_theme("dark")

    assert manager.current_theme == "dark"
    assert app_settings.startup_theme() == "light"


def test_theme_manager_toggle_does_not_persist():
    app_settings.set_startup_theme("light")

    manager = ThemeManager()
    manager.toggle_theme()

    assert manager.current_theme == "dark"
    assert app_settings.startup_theme() == "light"


def test_language_manager_toggle_does_not_persist():
    app_settings.set_startup_language("tr")

    manager = LanguageManager()
    manager.toggle_language()

    assert manager.current_language == "en"
    assert app_settings.startup_language() == "tr"


def test_persisted_startup_change_does_not_affect_existing_manager_runtime():
    app_settings.set_startup_language("tr")
    app_settings.set_startup_theme("light")

    manager_language = LanguageManager()
    manager_theme = ThemeManager()

    # Ayarlar sayfasından kalıcı varsayılan değiştirilir (Madde 7-10'daki
    # settings_page.py::_on_theme_chosen/_on_language_chosen çağrısının
    # karşılığı) -- zaten var olan yönetici örneklerinin çalışma zamanı
    # değeri bundan ETKİLENMEMELİDİR (yalnızca bir sonraki açılışta
    # uygulanır).
    app_settings.set_startup_language("en")
    app_settings.set_startup_theme("dark")

    assert manager_language.current_language == "tr"
    assert manager_theme.current_theme == "light"

    # Ama yeni bir yönetici örneği (örn. bir sonraki açılış) artık yeni
    # kalıcı varsayılanı okur.
    assert LanguageManager().current_language == "en"
    assert ThemeManager().current_theme == "dark"


def test_language_manager_set_language_emits_signal():
    manager = LanguageManager()
    received = []
    manager.language_changed.connect(received.append)

    manager.set_language("en")

    assert received == ["en"]


def test_theme_manager_set_theme_emits_signal():
    manager = ThemeManager()
    received = []
    manager.theme_changed.connect(received.append)

    manager.set_theme("dark")

    assert received == ["dark"]


def test_invalid_language_and_theme_are_ignored_at_runtime():
    language_manager = LanguageManager()
    theme_manager = ThemeManager()

    language_manager.set_language("de")
    theme_manager.set_theme("neon")

    assert language_manager.current_language == "tr"
    assert theme_manager.current_theme == "light"
