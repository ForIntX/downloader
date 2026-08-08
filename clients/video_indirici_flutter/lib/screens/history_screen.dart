import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../l10n/app_localizations.dart';
import '../l10n/localized_material.dart';
import '../models/download_models.dart';
import '../providers/app_controller.dart';
import '../widgets/job_tile.dart';

class HistoryScreen extends ConsumerStatefulWidget {
  const HistoryScreen({super.key});

  @override
  ConsumerState<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends ConsumerState<HistoryScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this)..addListener(_refreshTab);
  }

  @override
  void dispose() {
    _tabs
      ..removeListener(_refreshTab)
      ..dispose();
    super.dispose();
  }

  void _refreshTab() {
    if (!_tabs.indexIsChanging && mounted) setState(() {});
  }

  MediaKind? get _selectedKind => switch (_tabs.index) {
    1 => MediaKind.audio,
    2 => MediaKind.video,
    _ => null,
  };

  String get _selectedLabel => switch (_tabs.index) {
    1 => 'müzik',
    2 => 'video',
    _ => 'geçmiş',
  };

  @override
  Widget build(BuildContext context) {
    final history = ref.watch(
      appControllerProvider.select((state) => state.history),
    );
    final audio = history
        .where((job) => job.preset.kind == MediaKind.audio)
        .toList(growable: false);
    final video = history
        .where((job) => job.preset.kind == MediaKind.video)
        .toList(growable: false);
    final selectedCount = switch (_tabs.index) {
      1 => audio.length,
      2 => video.length,
      _ => history.length,
    };

    return Column(
      children: [
        Material(
          color: Theme.of(context).colorScheme.surface,
          child: Column(
            children: [
              Row(
                children: [
                  Expanded(
                    child: TabBar(
                      controller: _tabs,
                      isScrollable: true,
                      tabAlignment: TabAlignment.start,
                      tabs: [
                        Tab(text: tr('Tümü (${history.length})')),
                        Tab(
                          icon: const Icon(Icons.audiotrack, size: 20),
                          text: tr('Müzikler (${audio.length})'),
                        ),
                        Tab(
                          icon: const Icon(Icons.movie_outlined, size: 20),
                          text: tr('Videolar (${video.length})'),
                        ),
                      ],
                    ),
                  ),
                  PopupMenuButton<String>(
                    tooltip: tr('Geçmişi temizle'),
                    enabled: history.isNotEmpty,
                    onSelected: (value) => _confirmClear(
                      value == 'all' ? null : _selectedKind,
                      all: value == 'all',
                    ),
                    itemBuilder: (context) => [
                      PopupMenuItem(
                        value: 'selected',
                        enabled: selectedCount > 0,
                        child: Text(
                          _tabs.index == 0
                              ? 'Tüm geçmişi temizle'
                              : 'Bu kategoriyi temizle',
                        ),
                      ),
                      if (_tabs.index != 0)
                        const PopupMenuItem(
                          value: 'all',
                          child: Text('Tüm geçmişi temizle'),
                        ),
                    ],
                    icon: const Icon(Icons.delete_sweep_outlined),
                  ),
                  const SizedBox(width: 8),
                ],
              ),
              const Divider(height: 1),
            ],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _tabs,
            children: [
              _HistoryList(items: history, emptyText: 'Geçmiş henüz boş.'),
              _HistoryList(
                items: audio,
                emptyText: 'Henüz indirilmiş bir müzik yok.',
              ),
              _HistoryList(
                items: video,
                emptyText: 'Henüz indirilmiş bir video yok.',
              ),
            ],
          ),
        ),
      ],
    );
  }

  Future<void> _confirmClear(MediaKind? kind, {required bool all}) async {
    final label = all ? 'tüm geçmiş' : _selectedLabel;
    final approved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          '${label[0].toUpperCase()}${label.substring(1)} silinsin mi?',
        ),
        content: const Text(
          'Yalnızca geçmiş kayıtları kaldırılır. Telefona indirilen müzik ve video dosyaları silinmez.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Vazgeç'),
          ),
          FilledButton.icon(
            onPressed: () => Navigator.pop(context, true),
            icon: const Icon(Icons.delete_outline),
            label: const Text('Geçmişten sil'),
          ),
        ],
      ),
    );
    if (approved != true) return;
    final removed = await ref
        .read(appControllerProvider.notifier)
        .clearHistory(kind: all ? null : kind);
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('$removed geçmiş kaydı silindi.')));
  }
}

class _HistoryList extends StatelessWidget {
  const _HistoryList({required this.items, required this.emptyText});

  final List<DownloadJob> items;
  final String emptyText;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(emptyText, textAlign: TextAlign.center),
        ),
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: items.length,
      separatorBuilder: (_, _) => const SizedBox(height: 8),
      itemBuilder: (context, index) => JobTile(job: items[index]),
    );
  }
}
