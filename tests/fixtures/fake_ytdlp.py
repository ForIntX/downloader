#!/usr/bin/env python3
import json
import os
import signal
import sys
import time
from pathlib import Path


cancelled = False


def stop(_signum, _frame):
    global cancelled
    if os.environ.get("FAKE_IGNORE_TERM") == "1":
        return
    cancelled = True


signal.signal(signal.SIGTERM, stop)

if "--dump-single-json" in sys.argv:
    print(json.dumps({"id": "abcdefghijk", "title": "Test Video", "webpage_url": "https://youtube.com/watch?v=abcdefghijk", "duration": 42}))
    raise SystemExit(0)

if "--flat-playlist" in sys.argv:
    count = int(os.environ.get("FAKE_PLAYLIST_COUNT", "25"))
    for index in range(count):
        print(json.dumps({
            "id": f"id{index:09d}"[-11:],
            "title": f"Video {index}",
            "url": f"https://example.com/video/{index}",
            "playlist_title": "Fixture Playlist",
            "playlist_uploader": "Fixture",
        }), flush=True)
    raise SystemExit(0)

delay = float(os.environ.get("FAKE_DOWNLOAD_DELAY", "0"))
for percent in range(0, 101, 10):
    if cancelled:
        raise SystemExit(143)
    print(f"__VIDEO_INDIRICI_PROGRESS__{percent:.1f}%|1.0MiB/s|00:01|10.0MiB", flush=True)
    if delay:
        time.sleep(delay)

output = Path(os.environ.get("FAKE_OUTPUT", "/tmp/video-indirici-fake.mp4"))
output.parent.mkdir(parents=True, exist_ok=True)
output.write_bytes(b"fixture")
if os.environ.get("FAKE_FAIL") == "1":
    print("fixture download error", flush=True)
    raise SystemExit(2)
if os.environ.get("FAKE_NO_OUTPUT_MARKER") != "1":
    print(f"__VIDEO_INDIRICI_FILE__{output}", flush=True)
