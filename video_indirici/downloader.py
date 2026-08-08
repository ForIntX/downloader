from __future__ import annotations

import copy
import json
import os
import re
import signal
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .constants import OUTPUT_MARKER, SUB_LANG_MAP
from .models import (
    PRESET_BY_ID,
    DownloadEvent,
    DownloadJob,
    DownloadStatus,
    PlaylistEntry,
    now_iso,
)
from .persistence import LOGGER
from .utils import parse_speed_limit, redact_command, safe_folder_name

EventCallback = Callable[[DownloadEvent], None]


def cookie_arguments(config: dict[str, Any]) -> list[str]:
    mode = str(config.get("cookie_mode", "none"))
    if mode == "browser":
        browser = str(config.get("cookie_browser", "firefox"))
        profile = str(config.get("cookie_profile", "")).strip()
        value = f"{browser}:{profile}" if profile else browser
        return ["--cookies-from-browser", value]
    if mode == "file":
        cookie_file = Path(str(config.get("cookie_file", ""))).expanduser()
        if not cookie_file.is_file():
            raise ValueError("Seçilen cookies.txt dosyası bulunamadı")
        return ["--cookies", str(cookie_file)]
    return []


def build_download_command(
    job: DownloadJob,
    config: dict[str, Any],
    ytdlp_executable: str = "yt-dlp",
) -> tuple[list[str], Path]:
    preset = PRESET_BY_ID.get(job.preset_id)
    if preset is None:
        raise ValueError(f"Bilinmeyen indirme preseti: {job.preset_id}")

    output_dir = Path(str(config.get("folder", ""))).expanduser()
    if job.playlist_title and config.get("playlist_folder", True):
        output_dir /= safe_folder_name(job.playlist_title)

    filename_template = str(config.get("filename_template", "%(title)s.%(ext)s"))
    if job.playlist_title and job.playlist_index:
        filename_template = str(
            config.get("playlist_filename_template", "%(playlist_index)03d - %(title)s.%(ext)s")
        )
        filename_template = filename_template.replace(
            "%(playlist_index)03d", f"{job.playlist_index:03d}"
        ).replace("%(playlist_index)s", str(job.playlist_index))

    format_selector = job.custom_format.strip() if preset.kind == "custom" else preset.format_selector
    if not format_selector:
        raise ValueError("Gelişmiş format alanı boş bırakılamaz")

    command = [
        ytdlp_executable,
        "-f",
        format_selector,
        "-o",
        str(output_dir / filename_template),
        "--newline",
        "--progress",
        "--no-colors",
        "--no-warnings",
        "--progress-template",
        "download:__VIDEO_INDIRICI_PROGRESS__%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s|%(progress._total_bytes_str)s",
        "--print",
        f"after_move:{OUTPUT_MARKER}%(filepath)s",
        "--concurrent-fragments",
        str(config.get("concurrent_fragments", 4)),
    ]

    command.extend(["--force-overwrites"] if job.force_overwrite else ["--no-overwrites", "--continue"])
    rate = parse_speed_limit(str(config.get("speed_limit", "Sınırsız")))
    if rate:
        command.extend(["--limit-rate", rate])

    if preset.kind == "audio":
        command.extend(["--extract-audio", "--audio-format", preset.audio_format])
        if preset.audio_quality:
            command.extend(["--audio-quality", preset.audio_quality])
    elif preset.merge_container:
        command.extend(["--merge-output-format", preset.merge_container])

    if config.get("download_subs", False) and preset.kind != "audio":
        language = SUB_LANG_MAP.get(str(config.get("sub_lang", "Türkçe")), "tr")
        command.extend(["--write-subs", "--sub-langs", language])
        if config.get("sub_auto", False):
            command.append("--write-auto-subs")
        if config.get("embed_subs", False):
            command.append("--embed-subs")

    if config.get("download_thumbnail", True):
        command.append("--write-thumbnail")
    if config.get("embed_metadata", True):
        command.append("--embed-metadata")
    if config.get("keep_chapters", True) and preset.kind != "audio":
        command.append("--embed-chapters")

    command.extend(cookie_arguments(config))
    command.append(job.url)
    return command, output_dir


def parse_progress_line(line: str) -> dict[str, Any] | None:
    marker = "__VIDEO_INDIRICI_PROGRESS__"
    if marker not in line:
        return None
    value = line.split(marker, 1)[1].strip()
    parts = value.split("|", 3)
    while len(parts) < 4:
        parts.append("")
    percent_text, speed, eta, total = (part.strip() for part in parts)
    match = re.search(r"([\d.]+)%", percent_text)
    return {
        "progress": min(100.0, float(match.group(1))) if match else 0.0,
        "speed": "" if speed in ("NA", "Unknown") else speed,
        "eta": "" if eta in ("NA", "Unknown") else eta,
        "size": "" if total in ("NA", "Unknown") else total,
    }


class MetadataScanner:
    def __init__(
        self,
        event_callback: EventCallback,
        config_provider: Callable[[], dict[str, Any]],
        ytdlp_executable: str = "yt-dlp",
    ) -> None:
        self._emit = event_callback
        self._config_provider = config_provider
        self._ytdlp = ytdlp_executable
        self._token = ""
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    @property
    def active(self) -> bool:
        with self._lock:
            return bool(self._process and self._process.poll() is None)

    def start(self, url: str, playlist: bool) -> str:
        self.cancel()
        token = str(uuid4())
        self._token = token
        target = self._scan_playlist if playlist else self._scan_video
        threading.Thread(target=target, args=(url, token), daemon=True, name="metadata").start()
        self._emit(DownloadEvent("metadata_started", payload={"token": token, "playlist": playlist}))
        return token

    def cancel(self) -> None:
        self._token = ""
        with self._lock:
            process = self._process
        if process and process.poll() is None:
            threading.Thread(
                target=self._terminate_process,
                args=(process,),
                daemon=True,
                name="metadata-cancel",
            ).start()

    @staticmethod
    def _terminate_process(process: subprocess.Popen[str]) -> None:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                LOGGER.exception("Metadata süreci zorla kapatılamadı")
        except OSError:
            LOGGER.exception("Metadata süreci sonlandırılamadı")

    def _scan_video(self, url: str, token: str) -> None:
        process: subprocess.Popen[str] | None = None
        try:
            command = [self._ytdlp, "--dump-single-json", "--no-playlist", "--no-warnings"]
            command.extend(cookie_arguments(self._config_provider()))
            command.append(url)
            LOGGER.info("Metadata komutu: %s", redact_command(command))
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                stdin=subprocess.DEVNULL,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                preexec_fn=os.setsid,
            )
            with self._lock:
                self._process = process
            stdout, stderr = process.communicate(timeout=120)
            if token != self._token:
                return
            if process.returncode:
                raise RuntimeError((stderr or "Video bilgisi alınamadı")[-500:])
            info = json.loads(stdout)
            self._emit(DownloadEvent("metadata_video", payload={"token": token, "info": info}))
        except subprocess.TimeoutExpired:
            if process:
                process.kill()
                process.communicate()
            if token == self._token:
                self._emit(DownloadEvent("metadata_error", payload={"token": token, "error": "Video bilgisi zaman aşımına uğradı"}))
        except Exception as exc:
            if token == self._token:
                LOGGER.exception("Video metadata hatası")
                self._emit(DownloadEvent("metadata_error", payload={"token": token, "error": str(exc)}))
        finally:
            with self._lock:
                if self._process is process:
                    self._process = None
            if token == self._token:
                self._emit(DownloadEvent("metadata_finished", payload={"token": token}))

    def _scan_playlist(self, url: str, token: str) -> None:
        command = [
            self._ytdlp,
            "--flat-playlist",
            "--lazy-playlist",
            "--dump-json",
            "--ignore-errors",
            "--no-warnings",
        ]
        process: subprocess.Popen[str] | None = None
        try:
            command.extend(cookie_arguments(self._config_provider()))
            command.append(url)
            LOGGER.info("Playlist komutu: %s", redact_command(command))
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
                preexec_fn=os.setsid,
            )
            with self._lock:
                self._process = process
            batch: list[PlaylistEntry] = []
            title = "Oynatma Listesi"
            uploader = ""
            errors: deque[str] = deque(maxlen=10)
            count = 0
            assert process.stdout is not None
            with process.stdout:
                for line in process.stdout:
                    if token != self._token:
                        return
                    try:
                        info = json.loads(line)
                    except json.JSONDecodeError:
                        if line.strip():
                            errors.append(line.strip())
                        continue
                    count += 1
                    entry = PlaylistEntry.from_info(info, count)
                    if not entry.url:
                        continue
                    title = str(info.get("playlist_title") or info.get("playlist") or title)
                    uploader = str(info.get("playlist_uploader") or uploader)
                    batch.append(entry)
                    if len(batch) == 25:
                        self._emit(
                            DownloadEvent(
                                "metadata_entries",
                                payload={"token": token, "entries": batch, "title": title, "uploader": uploader},
                            )
                        )
                        batch = []
            returncode = process.wait()
            if batch and token == self._token:
                self._emit(
                    DownloadEvent(
                        "metadata_entries",
                        payload={"token": token, "entries": batch, "title": title, "uploader": uploader},
                    )
                )
            if token == self._token and returncode and not count:
                raise RuntimeError("\n".join(errors) or "Playlist bilgisi alınamadı")
        except Exception as exc:
            if token == self._token:
                LOGGER.exception("Playlist metadata hatası")
                self._emit(DownloadEvent("metadata_error", payload={"token": token, "error": str(exc)}))
        finally:
            with self._lock:
                if self._process is process:
                    self._process = None
            if token == self._token:
                self._emit(DownloadEvent("metadata_finished", payload={"token": token}))


class DownloadEngine:
    def __init__(
        self,
        event_callback: EventCallback,
        config_provider: Callable[[], dict[str, Any]],
        ytdlp_executable: str = "yt-dlp",
    ) -> None:
        self._emit = event_callback
        self._config_provider = config_provider
        self._ytdlp = ytdlp_executable
        self._jobs: list[DownloadJob] = []
        self._running_ids: set[str] = set()
        self._processes: dict[str, subprocess.Popen[str]] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._notified_batches: set[str] = set()
        self._lock = threading.RLock()
        self._shutting_down = False

    def set_jobs(self, jobs: list[DownloadJob]) -> None:
        with self._lock:
            self._jobs = jobs

    def snapshot(self) -> list[DownloadJob]:
        with self._lock:
            return copy.deepcopy(self._jobs)

    def active_count(self) -> int:
        with self._lock:
            return len(self._running_ids)

    def has_active(self) -> bool:
        return self.active_count() > 0

    def find_duplicate(self, url: str) -> DownloadJob | None:
        normalized = url.strip().rstrip("/")
        with self._lock:
            return next((job for job in self._jobs if job.url.strip().rstrip("/") == normalized and job.status != DownloadStatus.CANCELLED.value), None)

    def add_jobs(self, jobs: list[DownloadJob], start: bool = True) -> None:
        with self._lock:
            self._jobs.extend(jobs)
        self._emit(DownloadEvent("jobs_added", payload={"jobs": jobs}))
        self._emit(DownloadEvent("queue_changed"))
        if start:
            self.start_available()

    def start_available(self) -> None:
        to_start: list[DownloadJob] = []
        with self._lock:
            if self._shutting_down:
                return
            maximum = max(1, int(self._config_provider().get("parallel", 3)))
            available = max(0, maximum - len(self._running_ids))
            for job in self._jobs:
                if available <= 0:
                    break
                if job.status == DownloadStatus.PENDING.value and job.id not in self._running_ids:
                    job.status = DownloadStatus.DOWNLOADING.value
                    job.error = ""
                    job.progress = 0
                    self._running_ids.add(job.id)
                    to_start.append(job)
                    available -= 1
        for job in to_start:
            self._emit(DownloadEvent("job_updated", job.id, {"job": job}))
            thread = threading.Thread(target=self._download_worker, args=(job,), daemon=True, name=f"download-{job.id[:8]}")
            with self._lock:
                self._threads[job.id] = thread
            thread.start()

    def pause(self, job_id: str) -> None:
        with self._lock:
            job = self._find_locked(job_id)
            process = self._processes.get(job_id)
            if not job or not process or process.poll() is not None:
                return
            if job.status == DownloadStatus.DOWNLOADING.value:
                os.killpg(os.getpgid(process.pid), signal.SIGSTOP)
                job.status = DownloadStatus.PAUSED.value
            elif job.status == DownloadStatus.PAUSED.value:
                os.killpg(os.getpgid(process.pid), signal.SIGCONT)
                job.status = DownloadStatus.DOWNLOADING.value
            else:
                return
        self._emit(DownloadEvent("job_updated", job_id, {"job": job}))

    def cancel(self, job_id: str) -> None:
        with self._lock:
            job = self._find_locked(job_id)
            if not job or job.status in (DownloadStatus.COMPLETED.value, DownloadStatus.CANCELLED.value):
                return
            job.status = DownloadStatus.CANCELLED.value
            process = self._processes.get(job_id)
            is_running = job_id in self._running_ids
        self._emit(DownloadEvent("job_updated", job_id, {"job": job}))
        if process and process.poll() is None:
            threading.Thread(target=self._terminate_process, args=(process,), daemon=True).start()
        elif not is_running:
            self.start_available()

    def retry(self, job_id: str, force_overwrite: bool = False) -> None:
        with self._lock:
            job = self._find_locked(job_id)
            if not job or job_id in self._running_ids:
                return
            job.status = DownloadStatus.PENDING.value
            job.progress = 0
            job.speed = job.eta = job.size = job.error = job.output_path = ""
            job.force_overwrite = force_overwrite
            self._notified_batches.discard(job.batch_id)
        self._emit(DownloadEvent("job_updated", job_id, {"job": job}))
        self.start_available()

    def remove(self, job_id: str) -> None:
        self.cancel(job_id)
        with self._lock:
            self._jobs = [job for job in self._jobs if job.id != job_id]
        self._emit(DownloadEvent("job_removed", job_id))
        self._emit(DownloadEvent("queue_changed"))

    def clear_finished(self) -> None:
        removable = {DownloadStatus.COMPLETED.value, DownloadStatus.CANCELLED.value}
        with self._lock:
            self._jobs = [job for job in self._jobs if job.status not in removable]
            jobs = self.snapshot()
        self._emit(DownloadEvent("order_changed", payload={"jobs": jobs}))

    def clear_all(self) -> None:
        with self._lock:
            for job in self._jobs:
                if job.status not in (DownloadStatus.COMPLETED.value, DownloadStatus.CANCELLED.value):
                    job.status = DownloadStatus.CANCELLED.value
            processes = [process for process in self._processes.values() if process.poll() is None]
            self._jobs.clear()
        self._emit(DownloadEvent("order_changed", payload={"jobs": []}))
        for process in processes:
            threading.Thread(target=self._terminate_process, args=(process,), daemon=True).start()

    def move(self, job_id: str, direction: int) -> bool:
        with self._lock:
            index = next((i for i, job in enumerate(self._jobs) if job.id == job_id), -1)
            if index < 0 or self._jobs[index].status != DownloadStatus.PENDING.value:
                return False
            target = index + direction
            while 0 <= target < len(self._jobs) and self._jobs[target].status != DownloadStatus.PENDING.value:
                target += direction
            if target < 0 or target >= len(self._jobs):
                return False
            self._jobs[index], self._jobs[target] = self._jobs[target], self._jobs[index]
        self._emit(DownloadEvent("order_changed", payload={"jobs": self.snapshot()}))
        return True

    def move_before(self, source_id: str, target_id: str) -> bool:
        with self._lock:
            source = self._find_locked(source_id)
            target = self._find_locked(target_id)
            if not source or not target or source.status != DownloadStatus.PENDING.value or target.status != DownloadStatus.PENDING.value:
                return False
            self._jobs.remove(source)
            self._jobs.insert(self._jobs.index(target), source)
        self._emit(DownloadEvent("order_changed", payload={"jobs": self.snapshot()}))
        return True

    def shutdown(self, timeout: float = 5.0) -> None:
        with self._lock:
            self._shutting_down = True
            ids = list(self._running_ids)
        for job_id in ids:
            self.cancel(job_id)
        deadline = time.monotonic() + timeout
        for thread in list(self._threads.values()):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            thread.join(remaining)

    def _download_worker(self, job: DownloadJob) -> None:
        output_tail: deque[str] = deque(maxlen=25)
        output_path = ""
        last_progress_emit = 0.0
        try:
            with self._lock:
                if job.status == DownloadStatus.CANCELLED.value:
                    return
            config = self._config_provider()
            command, output_dir = build_download_command(job, config, self._ytdlp)
            output_dir.mkdir(parents=True, exist_ok=True)
            LOGGER.info("İndirme komutu: %s", redact_command(command))
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
                preexec_fn=os.setsid,
            )
            with self._lock:
                self._processes[job.id] = process
                cancelled_before_launch = job.status == DownloadStatus.CANCELLED.value
            if cancelled_before_launch:
                self._terminate_process(process)
            assert process.stdout is not None
            with process.stdout:
                for raw_line in process.stdout:
                    line = raw_line.strip()
                    if line:
                        output_tail.append(line)
                    if line.startswith(OUTPUT_MARKER):
                        output_path = line[len(OUTPUT_MARKER):].strip()
                        continue
                    progress = parse_progress_line(line)
                    now = time.monotonic()
                    if progress and (now - last_progress_emit >= 0.2 or progress["progress"] >= 100):
                        with self._lock:
                            job.progress = progress["progress"]
                            job.speed = progress["speed"]
                            job.eta = progress["eta"]
                            job.size = progress["size"]
                        self._emit(DownloadEvent("job_progress", job.id, progress))
                        last_progress_emit = now
            returncode = process.wait(timeout=10)
            with self._lock:
                if job.status == DownloadStatus.CANCELLED.value:
                    return
                if returncode == 0:
                    if not output_path:
                        job.status = DownloadStatus.ERROR.value
                        job.error = "yt-dlp tamamlandı ancak kesin çıktı yolunu döndürmedi"
                    else:
                        job.status = DownloadStatus.COMPLETED.value
                        job.progress = 100
                        job.speed = job.eta = ""
                        job.output_path = output_path
                        job.completed_at = now_iso()
                else:
                    job.status = DownloadStatus.ERROR.value
                    job.error = "\n".join(output_tail)[-1000:] or f"yt-dlp çıkış kodu: {returncode}"
        except Exception as exc:
            with self._lock:
                if job.status != DownloadStatus.CANCELLED.value:
                    job.status = DownloadStatus.ERROR.value
                    job.error = str(exc)[:1000]
            LOGGER.exception("İndirme başarısız: %s", job.url)
        finally:
            with self._lock:
                self._processes.pop(job.id, None)
                self._running_ids.discard(job.id)
                self._threads.pop(job.id, None)
            self._emit(DownloadEvent("job_updated", job.id, {"job": job}))
            self._emit_batch_if_finished(job.batch_id)
            self.start_available()
            if not self.has_active():
                self._emit(DownloadEvent("engine_idle"))

    def _emit_batch_if_finished(self, batch_id: str) -> None:
        with self._lock:
            if batch_id in self._notified_batches:
                return
            jobs = [job for job in self._jobs if job.batch_id == batch_id]
            unfinished = {DownloadStatus.PENDING.value, DownloadStatus.DOWNLOADING.value, DownloadStatus.PAUSED.value}
            if not jobs or any(job.status in unfinished for job in jobs):
                return
            self._notified_batches.add(batch_id)
            completed = sum(job.status == DownloadStatus.COMPLETED.value for job in jobs)
            failed = sum(
                job.status in (DownloadStatus.ERROR.value, DownloadStatus.CANCELLED.value)
                for job in jobs
            )
            folders = sorted({str(Path(job.output_path).parent) for job in jobs if job.output_path})
        self._emit(
            DownloadEvent(
                "batch_finished",
                payload={"batch_id": batch_id, "completed": completed, "failed": failed, "folders": folders},
            )
        )

    def _terminate_process(self, process: subprocess.Popen[str]) -> None:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGCONT)
        except OSError:
            pass
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait(timeout=3)
            except OSError:
                LOGGER.exception("İndirme süreci zorla kapatılamadı")
            except subprocess.TimeoutExpired:
                LOGGER.error("İndirme süreci SIGKILL sonrasında kapanmadı: %s", process.pid)
        except OSError:
            LOGGER.exception("İndirme süreci kapatılamadı")

    def _find_locked(self, job_id: str) -> DownloadJob | None:
        return next((job for job in self._jobs if job.id == job_id), None)
