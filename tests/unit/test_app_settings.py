"""Uygulama ayarları — QSettings gerçek kayıt defteri yerine tmp'ye yönlendirilir."""

import pytest
from PySide6.QtCore import QCoreApplication, QSettings

from pdf_reme.presentation import app_settings


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


def test_defaults():
    assert app_settings.startup_animation() is True
    assert app_settings.theme_animation() is True
    assert app_settings.language_animation() is True
    assert app_settings.default_compress_level() == "balanced"
    assert app_settings.split_keep_rest() is True
    assert app_settings.auto_update_check() is False


def test_round_trip():
    app_settings.set_startup_animation(False)
    app_settings.set_theme_animation(False)
    app_settings.set_language_animation(False)
    app_settings.set_default_compress_level("light")
    app_settings.set_split_keep_rest(False)
    app_settings.set_auto_update_check(True)

    assert app_settings.startup_animation() is False
    assert app_settings.theme_animation() is False
    assert app_settings.language_animation() is False
    assert app_settings.default_compress_level() == "light"
    assert app_settings.split_keep_rest() is False
    assert app_settings.auto_update_check() is True

    app_settings.set_startup_animation(True)
    app_settings.set_split_keep_rest(True)

    assert app_settings.startup_animation() is True
    assert app_settings.split_keep_rest() is True


def test_invalid_compress_level_is_ignored():
    app_settings.set_default_compress_level("strong")
    app_settings.set_default_compress_level("ultra")

    assert app_settings.default_compress_level() == "strong"


def test_corrupt_stored_values_fall_back_to_defaults():
    settings = QSettings()
    settings.setValue("defaults/compress_level", "bozuk")
    settings.setValue("startup/animation", "belki")

    assert app_settings.default_compress_level() == "balanced"
    # Tanınmayan metin false sayılır; yalnız 1/true/yes açıktır.
    assert app_settings.startup_animation() is False


def test_string_booleans_from_ini_are_parsed():
    settings = QSettings()
    settings.setValue("startup/animation", "true")
    settings.setValue("defaults/split_keep_rest", "false")

    assert app_settings.startup_animation() is True
    assert app_settings.split_keep_rest() is False


def test_startup_language_and_theme_defaults():
    # Madde 7-10: kalıcı başlangıç varsayılanları, hiç ayarlanmamışken
    # i18n/theme modüllerinin kendi varsayılanlarına düşer.
    assert app_settings.startup_language() == "tr"
    assert app_settings.startup_theme() == "light"


def test_startup_language_and_theme_round_trip():
    app_settings.set_startup_language("en")
    app_settings.set_startup_theme("dark")

    assert app_settings.startup_language() == "en"
    assert app_settings.startup_theme() == "dark"

    app_settings.set_startup_language("tr")
    app_settings.set_startup_theme("light")

    assert app_settings.startup_language() == "tr"
    assert app_settings.startup_theme() == "light"


def test_startup_language_and_theme_reuse_legacy_keys():
    # Geriye uyumluluk: yeni fonksiyonlar, LanguageManager/ThemeManager'ın
    # eskiden doğrudan okuyup yazdığı anahtar adlarını birebir kullanır --
    # böylece mevcut kullanıcının kayıtlı değeri sıfırlanmadan "başlangıç
    # varsayılanı" haline gelir.
    settings = QSettings()
    settings.setValue("appearance/language", "en")
    settings.setValue("appearance/theme", "dark")

    assert app_settings.startup_language() == "en"
    assert app_settings.startup_theme() == "dark"


def test_invalid_startup_language_and_theme_are_ignored():
    app_settings.set_startup_language("de")
    app_settings.set_startup_theme("blue")

    assert app_settings.startup_language() == "tr"
    assert app_settings.startup_theme() == "light"


def test_corrupt_stored_startup_language_and_theme_fall_back_to_defaults():
    settings = QSettings()
    settings.setValue("appearance/language", "xx")
    settings.setValue("appearance/theme", "neon")

    assert app_settings.startup_language() == "tr"
    assert app_settings.startup_theme() == "light"
