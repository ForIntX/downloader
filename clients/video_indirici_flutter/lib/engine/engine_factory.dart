import 'dart:io';

import 'download_engine.dart';
import 'platform_download_engine.dart';
import 'windows_process_engine.dart';

DownloadEngine createDownloadEngine() {
  if (Platform.isWindows) return WindowsProcessDownloadEngine();
  return PlatformDownloadEngine();
}
