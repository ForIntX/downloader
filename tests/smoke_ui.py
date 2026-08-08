#!/usr/bin/env python3
"""Open the real GTK window with isolated XDG data and close it automatically."""

import os
import sys
import tempfile
import traceback
import wave
from base64 import b64decode
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


with tempfile.TemporaryDirectory(prefix="video-indirici-ui-") as directory:
    os.environ["XDG_CONFIG_HOME"] = os.path.join(directory, "config")
    os.environ["XDG_DATA_HOME"] = os.path.join(directory, "data")
    os.environ["XDG_STATE_HOME"] = os.path.join(directory, "state")
    os.environ["XDG_CACHE_HOME"] = os.path.join(directory, "cache")

    from gi.repository import GLib
    from video_indirici.models import DownloadJob, HistoryEntry, PlaylistEntry
    from video_indirici.player import MediaItem
    from video_indirici.ui import SettingsWindow, VideoIndiriciApplication
    from video_indirici.ui_models import HistoryObject, JobObject, PlaylistObject

    application = VideoIndiriciApplication()
    failures = []

    def close_window():
        if application.props.active_window:
            application.props.active_window.close()
        return False

    def populate():
        window = application.props.active_window
        if window is None:
            return True
        window.config["clipboard"] = False
        window.video_mode.set_active(True)
        started = GLib.get_monotonic_time()
        for index in range(2000):
            window.playlist_store.append(PlaylistObject(PlaylistEntry(
                str(index),
                f"https://example.com/{index}",
                "Çok uzun playlist başlığı " * 5,
                playlist_index=index + 1,
            )))
        assert GLib.get_monotonic_time() - started < 500_000
        queue_started = GLib.get_monotonic_time()
        for index in range(2000):
            window.queue_store.append(JobObject(DownloadJob(
                url=f"https://example.com/queue/{index}",
                title="Çok uzun kuyruk başlığı " * 5,
                preset_id="video-best-mp4",
            )))
        assert GLib.get_monotonic_time() - queue_started < 500_000
        window._render_video_info({
            "id": "abcdefghijk",
            "title": "Tek Video Bilgi Kartı",
            "uploader": "Test Kanalı",
            "duration": 125,
            "view_count": 1234567,
            "upload_date": "20260808",
            "width": 1920,
            "height": 1080,
            "extractor_key": "Youtube",
            "description": "Video açıklaması\n" * 120,
        })
        assert window.video_title_label.get_label() == "Tek Video Bilgi Kartı"
        assert "1.234.567" in window.video_properties_label.get_label()
        assert window.download_content_stack.get_visible_child_name() == "video"
        assert not window.video_description_revealer.get_reveal_child()
        window.video_description_toggle.set_active(True)
        assert window.video_description_revealer.get_reveal_child()
        window._thumbnail_token = "smoke-thumbnail"
        png = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        window._apply_video_thumbnail("smoke-thumbnail", png)
        assert window.video_thumbnail_stack.get_visible_child_name() == "thumbnail"
        window.history_store.append(HistoryObject(HistoryEntry("Video geçmişi " * 5, "https://example.com/1", "/tmp/missing.mp4", "video-best-mp4")))
        window.history_store.append(HistoryObject(HistoryEntry("Müzik geçmişi " * 5, "https://example.com/2", "/tmp/missing.mp3", "audio-mp3-192")))
        window.history_filter_buttons["audio"].set_active(True)
        assert window.history_filtered.get_n_items() == 1
        window.history_filter_buttons["video"].set_active(True)
        assert window.history_filtered.get_n_items() == 1
        window.history_filter_buttons["all"].set_active(True)
        assert window.history_filtered.get_n_items() == 2
        audio_path = Path(directory) / "silent.wav"
        with wave.open(str(audio_path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b"\0\0" * 800)
        second_audio_path = Path(directory) / "silent-2.wav"
        with wave.open(str(second_audio_path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b"\0\0" * 800)
        playlist = [
            MediaItem(audio_path, "Birinci parça", "audio"),
            MediaItem(second_audio_path, "İkinci parça", "audio"),
        ]
        window._open_internal_player(audio_path, "Birinci parça", playlist)
        assert len(window._player_windows) == 1
        player = window._player_windows[-1]
        assert player.index == 0
        assert player.current_item.title == "Birinci parça"
        assert not player.previous_button.get_sensitive()
        assert player.next_button.get_sensitive()
        player.next()
        assert player.index == 1
        assert player.current_item.title == "İkinci parça"
        assert player.previous_button.get_sensitive()
        assert not player.next_button.get_sensitive()
        player.previous()
        player.volume_scale.set_value(0.4)
        assert round(player.stream.get_volume(), 1) == 0.4
        player.toggle_mute()
        assert player.volume_scale.get_value() == 0
        player.toggle_mute()
        assert round(player.volume_scale.get_value(), 1) == 0.4
        player.close()
        assert not window._player_windows
        window.present()
        settings = SettingsWindow(window, window.config, lambda _config: None)
        settings.close()
        GLib.timeout_add(500, verify_video_scroll)
        return False

    def verify_video_scroll():
        try:
            window = application.props.active_window
            assert window is not None
            adjustment = window.video_info_scroll.get_vadjustment()
            assert adjustment.get_upper() > adjustment.get_page_size()
            window.video_description_toggle.set_active(False)
            assert not window.video_description_revealer.get_reveal_child()
            window.playlist_mode.set_active(True)
            GLib.timeout_add(500, verify_virtualization)
        except Exception:
            failures.append(traceback.format_exc())
            GLib.timeout_add(200, close_window)
        return False

    def verify_virtualization():
        try:
            window = application.props.active_window
            assert window is not None
            assert window.playlist_store.get_n_items() == 2000
            realized_rows = window.playlist_view.observe_children().get_n_items()
            assert 0 < realized_rows < 500, f"gerçekleştirilen satır: {realized_rows}"
            window.tab_buttons["queue"].set_active(True)
            GLib.timeout_add(500, verify_queue_virtualization)
        except Exception:
            failures.append(traceback.format_exc())
            GLib.timeout_add(200, close_window)
        return False

    def verify_queue_virtualization():
        try:
            window = application.props.active_window
            assert window is not None
            assert window.queue_store.get_n_items() == 2000
            realized_rows = window.queue_view.observe_children().get_n_items()
            assert 0 < realized_rows < 500, f"gerçekleştirilen kuyruk satırı: {realized_rows}"
            original_has_active = window.engine.has_active
            window.engine.has_active = lambda: True
            assert window._on_close_request() is True
            window.engine.has_active = original_has_active
            for child_window in application.get_windows():
                if child_window is not window:
                    child_window.close()
        except Exception:
            failures.append(traceback.format_exc())
        finally:
            GLib.timeout_add(200, close_window)
        return False

    application.connect("activate", lambda *_args: GLib.idle_add(populate))
    result = application.run(["video-indirici-smoke"])
    if failures:
        raise AssertionError("\n".join(failures))
    raise SystemExit(result)
