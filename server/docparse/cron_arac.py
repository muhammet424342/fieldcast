# -*- coding: utf-8 -*-
"""SysAdmin adaylari icin cron zamanlama planlayicisi (taslak prototip).

Girdi: gorev listesi iceren JSON dosyasi; iki bicim kabul edilir:

    [{"ad": "gece-yedek", "cron": "30 2 * * *"}, ...]

veya

    {"gorevler": [{"ad": "...", "cron": "..."}, ...]}

Her gorev icin:
  - cron ifadesi ayristirilir (5 alan: dakika saat gun ay hafta-gunu),
  - okunabilir Turkce karsiligi uretilir,
  - yil icindeki gercek calisma gunleri ve saatleri hesaplanir,
  - ayni dakikaya denk gelen gorev cakismalari bulunur,
  - 24 saatlik yillik yuk dagilimi cikarilir ve ayni saati paylasan
    gorevler icin bos/en az yuklu saate tasima onerisi uretilir.

Hicbir sey disariya gonderilmez, servis kurulmaz/baslatilmaz; sadece
stdout'a JSON rapor basilir. '--birim' bayragi systemd service+timer
sablonunu yazar (kurulum yine yapilmaz).

Cikis kodlari:
  0 -> temiz plan (cakisma/oneri olabilir, bunlar hata degildir)
  1 -> gorev verisinde hata (gecersiz cron, bos/tekrar ad, hic calismayan
       ifade, bos plan)
  2 -> kullanim hatasi / dosya veya JSON okuma hatasi
"""
import json
import os
import sys
from datetime import date, datetime, timedelta

TIMA = "cron-zamanlayici"
ALANLAR = ("dakika", "saat", "gun", "ay", "hafta_gunu")
SINIRLAR = {
    "dakika": (0, 59),
    "saat": (0, 23),
    "gun": (1, 31),
    "ay": (1, 12),
    "hafta_gunu": (0, 7),
}
AY_ADLARI = ("Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
             "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik")
# Ic hafta gunu: Pazartesi=0 ... Pazar=6
GUN_ADLARI = ("Pazartesi", "Sali", "Carsamba", "Persembe", "Cuma",
              "Cumartesi", "Pazar")


def _liste(parcalar):
    parcalar = [str(p) for p in parcalar]
    if not parcalar:
        return ""
    if len(parcalar) == 1:
        return parcalar[0]
    return ", ".join(parcalar[:-1]) + " ve " + parcalar[-1]


def _alan_coz(metin, ad, alt, ust):
    """Tek bir cron alanini kumeye cevirir; gecersizse ValueError atar."""
    if not isinstance(metin, str) or not metin.strip():
        raise ValueError("%s alani bos" % ad)
    degerler = set()
    for parca in metin.split(","):
        parca = parca.strip()
        if not parca:
            raise ValueError("%s alaninda bos parca" % ad)
        taban = parca
        adim = 1
        if "/" in parca:
            taban, adim_metin = parca.split("/", 1)
            try:
                adim = int(adim_metin)
            except ValueError:
                raise ValueError("%s adimi sayi degil: %s" % (ad, adim_metin))
            if adim <= 0:
                raise ValueError("%s adimi pozitif olmali" % ad)
        if taban == "*":
            bas, son = alt, ust
        elif "-" in taban:
            bas_metin, son_metin = taban.split("-", 1)
            try:
                bas, son = int(bas_metin), int(son_metin)
            except ValueError:
                raise ValueError("%s araligi sayi degil: %s" % (ad, taban))
        else:
            try:
                bas = int(taban)
            except ValueError:
                raise ValueError("%s degeri sayi degil: %s" % (ad, taban))
            son = ust if "/" in parca else bas
        if bas < alt or son > ust or bas > son:
            raise ValueError("%s degeri aralik disinda: %s" % (ad, taban))
        degerler.update(range(bas, son + 1, adim))
    return degerler


def _tam_kume(ad):
    alt, ust = SINIRLAR[ad]
    return set(range(alt, ust + 1))


def _ic_hafta(gunler):
    """Cron hafta gunu (0/7=Pazar) -> ic gun (0=Pazartesi)."""
    return {6 if g in (0, 7) else g - 1 for g in gunler}


def cron_coz(ifade):
    """Cron ifadesini alan kumelerine ayirir.

    Doner: dakika/saat/gun/ay/hafta_gunu kumeleri, ham alanlar ve
    alanin serbest (*) olup olmadigini belirten bayraklar.
    """
    if not isinstance(ifade, str):
        raise ValueError("cron ifadesi metin olmali")
    parcalar = ifade.split()
    if len(parcalar) != 5:
        raise ValueError("cron 5 alan olmali, bulunan: %d" % len(parcalar))
    cozum = {"ifade": " ".join(parcalar), "ham": parcalar}
    for ad, ham in zip(ALANLAR, parcalar):
        alt, ust = SINIRLAR[ad]
        kume = _alan_coz(ham, ad, alt, ust)
        cozum[ad] = kume
        cozum[ad + "_serbest"] = ham.strip() == "*"
    cozum["hafta_gunu"] = _ic_hafta(cozum["hafta_gunu"])
    return cozum


def _zaman_metni(cozum):
    dakika = cozum["dakika"]
    saat = cozum["saat"]
    dak_ham, saat_ham = cozum["ham"][0], cozum["ham"][1]
    if dak_ham.startswith("*/") and saat_ham == "*":
        return "her %d dakikada bir" % int(dak_ham.split("/")[1])
    if dak_ham in ("0", "00") and saat_ham.startswith("*/"):
        return "her %d saatte bir" % int(saat_ham.split("/")[1])
    if len(dakika) == 60 and len(saat) == 24:
        return "her dakika"
    if len(saat) == 24:
        if dakika == {0}:
            return "her saat basi"
        if len(dakika) == 1:
            return "her saat %02d. dakikada" % next(iter(dakika))
        return "her saat su dakikalarda: %s" % _liste(
            "%02d" % d for d in sorted(dakika))
    if len(dakika) == 1:
        dk = next(iter(dakika))
        return _liste("%02d:%02d" % (s, dk) for s in sorted(saat))
    return "saat %s icin dakikalar %s" % (
        _liste(sorted(saat)),
        _liste("%02d" % d for d in sorted(dakika)))


def _gun_onek(cozum):
    ay = cozum["ay"]
    hafta = cozum["hafta_gunu"]
    gun = cozum["gun"]
    ay_onek = ""
    if not cozum["ay_serbest"]:
        ay_onek = "Yalnizca %s ayinda " % _liste(
            AY_ADLARI[m - 1] for m in sorted(ay))
    if cozum["hafta_gunu_serbest"] and cozum["gun_serbest"]:
        temel = "Her gun"
    elif cozum["gun_serbest"]:
        wd = sorted(hafta)
        if wd == [0, 1, 2, 3, 4]:
            temel = "Hafta ici her gun"
        elif wd == [5, 6]:
            temel = "Hafta sonu her gun"
        elif len(wd) == 1:
            temel = "Her %s" % GUN_ADLARI[wd[0]]
        else:
            temel = "%s gunleri" % _liste(GUN_ADLARI[g] for g in wd)
    elif cozum["hafta_gunu_serbest"]:
        gunler = sorted(gun)
        if len(gunler) == 1:
            temel = "Her ayin %d. gunu" % gunler[0]
        else:
            temel = "Her ayin %s. gunleri" % _liste(gunler)
    else:
        wd = sorted(hafta)
        temel = "Her ayin %s. gunu veya %s gunleri" % (
            _liste(sorted(gun)), _liste(GUN_ADLARI[g] for g in wd))
    if ay_onek:
        temel = temel[0].lower() + temel[1:]
    return ay_onek + temel


def cron_tanimi(ifade):
    """Cron ifadesinin okunabilir Turkce karsiligini dondurur."""
    cozum = cron_coz(ifade)
    onek = _gun_onek(cozum)
    zaman = _zaman_metni(cozum)
    if onek == "Her gun" and (
            zaman == "her dakika" or " dakikada bir" in zaman
            or " saatte bir" in zaman):
        metin = zaman
    else:
        metin = onek + " " + zaman
    return metin[0].upper() + metin[1:]


def zaman_ciftleri(cozum):
    """(saat, dakika) ciftleri kumesi."""
    return {(s, d) for s in cozum["saat"] for d in cozum["dakika"]}


def gun_kumesi(cozum, yil=2026):
    """Verilen yilda cron ifadesinin gercekten calistigi gunler."""
    gunler = set()
    gun_serbest = cozum["gun_serbest"]
    hafta_serbest = cozum["hafta_gunu_serbest"]
    gunun = date(yil, 1, 1)
    son = date(yil, 12, 31)
    while gunun <= son:
        if gunun.month in cozum["ay"]:
            dom_ok = gunun.day in cozum["gun"]
            dow_ok = gunun.weekday() in cozum["hafta_gunu"]
            if gun_serbest and hafta_serbest:
                eslesir = True
            elif gun_serbest:
                eslesir = dow_ok
            elif hafta_serbest:
                eslesir = dom_ok
            else:
                eslesir = dom_ok or dow_ok
            if eslesir:
                gunler.add(gunun)
        gunun += timedelta(days=1)
    return gunler


def _gorev_listesi(veri):
    if isinstance(veri, dict):
        if "gorevler" not in veri:
            raise ValueError("JSON nesnesinde 'gorevler' anahtari yok")
        veri = veri["gorevler"]
    if not isinstance(veri, list):
        raise ValueError("gorevler bir liste olmali")
    return veri


def plan_olustur(veri, yil=2026):
    """Gorev listesinden rapor uretir; hatalar da rapora yazilir."""
    ham_gorevler = _gorev_listesi(veri)
    hatalar = []
    cozumler = []
    gorulen_adlar = set()
    if not ham_gorevler:
        hatalar.append({"ad": None, "cron": None, "hata": "bos plan"})
    for sira, gorev in enumerate(ham_gorevler, start=1):
        if not isinstance(gorev, dict):
            hatalar.append({"ad": None, "cron": None, "hata": "gecersiz gorev",
                            "detay": "gorev %d nesne degil" % sira})
            continue
        ad = gorev.get("ad")
        if not isinstance(ad, str) or not ad.strip():
            hatalar.append({"ad": None, "cron": gorev.get("cron"),
                            "hata": "bos ad"})
            continue
        ad = ad.strip()
        if ad in gorulen_adlar:
            hatalar.append({"ad": ad, "cron": gorev.get("cron"),
                            "hata": "tekrar ad"})
            continue
        gorulen_adlar.add(ad)
        cron = gorev.get("cron")
        try:
            cozum = cron_coz(cron)
        except ValueError as hata:
            hatalar.append({"ad": ad, "cron": cron, "hata": "gecersiz cron",
                            "detay": str(hata)})
            continue
        gunler = gun_kumesi(cozum, yil)
        if not gunler:
            hatalar.append({"ad": ad, "cron": cron, "hata": "hic calismaz",
                            "detay": "%d yilinda hicbir gun eslesmiyor"
                                     % yil})
            continue
        cozum["ad"] = ad
        cozum["gunler"] = gunler
        cozumler.append(cozum)

    cakismalar = _cakismalar(cozumler)
    dagilim = saat_dagilimi(cozumler)
    oneriler = oneri_uret(cozumler, dagilim)
    gorevler = []
    for cozum in cozumler:
        gorevler.append({
            "ad": cozum["ad"],
            "cron": cozum["ifade"],
            "tanim": cron_tanimi(cozum["ifade"]),
            "gun_sayisi": len(cozum["gunler"]),
            "gunluk_calisma": len(zaman_ciftleri(cozum)),
            "yillik_calisma": len(cozum["gunler"]) * len(
                zaman_ciftleri(cozum)),
        })
    en_yogun = None
    if dagilim and max(dagilim) > 0:
        en_yogun = dagilim.index(max(dagilim))
    return {
        "yil": yil,
        "gorev_sayisi": len(cozumler),
        "gorevler": gorevler,
        "saat_dagilimi": dagilim,
        "en_yogun_saat": en_yogun,
        "cakismalar": cakismalar,
        "oneriler": oneriler,
        "hatalar": hatalar,
    }


def _cakismalar(cozumler):
    """Ayni gun ve ayni dakikaya denk gelen gorev ciftleri."""
    sonuc = []
    for i in range(len(cozumler)):
        for j in range(i + 1, len(cozumler)):
            a, b = cozumler[i], cozumler[j]
            ortak_gun = a["gunler"] & b["gunler"]
            ortak_zaman = zaman_ciftleri(a) & zaman_ciftleri(b)
            if not ortak_gun or not ortak_zaman:
                continue
            sonuc.append({
                "gorevler": [a["ad"], b["ad"]],
                "ortak_saatler": ["%02d:%02d" % (s, d)
                                  for s, d in sorted(ortak_zaman)],
                "ortak_gun_sayisi": len(ortak_gun),
                "yillik_cakisma": len(ortak_gun) * len(ortak_zaman),
            })
    sonuc.sort(key=lambda k: (-k["yillik_cakisma"], k["gorevler"]))
    return sonuc


def saat_dagilimi(cozumler):
    """Yillik calismalarin 24 saatlik kovaya dagilimi (0..23)."""
    dagilim = [0] * 24
    for cozum in cozumler:
        gun_sayisi = len(cozum["gunler"])
        for saat in cozum["saat"]:
            kova = saat if saat < 24 else 23
            dagilim[kova] += gun_sayisi * len(cozum["dakika"])
    return dagilim


def oneri_uret(cozumler, dagilim):
    """Ayni saati paylasan tek-saatlik gorevleri bos saate tasima onerisi."""
    tek_saat = [c for c in cozumler if len(c["saat"]) == 1]
    gruplar = {}
    for cozum in tek_saat:
        gruplar.setdefault(next(iter(cozum["saat"])), []).append(cozum)
    dolu = set(gruplar)
    oneriler = []
    for saat in sorted(gruplar):
        grup = gruplar[saat]
        if len(grup) < 2:
            continue
        for cozum in grup[1:]:
            adaylar = [h for h in range(24) if h not in dolu]
            if not adaylar:
                break
            adaylar.sort(key=lambda h: (dagilim[h], abs(h - saat), h))
            hedef = adaylar[0]
            dolu.add(hedef)
            oneriler.append({
                "ad": cozum["ad"],
                "mevcut_saat": saat,
                "onerilen_saat": hedef,
                "neden": "%d gorev ayni saatte" % len(grup),
            })
    return oneriler


def systemd_birimleri(script_yol, plan_yol, yil=2026):
    servis = "\n".join([
        "[Unit]",
        "Description=Cron zamanlama plani raporu",
        "",
        "[Service]",
        "Type=oneshot",
        "ExecStart=/usr/bin/python3 %s --yil %d %s" % (
            script_yol, yil, plan_yol),
        "",
        "[Install]",
        "WantedBy=multi-user.target",
        "",
    ])
    timer = "\n".join([
        "[Unit]",
        "Description=Cron zamanlama plani zamanlayicisi",
        "",
        "[Timer]",
        "OnCalendar=*-*-* 03:15:00",
        "Persistent=true",
        "",
        "[Install]",
        "WantedBy=timers.target",
        "",
    ])
    return {TIMA + ".service": servis, TIMA + ".timer": timer}


def _yil_oku(metin):
    try:
        yil = int(metin)
    except ValueError:
        raise ValueError("yil sayi degil: %s" % metin)
    if yil < 1970 or yil > 9999:
        raise ValueError("yil aralik disinda: %d" % yil)
    return yil


def main(argv):
    args = list(argv[1:])
    yil = datetime.now().year
    tanim = None
    birim = False
    konumlar = []
    while args:
        bayrak = args.pop(0)
        if bayrak == "--tanim":
            if not args:
                print("Kullanim: --tanim \"CRON IFADESI\"", file=sys.stderr)
                return 2
            tanim = args.pop(0)
        elif bayrak == "--birim":
            birim = True
        elif bayrak == "--yil":
            if not args:
                print("Kullanim: --yil YIL", file=sys.stderr)
                return 2
            try:
                yil = _yil_oku(args.pop(0))
            except ValueError as hata:
                print(str(hata), file=sys.stderr)
                return 2
        elif bayrak.startswith("--"):
            print("Bilinmeyen bayrak: %s" % bayrak, file=sys.stderr)
            return 2
        else:
            konumlar.append(bayrak)
    if tanim is not None:
        if konumlar or birim:
            print("--tanim tek basina kullanilmali", file=sys.stderr)
            return 2
        try:
            print(cron_tanimi(tanim))
        except ValueError as hata:
            print("Gecersiz cron: %s" % hata, file=sys.stderr)
            return 1
        return 0
    if birim:
        if len(konumlar) != 1:
            print("Kullanim: %s --birim plan.json" % argv[0],
                  file=sys.stderr)
            return 2
        birimler = systemd_birimleri(
            os.path.abspath(argv[0]), konumlar[0], yil)
        for ad, icerik in birimler.items():
            print("# %s" % ad)
            print(icerik)
        return 0
    if len(konumlar) != 1:
        print("Kullanim: %s [--yil YIL] plan.json | --tanim \"CRON\" | "
              "--birim plan.json" % argv[0], file=sys.stderr)
        return 2
    try:
        with open(konumlar[0], encoding="utf-8") as dosya:
            metin = dosya.read()
    except OSError as hata:
        print("Plan dosyasi okunamadi: %s" % hata, file=sys.stderr)
        return 2
    try:
        veri = json.loads(metin)
    except ValueError as hata:
        print("Plan JSON gecersiz: %s" % hata, file=sys.stderr)
        return 2
    try:
        rapor = plan_olustur(veri, yil)
    except ValueError as hata:
        print("Plan bicimi gecersiz: %s" % hata, file=sys.stderr)
        return 2
    print(json.dumps(rapor, ensure_ascii=False, indent=2))
    return 1 if rapor["hatalar"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
