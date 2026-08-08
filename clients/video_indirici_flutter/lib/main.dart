import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';

import 'app.dart';
import 'l10n/app_localizations.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  LicenseRegistry.addLicense(() async* {
    final asset = tr('Türkçe') == 'Turkish'
        ? 'assets/third_party_licenses.en.txt'
        : 'assets/third_party_licenses.txt';
    yield LicenseEntryWithLineBreaks(const [
      'Downloader third-party components / Üçüncü taraf bileşenleri',
    ], await rootBundle.loadString(asset));
  });
  runApp(const ProviderScope(child: VideoIndiriciApp()));
}
