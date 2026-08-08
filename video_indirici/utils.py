from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from .constants import SPEED_LIMITS, SUPPORTED_HOSTS


def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
        host = (parsed.hostname or "").lower()
        return parsed.scheme in ("http", "https") and any(
            host == allowed or host.endswith(f".{allowed}") for allowed in SUPPORTED_HOSTS
        )
    except ValueError:
        return False


def is_playlist_url(url: str) -> bool:
    lowered = url.lower()
    return any(token in lowered for token in ("playlist", "list=", "youtube.com/@", "/channel/", "/sets/"))


def parse_speed_limit(text: str) -> str | None:
    if text not in SPEED_LIMITS or text == "Sınırsız":
        return None
    match = re.match(r"([\d.]+)\s*(KB|MB|GB)", text)
    if not match:
        return None
    value = float(match.group(1))
    printable = str(int(value)) if value.is_integer() else str(value)
    return f"{printable}{match.group(2)[0]}"


def format_size(value: float | int | str) -> str:
    try:
        size = float(value)
    except (TypeError, ValueError):
        return str(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return ""


def format_eta(value: float | int | str) -> str:
    try:
        seconds = max(0, int(float(value)))
    except (TypeError, ValueError):
        return "--:--"
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


def format_duration(value: float | int | str) -> str:
    try:
        seconds = max(0, int(float(value)))
    except (TypeError, ValueError):
        return ""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


def safe_folder_name(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", value).strip(". ")
    return cleaned[:180] or "Playlist"


def path_uri(path: str | Path) -> str:
    return Path(path).expanduser().resolve().as_uri()


def redact_command(command: list[str]) -> list[str]:
    redacted = list(command)
    for flag in ("--cookies", "--cookies-from-browser"):
        try:
            index = redacted.index(flag)
        except ValueError:
            continue
        if index + 1 < len(redacted):
            redacted[index + 1] = "<gizlendi>"
    return redacted
