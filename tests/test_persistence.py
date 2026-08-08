import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_indirici.models import DownloadJob, HistoryEntry
from video_indirici.persistence import PersistenceManager, atomic_write_json, load_json


class PersistenceTests(unittest.TestCase):
    def test_atomic_json_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            atomic_write_json(path, {"schema_version": 2, "items": ["ğ"]})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["items"], ["ğ"])
            self.assertFalse(list(path.parent.glob("*.tmp")))

    def test_corrupt_json_is_backed_up(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(load_json(path, {"ok": True}), {"ok": True})
            self.assertFalse(path.exists())
            self.assertEqual(len(list(path.parent.glob("state.json.corrupt-*"))), 1)

    def test_manager_writes_schema_v2(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("video_indirici.persistence.CONFIG_DIR", root / "config"), \
                 patch("video_indirici.persistence.DATA_DIR", root / "data"), \
                 patch("video_indirici.persistence.STATE_DIR", root / "state"), \
                 patch("video_indirici.persistence.CONFIG_FILE", root / "config/config.json"), \
                 patch("video_indirici.persistence.QUEUE_FILE", root / "data/queue.json"), \
                 patch("video_indirici.persistence.HISTORY_FILE", root / "data/history.json"), \
                 patch("video_indirici.persistence.LEGACY_CONFIG_FILE", root / "legacy/config.json"):
                manager = PersistenceManager()
                manager.save_config({"parallel": "2"}, asynchronous=False)
                manager.save_queue([DownloadJob(url="https://example.com", title="T", preset_id="video-best-mp4")], asynchronous=False)
                manager.save_history([HistoryEntry("T", "https://example.com", "/tmp/t.mp4", "video-best-mp4")], asynchronous=False)
                self.assertEqual(manager.load_config()["schema_version"], 2)
                self.assertEqual(len(manager.load_queue()), 1)
                self.assertEqual(len(manager.load_history()), 1)
                manager.close()

    def test_legacy_files_migrate_and_async_close_flushes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy_dir = root / "data"
            legacy_dir.mkdir(parents=True)
            (legacy_dir / "config.json").write_text(
                json.dumps({"format": "bestaudio/best", "parallel": "2"}), encoding="utf-8"
            )
            (legacy_dir / "queue.json").write_text(json.dumps([{
                "id": 1,
                "url": "https://example.com/old",
                "title": "Eski",
                "format": "bestaudio/best",
                "status": "indiriliyor",
                "filepath": "/tmp/old.mp3",
            }]), encoding="utf-8")
            (legacy_dir / "history.json").write_text(json.dumps([{
                "title": "Eski",
                "url": "https://example.com/old",
                "filepath": "/tmp/old.mp3",
            }]), encoding="utf-8")
            with patch("video_indirici.persistence.CONFIG_DIR", root / "config"), \
                 patch("video_indirici.persistence.DATA_DIR", legacy_dir), \
                 patch("video_indirici.persistence.STATE_DIR", root / "state"), \
                 patch("video_indirici.persistence.CONFIG_FILE", root / "config/config.json"), \
                 patch("video_indirici.persistence.QUEUE_FILE", legacy_dir / "queue.json"), \
                 patch("video_indirici.persistence.HISTORY_FILE", legacy_dir / "history.json"), \
                 patch("video_indirici.persistence.LEGACY_CONFIG_FILE", legacy_dir / "config.json"):
                manager = PersistenceManager()
                config = manager.load_config()
                jobs = manager.load_queue()
                history = manager.load_history()
                self.assertEqual(config["default_preset"], "audio-mp3-192")
                self.assertEqual(jobs[0].status, "pending")
                self.assertEqual(history[0].output_path, "/tmp/old.mp3")
                manager.save_config({**config, "parallel": "4"})
                manager.close()
                self.assertEqual(json.loads((root / "config/config.json").read_text())["parallel"], "4")
                self.assertEqual(json.loads((legacy_dir / "queue.json").read_text())["schema_version"], 2)
                self.assertEqual(json.loads((legacy_dir / "history.json").read_text())["schema_version"], 2)


if __name__ == "__main__":
    unittest.main()
