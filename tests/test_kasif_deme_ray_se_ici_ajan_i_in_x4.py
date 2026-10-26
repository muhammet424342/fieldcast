# -*- coding: utf-8 -*-
"""api/ray.py odeme rayi secici testleri.

Kilitlenen davranis:
  * Ajan imzasi (curl/python-requests/...) -> 402 + x402 v2 sartlari.
  * Insan tarayici imzasi (Mozilla/...)     -> api/moove.py link akisi, 302.
  * Opsiyonel X-Fieldcast-Ray basligi tarafi zorlar.
  * Anlasilamayan istek guvenli tarafa (ajan/402) duser; bedava cikarim acilmaz.
  * X402_PAY_TO bos ise uc 503 doner (bedava cikarim acilmaz).
  * Cikarim mantigi ray.py'de yeniden yazilmaz; odemeli istek mevcut
    api/pay.py -> api/index.py cekirdegine devredilir.

Calistirma:
  python3 -m unittest discover -s tests -v
  (veya: python3 tests/test_kasif_deme_ray_se_ici_ajan_i_in_x4.py)

Paketler (flask/x402) yoksa proje .venv yorumlayicisi ile yeniden calisir;
paket kurulmaz.
"""
import base64
import importlib
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
API_DIR = os.path.join(REPO_ROOT, "api")
GECIS_AYARI = "FIELDCAST_RAY_TEST_YORUMLAYICI"

AJAN_UA = "python-requests/2.31.0"
TARAYICI_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
PAY_TO = "0x" + "3" * 40
TEST_AG = "eip155:84532"
USDC_TEST = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"

ENV = {
    "X402_PAY_TO": PAY_TO,
    "X402_NETWORK": TEST_AG,
    "X402_PRICE": "$0.01",
    "X402_BAZAAR": "0",
    "FIELDCAST_MOOVE_LINK": "",
    "MOOVE_LINK": "",
}


def _paketler_var_mi():
    for ad in ("flask", "x402"):
        try:
            importlib.import_module(ad)
        except ImportError:
            return False
    return True


def _proje_yorumlayicisi():
    adaylar = [os.environ.get("FIELDCAST_TEST_PYTHON", "")]
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
            "Bu test flask + x402 gerektiriyor, bulunamadi.\n"
            f"  {os.path.join(REPO_ROOT, '.venv', 'bin', 'python')} "
            f"{os.path.abspath(__file__)}"
        )
    print(
        f"[ray testleri] paketler bu yorumlayicida yok; {yorumlayici} ile "
        "yeniden calistiriliyor",
        file=sys.stderr,
    )
    os.environ[GECIS_AYARI] = "1"
    os.execv(yorumlayici, [yorumlayici, os.path.abspath(__file__)])


_dogru_yorumlayiciya_gectir()

if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

import ray  # noqa: E402  (bootstrap'tan sonra)


def _sartlar(yanit):
    baslik = yanit.headers.get("PAYMENT-REQUIRED")
    if not baslik:
        return None
    return json.loads(base64.b64decode(baslik))


class RaySeciciTestleri(unittest.TestCase):
    def setUp(self):
        self._ortam = patch.dict(os.environ, ENV)
        self._ortam.start()
        self.client = ray.app.test_client()

    def tearDown(self):
        self._ortam.stop()

    # --- taraf tespiti ----------------------------------------------------
    def test_ajan_ua_402_ve_x402_sartlari(self):
        yanit = self.client.post(
            "/ray",
            json={"text": "INVOICE 1", "fields": ["total"]},
            headers={"User-Agent": AJAN_UA, "Accept": "application/json"},
        )
        self.assertEqual(yanit.status_code, 402)
        sart = _sartlar(yanit)
        self.assertIsNotNone(sart, "PAYMENT-REQUIRED basligi yok")
        self.assertEqual(sart["x402Version"], 2)
        kabul = sart["accepts"][0]
        self.assertEqual(kabul["scheme"], "exact")
        self.assertEqual(kabul["network"], TEST_AG)
        self.assertEqual(kabul["payTo"], PAY_TO)
        self.assertEqual(kabul["asset"], USDC_TEST)
        self.assertEqual(kabul["amount"], "10000")
        self.assertEqual(yanit.get_json(), {})
        self.assertIsNone(yanit.headers.get("X-PAYMENT"))

    def test_curl_ajandir(self):
        yanit = self.client.post(
            "/ray",
            json={"text": "x", "fields": ["a"]},
            headers={"User-Agent": "curl/8.5.0", "Accept": "*/*"},
        )
        self.assertEqual(yanit.status_code, 402)

    def test_insan_tarayici_moove_linkine_yonlendirilir(self):
        yanit = self.client.post(
            "/ray",
            json={"text": "x", "fields": ["a"]},
            headers={"User-Agent": TARAYICI_UA, "Accept": "text/html"},
        )
        self.assertEqual(yanit.status_code, 302)
        self.assertTrue(yanit.headers["Location"].startswith("/moove"))

    def test_moove_linki_env_ile_degistirilebilir(self):
        with patch.dict(os.environ, {"FIELDCAST_MOOVE_LINK": "/odeme/link"}):
            yanit = self.client.get(
                "/ray", headers={"User-Agent": TARAYICI_UA, "Accept": "text/html"}
            )
        self.assertEqual(yanit.status_code, 302)
        self.assertTrue(yanit.headers["Location"].startswith("/odeme/link"))

    def test_yonlendirme_sorgu_dizesini_korur(self):
        yanit = self.client.get(
            "/ray?fields=total",
            headers={"User-Agent": TARAYICI_UA, "Accept": "text/html"},
        )
        self.assertIn("fields=total", yanit.headers["Location"])

    def test_acik_baslik_tarafi_zorlar(self):
        insan = self.client.post(
            "/ray",
            json={"text": "x", "fields": ["a"]},
            headers={"User-Agent": AJAN_UA, "X-Fieldcast-Ray": "human"},
        )
        self.assertEqual(insan.status_code, 302)
        ajan = self.client.post(
            "/ray",
            json={"text": "x", "fields": ["a"]},
            headers={"User-Agent": TARAYICI_UA, "X-Fieldcast-Ray": "agent"},
        )
        self.assertEqual(ajan.status_code, 402)

    def test_accept_html_tek_basina_insan_sayilir(self):
        yanit = self.client.get(
            "/ray", headers={"User-Agent": "Bilinmeyen/1.0", "Accept": "text/html"}
        )
        self.assertEqual(yanit.status_code, 302)

    def test_belirsiz_istek_guvenli_tarafa_duser(self):
        yanit = self.client.post(
            "/ray",
            json={"text": "x", "fields": ["a"]},
            headers={"User-Agent": "Bilinmeyen/1.0", "Accept": "*/*"},
        )
        self.assertEqual(yanit.status_code, 402)

    def test_bos_pay_to_bedava_cikarim_acmaz(self):
        with patch.dict(os.environ, {"X402_PAY_TO": ""}):
            yanit = self.client.post(
                "/ray",
                json={"text": "x", "fields": ["a"]},
                headers={"User-Agent": AJAN_UA, "Accept": "application/json"},
            )
        self.assertEqual(yanit.status_code, 503)
        self.assertEqual(yanit.get_json()["error"], "x402_not_configured")
        self.assertIsNone(yanit.headers.get("PAYMENT-REQUIRED"))

    # --- ortak cikarim cekirdegi -----------------------------------------
    def test_sartlar_pay_ile_ayni_kaynaktan(self):
        with patch.dict(os.environ, {"X402_NETWORK": "eip155:8453"}):
            sart = ray.odeme_sartlari("http://localhost")
        self.assertEqual(sart["accepts"][0]["network"], "eip155:8453")
        self.assertEqual(
            sart["resource"]["url"], "http://localhost/x402/extract"
        )

    def test_cikarim_mantigi_ray_icinde_yeniden_yazilmamis(self):
        """ray.py kendi prompt/ayristirma motorunu tasimaz; index.py cekirdegi."""
        with open(ray.__file__, encoding="utf-8") as dosya:
            kaynak = dosya.read()
        self.assertNotIn("class Flask(Flask)", kaynak)
        self.assertNotIn("def extract_fields", kaynak)
        self.assertNotIn("def read_document_from_request", kaynak)


if __name__ == "__main__":
    unittest.main(verbosity=2)
