import 'dart:async';
import 'dart:io';

import 'package:audio_service/audio_service.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:video_player/video_player.dart';

import '../models/download_models.dart';
import '../l10n/app_localizations.dart';
import '../l10n/localized_material.dart';
import '../providers/app_controller.dart';
import '../services/background_audio.dart';

class MediaPlayerScreen extends ConsumerStatefulWidget {
  const MediaPlayerScreen({required this.job, super.key});

  final DownloadJob job;

  @override
  ConsumerState<MediaPlayerScreen> createState() => _MediaPlayerScreenState();
}

class _MediaPlayerScreenState extends ConsumerState<MediaPlayerScreen> {
  VideoPlayerController? _videoPlayer;
  AppAudioHandler? _audioHandler;
  StreamSubscription<dynamic>? _audioErrorSubscription;
  late DownloadJob _currentJob;
  List<DownloadJob> _videoQueue = const [];
  var _videoIndex = 0;
  var _videoGeneration = 0;
  var _loading = true;
  Object? _error;

  bool get _usesBackgroundAudio =>
      !kIsWeb &&
      defaultTargetPlatform == TargetPlatform.android &&
      (_currentJob.preset.kind == MediaKind.audio ||
          _currentJob.presetId.startsWith('audio-'));

  @override
  void initState() {
    super.initState();
    _currentJob = widget.job;
    _initialize();
  }

  Future<void> _initialize() async {
    if (_usesBackgroundAudio) {
      try {
        final started = await ref
            .read(appControllerProvider.notifier)
            .playAudio(widget.job);
        if (!started) throw StateError('Dosya konumu bulunamadı.');
        final handler = backgroundAudioHandler;
        if (handler == null) throw StateError('Müzik servisi başlatılamadı.');
        await _audioErrorSubscription?.cancel();
        _audioErrorSubscription = handler.customEvent.listen((event) {
          if (!mounted || event is! Map || event['kind'] != 'error') return;
          setState(() {
            _error = event['message'] ?? 'Müzik oynatılamadı.';
            _loading = false;
          });
        });
        if (mounted) {
          setState(() {
            _audioHandler = handler;
            _loading = false;
          });
        }
      } catch (error) {
        if (mounted) {
          setState(() {
            _error = error;
            _loading = false;
          });
        }
      }
      return;
    }

    _videoQueue = ref
        .read(appControllerProvider)
        .history
        .where(
          (job) =>
              job.status == DownloadStatus.completed &&
              job.preset.kind == MediaKind.video &&
              job.outputPath != null,
        )
        .toList(growable: false);
    _videoIndex = _videoQueue.indexWhere((job) => job.id == widget.job.id);
    if (_videoIndex < 0) {
      _videoQueue = [widget.job, ..._videoQueue];
      _videoIndex = 0;
    }
    await _loadVideo(_videoIndex);
  }

  Future<void> _loadVideo(int index) async {
    if (index < 0 || index >= _videoQueue.length) return;
    final generation = ++_videoGeneration;
    final previous = _videoPlayer;
    _videoPlayer = null;
    _currentJob = _videoQueue[index];
    _videoIndex = index;
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    await previous?.dispose();
    try {
      final path = _currentJob.outputPath;
      if (path == null ||
          !await ref
              .read(appControllerProvider.notifier)
              .engine
              .outputExists(path)) {
        throw StateError('Dosya taşınmış veya silinmiş.');
      }
      final uri = Uri.parse(path);
      final player = uri.scheme == 'content'
          ? VideoPlayerController.contentUri(uri)
          : VideoPlayerController.file(File(path));
      await player.initialize().timeout(const Duration(seconds: 20));
      if (!mounted || generation != _videoGeneration) {
        await player.dispose();
        return;
      }
      _videoPlayer = player;
      await player.play();
      if (mounted) setState(() => _loading = false);
    } catch (error) {
      if (mounted && generation == _videoGeneration) {
        setState(() {
          _error = error is TimeoutException
              ? 'Video 20 saniye içinde hazırlanamadı.'
              : error;
          _loading = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _videoGeneration++;
    _videoPlayer?.dispose();
    _audioErrorSubscription?.cancel();
    // Ses oynatıcı bilerek durdurulmaz; Android medya servisi arka planda sürer.
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          _currentJob.title,
          localize: false,
          overflow: TextOverflow.ellipsis,
        ),
        actions: [
          IconButton(
            tooltip: tr('Harici uygulamada aç'),
            onPressed: _openExternally,
            icon: const Icon(Icons.open_in_new),
          ),
        ],
      ),
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) => SingleChildScrollView(
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: constraints.maxHeight),
              child: Center(
                child: _error != null
                    ? _errorView()
                    : _loading
                    ? _loadingView()
                    : _usesBackgroundAudio
                    ? _audioView(_audioHandler!)
                    : _videoView(_videoPlayer!),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _loadingView() => const Column(
    mainAxisSize: MainAxisSize.min,
    children: [
      CircularProgressIndicator(),
      SizedBox(height: 14),
      Text('Medya hazırlanıyor…'),
    ],
  );

  Widget _videoView(VideoPlayerController player) => Padding(
    padding: const EdgeInsets.all(20),
    child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 560),
          child: AspectRatio(
            aspectRatio: player.value.aspectRatio > 0
                ? player.value.aspectRatio
                : 16 / 9,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: VideoPlayer(player),
            ),
          ),
        ),
        const SizedBox(height: 24),
        Text(
          _currentJob.title,
          localize: false,
          maxLines: 2,
          textAlign: TextAlign.center,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 14),
        VideoProgressIndicator(
          player,
          allowScrubbing: true,
          padding: const EdgeInsets.symmetric(vertical: 8),
        ),
        ValueListenableBuilder<VideoPlayerValue>(
          valueListenable: player,
          builder: (context, value, _) => Column(
            children: [
              Text(
                '${_duration(value.position)} / ${_duration(value.duration)}'
                '  •  ${_videoIndex + 1} / ${_videoQueue.length}',
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    tooltip: tr('Önceki video'),
                    onPressed: _videoIndex > 0
                        ? () => _loadVideo(_videoIndex - 1)
                        : null,
                    icon: const Icon(Icons.skip_previous),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    iconSize: 34,
                    tooltip: tr(value.isPlaying ? 'Duraklat' : 'Oynat'),
                    onPressed: () =>
                        value.isPlaying ? player.pause() : player.play(),
                    icon: Icon(
                      value.isPlaying ? Icons.pause : Icons.play_arrow,
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    tooltip: tr('Sonraki video'),
                    onPressed: _videoIndex + 1 < _videoQueue.length
                        ? () => _loadVideo(_videoIndex + 1)
                        : null,
                    icon: const Icon(Icons.skip_next),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    tooltip: tr('Videoyu durdur'),
                    onPressed: () async {
                      await player.pause();
                      await player.seekTo(Duration.zero);
                    },
                    icon: const Icon(Icons.stop_circle_outlined),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    ),
  );

  Widget _audioView(AppAudioHandler handler) => StreamBuilder<MediaItem?>(
    stream: handler.mediaItem,
    initialData: handler.mediaItem.value,
    builder: (context, itemSnapshot) {
      final item = itemSnapshot.data;
      return StreamBuilder<PlaybackState>(
        stream: handler.playbackState,
        initialData: handler.playbackState.value,
        builder: (context, stateSnapshot) {
          final playback = stateSnapshot.data!;
          final index = handler.currentIndex ?? 0;
          final queueLength = handler.queue.value.length;
          return Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 220,
                  height: 220,
                  clipBehavior: Clip.antiAlias,
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.secondaryContainer,
                    borderRadius: BorderRadius.circular(28),
                  ),
                  child: item?.artUri == null
                      ? Icon(
                          Icons.graphic_eq,
                          size: 96,
                          color: Theme.of(
                            context,
                          ).colorScheme.onSecondaryContainer,
                        )
                      : Image.network(
                          item!.artUri.toString(),
                          fit: BoxFit.cover,
                          errorBuilder: (_, _, _) =>
                              const Icon(Icons.graphic_eq, size: 96),
                        ),
                ),
                const SizedBox(height: 24),
                Text(
                  item?.title ?? _currentJob.title,
                  localize: false,
                  maxLines: 2,
                  textAlign: TextAlign.center,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 4),
                Text('${index + 1} / $queueLength'),
                const SizedBox(height: 14),
                _audioProgress(handler, item?.duration),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    IconButton(
                      tooltip: tr('Önceki müzik'),
                      onPressed: index > 0 ? handler.skipToPrevious : null,
                      icon: const Icon(Icons.skip_previous),
                    ),
                    const SizedBox(width: 8),
                    IconButton.filled(
                      iconSize: 34,
                      tooltip: tr(playback.playing ? 'Duraklat' : 'Oynat'),
                      onPressed: playback.playing
                          ? handler.pause
                          : handler.play,
                      icon: Icon(
                        playback.playing ? Icons.pause : Icons.play_arrow,
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton(
                      tooltip: tr('Sonraki müzik'),
                      onPressed: index + 1 < queueLength
                          ? handler.skipToNext
                          : null,
                      icon: const Icon(Icons.skip_next),
                    ),
                    const SizedBox(width: 8),
                    IconButton(
                      tooltip: tr('Oynatmayı durdur'),
                      onPressed: handler.stop,
                      icon: const Icon(Icons.stop_circle_outlined),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      );
    },
  );

  Widget _audioProgress(AppAudioHandler handler, Duration? duration) =>
      StreamBuilder<Duration>(
        stream: handler.positionStream,
        initialData: Duration.zero,
        builder: (context, snapshot) {
          final total = duration ?? Duration.zero;
          final position = snapshot.data ?? Duration.zero;
          final maximum = total.inMilliseconds > 0
              ? total.inMilliseconds.toDouble()
              : 1.0;
          final value = position.inMilliseconds
              .toDouble()
              .clamp(0, maximum)
              .toDouble();
          return Column(
            children: [
              Slider(
                value: value,
                max: maximum,
                onChanged: total > Duration.zero
                    ? (milliseconds) => handler.seek(
                        Duration(milliseconds: milliseconds.round()),
                      )
                    : null,
              ),
              Text('${_duration(position)} / ${_duration(total)}'),
            ],
          );
        },
      );

  Widget _errorView() => Padding(
    padding: const EdgeInsets.all(24),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(Icons.error_outline, size: 52),
        const SizedBox(height: 12),
        const Text('Dosya uygulama içinde oynatılamadı.'),
        const SizedBox(height: 6),
        Text(
          '$_error',
          maxLines: 4,
          textAlign: TextAlign.center,
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 10,
          runSpacing: 8,
          alignment: WrapAlignment.center,
          children: [
            OutlinedButton.icon(
              onPressed: _retryPlayback,
              icon: const Icon(Icons.refresh),
              label: const Text('Yeniden dene'),
            ),
            FilledButton.icon(
              onPressed: _openExternally,
              icon: const Icon(Icons.open_in_new),
              label: const Text('Harici uygulamada aç'),
            ),
          ],
        ),
      ],
    ),
  );

  Future<void> _openExternally() async {
    try {
      var job = _currentJob;
      if (_usesBackgroundAudio) {
        final currentId = _audioHandler?.mediaItem.value?.id;
        if (currentId != null) {
          for (final candidate in ref.read(appControllerProvider).jobs) {
            if (candidate.id == currentId) {
              job = candidate;
              break;
            }
          }
        }
      }
      await ref.read(appControllerProvider.notifier).openOutput(job);
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Dosya açılamadı: $error')));
    }
  }

  Future<void> _retryPlayback() async {
    setState(() {
      _error = null;
      _loading = true;
      if (_usesBackgroundAudio) _audioHandler = null;
    });
    if (_usesBackgroundAudio) {
      await _initialize();
    } else {
      await _loadVideo(_videoIndex);
    }
  }

  String _duration(Duration value) {
    final minutes = value.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = value.inSeconds.remainder(60).toString().padLeft(2, '0');
    if (value.inHours > 0) return '${value.inHours}:$minutes:$seconds';
    return '$minutes:$seconds';
  }
}
