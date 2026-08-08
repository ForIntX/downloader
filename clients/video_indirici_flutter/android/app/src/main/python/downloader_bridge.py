"""Android tarafındaki Kotlin köprüsü için küçük yt-dlp adaptörü.

FFmpeg işlemleri Kotlin tarafındaki LGPL FFmpegKit ile yapılır. Böylece yt-dlp
Android'de bir harici ffmpeg süreci başlatmak zorunda kalmaz.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yt_dlp
from yt_dlp.utils import DownloadCancelled

_qjs_path: str | None = None


def set_qjs_path(path: str | None) -> None:
    global _qjs_path
    _qjs_path = path if path and os.path.isfile(path) else None


def _base_options() -> dict[str, Any]:
    options = {
        "quiet": True,
        "no_warnings": True,
        "ignoreconfig": True,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
        "concurrent_fragment_downloads": 4,
        "continuedl": True,
        "noplaylist": True,
    }
    if _qjs_path:
        options["js_runtimes"] = {"quickjs": {"path": _qjs_path}}
    return options


def _safe_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _rate_limit_bytes(value: Any) -> int | None:
    text = str(value or "").strip().upper()
    if not text:
        return None
    multiplier = 1
    if text.endswith("K"):
        multiplier, text = 1024, text[:-1]
    elif text.endswith("M"):
        multiplier, text = 1024 * 1024, text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        return None


def _metadata(info: dict[str, Any]) -> dict[str, Any]:
    thumbnails = info.get("thumbnails") or []
    thumbnail = info.get("thumbnail")
    if thumbnails:
        usable = [item for item in thumbnails if item.get("url")]
        moderate = [item for item in usable if (_safe_int(item.get("width")) or 10_000) <= 640]
        if moderate:
            thumbnail = max(moderate, key=lambda item: _safe_int(item.get("width")) or 0).get("url")
        elif not thumbnail and usable:
            thumbnail = usable[0].get("url")
    return {
        "id": str(info.get("id") or ""),
        "url": str(info.get("webpage_url") or info.get("original_url") or ""),
        "webpage_url": str(info.get("webpage_url") or info.get("original_url") or ""),
        "title": str(info.get("title") or "Başlık bulunamadı"),
        "channel": info.get("channel") or info.get("uploader"),
        "uploader": info.get("uploader"),
        "description": info.get("description"),
        "thumbnail": thumbnail,
        "duration": _safe_int(info.get("duration")),
        "view_count": _safe_int(info.get("view_count")),
        "width": _safe_int(info.get("width")),
        "height": _safe_int(info.get("height")),
        "upload_date": info.get("upload_date"),
    }


def get_video_info(url: str) -> dict[str, Any]:
    options = _base_options()
    options.update({"skip_download": True, "playlistend": 1, "check_formats": False})
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict):
        raise RuntimeError("Video bilgisi alınamadı")
    return _metadata(info)


def get_video_info_json(url: str) -> str:
    return json.dumps(get_video_info(url), ensure_ascii=False)


def get_playlist(url: str) -> list[dict[str, Any]]:
    options = _base_options()
    options.update({"extract_flat": "in_playlist", "lazy_playlist": True, "noplaylist": False})
    result: list[dict[str, Any]] = []
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
        entries = info.get("entries") if isinstance(info, dict) else None
        if entries is None:
            return result
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            video_id = str(entry.get("id") or "")
            webpage_url = entry.get("webpage_url") or entry.get("url") or ""
            if webpage_url and not str(webpage_url).startswith(("http://", "https://")):
                webpage_url = f"https://www.youtube.com/watch?v={webpage_url}"
            result.append(
                {
                    "id": video_id,
                    "url": str(webpage_url),
                    "title": str(entry.get("title") or "Başlık bulunamadı"),
                    "channel": entry.get("channel") or entry.get("uploader"),
                    "duration": _safe_int(entry.get("duration")),
                    "thumbnail": entry.get("thumbnail"),
                    "available": entry.get("availability") not in {"private", "premium_only", "subscriber_only"},
                    "selected": True,
                }
            )
    return result


def get_playlist_json(url: str) -> str:
    return json.dumps(get_playlist(url), ensure_ascii=False)


def scan_playlist(url: str, callback: Any) -> None:
    """Flat playlist girdilerini toplu sonuç beklemeden Kotlin'e aktar."""
    options = _base_options()
    options.update({"extract_flat": "in_playlist", "lazy_playlist": True, "noplaylist": False})
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
        entries = info.get("entries") if isinstance(info, dict) else None
        if entries is None:
            return
        for entry in entries:
            if callback.isCancelled():
                return
            if not isinstance(entry, dict):
                continue
            video_id = str(entry.get("id") or "")
            webpage_url = entry.get("webpage_url") or entry.get("url") or ""
            if webpage_url and not str(webpage_url).startswith(("http://", "https://")):
                webpage_url = f"https://www.youtube.com/watch?v={webpage_url}"
            callback.onEntry(
                json.dumps(
                    {
                        "id": video_id,
                        "url": str(webpage_url),
                        "title": str(entry.get("title") or "Başlık bulunamadı"),
                        "channel": entry.get("channel") or entry.get("uploader"),
                        "duration": _safe_int(entry.get("duration")),
                        "thumbnail": entry.get("thumbnail"),
                        "available": entry.get("availability")
                        not in {"private", "premium_only", "subscriber_only"},
                        "selected": True,
                    },
                    ensure_ascii=False,
                )
            )


def _download_component(
    url: str,
    format_selector: str,
    output_template: str,
    callback: Any,
    phase_start: float,
    phase_size: float,
    rate_limit: int | None = None,
    concurrent_fragments: int = 4,
) -> dict[str, Any]:
    last_path: list[str] = []

    def progress_hook(status: dict[str, Any]) -> None:
        if callback.isCancelled():
            raise DownloadCancelled("Kullanıcı tarafından durduruldu")
        state = status.get("status")
        if state == "downloading":
            downloaded = status.get("downloaded_bytes") or 0
            total = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
            percent = (downloaded / total * 100.0) if total else 0.0
            overall = phase_start + percent * phase_size
            callback.onProgress(
                float(overall),
                str(status.get("_speed_str") or "").strip(),
                _safe_int(status.get("eta")) or -1,
            )
        elif state == "finished":
            filename = status.get("filename")
            if filename:
                last_path[:] = [str(filename)]

    options = _base_options()
    options.update(
        {
            "format": format_selector,
            "outtmpl": output_template,
            "progress_hooks": [progress_hook],
            "overwrites": False,
            "concurrent_fragment_downloads": max(1, min(8, concurrent_fragments)),
        }
    )
    if rate_limit:
        options["ratelimit"] = rate_limit
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        if not last_path and isinstance(info, dict):
            requested = info.get("requested_downloads") or []
            if requested and requested[0].get("filepath"):
                last_path.append(str(requested[0]["filepath"]))
            else:
                last_path.append(str(ydl.prepare_filename(info)))
    if not last_path or not os.path.exists(last_path[-1]):
        raise RuntimeError("İndirilen geçici dosya bulunamadı")
    selected = info
    if isinstance(info, dict):
        requested = info.get("requested_downloads") or []
        if requested and isinstance(requested[0], dict):
            selected = requested[0]
    audio_codec = selected.get("acodec") if isinstance(selected, dict) else None
    video_codec = selected.get("vcodec") if isinstance(selected, dict) else None
    return {
        "path": last_path[-1],
        "has_audio": audio_codec not in {None, "none"},
        "has_video": video_codec not in {None, "none"},
    }


def download_job(job: dict[str, Any], temp_root: str, callback: Any) -> dict[str, Any]:
    job_id = str(job["id"])
    url = str(job["url"])
    preset_id = str(job["preset_id"])
    rate_limit = _rate_limit_bytes(job.get("speed_limit"))
    concurrent_fragments = _safe_int(job.get("concurrent_fragments")) or 4
    job_dir = Path(temp_root) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    if preset_id == "custom":
        selector = str(job.get("custom_format") or "").strip()
        if not selector:
            raise ValueError("Özel yt-dlp formatı boş bırakılamaz")
        if "+" in selector:
            video_selector, audio_selector = (part.strip() for part in selector.split("+", 1))
            if not video_selector or not audio_selector:
                raise ValueError("Geçersiz özel yt-dlp formatı")
            video = _download_component(
                url,
                video_selector,
                str(job_dir / "custom-video.%(ext)s"),
                callback,
                0.0,
                0.75,
                rate_limit,
                concurrent_fragments,
            )
            audio = _download_component(
                url,
                audio_selector,
                str(job_dir / "custom-audio.%(ext)s"),
                callback,
                75.0,
                0.25,
                rate_limit,
                concurrent_fragments,
            )
            return {
                "kind": "video",
                "components": [video["path"], audio["path"]],
                "extension": "mp4",
            }
        component = _download_component(
            url,
            selector,
            str(job_dir / "custom.%(ext)s"),
            callback,
            0.0,
            1.0,
            rate_limit,
            concurrent_fragments,
        )
        if component["has_video"]:
            return {"kind": "video", "components": [component["path"]], "extension": "mp4"}
        return {
            "kind": "audio",
            "components": [component["path"]],
            "extension": "m4a",
            "bitrate": 192,
        }

    if preset_id.startswith("audio-"):
        component = _download_component(
            url,
            "bestaudio[ext=m4a]/bestaudio/bestaudio*[ext=m4a]/bestaudio*/best[acodec!=none]/best",
            str(job_dir / "source.%(ext)s"),
            callback,
            0.0,
            1.0,
            rate_limit,
            concurrent_fragments,
        )
        extension = preset_id.removeprefix("audio-")
        if extension.isdigit():
            extension = "mp3"
        return {
            "kind": "audio",
            "components": [component["path"]],
            "extension": extension,
            "bitrate": _safe_int(job.get("audio_bitrate")) or 192,
        }

    height = _safe_int(job.get("height"))
    height_filter = f"[height<={height}]" if height else ""
    video_format = "/".join(
        (
            f"bestvideo{height_filter}[ext=mp4]",
            f"bestvideo{height_filter}",
            f"bestvideo*{height_filter}[ext=mp4]",
            f"bestvideo*{height_filter}",
            f"best{height_filter}[ext=mp4]",
            f"best{height_filter}",
            "best[ext=mp4]",
            "best",
        )
    )
    video = _download_component(
        url,
        video_format,
        str(job_dir / "video.%(ext)s"),
        callback,
        0.0,
        0.75,
        rate_limit,
        concurrent_fragments,
    )
    if video["has_audio"]:
        callback.onProgress(100.0, "", -1)
        return {"kind": "video", "components": [video["path"]], "extension": "mp4"}

    audio = _download_component(
        url,
        "bestaudio[ext=m4a]/bestaudio/bestaudio*[ext=m4a]/bestaudio*/best[acodec!=none]/best",
        str(job_dir / "audio.%(ext)s"),
        callback,
        75.0,
        0.25,
        rate_limit,
        concurrent_fragments,
    )
    return {
        "kind": "video",
        "components": [video["path"], audio["path"]],
        "extension": "mp4",
    }


def download_job_json(job_json: str, temp_root: str, callback: Any) -> str:
    return json.dumps(download_job(json.loads(job_json), temp_root, callback), ensure_ascii=False)
