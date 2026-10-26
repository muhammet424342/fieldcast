# -*- coding: utf-8 -*-
"""Fieldcast odeme rayi secici — tek giris noktasi.

Ayni adrese gelen istegi tarafina gore IKI mevcut akistan birine baglar:

  * Ajan (programatik istemci)  -> /x402/extract odeme akisi. Odeme yoksa
    HTTP 402 + x402 v2 sartlari (PAYMENT-REQUIRED) doner. Ucret burada
    tahsil edilmez; odeme basligi varsa istek mevcut x402 katmanina devredilir.
  * Insan tarayici             -> api/moove.py'nin link akisi, HTTP 302 ile
    yonlendirilir. Link adresi FIELDCAST_MOOVE_LINK ile degistirilebilir.

Cikarim mantigi BURADA YOKTUR ve yeniden yazilmaz: ajanin odemeli istegi
api/pay.py uzerinden api/index.py'deki extract_fields/read_document_from_request
cekirdegine gider. Bu dosya yalnizca taraf secimi, yonlendirme ve 402
sartlarinin bicimini tutar.
"""
import base64
import json
import os
import re
from decimal import Decimal, InvalidOperation, ROUND_DOWN

try:  # Flask yoksa modul yine de import edilebilsin (test/koleksiyon).
    from flask import Flask, Response, jsonify, redirect, request
except ImportError:  # pragma: no cover - paketler kurulu ortamda girmez
    Flask = None


# Istegi tarafina zorlamak icin opsiyonel baslik. Adi degisebilir diye birkac
# yaygin varyant kabul edilir; ilk dolu olan kullanilir.
TARAF_BASLIKLARI = (
    "X-Fieldcast-Ray",
    "X-Fieldcast-Rail",
    "X-Fieldcast-Client",
    "X-Client-Type",
    "X-Agent",
)

AJAN_ISARETLERI = (
    "agent",
    "ajan",
    "bot",
    "machine",
    "api",
    "x402",
)

INSAN_ISARETLERI = (
    "human",
    "insan",
    "browser",
    "tarayici",
    "web",
    "link",
)

# Programatik istemci imzalari. "bot" da insan degildir; 402 sartlarini alir.
AJAN_UA_ISARETLERI = (
    "curl/",
    "wget/",
    "python-requests",
    "python-urllib",
    "urllib3",
    "aiohttp",
    "httpx",
    "requests/",
    "node-fetch",
    "axios",
    "undici",
    "go-http-client",
    "okhttp",
    "java/",
    "libwww-perl",
    "httpie",
    "postmanruntime",
    "insomnia",
    "mcp",
    "agent",
    "bot",
    "spider",
    "crawler",
    "openai",
    "anthropic",
    "langchain",
)

TARAYICI_UA_ISARETLERI = (
    "mozilla/",
    "chrome/",
    "chromium",
    "safari/",
    "firefox/",
    "edg/",
    "opr/",
    "opera",
    "msie",
    "trident",
    "mobile",
    "android",
    "iphone",
    "ipad",
)

# api/moove.py'nin link akisi. Modul henuz yoksa varsayilan yol kullanilir;
# modul geldiginde yaygin sabit adlari kendiliginden okunur.
MOOVE_VARSAYILAN = "/moove"

# api/pay.py'deki varsayilanlarin aynisi (paket yoksa yedek yol).
_X402_PAY_TO_VARSAYILAN = "0x3f425d6ffd2855585483d65da684651e330759e0"
_X402_NETWORK_VARSAYILAN = "eip155:8453"
_X402_PRICE_VARSAYILAN = "$0.01"

# x402 SDK'nin default_assets.py degerleri; paket yoksa bilinen iki ag icin
# yedek. Baska agda varlik uydurulmaz, alan disarida birakilir.
_BILINEN_VARLIKLAR = {
    "eip155:8453": {
        "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "name": "USD Coin",
        "version": "2",
        "decimals": 6,
    },
    "eip155:84532": {
        "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        "name": "USDC",
        "version": "2",
        "decimals": 6,
    },
}

_X402_ACIKLAMA_VARSAYILAN = (
    "Extract structured data from a document. Send raw text or a PDF plus the "
    "list of field names you want, and receive those fields back as typed JSON. "
    "Fields that do not appear in the document are returned as null rather than "
    "invented. Useful for invoices, receipts, contracts, forms and reports."
)


def _baslik_al(basliklar, ad):
    """Baslik sozlugunden/werkzeug Headers'tan buyuk-kucuk harf duyarsiz okur."""
    if basliklar is None:
        return ""
    try:
        deger = basliklar.get(ad)
    except (AttributeError, TypeError):
        deger = None
    if deger is not None:
        return str(deger).strip()
    for anahtar in basliklar:
        if str(anahtar).lower() == ad.lower():
            deger = basliklar[anahtar]
            return "" if deger is None else str(deger).strip()
    return ""


def taraf_tespit(user_agent="", accept="", ray_header=""):
    """Istek tarafini dondurur: "agent" veya "human".

    Sira: acik baslik > programatik UA > tarayici UA > Accept imzasi > agent.
    Belirsiz istek guvenli tarafa (agent/402) duser; boylece bedava cikarim
    yanlislikla acilmaz.
    """
    zorla = (ray_header or "").strip().lower()
    if zorla:
        if any(isaret in zorla for isaret in AJAN_ISARETLERI):
            return "agent"
        if any(isaret in zorla for isaret in INSAN_ISARETLERI):
            return "human"

    ua = (user_agent or "").lower()
    if any(isaret in ua for isaret in AJAN_UA_ISARETLERI):
        return "agent"
    if any(isaret in ua for isaret in TARAYICI_UA_ISARETLERI):
        return "human"

    kabul = (accept or "").lower()
    if "text/html" in kabul:
        return "human"
    if "application/json" in kabul:
        return "agent"

    return "agent"


# Geriye donuk/okunabilirlik icin Turkce adlar da ayni islevi gosterir.
tarafi_tespit = taraf_tespit
iste_tarafi = taraf_tespit


def istek_tarafi(basliklar=None):
    """Flask istegi (veya verilen basliklar) icin taraf tespiti."""
    if basliklar is None:
        basliklar = request.headers
    ray_header = ""
    for ad in TARAF_BASLIKLARI:
        ray_header = _baslik_al(basliklar, ad)
        if ray_header:
            break
    return taraf_tespit(
        _baslik_al(basliklar, "User-Agent"),
        _baslik_al(basliklar, "Accept"),
        ray_header,
    )


def moove_link_hedefi():
    """Insan tarayicinin yonlendirilecegi link akisi adresi."""
    for anahtar in ("FIELDCAST_MOOVE_LINK", "MOOVE_LINK"):
        deger = os.environ.get(anahtar, "").strip()
        if deger:
            return deger
    try:
        import moove  # api/moove.py geldiginde kullanilir
    except ImportError:
        moove = None
    if moove is not None:
        for ad in ("LINK_YOLU", "link_yolu", "ODEME_LINKI", "odeme_linki", "LINK"):
            deger = getattr(moove, ad, None)
            if isinstance(deger, str) and deger.strip():
                return deger.strip()
    return MOOVE_VARSAYILAN


def _pay_ayarlari():
    """Odeme sabitlerini api/pay.py'den al; ENV acikca verilmisse onu kullan.

    Boylece ray.py ile pay.py ayni fiyat/ag/alici degerlerini gosterir; ikinci
    bir kopya sessizce ayrismaz.
    """
    pay_to = os.environ.get("X402_PAY_TO")
    network = os.environ.get("X402_NETWORK")
    price = os.environ.get("X402_PRICE")
    aciklama = None
    try:
        import pay

        if pay_to is None:
            pay_to = pay.PAY_TO
        if network is None:
            network = pay.NETWORK
        if price is None:
            price = pay.PRICE
        aciklama = getattr(pay, "X402_ACIKLAMA", None)
    except Exception:
        pass

    pay_to = (_X402_PAY_TO_VARSAYILAN if pay_to is None else pay_to).strip()
    network = (_X402_NETWORK_VARSAYILAN if network is None else network).strip()
    price = (_X402_PRICE_VARSAYILAN if price is None else price).strip()
    return pay_to, network, price, aciklama or _X402_ACIKLAMA_VARSAYILAN


def _varlik_bilgisi(network):
    try:
        from x402.mechanisms.evm.default_assets import DEFAULT_ASSETS

        kayitlar = DEFAULT_ASSETS.get(network) or []
        if kayitlar:
            return dict(kayitlar[0])
    except Exception:
        pass
    return dict(_BILINEN_VARLIKLAR.get(network) or {})


def _atomik_miktar(price, ondalik):
    """'$0.01' + 6 ondalik -> '10000'. Uydurma yok; okunamazsa None."""
    eslesme = re.search(r"[0-9]+(?:[.,][0-9]+)?", price or "")
    if not eslesme:
        return None
    try:
        tutar = Decimal(eslesme.group(0).replace(",", "."))
        carpan = Decimal(10) ** int(ondalik)
        return str((tutar * carpan).to_integral_value(rounding=ROUND_DOWN))
    except (InvalidOperation, ValueError):
        return None


def odeme_sartlari(kok=None, network=None):
    """x402 v2 402 sartlari (cozulmus JSON). api/pay.py ile ayni bicim."""
    pay_to, varsayilan_network, price, aciklama = _pay_ayarlari()
    network = network or varsayilan_network
    if kok is None:
        kok = "http://localhost"
    kok = str(kok).rstrip("/")

    varlik = _varlik_bilgisi(network)
    kabul = {
        "scheme": "exact",
        "network": network,
        "payTo": pay_to,
        "maxTimeoutSeconds": 300,
    }
    if varlik.get("asset"):
        kabul["asset"] = varlik["asset"]
    miktar = _atomik_miktar(price, varlik.get("decimals", 6))
    if miktar is not None:
        kabul["amount"] = miktar
    if varlik.get("name"):
        kabul["extra"] = {
            "name": varlik["name"],
            "version": varlik.get("version", "2"),
        }

    return {
        "x402Version": 2,
        "error": "Payment required",
        "resource": {
            "url": kok + "/x402/extract",
            "description": aciklama,
            "mimeType": "application/json",
            "serviceName": "Fieldcast",
            "tags": ["documents", "pdf", "extraction", "invoices", "json"],
        },
        "accepts": [kabul],
    }


def _odeme_gerekli(sartlar):
    """402: govde bos, sartlar PAYMENT-REQUIRED basliginda (mevcut akis)."""
    yanit = jsonify({})
    yanit.status_code = 402
    yanit.headers["PAYMENT-REQUIRED"] = base64.b64encode(
        json.dumps(sartlar, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).decode("ascii")
    yanit.headers["Cache-Control"] = "no-store"
    yanit.headers["Access-Control-Expose-Headers"] = "PAYMENT-REQUIRED, PAYMENT-RESPONSE"
    return yanit


def _odeme_basligi_var():
    for ad in ("PAYMENT-SIGNATURE", "X-PAYMENT"):
        if _baslik_al(request.headers, ad):
            return True
    return False


def _pay_uygulamasina_devret():
    """Odemeli ajan istegini mevcut api/pay.py x402 katmanina devreder.

    Boylece dogrulama/tahsilat/cikarim zinciri yeniden yazilmaz; pay.py de
    cikarim icin api/index.py'yi cagirir.
    """
    try:
        from pay import app as pay_app
    except Exception as exc:  # paketler eksikse uc sessizce acilmaz
        return (
            jsonify(
                {
                    "error": "x402_unavailable",
                    "detail": "odeme katmani yuklenemedi: " + str(exc)[:160],
                }
            ),
            503,
        )

    ortam = dict(request.environ)
    ortam.pop("werkzeug.request", None)
    ortam.pop("werkzeug.socket", None)
    ortam["PATH_INFO"] = "/x402/extract"
    ortam["SCRIPT_NAME"] = ""
    ortam["REQUEST_METHOD"] = "POST"

    toplanan = {}

    def start_response(status, headers, exc_info=None):
        toplanan["status"] = status
        toplanan["headers"] = headers
        return lambda _veri: None

    govde = pay_app(ortam, start_response)
    try:
        veri = b"".join(govde)
    finally:
        kapat = getattr(govde, "close", None)
        if kapat:
            kapat()

    yanit = Response(veri, status=int(toplanan.get("status", "500").split()[0]))
    for ad, deger in toplanan.get("headers", []):
        if ad.lower() in ("content-length", "transfer-encoding"):
            continue
        yanit.headers[ad] = deger
    return yanit


def ray_yaniti():
    """Ana karar: tarafi tespit et, ilgili mevcut akisa bagla."""
    taraf = istek_tarafi()

    if taraf == "human":
        hedef = moove_link_hedefi()
        sorgu = request.query_string.decode("latin-1")
        if sorgu:
            hedef += ("&" if "?" in hedef else "?") + sorgu
        return redirect(hedef, code=302)

    pay_to, network, _price, _aciklama = _pay_ayarlari()
    if not pay_to:
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

    if _odeme_basligi_var():
        return _pay_uygulamasina_devret()

    return _odeme_gerekli(odeme_sartlari(request.url_root, network))


if Flask is not None:
    app = Flask(__name__)

    @app.after_request
    def cors(resp):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, X-API-Key, X-PAYMENT, PAYMENT-SIGNATURE, "
            + ", ".join(TARAF_BASLIKLARI)
        )
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Expose-Headers"] = (
            "PAYMENT-REQUIRED, PAYMENT-RESPONSE"
        )
        return resp

    @app.route("/", methods=["GET", "POST", "OPTIONS"])
    @app.route("/ray", methods=["GET", "POST", "OPTIONS"])
    @app.route("/ray/", methods=["GET", "POST", "OPTIONS"])
    def ray_route():
        if request.method == "OPTIONS":
            return ("", 204)
        return ray_yaniti()
else:  # pragma: no cover
    app = None


if __name__ == "__main__":
    if app is None:
        raise SystemExit("Flask gerekli: pip install -r requirements.txt")
    app.run(host="0.0.0.0", port=int(os.environ.get("FIELDCAST_RAY_PORT", "8011")))
