"""
Fieldcast API - belge (PDF/metin) -> yapilandirilmis JSON.

Sunucudaki kopya erisilemez oldugu icin 18 Agu 2026'da PC'de yeniden kuruldu.
Calistir:  python fieldcast_app.py    (varsayilan port 8010)
"""
import json
import os
import re
import sqlite3
import urllib.request
from datetime import datetime

from flask import Flask, jsonify, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("FIELDCAST_DB", "/tmp/usage.db")
PORT = int(os.environ.get("FIELDCAST_PORT", "8010"))

# --- Cikarim motoru: NVIDIA birincil (ucretsiz), DeepSeek son care (ucretli) ---
# 26 Agu 2026: 10 alanli fatura testinde NVIDIA modelleri DeepSeek'in 10/10'unu
# esitledi ve daha hizli calisti. Isletme maliyeti sifira indi.
# Anahtarlar ORTAMDAN gelir, kodda gomulu tutulmaz.
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "").strip()
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# Olculmus sira: once dogruluk, esitlikte hiz. Biri hata/limit verirse siradaki denenir.
#   minimax-m3 10/10 1.5sn | kimi-k3 10/10 2.7sn
#   mistral-nemotron 10/10 3.7sn | llama-3.1-70b 10/10 4.2sn
# llama-3.1-8b listede YOK: 8/10, tarih normalizasyonunu kaciriyor.
NVIDIA_MODELS = [
    "minimaxai/minimax-m3",
    "moonshotai/kimi-k3",
    "mistralai/mistral-nemotron",
    "meta/llama-3.1-70b-instruct",
]

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# key -> (plan adi, aylik limit)
API_KEYS = {
    "demo_key_public": ("demo", 50),
}

MAX_CHARS = 20000  # tek belgeden motora gonderilecek azami metin


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS usage ("
        "api_key TEXT, month TEXT, calls INTEGER, PRIMARY KEY (api_key, month))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS calls ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, api_key TEXT, ts TEXT, "
        "fields INTEGER, chars INTEGER, ok INTEGER)"
    )
    return conn


def current_month():
    return datetime.utcnow().strftime("%Y-%m")


def usage_count(conn, key):
    row = conn.execute(
        "SELECT calls FROM usage WHERE api_key=? AND month=?", (key, current_month())
    ).fetchone()
    return row[0] if row else 0


def record_call(conn, key, fields, chars, ok):
    month = current_month()
    conn.execute(
        "INSERT INTO usage (api_key, month, calls) VALUES (?,?,1) "
        "ON CONFLICT(api_key, month) DO UPDATE SET calls = calls + 1",
        (key, month),
    )
    conn.execute(
        "INSERT INTO calls (api_key, ts, fields, chars, ok) VALUES (?,?,?,?,?)",
        (key, datetime.utcnow().isoformat(timespec="seconds"), fields, chars, 1 if ok else 0),
    )
    conn.commit()


def pdf_to_text(file_storage):
    import pdfplumber

    parts = []
    with pdfplumber.open(file_storage) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def _prompt(text, fields):
    return (
        "Extract the requested fields from the document text below.\n"
        "Return ONLY a JSON object, no explanation, no markdown fence.\n"
        "Use exactly these keys: " + ", ".join(fields) + "\n"
        "Normalise dates to ISO-8601 (YYYY-MM-DD). Keep monetary values as numbers.\n"
        "If a field is not present in the document, set it to null. "
        "Do not invent values.\n\n"
        "DOCUMENT:\n" + text[:MAX_CHARS]
    )


def _sohbet(url, key, model, prompt, zaman=90):
    """OpenAI-uyumlu tek cagri. NVIDIA ve DeepSeek ayni govde formatini kabul ediyor."""
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 900,
        }
    ).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=zaman) as resp:
        payload = json.load(resp)
    return (payload["choices"][0]["message"].get("content") or "").strip()


def _json_ayikla(content):
    """Model cevabindan JSON nesnesini cikarir.

    Akil yurutme modelleri cevabi <think>...</think> ile onceleyebiliyor,
    bazilari markdown citi ekliyor. Ikisi de temizlenir.
    """
    if not content:
        raise ValueError("empty response from model")
    if "</think>" in content:
        content = content.split("</think>")[-1]
    content = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError("model did not return JSON")
        return json.loads(match.group(0))


def extract_fields(text, fields):
    """Belge metninden istenen alanlari cikarir. Bulunamayan alan null doner.

    Saglayici sirasi: NVIDIA modelleri (ucretsiz) -> DeepSeek (ucretli, son care).
    Bir saglayici duserse istek olmez, siradakine gecilir. Hepsi duserse
    toplu hata mesaji yukari firlatilir; cagiran kat 502 dondurur.
    """
    prompt = _prompt(text, fields)
    hatalar = []

    if NVIDIA_API_KEY:
        for model in NVIDIA_MODELS:
            try:
                return _json_ayikla(_sohbet(NVIDIA_URL, NVIDIA_API_KEY, model, prompt))
            except Exception as exc:
                hatalar.append("nvidia/%s: %s" % (model, str(exc)[:80]))

    if DEEPSEEK_API_KEY:
        try:
            return _json_ayikla(
                _sohbet(DEEPSEEK_URL, DEEPSEEK_API_KEY, DEEPSEEK_MODEL, prompt)
            )
        except Exception as exc:
            hatalar.append("deepseek: %s" % str(exc)[:80])

    if not hatalar:
        raise RuntimeError("no extraction provider configured (set NVIDIA_API_KEY)")
    raise RuntimeError("all providers failed -> " + " | ".join(hatalar))


def read_document_from_request(req):
    """Istekten (multipart veya JSON) belge metni ve alan listesini cikarir.

    Doner: (text, fields, hata). Hata varsa (None, None, (payload, status)).
    """
    if req.files.get("file"):
        raw = req.form.get("fields", "")
        fields = [f.strip() for f in raw.split(",") if f.strip()]
        upload = req.files["file"]
        name = (upload.filename or "").lower()
        try:
            if name.endswith(".pdf"):
                text = pdf_to_text(upload)
            else:
                text = upload.read().decode("utf-8", "replace")
        except Exception as exc:
            return None, None, ({"error": "file_unreadable", "detail": str(exc)[:200]}, 400)
    else:
        data = req.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        fields = data.get("fields") or []

    if not text:
        return None, None, ({"error": "no_document_text"}, 400)
    if not fields:
        return None, None, ({"error": "no_fields_requested"}, 400)
    if len(fields) > 40:
        return None, None, ({"error": "too_many_fields", "max": 40}, 400)
    return text, fields, None


app = Flask(__name__)


@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key"
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    return resp


@app.get("/")
def index():
    return jsonify(
        {
            "service": "Fieldcast API",
            "description": "Turn PDFs and raw text into structured JSON.",
            "endpoints": {
                "POST /v1/extract": "json {text, fields[]} or multipart file + fields",
                "GET /health": "liveness",
            },
            "auth": "X-API-Key header",
        }
    )


@app.get("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat(timespec="seconds")})


@app.post("/v1/extract")
def extract():
    key = request.headers.get("X-API-Key", "")
    if key not in API_KEYS:
        return jsonify({"error": "invalid_api_key"}), 401

    plan, limit = API_KEYS[key]
    conn = db()
    used = usage_count(conn, key)
    if used >= limit:
        return jsonify({"error": "quota_exceeded", "plan": plan, "limit": limit}), 429

    text, fields, err = read_document_from_request(request)
    if err:
        payload, status = err
        return jsonify(payload), status

    try:
        result = extract_fields(text, fields)
        record_call(conn, key, len(fields), len(text), True)
    except Exception as exc:
        record_call(conn, key, len(fields), len(text), False)
        return jsonify({"error": "extraction_failed", "detail": str(exc)[:200]}), 502

    return jsonify(
        {
            "data": result,
            "usage": {"plan": plan, "used": used + 1, "limit": limit},
            "chars_processed": len(text),
        }
    )


if __name__ == "__main__":
    print("Fieldcast API -> http://127.0.0.1:%d" % PORT)
    app.run(host="0.0.0.0", port=PORT)
