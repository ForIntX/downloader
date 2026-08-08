import unittest

from video_indirici.i18n import set_language, tr


class LocalizationTests(unittest.TestCase):
    def tearDown(self) -> None:
        set_language("tr")

    def test_turkish_is_the_default_language(self) -> None:
        set_language("tr")
        self.assertEqual(tr("İndir"), "İndir")

    def test_static_and_dynamic_text_is_translated(self) -> None:
        set_language("en")
        self.assertEqual(tr("İndir"), "Download")
        self.assertEqual(tr("3 aktif / 8 toplam"), "3 active / 8 total")
        self.assertEqual(
            tr("Tarama durduruldu · 12 video bulundu"),
            "Scan stopped · 12 videos found",
        )


if __name__ == "__main__":
    unittest.main()
