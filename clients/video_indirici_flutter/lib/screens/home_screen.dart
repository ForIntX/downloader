import 'dart:async';

import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/download_models.dart';
import '../core/constants.dart';
import '../l10n/app_localizations.dart';
import '../l10n/localized_material.dart';
import '../providers/app_controller.dart';
import '../widgets/marquee_text.dart';
import '../widgets/video_info_card.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  final _urlController = TextEditingController();
  var _playlistMode = false;
  StreamSubscription<Object?>? _shareSubscription;

  @override
  void initState() {
    super.initState();
    _shareSubscription = const EventChannel(shareEventChannel)
        .receiveBroadcastStream()
        .listen((value) {
          if (value is String && mounted) _urlController.text = value;
        }, onError: (_) {});
  }

  @override
  void dispose() {
    _shareSubscription?.cancel();
    _urlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    ref.listen<String?>(appControllerProvider.select((state) => state.error), (
      previous,
      next,
    ) {
      if (next != null && next != previous) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(next), showCloseIcon: true));
      }
    });
    final state = ref.watch(appControllerProvider);
    final controller = ref.read(appControllerProvider.notifier);
    if (!state.initialized) {
      return const Center(child: CircularProgressIndicator());
    }
    return CustomScrollView(
      slivers: [
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          sliver: SliverToBoxAdapter(
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1100),
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Video veya playlist URL\'si',
                          style: Theme.of(context).textTheme.titleMedium
                              ?.copyWith(fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 10),
                        LayoutBuilder(
                          builder: (context, constraints) {
                            if (constraints.maxWidth < 620) {
                              return Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  _urlField(controller, pasteInside: true),
                                  const SizedBox(height: 10),
                                  _informationButton(state, controller),
                                ],
                              );
                            }
                            return Row(
                              children: [
                                Expanded(child: _urlField(controller)),
                                const SizedBox(width: 8),
                                IconButton.filledTonal(
                                  tooltip: tr('Panodan yapıştır'),
                                  onPressed: _pasteUrl,
                                  icon: const Icon(Icons.content_paste),
                                ),
                                const SizedBox(width: 8),
                                _informationButton(state, controller),
                              ],
                            );
                          },
                        ),
                        const SizedBox(height: 10),
                        Row(
                          children: [
                            SegmentedButton<bool>(
                              segments: const [
                                ButtonSegment(
                                  value: false,
                                  label: Text('Video'),
                                  icon: Icon(Icons.movie_outlined),
                                ),
                                ButtonSegment(
                                  value: true,
                                  label: Text('Playlist'),
                                  icon: Icon(Icons.playlist_play),
                                ),
                              ],
                              selected: {_playlistMode},
                              onSelectionChanged: (value) =>
                                  setState(() => _playlistMode = value.first),
                            ),
                            const Spacer(),
                            if (state.scanning)
                              OutlinedButton.icon(
                                onPressed: controller.stopScan,
                                icon: const Icon(Icons.stop),
                                label: const Text('Taramayı durdur'),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
        if (state.video != null)
          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            sliver: SliverToBoxAdapter(
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1100),
                  child: VideoInfoCard(video: state.video!),
                ),
              ),
            ),
          ),
        if (state.playlist.isNotEmpty) ...[
          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            sliver: SliverToBoxAdapter(
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1100),
                  child: Column(
                    children: [
                      TextField(
                        onChanged: controller.setFilter,
                        decoration: InputDecoration(
                          hintText: tr(
                            '${state.playlist.length} video içinde ara',
                          ),
                          prefixIcon: const Icon(Icons.search),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          OutlinedButton(
                            onPressed: () => controller.selectAll(true),
                            child: const Text('Tümünü seç'),
                          ),
                          OutlinedButton(
                            onPressed: controller.selectVisible,
                            child: const Text('Görünenleri seç'),
                          ),
                          OutlinedButton(
                            onPressed: () => controller.selectAll(false),
                            child: const Text('Seçimi kaldır'),
                          ),
                          Text(
                            '${state.playlist.where((item) => item.selected).length} seçili',
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            sliver: SliverList.builder(
              itemCount: state.visiblePlaylist.length,
              itemBuilder: (context, index) {
                final item = state.visiblePlaylist[index];
                return Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 1100),
                    child: CheckboxListTile(
                      key: ValueKey(item.id),
                      value: item.selected,
                      enabled: item.available,
                      onChanged: (value) => controller.togglePlaylistEntry(
                        item.id,
                        value ?? false,
                      ),
                      title: MarqueeText(
                        item.title,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      subtitle: Text(
                        item.channel ?? item.url,
                        localize: false,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      secondary: item.thumbnailUrl == null
                          ? const Icon(Icons.movie_outlined)
                          : ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: Image.network(
                                item.thumbnailUrl!,
                                width: 86,
                                height: 52,
                                fit: BoxFit.cover,
                                errorBuilder: (_, _, _) =>
                                    const Icon(Icons.broken_image_outlined),
                              ),
                            ),
                    ),
                  ),
                );
              },
            ),
          ),
        ],
        if (state.video != null || state.playlist.isNotEmpty)
          SliverPadding(
            padding: const EdgeInsets.all(16),
            sliver: SliverToBoxAdapter(
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1100),
                  child: Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: DropdownButtonFormField<String>(
                                  initialValue: state.presetId,
                                  decoration: InputDecoration(
                                    labelText: tr('Format ve kalite'),
                                  ),
                                  items: [
                                    for (final preset in DownloadPreset.presets)
                                      DropdownMenuItem(
                                        value: preset.id,
                                        child: Text(preset.label),
                                      ),
                                  ],
                                  onChanged: (value) {
                                    if (value != null) {
                                      controller.setPreset(value);
                                    }
                                  },
                                ),
                              ),
                              const SizedBox(width: 12),
                              FilledButton.icon(
                                onPressed: state.scanning
                                    ? null
                                    : () => _enqueue(context, controller),
                                icon: const Icon(Icons.download),
                                label: const Text('İndir'),
                              ),
                            ],
                          ),
                          if (state.presetId == 'custom') ...[
                            const SizedBox(height: 12),
                            TextFormField(
                              key: const ValueKey('custom-format-field'),
                              initialValue: state.customFormat,
                              onChanged: controller.setCustomFormat,
                              decoration: InputDecoration(
                                labelText: tr('Özel yt-dlp formatı'),
                                hintText: tr(
                                  'Örn. 137+140 veya best[height<=1080]',
                                ),
                                helperText: tr(
                                  'Gelişmiş kullanıcılar için doğrudan format seçicisi.',
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        const SliverPadding(padding: EdgeInsets.only(bottom: 40)),
      ],
    );
  }

  Widget _urlField(AppController controller, {bool pasteInside = false}) =>
      TextField(
        controller: _urlController,
        keyboardType: TextInputType.url,
        textInputAction: TextInputAction.go,
        onSubmitted: (_) => controller.getInformation(
          _urlController.text,
          playlist: _playlistMode,
        ),
        decoration: InputDecoration(
          hintText: 'https://...',
          prefixIcon: const Icon(Icons.link),
          suffixIcon: pasteInside
              ? IconButton(
                  tooltip: tr('Panodan yapıştır'),
                  onPressed: _pasteUrl,
                  icon: const Icon(Icons.content_paste),
                )
              : null,
        ),
      );

  Widget _informationButton(AppState state, AppController controller) =>
      FilledButton.icon(
        onPressed: state.busy
            ? null
            : () => controller.getInformation(
                _urlController.text,
                playlist: _playlistMode,
              ),
        icon: state.busy
            ? const SizedBox.square(
                dimension: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Icon(Icons.travel_explore),
        label: const Text('Bilgi getir'),
      );

  Future<void> _pasteUrl() async {
    final data = await Clipboard.getData(Clipboard.kTextPlain);
    if (data?.text != null) _urlController.text = data!.text!;
  }

  Future<void> _enqueue(BuildContext context, AppController controller) async {
    var result = await controller.enqueueCurrent();
    if (!context.mounted) return;
    if (result.redownloadable > 0) {
      final approved = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Daha önce indirilmiş'),
          content: Text(
            '${result.redownloadable} öğe kuyrukta veya geçmişte zaten bulunuyor. Yeniden indirmek ister misiniz?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Atla'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Yeniden indir'),
            ),
          ],
        ),
      );
      if (approved == true) {
        final repeated = await controller.enqueueCurrent(
          redownloadDuplicates: true,
        );
        result = EnqueueResult(
          added: result.added + repeated.added,
          skipped: repeated.skipped,
        );
      }
    }
    if (!context.mounted) return;
    final message = result.added > 0
        ? '${result.added} öğe kuyruğa eklendi${result.skipped == 0 ? '' : ', ${result.skipped} etkin tekrar atlandı'}'
        : result.redownloadable > 0
        ? 'Öğe yeniden indirilmedi.'
        : 'Bu öğe zaten kuyrukta veya indiriliyor.';
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }
}
