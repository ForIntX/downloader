from __future__ import annotations

import re
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


_language = "tr"


def set_language(language: str) -> None:
    global _language
    _language = "en" if language == "en" else "tr"


def get_language() -> str:
    return _language


_ENGLISH = {
    "Ayarlar": "Settings",
    "yt-dlp güncelle": "Update yt-dlp",
    "Log klasörünü aç": "Open log folder",
    "Log Klasörünü Aç": "Open Log Folder",
    "Hakkında": "About",
    "İndir": "Download",
    "↓ İndir": "↓ Download",
    "↓ Videoyu İndir": "↓ Download Video",
    "Kuyruk": "Queue",
    "Geçmiş": "History",
    "Video veya playlist URL'si": "Video or playlist URL",
    "Yapıştır": "Paste",
    "Bilgi Getir": "Get Information",
    "URL girip bilgi getirin": "Enter a URL and get information",
    "Video": "Video",
    "Playlist": "Playlist",
    "Bilgiler alınıyor…": "Loading information…",
    "Oynatma Listesi": "Playlist",
    "Taramayı Durdur": "Stop Scanning",
    "Video URL'sini girip Bilgi Getir'e basın": "Enter a video URL and select Get Information",
    "Video bilgisi alınamadı": "Video information could not be retrieved",
    "Video bilgisi bekleniyor": "Waiting for video information",
    "Bilinmeyen video": "Unknown video",
    "Bilinmeyen kanal": "Unknown channel",
    "Bilinmeyen kaynak": "Unknown source",
    "Bilinmiyor": "Unknown",
    "Açıklamayı Göster": "Show Description",
    "Açıklamayı Gizle": "Hide Description",
    "Açıklama bulunmuyor.": "No description available.",
    "Kapak resmi yükleniyor…": "Loading thumbnail…",
    "Kapak resmi bulunamadı": "Thumbnail not found",
    "Kapak resmi yüklenemedi": "Thumbnail could not be loaded",
    "Playlist içinde ara…": "Search within playlist…",
    "Tümünü Seç": "Select All",
    "Filtredekileri Seç": "Select Filtered",
    "Seçimi Kaldır": "Clear Selection",
    "Playlistteki bütün videoları seçer": "Selects every video in the playlist",
    "Arama sonucunda şu anda görünen videoları seçer": "Selects videos currently visible in the search results",
    "Playlistteki bütün seçimleri kaldırır": "Clears all playlist selections",
    "Özel yt-dlp format ifadesi": "Custom yt-dlp format expression",
    "Gelişmiş format alanına bir yt-dlp format ifadesi girin.": "Enter a yt-dlp format expression in the advanced format field.",
    "Bekleyenleri Başlat": "Start Pending",
    "Tamamlananları Temizle": "Clear Completed",
    "Tümünü Temizle": "Clear All",
    "Kuyruk boş": "The queue is empty",
    "Kuyruk temizlensin mi?": "Clear the queue?",
    "Aktif indirmeler iptal edilecek.": "Active downloads will be cancelled.",
    "Geçmiş boş": "History is empty",
    "Tümü": "All",
    "Müzikler": "Music",
    "Videolar": "Videos",
    "Geçmişi Temizle": "Clear History",
    "Geçmiş temizlensin mi?": "Clear history?",
    "Tüm geçmiş kayıtları silinir; indirilen dosyalar silinmez.": "All history records will be deleted; downloaded files will remain.",
    "Müzik geçmiş kayıtları silinir; indirilen dosyalar silinmez.": "Music history records will be deleted; downloaded files will remain.",
    "Video geçmiş kayıtları silinir; indirilen dosyalar silinmez.": "Video history records will be deleted; downloaded files will remain.",
    "geçmiş kayıtları silinir; indirilen dosyalar silinmez.": "history records will be deleted; downloaded files will remain.",
    "Vazgeç": "Cancel",
    "Temizle": "Clear",
    "Bekliyor": "Pending",
    "İndiriliyor": "Downloading",
    "Duraklatıldı": "Paused",
    "Tamamlandı": "Completed",
    "Hata": "Error",
    "İptal": "Cancelled",
    "Duraklat": "Pause",
    "Devam Et": "Resume",
    "Duraklat / Devam": "Pause / Resume",
    "Kaldır": "Remove",
    "Yukarı taşı": "Move up",
    "Aşağı taşı": "Move down",
    "Dosyayı oynat": "Play file",
    "Klasörü aç": "Open folder",
    "Tekrar indir": "Download again",
    "Yeniden İndir": "Download Again",
    "Dosya bulunamadı": "File not found",
    "Dosya taşınmış veya silinmiş olabilir. Yeniden indirmek ister misiniz?": "The file may have been moved or deleted. Would you like to download it again?",
    "Dosya açılamadı": "File could not be opened",
    "Klasör açılamadı": "Folder could not be opened",
    "Bilgi alınamadı": "Information could not be retrieved",
    "Bilinmeyen hata": "Unknown error",
    "Kapat": "Close",
    "İndirme hatası": "Download error",
    "İşlem başarısız": "Operation failed",
    "Hata ayrıntısı": "Error details",
    "Ayrıntıyı Kopyala": "Copy Details",
    "İndirme grubu tamamlandı": "Download batch completed",
    "Ayarlar kaydedildi": "Settings saved",
    "Panoda desteklenen bir video bağlantısı bulundu": "A supported video URL was found on the clipboard",
    "yt-dlp güncelleniyor…": "Updating yt-dlp…",
    "yt-dlp güncellendi": "yt-dlp updated",
    "yt-dlp güncellenemedi": "yt-dlp could not be updated",
    "GTK4 / Libadwaita tabanlı yt-dlp video ve playlist indirici.": "A yt-dlp video and playlist downloader built with GTK4 / Libadwaita.",
    "Uygulama dili": "Application language",
    "Türkçe": "Turkish",
    "İngilizce": "English",
    "İndirme klasörü": "Download folder",
    "Gözat": "Browse",
    "Eş zamanlı indirme": "Concurrent downloads",
    "Paralel parçalar": "Concurrent fragments",
    "Hız sınırı": "Speed limit",
    "Sınırsız": "Unlimited",
    "Varsayılan format": "Default format",
    "En iyi MP4": "Best MP4",
    "Özel yt-dlp formatı": "Custom yt-dlp format",
    "Örn. 137+140": "Example: 137+140",
    "Format eksik": "Missing format",
    "Gelişmiş / özel format": "Advanced / custom format",
    "Dosya adı şablonu": "Filename template",
    "Playlist dosya şablonu": "Playlist filename template",
    "Bildirim göster": "Show notifications",
    "Grup bitince klasörü aç": "Open folder when batch finishes",
    "Pano bağlantılarını algıla": "Detect clipboard links",
    "Küçük resmi indir": "Download thumbnail",
    "Metadata göm": "Embed metadata",
    "Bölümleri göm": "Embed chapters",
    "Playlist için klasör oluştur": "Create a folder for playlists",
    "Altyazı indir": "Download subtitles",
    "Otomatik altyazı": "Automatic subtitles",
    "Altyazıyı videoya göm": "Embed subtitles into video",
    "Altyazı dili": "Subtitle language",
    "Almanca": "German",
    "Fransızca": "French",
    "İspanyolca": "Spanish",
    "Japonca": "Japanese",
    "Çerez yöntemi": "Cookie method",
    "Yok": "None",
    "Tarayıcı": "Browser",
    "Tarayıcı profili": "Browser profile",
    "İsteğe bağlı profil": "Optional profile",
    "Seç": "Choose",
    "Varsayılanlara Dön": "Restore Defaults",
    "Kaydet": "Save",
    "İndirme klasörü seç": "Choose download folder",
    "cookies.txt seç": "Choose cookies.txt",
    "Eksik ayar": "Missing setting",
    "Klasör ve dosya adı şablonları boş bırakılamaz.": "Folder and filename templates cannot be empty.",
    "Klasöre yazma izni yok": "The folder is not writable",
    "Klasör kullanılamıyor": "Folder cannot be used",
    "Çerez dosyası bulunamadı": "Cookie file not found",
    "cookies.txt seçilmedi": "No cookies.txt file selected",
    "İndirmeler devam ediyor": "Downloads are still running",
    "İndirmeleri iptal edip uygulamadan çıkmak ister misiniz?": "Would you like to cancel downloads and exit the application?",
    "İndirmeleri İptal Et ve Çık": "Cancel Downloads and Exit",
    "Uygulamaya Dön": "Return to Application",
    "Desteklenen bir video veya playlist bağlantısı girin.": "Enter a supported video or playlist URL.",
    "Geçersiz URL": "Invalid URL",
    "Eklenecek yeni bağlantı yok": "No new links to add",
    "Tekrarlanan bağlantılar bulundu": "Duplicate links found",
    "Tekrarları Atla": "Skip Duplicates",
    "bağlantı kuyrukta veya geçmişte mevcut. Varsayılan olarak atlanacak.": "links already exist in the queue or history and will be skipped by default.",
    "Eksik bağımlılık": "Missing dependency",
    "Bulunamayan araçlar:": "Missing tools:",
    "Kurulumu yeniden çalıştırın.": "Run the installer again.",
    "Harici Uygulamada Aç": "Open in External Application",
    "Dosyayı sistemin varsayılan uygulamasında aç": "Open the file in the system default application",
    "Oynatılacak dosya bulunamadı": "No file available to play",
    "Dosya bulunamadı. Taşınmış veya silinmiş olabilir.": "The file was not found. It may have been moved or deleted.",
    "Önceki dosya": "Previous file",
    "Sonraki dosya": "Next file",
    "10 saniye geri": "Back 10 seconds",
    "10 saniye ileri": "Forward 10 seconds",
    "Oynat / duraklat": "Play / pause",
    "Oynat": "Play",
    "Sesi kapat": "Mute",
    "Sesi aç": "Unmute",
    "Tarama durduruldu": "Scan stopped",
    "video bulundu": "videos found",
    "Kanal:": "Channel:",
    "Kaynak:": "Source:",
    "Platform:": "Platform:",
}


def tr(value: str) -> str:
    if _language != "en" or not value:
        return value
    translated = _ENGLISH.get(value)
    if translated is not None:
        return translated
    match = re.fullmatch(r"(\d+) indirme tamamlandı(?:, (\d+) hata)?", value)
    if match:
        result = f"{match.group(1)} downloads completed"
        return result + (f", {match.group(2)} failed" if match.group(2) else "")
    patterns = (
        (r"^(\d+) aktif / (\d+) toplam$", r"\1 active / \2 total"),
        (r"^(\d+) kayıt$", r"\1 records"),
        (r"^(\d+) gösteriliyor / (\d+) toplam$", r"\1 shown / \2 total"),
        (r"^Kuyruk \((\d+)\)$", r"Queue (\1)"),
        (r"^↓ Seçilenleri İndir \((\d+)\)$", r"↓ Download Selected (\1)"),
        (r"^Tarama durduruldu · (\d+) video bulundu$", r"Scan stopped · \1 videos found"),
        (r"^(.+) · (\d+) video bulundu…$", r"\1 · \2 videos found…"),
        (r"^(.+) · (\d+) video$", r"\1 · \2 videos"),
        (r"^İndirme hatası: (.+)$", r"Download error: \1"),
        (r"^(\d+) bağlantı kuyrukta veya geçmişte mevcut\. Varsayılan olarak atlanacak\.$", r"\1 links already exist in the queue or history and will be skipped by default."),
    )
    for pattern, replacement in patterns:
        if re.fullmatch(pattern, value):
            return re.sub(pattern, replacement, value)
    if value.startswith("Kanal:"):
        return value.replace("Kanal:", "Channel:", 1)
    if value.startswith("Platform:"):
        return value.replace("Video kimliği:", "Video ID:").replace("Platform:", "Platform:", 1)
    if value.startswith("Süre:"):
        return (
            value.replace("Süre:", "Duration:", 1)
            .replace("İzlenme:", "Views:")
            .replace("Yayın:", "Published:")
            .replace("Kaynak:", "Source:")
        )
    if value.startswith("Dosya oynatılamadı:"):
        return value.replace("Dosya oynatılamadı:", "File could not be played:", 1)
    return value


def _translate_property(widget: Any, getter: str, setter: str, cache_name: str) -> None:
    if getattr(widget, f"{cache_name}_skip", False):
        return
    try:
        current = getattr(widget, getter)()
    except (AttributeError, TypeError):
        return
    if not isinstance(current, str):
        return
    rendered_name = f"{cache_name}_rendered"
    if not hasattr(widget, cache_name) or current != getattr(widget, rendered_name, current):
        setattr(widget, cache_name, current)
    rendered = tr(getattr(widget, cache_name))
    if current != rendered:
        try:
            getattr(widget, setter)(rendered)
        except (AttributeError, TypeError):
            return
    setattr(widget, rendered_name, rendered)


def translate_widget_tree(widget: Gtk.Widget) -> None:
    """Translate existing and dynamically-created GTK widgets in place."""
    if isinstance(widget, Gtk.Label):
        _translate_property(widget, "get_label", "set_label", "_i18n_label")
    if isinstance(widget, Gtk.Entry):
        _translate_property(widget, "get_placeholder_text", "set_placeholder_text", "_i18n_placeholder")
    if isinstance(widget, Gtk.Window):
        _translate_property(widget, "get_title", "set_title", "_i18n_title")
    if isinstance(widget, Adw.PreferencesRow):
        _translate_property(widget, "get_title", "set_title", "_i18n_row_title")
        _translate_property(widget, "get_subtitle", "set_subtitle", "_i18n_row_subtitle")
    if isinstance(widget, Adw.WindowTitle):
        _translate_property(widget, "get_title", "set_title", "_i18n_window_title")
        _translate_property(widget, "get_subtitle", "set_subtitle", "_i18n_window_subtitle")
    _translate_property(widget, "get_tooltip_text", "set_tooltip_text", "_i18n_tooltip")

    child = widget.get_first_child()
    while child is not None:
        next_child = child.get_next_sibling()
        translate_widget_tree(child)
        child = next_child
