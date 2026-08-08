# 1.0 Beta yayın kontrol listesi

[Türkçe](release-checklist.md) | [English](release-checklist-en.md)

## Android

- Fiziksel ARM64 cihazda tek video MP4 ve MP3 indirme
- 2.000 girdilik playlist tarama, durdurma ve kuyruk testi
- Ekran kapalıyken, uygulama arka plandayken ve süreç sonlandırıldığında devam
- Android 12, 13, 14, 15 ve 16 emülatör testleri
- Kalıcı Play upload anahtarı ve GitHub Actions secret'ları
- Play Console gizlilik politikası, veri güvenliği ve içerik derecelendirmesi
- yt-dlp, EJS ve JavaScript runtime gerçek YouTube testi
- Özel format, hız sınırı, paralel parça ve dosya adı şablonu testi

## Windows

- Windows CI'da release derlemesi, taşınabilir ZIP ve Inno Setup
- yt-dlp, Deno, FFmpeg ve FFprobe sürüm/lisans doğrulaması
- Özel format, hız sınırı, paralel parça ve dosya adı şablonu testi
- Chrome, Edge, Firefox ve Brave çerez seçenekleri
- SmartScreen uyarısını kaldırmak için isteğe bağlı kod imzalama sertifikası

## Linux

- GTK dahili MP3/MP4 oynatıcı ve harici uygulama geri dönüşü
- Müzik/video geçmiş filtreleri ve kategori bazlı temizleme
- GStreamer codec paketleriyle MP3, M4A, Opus ve MP4 oynatma

`Publish platform release` iş akışı yalnızca elle başlatıldığında GitHub
Release oluşturur. Hiçbir iş akışı mağazaya otomatik yükleme yapmaz.
