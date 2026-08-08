from __future__ import annotations

import os
from pathlib import Path

APP_ID = "com.forintx.VideoIndirici"
APP_NAME = "Downloader"
WEBSITE_URL = "https://muhammetburakakkas.com"
SCHEMA_VERSION = 2


def _read_version() -> str:
    candidates = (
        Path(__file__).resolve().parent.parent / "VERSION",
        Path(__file__).resolve().parent / "VERSION",
    )
    for candidate in candidates:
        try:
            return candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
    return "1.0.0-beta.2"


APP_VERSION = _read_version()
APP_VERSION_LABEL = "1.0 Beta" if APP_VERSION.startswith("1.0.0-beta.") else APP_VERSION.replace("-", " ")

HOME = Path.home()
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "video-indirici"
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share")) / "video-indirici"
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", HOME / ".local/state")) / "video-indirici"
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache")) / "video-indirici"

CONFIG_FILE = CONFIG_DIR / "config.json"
QUEUE_FILE = DATA_DIR / "queue.json"
HISTORY_FILE = DATA_DIR / "history.json"
LOG_FILE = STATE_DIR / "app.log"
LEGACY_CONFIG_FILE = DATA_DIR / "config.json"

DEFAULT_DOWNLOAD_DIR = HOME / "Videolar" / "YouTube"
OUTPUT_MARKER = "__VIDEO_INDIRICI_FILE__"

SPEED_LIMITS = (
    "Sınırsız",
    "256 KB/s",
    "512 KB/s",
    "1 MB/s",
    "2 MB/s",
    "5 MB/s",
    "10 MB/s",
)
PARALLEL_OPTIONS = ("1", "2", "3", "4")
FRAGMENT_OPTIONS = ("1", "2", "4", "8")
COOKIE_BROWSERS = ("firefox", "chrome", "chromium", "brave")

SUB_LANGS = ("Türkçe", "İngilizce", "Almanca", "Fransızca", "İspanyolca", "Japonca")
SUB_LANG_MAP = {
    "Türkçe": "tr",
    "İngilizce": "en",
    "Almanca": "de",
    "Fransızca": "fr",
    "İspanyolca": "es",
    "Japonca": "ja",
}

DEFAULT_CONFIG = {
    "schema_version": SCHEMA_VERSION,
    "config_version": APP_VERSION,
    "language": "tr",
    "folder": str(DEFAULT_DOWNLOAD_DIR),
    "notify": True,
    "open_folder": False,
    "clipboard": True,
    "speed_limit": "Sınırsız",
    "parallel": "3",
    "concurrent_fragments": 4,
    "default_preset": "video-best-mp4",
    "custom_format": "",
    "filename_template": "%(title)s.%(ext)s",
    "playlist_filename_template": "%(playlist_index)03d - %(title)s.%(ext)s",
    "download_subs": False,
    "sub_lang": "Türkçe",
    "sub_auto": False,
    "embed_subs": False,
    "download_thumbnail": True,
    "embed_metadata": True,
    "keep_chapters": True,
    "playlist_folder": True,
    "cookie_mode": "none",
    "cookie_browser": "firefox",
    "cookie_profile": "",
    "cookie_file": "",
}

SUPPORTED_HOSTS = (
    "youtube.com",
    "youtu.be",
    "twitch.tv",
    "dailymotion.com",
    "vimeo.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
)
