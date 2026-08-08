# Katkı rehberi

[Türkçe](CONTRIBUTING.md) | [English](CONTRIBUTING.en.md)

Katkı yapmadan önce mevcut issue ve pull request'leri kontrol edin. Büyük
değişiklikler için uygulamaya geçmeden önce bir özellik isteği açın.

## Yerel kontroller

Linux kodu için:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile app.py video_indirici/*.py
bash -n start.sh install.sh uninstall.sh
```

Flutter kodu için:

```bash
cd clients/video_indirici_flutter
flutter pub get
dart analyze lib test
flutter test
```

Commit'lere derleme çıktısı, APK/AAB, Windows ikili dosyaları, çerez,
imzalama anahtarı veya makineye özel ayarlar eklemeyin.
