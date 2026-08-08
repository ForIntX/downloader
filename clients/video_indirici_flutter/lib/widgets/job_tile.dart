import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';

import '../models/download_models.dart';
import '../providers/app_controller.dart';
import '../screens/media_player_screen.dart';
import 'marquee_text.dart';

class JobTile extends ConsumerWidget {
  const JobTile({required this.job, this.dragHandle, super.key});

  final DownloadJob job;
  final Widget? dragHandle;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final controller = ref.read(appControllerProvider.notifier);
    final scheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            if (dragHandle != null) ...[dragHandle!, const SizedBox(width: 8)],
            if (job.thumbnailUrl != null)
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.network(
                  job.thumbnailUrl!,
                  width: 82,
                  height: 52,
                  fit: BoxFit.cover,
                  errorBuilder: (_, _, _) => const SizedBox.shrink(),
                ),
              ),
            if (job.thumbnailUrl != null) const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  MarqueeText(
                    job.title,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${job.preset.label} • ${_status(job.status)}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  if (job.status.isActive ||
                      job.status == DownloadStatus.paused) ...[
                    const SizedBox(height: 8),
                    LinearProgressIndicator(
                      value: job.progress <= 0 ? null : job.progress / 100,
                    ),
                    const SizedBox(height: 3),
                    Text(
                      '${job.progress.toStringAsFixed(1)}%${job.speed == null ? '' : ' • ${job.speed}'}',
                      style: Theme.of(context).textTheme.labelSmall,
                    ),
                  ],
                  if (job.error != null) ...[
                    const SizedBox(height: 5),
                    Text(
                      job.error!,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: scheme.error, fontSize: 12),
                    ),
                    TextButton.icon(
                      onPressed: () => _showErrorDetails(context),
                      icon: const Icon(Icons.info_outline, size: 16),
                      label: const Text('Hata ayrıntısı'),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: 8),
            if (job.status == DownloadStatus.completed)
              IconButton.filledTonal(
                tooltip: job.preset.kind == MediaKind.video
                    ? 'Videoyu oynat'
                    : 'Müziği çal',
                onPressed: () => _playInside(context, controller),
                icon: Icon(
                  job.preset.kind == MediaKind.video
                      ? Icons.play_arrow
                      : Icons.headphones,
                ),
              ),
            PopupMenuButton<String>(
              tooltip: 'İşlemler',
              onSelected: (value) async {
                switch (value) {
                  case 'pause':
                    await controller.pause(job);
                  case 'resume':
                    await controller.resume(job);
                  case 'cancel':
                    await controller.cancel(job);
                  case 'retry':
                    await controller.retry(job);
                  case 'play_inside':
                    await _playInside(context, controller);
                  case 'open_external':
                    await _openExternalOrOffer(context, controller);
                  case 'open_location':
                    await _openLocationOrOffer(context, controller);
                  case 'share':
                    await controller.shareOutput(job);
                  case 'remove':
                    await controller.remove(job);
                }
              },
              itemBuilder: (context) => [
                if (job.status.isActive)
                  const PopupMenuItem(value: 'pause', child: Text('Duraklat')),
                if (job.status == DownloadStatus.paused)
                  const PopupMenuItem(value: 'resume', child: Text('Devam et')),
                if (job.status.isActive ||
                    job.status == DownloadStatus.pending ||
                    job.status == DownloadStatus.paused)
                  const PopupMenuItem(value: 'cancel', child: Text('İptal et')),
                if (job.status == DownloadStatus.failed ||
                    job.status == DownloadStatus.cancelled)
                  const PopupMenuItem(
                    value: 'retry',
                    child: Text('Yeniden dene'),
                  ),
                if (job.status == DownloadStatus.completed) ...[
                  const PopupMenuItem(
                    value: 'play_inside',
                    child: Text('Uygulamada oynat'),
                  ),
                  const PopupMenuItem(
                    value: 'open_external',
                    child: Text('Harici uygulamada aç'),
                  ),
                  const PopupMenuItem(
                    value: 'open_location',
                    child: Text('Dosya konumunu aç'),
                  ),
                  const PopupMenuItem(value: 'share', child: Text('Paylaş')),
                ],
                const PopupMenuDivider(),
                const PopupMenuItem(
                  value: 'remove',
                  child: Text('Listeden kaldır'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _offerRedownload(
    BuildContext context,
    AppController controller,
  ) async {
    final retry = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Dosya bulunamadı'),
        content: const Text(
          'Dosya taşınmış veya silinmiş. Yeniden indirmek ister misiniz?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Vazgeç'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Yeniden indir'),
          ),
        ],
      ),
    );
    if (retry == true) await controller.retry(job);
  }

  Future<void> _playInside(
    BuildContext context,
    AppController controller,
  ) async {
    final path = job.outputPath;
    if (path == null || !await controller.engine.outputExists(path)) {
      if (context.mounted) await _offerRedownload(context, controller);
      return;
    }
    if (!context.mounted) return;
    await Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => MediaPlayerScreen(job: job)),
    );
  }

  Future<void> _openExternalOrOffer(
    BuildContext context,
    AppController controller,
  ) async {
    try {
      final opened = await controller.openOutput(job);
      if (!opened && context.mounted) {
        await _offerRedownload(context, controller);
      }
    } catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Dosya açılamadı: $error'), showCloseIcon: true),
      );
    }
  }

  Future<void> _openLocationOrOffer(
    BuildContext context,
    AppController controller,
  ) async {
    try {
      final opened = await controller.openOutputLocation(job);
      if (!opened && context.mounted) {
        await _offerRedownload(context, controller);
      }
    } catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Dosya konumu açılamadı: $error'),
          showCloseIcon: true,
        ),
      );
    }
  }

  Future<void> _showErrorDetails(BuildContext context) async {
    final error = job.error;
    if (error == null) return;
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('İndirme hatası'),
        content: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: SingleChildScrollView(child: SelectableText(error)),
        ),
        actions: [
          TextButton.icon(
            onPressed: () async {
              await Clipboard.setData(ClipboardData(text: error));
              if (context.mounted) Navigator.pop(context);
            },
            icon: const Icon(Icons.copy),
            label: const Text('Kopyala'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Kapat'),
          ),
        ],
      ),
    );
  }

  String _status(DownloadStatus value) => switch (value) {
    DownloadStatus.pending => 'Bekliyor',
    DownloadStatus.preparing => 'Hazırlanıyor',
    DownloadStatus.downloading => 'İndiriliyor',
    DownloadStatus.processing => 'Dönüştürülüyor',
    DownloadStatus.paused => 'Duraklatıldı',
    DownloadStatus.completed => 'Tamamlandı',
    DownloadStatus.failed => 'Hata',
    DownloadStatus.cancelled => 'İptal edildi',
  };
}
