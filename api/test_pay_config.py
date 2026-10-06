# -*- coding: utf-8 -*-
"""Ana ag (eip155:8453) CDP facilitator yapilandirmasi.

X402_NETWORK=eip155:8453 iken facilitator, CDP_API_KEY_ID ve
CDP_API_KEY_SECRET ile kurulur. Anahtar yoksa POST /x402/extract HTTP 503
doner ve govdede "ana ag icin CDP anahtari gerekli" yazar; ag sessizce
eip155:84532 yapilmaz. Test agi yolu CDP anahtari istemez.

Calistirma:
    python3 api/test_pay_config.py

Paketler sistem python3'te yoksa proje .venv yorumlayicisiyle yeniden
calisir. Paket kurulmaz.
"""
import base64
import importlib
import json
import os
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_DIR = os.path.join(REPO_ROOT, "api")
GEREKEN_PAKETLER = ("flask", "x402", "httpx", "idna")
GECIS_AYARI = "FIELDCAST_TEST_YORUMLAYICI_KULLANILDI"

ANA_AG = "eip155:8453"
TEST_AG = "eip155:84532"
CDP_URL = "https://api.cdp.coinbase.com/platform/v2/x402"
MESAJ = "ana ag icin CDP anahtari gerekli"
TAKLIT_ID = "taklit-anahtar-id"
TAKLIT_GIZLI = "taklit-anahtar-gizli"

ENV_ANAHTARLARI = (
    "X402_NETWORK",
    "X402_FACILITATOR_URL",
    "X402_PAY_TO",
    "X402_PRICE",
    "X402_BAZAAR",
    "CDP_API_KEY_ID",
    "CDP_API_KEY_SECRET",
)


def _paketler_var_mi():
    for ad in GEREKEN_PAKETLER:
        try:
            importlib.import_module(ad)
        except ImportError:
            return False
    return True


def _proje_yorumlayicisi():
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
            return yol
    return None


def _dogru_yorumlayiciya_gectir():
    if _paketler_var_mi():
        return
    yorumlayici = None
    if not os.environ.get(GECIS_AYARI):
        yorumlayici = _proje_yorumlayicisi()
    if yorumlayici is None:
        raise SystemExit(
            "Bu test flask + x402 + httpx + idna gerektiriyor, bulunamadi.\n"
            f"  {os.path.join(REPO_ROOT, '.venv', 'bin', 'python')} "
            "api/test_pay_config.py"
        )
    print(
        f"[pay config testleri] paketler bu yorumlayicida yok; {yorumlayici} ile "
        "yeniden calistiriliyor",
        file=sys.stderr,
    )
    os.environ[GECIS_AYARI] = "1"
    os.execv(yorumlayici, [yorumlayici, os.path.abspath(__file__)])


_dogru_yorumlayiciya_gectir()

if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)


def pay_modulu(ortam=None):
    """api/pay.py'yi verilen ortamla bastan yukler. Anahtarlari da temizler."""
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


def _sahte_supported(network):
    from x402.schemas import SupportedKind, SupportedResponse

    def get_supported(_self):
        return SupportedResponse(
            kinds=[
                SupportedKind(x402_version=2, scheme="exact", network=network),
            ]
        )

    return get_supported


class TestAnaAgCdpYapilandirmasi(unittest.TestCase):
    def test_anahtar_taklit_edilince_yapilandirma_8453_gosterir(self):
        pay = pay_modulu(
            {
                "X402_NETWORK": ANA_AG,
                "X402_BAZAAR": "0",
                "CDP_API_KEY_ID": TAKLIT_ID,
                "CDP_API_KEY_SECRET": TAKLIT_GIZLI,
            }
        )
        self.assertIsNone(pay.ANA_AG_HATASI)
        self.assertEqual(pay.NETWORK, ANA_AG)
        self.assertEqual(pay.FACILITATOR_AYARI["network"], ANA_AG)
        self.assertEqual(pay.FACILITATOR_AYARI["url"], CDP_URL)
        self.assertNotEqual(pay.FACILITATOR_AYARI["network"], TEST_AG)
        self.assertNotIn("84532", pay.FACILITATOR_AYARI["url"])
        rota = pay.ROUTES["POST /x402/extract"]
        self.assertEqual(rota.accepts.network, ANA_AG)
        self.assertEqual(pay.FACILITATOR_ISTEMCI.url, CDP_URL)
        kesif = pay.app.test_client().get("/.well-known/x402").get_json()
        self.assertIs(kesif["configured"], True)
        self.assertEqual(kesif["facilitator"], CDP_URL)
        self.assertEqual(kesif["resources"][0]["accepts"][0]["network"], ANA_AG)

        from x402.http import HTTPFacilitatorClientSync

        with patch.object(
            HTTPFacilitatorClientSync, "get_supported", _sahte_supported(ANA_AG)
        ):
            yanit = pay.app.test_client().post(
                "/x402/extract", json={"text": "INVOICE 1", "fields": ["total"]}
            )
        self.assertEqual(yanit.status_code, 402)
        baslik = yanit.headers["PAYMENT-REQUIRED"]
        sart = json.loads(base64.b64decode(baslik))
        self.assertEqual(sart["accepts"][0]["network"], ANA_AG)
        self.assertNotEqual(sart["accepts"][0]["network"], TEST_AG)

    def test_taklit_anahtar_baslik_ureticisine_gider_ve_koda_yazilmaz(self):
        pay = pay_modulu(
            {
                "X402_NETWORK": ANA_AG,
                "X402_BAZAAR": "0",
                "CDP_API_KEY_ID": TAKLIT_ID,
                "CDP_API_KEY_SECRET": TAKLIT_GIZLI,
            }
        )
        gorulen = {}

        def create_cdp_auth_headers(key_id, secret):
            def _headers():
                gorulen["id"] = key_id
                gorulen["secret"] = secret
                return {
                    "verify": {"Authorization": "Bearer taklit"},
                    "settle": {"Authorization": "Bearer taklit"},
                    "supported": {"Authorization": "Bearer taklit"},
                }

            return _headers

        cdp_mod = types.ModuleType("cdp")
        x402_mod = types.ModuleType("cdp.x402")
        x402_mod.create_cdp_auth_headers = create_cdp_auth_headers
        with patch.dict(sys.modules, {"cdp": cdp_mod, "cdp.x402": x402_mod}):
            basliklar = pay.FACILITATOR_AYARI["create_headers"]()
        self.assertEqual(gorulen["id"], TAKLIT_ID)
        self.assertEqual(gorulen["secret"], TAKLIT_GIZLI)
        self.assertEqual(basliklar["verify"]["Authorization"], "Bearer taklit")

        with open(pay.__file__, encoding="utf-8") as dosya:
            kaynak = dosya.read()
        self.assertNotIn(TAKLIT_ID, kaynak)
        self.assertNotIn(TAKLIT_GIZLI, kaynak)
        self.assertNotRegex(kaynak, r'CDP_API_KEY_SECRET\s*=\s*["\'][^"\']+["\']')
        self.assertNotRegex(kaynak, r'CDP_API_KEY_ID\s*=\s*["\'][^"\']+["\']')

    def test_anahtar_yokken_503_ve_ag_84532_olmaz(self):
        pay = pay_modulu({"X402_NETWORK": ANA_AG, "X402_BAZAAR": "0"})
        self.assertEqual(pay.NETWORK, ANA_AG)
        self.assertIsNone(pay.FACILITATOR_AYARI)
        self.assertEqual(pay.ANA_AG_HATASI, MESAJ)
        self.assertIsNone(pay.ROUTES)
        yanit = pay.app.test_client().post(
            "/x402/extract", json={"text": "INVOICE 1", "fields": ["total"]}
        )
        self.assertEqual(yanit.status_code, 503)
        govde = yanit.get_json()
        self.assertIn(MESAJ, govde["detail"])
        self.assertEqual(govde["error"], "cdp_api_key_required")
        self.assertIsNone(yanit.headers.get("PAYMENT-REQUIRED"))
        self.assertNotIn(TEST_AG, json.dumps(govde))
        saglik = pay.app.test_client().get("/x402/health").get_json()
        self.assertEqual(saglik["network"], ANA_AG)
        self.assertEqual(saglik["status"], "not_configured")
        self.assertEqual(saglik["ana_ag_hata"], MESAJ)
        self.assertEqual(saglik["facilitator"], CDP_URL)
        kesif = pay.app.test_client().get("/.well-known/x402").get_json()
        self.assertIs(kesif["configured"], False)
        self.assertEqual(kesif["resources"], [])
        self.assertIn(MESAJ, kesif["not"])
        kok = pay.app.test_client().get("/x402").get_json()
        self.assertIs(kok["configured"], False)
        self.assertEqual(kok["network"], ANA_AG)

    def test_anahtarin_yarisi_da_503(self):
        for ortam in (
            {"CDP_API_KEY_ID": TAKLIT_ID},
            {"CDP_API_KEY_SECRET": TAKLIT_GIZLI},
            {"CDP_API_KEY_ID": "  ", "CDP_API_KEY_SECRET": TAKLIT_GIZLI},
        ):
            with self.subTest(ortam=sorted(ortam)):
                pay = pay_modulu(dict(ortam, X402_NETWORK=ANA_AG))
                self.assertEqual(pay.NETWORK, ANA_AG)
                yanit = pay.app.test_client().post(
                    "/x402/extract", json={"text": "x", "fields": ["a"]}
                )
                self.assertEqual(yanit.status_code, 503)
                self.assertIn(MESAJ, yanit.get_json()["detail"])

    def test_testnet_cdp_anahtarisiz_ayri_kalir(self):
        pay = pay_modulu({"X402_NETWORK": TEST_AG, "X402_BAZAAR": "0"})
        self.assertEqual(pay.NETWORK, TEST_AG)
        self.assertIsNone(pay.ANA_AG_HATASI)
        self.assertEqual(pay.FACILITATOR_AYARI["network"], TEST_AG)
        self.assertNotEqual(pay.FACILITATOR_AYARI["url"], CDP_URL)
        self.assertIsNone(pay.FACILITATOR_AYARI["create_headers"])
        self.assertEqual(pay.ROUTES["POST /x402/extract"].accepts.network, TEST_AG)

    def test_testnet_cdp_anahtari_olsa_da_ana_aga_gecmez(self):
        pay = pay_modulu(
            {
                "X402_NETWORK": TEST_AG,
                "X402_BAZAAR": "0",
                "CDP_API_KEY_ID": TAKLIT_ID,
                "CDP_API_KEY_SECRET": TAKLIT_GIZLI,
            }
        )
        self.assertEqual(pay.NETWORK, TEST_AG)
        self.assertEqual(pay.FACILITATOR_AYARI["network"], TEST_AG)
        self.assertNotEqual(pay.FACILITATOR_AYARI["url"], CDP_URL)
        self.assertIsNone(pay.ANA_AG_HATASI)


if __name__ == "__main__":
    unittest.main(verbosity=2)
