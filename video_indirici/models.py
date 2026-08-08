from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DownloadStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


LEGACY_STATUS_MAP = {
    "bekliyor": DownloadStatus.PENDING.value,
    "indiriliyor": DownloadStatus.DOWNLOADING.value,
    "duraklatildi": DownloadStatus.PAUSED.value,
    "tamamlandi": DownloadStatus.COMPLETED.value,
    "hata": DownloadStatus.ERROR.value,
    "iptal": DownloadStatus.CANCELLED.value,
}


@dataclass(frozen=True)
class DownloadPreset:
    id: str
    label: str
    kind: str
    format_selector: str
    merge_container: str = ""
    audio_format: str = ""
    audio_quality: str = ""


PRESETS = (
    DownloadPreset(
        "video-best-mp4",
        "En iyi kalite (MP4)",
        "video",
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        merge_container="mp4",
    ),
    DownloadPreset("video-2160-mp4", "2160p MP4", "video", "bestvideo[height<=2160]+bestaudio/best[height<=2160]", "mp4"),
    DownloadPreset("video-1440-mp4", "1440p MP4", "video", "bestvideo[height<=1440]+bestaudio/best[height<=1440]", "mp4"),
    DownloadPreset("video-1080-mp4", "1080p MP4", "video", "bestvideo[height<=1080]+bestaudio/best[height<=1080]", "mp4"),
    DownloadPreset("video-720-mp4", "720p MP4", "video", "bestvideo[height<=720]+bestaudio/best[height<=720]", "mp4"),
    DownloadPreset("video-480-mp4", "480p MP4", "video", "bestvideo[height<=480]+bestaudio/best[height<=480]", "mp4"),
    DownloadPreset("audio-mp3-320", "MP3 320 kbps", "audio", "bestaudio/best", audio_format="mp3", audio_quality="320K"),
    DownloadPreset("audio-mp3-256", "MP3 256 kbps", "audio", "bestaudio/best", audio_format="mp3", audio_quality="256K"),
    DownloadPreset("audio-mp3-192", "MP3 192 kbps", "audio", "bestaudio/best", audio_format="mp3", audio_quality="192K"),
    DownloadPreset("audio-mp3-128", "MP3 128 kbps", "audio", "bestaudio/best", audio_format="mp3", audio_quality="128K"),
    DownloadPreset("audio-m4a", "M4A en iyi kalite", "audio", "bestaudio[ext=m4a]/bestaudio/best", audio_format="m4a", audio_quality="0"),
    DownloadPreset("audio-opus", "Opus en iyi kalite", "audio", "bestaudio[acodec=opus]/bestaudio/best", audio_format="opus", audio_quality="0"),
    DownloadPreset("custom", "Gelişmiş / özel format", "custom", ""),
)
PRESET_BY_ID = {preset.id: preset for preset in PRESETS}


@dataclass
class PlaylistEntry:
    key: str
    url: str
    title: str
    channel: str = ""
    duration: float = 0
    thumbnail: str = ""
    selected: bool = True
    playlist_index: int = 0

    @classmethod
    def from_info(cls, info: dict[str, Any], index: int) -> "PlaylistEntry":
        url = str(info.get("webpage_url") or info.get("url") or "")
        video_id = str(info.get("id") or "")
        extractor = str(info.get("ie_key") or info.get("extractor_key") or "").lower()
        if not url.startswith(("http://", "https://")) and video_id:
            if "youtube" in extractor or len(video_id) == 11:
                url = f"https://www.youtube.com/watch?v={video_id}"
        return cls(
            key=video_id or url or f"entry-{index}",
            url=url,
            title=str(info.get("title") or f"Video {index}"),
            channel=str(info.get("uploader") or info.get("channel") or ""),
            duration=float(info.get("duration") or 0),
            thumbnail=str(info.get("thumbnail") or ""),
            playlist_index=index,
        )


@dataclass
class DownloadJob:
    url: str
    title: str
    preset_id: str
    id: str = field(default_factory=lambda: str(uuid4()))
    batch_id: str = field(default_factory=lambda: str(uuid4()))
    custom_format: str = ""
    channel: str = ""
    duration: float = 0
    thumbnail: str = ""
    playlist_title: str = ""
    playlist_index: int = 0
    status: str = DownloadStatus.PENDING.value
    progress: float = 0
    speed: str = ""
    eta: str = ""
    size: str = ""
    error: str = ""
    output_path: str = ""
    added_at: str = field(default_factory=now_iso)
    completed_at: str = ""
    force_overwrite: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "DownloadJob":
        data = dict(raw)
        data["status"] = LEGACY_STATUS_MAP.get(str(data.get("status", "")), data.get("status", DownloadStatus.PENDING.value))
        if data["status"] in (DownloadStatus.DOWNLOADING.value, DownloadStatus.PAUSED.value):
            data["status"] = DownloadStatus.PENDING.value
            data["progress"] = 0
        data["output_path"] = str(data.pop("filepath", data.get("output_path", "")))
        data["preset_id"] = str(data.get("preset_id") or _legacy_preset(data.get("format", "")))
        data.pop("format", None)
        data["id"] = str(data.get("id") or uuid4())
        data["batch_id"] = str(data.get("batch_id") or uuid4())
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in data.items() if key in allowed})


def _legacy_preset(format_selector: str) -> str:
    text = str(format_selector)
    if text == "bestaudio/best":
        return "audio-mp3-192"
    for preset in PRESETS:
        if preset.format_selector == text:
            return preset.id
    return "video-best-mp4"


@dataclass
class DownloadEvent:
    kind: str
    job_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=now_iso)


@dataclass
class HistoryEntry:
    title: str
    url: str
    output_path: str
    preset_id: str
    channel: str = ""
    duration: float = 0
    completed_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def kind(self) -> str:
        preset = PRESET_BY_ID.get(self.preset_id)
        return "audio" if preset and preset.kind == "audio" else "video"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "HistoryEntry":
        data = dict(raw)
        data["output_path"] = str(data.pop("filepath", data.get("output_path", "")))
        data["preset_id"] = str(data.get("preset_id") or "video-best-mp4")
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in data.items() if key in allowed})
