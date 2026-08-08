# Contributing guide

[English](CONTRIBUTING.en.md) | [Türkçe](CONTRIBUTING.md)

Check existing issues and pull requests before contributing. For substantial
changes, open a feature request before beginning implementation.

## Local checks

For the Linux code:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile app.py video_indirici/*.py
bash -n start.sh install.sh uninstall.sh
```

For the Flutter code:

```bash
cd clients/video_indirici_flutter
flutter pub get
dart analyze lib test
flutter test
```

Do not commit build output, APK/AAB packages, Windows binaries, cookies, signing
keys, passwords, or machine-specific settings.
