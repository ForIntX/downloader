import 'package:flutter_test/flutter_test.dart';
import 'package:video_indirici/models/download_models.dart';
import 'package:video_indirici/services/background_audio.dart';

void main() {
  test('yalnız tamamlanmış ses dosyaları oynatma kuyruğuna girer', () {
    final now = DateTime(2026);
    final items = audioItemsFromJobs([
      DownloadJob(
        id: 'audio-ready',
        url: 'https://example.com/1',
        title: 'Hazır müzik',
        presetId: 'audio-256',
        createdAt: now,
        status: DownloadStatus.completed,
        outputPath: 'content://media/audio/1',
      ),
      DownloadJob(
        id: 'video-ready',
        url: 'https://example.com/2',
        title: 'Video',
        presetId: 'video-best',
        createdAt: now,
        status: DownloadStatus.completed,
        outputPath: 'content://media/video/2',
      ),
      DownloadJob(
        id: 'audio-failed',
        url: 'https://example.com/3',
        title: 'Hatalı müzik',
        presetId: 'audio-192',
        createdAt: now,
        status: DownloadStatus.failed,
      ),
    ]);

    expect(items, hasLength(1));
    expect(items.single.id, 'audio-ready');
    expect(items.single.extras!['uri'], 'content://media/audio/1');
  });
}
