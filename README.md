# Downloader

[English](README.md) | [Türkçe](README.tr.md)

A Linux, Android, and Windows application for downloading video, playlists,
and audio from YouTube and other sources supported by yt-dlp.

Project version: **1.0.0-beta.3** (`1.0 Beta`)

| Platform | Status | Technology |
| --- | --- | --- |
| Linux | Available | GTK4 / Libadwaita / Python |
| Android 8+ | Alpha APK ready | Flutter / Kotlin / Python 3.12 |
| Windows 10+ | Source and packaging ready | Flutter / yt-dlp / FFmpeg |

## Shared features

- Video: best quality, 2160p, 1440p, 1080p, 720p, and 480p MP4
- Audio: MP3 at 128/192/256/320 kbps, M4A, and Opus
- Thumbnail, channel, duration, view count, and collapsible description for a single video
- Virtualized list, search, and bulk selection for playlists with 2,000 entries
- Persistent queue/history, duplicate URL checks, reordering, pause, and cancel
- Open, share, or download again using the exact output file path
- In-app MP3/MP4 player and download locations on Android
- Background music queue with previous/next controls in notifications and on the lock screen
- Music/video history tabs, category-based cleanup, and a video playback queue
- Wi-Fi-only and charging-only settings that immediately reschedule pending jobs
- Custom yt-dlp format, speed limit, concurrent fragments, and filename templates on Android/Windows
- Linux in-app player with timeline, volume, 10-second seek, and previous/next file controls
- Linux music/video history filters and category-based cleanup
- Turkish and English interface, dark theme, and narrow/wide layouts

## Android

The Android client is in `clients/video_indirici_flutter`. Python 3.12,
yt-dlp `2026.01.29`, yt-dlp-ejs, QuickJS-NG `0.15.0`, and an LGPL FFmpegKit
build are bundled with the application.

Downloads run as a user-initiated data transfer job on Android 14 and newer,
and as a foreground service on older versions. Completed files are written
through MediaStore to `Download/video_indirici/musics` or
`Download/video_indirici/videos`. Location rows in Settings open their folders
directly. **Open file location** in a completed job's overflow menu opens the
actual containing folder.

Build installable packages:

```bash
cd clients/video_indirici_flutter
flutter pub get
flutter test
flutter build apk --release --target-platform android-arm64,android-x64
flutter build appbundle --release --target-platform android-arm64,android-x64
```

The installable APK is created at
`clients/video_indirici_flutter/build/app/outputs/flutter-apk/app-release.apk`;
the Play Console bundle is created at
`clients/video_indirici_flutter/build/app/outputs/bundle/release/app-release.aab`.
Use your own upload key before permanent distribution.

The Play AAB workflow expects two GitHub Actions secrets:
`ANDROID_KEYSTORE_BASE64` and `ANDROID_KEY_PROPERTIES`, containing the complete
`key.properties` file. Keys and passwords must never be committed.

> YouTube downloading functionality may lead to store rejection or account
> action under Google Play and YouTube policies.

For the easiest installation, download the `Android.apk` file from
[GitHub Releases](https://github.com/ForIntX/downloader/releases), open it on
the phone, and approve installation from the browser/file manager when Android
asks. The `Android.aab` file is only for Play Console and cannot be installed
directly.

## Windows

The Windows client uses the same Flutter interface. Its workflow downloads
`yt-dlp.exe`, Deno, and LGPL FFmpeg, then creates both a portable ZIP and an
Inno Setup installer. Run **Windows packages** manually on the Actions page to
test the Windows package.

Firefox, Chrome, Edge, and Brave profiles and a manually selected `cookies.txt`
file are supported. Cookie contents are not written to the database or logs.

Local Windows build:

```powershell
cd clients\video_indirici_flutter
flutter pub get
flutter test
flutter build windows --release
```

Engine binaries must be placed under `windows/tools`; see the README in that
directory for details.

Most users should download `Windows-Setup.exe` from
[GitHub Releases](https://github.com/ForIntX/downloader/releases) and follow
the installer. The portable ZIP is provided for users who do not want an
installation. Until the executable is code-signed, Windows may display a
SmartScreen warning.

## Linux installation

On Debian/Ubuntu, download the `Linux.deb` file from
[GitHub Releases](https://github.com/ForIntX/downloader/releases) and open it
with the system software installer. After installation, launch **Downloader**
from the application menu.

For Fedora, Arch, and other supported systems, extract `Linux.tar.gz` and run:

```bash
chmod +x start.sh install.sh uninstall.sh
./install.sh --check
./install.sh
```

For later launches, select **Downloader** from the application menu. Use
`./start.sh` to run directly from the source tree without installing.

The play button on a completed download opens it inside the application. Space
plays/pauses, Left/Right seeks by 10 seconds, and `Ctrl+Left/Right` switches
between history files of the same type.

Uninstalling preserves user data by default:

```bash
./uninstall.sh
./uninstall.sh --purge
```

## Tests

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile app.py video_indirici/*.py
bash -n start.sh install.sh uninstall.sh

cd clients/video_indirici_flutter
dart analyze lib test
flutter test
```

Turkish and English privacy and Play Store preparation documents are under
`docs/`.

Pushing a version tag automatically builds the Linux, Android, and Windows
packages and publishes them under one GitHub Release. The same workflow can
also be started manually from GitHub Actions.

Website: [muhammetburakakkas.com](https://muhammetburakakkas.com)

Application source is provided under the [MIT License](LICENSE). Bundled
third-party tools remain subject to their own licenses.
