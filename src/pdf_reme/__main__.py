import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
)


def get_app_icon() -> QIcon:
    icon_path = (
        Path(__file__).resolve().parent
        / "resources"
        / "images"
        / "icon.png"
    )

    original = QPixmap(
        str(icon_path)
    )

    if original.isNull():
        return QIcon()

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


def main() -> int:
    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        "PDF-REME"
    )

    app.setOrganizationName(
        "PDF-REME"
    )

    app_icon = get_app_icon()

    app.setWindowIcon(
        app_icon
    )

    window = QMainWindow()

    window.setWindowTitle(
        "PDF-REME"
    )

    window.setWindowIcon(
        app_icon
    )

    window.resize(
        1280,
        800,
    )

    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(
        main()
    )