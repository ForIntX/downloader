import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:video_indirici/data/database.dart';
import 'package:video_indirici/engine/download_engine.dart';
import 'package:video_indirici/models/download_models.dart';
import 'package:video_indirici/providers/app_controller.dart';

class FakeEngine implements DownloadEngine {
  final controller = StreamController<DownloadEvent>.broadcast();
  final started = <DownloadJob>[];
  bool wifiOnly = false;
  bool chargingOnly = false;
  String cookieMode = 'none';
  String localeCode = 'tr';
  int videoInfoRequests = 0;
  String? openedLocation;

  @override
  Stream<DownloadEvent> get events => controller.stream;
  @override
  Future<void> configure({
    required bool wifiOnly,
    required bool chargingOnly,
    String cookieMode = 'none',
    String cookieBrowser = 'firefox',
    String cookieProfile = '',
    String cookieFile = '',
    String localeCode = 'tr',
  }) async {
    this.wifiOnly = wifiOnly;
    this.chargingOnly = chargingOnly;
    this.cookieMode = cookieMode;
    this.localeCode = localeCode;
  }

  @override
  Future<VideoMetadata> getVideoInfo(String url) async {
    videoInfoRequests++;
    return VideoMetadata(id: 'v1', url: url, title: 'Video');
  }

  @override
  Stream<PlaylistEntry> scanPlaylist(String url) => Stream.fromIterable(
    List.generate(
      2000,
      (index) => PlaylistEntry(
        id: '$index',
        url: '$url/$index',
        title: 'Video $index',
      ),
    ),
  );
  @override
  Future<void> start(DownloadJob job) async => started.add(job);
  @override
  Future<void> pause(String jobId) async {}
  @override
  Future<void> resume(DownloadJob job) async {}
  @override
  Future<void> cancel(String jobId, {bool deletePartial = false}) async {}
  @override
  Future<bool> outputExists(String path) async => true;
  @override
  Future<void> openOutput(String path) async {}
  @override
  Future<void> openOutputLocation(String path) async {
    openedLocation = path;
  }

  @override
  Future<void> shareOutput(String path) async {}
  @override
  Future<Map<String, String>> downloadLocations() async => const {
    'video': 'Download/video_indirici/videos',
    'audio': 'Download/video_indirici/musics',
  };
  @override
  Future<void> openDownloadLocation(String kind) async {}
  @override
  Future<Map<String, Object?>> diagnostics() async => {};
  @override
  Future<void> dispose() => controller.close();
}

void main() {
  late FakeEngine engine;
  late AppDatabase database;
  late AppController controller;

  setUp(() async {
    sqfliteFfiInit();
    engine = FakeEngine();
    database = AppDatabase(
      factory: databaseFactoryFfi,
      pathOverride: inMemoryDatabasePath,
    );
    controller = AppController(database: database, engine: engine);
    await controller.initialize();
  });

  tearDown(() => controller.dispose());

  test('aynı URL ikinci kez kuyruğa eklenmez', () async {
    await controller.getInformation('https://example.com/v', playlist: false);
    final first = await controller.enqueueCurrent();
    final second = await controller.enqueueCurrent();
    expect(first.added, 1);
    expect(second.skipped, 1);
    expect(controller.state.jobs, hasLength(1));
  });

  test('Wi-Fi ve şarj koşulları motora aktarılır', () async {
    await controller.setWifiOnly(true);
    await controller.setChargingOnly(true);
    expect(engine.wifiOnly, isTrue);
    expect(engine.chargingOnly, isTrue);
    expect(await database.getSetting('wifi_only'), 'true');
    expect(await database.getSetting('charging_only'), 'true');
  });

  test('İngilizce dil tercihi kalıcıdır ve motora aktarılır', () async {
    await controller.setLocale('en');
    expect(controller.state.localeCode, 'en');
    expect(engine.localeCode, 'en');
    expect(await database.getSetting('locale'), 'en');
  });

  test('gelişmiş indirme ayarları işe sabitlenir', () async {
    await controller.setPreset('custom');
    await controller.setCustomFormat('137+140');
    await controller.setSpeedLimit('2M');
    await controller.setConcurrentFragments(7);
    await controller.setFilenameTemplate('%(title)s-%(id)s.%(ext)s');
    await controller.setCookieMode('browser');
    await controller.setCookieBrowser('edge');
    await controller.setCookieProfile('Default');
    await controller.getInformation(
      'https://www.youtube.com/watch?v=video-id',
      playlist: false,
    );

    final result = await controller.enqueueCurrent();
    await Future<void>.delayed(const Duration(milliseconds: 20));

    expect(result.added, 1);
    final job = engine.started.single;
    expect(job.sourceId, 'v1');
    expect(job.customFormat, '137+140');
    expect(job.speedLimit, '2M');
    expect(job.concurrentFragments, 7);
    expect(job.filenameTemplate, '%(title)s-%(id)s.%(ext)s');
    expect(job.cookieMode, 'browser');
    expect(job.cookieBrowser, 'edge');
    expect(job.cookieProfile, 'Default');
    expect(engine.cookieMode, 'browser');
  });

  test('aynı videonun bilgisi ikinci istekte önbellekten gelir', () async {
    await controller.getInformation(
      'https://youtu.be/video-id',
      playlist: false,
    );
    await controller.getInformation(
      'https://www.youtube.com/watch?v=video-id',
      playlist: false,
    );
    expect(engine.videoInfoRequests, 1);
  });

  test('tamamlanan URL kullanıcı onayıyla yeniden kuyruğa eklenir', () async {
    await controller.getInformation(
      'https://youtu.be/video-id',
      playlist: false,
    );
    await controller.enqueueCurrent();
    await Future<void>.delayed(Duration.zero);
    final firstJob = controller.state.jobs.single;
    engine.controller.add(
      DownloadEvent(
        jobId: firstJob.id,
        status: DownloadStatus.completed,
        progress: 100,
        outputPath: 'content://media/1',
      ),
    );
    await Future<void>.delayed(const Duration(milliseconds: 20));

    final duplicate = await controller.enqueueCurrent();
    expect(duplicate.redownloadable, 1);
    final repeated = await controller.enqueueCurrent(
      redownloadDuplicates: true,
    );
    expect(repeated.added, 1);
    expect(controller.state.jobs, hasLength(2));
  });

  test(
    'motor olayı kesin dosya yolunu ve tamamlanma durumunu kaydeder',
    () async {
      await controller.getInformation('https://example.com/v', playlist: false);
      await controller.enqueueCurrent();
      await Future<void>.delayed(Duration.zero);
      final job = controller.state.jobs.single;
      engine.controller.add(
        DownloadEvent(
          jobId: job.id,
          status: DownloadStatus.completed,
          progress: 100,
          outputPath: 'content://media/1',
        ),
      );
      await Future<void>.delayed(const Duration(milliseconds: 20));
      expect(controller.state.jobs.single.status, DownloadStatus.completed);
      expect(controller.state.jobs.single.outputPath, 'content://media/1');
      expect(
        await controller.openOutputLocation(controller.state.jobs.single),
        isTrue,
      );
      expect(engine.openedLocation, 'content://media/1');
    },
  );

  test('müzik geçmişi temizlenirken video ve kuyruk korunur', () async {
    await controller.getInformation(
      'https://example.com/video',
      playlist: false,
    );
    await controller.enqueueCurrent();
    await Future<void>.delayed(Duration.zero);
    final video = controller.state.jobs.single;
    engine.controller.add(
      DownloadEvent(
        jobId: video.id,
        status: DownloadStatus.completed,
        outputPath: 'content://media/video/1',
      ),
    );
    await Future<void>.delayed(const Duration(milliseconds: 20));

    await controller.setPreset('audio-256');
    await controller.getInformation(
      'https://example.com/audio',
      playlist: false,
    );
    await controller.enqueueCurrent();
    await Future<void>.delayed(Duration.zero);
    final audio = controller.state.jobs.firstWhere((job) => job.id != video.id);
    engine.controller.add(
      DownloadEvent(
        jobId: audio.id,
        status: DownloadStatus.completed,
        outputPath: 'content://media/audio/1',
      ),
    );
    await Future<void>.delayed(const Duration(milliseconds: 20));

    await controller.getInformation(
      'https://example.com/pending',
      playlist: false,
    );
    await controller.enqueueCurrent();
    await Future<void>.delayed(Duration.zero);
    final pending = controller.state.jobs.firstWhere(
      (job) => job.id != video.id && job.id != audio.id,
    );

    expect(await controller.clearHistory(kind: MediaKind.audio), 1);
    expect(
      controller.state.jobs.map((job) => job.id),
      containsAll([video.id, pending.id]),
    );
    expect(
      controller.state.jobs.map((job) => job.id),
      isNot(contains(audio.id)),
    );
    expect(
      (await database.loadJobs()).map((job) => job.id),
      isNot(contains(audio.id)),
    );
  });
}
