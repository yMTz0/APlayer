import json
import re
from dataclasses import dataclass, field

import requests
from PySide6.QtCore import QThread, Signal

from utils import BASE_URL, get_default_headers, setup_logging

logger = setup_logging()


@dataclass
class EpisodeInfo:
    id: int
    number: str
    url: str
    thumbnail: str
    audio: str = ""
    title: str = ""


@dataclass
class PlayerSource:
    name: str
    url: str
    player_type: str = ""
    blogger_token: str = ""


@dataclass
class AnimeInfo:
    title: str
    url: str
    slug: str = ""
    thumbnail: str = ""
    audio: str = ""
    year: str = ""
    episodes: list[EpisodeInfo] = field(default_factory=list)


class GoyabuScraper:
    """Extrator de metadados para a estrutura do goyabu.io.

    A página do anime embute um array JSON `allEpisodes` inline no HTML.
    A página do episódio embute `playersData` com as URLs dos players.
    """

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(get_default_headers())
        self._nonce: str | None = None

    def _get(self, url: str) -> str:
        self._session.headers["User-Agent"] = get_default_headers()["User-Agent"]
        resp = self._session.get(url, timeout=15)
        resp.raise_for_status()
        return resp.text

    def _ensure_nonce(self) -> str | None:
        """Visita a homepage para obter o nonce e os cookies de sessão que
        validam as chamadas à API de busca."""
        if self._nonce:
            return self._nonce
        html = self._get(BASE_URL)
        match = re.search(r'glosAP\s*=\s*\{[^}]*"nonce"\s*:\s*"([^"]+)"', html)
        self._nonce = match.group(1) if match else None
        return self._nonce

    def search_anime(self, query: str) -> list[AnimeInfo]:
        nonce = self._ensure_nonce()
        if not nonce:
            logger.warning("Nonce de busca não encontrado")
            return []

        resp = self._session.get(
            f"{BASE_URL}/wp-json/animeonline/search/",
            params={"keyword": query, "nonce": nonce},
            headers={"Referer": BASE_URL},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        if isinstance(data, dict) and "error" not in data:
            for _id, item in data.items():
                results.append(
                    AnimeInfo(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        thumbnail=item.get("img", ""),
                        audio=item.get("audio", ""),
                        year=str(item.get("year", "")),
                    )
                )

        logger.info("Busca '%s': %d resultados", query, len(results))
        return results

    def extract_episodes(self, anime_url: str) -> AnimeInfo:
        html = self._get(anime_url)

        title_match = re.search(r'<h1[^>]*class="text-hidden"[^>]*>([^<]+)</h1>', html)
        title = title_match.group(1).strip() if title_match else "Desconhecido"

        ep_match = re.search(r"allEpisodes\s*=\s*(\[\{.*?\}])\s*;", html)
        if not ep_match:
            logger.warning("allEpisodes não encontrado em %s", anime_url)
            return AnimeInfo(title=title, url=anime_url, episodes=[])

        episodes_json = json.loads(ep_match.group(1))
        episodes = []
        for ep in episodes_json:
            ep_url = BASE_URL + ep["link"] if ep["link"].startswith("/") else ep["link"]
            thumb = ""
            if ep.get("miniature"):
                thumb = BASE_URL + ep["miniature"] if ep["miniature"].startswith("/") else ep["miniature"]
            elif ep.get("imagem"):
                img = ep["imagem"]
                thumb = (BASE_URL + img) if img.startswith("/") else img

            episodes.append(
                EpisodeInfo(
                    id=ep["id"],
                    number=str(ep.get("episodio", "")),
                    url=ep_url,
                    thumbnail=thumb,
                    audio=ep.get("audio", ""),
                    title=ep.get("episode_name", ""),
                )
            )

        logger.info("Anime '%s': %d episódios extraídos", title, len(episodes))
        return AnimeInfo(title=title, url=anime_url, episodes=episodes)

    def extract_player_sources(self, episode_url: str) -> list[PlayerSource]:
        html = self._get(episode_url)

        match = re.search(r"playersData\s*=\s*(\[\{.*?\}])\s*;", html)
        if not match:
            logger.warning("playersData não encontrado em %s", episode_url)
            return []

        players_json = json.loads(match.group(1))
        sources = []
        for p in players_json:
            sources.append(
                PlayerSource(
                    name=p.get("name", ""),
                    url=p.get("url", ""),
                    player_type=p.get("select", ""),
                    blogger_token=p.get("blogger_token", ""),
                )
            )

        logger.info("Episódio: %d fontes de player encontradas", len(sources))
        return sources

    def get_search_nonce(self) -> str | None:
        html = self._get(BASE_URL)
        match = re.search(r'glosAP\s*=\s*\{[^}]*"nonce"\s*:\s*"([^"]+)"', html)
        return match.group(1) if match else None

    def close(self):
        self._session.close()


class ScraperWorker(QThread):
    """Worker thread para operações de scraping sem bloquear a UI."""

    results_ready = Signal(object)
    error_occurred = Signal(str)

    class Task:
        SEARCH = "search"
        EPISODES = "episodes"
        PLAYER = "player"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scraper = GoyabuScraper()
        self._task: str = ""
        self._args: dict = {}

    def configure(self, task: str, **kwargs) -> "ScraperWorker":
        self._task = task
        self._args = kwargs
        return self

    def run(self):
        try:
            if self._task == self.Task.SEARCH:
                result = self._scraper.search_anime(self._args["query"])
            elif self._task == self.Task.EPISODES:
                result = self._scraper.extract_episodes(self._args["url"])
            elif self._task == self.Task.PLAYER:
                result = self._scraper.extract_player_sources(self._args["url"])
            else:
                self.error_occurred.emit(f"Tarefa desconhecida: {self._task}")
                return
            self.results_ready.emit(result)
        except requests.RequestException as e:
            logger.error("Erro de rede: %s", e)
            self.error_occurred.emit(f"Erro de rede: {e}")
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error("Erro de parsing: %s", e)
            self.error_occurred.emit(f"Erro ao processar dados: {e}")

    def stop(self):
        self._scraper.close()
        self.quit()
        self.wait()
