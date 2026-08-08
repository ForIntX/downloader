import 'package:flutter/material.dart';

import '../models/download_models.dart';

class VideoInfoCard extends StatelessWidget {
  const VideoInfoCard({required this.video, super.key});

  final VideoMetadata video;

  String _duration(int? value) {
    if (value == null) return '—';
    final duration = Duration(seconds: value);
    final minutes = duration.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = duration.inSeconds.remainder(60).toString().padLeft(2, '0');
    return duration.inHours > 0
        ? '${duration.inHours}:$minutes:$seconds'
        : '$minutes:$seconds';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final wide = constraints.maxWidth > 680;
            final image = video.thumbnailUrl == null
                ? const AspectRatio(
                    aspectRatio: 16 / 9,
                    child: ColoredBox(color: Colors.black12),
                  )
                : AspectRatio(
                    aspectRatio: 16 / 9,
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Image.network(
                        video.thumbnailUrl!,
                        fit: BoxFit.cover,
                        errorBuilder: (_, _, _) =>
                            const ColoredBox(color: Colors.black12),
                      ),
                    ),
                  );
            final details = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  video.title,
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  video.channel ?? 'Kanal bilinmiyor',
                  style: theme.textTheme.bodyMedium,
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 14,
                  runSpacing: 6,
                  children: [
                    _Fact(
                      icon: Icons.schedule,
                      text: _duration(video.durationSeconds),
                    ),
                    if (video.viewCount != null)
                      _Fact(
                        icon: Icons.visibility_outlined,
                        text: '${video.viewCount}',
                      ),
                    if (video.width != null && video.height != null)
                      _Fact(
                        icon: Icons.high_quality_outlined,
                        text: '${video.width}×${video.height}',
                      ),
                    if (video.uploadDate != null)
                      _Fact(
                        icon: Icons.calendar_today_outlined,
                        text: video.uploadDate!,
                      ),
                  ],
                ),
                if (video.description?.trim().isNotEmpty ?? false) ...[
                  const SizedBox(height: 8),
                  ExpansionTile(
                    tilePadding: EdgeInsets.zero,
                    childrenPadding: const EdgeInsets.only(bottom: 8),
                    title: const Text('Açıklama'),
                    children: [
                      SelectableText(
                        video.description!,
                        style: theme.textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ],
              ],
            );
            if (!wide) {
              return Column(
                children: [image, const SizedBox(height: 14), details],
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(width: 320, child: image),
                const SizedBox(width: 16),
                Expanded(child: details),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _Fact extends StatelessWidget {
  const _Fact({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [Icon(icon, size: 16), const SizedBox(width: 5), Text(text)],
  );
}
