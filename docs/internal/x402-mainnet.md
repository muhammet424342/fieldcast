# x402 — Base mainnet kapisi

`api/pay.py` ucu: ajan hesap acmadan, cagri basi 0,01 USDC odeyerek cikarim alir.
Bu dosya o kapinin **gercekten ne dondugunu** gosterir.

Durum (5 Eki 2026): varsayilan ag **Base mainnet** (`eip155:8453`), odeme
alici adresi bagli, facilitator calisiyor. Artik **gercek para** akabilir.

> Deploy YAPILMADI. Bu degisiklik henuz Vercel'e cikmadi; testler yesil, insan
> onayi bekliyor. Asagidaki ciktilar **yerelde** uretilmistir.

---

## 1. Uc ne donuyor (gercek cikti)

Uc su an `api/pay.py` ile ayni ayarlarda ayakta. Ciktilar bu komutla alindi
(proje yorumlayicisi; duz `python3` ile de ayni sonuc alinir):

    python3 -c "
    import sys; sys.path.insert(0,'api'); import pay
    c = pay.app.test_client()
    print(c.get('/x402/health').get_json())
    print(c.post('/x402/extract', json={'text':'x','fields':['a']}).status_code)"

### Ucretsiz tani: `GET /x402/health` -> 200

    {
      "aciklama": "Base (ana ag, gercek USDC)",
      "facilitator": "https://facilitator.payai.network",
      "network": "eip155:8453",
      "para": "GERCEK USDC",
      "pay_to": "0x3f425d6ffd2855585483d65da684651e330759e0",
      "price": "$0.01",
      "status": "ok",
      "testnet": false
    }

`network` tek basina birakilmadi: `testnet` bayragi + `para` (gercek/sanal) +
insan diliyle `aciklama` birlikte doner. Musteri 0,01 USDC gorup test parasini
gercek sanmasin diye. `X402_NETWORK=eip155:84532` verilirse ayni uc
`"para": "sanal"` ve `"testnet": true` doner.

---

## 2. Calisan kapi ornegi: curl -> 402 -> PAYMENT-REQUIRED -> odeme -> 200

Uc yerelde sunmak icin (dosyanin `__main__` blogu yok, dogrudan calistirmak
sunucu kaldirmaz) — proje yorumlayicisi (flask/x402 kurulu olan) ile:

    PYTHONPATH=api python -c "import pay; pay.app.run(port=8113)"

Port 8113 secildi: 8010 bu makinede `/opt/projeler/docparse/docparse_app.py`
(canli servis) tarafindan kullaniliyor; dokunulmadi.

### Adim 1 — odemesiz istek, HTTP 402

    curl -i -X POST http://127.0.0.1:8113/x402/extract \
      -H "Content-Type: application/json" \
      -d '{"text":"INVOICE INV-2043  Total: 1,240.50 EUR","fields":["invoice_number","total"]}'

Gercek cevap (ilk satirlar):

    HTTP/1.1 402 Payment Required
    Content-Type: application/json
    PAYMENT-REQUIRED: eyJ4NDAyVmVyc2lvbiI6MiwiZXJyb3IiOiJQYXltZW50IHJlcXVpcmVkIiw…

Govde `{}` (bos). Sartlar **yalnizca** `PAYMENT-REQUIRED` basliginda gelir;
basligin cozulmus halinde `error` alani `"Payment required"` yazar.

### Adim 2 — sartlari oku (baslik base64 JSON'dur)

    curl -s -D - -o /dev/null -X POST http://127.0.0.1:8113/x402/extract \
      -H "Content-Type: application/json" \
      -d '{"text":"INVOICE INV-2043","fields":["invoice_number"]}' \
      | grep -i '^payment-required:' | cut -d' ' -f2 | tr -d '\r' \
      | base64 -d | jq '.accepts[0]'

Bu komut satiri basindan sonuna kadar **bu dosyada calistirilip dogrulandi**,
cikti asagidakidir:

    {
      "scheme": "exact",
      "network": "eip155:8453",                                    <- Base mainnet
      "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",      <- USDC (Base)
      "amount": "10000",                                          <- 0,01 USDC
      "payTo": "0x3f425d6ffd2855585483d65da684651e330759e0",      <- bizim cebe
      "maxTimeoutSeconds": 300,
      "extra": { "name": "USD Coin", "version": "2" }
    }

Odeme zinciri Base mainnet USDC adresini `x402/mechanisms/evm/default_assets.py`
icinden alir (yorumda `Base mainnet USDC` yaziyor). `amount` atomik birimdir:
6 ondalik x 0,01 = 10.000.

### Adim 3 — odemeyi yap

Odeme cuzdani imzalamak gerekir; ham `curl` ile EIP-3009 imzasi uretilmez.
Bu adim repodaki hazir istemciyle yapilir (`buyer-agent/`, ayni akis):

    import { x402Client, wrapFetchWithPayment } from "@x402/fetch";
    import { ExactEvmScheme } from "@x402/evm/exact/client";

    const x402 = new x402Client();
    x402.register("eip155:8453", new ExactEvmScheme(walletClient.account));
    const fetchPaid = wrapFetchWithPayment(fetch, x402);

    const res = await fetchPaid("https://…/x402/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, fields }),
    });
    // 200 + govde: cikarim sonucu
    // PAYMENT-RESPONSE basligi: uzlasma/teslim kaniti

Kisa curl ile yapilamayan tek adim bu. Elle kurulmak istenirse ikinci istek
odeme yukunu `PAYMENT-SIGNATURE` basliginda tasir (x402 v2 adi; sunucu v1 adi
`X-PAYMENT`'i de kabul eder). Yuk base64 JSON'dur. Sunucu once `verify` eder,
cikarim kosuluna uygunsa 200 doner, uzlasma `settle` ile olur.

> **Durustluk notu:** 1. ve 2. adimlar bu calismada gercekten calistirildi ve
> yukaridaki ciktilar kopyalandi. 3. adim (imzali odeme -> 200) **bu calismada
> calistirilmadi** — doldurulmus bir Base mainnet cuzdani yok. Ayni odeme
> akisi `buyer-agent/` icinde canli calisiyor ve `buyer-agent/README.md`
> Base mainnet'te uzlasma (`settle`) oldugunu kaydediyor; ayri bir dogrulama
> isidir. 3. adimi deploy sonrasi canli kurusta dogrulamak gerekir.

### Adim 4 — HTTP 200

Odeme dogrulanip cikarim bitince: `200` + `{"data": {...}, "chars_processed": N}`.

Uc 4xx/5xx donerse odeme **alinmaz** (x402 middleware tahsilati iptal eder),
yani basarisiz cikarim icin ajana para kesilmez.

---

## 3. Fiyat semasi

| Kalem | Deger | Nerede |
|---|---|---|
| Birim fiyat | `$0.01` (0,01 USDC) | `X402_PRICE`, varsayilan |
| Atomik tutar | `10000` (6 ondalik) | 402 ciktisinda `accepts[0].amount` |
| Varlik | USDC, `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | x402 SDK varsayilan asset'i |
| Ag | `eip155:8453` (Base mainnet) | `X402_NETWORK`, varsayilan |
| Alici | `0x3f425d6ffd2855585483d65da684651e330759e0` | `X402_PAY_TO`, varsayilan |
| Sema | `exact` (EIP-3009 transferWithAuthorization) | `ROUTES` icinde sabit |
| Odeme penceresi | 300 sn | `maxTimeoutSeconds` |
| Odemesiz cagri | HTTP 402 | ucretsizce fiyat ogrenilir |
| Adres bos (`X402_PAY_TO=""`) | HTTP 503, uc kapali | bedava cikarim acilmaz |

Fiyat artik gercek para birimi. `X402_PRICE` degistirilebilir; `X402_NETWORK`
degistirilerek test agina (sanal para) donulebilir.

## 4. Akis semasi

    Ajan (istemci)                Fieldcast api/pay.py          Facilitator (PayAI)      Base zinciri
         |                                |                             |                  |
    (1) POST /x402/extract                |                             |                  |
         |  -- odemesiz ------------------>|                             |                  |
         |                                | /supported (ag/sema) ------>|                  |
         |<-- 402 + PAYMENT-REQUIRED -----|                             |                  |
         |    (base64: ag, varlik, 10000,  |                             |                  |
         |     payTo)                      |                             |                  |
         |                                |                             |                  |
    (2) ajan sartlari okur, 0,01 USDC <-- USDC var mi? + 300 sn icinde imzalar
         |    (EIP-3009 imzasi)            |                             |                  |
    (3) POST /x402/extract                |                             |                  |
         |  -- PAYMENT-SIGNATURE: <base64> ->|                             |                  |
         |     (X-PAYMENT de kabul edilir)   |                             |                  |
         |                                | /verify ------------------->|                  |
         |                                |<-- dogrulandi -------------|                  |
         |                                |   (hata -> 402, para alinmaz)                  |
         |                                | cikarim calisir             |                  |
         |                                | (400/5xx ise iptal)         |                  |
         |                                | /settle ------------------->|                  |
         |                                |                             | onay/odeme ----->|
         |<-- 200 + {"data": …} ----------|                             |                  |
         |    PAYMENT-RESPONSE              |                             |                  |
         |    (uzlasma kaniti)              |                             |                  |

Notlar:

- `/verify` sarti tutmazsa 402 doner, **tahsilat yapilmaz**.
- Cikarim 4xx/5xx donerse `settle` yapilmaz.
- 402 uretmek bile facilitatorun `/supported` ucunu gerektirir: adres yanlissa
  uc 402 yerine hata firlatir. (Bu yuzden varsayilan adres testlerde canli
  dogrulanir.)
- Sunucu anahtari tutmaz; odemeyi ajan yapar, sunucu yalnizca dogrular.

## 5. Ortam degiskenleri

Ucunun de varsayilani vardir ama hepsi ENV ile override edilebilir; Vercel'de
`.env` / Environment Variables'a yazilir. hicbiri koda gomulu degildir.

| Degisken | Varsayilan | Anlami |
|---|---|---|
| `X402_NETWORK` | `eip155:8453` | farkli ag (testnet icin `eip155:84532`) |
| `X402_FACILITATOR_URL` | `https://facilitator.payai.network` | dogrulayici/uzlastirici |
| `X402_PAY_TO` | `0x3f425d6…59e0` | bos birakilirsa uc 503 doner (kapanir) |
| `X402_PRICE` | `$0.01` | cagri basi fiyat |
| `X402_BAZAAR` | `1` | `0` ise kesif uzantisi kurulmaz |

### Neden facilitator degisti

Ayni gun iki adres `/supported` ucundan okundu:

| Adres | HTTP | kind sayisi | `eip155:8453` + `exact` |
|---|---|---|---|
| `https://x402.org/facilitator` | 200 | 11 | **yok** |
| `https://facilitator.payai.network` | 200 | 35 | **var** |

`x402.org` listesi test aglariyla sinirli (`eip155:84532` var, `eip155:8453` yok).
PayAI anahtar istemeden mainnet'i tasiyor. Bu yuzden eski yorumdaki "anahtarsiz
mainnet yapamaz" notu gercek durumla degistirildi.

## 6. Dogrulama

Testler: `tests/test_x402_ana_network_ve_testnet.py` (29 test, stdlib `unittest`).

    python3 -m unittest discover -s tests -v

Hangi python ile acilirsa acilsin ayni sonuc verir: dosya gercek paketleri
(flask/x402/httpx/idna) arar, bulamazsa proje `.venv` yorumlayicisini kendisi
bulup testleri orada yeniden calistirir. Bunu bir denetimde yasandi: sistem
`python3` ile acildiginda 26 ayri `ModuleNotFoundError` aliniyordu; duzeltme
sonrasi ayni komut yesil.

Kapsam: varsayilan ag/adres/facilitator, ENV override, bos `PAY_TO` -> 503,
health ciktisindaki gercek/sanal ayrimi, 402 sartlari (ag, varlik, 10.000, alici),
ust yorumun eski iddiayi tasimamasi ve PayAI'nin `/supported` ucundan
`eip155:8453` + `exact` ilan etmeye devam etmesi. Ayrica yorumlayici sablonunun
gercekten calistigi (paketler kurulu, bulunan yorumlayici paketleri goruyor).

### Mutasyon kontrolu

Bir degisikligin testi yazildi demek, testin onu tutuyor demek degildir. Sekiz
degisiklik teker teker geri alindi; hepsinde testler kirmizi oldu:

| # | Geri alinan degisiklik | Sonuc |
|---|---|---|
| 1 | ag varsayilani `eip155:84532`'ye dondu | 5 test kirmizi |
| 2 | facilitator `x402.org`'a dondu | 7 test kirmizi |
| 3 | `X402_PAY_TO` bos birakildi | 9 test kirmizi |
| 4 | `/x402/health` ciktisindan `network` alani kaldirildi | 1 test kirmizi |
| 5 | `para` alani sabitlendi (testnet ayrimi gitti) | 1 test kirmizi |
| 6 | eski "anahtarsiz mainnet yapamaz" yorumu geri geldi | 1 test kirmizi |
| 7 | bootstrap yorumlayici yolunu `realpath` ile cozd | 2 test kirmizi |
| 8 | paket dogrulamasi kaldirildi | 26 test kirmizi |

Satir 7 ve 8, duzeltmenin kendisi icin: yorumlayici yolunu cozmek site-packages'i
sildiriyor ve denetcinin gördugu hatanin aynisi geri geliyordu.

## 7. Bilinen bosluklar

- `README.md` icine bu dosyaya link **eklenmedi**: bu calismada dosya siniri
  `api/pay.py`, `docs/internal/x402-mainnet.md` ve test dosyasi ile kisitliydi.
  README'nin x402 bolumu hala "public `x402.org` facilitator only advertises
  testnets" diyor ve PayAI/mainnet gecisini yansitmıyor. Baglanacak metin ve
  yer hazir; dosya izni verilirse tek satir.
- `Access-Control-Expose-Headers` eklenmedi. Tarayici JS'i `PAYMENT-REQUIRED`
  basligini **okuyamaz** (sunucudan sunucuya ajanlar sorun degil). Tarayici
  icinden x402 akisi istenirse eklenmeli.
- 3. adim (imzali odeme -> 200) bu calismada dogrulanmadi, bolum 2'de yazili.
- `api/pay.py` icinde `if __name__ == "__main__"` blogu **yok**; dogrudan
  `python api/pay.py` sunucu kaldirmaz (README'deki o komut ise calismiyor).
  Yerelde calistirmak icin bolum 2'deki `PYTHONPATH=api python -c "import pay;
  pay.app.run(...)"` yolu kullanildi. Ayri bir is; bu dosyada degistirilmedi.
- `/tmp` sayaci Vercel'de soguk baslatmada sifirlanir (tum servis icin ortak).
- Vercel'e **deploy edilmedi**.
