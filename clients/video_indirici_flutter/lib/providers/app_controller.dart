import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import '../core/constants.dart';
import '../data/database.dart';
import '../engine/download_engine.dart';
import '../engine/engine_factory.dart';
import '../models/download_models.dart';
import '../services/background_audio.dart';

class AppState {
  const AppState({
    this.initialized = false,
    this.busy = false,
    this.scanning = false,
    this.video,
    this.playlist = const [],
    this.jobs = const [],
    this.filter = '',
    this.presetId = 'video-best',
    this.error,
    this.wifiOnly = false,
    this.chargingOnly = false,
    this.concurrentDownloads = 1,
    this.concurrentFragments = 4,
    this.speedLimit = '',
    this.filenameTemplate = defaultOutputTemplate,
    this.customFormat = '',
    this.cookieMode = 'none',
    this.cookieBrowser = 'firefox',
    this.cookieProfile = '',
    this.cookieFile = '',
    this.localeCode = 'en',
  });

  final bool initialized;
  final bool busy;
  final bool scanning;
  final VideoMetadata? video;
  final List<PlaylistEntry> playlist;
  final List<DownloadJob> jobs;
  final String filter;
  final String presetId;
  final String? error;
  final bool wifiOnly;
  final bool chargingOnly;
  final int concurrentDownloads;
  final int concurrentFragments;
  final String speedLimit;
  final String filenameTemplate;
  final String customFormat;
  final String cookieMode;
  final String cookieBrowser;
  final String cookieProfile;
  final String cookieFile;
  final String localeCode;

  List<PlaylistEntry> get visiblePlaylist {
    final query = filter.trim().toLowerCase();
    if (query.isEmpty) return playlist;
    return playlist
        .where(
          (entry) =>
              entry.title.toLowerCase().contains(query) ||
              (entry.channel?.toLowerCase().contains(query) ?? false),
        )
        .toList(growable: false);
  }

  List<DownloadJob> get queue =>
      jobs.where((job) => !job.status.isFinished).toList(growable: false);
  List<DownloadJob> get history => jobs
      .where((job) => job.status.isFinished)
      .toList(growable: false)
      .reversed
      .toList();
  bool get hasActiveDownloads => jobs.any((job) => job.status.isActive);

  AppState copyWith({
    bool? initialized,
    bool? busy,
    bool? scanning,
    VideoMetadata? video,
    bool clearVideo = false,
    List<PlaylistEntry>? playlist,
    List<DownloadJob>? jobs,
    String? filter,
    String? presetId,
    String? error,
    bool clearError = false,
    bool? wifiOnly,
    bool? chargingOnly,
    int? concurrentDownloads,
    int? concurrentFragments,
    String? speedLimit,
    String? filenameTemplate,
    String? customFormat,
    String? cookieMode,
    String? cookieBrowser,
    String? cookieProfile,
    String? cookieFile,
    String? localeCode,
  }) => AppState(
    initialized: initialized ?? this.initialized,
    busy: busy ?? this.busy,
    scanning: scanning ?? this.scanning,
    video: clearVideo ? null : video ?? this.video,
    playlist: playlist ?? this.playlist,
    jobs: jobs ?? this.jobs,
    filter: filter ?? this.filter,
    presetId: presetId ?? this.presetId,
    error: clearError ? null : error ?? this.error,
    wifiOnly: wifiOnly ?? this.wifiOnly,
    chargingOnly: chargingOnly ?? this.chargingOnly,
    concurrentDownloads: concurrentDownloads ?? this.concurrentDownloads,
    concurrentFragments: concurrentFragments ?? this.concurrentFragments,
    speedLimit: speedLimit ?? this.speedLimit,
    filenameTemplate: filenameTemplate ?? this.filenameTemplate,
    customFormat: customFormat ?? this.customFormat,
    cookieMode: cookieMode ?? this.cookieMode,
    cookieBrowser: cookieBrowser ?? this.cookieBrowser,
    cookieProfile: cookieProfile ?? this.cookieProfile,
    cookieFile: cookieFile ?? this.cookieFile,
    localeCode: localeCode ?? this.localeCode,
  );
}

class EnqueueResult {
  const EnqueueResult({
    required this.added,
    required this.skipped,
    this.redownloadable = 0,
  });
  final int added;
  final int skipped;
  final int redownloadable;
}

class AppController extends StateNotifier<AppState> {
  AppController({AppDatabase? database, DownloadEngine? engine})
    : database = database ?? AppDatabase(),
      engine = engine ?? createDownloadEngine(),
      super(const AppState()) {
    _eventSubscription = this.engine.events.listen(
      _handleEvent,
      onError: _handleEngineError,
    );
  }

  final AppDatabase database;
  final DownloadEngine engine;
  final _uuid = const Uuid();
  StreamSubscription<DownloadEvent>? _eventSubscription;
  StreamSubscription<PlaylistEntry>? _scanSubscription;
  final Map<String, DateTime> _lastProgressWrite = {};
  final Map<String, VideoMetadata> _videoInfoCache = {};

  Future<void> initialize() async {
    try {
      var jobs = await database.loadJobs();
      jobs = [
        for (final job in jobs)
          if (job.status.isActive)
            job.copyWith(
              status: DownloadStatus.paused,
              updatedAt: DateTime.now(),
            )
          else
            job,
      ];
      await database.saveJobs(jobs);
      state = state.copyWith(
        initialized: true,
        jobs: jobs,
        presetId: await database.getSetting('preset_id') ?? state.presetId,
        wifiOnly: (await database.getSetting('wifi_only')) == 'true',
        chargingOnly: (await database.getSetting('charging_only')) == 'true',
        concurrentDownloads:
            int.tryParse(
              await database.getSetting('concurrent_downloads') ?? '',
            ) ??
            1,
        concurrentFragments:
            int.tryParse(
              await database.getSetting('concurrent_fragments') ?? '',
            ) ??
            4,
        speedLimit: await database.getSetting('speed_limit') ?? '',
        filenameTemplate:
            await database.getSetting('filename_template') ??
            defaultOutputTemplate,
        customFormat: await database.getSetting('custom_format') ?? '',
        cookieMode: await database.getSetting('cookie_mode') ?? 'none',
        cookieBrowser: await database.getSetting('cookie_browser') ?? 'firefox',
        cookieProfile: await database.getSetting('cookie_profile') ?? '',
        cookieFile: await database.getSetting('cookie_file') ?? '',
        localeCode: await database.getSetting('locale') ?? 'en',
        clearError: true,
      );
      await _configureEngine();
      unawaited(_runNext());
    } catch (error) {
      state = state.copyWith(
        initialized: true,
        error: 'Veriler açılamadı: $error',
      );
    }
  }

  Future<void> getInformation(String url, {required bool playlist}) async {
    final normalized = url.trim();
    if (normalized.isEmpty) {
      state = state.copyWith(error: 'Bir video veya playlist URL\'si girin.');
      return;
    }
    await stopScan();
    state = state.copyWith(
      busy: true,
      scanning: playlist,
      clearError: true,
      clearVideo: playlist,
      playlist: const [],
    );
    if (!playlist) {
      try {
        final cacheKey = _normalizeUrl(normalized);
        final info =
            _videoInfoCache[cacheKey] ?? await engine.getVideoInfo(normalized);
        _videoInfoCache[cacheKey] = info;
        state = state.copyWith(video: info, busy: false);
      } catch (error) {
        state = state.copyWith(busy: false, error: _friendlyError(error));
      }
      return;
    }
    final entries = <PlaylistEntry>[];
    _scanSubscription = engine
        .scanPlaylist(normalized)
        .listen(
          (entry) {
            entries.add(entry);
            state = state.copyWith(
              playlist: List.unmodifiable(entries),
              busy: false,
            );
          },
          onError: (Object error) {
            state = state.copyWith(
              busy: false,
              scanning: false,
              error: _friendlyError(error),
            );
          },
          onDone: () {
            state = state.copyWith(busy: false, scanning: false);
          },
        );
  }

  Future<void> stopScan() async {
    await _scanSubscription?.cancel();
    _scanSubscription = null;
    if (state.scanning) state = state.copyWith(scanning: false, busy: false);
  }

  void setFilter(String value) => state = state.copyWith(filter: value);

  void togglePlaylistEntry(String id, bool selected) {
    state = state.copyWith(
      playlist: [
        for (final item in state.playlist)
          item.id == id ? item.copyWith(selected: selected) : item,
      ],
    );
  }

  void selectAll(bool selected) {
    state = state.copyWith(
      playlist: [
        for (final item in state.playlist) item.copyWith(selected: selected),
      ],
    );
  }

  void selectVisible() {
    final visibleIds = state.visiblePlaylist.map((entry) => entry.id).toSet();
    state = state.copyWith(
      playlist: [
        for (final item in state.playlist)
          if (visibleIds.contains(item.id))
            item.copyWith(selected: true)
          else
            item,
      ],
    );
  }

  Future<void> setPreset(String presetId) async {
    state = state.copyWith(presetId: presetId);
    await database.setSetting('preset_id', presetId);
  }

  Future<void> setCustomFormat(String value) async {
    state = state.copyWith(customFormat: value);
    await database.setSetting('custom_format', value);
  }

  Future<EnqueueResult> enqueueCurrent({
    bool redownloadDuplicates = false,
  }) async {
    final customFormat = state.customFormat.trim();
    if (state.presetId == 'custom' && customFormat.isEmpty) {
      state = state.copyWith(error: 'Özel yt-dlp formatı boş bırakılamaz.');
      return const EnqueueResult(added: 0, skipped: 0);
    }
    final filenameTemplate = state.filenameTemplate.trim();
    if (filenameTemplate.isEmpty ||
        filenameTemplate.contains('/') ||
        filenameTemplate.contains('\\')) {
      state = state.copyWith(
        error: 'Dosya adı şablonu boş olamaz ve klasör ayıracı içeremez.',
      );
      return const EnqueueResult(added: 0, skipped: 0);
    }
    final candidates = <PlaylistEntry>[
      if (state.playlist.isNotEmpty)
        ...state.playlist.where((entry) => entry.selected && entry.available),
      if (state.playlist.isEmpty && state.video != null)
        PlaylistEntry(
          id: state.video!.id,
          url: state.video!.url,
          title: state.video!.title,
          channel: state.video!.channel,
          thumbnailUrl: state.video!.thumbnailUrl,
        ),
    ];
    final jobs = [...state.jobs];
    var skipped = 0;
    var redownloadable = 0;
    var position = jobs.fold<int>(
      0,
      (max, job) => job.position >= max ? job.position + 1 : max,
    );
    for (final item in candidates) {
      final normalizedUrl = _normalizeUrl(item.url);
      final duplicates = jobs
          .where((job) => _normalizeUrl(job.url) == normalizedUrl)
          .toList(growable: false);
      if (duplicates.isNotEmpty) {
        final canRedownload = duplicates.every((job) => job.status.isFinished);
        if (!redownloadDuplicates || !canRedownload) {
          skipped++;
          if (canRedownload) redownloadable++;
          continue;
        }
      }
      jobs.add(
        DownloadJob(
          id: _uuid.v4(),
          url: item.url,
          title: item.title,
          presetId: state.presetId,
          thumbnailUrl: item.thumbnailUrl,
          position: position++,
          createdAt: DateTime.now(),
          sourceId: item.id,
          customFormat: customFormat,
          speedLimit: state.speedLimit,
          concurrentFragments: state.concurrentFragments,
          filenameTemplate: filenameTemplate,
          cookieMode: state.cookieMode,
          cookieBrowser: state.cookieBrowser,
          cookieProfile: state.cookieProfile,
          cookieFile: state.cookieFile,
        ),
      );
    }
    state = state.copyWith(jobs: jobs);
    await database.saveJobs(jobs);
    unawaited(_runNext());
    return EnqueueResult(
      added: candidates.length - skipped,
      skipped: skipped,
      redownloadable: redownloadable,
    );
  }

  Future<void> _runNext() async {
    final active = state.jobs.where((job) => job.status.isActive).length;
    if (active >= state.concurrentDownloads) return;
    final pending =
        state.jobs.where((job) => job.status == DownloadStatus.pending).toList()
          ..sort((a, b) => a.position.compareTo(b.position));
    if (pending.isEmpty) return;
    final slots = state.concurrentDownloads - active;
    for (final job in pending.take(slots)) {
      final preparing = job.copyWith(
        status: DownloadStatus.preparing,
        updatedAt: DateTime.now(),
        clearError: true,
      );
      await _replaceAndSave(preparing);
      try {
        await engine.start(preparing);
      } catch (error) {
        await _replaceAndSave(
          preparing.copyWith(
            status: DownloadStatus.failed,
            error: _friendlyError(error),
          ),
        );
      }
    }
  }

  void _handleEvent(DownloadEvent event) {
    final index = state.jobs.indexWhere((job) => job.id == event.jobId);
    if (index < 0) return;
    final old = state.jobs[index];
    final updated = old.copyWith(
      status: event.status,
      progress: event.progress,
      speed: event.speed,
      etaSeconds: event.etaSeconds,
      outputPath: event.outputPath,
      error: event.error,
      updatedAt: DateTime.now(),
    );
    final jobs = [...state.jobs]..[index] = updated;
    state = state.copyWith(jobs: jobs);
    final now = DateTime.now();
    final lastWrite = _lastProgressWrite[event.jobId];
    if (event.status != DownloadStatus.downloading ||
        lastWrite == null ||
        now.difference(lastWrite) >= progressThrottle) {
      _lastProgressWrite[event.jobId] = now;
      unawaited(database.saveJob(updated));
    }
    if (event.status.isFinished) unawaited(_runNext());
  }

  void _handleEngineError(Object error, StackTrace stackTrace) {
    state = state.copyWith(error: _friendlyError(error));
  }

  Future<void> pause(DownloadJob job) async {
    await engine.pause(job.id);
    await _replaceAndSave(
      job.copyWith(status: DownloadStatus.paused, updatedAt: DateTime.now()),
    );
    unawaited(_runNext());
  }

  Future<void> resume(DownloadJob job) async {
    final pending = job.copyWith(
      status: DownloadStatus.pending,
      updatedAt: DateTime.now(),
      clearError: true,
    );
    await _replaceAndSave(pending);
    unawaited(_runNext());
  }

  Future<void> cancel(DownloadJob job, {bool deletePartial = false}) async {
    await engine.cancel(job.id, deletePartial: deletePartial);
    await _replaceAndSave(
      job.copyWith(status: DownloadStatus.cancelled, updatedAt: DateTime.now()),
    );
    unawaited(_runNext());
  }

  Future<void> cancelActiveDownloads() async {
    final active = state.jobs.where((job) => job.status.isActive).toList();
    for (final job in active) {
      await engine.cancel(job.id);
    }
    if (active.isEmpty) return;
    final activeIds = active.map((job) => job.id).toSet();
    final now = DateTime.now();
    final jobs = [
      for (final job in state.jobs)
        if (activeIds.contains(job.id))
          job.copyWith(status: DownloadStatus.cancelled, updatedAt: now)
        else
          job,
    ];
    state = state.copyWith(jobs: jobs);
    await database.saveJobs(jobs);
  }

  Future<void> retry(DownloadJob job) async {
    final retried = job.copyWith(
      status: DownloadStatus.pending,
      progress: 0,
      updatedAt: DateTime.now(),
      clearError: true,
    );
    await _replaceAndSave(retried);
    unawaited(_runNext());
  }

  Future<void> remove(DownloadJob job) async {
    if (job.status.isActive) await engine.cancel(job.id);
    state = state.copyWith(
      jobs: state.jobs.where((item) => item.id != job.id).toList(),
    );
    await database.deleteJob(job.id);
  }

  Future<int> clearHistory({MediaKind? kind}) async {
    final removed = state.history
        .where((job) => kind == null || job.preset.kind == kind)
        .toList(growable: false);
    if (removed.isEmpty) return 0;
    final ids = removed.map((job) => job.id).toSet();
    state = state.copyWith(
      jobs: state.jobs.where((job) => !ids.contains(job.id)).toList(),
    );
    await database.deleteJobs(ids);
    return removed.length;
  }

  Future<void> reorder(int oldIndex, int newIndex) async {
    final queue = state.queue;
    if (oldIndex < 0 ||
        oldIndex >= queue.length ||
        queue[oldIndex].status.isActive) {
      return;
    }
    final moved = queue.removeAt(oldIndex);
    queue.insert(newIndex.clamp(0, queue.length), moved);
    final positions = {for (var i = 0; i < queue.length; i++) queue[i].id: i};
    final jobs = [
      for (final job in state.jobs)
        positions.containsKey(job.id)
            ? job.copyWith(position: positions[job.id])
            : job,
    ];
    state = state.copyWith(jobs: jobs);
    await database.saveJobs(jobs);
  }

  Future<bool> openOutput(DownloadJob job) async {
    final path = job.outputPath;
    if (path == null || !await engine.outputExists(path)) return false;
    await engine.openOutput(path);
    return true;
  }

  Future<bool> openOutputLocation(DownloadJob job) async {
    final path = job.outputPath;
    if (path == null || !await engine.outputExists(path)) return false;
    await engine.openOutputLocation(path);
    return true;
  }

  Future<bool> playAudio(DownloadJob selected) async {
    final path = selected.outputPath;
    if (path == null || !await engine.outputExists(path)) return false;
    final handler = await initializeBackgroundAudio();
    if (handler == null) return false;
    await handler
        .loadJobs(state.history, selectedJobId: selected.id)
        .timeout(const Duration(seconds: 20));
    return true;
  }

  Future<void> shareOutput(DownloadJob job) async {
    final path = job.outputPath;
    if (path == null || !await engine.outputExists(path)) {
      throw const DownloadEngineException('Dosya bulunamadı.');
    }
    await engine.shareOutput(path);
  }

  Future<void> setWifiOnly(bool value) async {
    state = state.copyWith(wifiOnly: value);
    await database.setSetting('wifi_only', '$value');
    await _configureEngine();
    unawaited(_runNext());
  }

  Future<void> setChargingOnly(bool value) async {
    state = state.copyWith(chargingOnly: value);
    await database.setSetting('charging_only', '$value');
    await _configureEngine();
    unawaited(_runNext());
  }

  Future<void> setConcurrentDownloads(int value) async {
    state = state.copyWith(concurrentDownloads: value.clamp(1, 3));
    await database.setSetting(
      'concurrent_downloads',
      '${state.concurrentDownloads}',
    );
    unawaited(_runNext());
  }

  Future<void> setConcurrentFragments(int value) async {
    state = state.copyWith(concurrentFragments: value.clamp(1, 8));
    await database.setSetting(
      'concurrent_fragments',
      '${state.concurrentFragments}',
    );
  }

  Future<void> setSpeedLimit(String value) async {
    state = state.copyWith(speedLimit: value);
    await database.setSetting('speed_limit', value);
  }

  Future<void> setFilenameTemplate(String value) async {
    state = state.copyWith(filenameTemplate: value);
    await database.setSetting('filename_template', value);
  }

  Future<void> setCookieMode(String value) async {
    state = state.copyWith(cookieMode: value);
    await database.setSetting('cookie_mode', value);
    await _configureEngine();
  }

  Future<void> setCookieBrowser(String value) async {
    state = state.copyWith(cookieBrowser: value);
    await database.setSetting('cookie_browser', value);
    await _configureEngine();
  }

  Future<void> setCookieProfile(String value) async {
    state = state.copyWith(cookieProfile: value);
    await database.setSetting('cookie_profile', value);
    await _configureEngine();
  }

  Future<void> setCookieFile(String value) async {
    state = state.copyWith(cookieFile: value);
    await database.setSetting('cookie_file', value);
    await _configureEngine();
  }

  Future<void> setLocale(String value) async {
    state = state.copyWith(localeCode: value);
    await database.setSetting('locale', value);
    await _configureEngine();
  }

  Future<void> clearPersonalData() async {
    for (final job in state.jobs.where((item) => item.status.isActive)) {
      await engine.cancel(job.id);
    }
    await database.clearPersonalData();
    _videoInfoCache.clear();
    state = const AppState(initialized: true);
    await _configureEngine();
  }

  Future<void> _replaceAndSave(DownloadJob updated) async {
    final jobs = [
      for (final job in state.jobs)
        if (job.id == updated.id) updated else job,
    ];
    state = state.copyWith(jobs: jobs);
    await database.saveJob(updated);
  }

  Future<void> _configureEngine() => engine.configure(
    wifiOnly: state.wifiOnly,
    chargingOnly: state.chargingOnly,
    cookieMode: state.cookieMode,
    cookieBrowser: state.cookieBrowser,
    cookieProfile: state.cookieProfile,
    cookieFile: state.cookieFile,
    localeCode: state.localeCode,
  );

  String _normalizeUrl(String value) {
    final trimmed = value.trim();
    final uri = Uri.tryParse(trimmed);
    if (uri != null) {
      final host = uri.host.toLowerCase().replaceFirst('www.', '');
      String? videoId;
      if (host == 'youtu.be') {
        videoId = uri.pathSegments.firstOrNull;
      } else if (host == 'youtube.com' || host.endsWith('.youtube.com')) {
        videoId = uri.queryParameters['v'];
        if (videoId == null && uri.pathSegments.length >= 2) {
          if (const {'shorts', 'embed', 'live'}.contains(uri.pathSegments[0])) {
            videoId = uri.pathSegments[1];
          }
        }
      }
      if (videoId != null && videoId.isNotEmpty) return 'youtube:$videoId';
    }
    return trimmed
        .replaceFirst(RegExp(r'^https?://(www\.)?'), '')
        .replaceAll(RegExp(r'[?&]feature=[^&]+'), '');
  }

  String _friendlyError(Object error) {
    if (error is DownloadEngineException) return error.toString();
    return error
        .toString()
        .replaceFirst('PlatformException(', '')
        .replaceFirst(RegExp(r'\)$'), '');
  }

  @override
  void dispose() {
    unawaited(_scanSubscription?.cancel());
    unawaited(_eventSubscription?.cancel());
    unawaited(engine.dispose());
    unawaited(database.close());
    super.dispose();
  }
}

final appControllerProvider = StateNotifierProvider<AppController, AppState>((
  ref,
) {
  final controller = AppController();
  ref.onDispose(controller.dispose);
  unawaited(controller.initialize());
  return controller;
});
