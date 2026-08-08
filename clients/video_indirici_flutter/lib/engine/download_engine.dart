import '../models/download_models.dart';

abstract interface class DownloadEngine {
  Stream<DownloadEvent> get events;

  Future<VideoMetadata> getVideoInfo(String url);

  Stream<PlaylistEntry> scanPlaylist(String url);

  Future<void> configure({
    required bool wifiOnly,
    required bool chargingOnly,
    String cookieMode = 'none',
    String cookieBrowser = 'firefox',
    String cookieProfile = '',
    String cookieFile = '',
    String localeCode = 'tr',
  });

  Future<void> start(DownloadJob job);

  Future<void> pause(String jobId);

  Future<void> resume(DownloadJob job);

  Future<void> cancel(String jobId, {bool deletePartial = false});

  Future<bool> outputExists(String path);

  Future<void> openOutput(String path);

  Future<void> openOutputLocation(String path);

  Future<void> shareOutput(String path);

  Future<Map<String, String>> downloadLocations();

  Future<void> openDownloadLocation(String kind);

  Future<Map<String, Object?>> diagnostics();

  Future<void> dispose();
}

class DownloadEngineException implements Exception {
  const DownloadEngineException(this.message, {this.details});

  final String message;
  final String? details;

  @override
  String toString() => details == null ? message : '$message\n$details';
}
