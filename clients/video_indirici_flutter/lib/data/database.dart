import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import '../models/download_models.dart';

class AppDatabase {
  AppDatabase({DatabaseFactory? factory, this._pathOverride})
    : _factoryOverride = factory;

  final DatabaseFactory? _factoryOverride;
  final String? _pathOverride;
  Database? _database;

  Future<Database> get database async => _database ??= await _open();

  Future<Database> _open() async {
    final factory = _factoryOverride ?? _platformFactory();
    final String path;
    if (_pathOverride != null) {
      path = _pathOverride;
    } else {
      final Directory support = await getApplicationSupportDirectory();
      await support.create(recursive: true);
      path = p.join(support.path, 'video_indirici_v3.sqlite');
    }
    return factory.openDatabase(
      path,
      options: OpenDatabaseOptions(
        version: 2,
        onConfigure: (db) => db.execute('PRAGMA foreign_keys = ON'),
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
              position INTEGER NOT NULL DEFAULT 0,
              source_id TEXT NOT NULL DEFAULT '',
              custom_format TEXT NOT NULL DEFAULT '',
              speed_limit TEXT NOT NULL DEFAULT '',
              concurrent_fragments INTEGER NOT NULL DEFAULT 4,
              filename_template TEXT NOT NULL DEFAULT '%(title).180B [%(id)s].%(ext)s',
              cookie_mode TEXT NOT NULL DEFAULT 'none',
              cookie_browser TEXT NOT NULL DEFAULT 'firefox',
              cookie_profile TEXT NOT NULL DEFAULT '',
              cookie_file TEXT NOT NULL DEFAULT ''
            )
          ''');
          await db.execute(
            'CREATE INDEX jobs_status_position ON jobs(status, position)',
          );
          await db.execute('CREATE INDEX jobs_url ON jobs(url)');
          await db.execute('''
            CREATE TABLE settings (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            )
          ''');
        },
        onUpgrade: (db, oldVersion, newVersion) async {
          if (oldVersion < 2) {
            await db.execute(
              "ALTER TABLE jobs ADD COLUMN source_id TEXT NOT NULL DEFAULT ''",
            );
            await db.execute(
              "ALTER TABLE jobs ADD COLUMN custom_format TEXT NOT NULL DEFAULT ''",
            );
            await db.execute(
              "ALTER TABLE jobs ADD COLUMN speed_limit TEXT NOT NULL DEFAULT ''",
            );
            await db.execute(
              'ALTER TABLE jobs ADD COLUMN concurrent_fragments INTEGER NOT NULL DEFAULT 4',
            );
            await db.execute(
              "ALTER TABLE jobs ADD COLUMN filename_template TEXT NOT NULL DEFAULT '%(title).180B [%(id)s].%(ext)s'",
            );
            await db.execute(
              "ALTER TABLE jobs ADD COLUMN cookie_mode TEXT NOT NULL DEFAULT 'none'",
            );
            await db.execute(
              "ALTER TABLE jobs ADD COLUMN cookie_browser TEXT NOT NULL DEFAULT 'firefox'",
            );
            await db.execute(
              "ALTER TABLE jobs ADD COLUMN cookie_profile TEXT NOT NULL DEFAULT ''",
            );
            await db.execute(
              "ALTER TABLE jobs ADD COLUMN cookie_file TEXT NOT NULL DEFAULT ''",
            );
          }
        },
      ),
    );
  }

  DatabaseFactory _platformFactory() {
    if (Platform.isWindows || Platform.isLinux) {
      sqfliteFfiInit();
      return databaseFactoryFfi;
    }
    return databaseFactory;
  }

  Future<List<DownloadJob>> loadJobs() async {
    final db = await database;
    final rows = await db.query(
      'jobs',
      orderBy: 'position ASC, created_at ASC',
    );
    return rows.map(DownloadJob.fromJson).toList(growable: false);
  }

  Future<void> saveJob(DownloadJob job) async {
    final db = await database;
    await db.insert(
      'jobs',
      job.toDatabaseJson(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<void> saveJobs(Iterable<DownloadJob> jobs) async {
    final db = await database;
    await db.transaction((txn) async {
      final batch = txn.batch();
      for (final job in jobs) {
        batch.insert(
          'jobs',
          job.toDatabaseJson(),
          conflictAlgorithm: ConflictAlgorithm.replace,
        );
      }
      await batch.commit(noResult: true);
    });
  }

  Future<void> deleteJob(String id) async {
    final db = await database;
    await db.delete('jobs', where: 'id = ?', whereArgs: [id]);
  }

  Future<void> deleteJobs(Iterable<String> ids) async {
    final values = ids.toList(growable: false);
    if (values.isEmpty) return;
    final db = await database;
    await db.transaction((txn) async {
      final batch = txn.batch();
      for (final id in values) {
        batch.delete('jobs', where: 'id = ?', whereArgs: [id]);
      }
      await batch.commit(noResult: true);
    });
  }

  Future<String?> getSetting(String key) async {
    final db = await database;
    final rows = await db.query(
      'settings',
      where: 'key = ?',
      whereArgs: [key],
      limit: 1,
    );
    return rows.isEmpty ? null : rows.first['value'] as String;
  }

  Future<void> setSetting(String key, String value) async {
    final db = await database;
    await db.insert('settings', {
      'key': key,
      'value': value,
    }, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<void> clearPersonalData() async {
    final db = await database;
    await db.transaction((txn) async {
      await txn.delete('jobs');
      await txn.delete('settings');
    });
  }

  Future<void> close() async {
    await _database?.close();
    _database = null;
  }
}
