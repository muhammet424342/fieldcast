# -*- coding: utf-8 -*-
"""Fieldcast urun ekran goruntuleri - dizin kayitlari icin.

Dizinlerin cogu 1920x1080 gercek ekran goruntusu istiyor.
Canli siteden cekilir; uydurma mockup uretilmez.
"""
import os
import pathlib
import time

from playwright.sync_api import sync_playwright

CANLI = "https://fieldcast-peach.vercel.app"
CIKTI = pathlib.Path(__file__).parent / "ekran_goruntuleri"
CIKTI.mkdir(exist_ok=True)

# (dosya adi, yol, kaydirilacak secici veya None, aciklama)
# NOT: scroll_into_view_if_needed KULLANILMAZ - zaten gorunen bolumu kaydirmadigi
# icin ardisik kareler ayni cikiyordu. Bunun yerine elemanin offsetTop'una gidilir.
KARELER = [
    ("01-anasayfa-ust.png",   "/",            None,        "Hero + deger onerisi"),
    ("02-nasil-calisir.png",  "/",            "#how",      "Istek/yanit ornegi"),
    ("03-neden.png",          "/",            ".grid",     "Fark yaratan 4 madde"),
    ("04-ajanlar.png",        "/",            "#agents",   "x402 / ajan odemesi"),
    ("05-fiyatlandirma.png",  "/",            "#pricing",  "Fiyat tablosu"),
    ("06-sss.png",            "/",            "#faq",      "Sikca sorulanlar"),
    ("07-gizlilik.png",       "/privacy.html", None,       "Gizlilik politikasi"),
    ("09-karsilastirma.png",  "/alternatives/docparser", None, "Rakip karsilastirma sayfasi"),
    ("10-senaryo.png",        "/for/bookkeepers", None,     "Kullanim senaryosu sayfasi"),
]


def main():
    with sync_playwright() as p:
        tarayici = p.chromium.launch()
        sayfa = tarayici.new_page(viewport={"width": 1920, "height": 1080},
                                  device_scale_factor=1)
        for ad, yol, secici, aciklama in KARELER:
            sayfa.goto(CANLI + yol, wait_until="networkidle", timeout=60000)
            if ad.startswith("06-"):
                # SSS kapaliyken kare, fiyat karesiyle ayni yere cakiliyordu
                # (sayfa sonu). Cevaplari acinca hem ayrisiyor hem daha faydali.
                sayfa.evaluate(
                    "document.querySelectorAll('details')"
                    ".forEach(d => d.setAttribute('open',''))"
                )
                time.sleep(0.3)
            if secici:
                y = sayfa.evaluate(
                    "s => { const e = document.querySelector(s);"
                    "   if (!e) return null;"
                    "   return e.getBoundingClientRect().top + window.scrollY - 24; }",
                    secici,
                )
                if y is None:
                    print("  ! secici bulunamadi: %s" % secici)
                else:
                    sayfa.evaluate("y => window.scrollTo(0, y)", y)
            else:
                sayfa.evaluate("window.scrollTo(0, 0)")
            time.sleep(0.4)
            hedef = CIKTI / ad
            sayfa.screenshot(path=str(hedef))
            konum = sayfa.evaluate("window.scrollY")
            print("%-24s %6d bayt  y=%-5d %s" % (ad, hedef.stat().st_size, konum, aciklama))

        # Tam sayfa - dizinlerin "full page" isteyen azinligi icin
        sayfa.goto(CANLI + "/", wait_until="networkidle", timeout=60000)
        tam = CIKTI / "00-tam-sayfa.png"
        sayfa.screenshot(path=str(tam), full_page=True)
        print("%-24s %6d bayt  %s" % (tam.name, tam.stat().st_size, "Tam sayfa"))

        # Mobil gorunum - bazi dizinler istiyor
        mob = tarayici.new_page(viewport={"width": 390, "height": 844})
        mob.goto(CANLI + "/", wait_until="networkidle", timeout=60000)
        m = CIKTI / "08-mobil.png"
        mob.screenshot(path=str(m))
        print("%-24s %6d bayt  %s" % (m.name, m.stat().st_size, "Mobil 390x844"))

        tarayici.close()


if __name__ == "__main__":
    main()
