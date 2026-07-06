"""Persistência da biblioteca do usuário: favoritos e histórico de progresso.

Guarda tudo em um único JSON em %APPDATA%/APlayer/library.json, de modo a
sobreviver a reinícios e funcionar também no executável empacotado.
"""
import json
import time

from utils import data_dir, setup_logging

logger = setup_logging()

LIBRARY_PATH = data_dir() / "library.json"


def _anime_dict(anime) -> dict:
    return {
        "title": anime.title,
        "url": anime.url,
        "thumbnail": getattr(anime, "thumbnail", ""),
        "audio": getattr(anime, "audio", ""),
        "year": getattr(anime, "year", ""),
    }


class Library:
    """Gerencia favoritos e histórico. Uma instância única serve o app todo."""

    def __init__(self):
        self._data = {"favorites": {}, "history": {}}
        self._load()

    # ------------------------------------------------------------------
    def _load(self):
        if LIBRARY_PATH.exists():
            try:
                with open(LIBRARY_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._data["favorites"] = loaded.get("favorites", {})
                self._data["history"] = loaded.get("history", {})
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Falha ao ler biblioteca: %s", e)

    def _save(self):
        try:
            with open(LIBRARY_PATH, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.warning("Falha ao salvar biblioteca: %s", e)

    # ------------------------------------------------------------------
    #  Favoritos
    # ------------------------------------------------------------------
    def is_favorite(self, anime_url: str) -> bool:
        return anime_url in self._data["favorites"]

    def toggle_favorite(self, anime) -> bool:
        """Alterna favorito. Retorna o novo estado (True = favoritado)."""
        favs = self._data["favorites"]
        if anime.url in favs:
            del favs[anime.url]
            self._save()
            return False
        favs[anime.url] = _anime_dict(anime)
        self._save()
        return True

    def favorites(self) -> list[dict]:
        return list(self._data["favorites"].values())

    # ------------------------------------------------------------------
    #  Histórico / progresso
    # ------------------------------------------------------------------
    def record_open(self, anime, episode):
        """Registra a POSIÇÃO atual (último episódio aberto) para o 'continuar
        de onde parou'. NÃO marca o episódio como assistido — isso é manual."""
        hist = self._data["history"]
        entry = hist.get(anime.url, {})
        entry.update(_anime_dict(anime))
        entry["last_number"] = str(episode.number)
        entry["last_url"] = episode.url
        entry["updated_at"] = time.time()
        entry.setdefault("watched", [])
        hist[anime.url] = entry
        self._save()

    def set_watched(self, anime, episode, watched: bool):
        """Marca/desmarca um episódio como assistido (ação manual do usuário)."""
        hist = self._data["history"]
        entry = hist.get(anime.url, {})
        entry.update(_anime_dict(anime))
        entry.setdefault("updated_at", time.time())
        current = set(entry.get("watched", []))
        if watched:
            current.add(episode.url)
        else:
            current.discard(episode.url)
        entry["watched"] = list(current)
        hist[anime.url] = entry
        self._save()

    def history(self) -> list[dict]:
        """Animes em progresso, do mais recente para o mais antigo."""
        items = list(self._data["history"].values())
        items.sort(key=lambda e: e.get("updated_at", 0), reverse=True)
        return items

    def last_episode(self, anime_url: str) -> dict | None:
        entry = self._data["history"].get(anime_url)
        if entry and entry.get("last_url"):
            return {"number": entry.get("last_number", ""), "url": entry["last_url"]}
        return None

    def watched_episodes(self, anime_url: str) -> set[str]:
        entry = self._data["history"].get(anime_url)
        return set(entry.get("watched", [])) if entry else set()

    def remove_history(self, anime_url: str):
        if anime_url in self._data["history"]:
            del self._data["history"][anime_url]
            self._save()
