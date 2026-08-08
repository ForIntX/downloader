from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from .constants import (
    CONFIG_DIR,
    CONFIG_FILE,
    DATA_DIR,
    DEFAULT_CONFIG,
    HISTORY_FILE,
    LEGACY_CONFIG_FILE,
    LOG_FILE,
    QUEUE_FILE,
    SCHEMA_VERSION,
    STATE_DIR,
)
from .models import DownloadJob, HistoryEntry


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("video_indirici")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(
            LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
    except OSError:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return logger


LOGGER = configure_logging()


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _backup_corrupt(path: Path) -> None:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.corrupt-{stamp}")
    try:
        path.replace(backup)
        LOGGER.error("Bozuk JSON yedeklendi: %s", backup)
    except OSError:
        LOGGER.exception("Bozuk JSON yedeklenemedi: %s", path)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        LOGGER.exception("JSON okunamadı: %s", path)
        _backup_corrupt(path)
        return copy.deepcopy(default)


class PersistenceManager:
    """Versioned storage with ordered, atomic background writes."""

    def __init__(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="storage")
        self._lock = threading.Lock()
        self._futures: list[Future] = []

    def load_config(self) -> dict[str, Any]:
        if not CONFIG_FILE.exists() and LEGACY_CONFIG_FILE.exists():
            legacy = load_json(LEGACY_CONFIG_FILE, {})
            config = self._migrate_config(legacy)
            atomic_write_json(CONFIG_FILE, config)
            LOGGER.info("1.x ayarları XDG config dizinine taşındı")
            return config
        raw = load_json(CONFIG_FILE, {})
        config = self._migrate_config(raw)
        if raw != config:
            atomic_write_json(CONFIG_FILE, config)
        return config

    def load_queue(self) -> list[DownloadJob]:
        raw = load_json(QUEUE_FILE, {"schema_version": SCHEMA_VERSION, "items": []})
        items = raw if isinstance(raw, list) else raw.get("items", []) if isinstance(raw, dict) else []
        result: list[DownloadJob] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                result.append(DownloadJob.from_dict(item))
            except (TypeError, ValueError):
                LOGGER.exception("Kuyruk girdisi taşınamadı")
        migrated = {"schema_version": SCHEMA_VERSION, "items": [job.to_dict() for job in result]}
        if raw != migrated:
            atomic_write_json(QUEUE_FILE, migrated)
        return result

    def load_history(self) -> list[HistoryEntry]:
        raw = load_json(HISTORY_FILE, {"schema_version": SCHEMA_VERSION, "items": []})
        items = raw if isinstance(raw, list) else raw.get("items", []) if isinstance(raw, dict) else []
        result: list[HistoryEntry] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                result.append(HistoryEntry.from_dict(item))
            except (TypeError, ValueError):
                LOGGER.exception("Geçmiş girdisi taşınamadı")
        result = result[:500]
        migrated = {"schema_version": SCHEMA_VERSION, "items": [entry.to_dict() for entry in result]}
        if raw != migrated:
            atomic_write_json(HISTORY_FILE, migrated)
        return result

    def save_config(self, config: dict[str, Any], asynchronous: bool = True) -> None:
        value = {**DEFAULT_CONFIG, **copy.deepcopy(config)}
        value["schema_version"] = SCHEMA_VERSION
        self._write(CONFIG_FILE, value, asynchronous)

    def save_queue(self, jobs: list[DownloadJob], asynchronous: bool = True) -> None:
        value = {"schema_version": SCHEMA_VERSION, "items": [job.to_dict() for job in jobs]}
        self._write(QUEUE_FILE, value, asynchronous)

    def save_history(self, entries: list[HistoryEntry], asynchronous: bool = True) -> None:
        value = {"schema_version": SCHEMA_VERSION, "items": [entry.to_dict() for entry in entries[:500]]}
        self._write(HISTORY_FILE, value, asynchronous)

    def flush(self) -> None:
        with self._lock:
            futures = list(self._futures)
            self._futures.clear()
        for future in futures:
            try:
                future.result(timeout=10)
            except Exception:
                LOGGER.exception("Veri yazma işi tamamlanamadı")

    def close(self) -> None:
        self.flush()
        self._executor.shutdown(wait=True, cancel_futures=False)

    def _write(self, path: Path, value: Any, asynchronous: bool) -> None:
        if not asynchronous:
            atomic_write_json(path, value)
            return
        future = self._executor.submit(atomic_write_json, path, value)
        future.add_done_callback(self._write_finished)
        with self._lock:
            self._futures = [item for item in self._futures if not item.done()]
            self._futures.append(future)

    @staticmethod
    def _write_finished(future: Future) -> None:
        try:
            future.result()
        except Exception:
            LOGGER.exception("Atomik veri yazma işi başarısız")

    @staticmethod
    def _migrate_config(raw: Any) -> dict[str, Any]:
        config = dict(raw) if isinstance(raw, dict) else {}
        migrated = {**DEFAULT_CONFIG, **config}
        if "format" in config and "default_preset" not in config:
            from .models import _legacy_preset

            migrated["default_preset"] = _legacy_preset(str(config["format"]))
        migrated.pop("format", None)
        migrated["schema_version"] = SCHEMA_VERSION
        return migrated
