from PySide6.QtCore import (Qt, Slot, QPropertyAnimation, QEasingCurve,
                            QAbstractAnimation)
from PySide6.QtGui import QFont, QCursor
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from scraper import AnimeInfo, EpisodeInfo, ScraperWorker
from storage import Library
from utils import launch_player, setup_logging
from widgets import (
    BACKDROP,
    BG_DARK,
    BG_SURFACE,
    BORDER,
    GLASS_BAR,
    GLOSS_BTN,
    GLOSS_BTN_HI,
    TEAL,
    TEAL_DARK,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    AnimeCard,
    SearchWidget,
    StatusBar,
    VideoCard,
)

logger = setup_logging()


def _anime_from_dict(d: dict) -> AnimeInfo:
    return AnimeInfo(
        title=d.get("title", ""),
        url=d.get("url", ""),
        thumbnail=d.get("thumbnail", ""),
        audio=d.get("audio", ""),
        year=str(d.get("year", "")),
    )


class FlowGrid(QWidget):
    """Grid de cards que reflui conforme a largura (sem scroll próprio)."""

    def __init__(self, card_width: int, parent=None):
        super().__init__(parent)
        self._cw = card_width + 14
        self._cards: list[QWidget] = []
        self._cols = 0
        self._relaying = False
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(14)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

    def set_cards(self, cards: list[QWidget]):
        self.clear()
        self._cards = cards
        for c in cards:
            c.setParent(self)
        self._cols = 0  # força o próximo relayout
        self._relayout()

    def clear(self):
        for c in self._cards:
            c.setParent(None)
            c.deleteLater()
        self._cards = []
        self._cols = 0
        while self._grid.count():
            self._grid.takeAt(0)

    def _relayout(self):
        # Guarda de reentrância: addWidget dispara resizeEvent, que chama
        # _relayout de novo — sem isto vira recursão e estoura a pilha (segfault).
        if self._relaying:
            return
        cols = max(1, self.width() // self._cw)
        if cols == self._cols and self._grid.count() == len(self._cards):
            return
        self._relaying = True
        try:
            self._cols = cols
            while self._grid.count():
                self._grid.takeAt(0)
            for i, card in enumerate(self._cards):
                self._grid.addWidget(card, i // cols, i % cols)
        finally:
            self._relaying = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._cards:
            self._relayout()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("APlayer — Media Center")
        self.setMinimumSize(940, 620)
        self.resize(1180, 760)

        self._library = Library()
        self._worker = ScraperWorker(self)
        self._worker.results_ready.connect(self._on_results)
        self._worker.error_occurred.connect(self._on_error)
        self._current_anime: AnimeInfo | None = None
        self._player_proc = None
        self._setup_ui()
        self._render_home()

    # ------------------------------------------------------------------
    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("central")
        central.setStyleSheet(f"#central {{ background: {BACKDROP}; }}")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- Header ----
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(74)
        header.setStyleSheet(
            f"#header {{ background: {GLASS_BAR}; border-bottom: 1px solid rgba(255,255,255,0.75); }}")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(20)

        logo = QPushButton("▶  APlayer")
        logo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        logo.setFont(QFont("Segoe UI", 17, QFont.Weight.Black))
        logo.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {TEAL}; border: none; text-align: left; }}
            QPushButton:hover {{ color: #5eead4; }}
        """)
        logo.setToolTip("Início")
        logo.clicked.connect(self._go_home)
        hl.addWidget(logo)

        self._search = SearchWidget()
        self._search.search_requested.connect(self._on_search)
        hl.addWidget(self._search, 1)
        root.addWidget(header)

        # ---- Stack ----
        self._stack = QStackedWidget()
        root.addWidget(self._stack, 1)

        self._home_page = self._build_home()
        self._episodes_page = self._build_episodes()
        self._stack.addWidget(self._home_page)
        self._stack.addWidget(self._episodes_page)

        # ---- Status ----
        self._status = StatusBar()
        root.addWidget(self._status)

    def _build_home(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        self._home_layout = QVBoxLayout(container)
        self._home_layout.setContentsMargins(24, 20, 24, 16)
        self._home_layout.setSpacing(18)
        self._home_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(container)
        return scroll

    def _build_episodes(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 16, 24, 12)
        layout.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(12)
        back = QPushButton("‹  Voltar")
        back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        back.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        back.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {TEAL}; border: none; padding: 6px 4px; }}
            QPushButton:hover {{ color: {TEXT_PRIMARY}; }}
        """)
        back.clicked.connect(self._go_home)
        top.addWidget(back)

        self._anime_title = QLabel()
        self._anime_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self._anime_title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        top.addWidget(self._anime_title)

        top.addStretch()

        self._continue_btn = QPushButton()
        self._continue_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._continue_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self._continue_btn.setStyleSheet(f"""
            QPushButton {{ background: {GLOSS_BTN}; color: #ffffff;
                border: 1px solid rgba(255,255,255,0.7); border-radius: 18px; padding: 8px 18px; }}
            QPushButton:hover {{ background: {GLOSS_BTN_HI}; }}
        """)
        self._continue_btn.clicked.connect(self._on_continue)
        self._continue_btn.hide()
        top.addWidget(self._continue_btn)

        self._fav_btn = QPushButton()
        self._fav_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._fav_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self._fav_btn.clicked.connect(self._on_fav_toggle)
        top.addWidget(self._fav_btn)
        layout.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._episodes_grid = FlowGrid(card_width=VideoCard.POSTER.width())
        scroll.setWidget(self._episodes_grid)
        layout.addWidget(scroll, 1)
        return page

    # ------------------------------------------------------------------
    #  Home / biblioteca
    # ------------------------------------------------------------------
    def _clear_home(self):
        while self._home_layout.count():
            item = self._home_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _add_section(self, title: str, cards: list[QWidget], card_width: int):
        header = QLabel(title)
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {TEXT_PRIMARY};")
        self._home_layout.addWidget(header)

        grid = FlowGrid(card_width=card_width)
        grid.set_cards(cards)
        self._home_layout.addWidget(grid)

    def _render_home(self):
        """Mostra 'Continuar assistindo' e 'Favoritos' (estado inicial)."""
        self._clear_home()

        history = self._library.history()
        favorites = self._library.favorites()

        if not history and not favorites:
            hint = QLabel("Busque um anime para começar.\n\n"
                          "Favorite animes na estrela ★ e seu progresso aparece aqui.")
            hint.setFont(QFont("Segoe UI", 13))
            hint.setStyleSheet(f"color: {TEXT_SECONDARY};")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._home_layout.addStretch()
            self._home_layout.addWidget(hint)
            self._home_layout.addStretch()
            return

        if history:
            cards = []
            for entry in history[:12]:
                anime = _anime_from_dict(entry)
                sub = f"Parou no EP {entry.get('last_number', '?')}"
                card = AnimeCard(anime, is_favorite=self._library.is_favorite(anime.url), subtitle=sub)
                card.clicked.connect(self._on_anime_selected)
                card.favorite_clicked.connect(self._on_fav_card)
                cards.append(card)
            self._add_section("▶  Continuar assistindo", cards, AnimeCard.POSTER.width())

        if favorites:
            cards = []
            for entry in favorites:
                anime = _anime_from_dict(entry)
                card = AnimeCard(anime, is_favorite=True)
                card.clicked.connect(self._on_anime_selected)
                card.favorite_clicked.connect(self._on_fav_card)
                cards.append(card)
            self._add_section("★  Favoritos", cards, AnimeCard.POSTER.width())

    def _switch_to(self, page: QWidget):
        """Troca de página com um fade-in suave. O efeito é removido ao fim,
        para não interferir no relayout do grid (evita instabilidade)."""
        self._stack.setCurrentWidget(page)
        eff = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", page)
        anim.setDuration(240)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: page.setGraphicsEffect(None))
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def _go_home(self):
        self._render_home()
        self._switch_to(self._home_page)
        self._status.set_message("Pronto")

    # ------------------------------------------------------------------
    #  Busca
    # ------------------------------------------------------------------
    def _on_search(self, query: str):
        self._last_query = query
        self._status.set_message(f"Buscando '{query}'…")
        self._search.set_enabled(False)
        self._worker.configure(ScraperWorker.Task.SEARCH, query=query).start()

    @Slot(object)
    def _on_results(self, result):
        self._search.set_enabled(True)
        if isinstance(result, AnimeInfo):
            self._show_anime_episodes(result)
        elif isinstance(result, list):
            self._show_search_results(result)

    @Slot(str)
    def _on_error(self, error: str):
        self._search.set_enabled(True)
        self._status.set_message(error, is_error=True)
        logger.error("Erro: %s", error)

    def _show_search_results(self, results: list[AnimeInfo]):
        self._clear_home()
        if results:
            cards = []
            for anime in results:
                card = AnimeCard(anime, is_favorite=self._library.is_favorite(anime.url))
                card.clicked.connect(self._on_anime_selected)
                card.favorite_clicked.connect(self._on_fav_card)
                cards.append(card)
            self._add_section(f"Resultados ({len(results)})", cards, AnimeCard.POSTER.width())
            self._status.set_message(f"{len(results)} anime(s) encontrado(s)")
        else:
            q = getattr(self, "_last_query", "")
            msg = (f"Nenhum resultado para “{q}”.\n\n"
                   "Dica: o site cataloga os animes pelo nome em japonês (romaji).\n"
                   "Tente o título original — ex.: “Kimetsu no Yaiba” em vez de “Demon Slayer”,\n"
                   "ou “Shingeki no Kyojin” em vez de “Attack on Titan”.")
            lbl = QLabel(msg)
            lbl.setFont(QFont("Segoe UI", 12))
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._home_layout.addStretch()
            self._home_layout.addWidget(lbl)
            self._home_layout.addStretch()
            self._status.set_message("Nenhum resultado — tente o nome em japonês", is_error=True)
        self._switch_to(self._home_page)

    # ------------------------------------------------------------------
    #  Episódios
    # ------------------------------------------------------------------
    def _on_anime_selected(self, anime: AnimeInfo):
        self._status.set_message(f"Carregando episódios de '{anime.title}'…")
        self._worker.configure(ScraperWorker.Task.EPISODES, url=anime.url).start()

    def _show_anime_episodes(self, anime: AnimeInfo):
        self._current_anime = anime
        self._anime_title.setText(f"{anime.title}  ·  {len(anime.episodes)} episódios")
        self._update_fav_btn()

        watched = self._library.watched_episodes(anime.url)
        last = self._library.last_episode(anime.url)
        last_url = last["url"] if last else None

        if last:
            self._continue_btn.setText(f"▶  Continuar EP {last['number']}")
            self._continue_btn.show()
        else:
            self._continue_btn.hide()

        cards = []
        for ep in anime.episodes:
            card = VideoCard(
                ep,
                watched=ep.url in watched,
                highlight=(ep.url == last_url),
            )
            card.clicked.connect(self._on_episode_selected)
            card.watched_toggled.connect(self._on_watched_toggle)
            cards.append(card)
        self._episodes_grid.set_cards(cards)
        self._status.set_message(f"{len(anime.episodes)} episódio(s) carregado(s)")
        self._switch_to(self._episodes_page)

    def _on_episode_selected(self, episode: EpisodeInfo):
        title = f"EP {episode.number}"
        if self._current_anime:
            title = f"{self._current_anime.title} — EP {episode.number}"
            # Grava só a POSIÇÃO (continuar de onde parou); não marca assistido.
            self._library.record_open(self._current_anime, episode)
            self._continue_btn.setText(f"▶  Continuar EP {episode.number}")
            self._continue_btn.show()
        self._status.set_message(f"Abrindo player do episódio {episode.number}…")
        try:
            # Fecha a janela do player anterior para não empilhar janelas
            # (era o que causava o "player some/minimiza" a cada clique).
            if self._player_proc is not None and self._player_proc.poll() is None:
                self._player_proc.terminate()
            self._player_proc = launch_player(episode.url, title)
        except Exception as e:
            logger.error("Falha ao abrir player: %s", e)
            self._status.set_message(f"Erro ao abrir player: {e}", is_error=True)

    def _on_watched_toggle(self, episode: EpisodeInfo, watched: bool):
        if self._current_anime:
            self._library.set_watched(self._current_anime, episode, watched)
            estado = "assistido" if watched else "não assistido"
            self._status.set_message(f"EP {episode.number} marcado como {estado}")

    def _on_continue(self):
        if not self._current_anime:
            return
        last = self._library.last_episode(self._current_anime.url)
        if last:
            for ep in self._current_anime.episodes:
                if ep.url == last["url"]:
                    self._on_episode_selected(ep)
                    return

    # ------------------------------------------------------------------
    #  Favoritos
    # ------------------------------------------------------------------
    def _update_fav_btn(self):
        if not self._current_anime:
            return
        fav = self._library.is_favorite(self._current_anime.url)
        self._fav_btn.setText("★  Favoritado" if fav else "☆  Favoritar")
        color = "#fbbf24" if fav else TEXT_PRIMARY
        self._fav_btn.setStyleSheet(f"""
            QPushButton {{ background: rgba(255,255,255,0.10); color: {color};
                border: 1px solid rgba(255,255,255,0.20); border-radius: 18px; padding: 8px 16px; }}
            QPushButton:hover {{ background: rgba(255,255,255,0.18); color: #fbbf24; }}
        """)

    def _on_fav_toggle(self):
        if self._current_anime:
            self._library.toggle_favorite(self._current_anime)
            self._update_fav_btn()

    def _on_fav_card(self, anime: AnimeInfo):
        self._library.toggle_favorite(anime)
        state = "adicionado aos" if self._library.is_favorite(anime.url) else "removido dos"
        self._status.set_message(f"'{anime.title}' {state} favoritos")

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_focused_once", False):
            self._focused_once = True
            self._search.focus_input()

    def closeEvent(self, event):
        # Encerra o player e para a thread de scraping antes do teardown do Qt.
        if self._player_proc is not None and self._player_proc.poll() is None:
            self._player_proc.terminate()
        self._worker.stop()
        super().closeEvent(event)
