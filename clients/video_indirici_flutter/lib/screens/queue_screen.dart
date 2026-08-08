import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../l10n/localized_material.dart';
import '../providers/app_controller.dart';
import '../widgets/job_tile.dart';

class QueueScreen extends ConsumerWidget {
  const QueueScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final queue = ref.watch(
      appControllerProvider.select((state) => state.queue),
    );
    final controller = ref.read(appControllerProvider.notifier);
    if (queue.isEmpty) {
      return const _Empty(icon: Icons.queue_music, text: 'Kuyruk boş');
    }
    return ReorderableListView.builder(
      padding: const EdgeInsets.all(16),
      buildDefaultDragHandles: false,
      itemCount: queue.length,
      onReorderItem: controller.reorder,
      itemBuilder: (context, index) {
        final job = queue[index];
        return Padding(
          key: ValueKey(job.id),
          padding: const EdgeInsets.only(bottom: 8),
          child: JobTile(
            job: job,
            dragHandle: job.status.isActive
                ? const Icon(Icons.lock_outline, size: 20)
                : ReorderableDragStartListener(
                    index: index,
                    child: const Icon(Icons.drag_handle),
                  ),
          ),
        );
      },
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Center(
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 64, color: Theme.of(context).colorScheme.outline),
        const SizedBox(height: 12),
        Text(text, style: Theme.of(context).textTheme.titleMedium),
      ],
    ),
  );
}
