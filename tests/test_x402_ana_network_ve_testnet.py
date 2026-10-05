# -*- coding: utf-8 -*-
"""api/pay.py varsayilanlarinin Base MAINNET'e gecisini kilitler.

Amac: "varsayilan hali gercekten mainnet mi, sanal para mi?" sorusu bir daha
kaza ile degismesin. once kasif onerisiyle varsayilanlar su sekilde degisti:

  X402_NETWORK          eip155:84532 (Base Sepolia)  ->  eip155:8453 (Base mainnet)
  X402_FACILITATOR_URL  https://x402.org/facilitator  ->  https://facilitator.payai.network
  X402_PAY_TO           "" (kapali)                  ->  0x3f425d6ffd2855585483d65da684651e330759e0

Ucunun de ENV ile override edilebilir kalmasi da ayri bir test konusu: Vercel'de
.env yazilacak, kod icinde gomulu kalmayacak.

Calistirma:
  python3 -m unittest discover -s tests -v
  (veya dosyayi dogrudan: python3 tests/test_x402_ana_network_ve_testnet.py)

Hangi python ile calistirilirsa calistirilsin sonuc aynidir: dosya gercek
paketleri (flask/x402/httpx/idna) arar; bulamazsa projenin .venv yorumlayicisini
kendisi bulup ayni testleri orada yeniden calistirir (asagidaki bootstrap).
Paket kurulmaz, hicbir sey atlanmaz.

NOT: pytest kurulu degil; bu yuzden stdlib unittest kullanildi. pytest de varsa
dosya pytest ile de toplanir (sinif adi unittest.TestCase).
"""
import base64
import importlib
import json
import os
import subprocess
import sys
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
API_DIR = os.path.join(REPO_ROOT, "api")

GEREKEN_PAKETLER = ("flask", "x402", "httpx", "idna")
GECIS_AYARI = "FIELDCAST_TEST_YORUMLAYICI_KULLANILDI"


def _paketler_var_mi():
    for ad in GEREKEN_PAKETLER:
        try:
            importlib.import_module(ad)
        except ImportError:
            return False
    return True


def _proje_yorumlayicisi():
    """Bu kopyanin (worktree) .venv'i, yoksa calisma kopyasinin .venv'i.

    Sirasiyla: acik secim (FIELDCAST_TEST_PYTHON), worktree icindeki .venv,
    git'in "ortak" dizini (= ana calisma kopyasi) uzerindeki .venv. Boylece
    dosya nereden calistirilirsa calistirilsin ayni yorumlayiciyi bulur.
    """
    adaylar = []
    if os.environ.get("FIELDCAST_TEST_PYTHON"):
        adaylar.append(os.environ["FIELDCAST_TEST_PYTHON"])
    adaylar.append(os.path.join(REPO_ROOT, ".venv", "bin", "python"))
    try:
        ortak = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        ortak = ""
    if ortak:
        adaylar.append(os.path.join(os.path.dirname(ortak), ".venv", "bin", "python"))
    for yol in adaylar:
        if yol and os.path.isfile(yol) and os.access(yol, os.X_OK):
            # realpath YAPILMAZ: venv/bin/python bir sembolik bag; cozulurse
            # site-packages'i gormeyen sistem yorumlayicisi cikar.
            return yol
    return None


def _dogru_yorumlayiciya_gectir():
    """Paketler yoksa projeyi kendi .venv'i ile calistir.

    Sistem python3 ile acildiginda (paket kurulu degil) 26 ayri
    ModuleNotFoundError yerine: ayni test dosyasi dogru yorumlayicida bir kez
    yeniden calisir. Yorumlayici da yoksa sessizce test atlamak yerine cikis
    kodu 1 ile hata verir ve ne yapilacagini yazar.
    """
    if _paketler_var_mi():
        return
    yorumlayici = None
    if not os.environ.get(GECIS_AYARI):
        yorumlayici = _proje_yorumlayicisi()
    if yorumlayici is None:
        raise SystemExit(
            "Bu test flask + x402 + httpx + idna gerektiriyor, bulunamadi.\n"
            "Proje yorumlayicisiyla calistir:\n"
            f"  {os.path.join(REPO_ROOT, '.venv', 'bin', 'python')} "
            "-m unittest discover -s tests -v\n"
            "(ya da FIELDCAST_TEST_PYTHON ile yorumlayiciyi goster)"
        )
    print(
        f"[x402 testleri] paketler bu yorumlayicida yok; {yorumlayici} ile "
        "yeniden calistiriliyor",
        file=sys.stderr,
    )
    os.environ[GECIS_AYARI] = "1"
    os.execv(
        yorumlayici,
        [
            yorumlayici,
            "-m",
            "unittest",
            "discover",
            "-s",
            TESTS_DIR,
            "-v",
        ],
    )


_dogru_yorumlayiciya_gectir()

if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

MAINNET = "eip155:8453"
TESTNET = "eip155:84532"
PAYAI = "https://facilitator.payai.network"
ANA_ADRES = "0x3f425d6ffd2855585483d65da684651e330759e0"
# x402 SDK'nin Base mainnet USDC adresi (default_assets.py, "Base mainnet USDC")
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

ENV_ANAHTARLARI = (
    "X402_NETWORK",
    "X402_FACILITATOR_URL",
    "X402_PAY_TO",
    "X402_PRICE",
    "X402_BAZAAR",
)


def pay_modulu(ortam=None):
    """api/pay.py'yi verilen ENV ile TAZE import eder.

    pay.py ortami IMPORT ANINDA okur (dosya seviyesinde), bu yuzden test her
    senaryo icin modulu bellekten dusurup yeniden yukler. Yazma islemi modulu
    degistirmez; sadece ekler (Flask uygulamasi her import'ta yeni olur).
    """
    if ortam is None:
        ortam = {}
    eski = {k: os.environ.get(k) for k in ENV_ANAHTARLARI}
    try:
        for k in ENV_ANAHTARLARI:
            os.environ.pop(k, None)
        os.environ.update(ortam)
        sys.modules.pop("pay", None)
        return importlib.import_module("pay")
    finally:
        for k, v in eski.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def sartlar(modul, govde=None):
    """Odemesiz POST /x402/extract -> 402 + cozulmus PAYMENT-REQUIRED."""
    client = modul.app.test_client()
    yanit = client.post(
        "/x402/extract", json=govde or {"text": "INVOICE 1", "fields": ["total"]}
    )
    baslik = yanit.headers.get("PAYMENT-REQUIRED")
    return yanit, (json.loads(base64.b64decode(baslik)) if baslik else None)


class TestVarsayilanlar(unittest.TestCase):
    """Ortam degistirilmeden (yani Vercel .env'siz) gorulen degerler."""

    def setUp(self):
        self.pay = pay_modulu()

    def test_ag_base_mainnet(self):
        self.assertEqual(self.pay.NETWORK, MAINNET)

    def test_mainnet_oldugu_icin_testnet_bayragi_kapali(self):
        # IS_TESTNET = NETWORK != "eip155:8453" mantigi korundu; mainnet'te False.
        self.assertIs(self.pay.IS_TESTNET, False)

    def test_facilitator_payai_ana_adresi(self):
        self.assertEqual(self.pay.FACILITATOR_URL, PAYAI)

    def test_pay_to_bagli_ana_adres(self):
        self.assertEqual(self.pay.PAY_TO, ANA_ADRES)

    def test_pay_to_gercek_ethereum_adresi_biciminde(self):
        # Bozuk adres mainnet'te yanlis cebe para yollar; sekil burada kilitlenir.
        self.assertRegex(self.pay.PAY_TO, r"^0x[0-9a-fA-F]{40}$")
        self.assertEqual(len(self.pay.PAY_TO), 42)

    def test_fiyat_degismedi(self):
        self.assertEqual(self.pay.PRICE, "$0.01")


class TestOrtamOverride(unittest.TestCase):
    """Uc deger de ENV ile degistirilebiliyor olmali (Vercel .env)."""

    def test_ag_testnete_cevrilebiliyor(self):
        pay = pay_modulu({"X402_NETWORK": TESTNET})
        self.assertEqual(pay.NETWORK, TESTNET)
        self.assertIs(pay.IS_TESTNET, True)

    def test_facilitator_url_degistirilebiliyor(self):
        pay = pay_modulu({"X402_FACILITATOR_URL": "https://x402.org/facilitator"})
        self.assertEqual(pay.FACILITATOR_URL, "https://x402.org/facilitator")

    def test_pay_to_degistirilebiliyor(self):
        pay = pay_modulu({"X402_PAY_TO": "0x" + "1" * 40})
        self.assertEqual(pay.PAY_TO, "0x" + "1" * 40)

    def test_bos_pay_to_ucu_kapatir(self):
        # Geri alma yolu: adresi temizlemek ucu kapatir, bedava cikarim acmaz.
        pay = pay_modulu({"X402_PAY_TO": ""})
        self.assertEqual(pay.PAY_TO, "")
        self.assertFalse(bool(pay.PAY_TO))
        client = pay.app.test_client()
        self.assertEqual(client.get("/x402/health").get_json()["status"], "not_configured")
        yanit = client.post("/x402/extract", json={"text": "x", "fields": ["a"]})
        self.assertEqual(yanit.status_code, 503)
        self.assertEqual(yanit.get_json()["error"], "x402_not_configured")


class TestHealthCiktisi(unittest.TestCase):
    """Musteri sagda gercek/sanal ayrimini GORMELI; gizli kalmamali."""

    def test_ana_agda_gercek_para_yaziyor(self):
        yanit = pay_modulu().app.test_client().get("/x402/health")
        self.assertEqual(yanit.status_code, 200)
        govde = yanit.get_json()
        self.assertEqual(govde["network"], MAINNET)
        self.assertIs(govde["testnet"], False)
        self.assertEqual(govde["para"], "GERCEK USDC")
        self.assertEqual(govde["aciklama"], "Base (ana ag, gercek USDC)")

    def test_testnet_agda_sanal_para_yaziyor(self):
        yanit = pay_modulu({"X402_NETWORK": TESTNET}).app.test_client().get("/x402/health")
        govde = yanit.get_json()
        self.assertEqual(govde["network"], TESTNET)
        self.assertIs(govde["testnet"], True)
        self.assertEqual(govde["para"], "sanal")
        self.assertIn(TESTNET, govde["aciklama"])

    def test_health_hem_agi_hem_adresi_hem_facilitatori_bildiriyor(self):
        govde = pay_modulu().app.test_client().get("/x402/health").get_json()
        self.assertEqual(govde["pay_to"], ANA_ADRES)
        self.assertEqual(govde["facilitator"], PAYAI)
        self.assertEqual(govde["price"], "$0.01")

    def test_ana_uc_te_gercek_sanal_ayrimi_var(self):
        govde = pay_modulu().app.test_client().get("/x402").get_json()
        self.assertEqual(govde["network"], MAINNET)
        self.assertIs(govde["testnet"], False)
        self.assertEqual(govde["para"], "GERCEK USDC")
        self.assertIs(govde["configured"], True)


class TestOdemeAkisi(unittest.TestCase):
    """402 -> sartlar: ag, alici, varlik, tutar gercekten ne cikiyor?"""

    def test_odemesiz_istek_402_donuyor(self):
        yanit, _ = sartlar(pay_modulu())
        self.assertEqual(yanit.status_code, 402)

    def test_sartlar_base_mainnet_uzerinde(self):
        _, sart = sartlar(pay_modulu())
        kabul = sart["accepts"][0]
        self.assertEqual(kabul["network"], MAINNET)
        self.assertEqual(kabul["payTo"], ANA_ADRES)
        self.assertEqual(kabul["scheme"], "exact")
        self.assertEqual(kabul["asset"], USDC_BASE)

    def test_sartlar_bir_dolarlik_sent_olus_basinda(self):
        # $0.01 ve USDC 6 ondalik -> 10_000 atomik birim.
        _, sart = sartlar(pay_modulu())
        self.assertEqual(sart["accepts"][0]["amount"], "10000")

    def test_ortam_ile_ag_degisince_sartlar_da_degisiyor(self):
        _, sart = sartlar(pay_modulu({"X402_NETWORK": TESTNET}))
        self.assertEqual(sart["accepts"][0]["network"], TESTNET)

    def test_ortam_ile_adres_degisince_sartlar_da_degisiyor(self):
        _, sart = sartlar(pay_modulu({"X402_PAY_TO": "0x" + "2" * 40}))
        self.assertEqual(sart["accepts"][0]["payTo"], "0x" + "2" * 40)

    def test_odeme_yoksa_govde_bos_ve_anahtar_bicimi_base64(self):
        yanit, _ = sartlar(pay_modulu())
        self.assertEqual(yanit.headers.get("X-PAYMENT"), None)
        baslik = yanit.headers["PAYMENT-REQUIRED"]
        # Ust yorumda yazildigi gibi: base64 JSON, duz metin degil.
        self.assertNotIn("eip155", baslik)
        self.assertEqual(json.loads(base64.b64decode(baslik))["x402Version"], 2)


class TestFacilitatorKabiliyeti(unittest.TestCase):
    """Varsayilan facilitator mainnet'i TASIYOR MU? (canli /supported cagrisi)

    Butun degisikligin dayandigi tek gercek: PayAI /supported icinde
    eip155:8453 + exact donuyor. Bir gun PayAI bu agi dusururse ya da adres
    degisirse deploy ETMEDEN burasi kirmizi olur. Bu test agdan gecer; ag
    yoksa sessizce gecmez, hata verir.
    """

    def test_payai_supported_ana_agi_ve_exact_semasini_ilaniyor(self):
        from x402.http import FacilitatorConfig, HTTPFacilitatorClientSync

        istemci = HTTPFacilitatorClientSync(FacilitatorConfig(url=PAYAI))
        turler = istemci.get_supported().kinds
        self.assertIn(
            (MAINNET, "exact"),
            [(k.network, k.scheme) for k in turler],
            f"{PAYAI} artik {MAINNET} + exact ilan etmiyor; varsayilan "
            "facilitator'i degistirmek gerekir",
        )

    def test_eskiden_kullanilan_x402_org_facilitator_ana_agi_tasiyamiyor(self):
        # Neden varsayilan degisti: bu test kirilirsa yeni bir x402.org
        # surumu mainnet eklemisse yorumu da guncellemek gerekir.
        from x402.http import FacilitatorConfig, HTTPFacilitatorClientSync

        istemci = HTTPFacilitatorClientSync(
            FacilitatorConfig(url="https://x402.org/facilitator")
        )
        turler = istemci.get_supported().kinds
        self.assertNotIn(MAINNET, [k.network for k in turler])


class TestUstYorum(unittest.TestCase):
    """Modul yorumundaki ag secimi aciklamasi gercek durumla ayni olmali.

    Regresyon korumasi: eski yorum "anahtarsiz mainnet yapamaz" diyordu;
    geri donerse docs ve kod birbirinden kopar.
    """

    def setUp(self):
        self.yorum = pay_modulu().__doc__ or ""

    def test_eski_yanlis_iddia_kalmadi(self):
        # "Anahtarsiz mainnet yapamaz" / "gercek para akmaz" gibi ifadelerin
        # hepsi eski durumu anlatiyordu; yorum gercek durumla degismeli.
        for yasak in (
            "GERCEK PARA AKMAZ",
            "anahtarsiz mainnet",
            "YAPILAMAZ",
            "yapamaz",
            "CDP API anahtariyla",
            "SADECE TEST",
        ):
            with self.subTest(yasak=yasak):
                self.assertNotIn(yasak, self.yorum)

    def test_payai_facilitator_adresi_yorumda_geciyor(self):
        self.assertIn(PAYAI, self.yorum)

    def test_ana_agin_adresi_yorumda_geciyor(self):
        self.assertIn(MAINNET, self.yorum)

    def test_yorum_gercek_para_akisini_durust_soyluyor(self):
        # Yorum "sanal para" demiyorsa ya da gercek akisi sakliyorsa sunucu
        # operatoru yanlis bilgilendirir; fiyat/akis metni acikca yazili olmali.
        self.assertIn("GERCEK", self.yorum.upper())


class TestYorumlayiciSablonu(unittest.TestCase):
    """Bootstrap'in kendisi: testler her makinede gercekten calissin.

    Denetci bir kez sistem python3 ile calistirip 26 adet
    ModuleNotFoundError aldi. Buradaki testler, cozumun (dogru yorumlayiciya
    gecis) sessizce bozulmasini yakalar: aday yorumlayici gercekten paketleri
    gormeli ve bu dosya gercekten paketlerle calismali.
    """

    def test_bu_dosya_gercek_paketlerle_calisiyor(self):
        # Sahte (stub) flask/x402 ile yesil gostermek yasak: agdaki canli
        # /supported testleri ancak gerek paketlerle anlamli.
        self.assertTrue(
            _paketler_var_mi(),
            "testler flask/x402/httpx/idna olmadan calistirilmis; "
            "dogrulanacak durum degil",
        )

    def test_bulunan_yorumlayici_paketleri_gercekten_goruyor(self):
        yorumlayici = _proje_yorumlayicisi()
        self.assertIsNotNone(yorumlayici, "proje yorumlayicisi bulunamadi")
        self.assertTrue(os.access(yorumlayici, os.X_OK))
        deneme = subprocess.run(
            [yorumlayici, "-c", "import " + ", ".join(GEREKEN_PAKETLER)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(
            deneme.returncode,
            0,
            f"{yorumlayici} paketleri gormuyor: {deneme.stderr.strip()[-300:]}",
        )

    def test_yorumlayici_venv_yolunu_cezmistir(self):
        # venv/bin/python sembolik bag; realpath alinirsa site-packages kaybolur
        # ve gecis sessizce ayni hatali yorumlayiciya doner.
        yorumlayici = _proje_yorumlayicisi()
        if yorumlayici is None:
            self.skipTest("bu makinede proje yorumlayicisi yok")
        kok = os.path.dirname(os.path.dirname(yorumlayici))
        self.assertEqual(os.path.basename(kok), ".venv", yorumlayici)


if __name__ == "__main__":
    unittest.main(verbosity=2)
