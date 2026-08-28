# Fieldcast — Dizin Kayıt Dosyası

**Amaç:** her dizinde form doldurmak 2-3 dakika sürsün. Aşağıdakiler kopyala-yapıştır hazır.

**Not:** Ben hesap açamıyorum (bu benim için sert bir sınır). Hesabı sen açtıktan ve
Chrome'da giriş yapmış durumda kaldıktan sonra formları ben doldurup gönderebiliyorum.

---

## Her dizinde aynı olan alanlar

| Form alanı | Değer |
|---|---|
| Product name | `Fieldcast` |
| Website / URL | `https://fieldcast-peach.vercel.app` |
| Tagline (kısa) | `Documents in, structured JSON out. One API call.` |
| 60 karakter açıklama | `Turn PDFs and invoices into structured JSON in one API call.` |
| Category | Developer Tools → API / Document Processing |
| Pricing model | Freemium (free tier: 50 extraction/ay) |
| Starting price | `$19/mo` |
| Free trial / free tier | Evet — kart istemiyor |
| Founder | `Muhammet Karakurt` |
| İletişim e-posta | `muhammet@decaylabs.online` |
| Logo (PNG) | `ekran_goruntuleri/` yanındaki `public/logo-1024.png` |
| Şeffaf logo | `public/logo-512-transparent.png` |
| Favicon | `public/favicon.ico` |
| Gizlilik | `https://fieldcast-peach.vercel.app/privacy.html` |
| Şartlar | `https://fieldcast-peach.vercel.app/terms.html` |
| Tags | `api, document-parsing, pdf-to-json, invoice-extraction, data-extraction, ai-agents, x402, developer-tools` |

**Ekran görüntüsü sırası** (dizin kaç tane isterse baştan al):
`01-anasayfa-ust` → `02-nasil-calisir` → `04-ajanlar` → `05-fiyatlandirma` → `06-sss` → `08-mobil`

---

## Uzun açıklama — AJAN / MCP dizinleri için (Katman 4)

> Fieldcast exposes document extraction as a service that autonomous agents can actually buy.
>
> Alongside the standard API-key endpoint, it serves an x402 endpoint that requires no account and no key. An agent calls it, receives HTTP 402 with machine-readable payment terms, settles $0.01 in USDC on Base, and receives the extracted JSON in the same request flow.
>
> This closes a real gap: an autonomous agent cannot complete a signup form, accept terms, or enter a credit card — but it can pay per call. Any agent that needs to turn an invoice, receipt or contract into structured fields can use Fieldcast as a paid tool with zero onboarding.
>
> Input: a PDF or text plus a list of field names. Output: typed JSON — numbers as numbers, dates as ISO-8601 — with `null` for anything the document does not contain, never a fabricated value.

⚠️ **x402 ucu HENÜZ CANLI DEĞİL.** Kod var (`docparse_x402.py`) ama deploy edilmedi ve
cüzdan adresi/mainnet ayarı yapılmadı. Bu metni kullanmadan önce ya x402'yi yayına al,
ya da o paragrafı çıkar. **Olmayan özelliği dizine yazmak = kayıt silinme sebebi.**

---

## Uzun açıklama — AI dizinleri için (Katman 3, x402 iddiası olmadan)

> Fieldcast is an LLM-native document extraction API. Instead of computer-vision templates or a fixed invoice schema, it reads the document and returns exactly the fields you asked for.
>
> You pass a list of field names with the request. It handles layouts it has never seen before, works across languages, and adapts to a new document type by changing one array in your request rather than retraining anything.
>
> The design constraint that matters most: it never invents a value. A field absent from the source comes back `null`. For accounting and finance workflows, a missing total is recoverable — a hallucinated one is not.
>
> Free tier: 50 extractions per month, no card. PDF and plain text supported; OCR for scanned images is on the roadmap.

---

## Kurucu hikâyesi (çoğu dizin istiyor)

> I kept rebuilding the same invoice parser for different projects, and every time the real work was not the extraction — it was maintaining templates that broke whenever a supplier changed their layout. Fieldcast is that step deleted: you name the fields, the API returns them typed.

---

## Doğrulanabilir iddialar (abartma, bunlar ölçüldü)

- 10 alanlı fatura → 10/10 doğru, canlıda 1,8 sn
- Fiş (farklı belge türü, TRY, farklı tarih formatı) → tüm alanlar doğru
- Olmayan alanlar → `null`, uydurma yok
- Tarihler ISO-8601'e normalize, para değerleri sayı tipinde

**Yazma:** "%99 doğruluk", "enterprise-grade", "binlerce kullanıcı". Kullanıcı sayısı şu an 0.
İlk kullanıcılar geldiğinde rakamı güncelleriz.

---

## Dizin durumu (26 Ağu 2026 denetimi)

| Dizin | Kayıt yolu | Hesap gerekli? |
|---|---|---|
| AI Agents Directory | `/submit-agent` | ✅ EVET — "Sign In to Continue" |
| AgentHunter | `/submit` | ✅ EVET — `/auth/login`'e yönlendiriyor |
| AI Agents List | `/submit` | ✅ EVET — Login / Sign up |
| AI Agent Store | `/submit-agent` 404 | ana sayfadan "Submit an AI Agent" ile git |
| APITracker | ana sayfada submit yok | araştırılmalı |
| AI Agents Base | site 404 | ❌ ÖLÜ — tablodan düşür |

**Sonuç: Katman 4'ün tamamı hesap arkasında.** Sırayla hepsinde aynı desen çıktı.

---

## İşbölümü

1. **Sen:** dizinde hesap aç (Google ile giriş en hızlısı), giriş yapmış halde bırak
2. **Ben:** bu dosyadaki değerlerle formu doldurur, görselleri yükler, gönderir, `dizin_takip.csv`'ye işlerim

Tek seferde bir hesap açman yeterli — sonrasını ben götürürüm.
