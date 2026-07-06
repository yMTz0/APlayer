"""Player: abre o episódio numa janela dedicada do Edge/Chrome em modo aplicativo
(--app), com uma extensão que isola o player e esconde o site/anúncios do goyabu.

Usa o navegador Chromium do sistema (Edge, presente no Windows) — que tem os
codecs H.264/AAC — SEM depender do pythonnet/pywebview, que se mostrou frágil no
.exe empacotado. A janela não tem abas nem barra de endereço: mostra só o vídeo.
"""
import os
import subprocess
import sys
import webbrowser

from utils import data_dir, setup_logging

logger = setup_logging()


def _from_registry(exe: str) -> str | None:
    """Caminho do navegador no registro (App Paths) — robusto a instalações
    fora dos diretórios padrão."""
    try:
        import winreg
    except ImportError:
        return None
    key = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}"
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, key) as k:
                path, _ = winreg.QueryValueEx(k, None)
                if path and os.path.isfile(path):
                    return path
        except OSError:
            continue
    return None


def _find_chromium() -> str | None:
    """Localiza o Edge (ou Chrome) para abrir em modo app (janela sem abas)."""
    candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    for exe in ("msedge.exe", "chrome.exe"):
        found = _from_registry(exe)
        if found:
            return found
    return None


def _extension_dir() -> str | None:
    """Caminho da extensão que isola o player (esconde site/anúncios).
    Funciona em dev e no .exe empacotado (datas em sys._MEIPASS)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    ext = os.path.join(base, "player_ext")
    return ext if os.path.isfile(os.path.join(ext, "manifest.json")) else None


def open_player(url: str, title: str = "APlayer") -> subprocess.Popen | None:
    """Abre o episódio numa janela de app do Edge/Chrome, com a extensão de
    isolação. Retorna o processo (para o app poder fechá-lo depois)."""
    logger.info("Player: abrindo '%s'", title)
    browser = _find_chromium()
    if browser:
        args = [
            browser,
            f"--app={url}",
            "--window-size=1120,700",
            f"--user-data-dir={data_dir() / 'player_profile'}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-sync",
            "--disable-features=EdgeSync,msImplicitSignin,ShowSyncFirstRunExperience",
        ]
        ext = _extension_dir()
        if ext:
            args.append(f"--load-extension={ext}")
            args.append(f"--disable-extensions-except={ext}")
        try:
            proc = subprocess.Popen(args)
            logger.info("Player: janela de app (%s), isolação=%s",
                        os.path.basename(browser), bool(ext))
            return proc
        except Exception as e:
            logger.error("Player: falha ao abrir modo app (%s)", e)
    # Último recurso: handler padrão do sistema.
    logger.warning("Player: navegador Chromium não encontrado; usando handler padrão")
    try:
        os.startfile(url)
    except Exception:
        webbrowser.open(url)
    return None


# Executado como subprocesso (main.py --play) — mantido por compatibilidade.
def run(url: str, title: str):
    open_player(url, title)


if __name__ == "__main__":
    _url = sys.argv[1] if len(sys.argv) > 1 else ""
    _title = sys.argv[2] if len(sys.argv) > 2 else "APlayer"
    run(_url, _title)
