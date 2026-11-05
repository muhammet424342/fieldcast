# Fieldcast — deploy paketi

Belge (PDF / duz metin) -> yapilandirilmis JSON. Alan adlarini sen verirsin,
tipli JSON geri gelir. Bulunamayan alan `null` doner, uydurulmaz.

## Cloudflare'a alma

    cd cloudflare && npx wrangler deploy

API anahtarlari Worker'da `npx wrangler secret put` ile, sunucudaki API'de ise kendi .env dosyasinda tutulur:

| Degisken | Deger | Zorunlu |
|---|---|---|
| `NVIDIA_API_KEY` | `~/.nvidia_key` icindeki anahtar | EVET |
| `DEEPSEEK_API_KEY` | yedek saglayici | hayir |

`NVIDIA_API_KEY` yoksa servis calismaz ve bunu acikca soyler.

## Motor

26 Agu 2026 olcumu (10 alanli gercek fatura):

| Model | Skor | Sure |
|---|---|---|
| minimaxai/minimax-m3 | 10/10 | 1,5 sn |
| moonshotai/kimi-k3 | 10/10 | 2,7 sn |
| mistralai/mistral-nemotron | 10/10 | 3,7 sn |
| meta/llama-3.1-70b-instruct | 10/10 | 4,2 sn |
| meta/llama-3.1-8b-instruct | 8/10 | 1,2 sn (tarih hatasi - LISTEDE YOK) |

Sira: NVIDIA (ucretsiz) -> DeepSeek (ucretli, son care).
Biri duserse siradaki denenir; hepsi duserse 502 + hangi saglayicinin
neden dustugunu yazan acik hata doner. Sessiz korlesme yok.

## Uclar

- `GET /health` - canlilik
- `GET /` - servis tanimi
- `POST /v1/extract` - `X-API-Key` zorunlu
  - JSON: `{"text": "...", "fields": ["invoice_number","total"]}`
  - multipart: `file` + `fields=a,b,c` (PDF -> pdfplumber)

## Dogrulanmis testler (26 Agu 2026)

- 10 alanli fatura, multipart dosya -> 10/10 dogru, 2,0 sn
- Olmayan 4 alan istendi -> dordu de `null`, uydurma yok
- Gecersiz API anahtari -> 401
- Bozuk saglayici anahtari -> 502 + acik hata zinciri

## Not

Kullanim sayaci henuz kalici bir depoda degil (su an surec icinde tutuluyor;
yeniden baslatmada sifirlanabilir). Gercek kota takibi icin kalici bir veri deposu gerekir
(ilk odeme geldikten sonraki is).
