"""Janela de player baseada no Edge WebView2 (via pywebview).

Executada como PROCESSO SEPARADO do app principal PySide6, pois o pywebview
roda seu próprio loop de eventos (incompatível com o do Qt). O Edge WebView2
já vem no Windows e inclui os codecs proprietários (H.264/AAC) que faltam ao
QtWebEngine do PyPI — por isso o player do Blogger reproduz aqui.

Carrega a página do episódio (para que o JS do site decodifique o token do
Blogger) e injeta CSS/JS para isolar o container do player, escondendo a
navegação e os anúncios do site.
"""
import sys

import webview

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


def run(url: str, title: str):
    window = webview.create_window(
        title=title or "APlayer",
        url=url,
        width=1100,
        height=680,
        background_color="#000000",
        text_select=False,
    )
    window.events.loaded += lambda: _on_loaded(window)
    # gui='edgechromium' força o backend WebView2 (Edge) no Windows.
    webview.start(gui="edgechromium", private_mode=False)


if __name__ == "__main__":
    _url = sys.argv[1] if len(sys.argv) > 1 else ""
    _title = sys.argv[2] if len(sys.argv) > 2 else "APlayer"
    run(_url, _title)
