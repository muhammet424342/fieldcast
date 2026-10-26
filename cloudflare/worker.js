// Fieldcast Cloudflare Worker (26 Eki 2026): Vercel YOK.
// Statik site ../public'ten (Workers assets). API burada:
//   POST /v1/extract  -> json {text, fields[]} veya multipart file + fields (api/index.py ile ayni sozlesme)
//   GET  /health
//   /x402/extract, /x402/health -> sunucudaki x402 kapisi (Base USDC, PayAI facilitator)
// PDF metni Workers AI toMarkdown ile okunur; alanlar NVIDIA modellerinden, NVIDIA duserse Workers AI'dan.

const NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions";
// 26 Eki olcumu (3 zor ornek, 16 alan): ikisi de 16/16. Eski 4 model NVIDIA'da EOL (410).
const NVIDIA_MODELS = ["nvidia/nemotron-3.5-bolt-e4b", "minimaxai/minimax-m3.1-flash"];
const CF_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
const API_KEYS = { demo_key_public: "demo" };
const MAX_CHARS = 20000;
const MAX_FIELDS = 40;
const X402_GATE = "https://157-173-122-86.sslip.io/base";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Content-Type, X-API-Key, X-PAYMENT",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
};

function json(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...CORS } });
}

function prompt(text, fields) {
  return (
    "Extract the requested fields from the document text below.\n" +
    "Return ONLY a JSON object, no explanation, no markdown fence.\n" +
    "Use exactly these keys: " + fields.join(", ") + "\n" +
    "Normalise dates to ISO-8601 (YYYY-MM-DD). Keep monetary values as numbers.\n" +
    "If a field is not present in the document, set it to null. Do not invent values.\n\n" +
    "DOCUMENT:\n" + text.slice(0, MAX_CHARS)
  );
}

function jsonAyikla(content) {
  if (!content) throw new Error("empty response from model");
  if (content.includes("</think>")) content = content.split("</think>").pop();
  content = content.trim().replace(/^```(?:json)?|```$/gm, "").trim();
  try {
    return JSON.parse(content);
  } catch {
    const m = content.match(/\{[\s\S]*\}/);
    if (!m) throw new Error("model did not return JSON");
    return JSON.parse(m[0]);
  }
}

async function nvidia(key, model, p) {
  const r = await fetch(NVIDIA_URL, {
    method: "POST",
    headers: { Authorization: "Bearer " + key, "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ model, messages: [{ role: "user", content: p }], temperature: 0, max_tokens: 900 }),
    signal: AbortSignal.timeout(45000),
  });
  if (!r.ok) throw new Error("HTTP " + r.status);
  const d = await r.json();
  return (d.choices?.[0]?.message?.content || "").trim();
}

async function extractFields(env, text, fields) {
  const p = prompt(text, fields);
  const hatalar = [];
  if (env.NVIDIA_API_KEY) {
    for (const m of NVIDIA_MODELS) {
      try {
        return jsonAyikla(await nvidia(env.NVIDIA_API_KEY, m, p));
      } catch (e) {
        hatalar.push("nvidia/" + m + ": " + String(e.message).slice(0, 80));
      }
    }
  }
  try {
    const r = await env.AI.run(CF_MODEL, { messages: [{ role: "user", content: p }], temperature: 0, max_tokens: 900 });
    return jsonAyikla(typeof r.response === "string" ? r.response : JSON.stringify(r.response));
  } catch (e) {
    hatalar.push("workers-ai: " + String(e.message).slice(0, 80));
  }
  throw new Error("all providers failed -> " + hatalar.join(" | "));
}

async function belgeOku(env, req) {
  const tip = req.headers.get("Content-Type") || "";
  let text = "", fields = [];
  if (tip.includes("multipart/form-data")) {
    const form = await req.formData();
    const file = form.get("file");
    fields = String(form.get("fields") || "").split(",").map((s) => s.trim()).filter(Boolean);
    if (file && typeof file !== "string") {
      try {
        if (/\.pdf$/i.test(file.name) || file.type === "application/pdf") {
          const [md] = await env.AI.toMarkdown([{ name: file.name || "doc.pdf", blob: file }]);
          if (md.format === "error") throw new Error(md.error || "pdf could not be read");
          text = (md.data || "").trim();
        } else {
          text = (await file.text()).trim();
        }
      } catch (e) {
        return { hata: json({ error: "file_unreadable", detail: String(e.message).slice(0, 200) }, 400) };
      }
    } else {
      text = String(form.get("text") || "").trim();
    }
  } else {
    const d = await req.json().catch(() => ({}));
    text = String(d.text || "").trim();
    fields = Array.isArray(d.fields) ? d.fields.map(String) : [];
  }
  if (!text) return { hata: json({ error: "no_document_text" }, 400) };
  if (!fields.length) return { hata: json({ error: "no_fields_requested" }, 400) };
  if (fields.length > MAX_FIELDS) return { hata: json({ error: "too_many_fields", max: MAX_FIELDS }, 400) };
  return { text, fields };
}

async function extract(env, req) {
  const key = req.headers.get("X-API-Key") || "";
  const plan = API_KEYS[key];
  if (!plan) return json({ error: "invalid_api_key" }, 401);
  // ponytail: kalici aylik kota yok; IP basina dakikada 10 cagri (Cloudflare rate limit, depolama yok).
  // Gercek musteri anahtarlari gelince KV/D1'de aylik sayac.
  const ip = req.headers.get("CF-Connecting-IP") || "?";
  if (env.DENEME_SINIRI && !(await env.DENEME_SINIRI.limit({ key: ip })).success) {
    return json({ error: "quota_exceeded", plan, detail: "rate limit: 10 calls per minute" }, 429);
  }
  const { text, fields, hata } = await belgeOku(env, req);
  if (hata) return hata;
  try {
    return json({ data: await extractFields(env, text, fields), chars_processed: text.length });
  } catch (e) {
    return json({ error: "extraction_failed", detail: String(e.message).slice(0, 200) }, 502);
  }
}

export default {
  async fetch(req, env) {
    const u = new URL(req.url);
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    if (u.pathname === "/health") return json({ status: "ok", time: new Date().toISOString().slice(0, 19) });
    if (u.pathname === "/v1/extract") {
      return req.method === "POST" ? extract(env, req) : json({ error: "method_not_allowed" }, 405);
    }
    if (u.pathname === "/x402/extract" || u.pathname === "/x402/health") {
      const yol = u.pathname === "/x402/extract" ? "/v1/extract" : "/health";
      const r = await fetch(X402_GATE + yol + u.search, { method: req.method, headers: req.headers, body: req.body, duplex: "half" });
      return new Response(r.body, { status: r.status, headers: { ...Object.fromEntries(r.headers), ...CORS } });
    }
    return env.ASSETS.fetch(req);
  },
};
