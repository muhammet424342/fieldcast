# -*- coding: utf-8 -*-
"""public/dene.html "dene" ekrani ve ana sayfadaki giris noktasi kilitlenir.

Neden: kod bilmeyen kullanici icin tek yol curl'du. Artik bir dene ekrani var.
Bu test o ekranin kaybolmamasini ve API sozlesmesine bagli kalmasini saglar:

  - /v1/extract'e gider, varsayilan anahtar demo_key_public
  - PDF/duz metin icin multipart, yapistirilan metin icin JSON govde kurar
  - API'nin dondurdugu hata kodlarinin HEPSINI kullaniciya anlasilir cevirir
  - sonucu tablo + kopyala butonu olarak gosterir

Calistirma:
  python3 -m unittest discover -s tests -v
  (veya dosyayi dogrudan: python3 tests/test_dene_ekrani.py)

Bagimlilik yok; sadece stdlib.
"""
import os
import re
import unittest
from html.parser import HTMLParser

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
PUBLIC = os.path.join(REPO_ROOT, "public")
DENE = os.path.join(PUBLIC, "dene.html")
INDEX = os.path.join(PUBLIC, "index.html")

# api/index.py'nin dondurdugu hata kodlari; dene ekrani hepsini tanimali.
HATA_KODLARI = [
    "invalid_api_key",   # 401
    "quota_exceeded",    # 429
    "no_document_text",  # 400
    "no_fields_requested",
    "too_many_fields",
    "file_unreadable",
    "extraction_failed",  # 502
]


class _Sayfa(HTMLParser):
    def __init__(self):
        super().__init__()
        self.idler = set()
        self.script = []
        self._script_acik = False

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k == "id" and v:
                self.idler.add(v)
        if tag == "script":
            self._script_acik = True

    def handle_endtag(self, tag):
        if tag == "script":
            self._script_acik = False

    def handle_data(self, data):
        if self._script_acik:
            self.script.append(data)


def _oku(yol):
    with open(yol, "r", encoding="utf-8") as f:
        return f.read()


class DeneEkraniTestleri(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dene = _oku(DENE)
        cls.parser = _Sayfa()
        cls.parser.feed(cls.dene)
        cls.script = "\n".join(cls.parser.script)

    def test_dosya_var(self):
        self.assertTrue(os.path.isfile(DENE), "public/dene.html yok")

    def test_dogru_ucu_cagiriyor(self):
        self.assertIn("/v1/extract", self.dene)

    def test_varsayilan_anahtar_demo(self):
        self.assertIn('id="apiKey"', self.dene)
        self.assertIn('value="demo_key_public"', self.dene)

    def test_kullanicinin_anahtari_gonderiliyor(self):
        self.assertIn("X-API-Key", self.script)

    def test_pdf_icin_multipart(self):
        self.assertIn("FormData", self.script)
        self.assertIn('append("file"', self.script)
        self.assertIn('append("fields"', self.script)

    def test_metin_icin_json(self):
        self.assertIn("application/json", self.script)
        self.assertIn("JSON.stringify", self.script)

    def test_alanlar_virgulla_ayriliyor(self):
        self.assertIn('split(",")', self.script)

    def test_gerekli_ogeler_var(self):
        for gerekli in ["drop", "fileInput", "text", "fields", "run",
                        "result", "resultTable", "resultRaw", "copyBtn", "status"]:
            self.assertIn(gerekli, self.parser.idler, "eksik oge: " + gerekli)

    def test_script_yalnizca_var_olan_idleri_ister(self):
        """getElementById ile istenen her id HTML'de bulunmali (yazim hatasi yakalar)."""
        istenen = set(re.findall(r'getElementById\("([^"]+)"\)', self.script))
        self.assertTrue(istenen, "script hic getElementById kullanmiyor")
        eksik = istenen - self.parser.idler
        self.assertEqual(eksik, set(), "HTML'de olmayan id isteniyor: %s" % sorted(eksik))

    def test_tum_hata_kodlari_anlasilir_mesaja_bagli(self):
        for kod in HATA_KODLARI:
            self.assertIn(kod + ":", self.script,
                          "hata kodu mesaja baglanmamis: " + kod)

    def test_kopyala_butonu_var(self):
        self.assertIn("clipboard", self.script)

    def test_dosya_turu_dogrulaniyor(self):
        self.assertIn("Unsupported file type", self.script)

    def test_eski_sonuc_yeni_istekte_gizleniyor(self):
        """Extract'e basinca onceki sonuc hemen gizlenmeli.

        Aksi halde bos/gecersiz bir istekte eski tablo ekranda kalip
        kullaniciyi yaniltiyordu. Kontrol, erken donuslerden once yapilir.
        """
        self.assertIn(
            'el.result.classList.remove("on");\n    var fields', self.script,
            "run handler onceki sonucu gizlemiyor")

    def test_ana_sayfada_try_it_girisi(self):
        index = _oku(INDEX)
        self.assertIn('href="/dene.html"', index)
        self.assertIn("Try it", index)


if __name__ == "__main__":
    unittest.main(verbosity=2)
