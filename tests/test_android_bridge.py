import importlib.util
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
BRIDGE_PATH = ROOT / "clients/video_indirici_flutter/android/app/src/main/python/downloader_bridge.py"


def load_bridge():
    yt_dlp = types.ModuleType("yt_dlp")
    utils = types.ModuleType("yt_dlp.utils")
    utils.DownloadCancelled = type("DownloadCancelled", (Exception,), {})
    with patch.dict(sys.modules, {"yt_dlp": yt_dlp, "yt_dlp.utils": utils}):
        spec = importlib.util.spec_from_file_location("android_downloader_bridge_test", BRIDGE_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module


class AndroidBridgeTests(unittest.TestCase):
    def test_rate_limit_units(self):
        bridge = load_bridge()
        self.assertEqual(bridge._rate_limit_bytes("256K"), 256 * 1024)
        self.assertEqual(bridge._rate_limit_bytes("2M"), 2 * 1024 * 1024)
        self.assertIsNone(bridge._rate_limit_bytes(""))

    def test_custom_video_audio_selector_is_split_for_native_ffmpeg(self):
        bridge = load_bridge()
        calls = []

        def component(_url, selector, output, _callback, start, size, rate, fragments):
            calls.append((selector, output, start, size, rate, fragments))
            return {
                "path": f"/tmp/{len(calls)}.bin",
                "has_audio": len(calls) == 2,
                "has_video": len(calls) == 1,
            }

        with TemporaryDirectory() as directory, patch.object(
            bridge, "_download_component", side_effect=component
        ):
            result = bridge.download_job(
                {
                    "id": "job-1",
                    "url": "https://example.com/video",
                    "preset_id": "custom",
                    "custom_format": "137+140",
                    "speed_limit": "2M",
                    "concurrent_fragments": 7,
                },
                directory,
                object(),
            )

        self.assertEqual(result["kind"], "video")
        self.assertEqual(result["extension"], "mp4")
        self.assertEqual([call[0] for call in calls], ["137", "140"])
        self.assertTrue(all(call[4] == 2 * 1024 * 1024 for call in calls))
        self.assertTrue(all(call[5] == 7 for call in calls))


if __name__ == "__main__":
    unittest.main()
