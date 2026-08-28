# -*- coding: utf-8 -*-
"""Fieldcast x402 ucu — ajanlarin hesapsiz, cagri basi odeyerek kullandigi yuz.

Fark: X-API-Key yok. Odemesiz istek HTTP 402 + odeme sartlari doner; ajan
zincir uzerinde USDC oder ve cevabi ayni akista alir.

AG SECIMI (26 Agu 2026 dogrulamasi):
  https://x402.org/facilitator/supported ucundan okunan aglar SADECE TEST aglari.
  eip155:84532 (Base Sepolia) VAR, eip155:8453 (Base mainnet) YOK.
  Mainnet icin CDP API anahtariyla kimlik dogrulamasi gereken facilitator lazim.
  Bu yuzden varsayilan Base Sepolia'dir ve GERCEK PARA AKMAZ.

DEPLOY GUVENLIGI: X402_PAY_TO tanimli degilse surec COKMEZ; uc 503 doner ve
sebebini soyler. Boylece adres girilmeden yapilan deploy siteyi bozmaz.
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

PAY_TO = os.environ.get("X402_PAY_TO", "").strip()
NETWORK = os.environ.get("X402_NETWORK", "eip155:84532").strip()
PRICE = os.environ.get("X402_PRICE", "$0.01").strip()
FACILITATOR_URL = os.environ.get(
    "X402_FACILITATOR_URL", "https://x402.org/facilitator"
).strip()

IS_TESTNET = NETWORK != "eip155:8453"

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
            "configured": bool(PAY_TO),
        }
    )


@app.get("/x402/health")
def health():
    return jsonify(
        {
            "status": "ok" if PAY_TO else "not_configured",
            "network": NETWORK,
            "testnet": IS_TESTNET,
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

if PAY_TO:
    app.post("/x402/extract")(extract)

    from x402 import x402ResourceServerSync
    if BAZAAR:
        from x402.extensions.bazaar import OutputConfig, declare_discovery_extension
    from x402.http import FacilitatorConfig, HTTPFacilitatorClientSync
    from x402.http.middleware.flask import payment_middleware
    from x402.http.types import PaymentOption, RouteConfig
    from x402.mechanisms.evm.exact import register_exact_evm_server

    facilitator = HTTPFacilitatorClientSync(FacilitatorConfig(url=FACILITATOR_URL))
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
            description=(
                "Extract structured data from a document. Send raw text or a PDF plus the "
                "list of field names you want, and receive those fields back as typed JSON. "
                "Fields that do not appear in the document are returned as null rather than "
                "invented. Useful for invoices, receipts, contracts, forms and reports."
            ),
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

else:

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
