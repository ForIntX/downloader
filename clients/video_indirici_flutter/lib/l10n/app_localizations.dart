import 'package:flutter/widgets.dart';

String _currentLanguage = 'tr';

void setAppLanguage(String languageCode) {
  _currentLanguage = languageCode == 'en' ? 'en' : 'tr';
}

String tr(String value) {
  if (_currentLanguage != 'en') return value;
  final exact = _english[value];
  if (exact != null) return exact;

  final ytDlpExit = RegExp(
    r'^yt-dlp (\d+) koduyla kapandı\.$',
  ).firstMatch(value);
  if (ytDlpExit != null) {
    return 'yt-dlp exited with code ${ytDlpExit.group(1)}.';
  }

  RegExpMatch? match;
  match = RegExp(r'^(\d+) geçmiş kaydı silindi\.$').firstMatch(value);
  if (match != null) return '${match.group(1)} history records deleted.';
  match = RegExp(
    r'^(\d+) öğe kuyruğa eklendi(?:, (\d+) etkin tekrar atlandı)?$',
  ).firstMatch(value);
  if (match != null) {
    final result = '${match.group(1)} items added to the queue';
    return result +
        (match.group(2) == null
            ? ''
            : ', ${match.group(2)} active duplicates skipped');
  }
  match = RegExp(r'^(\d+) video içinde ara$').firstMatch(value);
  if (match != null) return '${match.group(1)} videos';
  match = RegExp(r'^(\d+) seçili$').firstMatch(value);
  if (match != null) return '${match.group(1)} selected';
  match = RegExp(r'^(\d+) etkin tekrar atlandı$').firstMatch(value);
  if (match != null) return '${match.group(1)} active duplicates skipped';
  match = RegExp(r'^Tümü \((\d+)\)$').firstMatch(value);
  if (match != null) return 'All (${match.group(1)})';
  match = RegExp(r'^Müzikler \((\d+)\)$').firstMatch(value);
  if (match != null) return 'Music (${match.group(1)})';
  match = RegExp(r'^Videolar \((\d+)\)$').firstMatch(value);
  if (match != null) return 'Videos (${match.group(1)})';
  const clearQuestions = <String, String>{
    'Müzik silinsin mi?': 'Clear music history?',
    'Video silinsin mi?': 'Clear video history?',
    'Tüm geçmiş silinsin mi?': 'Clear all history?',
  };
  final clearQuestion = clearQuestions[value];
  if (clearQuestion != null) return clearQuestion;
  match = RegExp(
    r'^(\d+) öğe kuyrukta veya geçmişte zaten bulunuyor\. Yeniden indirmek ister misiniz\?$',
  ).firstMatch(value);
  if (match != null) {
    return '${match.group(1)} items are already in the queue or history. '
        'Would you like to download them again?';
  }
  for (final category in const ['Müzikler', 'Videolar']) {
    final englishCategory = _english[category]!;
    if (value == '$category klasörünü aç') {
      return 'Open $englishCategory folder';
    }
    if (value == '$category klasörünü açmak için dokun.') {
      return 'Tap to open the $englishCategory folder.';
    }
    if (value.startsWith('$category klasörü açılamadı: ')) {
      return '$englishCategory folder could not be opened: '
          '${value.substring('$category klasörü açılamadı: '.length)}';
    }
  }
  const locationSuffix = '\nKlasörü açmak için dokun.';
  if (value.endsWith(locationSuffix)) {
    return '${value.substring(0, value.length - locationSuffix.length)}'
        '\nTap to open the folder.';
  }
  const errorPrefixes = <String, String>{
    'Dosya açılamadı: ': 'The file could not be opened: ',
    'Dosya konumu açılamadı: ': 'The file location could not be opened: ',
    'Veriler açılamadı: ': 'Data could not be opened: ',
  };
  for (final prefix in errorPrefixes.entries) {
    if (value.startsWith(prefix.key)) {
      return '${prefix.value}${value.substring(prefix.key.length)}';
    }
  }
  return value;
}

extension LocalizedBuildContext on BuildContext {
  String tr(String value) => appText(value);
}

String appText(String value) => tr(value);

const _english = <String, String>{
  'Ayarlar': 'Settings',
  'Açık kaynak lisansları': 'Open-source licenses',
  'Açıklama': 'Description',
  'Android oturum desteği': 'Android session support',
  'Android’de indirmeler bildirim üzerinden arka planda devam eder. Windows’ta çıkarsanız etkin işler iptal edilir ve parça dosyaları korunur.':
      'On Android, downloads continue in the background through notifications. On Windows, exiting cancels active jobs and preserves partial files.',
  'Arka planda devam et': 'Continue in background',
  'Atla': 'Skip',
  'Başlık bulunamadı': 'Title unavailable',
  'Bekliyor': 'Pending',
  'Bilgi getir': 'Get information',
  'Bir video veya playlist URL\'si girin.': 'Enter a video or playlist URL.',
  'Bu kategoriyi temizle': 'Clear this category',
  'Bu öğe zaten kuyrukta veya indiriliyor.':
      'This item is already queued or downloading.',
  'Daha önce indirilmiş': 'Previously downloaded',
  'Devam et': 'Resume',
  'Dil ve erişilebilirlik': 'Language and accessibility',
  'Dosya adı şablonu': 'Filename template',
  'Dosya adı şablonu geçersiz.': 'The filename template is invalid.',
  'Dosya açılamadı.': 'The file could not be opened.',
  'Dosya bulunamadı': 'File not found',
  'Dosya konumu': 'File location',
  'Dosya konumu açılamadı.': 'The file location could not be opened.',
  'Dosya konumu bulunamadı.': 'The file location could not be found.',
  'Dosya konumunu aç': 'Open file location',
  'Dosya taşınmış veya silinmiş.': 'The file was moved or deleted.',
  'Dosya taşınmış veya silinmiş. Yeniden indirmek ister misiniz?':
      'The file was moved or deleted. Would you like to download it again?',
  'Dosya uygulama içinde oynatılamadı.':
      'The file could not be played inside the app.',
  'Duraklat': 'Pause',
  'Duraklatıldı': 'Paused',
  'Dönüştürülüyor': 'Processing',
  'En iyi MP4': 'Best MP4',
  'English (yakında)': 'English',
  'Eşzamanlı indirme': 'Concurrent downloads',
  'Format ve kalite': 'Format and quality',
  'Gelişmiş indirme': 'Advanced downloads',
  'Gelişmiş kullanıcılar için doğrudan format seçicisi.':
      'Direct format selector for advanced users.',
  'Geçmiş': 'History',
  'Geçmiş henüz boş.': 'History is empty.',
  'Geçmiş kayıtları silinir; indirilen medya dosyaları telefonda kalır.':
      'History records are deleted; downloaded media stays on the device.',
  'Geçmiş silinsin mi?': 'Clear history?',
  'Geçmişi temizle': 'Clear history',
  'Geçmişten sil': 'Remove from history',
  'Görünenleri seç': 'Select visible',
  'Hakkında': 'About',
  'Hangi geçmiş silinsin?': 'Which history should be cleared?',
  'Harici uygulamada aç': 'Open in external app',
  'Hata': 'Error',
  'Hata ayrıntısı': 'Error details',
  'Hazırlanıyor': 'Preparing',
  'Henüz indirilmiş bir müzik yok.': 'No downloaded music yet.',
  'Henüz indirilmiş bir video yok.': 'No downloaded videos yet.',
  'Hız sınırı': 'Speed limit',
  'Kanal bilinmiyor': 'Unknown channel',
  'Kapat': 'Close',
  'Kişisel verileri ve geçmişi temizle': 'Clear personal data and history',
  'Klasör açılamadı.': 'The folder could not be opened.',
  'Konum bulunamadı': 'Location unavailable',
  'Konumlar okunuyor…': 'Loading locations…',
  'Kopyala': 'Copy',
  'Kuyruk': 'Queue',
  'Kuyruk boş': 'The queue is empty',
  'Kuyruk, geçmiş ve ayarlar silinir. İndirilen medya dosyaları silinmez.':
      'The queue, history, and settings will be deleted. Downloaded media files will remain.',
  'Listeden kaldır': 'Remove from list',
  'Medya hazırlanıyor…': 'Preparing media…',
  'Motor bilgilerini kopyala': 'Copy engine diagnostics',
  'Müzik oynatma': 'Music playback',
  'Müzik oynatılamadı.': 'The music could not be played.',
  'Müzik servisi başlatılamadı.': 'The music service could not be started.',
  'Müzikler': 'Music',
  'Müziği çal': 'Play music',
  'Oturum gerektiren içerikler için tarayıcı profilini veya cookies.txt dosyasını kullanın.':
      'Use a browser profile or cookies.txt for content that requires a session.',
  'Oynat': 'Play',
  'Oynatmayı durdur': 'Stop playback',
  'Oynatılabilir müzik bulunamadı.': 'No playable music was found.',
  'Panodan yapıştır': 'Paste from clipboard',
  'Paralel indirme parçaları': 'Concurrent fragments',
  'Paylaş': 'Share',
  'Profil (isteğe bağlı)': 'Profile (optional)',
  'Playlist taranamadı.': 'The playlist could not be scanned.',
  'cookies.txt dosya yolu': 'cookies.txt file path',
  'C:\\Users\\kullanici\\Downloads\\cookies.txt':
      r'C:\Users\user\Downloads\cookies.txt',
  'Seçilen cookies.txt dosyası bulunamadı.':
      'The selected cookies.txt file could not be found.',
  'Seçilen müzik bulunamadı.': 'The selected music could not be found.',
  'Seçimi kaldır': 'Clear selection',
  'Sil': 'Delete',
  'Sınırsız': 'Unlimited',
  'Sonraki müzik': 'Next track',
  'Sonraki video': 'Next video',
  'Tamamlandı': 'Completed',
  'Tanılama': 'Diagnostics',
  'Tanılama bilgileri kopyalandı.': 'Diagnostics copied.',
  'Taramayı durdur': 'Stop scanning',
  'Tarayıcı': 'Browser',
  'Tarayıcı profili': 'Browser profile',
  'Temizle': 'Clear',
  'Tüm geçmişi temizle': 'Clear all history',
  'Tüm indirme geçmişi': 'All download history',
  'Tüm kayıtları veya yalnızca müzik/video geçmişini sil.':
      'Delete all records or only music/video history.',
  'Tümünü seç': 'Select all',
  'Tümü': 'All',
  'Türkçe': 'Turkish',
  'Uygulamada oynat': 'Play in app',
  'Uygulamaya dön': 'Return to app',
  'Vazgeç': 'Cancel',
  'Veriler temizlensin mi?': 'Clear data?',
  'Video 20 saniye içinde hazırlanamadı.':
      'The video could not be prepared within 20 seconds.',
  'Video bilgisi alınamadı.': 'Video information could not be retrieved.',
  'Video veya playlist URL\'si': 'Video or playlist URL',
  'Videolar': 'Videos',
  'Videoyu durdur': 'Stop video',
  'Videoyu oynat': 'Play video',
  'Windows çerezleri': 'Windows cookies',
  'Yalnız Wi‑Fi ile indir': 'Download on Wi-Fi only',
  'Yalnız şarjdayken indir': 'Download only while charging',
  'Yalnızca geçmiş kayıtları kaldırılır. Telefona indirilen müzik ve video dosyaları silinmez.':
      'Only history records will be removed. Downloaded music and video files will remain.',
  'Yalnızca müzikler': 'Music only',
  'Yalnızca videolar': 'Videos only',
  'Yeni işler cihaz şarja bağlanana kadar bekler.':
      'New jobs wait until the device is charging.',
  'Yeni işler ölçülmeyen Wi‑Fi bağlantısını bekler.':
      'New jobs wait for an unmetered Wi-Fi connection.',
  'Yeniden dene': 'Retry',
  'Yeniden indir': 'Download again',
  'Yok': 'None',
  'Çerez yöntemi': 'Cookie method',
  'Önceki müzik': 'Previous track',
  'Önceki video': 'Previous video',
  'Örn. 137+140 veya best[height<=1080]':
      'Example: 137+140 or best[height<=1080]',
  'Örn. Default': 'Example: Default',
  'Özel yt-dlp formatı': 'Custom yt-dlp format',
  'Özel yt-dlp formatı boş bırakılamaz.':
      'The custom yt-dlp format cannot be empty.',
  'Öğe yeniden indirilmedi.': 'The item was not downloaded again.',
  'İlk sürümde kapalı. cookies.txt desteği 3.1.0 sürümünde eklenecek.':
      'Disabled in the first release. cookies.txt support is planned for version 3.1.0.',
  'İndir': 'Download',
  'İndirilen müzikler': 'Downloaded music',
  'İndirilen müziklerin arka planda oynatma kontrolleri':
      'Background playback controls for downloaded music',
  'İndirilenler klasörü bulunamadı.':
      'The Downloads folder could not be found.',
  'İndiriliyor': 'Downloading',
  'İndirme': 'Download',
  'İndirme geçmişini temizle': 'Clear download history',
  'İndirme hatası': 'Download error',
  'İndirmeler devam ediyor': 'Downloads are still running',
  'İndirmeleri iptal et ve çık': 'Cancel downloads and exit',
  'İptal edildi': 'Cancelled',
  'İptal et': 'Cancel',
  'İşlemler': 'Actions',
  '%(title)s, %(id)s ve %(ext)s alanlarını kullanabilirsiniz.':
      'You can use the %(title)s, %(id)s, and %(ext)s fields.',
  '256 KB/sn': '256 KB/s',
  '512 KB/sn': '512 KB/s',
  '1 MB/sn': '1 MB/s',
  '2 MB/sn': '2 MB/s',
  '5 MB/sn': '5 MB/s',
  '10 MB/sn': '10 MB/s',
};
