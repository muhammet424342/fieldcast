# -*- coding: utf-8 -*-
"""Uc paket. Para birimi tek kaynaktan: X402_PRICE.

api/pay.py ve worker/x402-proxy.js ayni ortam degiskenini okur; varsayilan
ikisinde de "$0.01". Bu modul ikinci bir fiyat yazmaz. Masa ve kurum ayri
bir etiket fiyati tasimaz; limitleri vardir, birim fiyat kapı ile aynidir.
"""
import os
from decimal import Decimal, InvalidOperation


class FiyatHatasi(ValueError):
    """Birim fiyat okunamadi veya sifir. Sessiz 0.00 uretmek yasak."""


# Limitler brifte verildi. Tutar degil, kota.
PAKET_TANIMLARI = (
    {
        "kod": "kapi",
        "ad": "Kapı",
        "periyot": "belge",
        "belge_limiti": None,
        "oncelikli_kuyruk": False,
    },
    {
        "kod": "masa",
        "ad": "Masa",
        "periyot": "ay",
        "belge_limiti": 500,
        "oncelikli_kuyruk": False,
    },
    {
        "kod": "kurum",
        "ad": "Kurum",
        "periyot": "ay",
        "belge_limiti": 2000,
        "oncelikli_kuyruk": True,
    },
)

VARSAYILAN_BIRIM = "$0.01"


def _ham_fiyat(ortam):
    if ortam is None:
        return os.environ.get("X402_PRICE", VARSAYILAN_BIRIM)
    return ortam.get("X402_PRICE", VARSAYILAN_BIRIM)


def birim_usd(ortam=None):
    """X402_PRICE degerini Decimal yapar. Bos, bozuk veya <=0 ise hata."""
    ham = str(_ham_fiyat(ortam)).strip()
    metin = ham[1:].strip() if ham.startswith("$") else ham
    if not metin:
        raise FiyatHatasi("X402_PRICE bos")
    try:
        deger = Decimal(metin)
    except InvalidOperation as exc:
        raise FiyatHatasi("X402_PRICE okunamadi: %s" % ham) from exc
    if deger <= 0:
        raise FiyatHatasi("X402_PRICE sifir veya negatif olamaz")
    return deger


def para(deger):
    """En az iki ondalik. Sondaki gereksiz sifirlari at, 0.10'u 0.1 yapma."""
    metin = format(deger.quantize(Decimal("0.0001")), "f")
    if "." in metin:
        metin = metin.rstrip("0").rstrip(".")
    if "." not in metin:
        return metin + ".00"
    kurus = metin.split(".", 1)[1]
    if len(kurus) < 2:
        metin += "0" * (2 - len(kurus))
    return metin


def liste(ortam=None):
    """Her pakette ayni birim_usd. Kaynak bir kez okunur."""
    birim = para(birim_usd(ortam))
    cikti = []
    for tanim in PAKET_TANIMLARI:
        satir = dict(tanim)
        satir["birim_usd"] = birim
        cikti.append(satir)
    return cikti
