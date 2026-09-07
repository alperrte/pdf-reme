import sys

from PySide6.QtWidgets import QApplication

from pdf_reme.presentation.windows.main_window import MainWindow
from pdf_reme.shared.paths.app_paths import AppPaths


def main() -> int:
    paths = AppPaths()

    print(f"PDF-REME veri yolu: {paths.data_dir}")

    paths.ensure_directories()

    print(f"Veri klasörü oluşturuldu mu: {paths.data_dir.exists()}")

    app = QApplication(sys.argv)

    app.setApplicationName("PDF-REME")
    app.setOrganizationName("PDF-REME")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())