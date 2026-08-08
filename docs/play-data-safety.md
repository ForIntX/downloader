# Google Play veri güvenliği taslağı

[Türkçe](play-data-safety.md) | [English](play-data-safety-en.md)

- Geliştirici sunucusuna veri toplanmaz veya paylaşılmaz.
- Kullanıcının URL'leri yalnızca medya kaynağına yapılan isteklerde kullanılır.
- Kuyruk, geçmiş, ayarlar ve loglar cihazda tutulur.
- Hesap oluşturma ve uygulama içi Google girişi yoktur.
- Uygulama reklam, konum, kişi, fotoğraf tarama veya finansal veri kullanmaz.
- Ağ, bildirim ve kullanıcının başlattığı uzun indirme izinleri temel işlev
  için kullanılır.

Play Console formu gönderilmeden önce uygulamaya sonradan eklenen SDK'lar ve gerçek
ağ trafiği yeniden denetlenmelidir.
