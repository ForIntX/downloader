import 'dart:async';
import 'dart:io';

import 'package:audio_service/audio_service.dart';
import 'package:just_audio/just_audio.dart' as ja;

import '../l10n/app_localizations.dart';
import '../models/download_models.dart';

Future<AppAudioHandler?>? _initializingAudio;
AppAudioHandler? _audioHandler;

AppAudioHandler? get backgroundAudioHandler => _audioHandler;

Future<AppAudioHandler?> initializeBackgroundAudio() {
  if (!Platform.isAndroid) return Future.value();
  return _initializingAudio ??= _createBackgroundAudio();
}

Future<AppAudioHandler?> _createBackgroundAudio() async {
  try {
    final handler = await AudioService.init<AppAudioHandler>(
      builder: AppAudioHandler.new,
      config: AudioServiceConfig(
        androidNotificationChannelId: 'com.forintx.videoindirici.playback',
        androidNotificationChannelName: tr('Müzik oynatma'),
        androidNotificationChannelDescription: tr(
          'İndirilen müziklerin arka planda oynatma kontrolleri',
        ),
        // app_icon manifestte de kullanıldığı için release kaynak küçültme
        // aşamasında silinmez. Dinamik mipmap adı bazı release APK'larda 0
        // dönüp Android'in "no valid small icon" hatasıyla kapanıyordu.
        androidNotificationIcon: 'drawable/app_icon',
        androidStopForegroundOnPause: false,
        androidResumeOnClick: true,
      ),
    );
    _audioHandler = handler;
    return handler;
  } catch (_) {
    // Başlatma hatası kalıcı olarak önbelleğe alınmasın; kullanıcı
    // oynatmayı yeniden denediğinde servis tekrar kurulabilsin.
    _initializingAudio = null;
    rethrow;
  }
}

List<MediaItem> audioItemsFromJobs(Iterable<DownloadJob> jobs) => [
  for (final job in jobs)
    if (job.status == DownloadStatus.completed &&
        job.preset.kind == MediaKind.audio &&
        job.outputPath != null)
      MediaItem(
        id: job.id,
        title: job.title,
        album: tr('İndirilen müzikler'),
        artist: 'Downloader',
        artUri: _safeUri(job.thumbnailUrl),
        extras: {'uri': job.outputPath, 'preset': job.preset.label},
      ),
];

Uri? _safeUri(String? value) {
  if (value == null || value.isEmpty) return null;
  return Uri.tryParse(value);
}

class AppAudioHandler extends BaseAudioHandler {
  AppAudioHandler() : _player = ja.AudioPlayer(maxSkipsOnError: 10) {
    _player.playbackEventStream.listen(_broadcastState);
    _player.currentIndexStream.listen(_broadcastCurrentItem);
    _player.durationStream.listen(_broadcastDuration);
    _player.errorStream.listen((error) {
      customEvent.add({
        'kind': 'error',
        'message': error.message ?? tr('Müzik oynatılamadı.'),
      });
    });
  }

  final ja.AudioPlayer _player;

  Stream<Duration> get positionStream => _player.positionStream;
  Stream<Duration?> get durationStream => _player.durationStream;
  int? get currentIndex => _player.currentIndex;

  Future<void> loadJobs(
    Iterable<DownloadJob> jobs, {
    required String selectedJobId,
  }) async {
    final items = audioItemsFromJobs(jobs);
    if (items.isEmpty) throw StateError(tr('Oynatılabilir müzik bulunamadı.'));
    final selectedIndex = items.indexWhere((item) => item.id == selectedJobId);
    if (selectedIndex < 0) throw StateError(tr('Seçilen müzik bulunamadı.'));
    queue.add(items);
    await _player.setAudioSources(
      [
        for (final item in items)
          ja.AudioSource.uri(
            Uri.parse(item.extras!['uri']! as String),
            tag: item,
          ),
      ],
      initialIndex: selectedIndex,
      initialPosition: Duration.zero,
    );
    mediaItem.add(items[selectedIndex]);
    await play();
  }

  @override
  Future<void> play() async {
    if (_player.processingState == ja.ProcessingState.completed) {
      await _player.seek(Duration.zero, index: _player.currentIndex);
    }
    // just_audio play() Future'ı parça durana veya bitene kadar tamamlanmaz.
    // AudioService komutunu ve oynatıcı ekranını bu süre boyunca bekletme.
    unawaited(
      _player.play().catchError((Object error) {
        customEvent.add({'kind': 'error', 'message': '$error'});
      }),
    );
  }

  @override
  Future<void> pause() => _player.pause();

  @override
  Future<void> seek(Duration position) => _player.seek(position);

  @override
  Future<void> skipToNext() async {
    final index = _player.currentIndex;
    if (index != null && index + 1 < queue.value.length) {
      await _player.seek(Duration.zero, index: index + 1);
      await play();
    }
  }

  @override
  Future<void> skipToPrevious() async {
    final index = _player.currentIndex;
    if (index != null && index > 0) {
      await _player.seek(Duration.zero, index: index - 1);
      await play();
    } else {
      await _player.seek(Duration.zero);
    }
  }

  @override
  Future<void> skipToQueueItem(int index) async {
    if (index < 0 || index >= queue.value.length) return;
    await _player.seek(Duration.zero, index: index);
    await play();
  }

  @override
  Future<void> stop() async {
    await _player.stop();
    playbackState.add(
      playbackState.value.copyWith(
        playing: false,
        processingState: AudioProcessingState.idle,
      ),
    );
    await super.stop();
  }

  void _broadcastCurrentItem(int? index) {
    if (index == null || index < 0 || index >= queue.value.length) return;
    mediaItem.add(queue.value[index]);
  }

  void _broadcastDuration(Duration? duration) {
    final current = mediaItem.value;
    final index = _player.currentIndex;
    if (current == null || index == null || current.duration == duration) {
      return;
    }
    final updated = current.copyWith(duration: duration);
    mediaItem.add(updated);
    final items = [...queue.value];
    if (index < items.length) {
      items[index] = updated;
      queue.add(items);
    }
  }

  void _broadcastState(ja.PlaybackEvent event) {
    final processingState = switch (_player.processingState) {
      ja.ProcessingState.idle => AudioProcessingState.idle,
      ja.ProcessingState.loading => AudioProcessingState.loading,
      ja.ProcessingState.buffering => AudioProcessingState.buffering,
      ja.ProcessingState.ready => AudioProcessingState.ready,
      ja.ProcessingState.completed => AudioProcessingState.completed,
    };
    final playing =
        _player.playing &&
        _player.processingState != ja.ProcessingState.completed;
    playbackState.add(
      PlaybackState(
        controls: [
          MediaControl.skipToPrevious,
          playing ? MediaControl.pause : MediaControl.play,
          MediaControl.skipToNext,
          MediaControl.stop,
        ],
        systemActions: const {
          MediaAction.seek,
          MediaAction.seekForward,
          MediaAction.seekBackward,
        },
        androidCompactActionIndices: const [0, 1, 2],
        processingState: processingState,
        playing: playing,
        updatePosition: _player.position,
        bufferedPosition: _player.bufferedPosition,
        speed: _player.speed,
        queueIndex: _player.currentIndex,
      ),
    );
  }
}
