import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';

import 'core/constants.dart';
import 'providers/app_controller.dart';
import 'screens/history_screen.dart';
import 'screens/home_screen.dart';
import 'screens/queue_screen.dart';
import 'screens/settings_screen.dart';

class VideoIndiriciApp extends ConsumerWidget {
  const VideoIndiriciApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final localeCode = ref.watch(
      appControllerProvider.select((state) => state.localeCode),
    );
    return MaterialApp(
      title: appName,
      debugShowCheckedModeBanner: false,
      locale: Locale(localeCode),
      supportedLocales: const [Locale('tr'), Locale('en')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      themeMode: ThemeMode.system,
      theme: _theme(Brightness.light),
      darkTheme: _theme(Brightness.dark),
      home: const AppShell(),
    );
  }

  ThemeData _theme(Brightness brightness) {
    final scheme = ColorScheme.fromSeed(
      seedColor: const Color(0xff3478f6),
      brightness: brightness,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      cardTheme: CardThemeData(
        margin: EdgeInsets.zero,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
      ),
    );
  }
}

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  var _index = 0;

  static const destinations = <NavigationDestination>[
    NavigationDestination(
      icon: Icon(Icons.download_outlined),
      selectedIcon: Icon(Icons.download),
      label: 'İndir',
    ),
    NavigationDestination(
      icon: Icon(Icons.queue_music_outlined),
      selectedIcon: Icon(Icons.queue_music),
      label: 'Kuyruk',
    ),
    NavigationDestination(
      icon: Icon(Icons.history),
      selectedIcon: Icon(Icons.history_toggle_off),
      label: 'Geçmiş',
    ),
    NavigationDestination(
      icon: Icon(Icons.settings_outlined),
      selectedIcon: Icon(Icons.settings),
      label: 'Ayarlar',
    ),
  ];

  static const screens = <Widget>[
    HomeScreen(),
    QueueScreen(),
    HistoryScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) return;
        final hasActive = ProviderScope.containerOf(
          context,
        ).read(appControllerProvider).hasActiveDownloads;
        if (!hasActive) {
          Navigator.of(context).pop();
          return;
        }
        final leave = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('İndirmeler devam ediyor'),
            content: const Text(
              'Android’de indirmeler bildirim üzerinden arka planda devam eder. Windows’ta çıkarsanız etkin işler iptal edilir ve parça dosyaları korunur.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Uygulamaya dön'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: Text(
                  Platform.isAndroid
                      ? 'Arka planda devam et'
                      : 'İndirmeleri iptal et ve çık',
                ),
              ),
            ],
          ),
        );
        if (leave == true && context.mounted) {
          if (Platform.isAndroid) {
            await SystemNavigator.pop();
          } else {
            await ProviderScope.containerOf(
              context,
            ).read(appControllerProvider.notifier).cancelActiveDownloads();
            if (context.mounted) Navigator.of(context).pop();
          }
        }
      },
      child: LayoutBuilder(
        builder: (context, constraints) {
          final wide = constraints.maxWidth >= 840;
          final content = IndexedStack(index: _index, children: screens);
          return Scaffold(
            appBar: AppBar(
              title: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(appName, style: TextStyle(fontWeight: FontWeight.w700)),
                  Text(
                    appVersion,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.normal,
                    ),
                  ),
                ],
              ),
              centerTitle: !wide,
            ),
            body: wide
                ? Row(
                    children: [
                      NavigationRail(
                        selectedIndex: _index,
                        onDestinationSelected: (value) =>
                            setState(() => _index = value),
                        labelType: NavigationRailLabelType.all,
                        destinations: [
                          for (final destination in destinations)
                            NavigationRailDestination(
                              icon: destination.icon,
                              selectedIcon: destination.selectedIcon,
                              label: Text(destination.label),
                            ),
                        ],
                      ),
                      const VerticalDivider(width: 1),
                      Expanded(child: content),
                    ],
                  )
                : content,
            bottomNavigationBar: wide
                ? null
                : NavigationBar(
                    selectedIndex: _index,
                    onDestinationSelected: (value) =>
                        setState(() => _index = value),
                    destinations: destinations,
                  ),
          );
        },
      ),
    );
  }
}
