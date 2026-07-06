import sys

from PySide6.QtWidgets import QApplication

from ui_main import MainWindow
from widgets import apply_dark_theme


def _run_player_mode():
    """Modo player: aberto como subprocesso pelo app principal.
    Abre a janela Edge WebView2 (com codecs H.264) para reproduzir o episódio.
    """
    import player_webview
    idx = sys.argv.index("--play")
    url = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else ""
    title = sys.argv[idx + 2] if len(sys.argv) > idx + 2 else "APlayer"
    player_webview.run(url, title)


def main():
    if "--play" in sys.argv:
        _run_player_mode()
        return

    app = QApplication(sys.argv)
    app.setApplicationName("APlayer")
    app.setApplicationVersion("1.0.0")

    apply_dark_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
