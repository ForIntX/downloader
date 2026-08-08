import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:video_indirici/data/database.dart';
import 'package:video_indirici/engine/download_engine.dart';
import 'package:video_indirici/models/download_models.dart';
import 'package:video_indirici/providers/app_controller.dart';
import 'package:video_indirici/screens/home_screen.dart';

class PlaylistEngine implements DownloadEngine {
  final _events = StreamController<DownloadEvent>.broadcast();

  @override
  Stream<DownloadEvent> get events => _events.stream;
  @override
  Future<void> configure({
    required bool wifiOnly,
    required bool chargingOnly,
    String cookieMode = 'none',
    String cookieBrowser = 'firefox',
    String cookieProfile = '',
    String cookieFile = '',
  }) async {}
  @override
  Future<VideoMetadata> getVideoInfo(String url) => throw UnimplementedError();
  @override
  Stream<PlaylistEntry> scanPlaylist(String url) => Stream.fromIterable(
    List.generate(
      2000,
      (index) => PlaylistEntry(
        id: '$index',
        url: '$url/$index',
        title: 'Playlist videosu $index',
      ),
    ),
  );

  @override
  Future<void> start(DownloadJob job) async {}
  @override
  Future<void> pause(String jobId) async {}
  @override
  Future<void> resume(DownloadJob job) async {}
  @override
  Future<void> cancel(String jobId, {bool deletePartial = false}) async {}
  @override
  Future<bool> outputExists(String path) async => false;
  @override
  Future<void> openOutput(String path) async {}
  @override
  Future<void> openOutputLocation(String path) async {}
  @override
  Future<void> shareOutput(String path) async {}
  @override
  Future<Map<String, String>> downloadLocations() async => const {};
  @override
  Future<void> openDownloadLocation(String kind) async {}
  @override
  Future<Map<String, Object?>> diagnostics() async => {};
  @override
  Future<void> dispose() => _events.close();
}

class SeededController extends AppController {
  SeededController({required super.database, required super.engine});

  void seedPlaylist(List<PlaylistEntry> entries) {
    state = state.copyWith(
      initialized: true,
      playlist: entries,
      scanning: false,
    );
  }
}

void main() {
  testWidgets(
    '2000 girdide ilk sonuç hızlı gelir ve yalnız görünür satırlar oluşur',
    (tester) async {
      sqfliteFfiInit();
      final engine = PlaylistEngine();
      final controller = SeededController(
        database: AppDatabase(
          factory: databaseFactoryFfi,
          pathOverride: inMemoryDatabasePath,
        ),
        engine: engine,
      );
      await tester.runAsync(controller.initialize);
      final stopwatch = Stopwatch()..start();
      final first = await tester.runAsync(
        () => engine.scanPlaylist('https://example.com/list').first,
      );
      expect(first, isNotNull);
      expect(first!.id, '0');
      expect(stopwatch.elapsedMilliseconds, lessThan(500));
      controller.seedPlaylist(
        List.generate(
          2000,
          (index) => PlaylistEntry(
            id: '$index',
            url: 'https://example.com/list/$index',
            title: 'Playlist videosu $index',
          ),
        ),
      );
      expect(controller.state.playlist, hasLength(2000));

      await tester.pumpWidget(
        ProviderScope(
          overrides: [appControllerProvider.overrideWith((ref) => controller)],
          child: const MaterialApp(home: Scaffold(body: HomeScreen())),
        ),
      );
      await tester.pump();
      await tester.drag(find.byType(CustomScrollView), const Offset(0, -650));
      await tester.pump();
      final builtRows = find.byType(CheckboxListTile).evaluate().length;
      expect(builtRows, greaterThan(0));
      expect(builtRows, lessThan(50));
      await tester.pumpWidget(const SizedBox.shrink());
    },
  );
}
