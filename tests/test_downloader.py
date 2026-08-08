import os
import tempfile
import time
import unittest
from pathlib import Path

from video_indirici.downloader import (
    DownloadEngine,
    MetadataScanner,
    build_download_command,
    cookie_arguments,
    parse_progress_line,
)
from video_indirici.models import DownloadJob, DownloadStatus


FIXTURE = str(Path(__file__).parent / "fixtures/fake_ytdlp.py")


def base_config(folder: str):
    return {
        "folder": folder,
        "parallel": "1",
        "concurrent_fragments": 4,
        "speed_limit": "Sınırsız",
        "filename_template": "%(title)s.%(ext)s",
        "playlist_filename_template": "%(playlist_index)03d - %(title)s.%(ext)s",
        "playlist_folder": True,
        "download_subs": False,
        "download_thumbnail": False,
        "embed_metadata": False,
        "keep_chapters": False,
        "cookie_mode": "none",
    }


class CommandTests(unittest.TestCase):
    def test_mp3_is_real_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            job = DownloadJob(url="https://example.com", title="Audio", preset_id="audio-mp3-320")
            command, _ = build_download_command(job, base_config(directory))
            self.assertIn("--extract-audio", command)
            self.assertEqual(command[command.index("--audio-format") + 1], "mp3")
            self.assertEqual(command[command.index("--audio-quality") + 1], "320K")

    def test_video_merge_and_custom_format(self):
        with tempfile.TemporaryDirectory() as directory:
            video = DownloadJob(url="https://example.com", title="Video", preset_id="video-1080-mp4")
            command, _ = build_download_command(video, base_config(directory))
            self.assertEqual(command[command.index("--merge-output-format") + 1], "mp4")
            custom = DownloadJob(url="https://example.com", title="Custom", preset_id="custom", custom_format="137+140")
            command, _ = build_download_command(custom, base_config(directory))
            self.assertEqual(command[command.index("-f") + 1], "137+140")

    def test_cookie_modes(self):
        self.assertEqual(cookie_arguments({"cookie_mode": "browser", "cookie_browser": "firefox", "cookie_profile": "work"}), ["--cookies-from-browser", "firefox:work"])
        with tempfile.NamedTemporaryFile() as cookie:
            self.assertEqual(cookie_arguments({"cookie_mode": "file", "cookie_file": cookie.name}), ["--cookies", cookie.name])

    def test_progress_parser(self):
        parsed = parse_progress_line("__VIDEO_INDIRICI_PROGRESS__42.5%|2MiB/s|00:09|20MiB")
        self.assertEqual(parsed["progress"], 42.5)
        self.assertEqual(parsed["eta"], "00:09")


class EngineIntegrationTests(unittest.TestCase):
    def test_fake_download_reports_exact_output_and_throttles_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "actual-result.mp4"
            old_output = os.environ.get("FAKE_OUTPUT")
            os.environ["FAKE_OUTPUT"] = str(output)
            events = []
            config = base_config(directory)
            engine = DownloadEngine(events.append, lambda: config, FIXTURE)
            job = DownloadJob(url="https://example.com/video", title="Test", preset_id="video-best-mp4")
            try:
                engine.add_jobs([job])
                deadline = time.monotonic() + 5
                while job.status in (DownloadStatus.PENDING.value, DownloadStatus.DOWNLOADING.value) and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertEqual(job.status, DownloadStatus.COMPLETED.value)
                self.assertEqual(job.output_path, str(output))
                progress_events = [event for event in events if event.kind == "job_progress"]
                self.assertLessEqual(len(progress_events), 3)
            finally:
                engine.shutdown()
                if old_output is None:
                    os.environ.pop("FAKE_OUTPUT", None)
                else:
                    os.environ["FAKE_OUTPUT"] = old_output

    def test_cancel_reaps_before_next_slot_completes(self):
        with tempfile.TemporaryDirectory() as directory:
            old_delay = os.environ.get("FAKE_DOWNLOAD_DELAY")
            os.environ["FAKE_DOWNLOAD_DELAY"] = "0.1"
            config = base_config(directory)
            engine = DownloadEngine(lambda _event: None, lambda: config, FIXTURE)
            first = DownloadJob(url="https://example.com/1", title="One", preset_id="video-best-mp4")
            second = DownloadJob(url="https://example.com/2", title="Two", preset_id="video-best-mp4")
            try:
                engine.add_jobs([first, second])
                time.sleep(0.1)
                engine.cancel(first.id)
                deadline = time.monotonic() + 6
                while second.status != DownloadStatus.COMPLETED.value and time.monotonic() < deadline:
                    time.sleep(0.03)
                self.assertEqual(first.status, DownloadStatus.CANCELLED.value)
                self.assertEqual(second.status, DownloadStatus.COMPLETED.value)
            finally:
                engine.shutdown()
                if old_delay is None:
                    os.environ.pop("FAKE_DOWNLOAD_DELAY", None)
                else:
                    os.environ["FAKE_DOWNLOAD_DELAY"] = old_delay

    def test_sigkill_fallback_reaps_stubborn_process(self):
        with tempfile.TemporaryDirectory() as directory:
            old_delay = os.environ.get("FAKE_DOWNLOAD_DELAY")
            old_ignore = os.environ.get("FAKE_IGNORE_TERM")
            os.environ["FAKE_DOWNLOAD_DELAY"] = "1"
            os.environ["FAKE_IGNORE_TERM"] = "1"
            job = DownloadJob(url="https://example.com/stubborn", title="Stubborn", preset_id="video-best-mp4")
            engine = DownloadEngine(lambda _event: None, lambda: base_config(directory), FIXTURE)
            try:
                engine.add_jobs([job])
                deadline = time.monotonic() + 2
                while job.progress == 0 and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertGreater(job.progress, 0)
                engine.cancel(job.id)
                deadline = time.monotonic() + 6
                while engine.active_count() and time.monotonic() < deadline:
                    time.sleep(0.03)
                self.assertEqual(job.status, DownloadStatus.CANCELLED.value)
                self.assertEqual(engine.active_count(), 0)
            finally:
                engine.shutdown()
                if old_delay is None:
                    os.environ.pop("FAKE_DOWNLOAD_DELAY", None)
                else:
                    os.environ["FAKE_DOWNLOAD_DELAY"] = old_delay
                if old_ignore is None:
                    os.environ.pop("FAKE_IGNORE_TERM", None)
                else:
                    os.environ["FAKE_IGNORE_TERM"] = old_ignore

    def test_missing_exact_path_is_an_error_and_retry_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            old_missing = os.environ.get("FAKE_NO_OUTPUT_MARKER")
            os.environ["FAKE_NO_OUTPUT_MARKER"] = "1"
            job = DownloadJob(url="https://example.com/retry", title="Retry", preset_id="video-best-mp4")
            engine = DownloadEngine(lambda _event: None, lambda: base_config(directory), FIXTURE)
            try:
                engine.add_jobs([job])
                deadline = time.monotonic() + 4
                while job.status in (DownloadStatus.PENDING.value, DownloadStatus.DOWNLOADING.value) and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertEqual(job.status, DownloadStatus.ERROR.value)
                os.environ.pop("FAKE_NO_OUTPUT_MARKER", None)
                engine.retry(job.id, force_overwrite=True)
                deadline = time.monotonic() + 4
                while job.status in (DownloadStatus.PENDING.value, DownloadStatus.DOWNLOADING.value) and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertEqual(job.status, DownloadStatus.COMPLETED.value)
                self.assertTrue(job.output_path)
            finally:
                engine.shutdown()
                if old_missing is None:
                    os.environ.pop("FAKE_NO_OUTPUT_MARKER", None)
                else:
                    os.environ["FAKE_NO_OUTPUT_MARKER"] = old_missing

    def test_reorder_duplicate_and_bulk_clear(self):
        events = []
        with tempfile.TemporaryDirectory() as directory:
            engine = DownloadEngine(events.append, lambda: base_config(directory), FIXTURE)
            jobs = [DownloadJob(url=f"https://example.com/{index}", title=str(index), preset_id="video-best-mp4") for index in range(2000)]
            try:
                engine.add_jobs(jobs, start=False)
                self.assertIsNotNone(engine.find_duplicate("https://example.com/1/"))
                self.assertTrue(engine.move(jobs[1].id, -1))
                self.assertEqual(engine.snapshot()[0].id, jobs[1].id)
                events.clear()
                started = time.monotonic()
                engine.clear_all()
                self.assertLess(time.monotonic() - started, 0.25)
                self.assertEqual(engine.snapshot(), [])
                order_events = [event for event in events if event.kind == "order_changed"]
                self.assertEqual(len(order_events), 1)
            finally:
                engine.shutdown()


class MetadataPerformanceTests(unittest.TestCase):
    def test_2000_entries_are_streamed_in_bounded_batches(self):
        events = []
        first_batch_at = []
        config = {"cookie_mode": "none"}
        def receive(event):
            events.append(event)
            if event.kind == "metadata_entries" and not first_batch_at:
                first_batch_at.append(time.monotonic())

        scanner = MetadataScanner(receive, lambda: config, FIXTURE)
        old_count = os.environ.get("FAKE_PLAYLIST_COUNT")
        os.environ["FAKE_PLAYLIST_COUNT"] = "2000"
        started = time.monotonic()
        try:
            scanner.start("https://example.com/playlist", True)
            deadline = time.monotonic() + 8
            while not any(event.kind == "metadata_finished" for event in events) and time.monotonic() < deadline:
                time.sleep(0.01)
            batches = [event for event in events if event.kind == "metadata_entries"]
            self.assertEqual(sum(len(event.payload["entries"]) for event in batches), 2000)
            self.assertTrue(all(len(event.payload["entries"]) <= 25 for event in batches))
            self.assertTrue(first_batch_at)
            self.assertLess(first_batch_at[0] - started, 0.5)
            self.assertLess(time.monotonic() - started, 8)
        finally:
            scanner.cancel()
            if old_count is None:
                os.environ.pop("FAKE_PLAYLIST_COUNT", None)
            else:
                os.environ["FAKE_PLAYLIST_COUNT"] = old_count


if __name__ == "__main__":
    unittest.main()
