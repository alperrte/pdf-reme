from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("PDF-REME")
        self.resize(1280, 800)
        self.setMinimumSize(1000, 650)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setFixedWidth(220)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 24, 20, 24)

        logo_label = QLabel("PDF-REME")
        sidebar_layout.addWidget(logo_label)
        sidebar_layout.addStretch()

        content = QWidget()

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 32, 32, 32)

        title_label = QLabel("Ana Sayfa")
        title_label.setStyleSheet(
            "font-size: 28px; font-weight: 600;"
        )

        description_label = QLabel(
            "PDF belgelerinizi yerel olarak yönetin, düzenleyin ve dönüştürün."
        )

        content_layout.addWidget(title_label)
        content_layout.addWidget(description_label)
        content_layout.addStretch()

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content, 1)