import unittest

from video_indirici.models import DownloadJob, DownloadStatus, HistoryEntry, PlaylistEntry, PRESET_BY_ID


class ModelTests(unittest.TestCase):
    def test_legacy_queue_job_migrates(self):
        job = DownloadJob.from_dict({
            "id": 7,
            "url": "https://youtube.com/watch?v=abcdefghijk",
            "title": "Eski",
            "format": "bestaudio/best",
            "status": "indiriliyor",
            "filepath": "/tmp/old.mp3",
        })
        self.assertEqual(job.id, "7")
        self.assertEqual(job.status, DownloadStatus.PENDING.value)
        self.assertEqual(job.preset_id, "audio-mp3-192")
        self.assertEqual(job.output_path, "/tmp/old.mp3")

    def test_playlist_entry_normalizes_youtube_id(self):
        entry = PlaylistEntry.from_info({"id": "abcdefghijk", "url": "abcdefghijk", "title": "X", "ie_key": "Youtube"}, 1)
        self.assertEqual(entry.url, "https://www.youtube.com/watch?v=abcdefghijk")

    def test_required_presets_exist(self):
        for preset_id in (
            "video-best-mp4", "video-2160-mp4", "video-1440-mp4", "video-1080-mp4",
            "video-720-mp4", "video-480-mp4", "audio-mp3-320", "audio-mp3-256",
            "audio-mp3-192", "audio-mp3-128", "audio-m4a", "audio-opus", "custom",
        ):
            self.assertIn(preset_id, PRESET_BY_ID)

    def test_history_entries_are_categorized_from_their_preset(self):
        audio = HistoryEntry("Song", "https://example.com/a", "/tmp/a.mp3", "audio-mp3-192")
        video = HistoryEntry("Video", "https://example.com/v", "/tmp/v.mp4", "video-1080-mp4")
        self.assertEqual(audio.kind, "audio")
        self.assertEqual(video.kind, "video")


if __name__ == "__main__":
    unittest.main()
