# Fieldcast — Dizin Kayıt Kiti

Her dizine **aynı metni yapıştırma**. AI motorları ve dizin moderatörleri kopya içeriği düşürüyor.
Aşağıda her katman için ayrı varyant var. Kayıt yaparken sadece ilgili bloğu kopyala.

---

## Sabit bilgiler

| Alan | Değer |
|---|---|
| Ürün adı | Fieldcast |
| URL | `https://fieldcast-peach.vercel.app` — **CANLI** (26 Ağu 2026) |
| Kategori | Developer Tools / AI / Document Processing |
| Fiyat modeli | Freemium (Free 50/ay, Starter $19, Pro $49, x402 $0.01/çağrı) |
| Kurucu | Muhammet Karakurt |
| İletişim | muhammet@decaylabs.online |
| Logo | `public/` → logo.svg, logo-1024.png, logo-512.png, logo-512-transparent.png, favicon.ico — **hazır** |
| Etiketler | api, document-parsing, invoice-ocr, pdf-to-json, data-extraction, ai-agents, x402, developer-tools |

---

## Tagline (10 kelime altı)

- **Birincil:** Documents in, structured JSON out. One API call.
- Yedek A: Name the fields. Get typed JSON back.
- Yedek B: PDF to JSON without drawing a single template.

---

## 60 karakter açıklama

`Turn PDFs and invoices into structured JSON in one API call.` (60)

---

## Katman 1 — Lansman platformları (Product Hunt, Fazier, Uneed, Microlaunch)
**Açı: SONUÇ.** Kitle diğer kurucular. Ne işe yaradığını merak ediyorlar.

> Every document parser I tried wanted me to draw a template first — and every template broke the week a supplier redesigned their invoice.
>
> Fieldcast skips that step entirely. You POST a PDF or raw text along with a list of the field names you want, and you get them back as typed JSON: totals as numbers, dates normalised to ISO-8601, and anything the document does not contain returned as `null` instead of a confident guess.
>
> No template designer. No training data. No fine-tuning. Up to 40 fields per call, named however your own database already names them.
>
> There is a free tier of 50 extractions a month so you can measure accuracy on your own documents rather than trusting a benchmark on mine.

---

## Katman 2 — SaaS / inceleme dizinleri (AlternativeTo, SaaSHub, G2, Capterra, SourceForge)
**Açı: ALTERNATİF.** İnsanlar "X alternatifi" diye arıyor. Orada karşıla.

> Fieldcast is a lightweight alternative to template-based document parsers like Docparser, Mindee and Nanonets.
>
> The difference is setup cost. Template tools require you to define a layout per document type before you extract anything, and that layout breaks when a vendor changes their format. Fieldcast takes a list of field names at request time instead, so a new supplier layout is not a new configuration project.
>
> Output is typed JSON — numeric totals, ISO dates — and unmatched fields return `null` rather than a fabricated value. Free tier: 50 extractions per month. Paid from $19/month for 1,000.

**Karşılaştırma sayfası olarak yazılacak alternatif sayfaları:**
`/alternatives/docparser` · `/alternatives/mindee` · `/alternatives/nanonets` *(HENÜZ YOK — Katman 2 öncesi yazılmalı)*

---

## Katman 3 — AI dizinleri (TAAFT, Futurepedia, Toolify, Future Tools, aitools.inc)
**Açı: AI-FIRST MİMARİ.** Bu kitle açıkça AI aracı arıyor.

> Fieldcast is an LLM-native document extraction API. Instead of computer-vision templates or a fixed invoice schema, it reads the document and returns exactly the fields you asked for.
>
> That means it handles layouts it has never seen before, works across languages, and adapts to a new document type by changing one array in your request rather than retraining anything.
>
> The design constraint that matters most: it is instructed never to invent a value. A field absent from the source comes back `null`. For accounting and finance workflows, a missing total is recoverable — a hallucinated one is not.
>
> Free tier available. PDF and plain text supported; OCR for scanned images is on the roadmap.

---

## Katman 4 — Agent / MCP kayıtları (AI Agents List, Glama, APITracker, AgentHunter, x402 Bazaar)
**Açı: AJAN AÇISI. Bu senin gerçek hendeğin — geleneksel SaaS buraya giremez.**

> Fieldcast exposes document extraction as a service that autonomous agents can actually buy.
>
> Alongside the standard API-key endpoint, it serves an **x402** endpoint that requires no account and no key. An agent calls it, receives HTTP 402 with machine-readable payment terms, settles $0.01 in USDC on Base, and receives the extracted JSON in the same request flow. The service declares itself to the x402 Bazaar, so agents searching for document extraction can discover it without a human in the loop.
>
> This closes a real gap: an autonomous agent cannot complete a signup form, accept terms, or enter a credit card — but it can pay per call. Any agent that needs to turn an invoice, receipt or contract into structured fields can use Fieldcast as a paid tool with zero onboarding.
>
> Input: PDF or text plus a list of field names. Output: typed JSON, `null` for anything not present.

---

## Katman 6 — "En iyi X" listelerine outreach (soğuk mail şablonu)

> Konu: Fieldcast for your [POST BAŞLIĞI] roundup
>
> Hi [AD] — your piece on [POST BAŞLIĞI] is the one I keep sending people, so I wanted to put one more option in front of you rather than ask for a link.
>
> Fieldcast is a document extraction API with no template step: you pass field names with the request and get typed JSON back. The angle your readers might not have seen elsewhere is that it also serves an x402 endpoint, so AI agents can pay $0.01 per call in USDC without an account — as far as I know it is the only document parser that does.
>
> Free tier is 50 extractions/month if you want to try it against your own file: [URL]
>
> Either way, thanks for the original post.
> — Muhammet

---

## Kurucu hikâyesi (2-3 cümle, çoğu dizin istiyor)

> I kept rebuilding the same invoice parser for different projects, and every time the real work was not the extraction — it was maintaining templates that broke whenever a supplier changed their layout. Fieldcast is that step deleted: you name the fields, the API returns them typed. I added the x402 endpoint because the next wave of callers will be agents that cannot sign up for anything.

---

## ⚠️ Kayıt yapmadan önce kapatılması gereken eksikler

| Eksik | Engel seviyesi | Not |
|---|---|---|
| ~~Canlı public URL~~ | ✅ TAMAM | `fieldcast-peach.vercel.app` — SSO koruması kapatıldı, `noindex` yok, çıkarım canlı test edildi |
| ~~PNG logo + favicon~~ | ✅ TAMAM | 1024 / 512 / 512-şeffaf PNG + favicon.ico + apple-touch-icon üretildi |
| 5-8 ürün ekran görüntüsü 1920×1080 | 🔴 SERT | Tier 1 dizinlerin çoğu zorunlu tutuyor. **Tek kalan sert engel.** |
| 60-90 sn demo videosu | 🟡 ORTA | Product Hunt'ta 2,7× daha fazla upvote. Sessiz ekran kaydı serbest (25 Ağu kararı) |
| 3 alternatif sayfası | 🟡 ORTA | Katman 2 öncesi. Link değerinin ineceği yer bunlar |
| 3 kullanım senaryosu sayfası | 🟡 ORTA | `/for/accountants`, `/for/agencies`, `/for/agent-builders` |
| 20 beta kullanıcı (G2 için) | 🟢 YUMUŞAK | Şu an 0. G2/Capterra bunsuz değersiz |
