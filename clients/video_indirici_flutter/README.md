# Downloader Flutter istemcisi

[Türkçe](README.md) | [English](README.en.md)

Android ve Windows için ortak Flutter arayüzü. Linux GTK uygulaması depo
kökünde ayrı olarak korunur.

## Geliştirme

```bash
flutter pub get
dart analyze lib test
flutter test
```

Android debug APK:

```bash
flutter build apk --debug --target-platform android-arm64,android-x64
```

Android motoru Kotlin, Chaquopy/Python 3.12, yt-dlp, paketlenmiş
QuickJS-NG 0.15.0 ve LGPL FFmpegKit kullanır. QuickJS ikililerini yeniden
üretmek için Android SDK yolu tanımlandıktan sonra:

```bash
ANDROID_SDK_ROOT=/Android/Sdk ./scripts/build_quickjs_android.sh
```

Windows motoru uygulamanın yanındaki `tools` klasöründeki yt-dlp, Deno ve
FFmpeg süreçlerini çalıştırır. Ortak arayüzde özel yt-dlp formatı, hız
sınırı, paralel parça ve dosya adı şablonu; Windows'ta ayrıca tarayıcı
profili ve `cookies.txt` desteği bulunur.

Play imzalama anahtarları ve Windows motor ikili dosyaları Git'e eklenmemelidir.
Android QuickJS ikilileri çevrimdışı ve tekrarlanabilir paketleme için repoda
tutulur; uygulama çalışma zamanında motor güncellemez.
