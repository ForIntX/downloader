import 'dart:async';

import 'package:flutter/services.dart';

import '../core/constants.dart';
import '../models/download_models.dart';
import 'download_engine.dart';

class PlatformDownloadEngine implements DownloadEngine {
  PlatformDownloadEngine()
    : _methods = const MethodChannel(engineMethodChannel),
      _eventChannel = const EventChannel(engineEventChannel) {
    _subscription = _eventChannel.receiveBroadcastStream().listen(
      (event) {
        if (event is Map) {
          _events.add(DownloadEvent.fromJson(event));
        }
      },
      onError: (Object error, StackTrace stackTrace) {
        _events.addError(error, stackTrace);
      },
    );
  }

  final MethodChannel _methods;
  final EventChannel _eventChannel;
  final EventChannel _playlistChannel = const EventChannel(
    playlistEventChannel,
  );
  final StreamController<DownloadEvent> _events = StreamController.broadcast();
  StreamSubscription<Object?>? _subscription;
  bool _wifiOnly = false;
  bool _chargingOnly = false;

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
    String localeCode = 'tr',
  }) async {
    _wifiOnly = wifiOnly;
    _chargingOnly = chargingOnly;
    await _methods.invokeMethod<void>('setDownloadConstraints', {
      'wifi_only': wifiOnly,
      'charging_only': chargingOnly,
      'locale': localeCode,
    });
  }

  @override
  Future<VideoMetadata> getVideoInfo(String url) async {
    final result = await _methods.invokeMapMethod<Object?, Object?>(
      'getVideoInfo',
      {'url': url},
    );
    if (result == null) {
      throw const DownloadEngineException('Video bilgisi alınamadı.');
    }
    return VideoMetadata.fromJson(result);
  }

  @override
  Stream<PlaylistEntry> scanPlaylist(String url) async* {
    final controller = StreamController<PlaylistEntry>();
    late final StreamSubscription<Object?> subscription;
    subscription = _playlistChannel.receiveBroadcastStream().listen((event) {
      if (event is! Map) return;
      switch (event['kind']) {
        case 'entry':
          final value = event['entry'];
          if (value is Map) controller.add(PlaylistEntry.fromJson(value));
          return;
        case 'done':
          unawaited(controller.close());
          return;
        case 'error':
          controller.addError(
            DownloadEngineException(
              event['message']?.toString() ?? 'Playlist taranamadı.',
            ),
          );
          unawaited(controller.close());
          return;
      }
    }, onError: controller.addError);
    try {
      await _methods.invokeMethod<void>('startPlaylistScan', {'url': url});
      yield* controller.stream;
    } finally {
      await _methods.invokeMethod<void>('stopPlaylistScan');
      await subscription.cancel();
      if (!controller.isClosed) await controller.close();
    }
  }

  @override
  Future<void> start(DownloadJob job) => _methods.invokeMethod<void>(
    'startDownload',
    {...job.toJson(), 'wifi_only': _wifiOnly, 'charging_only': _chargingOnly},
  );

  @override
  Future<void> pause(String jobId) =>
      _methods.invokeMethod<void>('pauseDownload', {'job_id': jobId});

  @override
  Future<void> resume(DownloadJob job) => _methods.invokeMethod<void>(
    'resumeDownload',
    {...job.toJson(), 'wifi_only': _wifiOnly, 'charging_only': _chargingOnly},
  );

  @override
  Future<void> cancel(String jobId, {bool deletePartial = false}) =>
      _methods.invokeMethod<void>('cancelDownload', {
        'job_id': jobId,
        'delete_partial': deletePartial,
      });

  @override
  Future<bool> outputExists(String path) async =>
      await _methods.invokeMethod<bool>('outputExists', {'path': path}) ??
      false;

  @override
  Future<void> openOutput(String path) =>
      _methods.invokeMethod<void>('openOutput', {'path': path});

  @override
  Future<void> openOutputLocation(String path) =>
      _methods.invokeMethod<void>('openOutputLocation', {'path': path});

  @override
  Future<void> shareOutput(String path) =>
      _methods.invokeMethod<void>('shareOutput', {'path': path});

  @override
  Future<Map<String, String>> downloadLocations() async {
    final result = await _methods.invokeMapMethod<String, String>(
      'downloadLocations',
    );
    return result ?? const {};
  }

  @override
  Future<void> openDownloadLocation(String kind) =>
      _methods.invokeMethod<void>('openDownloadLocation', {'kind': kind});

  @override
  Future<Map<String, Object?>> diagnostics() async =>
      await _methods.invokeMapMethod<String, Object?>('diagnostics') ??
      const {};

  @override
  Future<void> dispose() async {
    await _subscription?.cancel();
    await _events.close();
  }
}
