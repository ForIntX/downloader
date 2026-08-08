# 1.0 Beta release checklist

[English](release-checklist-en.md) | [Türkçe](release-checklist.md)

## Android

- MP4 and MP3 single-video downloads on a physical ARM64 device
- Scan, stop, and queue tests for a playlist with 2,000 entries
- Resume with the screen off, the application in the background, and the process terminated
- Android 12, 13, 14, 15, and 16 emulator tests
- Permanent Play upload key and GitHub Actions secrets
- Play Console privacy policy, data safety, and content rating
- Real YouTube tests for yt-dlp, EJS, and the JavaScript runtime
- Custom format, speed limit, concurrent fragments, and filename template tests
- Turkish/English language switching and native notification text

## Windows

- Release build, portable ZIP, and Inno Setup package in Windows CI
- yt-dlp, Deno, FFmpeg, and FFprobe version/license verification
- Custom format, speed limit, concurrent fragments, and filename template tests
- Chrome, Edge, Firefox, and Brave cookie options
- Optional code-signing certificate to remove SmartScreen warnings
- Turkish/English language switching

## Linux

- GTK in-app MP3/MP4 player and external-application fallback
- Music/video history filters and category-based cleanup
- MP3, M4A, Opus, and MP4 playback using GStreamer codec packages
- Turkish/English language switching, including settings and dialogs

No workflow creates a GitHub release or automatically uploads to a store.
