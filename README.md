# Downloader

[Türkçe](README.md) | [English](README.en.md)

YouTube ve yt-dlp tarafından desteklenen kaynaklardan video, playlist ve ses
indirmek için Linux, Android ve Windows uygulaması.

Proje sürümü: **1.0.0-beta.2** (`1.0 Beta`)

| Platform | Durum | Teknoloji |
| --- | --- | --- |
| Linux | Kullanılabilir | GTK4 / Libadwaita / Python |
| Android 8+ | Alpha APK hazır | Flutter / Kotlin / Python 3.12 |
| Windows 10+ | Kaynak ve paketleme hazır | Flutter / yt-dlp / FFmpeg |

## Ortak özellikler

- Video: en iyi kalite, 2160p, 1440p, 1080p, 720p ve 480p MP4
- Ses: MP3 128/192/256/320 kbps, M4A ve Opus
- Tek video için küçük resim, kanal, süre, izlenme ve açılır açıklama
- 2.000 girdilik playlist için sanallaştırılmış liste, arama ve toplu seçim
- Kalıcı kuyruk/geçmiş, tekrar URL denetimi, sıralama, duraklatma ve iptal
- Kesin çıktı yolu üzerinden dosyayı açma, paylaşma ve yeniden indirme
- Android’de uygulama içi MP3/MP4 oynatıcı ve indirilen dosya konumları
- Bildirim/kilit ekranından yönetilen, önceki-sonraki parça destekli arka plan müzik kuyruğu
- Müzik/video sekmeli geçmiş, kategori bazlı temizleme ve video oynatma kuyruğu
- Bekleyen işleri anında yeniden zamanlayan yalnız Wi‑Fi ve yalnız şarj ayarları
- Android/Windows için özel yt-dlp formatı, hız sınırı, paralel parça sayısı ve dosya adı şablonu
- Linux için zaman çizgisi, ses, 10 saniye sarma ve önceki/sonraki dosya destekli uygulama içi oynatıcı
- Linux müzik/video geçmiş filtreleri ve kategori bazlı temizleme
- Türkçe ve İngilizce arayüz, koyu tema ve dar/geniş ekran yerleşimi

## Android

Android istemcisi `clients/video_indirici_flutter` dizinindedir. Python 3.12,
yt-dlp `2026.01.29`, yt-dlp-ejs, QuickJS-NG `0.15.0` ve LGPL FFmpegKit
uygulama içinde paketlenir.
İndirmeler Android 14 ve sonrasında kullanıcı başlatmalı aktarım işi,
daha eski sürümlerde foreground service olarak çalışır. Tamamlanan dosya
MediaStore ile `Download/video_indirici/musics` veya
`Download/video_indirici/videos` alanına yazılır. Ayarlar ekranındaki
konum satırları ilgili klasörü doğrudan açar.
Tamamlanan bir işin üç nokta menüsündeki **Dosya konumunu aç**
seçeneği de dosyanın gerçek klasörünü açar.

Debug APK oluşturmak:

```bash
cd clients/video_indirici_flutter
flutter pub get
flutter test
flutter build apk --release --target-platform android-arm64,android-x64
flutter build appbundle --release --target-platform android-arm64,android-x64
```

Doğrudan telefona kurulabilen APK
`clients/video_indirici_flutter/build/app/outputs/flutter-apk/app-release.apk`,
Play Console paketi ise
`clients/video_indirici_flutter/build/app/outputs/bundle/release/app-release.aab`
konumunda oluşur. Kalıcı dağıtım öncesinde kendi upload anahtarınızla
imzalanmalıdır.

Play AAB iş akışı iki GitHub Actions secret'ı bekler:
`ANDROID_KEYSTORE_BASE64` ve tam `key.properties` içeriğini taşıyan
`ANDROID_KEY_PROPERTIES`. Anahtarlar veya parolalar Git'e eklenmez.

> Android uygulamasının YouTube indirme işlevi Google Play ve YouTube
> politikaları nedeniyle mağaza reddi veya hesap yaptırımı riski taşır.

## Windows

Windows istemcisi aynı Flutter arayüzünü kullanır. Windows iş akışı
`yt-dlp.exe`, Deno ve FFmpeg araçlarını indirir; ardından hem taşınabilir
ZIP hem Inno Setup kurulum dosyası oluşturur. İş akışı yalnızca elle
başlatılır ve otomatik release/push yapmaz.
Firefox, Chrome, Edge ve Brave profilleri ile elle belirtilen `cookies.txt`
dosyası desteklenir; çerez içeriği veritabanına veya loglara yazılmaz.

Yerel Windows derlemesi:

```powershell
cd clients\video_indirici_flutter
flutter pub get
flutter test
flutter build windows --release
```

Gerekli motor dosyaları `windows/tools` altına konulmalıdır; ayrıntılar o
klasördeki README'dedir.

## Linux kurulumu

Debian/Ubuntu, Fedora ve Arch tabanlı sistemlerde:

```bash
chmod +x start.sh install.sh uninstall.sh
./install.sh --check
./install.sh
```

Sonraki çalıştırmalarda uygulama menüsündeki **Downloader** simgesine
tıklanabilir. Kurmadan kaynak koddan çalıştırmak için `./start.sh`
kullanılır.

Tamamlanan bir indirmedeki oynat düğmesi dosyayı uygulama içinde açar.
Boşluk oynatır/duraklatır, sol/sağ ok 10 saniye sarar,
`Ctrl+Sol/Sağ` ise geçmişteki aynı tür dosyalar arasında geçiş yapar.

Kaldırma varsayılan olarak kullanıcı verilerini korur:

```bash
./uninstall.sh
./uninstall.sh --purge
```

## Testler

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile app.py video_indirici/*.py
bash -n start.sh install.sh uninstall.sh

cd clients/video_indirici_flutter
dart analyze lib test
flutter test
```

Gizlilik ve Play Store hazırlık belgelerinin Türkçe ve İngilizce
sürümleri `docs/` altındadır.

Website: [muhammetburakakkas.com](https://muhammetburakakkas.com)

Uygulama kaynak kodu [MIT Lisansı](LICENSE) ile sunulur. Paketlenmiş üçüncü
taraf araçlar kendi lisanslarına tabidir.
