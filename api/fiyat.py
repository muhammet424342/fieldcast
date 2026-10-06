# -*- coding: utf-8 -*-
"""TRY karsiligi. Cevrimdisi son basarili USD/TRY kuru.

Kur dosyasi 30 dakikadan taze ise aga gidilmez. Daha eskiyse ve
FIELDCAST_KUR_URL verilmisse oradan yenilenir. Depoda kur adresi yok;
adres kodda yazili degil. Kur okunamazsa HTTP 503, govdede tutar yok.
"""
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from urllib.request import urlopen

from paketler import FiyatHatasi, birim_usd, liste, para


class KurHatasi(Exception):
    """Kur dosyasi yok, bozuk, eskı ve yenisi de alinamaz."""


CACHE_SURE = timedelta(minutes=30)
VARSAYILAN_DOSYA = os.path.join(tempfile.gettempdir(), "fieldcast-usdtry.json")


def _utc(an):
    if an is None:
        an = datetime.now(timezone.utc)
    if an.tzinfo is None:
        an = an.replace(tzinfo=timezone.utc)
    return an


def _ayar(ortam, ad):
    if ortam is None:
        return os.environ.get(ad, "") or ""
    return ortam.get(ad, "") or ""


def _zaman_coz(ham):
    if not isinstance(ham, str) or not ham.strip():
        raise KurHatasi("kur zamani yok")
    metin = ham.strip()
    if metin.endswith("Z"):
        metin = metin[:-1] + "+00:00"
    try:
        an = datetime.fromisoformat(metin)
    except ValueError as exc:
        raise KurHatasi("kur zamani okunamadi") from exc
    return _utc(an)


def _kur_degeri(ham):
    try:
        deger = Decimal(str(ham))
    except (InvalidOperation, ValueError) as exc:
        raise KurHatasi("kur sayi degil") from exc
    if deger <= 0:
        raise KurHatasi("kur sifir veya negatif")
    return deger


def kur_yaz(yol, usd_try, zaman, kaynak):
    """Son basarili kuru diske yazar. Repo icine yazilmaz."""
    an = _utc(zaman)
    govde = {
        "usd_try": format(_kur_degeri(usd_try), "f"),
        "zaman": an.isoformat(),
        "kaynak": kaynak or "dosya",
    }
    dizin = os.path.dirname(yol)
    if dizin:
        os.makedirs(dizin, exist_ok=True)
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as dosya:
        json.dump(govde, dosya, ensure_ascii=False)
    os.replace(gecici, yol)


def kur_dosyadan(yol):
    if not yol or not os.path.isfile(yol):
        raise KurHatasi("son basarili kur dosyasi yok")
    try:
        with open(yol, encoding="utf-8") as dosya:
            veri = json.load(dosya)
    except (OSError, json.JSONDecodeError) as exc:
        raise KurHatasi("son basarili kur okunamadi") from exc
    if not isinstance(veri, dict) or "usd_try" not in veri:
        raise KurHatasi("son basarili kur okunamadi")
    return {
        "usd_try": _kur_degeri(veri["usd_try"]),
        "zaman": _zaman_coz(veri.get("zaman")),
        "kaynak": veri.get("kaynak") or "dosya",
    }


def _urllib_ac(url, timeout=10):
    return urlopen(url, timeout=timeout)


def kur_cek(url, ac, simdi):
    if not url or not str(url).strip():
        raise KurHatasi("FIELDCAST_KUR_URL ayarli degil")
    try:
        with ac(str(url).strip(), timeout=10) as cevap:
            kod = getattr(cevap, "status", None)
            if kod is None:
                kod = getattr(cevap, "code", 200)
            ham = cevap.read()
    except KurHatasi:
        raise
    except Exception as exc:
        raise KurHatasi("kur kaynagi ulasilamadi") from exc
    if int(kod) >= 400:
        raise KurHatasi("kur kaynagi HTTP %s" % kod)
    if isinstance(ham, bytes):
        ham = ham.decode("utf-8", "replace")
    try:
        veri = json.loads(ham)
    except json.JSONDecodeError as exc:
        raise KurHatasi("kur govdesi okunamadi") from exc
    if not isinstance(veri, dict) or "usd_try" not in veri:
        raise KurHatasi("kur govdesinde usd_try yok")
    return {
        "usd_try": _kur_degeri(veri["usd_try"]),
        "zaman": _utc(simdi),
        "kaynak": str(veri.get("kaynak") or "ag"),
    }


def taze_mi(zaman, simdi):
    return (_utc(simdi) - _utc(zaman)) <= CACHE_SURE


def kur_getir(yol, simdi, url, ac):
    """Taze dosyayi cevrimdisi okur. Eski dosyadan fiyat uretmez."""
    simdi = _utc(simdi)
    kayit = None
    try:
        kayit = kur_dosyadan(yol)
    except KurHatasi:
        kayit = None
    if kayit is not None and taze_mi(kayit["zaman"], simdi):
        return kayit
    try:
        yeni = kur_cek(url, ac, simdi)
    except KurHatasi as exc:
        if kayit is None:
            raise KurHatasi(
                "Kur okunamadi. Son basarili kur yok ve yenisi alinamadi. %s" % exc
            ) from exc
        raise KurHatasi(
            "Kur okunamadi. Son basarili kur 30 dakikadan eski (%s) ve yenisi "
            "alinamadi. Fiyat uretilmedi." % kayit["zaman"].isoformat()
        ) from exc
    kur_yaz(yol, yeni["usd_try"], yeni["zaman"], yeni["kaynak"])
    return yeni


def try_karsilik(birim, usd_try):
    tutar = (birim * usd_try).quantize(Decimal("0.0001"))
    if tutar <= 0:
        raise FiyatHatasi("TRY karsiligi sifir")
    return tutar


def fiyat_govdesi(kur, ortam):
    birim = birim_usd(ortam)
    karsilik = try_karsilik(birim, kur["usd_try"])
    usd_metin = para(birim)
    try_metin = para(karsilik)
    paketler = []
    for tanim in liste(ortam):
        paketler.append(
            {
                "kod": tanim["kod"],
                "ad": tanim["ad"],
                "periyot": tanim["periyot"],
                "belge_limiti": tanim["belge_limiti"],
                "oncelikli_kuyruk": tanim["oncelikli_kuyruk"],
                "birim_usd": usd_metin,
                "birim_try": try_metin,
            }
        )
    return {
        "kur": {
            "usd_try": format(kur["usd_try"], "f"),
            "zaman": _utc(kur["zaman"]).isoformat(),
            "kaynak": kur.get("kaynak") or "dosya",
        },
        "birim_usd": usd_metin,
        "birim_try": try_metin,
        "paketler": paketler,
    }


def kur_yok_cevabi(ayrinti):
    """Kur yokken tutar donulmez. 0.00 bir fiyat degildir."""
    return 503, {"hata": "kur_okunamadi", "ayrinti": str(ayrinti)}


def http_fiyat(ortam=None, simdi=None, ac=None, kur_dosyasi=None):
    """(HTTP kod, govde). Kur okunamazsa 503."""
    simdi = _utc(simdi)
    if not kur_dosyasi:
        kur_dosyasi = _ayar(ortam, "FIELDCAST_KUR_DOSYASI") or VARSAYILAN_DOSYA
    url = _ayar(ortam, "FIELDCAST_KUR_URL")
    if ac is None:
        ac = _urllib_ac
    try:
        kur = kur_getir(kur_dosyasi, simdi, url, ac)
        govde = fiyat_govdesi(kur, ortam)
    except KurHatasi as exc:
        return kur_yok_cevabi(exc)
    except FiyatHatasi as exc:
        return 503, {"hata": "fiyat_okunamadi", "ayrinti": str(exc)}
    return 200, govde


def uygulama(environ, start_response):
    """Stdlib WSGI. Flask gerekmez."""
    kod, govde = http_fiyat()
    raw = json.dumps(govde, ensure_ascii=False).encode("utf-8")
    sebep = "OK" if kod == 200 else "Service Unavailable"
    start_response(
        "%s %s" % (kod, sebep),
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(raw))),
        ],
    )
    return [raw]


if __name__ == "__main__":
    kod, govde = http_fiyat()
    print(json.dumps(govde, ensure_ascii=False, indent=2))
    raise SystemExit(0 if kod == 200 else 1)
