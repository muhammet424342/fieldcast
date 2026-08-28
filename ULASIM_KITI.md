# Fieldcast — İlk Müşteri Ulaşım Kiti

**Canlı:** https://fieldcast-peach.vercel.app
**Gönderen:** muhammet@decaylabs.online (DKIM/SPF/DMARC kurulu, warmup yapıldı)

---

## Önce iki uyarı — bunlar seni daha önce yaktı

### 1. Adres TAHMİN ETME
Geçen sefer cold-mail'in **%80'i bounce** etti çünkü adresler `careers@`, `info@` diye tahmin edilmişti.
Google'ın şikâyet eşiği %0,1. Yüksek bounce = domain yanar = `decaylabs.online` bir daha hiçbir yere ulaşamaz.

**Kural: adresi bir yerde YAZILI görmeden gönderme.** Kaynaklar aşağıda.

### 2. Muhasebeci API satın almaz
Fieldcast bir API — kullanmak için kod yazmak gerekiyor. Mali müşavir kod yazmaz.
Bu yüzden liste iki katmanlı:

| Katman | Kim | Bugün satın alabilir mi? |
|---|---|---|
| **A** | Muhasebe/lojistik/gider yazılımı yapan küçük SaaS ve geliştirici ajansları | ✅ Evet, bugün entegre eder |
| **B** | Otomasyon kullanan muhasebe firmaları | ⚠️ Ancak geliştirici varsa |

**A ile başla.** B için arayüz gerekiyor, o yok.

---

## Asıl koz: teklif değil, KANIT gönder

"API'me bak" demek işe yaramıyor. Bunun yerine:

> **"Bana 5 gerçek faturanı yolla, çalıştırıp sonucu göndereyim. Ücretsiz, kayıt yok."**

Neden çalışır:
- Risk sıfır — kayıt yok, kart yok, taahhüt yok
- Cevap vermesi kolay: dosya sürükle-bırak
- Kendi belgesindeki sonucu görüyor, benim kıyaslamama güvenmesi gerekmiyor
- Sonuç iyiyse ikna zaten olmuş oluyor

Bu, sıfır müşterisi olan tek kişilik bir ürünün elindeki en güçlü hamle. Referansın yok, ama **çalışan bir şeyin var**.

---

## Mail 1 — Katman A (geliştirici / küçük SaaS)

**Konu:** `invoice parsing`

> Hi [AD] — you're building [ÜRÜN] for [KİTLE], so you've probably already hit the part where every supplier's invoice layout is different.
>
> I built an API that skips the template step: you send the document plus the field names you want, and get typed JSON back. Fields that aren't in the document come back null instead of a made-up value.
>
> Want me to run five of your real invoices through it and send you the output? No signup, nothing to install.
>
> Muhammet

*(63 kelime)*

---

## Mail 1 — varyant: gider/harcama yazılımı

**Konu:** `receipt data`

> Hi [AD] — [ÜRÜN] handles receipts, which means someone on your side is dealing with the fact that no two receipts look alike.
>
> I run a document extraction API. You name the fields, it returns them typed — totals as numbers, dates as ISO. Anything missing comes back null rather than invented, which matters when the number goes into someone's books.
>
> Send me five real receipts and I'll show you the output. Takes me two minutes.
>
> Muhammet

*(72 kelime)*

---

## Mail 1 — Katman B (geliştiricisi olan muhasebe firması)

**Konu:** `supplier invoices`

> Hi [AD] — if [FİRMA] is keying supplier invoices in by hand, that's roughly two minutes each. At 500 a month it's 17 hours.
>
> I built something that turns an invoice PDF into structured fields in about two seconds. It doesn't need a template per supplier, and it returns null instead of guessing when a field isn't there.
>
> Happy to run five of your invoices and send you what comes back. Free, no signup.
>
> Muhammet

*(74 kelime)*

---

## Takip 1 — 4 gün sonra (yeni açı, "kontrol ediyorum" DEĞİL)

**Konu:** aynı thread'de yanıtla

> One thing I should have mentioned: the reason I keep going on about null is that it's the whole design choice.
>
> A parser that invents a total looks like it worked. You find out in reconciliation three months later. Fieldcast leaves the field empty instead, so it lands in a review queue the same day.
>
> Still happy to run a few of your files if useful.

*(62 kelime)*

---

## Takip 2 — 7 gün sonra (somut kanıt)

**Konu:** aynı thread

> Concrete example, since I'd rather show than describe.
>
> Ten-field invoice, live: all ten correct in 1.8 seconds. Same endpoint on a receipt in a different currency and date format: every field right, and four fields that weren't in the document came back null instead of fabricated.
>
> Free tier is 50 a month if you want to try it yourself: fieldcast-peach.vercel.app

*(60 kelime)*

---

## Takip 3 — 10 gün sonra (kapanış, buna uy)

**Konu:** aynı thread

> I'll stop here — you're clearly busy and I don't want to be another thing in your inbox.
>
> If invoice or receipt parsing ever becomes a problem worth solving, the free tier stays up and my address doesn't change.
>
> Good luck with [ÜRÜN].

*(44 kelime)*

**Kapanış mailini yaz ve GERÇEKTEN dur.** Devam edersen spam şikâyeti alırsın, domain yanar.

---

## Gerçek adres nereden bulunur (tahmin YOK)

| Kaynak | Ne bulunur | Nasıl |
|---|---|---|
| **GitHub profili** | Geliştiricinin herkese açık maili | Profil sayfası, ya da `git log` içindeki commit maili |
| **Şirket "Team/About" sayfası** | İsim + mail, yazılı | Küçük SaaS'lar genelde açıkça yazar |
| **X/Twitter bio** | "mail: x@y.com" | Indie hacker'ların çoğu yazıyor |
| **Indie Hackers / Product Hunt** | Kurucu profili | Ürün sayfasındaki maker linki |
| **Kendi blogu / kişisel site** | İletişim sayfası | En güvenilir kaynak |

**Yasak:** `info@`, `contact@`, `hello@`, `careers@` tahmini. Bunlar hem bounce hem de zaten kimse okumuyor.

**Gönderme öncesi:** her adresi SMTP doğrulamasından geçir (PC'deki Apollo kurulumu bunu yapıyor).
Bounce oranı %4'ü geçerse **DUR**, listeyi temizle.

---

## Kampanya kuralları

| Kural | Sebep |
|---|---|
| Tek seferde **en fazla 50 kişi** | ≤50'lik listeler 2,76× daha iyi yanıt alıyor |
| Günde **en fazla 20 mail** | Warmup'ı bozma |
| **Perşembe** gönder | En yüksek yanıt günü (%6,87) |
| Her mail **75 kelime altı** | %83 daha fazla yanıt |
| Mailde **tek link**, resim yok | Spam filtresi |
| `[AD]` ve `[ÜRÜN]` **gerçekten doldurulacak** | Doldurulmamış şablon anında yakalanıyor |

---

## Gerçekçi beklenti — hayal kurmayalım

50 mail → ~14 açılma → **2-3 yanıt** → 1 olumlu → belki 1 deneme.

İlk kampanyadan müşteri çıkmayabilir. Normal olan bu. Ölçmen gereken şey satış değil:

1. Bounce oranı %4'ün altında mı? (Değilse liste kalitesi bozuk)
2. Yanıt geldi mi? (Gelmiyorsa mesaj yanlış)
3. "5 belge yolla" teklifini kabul eden oldu mu? (Asıl sinyal bu)

3. madde 50 mailde bir kez bile olmuyorsa, sorun mail değil — **yanlış kitleye satıyoruz** demektir ve kanal değiştirmek gerekir.

---

## Bu kanal ölürse sıradaki

Cold mail tek yol değil, hatta muhtemelen en iyisi de değil. Alternatifler:

- **Ürünü kullananın olduğu yerde bulunmak:** r/Accounting, r/bookkeeping, Indie Hackers'ta "invoice parsing" sorulduğunda gerçekten yardımcı cevap yazmak (link atmadan)
- **Karşılaştırma sayfalarının SEO'su:** `/alternatives/docparser` zaten yazıldı, arama trafiği zamanla gelir
- **Ajan dizinleri:** hesap açılınca 8 dizin hazır bekliyor
