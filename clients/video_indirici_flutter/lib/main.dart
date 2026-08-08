import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';

import 'app.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  LicenseRegistry.addLicense(() async* {
    yield LicenseEntryWithLineBreaks(const [
      'Downloader üçüncü taraf bileşenleri',
    ], await rootBundle.loadString('assets/third_party_licenses.txt'));
  });
  runApp(const ProviderScope(child: VideoIndiriciApp()));
}
