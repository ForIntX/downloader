import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/constants.dart';
import '../models/download_models.dart';
import 'download_engine.dart';

class WindowsProcessDownloadEngine implements DownloadEngine {
  final StreamController<DownloadEvent> _events = StreamController.broadcast();
  final Map<String, Process> _processes = {};
  final Set<String> _paused = {};
  String _cookieMode = 'none';
  String _cookieBrowser = 'firefox';
  String _cookieProfile = '';
  String _cookieFile = '';

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
  }) async {
    _cookieMode = cookieMode;
    _cookieBrowser = cookieBrowser;
    _cookieProfile = cookieProfile;
    _cookieFile = cookieFile;
  }

  String get _toolDirectory {
    final executableDir = p.dirname(Platform.resolvedExecutable);
    final bundled = p.join(executableDir, 'tools');
    if (Directory(bundled).existsSync()) return bundled;
    return p.join(Directory.current.path, 'tools');
  }

  String get _ytDlp {
    final bundled = p.join(_toolDirectory, 'yt-dlp.exe');
    return File(bundled).existsSync() ? bundled : 'yt-dlp';
  }

  List<String> get _runtimeArguments {
    final deno = p.join(_toolDirectory, 'deno.exe');
    final ffmpeg = p.join(_toolDirectory, 'ffmpeg.exe');
    return [
      if (File(deno).existsSync()) ...['--js-runtimes', 'deno:$deno'],
      if (File(ffmpeg).existsSync()) ...['--ffmpeg-location', _toolDirectory],
    ];
  }

  List<String> _cookieArguments({
    String? mode,
    String? browser,
    String? profile,
    String? cookieFile,
  }) {
    final selectedMode = mode ?? _cookieMode;
    if (selectedMode == 'browser') {
      final selectedBrowser = browser ?? _cookieBrowser;
      final selectedProfile = (profile ?? _cookieProfile).trim();
      return [
        '--cookies-from-browser',
        selectedProfile.isEmpty
            ? selectedBrowser
            : '$selectedBrowser:$selectedProfile',
      ];
    }
    if (selectedMode == 'file') {
      final path = (cookieFile ?? _cookieFile).trim();
      if (path.isEmpty || !File(path).existsSync()) {
        throw const DownloadEngineException(
          'Seçilen cookies.txt dosyası bulunamadı.',
        );
      }
      return ['--cookies', path];
    }
    return const [];
  }

  @override
  Future<VideoMetadata> getVideoInfo(String url) async {
    final result = await Process.run(_ytDlp, [
      '--dump-single-json',
      '--no-playlist',
      '--no-warnings',
      ..._runtimeArguments,
      ..._cookieArguments(),
      url,
    ]);
    if (result.exitCode != 0) {
      throw DownloadEngineException(
        'Video bilgisi alınamadı.',
        details: result.stderr.toString(),
      );
    }
    return VideoMetadata.fromJson(
      jsonDecode(result.stdout as String) as Map<String, Object?>,
    );
  }

  @override
  Stream<PlaylistEntry> scanPlaylist(String url) async* {
    final process = await Process.start(_ytDlp, [
      '--flat-playlist',
      '--lazy-playlist',
      '--dump-json',
      '--no-warnings',
      ..._runtimeArguments,
      ..._cookieArguments(),
      url,
    ]);
    final errors = StringBuffer();
    process.stderr.transform(utf8.decoder).listen(errors.write);
    var completed = false;
    try {
      await for (final line
          in process.stdout
              .transform(utf8.decoder)
              .transform(const LineSplitter())) {
        if (line.trim().isEmpty) continue;
        yield PlaylistEntry.fromJson(jsonDecode(line) as Map<String, Object?>);
      }
      final code = await process.exitCode;
      completed = true;
      if (code != 0) {
        throw DownloadEngineException(
          'Playlist taranamadı.',
          details: errors.toString(),
        );
      }
    } finally {
      if (!completed) await _terminateTree(process.pid);
    }
  }

  @override
  Future<void> start(DownloadJob job) async {
    if (_processes.containsKey(job.id)) return;
    final downloads = await getDownloadsDirectory();
    if (downloads == null) {
      throw const DownloadEngineException('İndirilenler klasörü bulunamadı.');
    }
    final target = Directory(p.join(downloads.path, appName));
    await target.create(recursive: true);
    final preset = job.preset;
    final formatSelector = preset.id == 'custom'
        ? job.customFormat.trim()
        : preset.format;
    if (formatSelector.isEmpty) {
      throw const DownloadEngineException(
        'Özel yt-dlp formatı boş bırakılamaz.',
      );
    }
    final filenameTemplate = job.filenameTemplate.trim();
    if (filenameTemplate.isEmpty ||
        p.basename(filenameTemplate) != filenameTemplate) {
      throw const DownloadEngineException('Dosya adı şablonu geçersiz.');
    }
    final args = <String>[
      '--newline',
      '--continue',
      '--no-playlist',
      '--concurrent-fragments',
      '${job.concurrentFragments.clamp(1, 8)}',
      if (job.speedLimit.isNotEmpty) ...['--limit-rate', job.speedLimit],
      '--progress-template',
      'download:VI_PROGRESS:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s',
      '--print',
      'after_move:VI_FILE:%(filepath)s',
      '--windows-filenames',
      '-o',
      p.join(target.path, filenameTemplate),
      '-f',
      formatSelector,
      ..._runtimeArguments,
      ..._cookieArguments(
        mode: job.cookieMode,
        browser: job.cookieBrowser,
        profile: job.cookieProfile,
        cookieFile: job.cookieFile,
      ),
      if (preset.kind == MediaKind.video) ...['--merge-output-format', 'mp4'],
      if (preset.extension == 'mp3') ...[
        '--extract-audio',
        '--audio-format',
        'mp3',
        '--audio-quality',
        '${preset.audioBitrate}K',
      ],
      if (preset.extension == 'm4a') ...[
        '--extract-audio',
        '--audio-format',
        'm4a',
      ],
      if (preset.extension == 'opus') ...[
        '--extract-audio',
        '--audio-format',
        'opus',
      ],
      job.url,
    ];
    final process = await Process.start(_ytDlp, args);
    _processes[job.id] = process;
    _events.add(
      DownloadEvent(
        jobId: job.id,
        status: DownloadStatus.downloading,
        progress: 0,
      ),
    );
    final errors = StringBuffer();
    process.stderr
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen((line) {
          errors.writeln(line);
          _parseLine(job.id, line);
        });
    process.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen((line) => _parseLine(job.id, line));
    unawaited(
      process.exitCode.then((code) {
        _processes.remove(job.id);
        if (_paused.remove(job.id)) return;
        if (code == 0) {
          _events.add(
            DownloadEvent(
              jobId: job.id,
              status: DownloadStatus.completed,
              progress: 100,
            ),
          );
        } else {
          _events.add(
            DownloadEvent(
              jobId: job.id,
              status: DownloadStatus.failed,
              error: errors.toString().trim().isEmpty
                  ? 'yt-dlp $code koduyla kapandı.'
                  : errors.toString().trim(),
            ),
          );
        }
      }),
    );
  }

  void _parseLine(String jobId, String line) {
    if (line.startsWith('VI_FILE:')) {
      _events.add(
        DownloadEvent(
          jobId: jobId,
          status: DownloadStatus.processing,
          outputPath: line.substring('VI_FILE:'.length).trim(),
          progress: 100,
        ),
      );
    } else if (line.startsWith('VI_PROGRESS:')) {
      final fields = line.substring('VI_PROGRESS:'.length).split('|');
      final percent = double.tryParse(fields.first.replaceAll('%', '').trim());
      _events.add(
        DownloadEvent(
          jobId: jobId,
          status: DownloadStatus.downloading,
          progress: percent,
          speed: fields.length > 1 ? fields[1].trim() : null,
          etaSeconds: fields.length > 2 ? _parseEta(fields[2]) : null,
        ),
      );
    }
  }

  int? _parseEta(String raw) {
    final parts = raw.trim().split(':').map(int.tryParse).toList();
    if (parts.any((value) => value == null)) return null;
    var seconds = 0;
    for (final value in parts) {
      seconds = seconds * 60 + value!;
    }
    return seconds;
  }

  @override
  Future<void> pause(String jobId) async {
    final process = _processes[jobId];
    if (process == null) return;
    _paused.add(jobId);
    await _terminateTree(process.pid);
    _events.add(DownloadEvent(jobId: jobId, status: DownloadStatus.paused));
  }

  @override
  Future<void> resume(DownloadJob job) => start(job);

  @override
  Future<void> cancel(String jobId, {bool deletePartial = false}) async {
    _paused.remove(jobId);
    final process = _processes[jobId];
    if (process != null) await _terminateTree(process.pid);
    _events.add(DownloadEvent(jobId: jobId, status: DownloadStatus.cancelled));
  }

  @override
  Future<bool> outputExists(String path) => File(path).exists();

  @override
  Future<void> openOutput(String path) async {
    if (!await launchUrl(Uri.file(path))) {
      throw const DownloadEngineException('Dosya açılamadı.');
    }
  }

  @override
  Future<void> openOutputLocation(String path) async {
    final parent = File(path).parent.path;
    if (!await launchUrl(Uri.directory(parent))) {
      throw const DownloadEngineException('Dosya konumu açılamadı.');
    }
  }

  @override
  Future<void> shareOutput(String path) async {
    await SharePlus.instance.share(ShareParams(files: [XFile(path)]));
  }

  @override
  Future<Map<String, String>> downloadLocations() async {
    final downloads = await getDownloadsDirectory();
    final location = downloads == null
        ? p.join(
            Platform.environment['USERPROFILE'] ?? '',
            'Downloads',
            appName,
          )
        : p.join(downloads.path, appName);
    return {'video': location, 'audio': location};
  }

  @override
  Future<void> openDownloadLocation(String kind) async {
    final locations = await downloadLocations();
    final path = locations[kind] ?? locations['video'];
    if (path == null || !await launchUrl(Uri.directory(path))) {
      throw const DownloadEngineException('Klasör açılamadı.');
    }
  }

  @override
  Future<Map<String, Object?>> diagnostics() async => {
    'platform': Platform.operatingSystem,
    'yt_dlp': _ytDlp,
    'yt_dlp_available':
        _ytDlp != 'yt-dlp' ||
        (await Process.run('where', ['yt-dlp'])).exitCode == 0,
    'tool_directory': _toolDirectory,
  };

  @override
  Future<void> dispose() async {
    for (final process in _processes.values) {
      await _terminateTree(process.pid);
    }
    _processes.clear();
    await _events.close();
  }

  Future<void> _terminateTree(int pid) async {
    final process = _processes.values
        .where((item) => item.pid == pid)
        .firstOrNull;
    final graceful = await Process.run('taskkill', ['/PID', '$pid', '/T']);
    if (graceful.exitCode == 0 && process != null) {
      try {
        await process.exitCode.timeout(const Duration(seconds: 3));
        return;
      } on TimeoutException {
        // Alt süreç ağacı üç saniye içinde kapanmadı; zorla sonlandır.
      }
    }
    await Process.run('taskkill', ['/PID', '$pid', '/T', '/F']);
  }
}
