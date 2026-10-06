# -*- coding: utf-8 -*-
"""Paket fiyati tek kaynak, kur yokken 503.

Calistirma:
    python3 api/test_fiyat_ve_paket.py

Stdlib. Paket kurulmaz. Ag kullanilmaz; kur cekimi sahte ac() ile durur.
"""
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import fiyat
import paketler


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR = os.path.join(REPO, "public", "tr")
SIMDI = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)

ALAN = {
    "muhasebeci.html": "vkn,kdv_oranlari,odeme_vadesi",
    "lojistik.html": "plaka,sofor,sevk_tarihi,irsaliye_no",
    "gumruk.html": "gtip,mense,kalem_sayisi,beyanname_no",
}
GORUNEN = {
    "muhasebeci.html": ("VKN", "KDV oranları", "ödeme vadesi"),
    "lojistik.html": ("plaka", "şoför", "sevk tarihi", "irsaliye no"),
    "gumruk.html": ("GTIP", "menşe", "kalem sayısı", "beyanname no"),
}


class SahteCevap(object):
    def __init__(self, govde, kod=200):
        self.status = kod
        self._govde = govde.encode("utf-8") if isinstance(govde, str) else govde

    def read(self):
        return self._govde

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _yaz_kur(yol, usd_try, zaman, kaynak="test-dosya"):
    fiyat.kur_yaz(yol, usd_try, zaman, kaynak)


def _olmayan():
    fd, yol = tempfile.mkstemp(prefix="fc-kur-")
    os.close(fd)
    os.remove(yol)
    return yol


class PaketTestleri(unittest.TestCase):
    def test_uc_paket_ve_kotalar(self):
        satirlar = paketler.liste({})
        self.assertEqual([s["kod"] for s in satirlar], ["kapi", "masa", "kurum"])
        kapi, masa, kurum = satirlar
        self.assertIsNone(kapi["belge_limiti"])
        self.assertEqual(kapi["periyot"], "belge")
        self.assertFalse(kapi["oncelikli_kuyruk"])
        self.assertEqual(masa["belge_limiti"], 500)
        self.assertEqual(masa["periyot"], "ay")
        self.assertFalse(masa["oncelikli_kuyruk"])
        self.assertEqual(kurum["belge_limiti"], 2000)
        self.assertTrue(kurum["oncelikli_kuyruk"])

    def test_birim_tek_kaynak_varsayilan(self):
        satirlar = paketler.liste({})
        birimler = {s["birim_usd"] for s in satirlar}
        self.assertEqual(birimler, {"0.01"})
        self.assertEqual(paketler.para(paketler.birim_usd({})), "0.01")

    def test_x402_price_uc_paketi_birden_degistirir(self):
        satirlar = paketler.liste({"X402_PRICE": "$0.02"})
        self.assertEqual({s["birim_usd"] for s in satirlar}, {"0.02"})

    def test_env_x402_price_okunur(self):
        eski = os.environ.get("X402_PRICE")
        os.environ["X402_PRICE"] = "$0.03"
        try:
            self.assertEqual(paketler.para(paketler.birim_usd(None)), "0.03")
        finally:
            if eski is None:
                os.environ.pop("X402_PRICE", None)
            else:
                os.environ["X402_PRICE"] = eski

    def test_sifir_fiyat_hata(self):
        with self.assertRaises(paketler.FiyatHatasi):
            paketler.birim_usd({"X402_PRICE": "$0.00"})
        with self.assertRaises(paketler.FiyatHatasi):
            paketler.birim_usd({"X402_PRICE": "abc"})


class KurTestleri(unittest.TestCase):
    def setUp(self):
        self.yol = _olmayan()
        self.cagri = 0

    def _ac(self, url, timeout=10):
        self.cagri += 1
        return SahteCevap('{"usd_try":"20","kaynak":"sahte"}')

    def _patlat(self, url, timeout=10):
        self.cagri += 1
        raise AssertionError("taze kurda aga gidilmez")

    def test_taze_kur_cevrimdisi_ve_try(self):
        _yaz_kur(self.yol, "10", SIMDI - timedelta(minutes=5))
        kod, govde = fiyat.http_fiyat(
            ortam={}, simdi=SIMDI, ac=self._patlat, kur_dosyasi=self.yol
        )
        self.assertEqual(kod, 200)
        self.assertEqual(self.cagri, 0)
        self.assertEqual(govde["birim_usd"], "0.01")
        self.assertEqual(govde["birim_try"], "0.10")
        self.assertEqual(Decimal(govde["kur"]["usd_try"]), Decimal("10"))
        birimler = {p["birim_try"] for p in govde["paketler"]}
        self.assertEqual(birimler, {"0.10"})
        self.assertEqual(govde["paketler"][1]["belge_limiti"], 500)
        self.assertEqual(govde["paketler"][2]["belge_limiti"], 2000)
        self.assertTrue(govde["paketler"][2]["oncelikli_kuyruk"])
        self.assertNotIn("aylik_try", json.dumps(govde))

    def test_otuz_dakika_hala_taze(self):
        _yaz_kur(self.yol, "10", SIMDI - timedelta(minutes=30))
        kod, govde = fiyat.http_fiyat(
            ortam={}, simdi=SIMDI, ac=self._patlat, kur_dosyasi=self.yol
        )
        self.assertEqual(kod, 200, govde)
        self.assertEqual(self.cagri, 0)
        self.assertEqual(govde["birim_try"], "0.10")

    def test_eski_kur_yenilenemezse_503_ve_sifir_fiyat_yok(self):
        _yaz_kur(self.yol, "10", SIMDI - timedelta(minutes=31))
        kod, govde = fiyat.http_fiyat(
            ortam={}, simdi=SIMDI, ac=self._patlat, kur_dosyasi=self.yol
        )
        self.assertEqual(kod, 503)
        self.assertEqual(govde["hata"], "kur_okunamadi")
        self.assertNotIn("birim_try", govde)
        self.assertNotIn("paketler", govde)
        self.assertNotIn("0.00", json.dumps(govde))
        self.assertIn("Fiyat uretilmedi", govde["ayrinti"])

    def test_dosya_yoksa_503(self):
        kod, govde = fiyat.http_fiyat(
            ortam={}, simdi=SIMDI, ac=self._patlat, kur_dosyasi=self.yol
        )
        self.assertEqual(kod, 503)
        self.assertEqual(govde["hata"], "kur_okunamadi")
        self.assertNotIn("0.00", json.dumps(govde))
        self.assertEqual(self.cagri, 0)

    def test_bozuk_dosya_503(self):
        with open(self.yol, "w", encoding="utf-8") as dosya:
            dosya.write("{")
        kod, govde = fiyat.http_fiyat(
            ortam={}, simdi=SIMDI, ac=self._patlat, kur_dosyasi=self.yol
        )
        self.assertEqual(kod, 503)
        self.assertNotIn("birim_try", govde)

    def test_sifir_kur_503(self):
        with open(self.yol, "w", encoding="utf-8") as dosya:
            json.dump(
                {"usd_try": "0.00", "zaman": SIMDI.isoformat(), "kaynak": "test"},
                dosya,
            )
        kod, govde = fiyat.http_fiyat(
            ortam={}, simdi=SIMDI, ac=self._patlat, kur_dosyasi=self.yol
        )
        self.assertEqual(kod, 503)
        self.assertNotIn("birim_try", govde)
        self.assertNotIn("0.00", json.dumps(govde))

    def test_eski_kur_yenilenince_yeni_deger(self):
        _yaz_kur(self.yol, "10", SIMDI - timedelta(minutes=31))
        kod, govde = fiyat.http_fiyat(
            ortam={"FIELDCAST_KUR_URL": "http://127.0.0.1/kur"},
            simdi=SIMDI,
            ac=self._ac,
            kur_dosyasi=self.yol,
        )
        self.assertEqual(kod, 200, govde)
        self.assertEqual(self.cagri, 1)
        self.assertEqual(govde["birim_try"], "0.20")
        self.assertEqual(Decimal(govde["kur"]["usd_try"]), Decimal("20"))
        with open(self.yol, encoding="utf-8") as dosya:
            kayit = json.load(dosya)
        self.assertEqual(Decimal(kayit["usd_try"]), Decimal("20"))

    def test_fiyat_sifirsa_kur_taze_olsa_da_503(self):
        _yaz_kur(self.yol, "10", SIMDI)
        kod, govde = fiyat.http_fiyat(
            ortam={"X402_PRICE": "$0.00"},
            simdi=SIMDI,
            ac=self._patlat,
            kur_dosyasi=self.yol,
        )
        self.assertEqual(kod, 503)
        self.assertEqual(govde["hata"], "fiyat_okunamadi")
        self.assertNotIn("birim_try", govde)
        self.assertNotIn("0.00", json.dumps(govde))

    def test_kaynak_kodda_uydurma_adres_yok(self):
        for ad in ("fiyat.py", "paketler.py"):
            with open(os.path.join(REPO, "api", ad), encoding="utf-8") as dosya:
                metin = dosya.read().lower()
            self.assertNotIn("vercel.app", metin)
            self.assertNotIn("workers.dev", metin)
            self.assertNotIn("tcmb", metin)
            self.assertNotIn("frankfurter", metin)

    def test_wsgi_kur_yokken_503(self):
        eski = {
            k: os.environ.get(k)
            for k in ("FIELDCAST_KUR_DOSYASI", "FIELDCAST_KUR_URL", "X402_PRICE")
        }
        durum = {}

        def start(status, headers):
            durum["status"] = status
            durum["headers"] = headers

        try:
            os.environ["FIELDCAST_KUR_DOSYASI"] = self.yol
            os.environ["FIELDCAST_KUR_URL"] = ""
            os.environ["X402_PRICE"] = "$0.01"
            govde = b"".join(fiyat.uygulama({"REQUEST_METHOD": "GET"}, start))
        finally:
            for k, v in eski.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        self.assertTrue(durum["status"].startswith("503"), durum)
        self.assertNotIn(b"0.00", govde)
        self.assertNotIn(b"birim_try", govde)
        veri = json.loads(govde.decode("utf-8"))
        self.assertEqual(veri["hata"], "kur_okunamadi")


class SayfaTestleri(unittest.TestCase):
    def _oku(self, ad):
        yol = os.path.join(TR, ad)
        with open(yol, encoding="utf-8") as dosya:
            return dosya.read()

    def test_dort_sayfa_worker_ucu(self):
        for ad in ("index.html", "muhasebeci.html", "lojistik.html", "gumruk.html"):
            metin = self._oku(ad)
            self.assertNotIn("vercel.app", metin)
            self.assertNotIn("workers.dev", metin)
            self.assertIn("$ORIGIN/x402/extract", metin)
            self.assertIn('type="file"', metin)
            self.assertIn('id="sonuc"', metin)
            self.assertIn("Kendi ajanınız çağırsın", metin)
            self.assertIn("$0.01", metin)
            self.assertIn('id="belge"', metin)
            self.assertIn('id="koken"', metin)

    def test_persona_alanlari_farkli(self):
        gorulen = {}
        for ad, beklenen in ALAN.items():
            metin = self._oku(ad)
            self.assertIn('data-alan="%s"' % beklenen, metin)
            gorulen[ad] = beklenen
            for etiket in GORUNEN[ad]:
                self.assertIn(etiket, metin)
        self.assertEqual(len(set(gorulen.values())), 3)
        self.assertNotIn("kdv_oranlari", self._oku("lojistik.html"))
        self.assertNotIn("kdv_oranlari", self._oku("gumruk.html"))
        self.assertNotIn("gtip", self._oku("muhasebeci.html"))
        self.assertNotIn("plaka", self._oku("gumruk.html"))
        self.assertNotIn("gtip", self._oku("lojistik.html"))

    def test_index_uc_personayi_ve_paketleri_gosterir(self):
        metin = self._oku("index.html")
        for ad in ("muhasebeci.html", "lojistik.html", "gumruk.html"):
            self.assertIn(ad, metin)
        for beklenen in ALAN.values():
            self.assertIn(beklenen, metin)
        for etiket in ("VKN", "şoför", "GTIP", "Kapı", "Masa", "Kurum"):
            self.assertIn(etiket, metin)
        self.assertIn("500", metin)
        self.assertIn("2000", metin)
        self.assertIn("öncelikli kuyruk", metin)
        self.assertIn("INV-2031", metin)

    def test_fatura_ornegi_gercek_dosyadan(self):
        with open(
            os.path.join(REPO, "buyer-agent", "demo", "clean_invoice.txt"),
            encoding="utf-8",
        ) as dosya:
            ornek = dosya.read().strip()
        for ad in ("index.html", "muhasebeci.html"):
            self.assertIn(ornek, self._oku(ad))

    def test_lojistik_sevkiyat_metnini_irsaliye_diye_yazmaz(self):
        with open(
            os.path.join(REPO, "buyer-agent", "demo", "shipping_notice.txt"),
            encoding="utf-8",
        ) as dosya:
            ornek = dosya.read().strip()
        metin = self._oku("lojistik.html")
        self.assertIn(ornek, metin)
        self.assertIn("irsaliye değil", metin)

    def test_gumruk_beyannamesi_uydurulmamis(self):
        metin = self._oku("gumruk.html")
        self.assertIn("gümrük beyannamesi örneği yok", metin)
        self.assertNotIn("GTIP:", metin)


if __name__ == "__main__":
    unittest.main()
