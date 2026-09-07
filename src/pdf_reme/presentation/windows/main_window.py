from PySide6.QtWidgets import QMainWindow, QLabel
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PDF-REME")
        self.resize(1200, 750)

        label = QLabel("PDF-REME\nRead • Edit • Merge • Easily")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setCentralWidget(label)