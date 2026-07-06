import json
import logging
import os
import random
import subprocess
import sys
from pathlib import Path

BASE_URL = "https://goyabu.io"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

CONFIG_PATH = Path(__file__).parent / "config.json"


def data_dir() -> Path:
    """Diretório persistente de dados do usuário (favoritos, histórico).
    Usa %APPDATA%/APlayer no Windows; fallback para ~/.aplayer."""
    base = os.environ.get("APPDATA") or str(Path.home())
    d = Path(base) / "APlayer"
    d.mkdir(parents=True, exist_ok=True)
    return d

DEFAULT_CONFIG = {
    "base_url": BASE_URL,
    "request_timeout": 15,
    "max_retries": 3,
}


def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def get_default_headers(referer: str | None = None) -> dict[str, str]:
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "DNT": "1",
    }
    if referer:
        headers["Referer"] = referer
    else:
        headers["Referer"] = BASE_URL
    return headers


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def launch_player(url: str, title: str):
    """Abre o episódio numa janela de app do Edge/Chrome (via player_webview).
    Import tardio para evitar dependência circular."""
    import player_webview
    return player_webview.open_player(url, title or "APlayer")


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("aplayer")
    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
            datefmt="%H:%M:%S",
        )
        # Console (útil rodando via Python)
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        logger.addHandler(stream)
        # Arquivo (essencial no .exe --windowed, onde não há console)
        try:
            fh = logging.FileHandler(data_dir() / "aplayer.log", encoding="utf-8")
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except OSError:
            pass
    logger.setLevel(level)
    return logger
