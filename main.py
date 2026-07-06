import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from splash import SplashScreen
from ui_main import MainWindow
from utils import logo_path
from widgets import apply_dark_theme


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("APlayer")
    app.setApplicationVersion("1.1.0")

    apply_dark_theme(app)

    lp = logo_path()
    if lp:
        app.setWindowIcon(QIcon(lp))

    # Tela de carregamento
    splash = SplashScreen()
    splash.show()

    window = MainWindow()
    if lp:
        window.setWindowIcon(QIcon(lp))

    def _reveal():
        window.show()
        splash.raise_()

    def _go():
        _reveal()
        splash.finish()

    # Mostra o splash por um instante e transita para o app.
    QTimer.singleShot(2000, _go)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
