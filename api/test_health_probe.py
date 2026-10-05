# -*- coding: utf-8 -*-
"""Saglik probu + kesif ucunun kilit testleri.

Kapsam:
  1) api/pay.py icindeki /.well-known/x402 ucu. Canlida bu adres 404 donuyordu
     (5 Eki 2026); test, adresin 200 + dogru JSON dondugunu ve ONCEKI ucun
     dondurdugu 402 odeme sartlariyla AYNI degerleri taydigini kilitler.
     Ikisi ayri yerde yazilirsa biri guncellenip digeri geride kalir; ajan
     odemeyi kabul edip cikarim alamayabilir.
  2) scripts/health_probe.py: 403 / 5xx / timeout / Vercel checkpoint
     sayfasi CRITIK sayiliyor; 200 + dogru JSON "TAMAM"; katman atfedi
     (vercel / worker / app / bilinmiyor) dogru.
  3) scripts/health_probe.sh: saglikli sunucuya 0, bozuk sunucuya 1 gecirir.

Ag YOK: probu testleri 127.0.0.1 uzerinde yerel sahte sunucu acar; canli
adrese istek atilmaz. Bu sayede "checkpoint gelirse CRITIK" kurali, gercek
bir Vercel olayini beklemeden test edilir.

Calistirma:
    python3 api/test_health_probe.py
    python3 -m unittest discover -s api -p "test_*.py" -v
    python3 -m unittest discover -s tests -v     # diger testler

Paketler (flask/x402/httpx/idna) bu makinede sistem python3'te kurulu degil;
dosya, calisan proje yorumlayicisini kendisi bulup orada yeniden calisir
(asagidaki bootstrap). hicbir sey kurulmaz.
"""
import base64
import importlib
import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
API_DIR = TESTS_DIR
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
PROBE_PY = os.path.join(SCRIPTS_DIR, "health_probe.py")
PROBE_SH = os.path.join(SCRIPTS_DIR, "health_probe.sh")

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
    git'in "ortak" dizini (= ana calisma kopyasi) uzerindeki .venv.
    venv/bin/python bir sembolik bag; realpath YAPILMAZ.
    """
    adaylar = []
    if os.environ.get("FIELDCAST_TEST_PYTHON"):
        adaylar.append(os.environ["FIELDCAST_TEST_PYTHON"])
    adaylar.append(os.path.join(REPO_ROOT, ".venv", "bin", "python"))
    try:
        ortak = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=15,
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
    """Paketler yoksa proje .venv'i ile ayni testleri yeniden calistir."""
    if _paketler_var_mi():
        return
    yorumlayici = None
    if not os.environ.get(GECIS_AYARI):
        yorumlayici = _proje_yorumlayicisi()
    if yorumlayici is None:
        raise SystemExit(
            "Bu test flask + x402 + httpx + idna gerektiriyor, bulunamadi.\n"
            "Proje yorumlayicisiyla calistir:\n"
            f"  {os.path.join(REPO_ROOT, '.venv', 'bin', 'python')} api/test_health_probe.py\n"
            "(ya da FIELDCAST_TEST_PYTHON ile yorumlayiciyi goster)"
        )
    print(
        f"[saglik probu testleri] paketler bu yorumlayicida yok; {yorumlayici} ile "
        "yeniden calistiriliyor", file=sys.stderr,
    )
    os.environ[GECIS_AYARI] = "1"
    os.execv(yorumlayici, [yorumlayici, os.path.abspath(__file__)])


_dogru_yorumlayiciya_gectir()

for _yol in (API_DIR, SCRIPTS_DIR):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import health_probe  # noqa: E402

MAINNET = "eip155:8453"
PAYAI = "https://facilitator.payai.network"
ANA_ADRES = "0x3f425d6ffd2855585483d65da684651e330759e0"
ENV_ANAHTARLARI = ("X402_NETWORK", "X402_FACILITATOR_URL", "X402_PAY_TO",
                   "X402_PRICE", "X402_BAZAAR")


def pay_modulu(ortam=None):
    """api/pay.py'yi verilen ENV ile TAZE import eder (pay.py ortami import
    aninda okur, bu yuzden bellekten dusurulup yeniden yuklenir)."""
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


def sartlar(modul):
    """Odemesiz POST /x402/extract -> 402 + cozulmus PAYMENT-REQUIRED."""
    yanit = modul.app.test_client().post(
        "/x402/extract", json={"text": "INVOICE 1", "fields": ["total"]}
    )
    baslik = yanit.headers.get("PAYMENT-REQUIRED")
    return yanit, (json.loads(base64.b64decode(baslik)) if baslik else None)


# --- sahte HTTP sunucusu -----------------------------------------------------
# Probu, 127.0.0.1 uzerinde acilan bu sunucuya bakar. Canli adrese istek
# atilmaz; test hem hizli hem cevrimdisidir.

SAHTE_SAGLIKLI = {
    "/x402/health": {
        "status": "ok", "network": MAINNET, "testnet": False, "para": "GERCEK USDC",
        "aciklama": "Base (ana ag, gercek USDC)", "price": "$0.01",
        "pay_to": ANA_ADRES, "facilitator": PAYAI,
    },
    "/.well-known/x402": {
        "x402Version": 2,
        "service": {"name": "Fieldcast", "url": "http://127.0.0.1"},
        "configured": True,
        "resources": [{
            "method": "POST", "path": "/x402/extract",
            "accepts": [{"scheme": "exact", "network": MAINNET,
                         "payTo": ANA_ADRES, "price": "$0.01"}],
        }],
    },
}


class _Handler(BaseHTTPRequestHandler):
    """Sahne sozlugu: rota -> govde (sozluk/liste) ya da (kod, basliklar, govde).

    Ikisi de kullanilir: sogru hali sozluk yazmak yeterli, ozel durumlar
    (403, checkpoint basligi, 5xx) icin ucunlu demet gerekiyor.
    """

    protocol_version = "HTTP/1.1"

    def do_GET(self):  # noqa: N802 (ad BaseHTTPRequestHandler'da boyle)
        self._cevik()

    def do_POST(self):  # noqa: N802
        """POST sahnesi de ayni sozlukten okunur.

        Worker'in EN KRITIK yolu odemesiz POST /x402/extract -> 402'dir. Sadece
        do_GET olsaydi sunucu 501 "Unsupported method" donerdi ve test gercek
        402 yerine hata kodu gormek zorunda kalirdi.
        """
        self._cevik(self._oku_govde())

    def _oku_govde(self):
        """Istek govdesini oku: content-length ya da chunked.

        Worker govdeyi AKIS olarak iletir ve content-length'i yeniden
        hesaplatmaz (bkz. worker/x402-proxy.js) -> upstream'e
        `transfer-encoding: chunked` ile gider. Gercek sunucular (Flask,
        gunicorn) bunu cozer; bu sahte sunucu da cozmek zorunda, yoksa
        govde bos gorunur ve test "Worker govdeyi dusuruyor" sanir.
        """
        kodlama = (self.headers.get("Transfer-Encoding") or "").lower()
        if "chunked" in kodlama:
            parcalar = []
            while True:
                baslik = self.rfile.readline().strip()
                try:
                    boyut = int(baslik.split(b";")[0] or b"0", 16)
                except ValueError:
                    break
                if boyut == 0:
                    self.rfile.readline()
                    break
                parcalar.append(self.rfile.read(boyut))
                self.rfile.readline()
            return b"".join(parcalar)
        # keep-alive'da cevabi yazmadan once govde tuketilmeli
        uzunluk = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(uzunluk) if uzunluk else b""

    def _cevik(self, ham_govde=b""):
        rota = self.path.split("?", 1)[0]
        # Gelen istek kaydi: "Worker POST govdesini/basligini iletiyor mu"
        # sorusu ancak upstream'in gordugunu kaydederek sorulabilir.
        self.server.kayit.append({
            "method": self.command,
            "path": rota,
            "govde": ham_govde.decode("utf-8", "replace"),
            "basliklar": {a.lower(): d for a, d in self.headers.items()},
        })
        girdi = self.server.sahne.get(rota)
        if girdi is None:
            kod, basliklar, govde = 404, {}, {"error": "not_found"}
        elif isinstance(girdi, tuple):
            kod, basliklar, govde = girdi
        else:
            kod, basliklar, govde = 200, {}, girdi
        if isinstance(govde, (dict, list)):
            basliklar = dict(basliklar or {})
            basliklar.setdefault("Content-Type", "application/json")
            govde = json.dumps(govde)
        ham = govde.encode("utf-8")
        self.send_response(kod)
        for ad, deger in (basliklar or {}).items():
            self.send_header(ad, deger)
        self.send_header("Content-Length", str(len(ham)))
        self.end_headers()
        self.wfile.write(ham)

    def log_message(self, *_args):
        """Test sunucusunun stderr'ini kirlatma."""


class SaglikliSunucu(object):
    """127.0.0.1 uzerinde kisa sureli sahte sunucu. `sahne` degistirilebilir."""

    def __init__(self, sahne=None):
        self.sunucu = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.sunucu.sahne = dict(sahne or SAHTE_SAGLIKLI)
        self.sunucu.kayit = []
        self.isim = "http://127.0.0.1:%d" % self.sunucu.server_address[1]
        self.ip = threading.Thread(target=self.sunucu.serve_forever, daemon=True)
        self.ip.start()

    def son_kayit(self, yol=None):
        """Upstream'e ulasan son istek kaydi (yol verildiyse o yolun kaydi)."""
        kayitlar = list(self.sunucu.kayit)
        if yol is not None:
            kayitlar = [k for k in kayitlar if k["path"] == yol]
        return kayitlar[-1] if kayitlar else None

    def sahneyi_ayarla(self, sahne, birlestir=False):
        """Sahneyi degistirir. birlestir=True ise sadece verilenleri yazar."""
        if birlestir:
            yeni = dict(self.sunucu.sahne)
            yeni.update(sahne)
            self.sunucu.sahne = yeni
        else:
            self.sunucu.sahne = dict(sahne)

    def kapat(self):
        self.sunucu.shutdown()
        self.sunucu.server_close()
        self.ip.join(timeout=5)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.kapat()


def bulgu(yol, url, zaman=10.0):
    """tek_uc sonucunu dondurur."""
    return health_probe.tek_uc(yol, url, zaman)


class TestKesifUcu(unittest.TestCase):
    """api/pay.py -> /.well-known/x402. Canlida 404 donuyordu."""

    def setUp(self):
        self.pay = pay_modulu()
        self.istemci = self.pay.app.test_client()

    def test_adres_200_donuyor(self):
        yanit = self.istemci.get("/.well-known/x402")
        self.assertEqual(yanit.status_code, 200)
        self.assertIn("application/json", yanit.headers.get("Content-Type", ""))

    def test_odeme_kaydi_ilan_ediliyor(self):
        govde = self.istemci.get("/.well-known/x402").get_json()
        self.assertEqual(govde["x402Version"], 2)
        self.assertIs(govde["configured"], True)
        self.assertEqual(len(govde["resources"]), 1)
        kayit = govde["resources"][0]
        self.assertEqual(kayit["method"], "POST")
        self.assertEqual(kayit["path"], "/x402/extract")

    def test_pay_to_bosken_odeme_kaydi_ilan_edilmiyor(self):
        # Hayalet uc yaratmamak: adres bosken 200 verilir ama resources BOS.
        # Kesif motoru var-olmayan bir odemeli ucu listelememeli.
        govde = pay_modulu({"X402_PAY_TO": ""}).app.test_client().get(
            "/.well-known/x402"
        ).get_json()
        self.assertIs(govde["configured"], False)
        self.assertEqual(govde["resources"], [])
        self.assertIn("X402_PAY_TO", govde["not"])

    def test_manifest_ucun_402_sartlariyla_ayni(self):
        # EN ONEMLI TEST. Manifest ayri elde yazilir; 402 sartlari odeme
        # katmanindan gelir. Ikisi ayri dogrudan ayrilirsa ajan manifesta
        # gore odeme yapar, 402 baska sartlar der, odeme reddedilir.
        yanit, sart = sartlar(self.pay)
        self.assertEqual(yanit.status_code, 402)
        kabul = self.istemci.get("/.well-known/x402").get_json()["resources"][0]["accepts"][0]
        gercek = sart["accepts"][0]
        self.assertEqual(kabul["network"], gercek["network"])
        self.assertEqual(kabul["payTo"], gercek["payTo"])
        self.assertEqual(kabul["scheme"], gercek["scheme"])

    def test_ortam_degisince_manifest_de_degisiyor(self):
        govde = pay_modulu({"X402_NETWORK": "eip155:84532"}).app.test_client().get(
            "/.well-known/x402"
        ).get_json()
        self.assertEqual(govde["resources"][0]["accepts"][0]["network"], "eip155:84532")

    def test_aciklama_metni_iki_yerde_ayni(self):
        # metin kopyasi iki yere yaziliyordu; ortak sabite baglandi.
        self.assertEqual(
            self.istemci.get("/.well-known/x402").get_json()["resources"][0]["description"],
            self.pay.X402_ACIKLAMA,
        )
        _, sart = sartlar(self.pay)
        self.assertEqual(
            sart["resource"]["description"], self.pay.X402_ACIKLAMA
        )

    def test_health_ucu_degismedi(self):
        # yeni adres eklenirken mevcut ucun bozulmamasi
        self.assertEqual(self.istemci.get("/x402/health").status_code, 200)


class TestProbeSaf(unittest.TestCase):
    """health_probe.py saf fonksiyonlari: ag olmadan siniflandirma."""

    def test_checkpoint_basligi_kritik(self):
        self.assertIsNotNone(
            health_probe.checkpoint_isareti({"x-vercel-mitigated": "challenge"}, "")
        )

    def test_checkpoint_govdesi_kritik(self):
        self.assertIsNotNone(
            health_probe.checkpoint_isareti({}, "<html>Security Checkpoint</html>")
        )

    def test_saglikli_vercel_cevabi_checkpoint_sayilmaz(self):
        # REGRESYON: x-vercel-id ve x-vercel-cache BASARILI her Vercel
        # cevabinda gelir. Bunlar guvenlik izi DEGILDIR; sayilirsa probe
        # saglikli ucu CRITIK ilan edip her seferinde yanik alarm verir.
        for baslik in ("x-vercel-id", "x-vercel-cache", "x-vercel-error"):
            with self.subTest(baslik=baslik):
                self.assertIsNone(
                    health_probe.checkpoint_isareti({baslik: "fra1::iad1::x"}, '{"status":"ok"}')
                )
                # ama katman atfedi bunu yine de Vercel olarak tanimlamali
                self.assertEqual(
                    health_probe.katman_belirle({baslik: "fra1::iad1::x"}, "", "x.vercel.app"),
                    "vercel",
                )

    def test_checkpoint_yoksa_katman_app(self):
        self.assertEqual(
            health_probe.katman_belirle({"content-type": "application/json"}, "", "ornek.com"),
            "app",
        )

    def test_baglanti_hatasinda_katman_bilinmiyor(self):
        # timeout/DNS'te katman AYIRT EDILEMEZ; worker ya da app demek tahmin
        # olurdu. "bilinmiyor" dogru cevap.
        self.assertEqual(
            health_probe.katman_belirle({}, "", "ornek.com", "timeout"), "bilinmiyor"
        )

    def test_workers_dev_uzerinde_kalan_checkpoint_workerin_sucludur(self):
        # Worker, upstream'ten gelen guvenlik basligini SOKMASI gerekir.
        # Sokmediyse iz gorunur ve suclu Worker'dir, Vercel degil.
        self.assertEqual(
            health_probe.katman_belirle(
                {"x-vercel-mitigated": "challenge"}, "", "x.workers.dev"
            ),
            "worker",
        )

    def test_worker_kendi_izini_bildiriyorsa_kalan_checkpoint_yine_worker(self):
        self.assertEqual(
            health_probe.katman_belirle(
                {"x-fieldcast-layer": "worker", "x-vercel-mitigated": "challenge"},
                "", "api.alanadi.com",
            ),
            "worker",
        )

    def test_dogrudan_vercel_checkpoint_vercel_sucludur(self):
        self.assertEqual(
            health_probe.katman_belirle({"x-vercel-mitigated": "challenge"}, "", "app.vercel.app"),
            "vercel",
        )


class TestProbeUcler(unittest.TestCase):
    """Yerel sahte sunucuya yapilan GET'ler: HTTP/JSON katmani."""

    def setUp(self):
        self.srv = SaglikliSunucu()
        self.addCleanup(self.srv.kapat)

    def test_saglikli_iki_uc_tamam(self):
        for yol in ("/x402/health", "/.well-known/x402"):
            with self.subTest(yol=yol):
                b = bulgu(yol, self.srv.isim)
                self.assertEqual(b.durum, health_probe.TAMAM)
                self.assertEqual(b.kod, 200)

    def test_403_kritik(self):
        self.srv.sahneyi_ayarla({"/x402/health": (403, {}, "<html>Forbidden</html>")})
        b = bulgu("/x402/health", self.srv.isim)
        self.assertEqual(b.durum, health_probe.KRITIK)
        self.assertIn("403", b.mesaj)

    def test_5xx_kritik(self):
        self.srv.sahneyi_ayarla({"/x402/health": (502, {}, "bad gateway")})
        b = bulgu("/x402/health", self.srv.isim)
        self.assertEqual(b.durum, health_probe.KRITIK)
        self.assertIn("502", b.mesaj)

    def test_404_kritik(self):
        # /.well-known/x402 canlida 404 donuyordu; bu bir "uc yok" durumu.
        self.srv.sahneyi_ayarla({})
        b = bulgu("/.well-known/x402", self.srv.isim)
        self.assertEqual(b.durum, health_probe.KRITIK)
        self.assertEqual(b.kod, 404)

    def test_checkpoint_sayfasi_kritik(self):
        self.srv.sahneyi_ayarla({
            "/x402/health": (200, {"x-vercel-mitigated": "challenge"},
                             "<html>Security Checkpoint</html>"),
        })
        b = bulgu("/x402/health", self.srv.isim)
        self.assertEqual(b.durum, health_probe.KRITIK)
        self.assertEqual(b.katman, "vercel")
        self.assertIn("checkpoint", b.mesaj)

    def test_200_ama_html_govde_kritik(self):
        # isaret basligi olmadan HTML donen checkpoint varyanti
        self.srv.sahneyi_ayarla({"/x402/health": (200, {}, "<html>bot check</html>")})
        b = bulgu("/x402/health", self.srv.isim)
        self.assertEqual(b.durum, health_probe.KRITIK)
        self.assertIn("JSON", b.mesaj)

    def test_200_ama_eksik_alan_kritik(self):
        # canlidaki eski surumun hali: 200 + JSON ama eksik alan
        self.srv.sahneyi_ayarla({
            "/x402/health": (200, {}, {"status": "ok", "network": "eip155:84532", "testnet": True}),
        })
        b = bulgu("/x402/health", self.srv.isim)
        self.assertEqual(b.durum, health_probe.KRITIK)
        self.assertIn("eksik alan", b.mesaj)

    def test_yapilandirilmamis_uc_uyari(self):
        self.srv.sahneyi_ayarla({
            "/x402/health": dict(SAHTE_SAGLIKLI["/x402/health"], status="not_configured"),
        })
        b = bulgu("/x402/health", self.srv.isim)
        self.assertEqual(b.durum, health_probe.UYARI)

    def test_timeout_kritik_ve_katman_bilinmiyor(self):
        # 1 saniyelik zaman asimi; sagit sunucu yerine kullanilmayan port.
        b = bulgu("/x402/health", "http://127.0.0.1:1", zaman=1.0)
        self.assertEqual(b.durum, health_probe.KRITIK)
        self.assertEqual(b.katman, "bilinmiyor")


class TestProbeCikisKodu(unittest.TestCase):
    """0 saglikli / 1 CRITIK / 2 komut hatasi. Cron ve CI buna bakiyor."""

    def _calistir(self, *args):
        return subprocess.run(
            [sys.executable, PROBE_PY] + list(args),
            capture_output=True, text=True, timeout=90,
        )

    def test_saglikli_sunucuda_sifir(self):
        with SaglikliSunucu() as srv:
            sonuc = self._calistir("--url", srv.isim, "--timeout", "10")
        self.assertEqual(sonuc.returncode, 0, sonuc.stdout + sonuc.stderr)
        self.assertIn("saglikli", sonuc.stdout)

    def test_checkpoint_sunucusunda_bir(self):
        with SaglikliSunucu() as srv:
            srv.sahneyi_ayarla({
                "/x402/health": (200, {"x-vercel-mitigated": "challenge"},
                                 "<html>Security Checkpoint</html>"),
            })
            sonuc = self._calistir("--url", srv.isim, "--timeout", "10")
        self.assertEqual(sonuc.returncode, 1, sonuc.stdout)
        self.assertIn("CRITIK", sonuc.stdout)

    def test_403_sunucusunda_bir(self):
        with SaglikliSunucu() as srv:
            srv.sahneyi_ayarla({"/x402/health": (403, {}, "no")})
            sonuc = self._calistir("--url", srv.isim, "--timeout", "10")
        self.assertEqual(sonuc.returncode, 1, sonuc.stdout)

    def test_json_ciktisi_gecerli_ve_katmani_yazar(self):
        with SaglikliSunucu() as srv:
            srv.sahneyi_ayarla({"/.well-known/x402": (403, {}, "no")})
            sonuc = self._calistir("--url", srv.isim, "--timeout", "10", "--json")
        self.assertEqual(sonuc.returncode, 1)
        rapor = json.loads(sonuc.stdout)
        self.assertEqual(rapor["sonuc"], "kritik")
        yollar = [b["path"] for b in rapor["bulgular"]]
        self.assertIn("/.well-known/x402", yollar)

    def test_schemi_olmayan_url_iki(self):
        self.assertEqual(self._calistir("--url", "ftp://ornek.com").returncode, 2)

    def test_strict_uyarida_bir(self):
        # Varsayilan yalnizca CRITIK sayar; --strict uyarilari da sayar.
        with SaglikliSunucu() as srv:
            srv.sahneyi_ayarla(
                {"/.well-known/x402": dict(
                    SAHTE_SAGLIKLI["/.well-known/x402"], configured=False)},
                birlestir=True,
            )
            normal = self._calistir("--url", srv.isim, "--timeout", "10")
            sert = self._calistir("--url", srv.isim, "--timeout", "10", "--strict")
        self.assertEqual(normal.returncode, 0, normal.stdout)
        self.assertEqual(sert.returncode, 1, sert.stdout)


class TestSarmalayici(unittest.TestCase):
    """scripts/health_probe.sh: ciktiyi bozmaz, cikis kodunu gecirir."""

    def setUp(self):
        self.yorumlayici = _proje_yorumlayicisi() or sys.executable

    def test_dosya_var_ve_calistirilabilir(self):
        self.assertTrue(os.path.isfile(PROBE_SH))
        self.assertTrue(os.access(PROBE_SH, os.X_OK), "health_probe.sh calistirilabilir degil")

    def test_saglikli_sunucuda_sifir(self):
        with SaglikliSunucu() as srv:
            sonuc = subprocess.run(
                ["/bin/bash", PROBE_SH, "--url", srv.isim, "--timeout", "10"],
                capture_output=True, text=True, timeout=120,
                env=dict(os.environ, FIELDCAST_PROBE_PYTHON=self.yorumlayici),
            )
        self.assertEqual(sonuc.returncode, 0, sonuc.stdout + sonuc.stderr)
        self.assertIn("saglikli", sonuc.stdout)

    def test_bozuk_sunucuda_bir(self):
        with SaglikliSunucu() as srv:
            srv.sahneyi_ayarla({"/x402/health": (500, {}, "boom")})
            sonuc = subprocess.run(
                ["/bin/bash", PROBE_SH, "--url", srv.isim, "--timeout", "10"],
                capture_output=True, text=True, timeout=120,
                env=dict(os.environ, FIELDCAST_PROBE_PYTHON=self.yorumlayici),
            )
        self.assertEqual(sonuc.returncode, 1, sonuc.stdout)
        self.assertIn("CRITIK", sonuc.stdout)

    def test_bos_url_hatasi_iki(self):
        sonuc = subprocess.run(
            ["/bin/bash", PROBE_SH, "--url", "ornek.com"],
            capture_output=True, text=True, timeout=120,
            env=dict(os.environ, FIELDCAST_PROBE_PYTHON=self.yorumlayici),
        )
        self.assertEqual(sonuc.returncode, 2)


WORKER_JS = os.path.join(REPO_ROOT, "worker", "x402-proxy.js")

# Worker testleri icin Node harness'i. Repo kokunde package.json yok; node
# .js dosyasini CommonJS sayar ve `export` patlar. Bu yuzden dosya data: URL
# olarak ice aktarilir (ESM olmaya zorlanir). Boylece ne paket kurulur ne de
# repoya dosya eklenir.
NODE_HARNESS = r"""
import { readFileSync } from "node:fs";
const kaynak = readFileSync(process.env.FC_WORKER_JS, "utf8");
const mod = await import("data:text/javascript;base64," + Buffer.from(kaynak).toString("base64"));
const isler = JSON.parse(process.argv[2]);
const sonuclar = [];
const hataLoglari = [];
const eskiError = console.error;
console.error = (...a) => hataLoglari.push(a.map(String).join(" "));

/*
 * JSON'a cevirirken `Headers` DUZ NESNEYE indirgenir.
 * Gerekce: Headers'in verisi sembolik dizidedir, JSON.stringify onu `{}`
 * yazar. Boylece python tarafinda `cikti.get("x-payment")` None doner ve
 * korunmus basliklar sessizce kaybolmus gibi gorunur (gercek ciktida
 * basliklar vardir). Diziler haric: Array.prototype.entries de vardir.
 */
const duz = (d) =>
  d && !Array.isArray(d) && typeof d.entries === "function"
    ? Object.fromEntries(d.entries())
    : d;

for (const is of isler) {
  try {
    if (is.tip === "saf" || is.tip === "saf-baslik") {
      const girdi = is.girdi.slice();
      if (is.tip === "saf-baslik") {
        // Uretimdeki girdi tipi: gercek Headers NESNESI. Diziden Headers
        // kurulur; Worker'in her iki girdiyi de kabul ettigi dogrudan
        // denenir (JSON, Headers'i tasiyamadigi icin bu sart).
        girdi[is.sira || 0] = new Headers(girdi[is.sira || 0]);
      }
      sonuclar.push({ ok: true, deger: duz(mod[is.ad](...girdi)) });
    } else if (is.tip === "fetch") {
      const istek = new Request(is.url, {
        method: is.method || "GET",
        headers: is.headers || {},
        body: is.body,
      });
      const yanit = await mod.default.fetch(istek, is.env || {});
      sonuclar.push({
        ok: true,
        status: yanit.status,
        headers: Object.fromEntries([...yanit.headers.entries()]),
        govde: await yanit.text(),
      });
    } else {
      sonuclar.push({ ok: false, hata: "bilinmeyen is tipi: " + is.tip });
    }
  } catch (hata) {
    sonuclar.push({ ok: false, hata: String(hata && hata.message ? hata.message : hata) });
  }
}
console.error = eskiError;
sonuclar.push({ ok: true, __loglar__: hataLoglari });
process.stdout.write(JSON.stringify(sonuclar));
"""


def node_var_mi():
    try:
        subprocess.run(["node", "-v"], capture_output=True, timeout=30)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def worker_calistir(isler):
    """Worker'in saf fonksiyonlarini / fetch()'ini node icinde cagirir.

    Doner: (sonuclar, hata_loglari). Worker'in console.error ciktisi ayrica
    toplanir; "hata durumunda hangi katmanin suclu oldugu loglanir" kurali
    bu yolla denetlenir.
    """
    if not node_var_mi():
        raise unittest.SkipTest("node bulunamadi; Worker testleri atlandi")
    import tempfile

    with tempfile.TemporaryDirectory() as gecici:
        yol = os.path.join(gecici, "harness.mjs")
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write(NODE_HARNESS)
        sonuc = subprocess.run(
            ["node", yol, json.dumps(isler)],
            capture_output=True, text=True, timeout=120,
            env=dict(os.environ, FC_WORKER_JS=WORKER_JS),
        )
    if sonuc.returncode != 0:
        raise AssertionError("node harness basarisiz: %s" % sonuc.stderr[-800:])
    veri = json.loads(sonuc.stdout)
    loglar = veri.pop().get("__loglar__", []) if veri else []
    return veri, loglar


def worker_tek(gorev):
    """Tek bir gorevi calistirir; hata varsa testi kirar."""
    veri, loglar = worker_calistir([gorev])
    sonuc = veri[0]
    if not sonuc.get("ok"):
        raise AssertionError("Worker cagrisi basarisiz: %s" % sonuc.get("hata"))
    sonuc["loglar"] = loglar
    return sonuc


ODEME_ENV = {
    "X402_PAY_TO": ANA_ADRES,
    "X402_NETWORK": MAINNET,
    "X402_PRICE": "$0.01",
    "X402_FACILITATOR_URL": PAYAI,
}

# Upstream'in dondurdugu sahte 402. PAYMENT-REQUIRED base64 JSON'dir (x402 v2).
SAHTE_SART = base64.b64encode(json.dumps({
    "x402Version": 2,
    "accepts": [{"scheme": "exact", "network": MAINNET, "payTo": ANA_ADRES,
                 "price": "$0.01"}],
}).encode()).decode()

# Istemcinin Worker'a gonderdigi sahte odeme basligi (odeme yapilmis istek).
SAHTE_ODEME = base64.b64encode(json.dumps({
    "x402Version": 2,
    "scheme": "exact",
    "network": MAINNET,
    "payload": {"authorization": {"from": ANA_ADRES, "value": "10000"}},
}).encode()).decode()


class TestWorkerSaf(unittest.TestCase):
    """worker/x402-proxy.js saf fonksiyonlari."""

    def test_yol_siniflandirma(self):
        beklenen = {
            "/x402/health": "api",
            "/x402/extract": "api",
            "/x402/": "api",
            "/.well-known/x402": "api",
            "/health": "api",
            "/v1/extract": "api",
            "/v1/": "api",
            "/": "site",
            "/docs": "site",
            "/alternatives/notion": "yok",
            "/privacy.html": "yok",
        }
        for yol, sonuc in beklenen.items():
            with self.subTest(yol=yol):
                self.assertEqual(worker_tek(
                    {"tip": "saf", "ad": "siniflandir", "girdi": [yol]}
                )["deger"], sonuc)

    def test_sorgu_dizesi_siniflandirmayi_bozmaz(self):
        self.assertEqual(worker_tek(
            {"tip": "saf", "ad": "siniflandir", "girdi": ["/x402/health?a=1"]}
        )["deger"], "api")

    def test_origin_verilmezse_null(self):
        # uydurma adrese istek atmamak: Worker "bilmiyorum" demeli
        self.assertIsNone(worker_tek(
            {"tip": "saf", "ad": "originUrl", "girdi": [{}, "/x402/health"]}
        )["deger"])

    def test_origin_son_slash_alinir(self):
        deger = worker_tek({
            "tip": "saf", "ad": "originUrl",
            "girdi": [{"X402_ORIGIN": "https://orijin.example/"}, "/x402/health"],
        })["deger"]
        self.assertEqual(deger, "https://orijin.example/x402/health")

    def test_manifest_pay_to_bosken_odeme_kaydi_yok(self):
        deger = worker_tek({
            "tip": "saf", "ad": "kesifManifesti",
            "girdi": [{}, "https://api.example"],
        })["deger"]
        self.assertIs(deger["configured"], False)
        self.assertEqual(deger["resources"], [])

    def test_manifest_env_degerlerini_yansitir(self):
        deger = worker_tek({
            "tip": "saf", "ad": "kesifManifesti",
            "girdi": [dict(ODEME_ENV, X402_NETWORK="eip155:84532"), "https://api.example"],
        })["deger"]
        self.assertIs(deger["configured"], True)
        kabul = deger["resources"][0]["accepts"][0]
        self.assertEqual(kabul["network"], "eip155:84532")
        self.assertEqual(kabul["payTo"], ANA_ADRES)
        self.assertEqual(kabul["price"], "$0.01")
        self.assertEqual(deger["facilitator"], PAYAI)
        self.assertEqual(deger["resources"][0]["path"], "/x402/extract")

    def test_checkpoint_basligi_tespit_edilir(self):
        deger = worker_tek({
            "tip": "saf", "ad": "guvenlikIsareti",
            "girdi": [200, [["x-vercel-mitigated", "challenge"]], ""],
        })["deger"]
        self.assertIsNotNone(deger)
        self.assertEqual(deger["tur"], "baslik")

    def test_checkpoint_govdesi_tespit_edilir(self):
        deger = worker_tek({
            "tip": "saf", "ad": "guvenlikIsareti",
            "girdi": [200, [], "<html>Security Checkpoint</html>"],
        })["deger"]
        self.assertEqual(deger["tur"], "govde")

    def test_saglikli_vercel_cevabi_checkpoint_sayilmaz(self):
        # x-vercel-id BASARILI cevaplarda da gelir. Sayilirsa Worker her
        # saglikli cevabi guvenlik sayfasina sanir ve API'yi kapatir.
        self.assertIsNone(worker_tek({
            "tip": "saf", "ad": "guvenlikIsareti",
            "girdi": [200, [["x-vercel-id", "fra1::iad1::x"], ["x-vercel-cache", "MISS"]], '{"status":"ok"}'],
        })["deger"])

    def test_hata_kodunda_katman_okunur(self):
        # 5xx + vercel izi -> suclu vercel; iz yoksa uygulama
        self.assertEqual(worker_tek({
            "tip": "saf", "ad": "hataKatmani",
            "girdi": [502, [["x-vercel-id", "fra1::iad1::x"]]],
        })["deger"], "vercel")
        self.assertEqual(worker_tek({
            "tip": "saf", "ad": "hataKatmani", "girdi": [502, []],
        })["deger"], "app")

    def test_set_cookie_ve_mitigated_cikis_yapmaz(self):
        cikti = worker_tek({
            "tip": "saf", "ad": "temizleBasliklar",
            "girdi": [[
                ["set-cookie", "__vercel_lb=a; Path=/"],
                ["x-vercel-mitigated", "challenge"],
                ["x-vercel-id", "fra1::iad1::x"],
                ["content-type", "application/json"],
                ["payment-required", "eyJ4NDAyVmVyc2lvbiI6Mn0="],
            ]],
        })["deger"]
        self.assertIsNone(cikti.get("set-cookie"))
        self.assertIsNone(cikti.get("x-vercel-mitigated"))
        self.assertIsNone(cikti.get("x-vercel-id"))
        self.assertEqual(cikti.get("content-type"), "application/json")
        # 402 sartlari KALIR
        self.assertEqual(cikti.get("payment-required"), "eyJ4NDAyVmVyc2lvbiI6Mn0=")
        self.assertEqual(cikti.get("x-fieldcast-layer"), "worker")

    def test_istemci_cookiesi_upstream_e_gitmez(self):
        cikti = worker_tek({
            "tip": "saf", "ad": "istemciBasliklariniSec",
            "girdi": [[
                ["cookie", "oturum=abc"],
                ["host", "eski.example"],
                ["x-payment", "odeme"],
                ["content-type", "application/json"],
                ["x-api-key", "demo_key_public"],
            ]],
        })["deger"]
        self.assertIsNone(cikti.get("cookie"))
        self.assertIsNone(cikti.get("host"))
        self.assertEqual(cikti.get("x-payment"), "odeme")
        self.assertEqual(cikti.get("x-api-key"), "demo_key_public")

    def test_gercek_headers_nesnesi_ile_de_calisir(self):
        """JSON Headers'i tasiyamaz; testler cift dizisiyle cagirir.

        Bu yuzden Worker'da baslik gezen yardimcilar HER IKI girdiyi de
        kabul etmeli. Yalnizca dizi calisiyorsa uretimdeki `Headers` yolu
        (fetch cevabi) sessizce bozulur; yalnizca Headers calisiyorsa test
        girdisi patlar. Ikisini de dogrudan dener.
        """
        cikti = worker_tek({
            "tip": "saf-baslik", "ad": "temizleBasliklar",
            "girdi": [[
                ["set-cookie", "__vercel_lb=a; Path=/"],
                ["x-vercel-mitigated", "challenge"],
                ["content-type", "application/json"],
                ["payment-required", "eyJ4NDAyVmVyc2lvbiI6Mn0="],
            ]],
        })["deger"]
        self.assertIsNone(cikti.get("set-cookie"))
        self.assertIsNone(cikti.get("x-vercel-mitigated"))
        self.assertEqual(cikti.get("content-type"), "application/json")
        self.assertEqual(cikti.get("payment-required"), "eyJ4NDAyVmVyc2lvbiI6Mn0=")

        cikti = worker_tek({
            "tip": "saf-baslik", "ad": "istemciBasliklariniSec",
            "girdi": [[["cookie", "oturum=abc"], ["x-payment", "odeme"]]],
        })["deger"]
        self.assertIsNone(cikti.get("cookie"))
        self.assertEqual(cikti.get("x-payment"), "odeme")

    def test_bos_baslik_girdisi_patlamaz(self):
        # Headers yerine null/bos gecerse cevap yine uretilmeli; yoksa
        # Worker'in kendi hatasi upstream'e hic ulasmadan 502 olur.
        self.assertIsNone(worker_tek(
            {"tip": "saf", "ad": "guvenlikIsareti", "girdi": [200, None, ""]}
        )["deger"])
        self.assertEqual(worker_tek(
            {"tip": "saf", "ad": "temizleBasliklar", "girdi": [None]}
        )["deger"].get("x-fieldcast-layer"), "worker")


class TestWorkerUctanUca(unittest.TestCase):
    """Worker.fetch() gercekten calisiyor mu: yerel sahte origin'e karsi.

    Worker'in upstream'i X402_ORIGIN ile verilir ve deger 127.0.0.1'e
    yazilir; node edge'de degil yerelde calistigi icin localhost'a
    ulasabiliyor. Boylece proxy zinciri bastan sona denenir.
    """

    def setUp(self):
        self.srv = SaglikliSunucu()
        self.addCleanup(self.srv.kapat)
        self.env = dict(ODEME_ENV, X402_ORIGIN=self.srv.isim,
                        SITE_URL="https://site.example")

    def _fetch(self, yol, method="GET", govde=None, basliklar=None, env=None):
        return worker_tek({
            "tip": "fetch",
            "url": "https://api.example" + yol,
            "method": method,
            "headers": basliklar or {},
            "body": govde,
            "env": env if env is not None else self.env,
        })

    def test_saglikli_health_aktarilir(self):
        yanit = self._fetch("/x402/health")
        self.assertEqual(yanit["status"], 200)
        self.assertEqual(json.loads(yanit["govde"])["status"], "ok")
        self.assertEqual(yanit["headers"]["x-fieldcast-layer"], "worker")

    def test_odemesiz_istekte_402_ve_sartlar_korunur(self):
        # EN KRITIK TEST: Worker araya girince 402 bozulursa ajan odeme
        # sartlarini goremez ve hicbir sey satin alamaz.
        self.srv.sahneyi_ayarla({
            "/x402/extract": (402, {"PAYMENT-REQUIRED": SAHTE_SART},
                             json.dumps({"error": "Payment required"})),
        }, birlestir=True)
        yanit = self._fetch("/x402/extract", method="POST",
                            basliklar={"content-type": "application/json"},
                            govde=json.dumps({"text": "x", "fields": ["a"]}))
        self.assertEqual(yanit["status"], 402)
        self.assertEqual(yanit["headers"]["payment-required"], SAHTE_SART)
        self.assertEqual(yanit["headers"]["x-fieldcast-route"], "x402-payment-required")
        self.assertEqual(yanit["headers"]["cache-control"], "no-store")

    def test_post_govdesi_odeme_basligi_upstream_e_ulasir(self):
        """Odeme YAPILMIS istek de ayni kapidan gecer.

        Iki seyi birden kilitler:
          - govde akis olarak iletilir (Worker govdeyi dusurmezse sunucu
            bos JSON gorur; odeme yapilan istek bos metne duser),
          - odeme basligi (x-payment) upstream'e ulasir, cookie GIDMEZ.
        Odeme dogrulamasi sunucuda yapilir; bu baslik olmadan sunucu
        istegi 402'de tutar, yani ajan odemeyi yapsa bile sonuc gelmez.
        """
        self.srv.sahneyi_ayarla({
            "/x402/extract": (200, {"Content-Type": "application/json"},
                             json.dumps({"total": 42})),
        }, birlestir=True)
        istek_govdesi = json.dumps({"text": "INVOICE 1", "fields": ["total"]})
        yanit = self._fetch("/x402/extract", method="POST",
                            basliklar={"content-type": "application/json",
                                       "cookie": "oturum=abc",
                                       "x-payment": SAHTE_ODEME},
                            govde=istek_govdesi)
        self.assertEqual(yanit["status"], 200)
        kayit = self.srv.son_kayit("/x402/extract")
        self.assertEqual(kayit["method"], "POST")
        self.assertEqual(json.loads(kayit["govde"])["text"], "INVOICE 1")
        self.assertEqual(kayit["basliklar"].get("x-payment"), SAHTE_ODEME)
        self.assertIsNone(kayit["basliklar"].get("cookie"))

    def test_upstream_checkpoint_sayfasi_gecirilmez(self):
        # Guvenlik sayfasini gecmek 200 + HTML donen sahte uc yaratirdi.
        # Worker 502 + layer=vercel donmeli.
        self.srv.sahneyi_ayarla({
            "/x402/health": (200, {"x-vercel-mitigated": "challenge"},
                             "<html>Security Checkpoint</html>"),
        }, birlestir=True)
        yanit = self._fetch("/x402/health")
        self.assertEqual(yanit["status"], 502)
        govde = json.loads(yanit["govde"])
        self.assertEqual(govde["layer"], "vercel")
        self.assertNotIn("Security Checkpoint", yanit["govde"])
        self.assertEqual(yanit["headers"]["x-fieldcast-upstream"], "vercel")

    def test_upstream_set_cookie_cikis_yapmaz(self):
        self.srv.sahneyi_ayarla({
            "/x402/health": (200, {"set-cookie": "__vercel_lb=gizli; Path=/"},
                             SAHTE_SAGLIKLI["/x402/health"]),
        }, birlestir=True)
        yanit = self._fetch("/x402/health")
        self.assertEqual(yanit["status"], 200)
        self.assertIsNone(yanit["headers"].get("set-cookie"))

    def test_origin_ayarli_degilse_503_ve_suclu_worker(self):
        yanit = self._fetch("/x402/health", env=dict(ODEME_ENV))
        self.assertEqual(yanit["status"], 503)
        govde = json.loads(yanit["govde"])
        self.assertEqual(govde["error"], "origin_not_configured")
        self.assertEqual(govde["layer"], "worker")

    def test_origin_oldeyse_502_ve_suclu_worker(self):
        # Dinlenmeyen port: Worker upstream'e ulasamadi -> katman Worker.
        olu = {"X402_ORIGIN": "http://127.0.0.1:1", "X402_TIMEOUT_MS": "1500"}
        yanit = self._fetch("/x402/health", env=dict(ODEME_ENV, **olu))
        self.assertEqual(yanit["status"], 502)
        self.assertEqual(json.loads(yanit["govde"])["layer"], "worker")

    def test_upstream_5xx_suclusu_isaretlenir_ve_loglanir(self):
        self.srv.sahneyi_ayarla({
            "/x402/health": (500, {}, json.dumps({"error": "boom"})),
        }, birlestir=True)
        yanit, loglar = worker_calistir([{
            "tip": "fetch", "url": "https://api.example/x402/health",
            "method": "GET", "headers": {}, "env": self.env,
        }])
        yanit = yanit[0]
        self.assertEqual(yanit["status"], 500)
        self.assertEqual(yanit["headers"]["x-fieldcast-error"], "app")
        self.assertTrue(any("katman=app" in l for l in loglar),
                        "Worker hatasi loglanmadi: %r" % (loglar,))

    def test_resmi_site_yollari_yonlendirilir(self):
        for yol in ("/", "/docs"):
            with self.subTest(yol=yol):
                yanit = self._fetch(yol)
                self.assertEqual(yanit["status"], 302)
                self.assertEqual(yanit["headers"]["location"], "https://site.example" + yol.rstrip("/"))
                self.assertEqual(yanit["headers"]["x-fieldcast-route"], "official-site")

    def test_kesif_manifesti_worker_env_inden_gelir(self):
        # origin'e gitmeden uretilir; manifest ayni sozlesmeyi paylasir
        yanit = self._fetch("/.well-known/x402")
        self.assertEqual(yanit["status"], 200)
        govde = json.loads(yanit["govde"])
        self.assertIs(govde["configured"], True)
        self.assertEqual(govde["resources"][0]["path"], "/x402/extract")
        self.assertEqual(govde["facilitator"], PAYAI)

    def test_bilinmeyen_yol_404_ve_worker_katmani(self):
        yanit = self._fetch("/alternatives/x")
        self.assertEqual(yanit["status"], 404)
        self.assertEqual(json.loads(yanit["govde"])["layer"], "worker")

    def test_options_on_kontrolu(self):
        yanit = self._fetch("/x402/extract", method="OPTIONS")
        self.assertEqual(yanit["status"], 204)
        self.assertEqual(yanit["headers"]["access-control-allow-origin"], "*")

    def test_probe_worker_adresine_getirilince_saglikli(self):
        # Uctan uca zincir: Worker -> yerel origin -> saglikli cevap. Probu
        # Worker adresine gosterdiginde 0 donmeli.
        sonuc = subprocess.run(
            [sys.executable, PROBE_PY, "--url", self.srv.isim, "--timeout", "10"],
            capture_output=True, text=True, timeout=90,
        )
        self.assertEqual(sonuc.returncode, 0, sonuc.stdout + sonuc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)