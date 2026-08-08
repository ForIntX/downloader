import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:video_indirici/data/database.dart';
import 'package:video_indirici/models/download_models.dart';

void main() {
  late AppDatabase database;

  setUp(() {
    sqfliteFfiInit();
    database = AppDatabase(
      factory: databaseFactoryFfi,
      pathOverride: inMemoryDatabasePath,
    );
  });

  tearDown(() => database.close());

  test('kuyruk ve ayarlar SQLite içinde kalıcıdır', () async {
    final job = DownloadJob(
      id: '1',
      url: 'https://example.com/1',
      title: 'Bir',
      presetId: 'video-720',
      createdAt: DateTime.utc(2026),
      position: 2,
      sourceId: 'video-id',
      customFormat: 'best[height<=720]',
      speedLimit: '1M',
      concurrentFragments: 6,
      filenameTemplate: '%(title)s-%(id)s.%(ext)s',
      cookieMode: 'file',
      cookieFile: r'C:\cookies.txt',
    );
    await database.saveJob(job);
    await database.setSetting('wifi_only', 'true');
    final jobs = await database.loadJobs();
    expect(jobs.single.title, 'Bir');
    expect(jobs.single.position, 2);
    expect(jobs.single.sourceId, 'video-id');
    expect(jobs.single.customFormat, 'best[height<=720]');
    expect(jobs.single.speedLimit, '1M');
    expect(jobs.single.concurrentFragments, 6);
    expect(jobs.single.filenameTemplate, '%(title)s-%(id)s.%(ext)s');
    expect(jobs.single.cookieMode, 'file');
    expect(jobs.single.cookieFile, r'C:\cookies.txt');
    expect(await database.getSetting('wifi_only'), 'true');
  });

  test('sürüm 1 veritabanı gelişmiş iş ayarlarına taşınır', () async {
    final directory = await Directory.systemTemp.createTemp('video-db-v1-');
    final path = '${directory.path}/legacy.sqlite';
    final legacy = await databaseFactoryFfi.openDatabase(
      path,
      options: OpenDatabaseOptions(
        version: 1,
        onCreate: (db, version) async {
          await db.execute('''
            CREATE TABLE jobs (
              id TEXT PRIMARY KEY,
              url TEXT NOT NULL,
              title TEXT NOT NULL,
              preset_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT,
              status TEXT NOT NULL,
              progress REAL NOT NULL DEFAULT 0,
              speed TEXT,
              eta_seconds INTEGER,
              output_path TEXT,
              thumbnail_url TEXT,
              error TEXT,
              position INTEGER NOT NULL DEFAULT 0
            )
          ''');
          await db.execute(
            'CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)',
          );
        },
      ),
    );
    await legacy.insert('jobs', {
      'id': 'legacy',
      'url': 'https://example.com/legacy',
      'title': 'Eski iş',
      'preset_id': 'video-best',
      'created_at': DateTime.utc(2026).toIso8601String(),
      'status': 'pending',
      'progress': 0,
      'position': 0,
    });
    await legacy.close();

    final migrated = AppDatabase(
      factory: databaseFactoryFfi,
      pathOverride: path,
    );
    final job = (await migrated.loadJobs()).single;
    expect(job.customFormat, isEmpty);
    expect(job.concurrentFragments, 4);
    expect(job.cookieMode, 'none');
    expect(job.filenameTemplate, contains('%(title)'));
    await migrated.close();
    await directory.delete(recursive: true);
  });
}
