import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/constants.dart';
import '../l10n/app_localizations.dart';
import '../l10n/localized_material.dart';
import '../models/download_models.dart';
import '../providers/app_controller.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(appControllerProvider);
    final controller = ref.read(appControllerProvider.notifier);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _Section(
          title: 'İndirme',
          children: [
            if (Platform.isAndroid) ...[
              SwitchListTile(
                title: const Text('Yalnız Wi‑Fi ile indir'),
                subtitle: const Text(
                  'Yeni işler ölçülmeyen Wi‑Fi bağlantısını bekler.',
                ),
                value: state.wifiOnly,
                onChanged: controller.setWifiOnly,
              ),
              SwitchListTile(
                title: const Text('Yalnız şarjdayken indir'),
                subtitle: const Text(
                  'Yeni işler cihaz şarja bağlanana kadar bekler.',
                ),
                value: state.chargingOnly,
                onChanged: controller.setChargingOnly,
              ),
            ],
            ListTile(
              title: const Text('Eşzamanlı indirme'),
              subtitle: Slider(
                value: state.concurrentDownloads.toDouble(),
                min: 1,
                max: 3,
                divisions: 2,
                label: '${state.concurrentDownloads}',
                onChanged: (value) =>
                    controller.setConcurrentDownloads(value.round()),
              ),
              trailing: Text('${state.concurrentDownloads}'),
            ),
            if (Platform.isAndroid)
              const ListTile(
                title: Text('Android oturum desteği'),
                subtitle: Text(
                  'İlk sürümde kapalı. cookies.txt desteği 3.1.0 sürümünde eklenecek.',
                ),
                enabled: false,
              ),
          ],
        ),
        const SizedBox(height: 12),
        _Section(
          title: 'Gelişmiş indirme',
          children: [
            DropdownButtonFormField<String>(
              initialValue: state.speedLimit,
              decoration: InputDecoration(
                labelText: tr('Hız sınırı'),
                prefixIcon: const Icon(Icons.speed),
              ),
              items: const [
                DropdownMenuItem(value: '', child: Text('Sınırsız')),
                DropdownMenuItem(value: '256K', child: Text('256 KB/sn')),
                DropdownMenuItem(value: '512K', child: Text('512 KB/sn')),
                DropdownMenuItem(value: '1M', child: Text('1 MB/sn')),
                DropdownMenuItem(value: '2M', child: Text('2 MB/sn')),
                DropdownMenuItem(value: '5M', child: Text('5 MB/sn')),
                DropdownMenuItem(value: '10M', child: Text('10 MB/sn')),
              ],
              onChanged: (value) => controller.setSpeedLimit(value ?? ''),
            ),
            ListTile(
              title: const Text('Paralel indirme parçaları'),
              subtitle: Slider(
                value: state.concurrentFragments.toDouble(),
                min: 1,
                max: 8,
                divisions: 7,
                label: '${state.concurrentFragments}',
                onChanged: (value) =>
                    controller.setConcurrentFragments(value.round()),
              ),
              trailing: Text('${state.concurrentFragments}'),
            ),
            TextFormField(
              key: const ValueKey('filename-template-setting'),
              initialValue: state.filenameTemplate,
              onChanged: controller.setFilenameTemplate,
              decoration: InputDecoration(
                labelText: tr('Dosya adı şablonu'),
                prefixIcon: const Icon(Icons.drive_file_rename_outline),
                helperText: tr(
                  '%(title)s, %(id)s ve %(ext)s alanlarını kullanabilirsiniz.',
                ),
              ),
            ),
            if (Platform.isWindows) ...[
              const Divider(height: 28),
              const ListTile(
                leading: Icon(Icons.cookie_outlined),
                title: Text('Windows çerezleri'),
                subtitle: Text(
                  'Oturum gerektiren içerikler için tarayıcı profilini veya cookies.txt dosyasını kullanın.',
                ),
              ),
              DropdownButtonFormField<String>(
                initialValue: state.cookieMode,
                decoration: InputDecoration(labelText: tr('Çerez yöntemi')),
                items: const [
                  DropdownMenuItem(value: 'none', child: Text('Yok')),
                  DropdownMenuItem(
                    value: 'browser',
                    child: Text('Tarayıcı profili'),
                  ),
                  DropdownMenuItem(value: 'file', child: Text('cookies.txt')),
                ],
                onChanged: (value) => controller.setCookieMode(value ?? 'none'),
              ),
              if (state.cookieMode == 'browser') ...[
                const SizedBox(height: 10),
                DropdownButtonFormField<String>(
                  initialValue: state.cookieBrowser,
                  decoration: InputDecoration(labelText: tr('Tarayıcı')),
                  items: const [
                    DropdownMenuItem(value: 'firefox', child: Text('Firefox')),
                    DropdownMenuItem(value: 'chrome', child: Text('Chrome')),
                    DropdownMenuItem(value: 'edge', child: Text('Edge')),
                    DropdownMenuItem(value: 'brave', child: Text('Brave')),
                  ],
                  onChanged: (value) {
                    if (value != null) controller.setCookieBrowser(value);
                  },
                ),
                const SizedBox(height: 10),
                TextFormField(
                  key: const ValueKey('cookie-profile-setting'),
                  initialValue: state.cookieProfile,
                  onChanged: controller.setCookieProfile,
                  decoration: InputDecoration(
                    labelText: tr('Profil (isteğe bağlı)'),
                    hintText: tr('Örn. Default'),
                  ),
                ),
              ],
              if (state.cookieMode == 'file') ...[
                const SizedBox(height: 10),
                TextFormField(
                  key: const ValueKey('cookie-file-setting'),
                  initialValue: state.cookieFile,
                  onChanged: controller.setCookieFile,
                  decoration: InputDecoration(
                    labelText: tr('cookies.txt dosya yolu'),
                    hintText: tr(r'C:\Users\kullanici\Downloads\cookies.txt'),
                  ),
                ),
              ],
            ],
          ],
        ),
        const SizedBox(height: 12),
        _Section(
          title: 'Dosya konumu',
          children: [
            FutureBuilder<Map<String, String>>(
              future: controller.engine.downloadLocations(),
              builder: (context, snapshot) {
                if (!snapshot.hasData) {
                  return const ListTile(
                    leading: Icon(Icons.folder_outlined),
                    title: Text('Konumlar okunuyor…'),
                  );
                }
                final locations = snapshot.data!;
                return Column(
                  children: [
                    _LocationTile(
                      icon: Icons.movie_outlined,
                      title: 'Videolar',
                      path: locations['video'] ?? 'Konum bulunamadı',
                      onOpen: () =>
                          controller.engine.openDownloadLocation('video'),
                    ),
                    _LocationTile(
                      icon: Icons.audiotrack_outlined,
                      title: 'Müzikler',
                      path: locations['audio'] ?? 'Konum bulunamadı',
                      onOpen: () =>
                          controller.engine.openDownloadLocation('audio'),
                    ),
                  ],
                );
              },
            ),
          ],
        ),
        const SizedBox(height: 12),
        _Section(
          title: 'Dil ve erişilebilirlik',
          children: [
            RadioGroup<String>(
              groupValue: state.localeCode,
              onChanged: (value) {
                if (value != null) controller.setLocale(value);
              },
              child: const Column(
                children: [
                  RadioListTile(value: 'tr', title: Text('Türkçe')),
                  RadioListTile(value: 'en', title: Text('English')),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        _Section(
          title: 'Tanılama',
          children: [
            ListTile(
              leading: const Icon(Icons.health_and_safety_outlined),
              title: const Text('Motor bilgilerini kopyala'),
              onTap: () async {
                final diagnostics = await controller.engine.diagnostics();
                await Clipboard.setData(
                  ClipboardData(
                    text: diagnostics.entries
                        .map((entry) => '${entry.key}: ${entry.value}')
                        .join('\n'),
                  ),
                );
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Tanılama bilgileri kopyalandı.'),
                    ),
                  );
                }
              },
            ),
            ListTile(
              leading: const Icon(Icons.history_toggle_off),
              title: const Text('İndirme geçmişini temizle'),
              subtitle: const Text(
                'Tüm kayıtları veya yalnızca müzik/video geçmişini sil.',
              ),
              onTap: () => _clearHistory(context, controller),
            ),
            ListTile(
              leading: const Icon(Icons.delete_sweep_outlined),
              title: const Text('Kişisel verileri ve geçmişi temizle'),
              onTap: () => _clearData(context, controller),
            ),
          ],
        ),
        const SizedBox(height: 12),
        _Section(
          title: 'Hakkında',
          children: [
            const ListTile(
              title: Text(appName),
              subtitle: Text(appVersion),
              leading: Icon(Icons.download_for_offline_outlined),
            ),
            ListTile(
              leading: const Icon(Icons.language),
              title: const Text('muhammetburakakkas.com'),
              onTap: () => launchUrl(
                Uri.parse(appWebsite),
                mode: LaunchMode.externalApplication,
              ),
            ),
            ListTile(
              leading: const Icon(Icons.description_outlined),
              title: const Text('Açık kaynak lisansları'),
              onTap: () => showLicensePage(
                context: context,
                applicationName: appName,
                applicationVersion: appVersion,
                applicationLegalese: 'MIT © 2026 Muhammet Burak Akkaş',
              ),
            ),
          ],
        ),
        const SizedBox(height: 30),
      ],
    );
  }

  Future<void> _clearData(
    BuildContext context,
    AppController controller,
  ) async {
    final approved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Veriler temizlensin mi?'),
        content: const Text(
          'Kuyruk, geçmiş ve ayarlar silinir. İndirilen medya dosyaları silinmez.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Vazgeç'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Temizle'),
          ),
        ],
      ),
    );
    if (approved == true) await controller.clearPersonalData();
  }

  Future<void> _clearHistory(
    BuildContext context,
    AppController controller,
  ) async {
    final selection = await showDialog<String>(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('Hangi geçmiş silinsin?'),
        children: [
          SimpleDialogOption(
            onPressed: () => Navigator.pop(context, 'audio'),
            child: const ListTile(
              leading: Icon(Icons.audiotrack),
              title: Text('Yalnızca müzikler'),
            ),
          ),
          SimpleDialogOption(
            onPressed: () => Navigator.pop(context, 'video'),
            child: const ListTile(
              leading: Icon(Icons.movie_outlined),
              title: Text('Yalnızca videolar'),
            ),
          ),
          SimpleDialogOption(
            onPressed: () => Navigator.pop(context, 'all'),
            child: const ListTile(
              leading: Icon(Icons.delete_sweep_outlined),
              title: Text('Tüm indirme geçmişi'),
            ),
          ),
        ],
      ),
    );
    if (selection == null || !context.mounted) return;
    final approved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Geçmiş silinsin mi?'),
        content: const Text(
          'Geçmiş kayıtları silinir; indirilen medya dosyaları telefonda kalır.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Vazgeç'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Sil'),
          ),
        ],
      ),
    );
    if (approved != true) return;
    final kind = switch (selection) {
      'audio' => MediaKind.audio,
      'video' => MediaKind.video,
      _ => null,
    };
    final count = await controller.clearHistory(kind: kind);
    if (context.mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('$count geçmiş kaydı silindi.')));
    }
  }
}

class _LocationTile extends StatelessWidget {
  const _LocationTile({
    required this.icon,
    required this.title,
    required this.path,
    required this.onOpen,
  });

  final IconData icon;
  final String title;
  final String path;
  final Future<void> Function() onOpen;

  @override
  Widget build(BuildContext context) => ListTile(
    leading: Icon(icon),
    title: Text(title),
    subtitle: Text('$path\nKlasörü açmak için dokun.'),
    isThreeLine: true,
    onTap: () => _open(context),
    trailing: IconButton(
      tooltip: tr('$title klasörünü aç'),
      onPressed: () => _open(context),
      icon: const Icon(Icons.folder_open_outlined),
    ),
  );

  Future<void> _open(BuildContext context) async {
    try {
      await onOpen();
    } catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('$title klasörü açılamadı: $error'),
          showCloseIcon: true,
        ),
      );
    }
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.children});
  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
            child: Text(
              title,
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
          ),
          ...children,
        ],
      ),
    ),
  );
}
