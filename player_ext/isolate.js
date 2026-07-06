// Content script: isola o container do player na página do episódio do goyabu,
// escondendo cabeçalho, navegação, comentários e anúncios — deixando só o vídeo.
// Reaplica continuamente (o site carrega o cabeçalho/anúncios de forma tardia).
(function () {
  "use strict";

  function ensureStyle() {
    var style = document.getElementById("aplayer-isolate");
    if (!style) {
      style = document.createElement("style");
      style.id = "aplayer-isolate";
      (document.head || document.documentElement).appendChild(style);
    }
    style.textContent =
      "html,body{margin:0!important;padding:0!important;background:#000!important;overflow:hidden!important;height:100%!important;}" +
      ".aplayer-host{position:fixed!important;top:0!important;left:0!important;width:100vw!important;height:100vh!important;" +
      "z-index:2147483647!important;background:#000!important;margin:0!important;padding:0!important;}" +
      ".aplayer-host iframe,.aplayer-host video{width:100%!important;height:100%!important;border:none!important;}" +
      "ins,.ad,.ads,.advert,.banner,[id*='ad-'],[class*='ad-'],[id*='ads'],iframe[src*='ads']{display:none!important;}";
  }

  function isolate() {
    // SÓ o container real do player — nunca um iframe qualquer (pode ser anúncio).
    var wrapper =
      document.querySelector(".playerWrapper") ||
      document.getElementById("player");
    if (!wrapper) return false;

    ensureStyle();

    // Esconde os irmãos de cada ancestral, do wrapper até o body. Reaplicado a
    // cada mutação, então cabeçalho/anúncios que carreguem depois somem também.
    var node = wrapper;
    while (node && node !== document.body && node.parentElement) {
      var parent = node.parentElement;
      Array.prototype.forEach.call(parent.children, function (sib) {
        if (sib !== node && !sib.classList.contains("aplayer-host")) {
          sib.style.setProperty("display", "none", "important");
        }
      });
      node = parent;
    }
    wrapper.classList.add("aplayer-host");
    return true;
  }

  // Bloqueia pop-ups/pop-unders de anúncios (window.open) no mundo da página.
  function blockPopups() {
    try {
      var s = document.createElement("script");
      s.textContent =
        "(function(){try{window.open=function(){return null;};" +
        "var _a=HTMLAnchorElement.prototype.click;}catch(e){}})();";
      (document.head || document.documentElement).appendChild(s);
      s.remove();
    } catch (e) {}
  }

  blockPopups();
  ensureStyle();

  // Reaplica isolate() com frequência no início e depois a cada mudança do DOM.
  var pending = false;
  function schedule() {
    if (pending) return;
    pending = true;
    setTimeout(function () { pending = false; isolate(); }, 120);
  }

  var quick = setInterval(isolate, 300);
  setTimeout(function () { clearInterval(quick); }, 15000);

  if (document.readyState !== "loading") isolate();
  document.addEventListener("DOMContentLoaded", isolate);

  try {
    new MutationObserver(schedule).observe(
      document.documentElement,
      { childList: true, subtree: true }
    );
  } catch (e) {}
})();
