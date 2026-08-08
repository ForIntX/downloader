import 'package:flutter_test/flutter_test.dart';
import 'package:video_indirici/models/download_models.dart';

void main() {
  test('preset kataloğu tüm planlanan MP3 ve MP4 kalitelerini içerir', () {
    final ids = DownloadPreset.presets.map((preset) => preset.id).toSet();
    expect(
      ids,
      containsAll(<String>{
        'video-best',
        'video-2160',
        'video-1440',
        'video-1080',
        'video-720',
        'video-480',
        'audio-128',
        'audio-192',
        'audio-256',
        'audio-320',
        'audio-m4a',
        'audio-opus',
        'custom',
      }),
    );
  });

  test('DownloadJob JSON dönüşümü durum ve kesin yolu korur', () {
    final original = DownloadJob(
      id: 'job-1',
      url: 'https://example.com/video',
      title: 'Uzun başlık',
      presetId: 'audio-320',
      createdAt: DateTime.utc(2026, 8, 8),
      updatedAt: DateTime.utc(2026, 8, 8, 1),
      status: DownloadStatus.completed,
      progress: 100,
      outputPath: 'content://media/audio/1',
      position: 4,
      sourceId: 'source-1',
      customFormat: '137+140',
      speedLimit: '2M',
      concurrentFragments: 8,
      filenameTemplate: '%(title)s-%(id)s.%(ext)s',
      cookieMode: 'browser',
      cookieBrowser: 'edge',
      cookieProfile: 'Default',
    );
    final restored = DownloadJob.fromJson(original.toJson());
    expect(restored.status, DownloadStatus.completed);
    expect(restored.outputPath, original.outputPath);
    expect(restored.preset.audioBitrate, 320);
    expect(restored.position, 4);
    expect(restored.sourceId, 'source-1');
    expect(restored.customFormat, '137+140');
    expect(restored.speedLimit, '2M');
    expect(restored.concurrentFragments, 8);
    expect(restored.filenameTemplate, '%(title)s-%(id)s.%(ext)s');
    expect(restored.cookieMode, 'browser');
    expect(restored.cookieBrowser, 'edge');
    expect(restored.cookieProfile, 'Default');
  });
}
