#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canli uc sagligi probu: /x402/health ve /.well-known/x402.

NEDEN AYRI BIR SCRIPT
---------------------
Sorun su: endpoint'e "curl -I" atmak HTTP 200 dondugu icin yesil gosterir,
oysa cevap gercek JSON degildir. Vercel'in guvenlik katmani (bot sinyali)
istenen yola 200 + HTML "Security Checkpoint" sayfasi koyar. Boylece bir
ucun gercekten ayakta oldugunu sadece kod yazarak anlamak zor; o cevapta
uc yok, Vercel var. Ayni sekilde upstream cok guvenlikli bir arac (Imperva
vb.) arkasindaysa Worker 502 doner ve suclu Worker sanilir.

Bu probun isi:
  1) Iki uca GET atar ve 200 + BEKLENEN JSON YAPI'yi dogrular.
  2) 403 / 5xx / timeout / Vercel checkpoint sayfasini CRITIK isaretler.
  3) Hata durumunda hangi KATMANIN suclu oldugunu soyler (katman atfedi):
        vercel  -> Vercel katmani cevabi degistirmis (checkpoint/mitigated)
        worker  -> Worker'in upstream'i (yani Worker'in arkasindaki Vercel)
        app     -> Cevap upstream'ten gelmis, katmanlar temiz, hizmette
        bilinmiyor -> Hic cevap yok (DNS/asagi/timeout); ayirt edilemez
     Bu ayrim olmadan "Worker bozuk" demek kolay ama cogu zaman yanlis.

BAGIMLILIK YOK: sadece stdlib (urllib/json/argparse). Projenin .venv'i ya da
sistem python3 ile ayni sonucu verir; hicbir sey kurulmaz.

KULLANIM
--------
    python3 scripts/health_probe.py
    python3 scripts/health_probe.py --url https://fieldcast-peach.vercel.app
    python3 scripts/health_probe.py --url <worker> --json
    python3 scripts/health_probe.py --strict        # uyarilari da hata say

CIKIS KODU
----------
    0  tum uclar saglikli (uyarilar varsa bile 0; --strict ile 1 olur)
    1  en az bir CRITIK bulundu
    2  komut satirinda hata (bilinmeyen secenek vb.)
"""
import argparse
import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

# README'de yazan canli adres. Varsayilan bu; --url ile degistirilir.
VARSAYILAN_URL = os.environ.get("FIELDCAST_URL", "https://fieldcast-peach.vercel.app").strip()

# Vercel'in guvenlik KATMANININ izleri. Bunlar cevabi degistirmis demektir:
# istek uygulamaya ulasmamis, Vercel bot sinyali yakalayip baska bir sey
# dondurmus.
VERCEL_GUVENLIK_ISARETLERI = (
    "x-vercel-mitigated",
    "x-vercel-sc-headers",
    "x-vercel-sc-cookies",
    "x-vercel-sc-host",
    "x-vercel-sc-failed",
)

# Vercel'in KIMLIK/yonlendirme izleri. Bunlar BASARILI her cevapta da olur
# (x-vercel-id, x-vercel-cache) -> tek basina hata degildir. Yalnizca "cevap
# Vercel katmanindan gelmis" demek icin kullanilir; katman atfedilirken ise
# yarar, CRITIK sayilmaz.
VERCEL_KIMLIK_ISARETLERI = (
    "x-vercel-id",
    "x-vercel-cache",
    "x-vercel-error",
    "x-matched-path",
    "x-vercel-deployment-url",
)

# Worker'in kendi cevaplarina koydugu isaret (bkz. worker/x402-proxy.js).
WORKER_ISARETI = "x-fieldcast-layer"

# Vercel'in bot sinyali yakalayip HTML sayfa dondurdugunu belli eden metin.
CHECKPOINT_METINLERI = ("Security Checkpoint",)

KRITIK = "CRITIK"
UYARI = "UYARI"
TAMAM = "TAMAM"

# Her ucun donmesi beklenen alanlar. Eksik alan = "200 dondu ama dogru
# govde degil" -> kritik. Boylece HTML sayfa, 200'lu hata, ya da yanlis
# servis cevabi sessizce gecmez.
BEKLENEN = {
    "/x402/health": ("status", "network", "testnet", "price", "pay_to", "facilitator"),
    "/.well-known/x402": ("x402Version", "service", "resources"),
}


class Bulgu(object):
    """Tek ucun sonucu."""

    def __init__(self, yol, durum, mesaj, katman=None, kod=None, ayrinti=None):
        self.yol = yol
        self.durum = durum
        self.mesaj = mesaj
        self.katman = katman
        self.kod = kod
        self.ayrinti = ayrinti

    def as_dict(self):
        return {
            "path": self.yol,
            "durum": self.durum,
            "katman": self.katman,
            "http": self.kod,
            "mesaj": self.mesaj,
            "ayrinti": self.ayrinti,
        }


def _kucuk_baslik(value):
    return (value or "").strip().lower()


def _bul(basliklar, adlar):
    """Verilen baslik adlarindan ilk dolu olani doner (yoksa None)."""
    kucuk = {_kucuk_baslik(k): v for k, v in (basliklar or {}).items()}
    for ad in adlar:
        if kucuk.get(ad):
            return ad
    return None


def checkpoint_isareti(basliklar, govde):
    """Guvenlik KATMANI cevabi degistirmis mi? (baslik veya govde metni)

    Dikkat: x-vercel-id / x-vercel-cache BASARILI cevaplarda da gelir;
    onlar sayilmaz. Sayilanlar sadece mitigation/checkpoint izleridir.
    """
    bulunan = _bul(basliklar, VERCEL_GUVENLIK_ISARETLERI)
    if bulunan:
        return bulunan
    for metin in CHECKPOINT_METINLERI:
        if metin in (govde or ""):
            return "govde:'%s'" % metin
    return None


def vercel_izleri(basliklar):
    """Cevabin Vercel katmanindan gectigini gosteren kimlik basligi var mi?"""
    return _bul(basliklar, VERCEL_KIMLIK_ISARETLERI)


def katman_belirle(basliklar, govde, ana_makine, baglanti_hatasi=None):
    """Suclu katmani soyler: vercel / worker / app / bilinmiyor.

    Kural sirasi onemli:
      * Hic cevap yoksa (timeout/DNS) katman AYIRT EDILEMEZ; "worker" ya da
        "app" demek tahmin olurdu. Dogru cevap bilinmiyor.
      * Guvenlik checkpoint'i varsa:
          - Worker uzerinden geliyorsa iz KALMIS demektir -> suclu Worker
            (Worker temizlemeyi yapmadi, ya da Worker arkasinda baska bir
            Vercel var).
          - dogrudan Vercel'e gidiyorsa suclu Vercel.
      * Guvenlik izi yoksa ama Vercel kimlik basligi varsa: cevap edge'den
        gelmis; 403/5xx uygulamaya ulasmadan uretilmis -> katman vercel.
      * Vercel izi de yoksa cevap dogrudan uygulamadan gelmis; hatasi
        uygulamanindir.
    """
    kucuk = {_kucuk_baslik(k): v for k, v in (basliklar or {}).items()}
    worker_host = ana_makine.endswith(".workers.dev")
    checkpoint = checkpoint_isareti(basliklar, govde)
    kendi_worker_iz = _kucuk_baslik(kucuk.get(WORKER_ISARETI) or "") == "worker"

    if baglanti_hatasi is not None:
        return "bilinmiyor"
    if checkpoint:
        return "worker" if (worker_host or kendi_worker_iz) else "vercel"
    if vercel_izleri(basliklar):
        return "vercel"
    return "app"


def _ozet(govde, uzunluk=160):
    """Tek satirlik govde ozeti (HTML sayfalarinda etiketleri izlemek icin)."""
    metin = " ".join((govde or "").split())
    return metin[:uzunluk] + ("..." if len(metin) > uzunluk else "")


def _govde_json(govde):
    """(nesne, hata_mesaji). Govde JSON degilse hata mesaji doner."""
    if not govde:
        return None, "govde bos"
    try:
        return json.loads(govde), None
    except ValueError as exc:
        return None, "govde JSON degil (%s)" % str(exc)[:80]


def _yollari_gozden_gecir(nesne, yol):
    """Beklenen alanlar ve odeme kaydi gercekten iceriyor mu?

    Doner: None (sorun yok) ya da (durum, mesaj).
      * Eksik alan -> CRITIK: 200 + JSON ama istenen sekil degil.
      * configured=false -> UYARI: govde dogru, hizmet odemesiz ilan ediyor
        demek (X402_PAY_TO bos). Erisilebilirlik sag, odeme kapali; agiri
        kritik degil. Eksik alanla ayni sepete konmamasi icin ayri tutuldu.
    """
    eksik = [ad for ad in BEKLENEN[yol] if ad not in nesne]
    if eksik:
        return KRITIK, "eksik alan(lar): %s" % ", ".join(eksik)
    if yol == "/.well-known/x402" and not nesne.get("configured"):
        return (
            UYARI,
            "configured=false; odemeli uc ilan edilmiyor (X402_PAY_TO bos)",
        )
    return None


def tek_uc(yol, url, zaman):
    """Bir ucu GET ile dener ve Bulgu doner."""
    tam = urllib.parse.urljoin(url if url.endswith("/") else url + "/", yol.lstrip("/"))
    istek = urllib.request.Request(tam, headers={"Accept": "application/json"})
    basliklar = {}
    govde = ""
    kod = None
    hata = None
    baglanti_hatasi = None

    try:
        baglam = ssl.create_default_context()
        with urllib.request.urlopen(istek, timeout=zaman, context=baglam) as yanit:
            kod = yanit.status
            basliklar = dict(yanit.headers.items())
            govde = yanit.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        # 403/404/5xx: govde yine de checkpoint olabilir, okunmali.
        kod = exc.code
        basliklar = dict(exc.headers.items()) if exc.headers else {}
        try:
            govde = exc.read().decode("utf-8", "replace")
        except Exception:
            govde = ""
        hata = "http_%d" % exc.code
    except socket.timeout:
        baglanti_hatasi = "timeout"
    except urllib.error.URLError as exc:
        baglanti_hatasi = "baglanti_kurulamadi: %s" % (getattr(exc, "reason", None) or exc)
    except Exception as exc:  # ssl, http.client, bilinmeyen
        baglanti_hatasi = "istek_basarisiz: %s" % str(exc)[:120]

    ana_makine = urllib.parse.urlparse(tam).hostname or ""
    katman = katman_belirle(basliklar, govde, ana_makine, baglanti_hatasi)

    if baglanti_hatasi is not None:
        return Bulgu(
            yol,
            KRITIK,
            "yanit yok (%s)" % baglanti_hatasi,
            katman,
            None,
            {"url": tam, "hata": baglanti_hatasi},
        )

    iz = checkpoint_isareti(basliklar, govde)
    if iz:
        return Bulgu(
            yol,
            KRITIK,
            "Vercel guvenlik katmani cevabi degistirmis (checkpoint sayfasi)",
            katman,
            kod,
            {"url": tam, "isaret": iz, "govde": _ozet(govde)},
        )

    if kod == 403:
        return Bulgu(
            yol,
            KRITIK,
            "HTTP 403: erisim reddedildi (bot sinyali ya da WAF)",
            katman,
            kod,
            {"url": tam, "govde": _ozet(govde)},
        )

    if 500 <= kod < 600:
        return Bulgu(
            yol,
            KRITIK,
            "HTTP %d: sunucu hatasi" % kod,
            katman,
            kod,
            {"url": tam, "govde": _ozet(govde)},
        )

    if kod != 200:
        return Bulgu(
            yol,
            KRITIK,
            "HTTP %d: 200 bekleniyordu (bu adres tanimli degil ya da yonlendirildi)"
            % kod,
            katman,
            kod,
            {"url": tam, "govde": _ozet(govde)},
        )

    nesne, hata_mesaji = _govde_json(govde)
    if nesne is None or not isinstance(nesne, dict):
        return Bulgu(
            yol,
            KRITIK,
            "200 dondu ama JSON nesnesi degil",
            katman,
            kod,
            {"url": tam, "hata": hata_mesaji, "govde": _ozet(govde)},
        )

    sorun = _yollari_gozden_gecir(nesne, yol)
    if sorun:
        durum, mesaj = sorun
        return Bulgu(yol, durum, mesaj, katman, kod, {"url": tam, "govde": _ozet(govde)})

    if yol == "/x402/health" and nesne.get("status") != "ok":
        # Uc ayakta, odeme yapilandirilmamis. Erisilebilirlik sorunu degil;
        # yine de gizlenmez.
        return Bulgu(
            yol,
            UYARI,
            "uc ayakta ama status=%s (X402_PAY_TO bos olabilir)" % nesne.get("status"),
            katman,
            kod,
            {"url": tam},
        )

    return Bulgu(yol, TAMAM, "200 + beklenen JSON", katman, kod, {"url": tam})


def prob(temel_url, zaman=10.0, yollar=None):
    """Verilen adreslere uygula; bulgularin listesi doner (sirali)."""
    yollar = yollar or list(BEKLENEN)
    return [tek_uc(yol, temel_url, zaman) for yol in yollar]


def _yaz(acik, sira, bulgu):
    etiket = "%-7s" % bulgu.durum
    satir = "%s %d. %-20s %s" % (etiket, sira, bulgu.yol, bulgu.mesaj)
    if bulgu.katman:
        satir += "  [suclu katman: %s]" % bulgu.katman
    if bulgu.kod is not None:
        satir += "  (http %d)" % bulgu.kod
    print(satir, file=acik)
    if bulgu.durum == KRITIK and bulgu.ayrinti:
        print("        ayrinti: %s" % json.dumps(bulgu.ayrinti, ensure_ascii=False),
              file=acik)


def main(argv=None):
    ayristirici = argparse.ArgumentParser(
        description="Fieldcast x402 uc sagligi probu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ayristirici.add_argument(
        "--url", default=VARSAYILAN_URL,
        help="problanacak temel adres (varsayilan: %s ya da $FIELDCAST_URL)" % VARSAYILAN_URL,
    )
    ayristirici.add_argument(
        "--timeout", type=float, default=10.0, help="istek basina saniye (varsayilan 10)",
    )
    ayristirici.add_argument("--json", action="store_true", help="makine icin JSON cikti")
    ayristirici.add_argument(
        "--strict", action="store_true",
        help="uyarilari da hata say (varsayilan: yalnizca CRITIK hata sayilir)",
    )

    try:
        secenek = ayristirici.parse_args(argv)
    except SystemExit as exc:
        # argparse zaten 2 ile cikiyor; burada sadece netlik icin.
        return int(exc.code or 2)

    temel = secenek.url.strip().rstrip("/")
    if not temel.startswith("http://") and not temel.startswith("https://"):
        print("HATA: --url http(s) ile baslamali: %r" % secenek.url, file=sys.stderr)
        return 2

    bulgular = prob(temel, secenek.timeout)

    if secenek.json:
        print(json.dumps(
            {
                "url": temel,
                "sonuc": (
                    "kritik" if any(b.durum == KRITIK for b in bulgular)
                    else "uyari" if any(b.durum == UYARI for b in bulgular)
                    else "saglikli"
                ),
                "bulgular": [b.as_dict() for b in bulgular],
            },
            indent=2,
            ensure_ascii=False,
        ))
    else:
        print("Fieldcast probu -> %s" % temel)
        for sira, bulgu in enumerate(bulgular, 1):
            _yaz(sys.stdout, sira, bulgu)
        kritik = [b for b in bulgular if b.durum == KRITIK]
        uyari = [b for b in bulgular if b.durum == UYARI]
        if kritik:
            print("\nSONUC: CRITIK x%d. Odeme ucu canli degil." % len(kritik))
        elif uyari:
            print("\nSONUC: erisilebilir, ama %d uyari var." % len(uyari))
        else:
            print("\nSONUC: iki uc da saglikli.")

    kritik_var = any(b.durum == KRITIK for b in bulgular)
    uyari_var = any(b.durum == UYARI for b in bulgular)
    if kritik_var or (secenek.strict and uyari_var):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())