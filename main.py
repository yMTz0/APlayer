import sys

from PySide6.QtWidgets import QApplication

from ui_main import MainWindow
from widgets import apply_dark_theme


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("APlayer")
    app.setApplicationVersion("1.0.0")

    apply_dark_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
