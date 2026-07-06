"""Janela de player baseada no Edge WebView2 (via pywebview).

Executada como PROCESSO SEPARADO do app principal PySide6, pois o pywebview
roda seu próprio loop de eventos (incompatível com o do Qt). O Edge WebView2
já vem no Windows e inclui os codecs proprietários (H.264/AAC) que faltam ao
QtWebEngine do PyPI — por isso o player do Blogger reproduz aqui.

Carrega a página do episódio (para que o JS do site decodifique o token do
Blogger) e injeta CSS/JS para isolar o container do player, escondendo a
navegação e os anúncios do site.
"""
import os
import subprocess
import sys
import traceback
import webbrowser

# Força o pythonnet a usar o .NET Framework (netfx), sempre presente no Windows
# 10/11. A autodetecção de runtime (coreclr vs netfx) do pythonnet às vezes
# falha no .exe empacotado ("Failed to resolve Python.Runtime.Loader.Initialize");
# fixar netfx torna a inicialização do WebView2 determinística.
os.environ.setdefault("PYTHONNET_RUNTIME", "netfx")

from utils import data_dir, setup_logging

logger = setup_logging()

# JS que isola o player: esconde os irmãos de cada ancestral (sem mover o
# iframe no DOM, o que o recarregaria) e fixa o container na viewport.
ISOLATE_JS = r"""
(function() {
    function isolate() {
        var wrapper = document.querySelector('.playerWrapper')
                    || document.getElementById('player')
                    || (document.getElementsByTagName('iframe')[0] || {}).parentElement;
        if (!wrapper) { return false; }
        var style = document.getElementById('aplayer-isolate');
        if (!style) {
            style = document.createElement('style');
            style.id = 'aplayer-isolate';
            document.head.appendChild(style);
        }
        style.innerHTML = ''
            + 'html,body{margin:0!important;padding:0!important;background:#000!important;overflow:hidden!important;}'
            + '.aplayer-host{position:fixed!important;top:0!important;left:0!important;width:100vw!important;'
            + 'height:100vh!important;z-index:2147483647!important;background:#000!important;margin:0!important;padding:0!important;}'
            + '.aplayer-host iframe,.aplayer-host video{width:100%!important;height:100%!important;border:none!important;}';
        var node = wrapper;
        while (node && node !== document.body && node.parentElement) {
            var parent = node.parentElement;
            Array.prototype.forEach.call(parent.children, function(sib) {
                if (sib !== node) { sib.style.setProperty('display', 'none', 'important'); }
            });
            node = parent;
        }
        wrapper.classList.add('aplayer-host');
        return true;
    }
    if (!isolate()) {
        var tries = 0;
        var t = setInterval(function() {
            tries++;
            if (isolate() || tries > 30) { clearInterval(t); }
        }, 400);
    }
})();
"""


def _on_loaded(window):
    try:
        window.evaluate_js(ISOLATE_JS)
    except Exception:
        pass


def _from_registry(exe: str) -> str | None:
    """Lê o caminho do navegador no registro (App Paths) — robusto a instalações
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
    """Localiza o Edge (ou Chrome) para abrir em modo app (janela sem abas).
    Tenta caminhos padrão e, em seguida, o registro do Windows."""
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
    # Fallback: registro (App Paths)
    for exe in ("msedge.exe", "chrome.exe"):
        found = _from_registry(exe)
        if found:
            return found
    return None


def _open_app_window(url: str):
    """Fallback confiável (sem pythonnet): abre o episódio numa janela dedicada
    do Edge/Chrome em modo aplicativo (--app) — sem barra de endereço nem abas,
    parecendo o player do app. Usa o mesmo motor Chromium (H.264) do WebView2."""
    browser = _find_chromium()
    if browser:
        data_root = str(data_dir() / "player_profile")
        try:
            subprocess.Popen([
                browser,
                f"--app={url}",
                "--window-size=1120,700",
                f"--user-data-dir={data_root}",
                "--no-first-run",
                "--no-default-browser-check",
            ])
            logger.info("Player: aberto em janela de app (%s)", os.path.basename(browser))
            return
        except Exception as e:
            logger.error("Player: falha ao abrir modo app (%s)", e)
    # Último recurso: handler padrão do sistema.
    try:
        os.startfile(url)
    except Exception:
        webbrowser.open(url)


def run(url: str, title: str):
    logger.info("Player: abrindo '%s' (runtime .NET=%s)", title,
                os.environ.get("PYTHONNET_RUNTIME"))
    # Caminho primário: janela embutida via Edge WebView2 (pywebview).
    try:
        import webview
        window = webview.create_window(
            title=title or "APlayer",
            url=url,
            width=1100,
            height=680,
            background_color="#000000",
            text_select=False,
        )
        window.events.loaded += lambda: _on_loaded(window)
        # storage_path gravável: o WebView2 precisa criar sua pasta de dados;
        # o local padrão (ao lado do .exe, ex.: em Downloads) pode ser bloqueado.
        wv2_dir = str(data_dir() / "webview2")
        webview.start(gui="edgechromium", private_mode=False, storage_path=wv2_dir)
        logger.info("Player: WebView2 embutido encerrado normalmente")
    except Exception as e:
        # Qualquer falha do WebView2 (pythonnet/clr, backend ausente, etc.):
        # registra o motivo COMPLETO no log e cai para o navegador padrão.
        logger.error("Player: WebView2 FALHOU (%s: %s) — abrindo no navegador",
                     type(e).__name__, e)
        logger.error("Player traceback:\n%s", traceback.format_exc())
        _open_app_window(url)


if __name__ == "__main__":
    _url = sys.argv[1] if len(sys.argv) > 1 else ""
    _title = sys.argv[2] if len(sys.argv) > 2 else "APlayer"
    run(_url, _title)
