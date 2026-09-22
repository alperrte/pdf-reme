import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QIcon, QPixmap
from PySide6.QtWidgets import QApplication

from pdf_reme.infrastructure.database.init_db import init_database
from pdf_reme.presentation.theme import get_theme_manager
from pdf_reme.presentation.windows.main_window import MainWindow
from pdf_reme.presentation.windows.splash_screen import SplashScreen


BASE_DIR = Path(__file__).resolve().parent


def get_app_icon() -> QIcon:
    icon_path = (
        BASE_DIR
        / "resources"
        / "images"
        / "icon.png"
    )

    original = QPixmap(
        str(icon_path)
    )

    if original.isNull():
        print(
            f"UYARI: Uygulama ikonu bulunamadı: {icon_path}"
        )

        return QIcon()

    # Taskbar üzerinde ikonun biraz daha büyük
    # görünmesi için tasarımı bozmadan kırpıyoruz.
    crop_ratio = 0.12

    crop_x = int(
        original.width()
        * crop_ratio
    )

    crop_y = int(
        original.height()
        * crop_ratio
    )

    cropped_width = (
        original.width()
        - (crop_x * 2)
    )

    cropped_height = (
        original.height()
        - (crop_y * 2)
    )

    cropped = original.copy(
        crop_x,
        crop_y,
        cropped_width,
        cropped_height,
    )

    zoomed = cropped.scaled(
        256,
        256,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    return QIcon(
        zoomed
    )


def load_stylesheet(
    app: QApplication,
) -> None:
    qss_path = (
        BASE_DIR
        / "resources"
        / "styles"
        / "app.qss"
    )

    if not qss_path.exists():
        print(
            f"UYARI: QSS bulunamadı: {qss_path}"
        )

        return

    stylesheet = qss_path.read_text(
        encoding="utf-8"
    )

    app.setStyleSheet(
        stylesheet
    )

    print(
        f"QSS yüklendi: {qss_path}"
    )


def load_fonts() -> None:
    fonts_dir = (
        BASE_DIR
        / "resources"
        / "fonts"
    )

    # Regular/Bold "Plus Jakarta Sans" ailesi altında klasik
    # stil eşleşmesiyle gelir; Medium/SemiBold ise OpenType'ın
    # 4 stilli aile modeli yüzünden kendi ayrı aile adlarıyla
    # kayıtlı olur (bkz. app.qss'teki font-family kullanımları).
    font_files = [
        "PlusJakartaSans-Regular.ttf",
        "PlusJakartaSans-Medium.ttf",
        "PlusJakartaSans-SemiBold.ttf",
        "PlusJakartaSans-Bold.ttf",
    ]

    for font_file in font_files:
        font_path = fonts_dir / font_file

        if font_path.exists():
            QFontDatabase.addApplicationFont(
                str(font_path)
            )
        else:
            print(
                f"UYARI: Font bulunamadı: {font_path}"
            )


def main() -> int:
    app = QApplication(
        sys.argv
    )

    app.setStyle(
        "Fusion"
    )

    app.setApplicationName(
        "PDF-REME"
    )

    app.setOrganizationName(
        "PDF-REME"
    )

    app.setApplicationDisplayName(
        "PDF-REME"
    )

    # Temiz kurulumda (ör. paketlenmiş exe) tablolar henüz yoktur; var olan
    # veritabanına dokunmaz, yalnızca eksik tabloları oluşturur.
    init_database()

    load_fonts()

    theme_manager = get_theme_manager()

    theme_manager.apply_palette(
        app
    )

    app_icon = get_app_icon()

    app.setWindowIcon(
        app_icon
    )

    load_stylesheet(
        app
    )

    window = MainWindow()

    window.setWindowIcon(
        app_icon
    )

    splash = SplashScreen()

    def _show_main_window() -> None:
        window.show()

        splash.close()

    splash.finished.connect(
        _show_main_window
    )

    splash.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(
        main()
    )