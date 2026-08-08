# Downloader Flutter client

[English](README.en.md) | [Türkçe](README.md)

A shared Flutter interface for Android and Windows. The Linux GTK application
is maintained separately at the repository root.

## Development

```bash
flutter pub get
dart analyze lib test
flutter test
```

Android debug APK:

```bash
flutter build apk --debug --target-platform android-arm64,android-x64
```

The Android engine uses Kotlin, Chaquopy/Python 3.12, yt-dlp, bundled
QuickJS-NG 0.15.0, and an LGPL FFmpegKit build. To rebuild the QuickJS binaries
after configuring the Android SDK path:

```bash
ANDROID_SDK_ROOT=/Android/Sdk ./scripts/build_quickjs_android.sh
```

The Windows engine runs yt-dlp, Deno, and FFmpeg processes from the `tools`
directory beside the application. The shared interface supports a custom
yt-dlp format, speed limit, concurrent fragments, and filename template;
Windows also supports browser profiles and `cookies.txt`.

Play signing keys and Windows engine binaries must not be committed. Android
QuickJS binaries are kept in the repository for offline, reproducible
packaging; the application does not update its engine at runtime.
