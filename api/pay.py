# -*- coding: utf-8 -*-
"""Fieldcast x402 ucu — ajanlarin hesapsiz, cagri basi odeyerek kullandigi yuz.

Fark: X-API-Key yok. Odemesiz istek HTTP 402 + odeme sartlari doner; ajan
zincir uzerinde USDC oder ve cevabi ayni akista alir.

AG SECIMI:
  Public x402.org/facilitator mainnet'i TASIYAMAZ; /supported ciktisinda aglar
  sadece test aglari (eip155:84532 var, eip155:8453 yok). Test agi yolu
  https://facilitator.payai.network adresini kullanir (X402_FACILITATOR_URL).
  Ana ag (eip155:8453) ayri yoldur: facilitator yapilandirmasi CDP_API_KEY_ID
  ve CDP_API_KEY_SECRET ortam degiskenlerinden uretilir. Anahtar yoksa uc
  HTTP 503 doner; ag eip155:84532 yapilmaz. Anahtarlar koda gomulmez.
  Anahtar varken gercek USDC akabilir. Fiyat $0.01/cag.
  Test agi: X402_NETWORK=eip155:84532 (sanal para, CDP anahtari istemez).

DEPLOY GUVENLIGI: adres varsayilandir, ama X402_PAY_TO="" ile BOS birakilirsa
surec COKMEZ; uc 503 doner ve sebebini soyler. Boylece adres geri alinmak
istendiginde uc bedava cikarim servisine donusmez.
"""
import os
import sys

# Vercel her giris noktasini yol uzerinden import ediyor ve api/ klasorunu
# sys.path'e KOYMUYOR -> "No module named 'index'" ile fonksiyon komple coker.
# Kendi klasorumuzu yola ekliyoruz; yerelde de ayni sekilde calisir.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, g, jsonify, request

# Cikarim mantigi tek yerde durur (api/index.py); burada yeniden yazilmaz.
from index import db, extract_fields, read_document_from_request, record_call

# Ucunun kimligi. Hepsi ENV ile override edilebilir; Vercel'de .env yazilir.
# X402_PAY_TO="" verilirse adres bilerek boslasir -> uc 503 doner (asagiya bak).
# Ana ag facilitator'i PayAI degil: CDP anahtarindan uretilir (asagiya bak).
PAY_TO = os.environ.get(
    "X402_PAY_TO", "0x3f425d6ffd2855585483d65da684651e330759e0"
).strip()
NETWORK = os.environ.get("X402_NETWORK", "eip155:8453").strip()
PRICE = os.environ.get("X402_PRICE", "$0.01").strip()
FACILITATOR_URL = os.environ.get(
    "X402_FACILITATOR_URL", "https://facilitator.payai.network"
).strip()

# Tek kural: Base mainnet degilse sanal para. Boylece "hangi ag?" sorusu
# gizli kalmaz; /x402/health bunu musteriye de soyler (asagida).
ANA_AG = "eip155:8453"
IS_TESTNET = NETWORK != ANA_AG
# CDP facilitator adresi (Coinbase CDP SDK: api.cdp.coinbase.com + /platform/v2/x402).
# Anahtarlar burada durmaz; yalnizca CDP_API_KEY_ID / CDP_API_KEY_SECRET okunur.
CDP_FACILITATOR_URL = "https://api.cdp.coinbase.com/platform/v2/x402"
ANA_AG_ANAHTAR_MESAJI = "ana ag icin CDP anahtari gerekli"


def cdp_anahtari():
    """CDP anahtar cifti. Biri bile bos ise ana ag facilitator'i kurulamaz."""
    key_id = os.environ.get("CDP_API_KEY_ID", "").strip()
    secret = os.environ.get("CDP_API_KEY_SECRET", "").strip()
    if key_id and secret:
        return key_id, secret
    return None


def cdp_create_headers(key_id, secret):
    """CDP SDK create_headers sozlesmesi. Import, baslik istenene kadar ertelenir."""

    def create_headers():
        try:
            from cdp.x402 import create_cdp_auth_headers
        except ImportError as exc:
            raise RuntimeError(
                "ana ag facilitator basligi icin cdp paketi gerekli"
            ) from exc
        return create_cdp_auth_headers(key_id, secret)()

    return create_headers


def facilitator_ayari_kur():
    """Testnet ile ana ag facilitator ayarini ayri uret.

    Ana ag anahtarsizsa (None, mesaj) doner. NETWORK degerini degistirmez;
    eip155:8453 anahtarsizken eip155:84532'ye dusulmez.
    """
    if NETWORK == ANA_AG:
        anahtar = cdp_anahtari()
        if anahtar is None:
            return None, ANA_AG_ANAHTAR_MESAJI
        key_id, secret = anahtar
        return {
            "url": CDP_FACILITATOR_URL,
            "network": ANA_AG,
            "create_headers": cdp_create_headers(key_id, secret),
        }, None
    return {
        "url": FACILITATOR_URL,
        "network": NETWORK,
        "create_headers": None,
    }, None


FACILITATOR_AYARI, ANA_AG_HATASI = facilitator_ayari_kur()
AG_ETIKETI = (
    "Base (ana ag, gercek USDC)" if not IS_TESTNET
    else f"test agi ({NETWORK}, sanal para)"
)

# Aciklamasi iki yerde kullaniliyor (odeme katmani ROUTES + kesif ucu). Tek
# yerde tutulur ki biri guncellenince digeri geride kalmasin; kesif manifesti
# ile 402 sartlari ayni metni gostermeye devam etsin.
X402_ACIKLAMA = (
    "Extract structured data from a document. Send raw text or a PDF plus the "
    "list of field names you want, and receive those fields back as typed JSON. "
    "Fields that do not appear in the document are returned as null rather than "
    "invented. Useful for invoices, receipts, contracts, forms and reports."
)

app = Flask(__name__)


@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-PAYMENT"
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    return resp


@app.get("/x402")
@app.get("/x402/")
def index_route():
    return jsonify(
        {
            "service": "Fieldcast (x402)",
            "description": "Turn PDFs and raw text into structured JSON. Pay per call in USDC.",
            "endpoints": {"POST /x402/extract": "paid", "GET /x402/health": "free"},
            "price": PRICE,
            "network": NETWORK,
            "testnet": IS_TESTNET,
            "para": "sanal" if IS_TESTNET else "GERCEK USDC",
            "configured": bool(PAY_TO) and not ANA_AG_HATASI,
        }
    )


@app.get("/x402/health")
def health():
    """Ucretsiz. Hangi agda oldugunu ve para gercek mi sanal mi ACIKCA yazar.

    Musteri "0.01 USDC" gorup gercek sanmak riski: testnet'te para yoktur.
    Bu yuzden network TEK basina birakilmadi; network + testnet bayragi +
    insan diliyle etiket birlikte doner.
    """
    return jsonify(
        {
            "status": "ok" if PAY_TO and not ANA_AG_HATASI else "not_configured",
            "network": NETWORK,
            "testnet": IS_TESTNET,
            "para": "sanal" if IS_TESTNET else "GERCEK USDC",
            "aciklama": AG_ETIKETI,
            "price": PRICE,
            "pay_to": PAY_TO,
            "facilitator": (
                FACILITATOR_AYARI["url"]
                if FACILITATOR_AYARI
                else (CDP_FACILITATOR_URL if NETWORK == ANA_AG else FACILITATOR_URL)
            ),
            **({"ana_ag_hata": ANA_AG_HATASI} if ANA_AG_HATASI else {}),
        }
    )


@app.get("/.well-known/x402")
def well_known_x402():
    """Kesif ucu: ucun ne sundugunu ajanlara/kesif motorlarina duyurur.

    Neden ayri bir dosya degil de uc: ajanlar once ucu dener, 404 alirsa
    "bu hizmet odemeli degil" sanir. Canli 5 Eki 2026'da bu adres 404 donuyordu
    (x-vercel-error: NOT_FOUND); o yuzden eklendi.

ICERIK UYDURULMAZ: manifest, odeme katmaninin gercekten kullandigi
    PAY_TO/NETWORK/PRICE/X402_ACIKLAMA degerlerinden turetilir; ayni degerler
    odemesiz istegin dondurecegi 402 sartlarinda da kullanilir. Boylece
    manifest ile 402 ayni kaynaktan gelir, biri degisince digeri geride kalmaz.

    Odeme yapilandirilmadiysa "configured": false doner ve resources BOS
    kalir; 200 verilir ama ucretli uc ilan edilmez. Boylece kesif motoru
    var-olmayan bir odemeli ucu listelemez.
    """
    kaynak = request.url_root.rstrip("/")
    if not PAY_TO or ANA_AG_HATASI:
        return jsonify(
            {
                "x402Version": 2,
                "service": {"name": "Fieldcast", "url": kaynak},
                "configured": False,
                "resources": [],
                "health": "/x402/health",
                "not": (
                    ANA_AG_ANAHTAR_MESAJI
                    if ANA_AG_HATASI and PAY_TO
                    else "X402_PAY_TO is not set on this deployment; "
                    "no paid endpoint is published here."
                ),
            }
        )

    return jsonify(
        {
            "x402Version": 2,
            "service": {
                "name": "Fieldcast",
                "url": kaynak,
                "description": "Turn PDFs and raw text into structured JSON. Pay per call in USDC.",
            },
            "configured": True,
            "facilitator": (
                FACILITATOR_AYARI["url"] if FACILITATOR_AYARI else FACILITATOR_URL
            ),
            "health": "/x402/health",
            "resources": [
                {
                    "method": "POST",
                    "path": "/x402/extract",
                    "mimeType": "application/json",
                    "description": X402_ACIKLAMA,
                    "accepts": [
                        {
                            "scheme": "exact",
                            "network": NETWORK,
                            "payTo": PAY_TO,
                            "price": PRICE,
                        }
                    ],
                }
            ],
        }
    )


def _field(obj, *names):
    """obj sozluk de olabilir pydantic modeli de; ilk dolu alani doner."""
    for name in names:
        value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
        if value is not None:
            return value
    return None


def payer_address():
    """Odemeyi yapan ajanin adresi; kayit icin, para akisini etkilemez."""
    payload = getattr(g, "payment_payload", None)
    if payload is None:
        return "x402"
    inner = _field(payload, "payload")
    auth = _field(inner, "authorization") if inner is not None else None
    for holder in (auth, inner, payload):
        if holder is None:
            continue
        value = _field(holder, "from_", "from", "payer")
        if isinstance(value, str) and value.startswith("0x"):
            return value
    return "x402"


def extract():
    """Odeme middleware dogruladiktan SONRA calisir.

    DEKORATOR YOK: rota asagida SARTLI olarak kaydediliyor. Hem burada hem
    else dalinda dekorator kullanilirsa Flask ayni kural iki kez kaydedildigi
    icin AssertionError firlatir ve tum deploy patlar.

    400+ donersek veya patlarsak middleware tahsilati iptal eder; yani
    basarisiz cikarim icin ajandan para alinmaz.
    """
    text, fields, err = read_document_from_request(request)
    if err:
        payload, status = err
        return jsonify(payload), status

    key = payer_address()
    conn = db()
    try:
        result = extract_fields(text, fields)
        record_call(conn, key, len(fields), len(text), True)
    except Exception as exc:
        record_call(conn, key, len(fields), len(text), False)
        return jsonify({"error": "extraction_failed", "detail": str(exc)[:200]}), 502

    return jsonify({"data": result, "chars_processed": len(text)})


# --- odeme katmani -----------------------------------------------------------
# PAY_TO yoksa middleware HIC kurulmaz: uc acik kalmaz, 503 doner.
# Boylece "adres unutuldu" durumu bedava cikarim servisine donusmez.

# Bazaar kesif uzantisi agir dogrulama zinciri cekiyor (idna + ek modüller).
# Vercel'de korumali istekte surec iz birakmadan oluyordu; kapatilabilir yapildi
# ki odeme katmani uzantidan bagimsiz test edilebilsin.
BAZAAR = os.environ.get("X402_BAZAAR", "1").strip() not in ("0", "false", "no")

def _facilitator_istemcisi(ayar):
    from x402.http import FacilitatorConfig, HTTPFacilitatorClientSync

    if ayar.get("create_headers"):
        return HTTPFacilitatorClientSync(
            {"url": ayar["url"], "create_headers": ayar["create_headers"]}
        )
    return HTTPFacilitatorClientSync(FacilitatorConfig(url=ayar["url"]))


if not PAY_TO:

    def extract_yapilandirilmamis():
        return (
            jsonify(
                {
                    "error": "x402_not_configured",
                    "detail": "X402_PAY_TO is not set on this deployment, so payments "
                    "cannot be collected and the endpoint is disabled.",
                }
            ),
            503,
        )

    app.post("/x402/extract")(extract_yapilandirilmamis)
    ROUTES = None
    FACILITATOR_ISTEMCI = None

elif ANA_AG_HATASI:

    def extract_ana_ag_anahtarsiz():
        return (
            jsonify(
                {
                    "error": "cdp_api_key_required",
                    "detail": ANA_AG_ANAHTAR_MESAJI,
                }
            ),
            503,
        )

    app.post("/x402/extract")(extract_ana_ag_anahtarsiz)
    ROUTES = None
    FACILITATOR_ISTEMCI = None

else:
    app.post("/x402/extract")(extract)

    from x402 import x402ResourceServerSync
    if BAZAAR:
        from x402.extensions.bazaar import OutputConfig, declare_discovery_extension
    from x402.http.middleware.flask import payment_middleware
    from x402.http.types import PaymentOption, RouteConfig
    from x402.mechanisms.evm.exact import register_exact_evm_server

    facilitator = _facilitator_istemcisi(FACILITATOR_AYARI)
    FACILITATOR_ISTEMCI = facilitator
    server = x402ResourceServerSync(facilitator)
    register_exact_evm_server(server)

    def discovery_extension_for_post(**kwargs):
        """declare_discovery_extension + eksik 'method' alani.

        SDK method'u calisma aninda doldurmak uzere bos birakiyor ama
        baslangictaki dogrulayici zorunlu tutuyor. Bazaar kaydinin eksik
        dusmemesi icin acikca yaziliyor.
        """
        extension = declare_discovery_extension(**kwargs)
        extension["bazaar"]["info"]["input"]["method"] = "POST"
        return extension

    ROUTES = {
        "POST /x402/extract": RouteConfig(
            accepts=PaymentOption(
                scheme="exact", pay_to=PAY_TO, price=PRICE, network=NETWORK
            ),
            description=X402_ACIKLAMA,
            service_name="Fieldcast",
            tags=["documents", "pdf", "extraction", "invoices", "json"],
            mime_type="application/json",
            extensions=(discovery_extension_for_post(
                body_type="json",
                input={
                    "text": "INVOICE #2026-114\nDate: 14 August 2026\nSubtotal: 1200.00\nTotal: 1416.00",
                    "fields": ["invoice_number", "date", "subtotal", "total"],
                },
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Raw document text. Omit if uploading a PDF as multipart.",
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 40,
                            "description": "Names of the fields to extract.",
                        },
                    },
                    "required": ["fields"],
                },
                output=OutputConfig(
                    example={
                        "data": {
                            "invoice_number": "2026-114",
                            "date": "2026-08-14",
                            "subtotal": 1200.0,
                            "total": 1416.0,
                        },
                        "chars_processed": 78,
                    }
                ),
            ) if BAZAAR else None),
        )
    }

    payment_middleware(app, ROUTES, server)
