// Fieldcast x402 proxy - Cloudflare Worker (workers.dev, ucretsiz kota).
//
// NE YAPAR
// Odeme ucunu Vercel'e baglamadan sunabilir hale getirir. Worker sirada bir
// vektor degildir:
//   1) Resmi site yollari (/, /docs) RESMI SITE olarak isaretlenir: Worker
//      bunlari kendisi API diye degil, "site burada" diye isaretler ve
//      SITE_URL'e yonlendirir.
//   2) API yollari (/x402/*, /v1/*, /health, /.well-known/x402) sunucudaki
//      Fieldcast uygulamasina AKTARILIR. Odeme dogrulamasi Worker'da YOK:
//      Worker 402 sartlarini ve odemeyi degistirmez, oldugu gibi gecer.
//   3) /.well-known/x402 kesif manifesti Worker'in KENDI ortam degiskenlerinden
//      uretilir (X402_PAY_TO / X402_NETWORK / X402_PRICE /
//      X402_FACILITATOR_URL). Boylece kesif, origin cokerten de calisir.
//
// NEDEN BU KADAR KOD
// Vercel'in guvenlik katmani (bot sinyali) arkasindaki bir uca korumasiz
// GET atildiginda 200 + HTML "Security Checkpoint" donuyor. Boylece:
//   - Ucun HTTP kodu 200 olsa bile o gercek cevap DEGIL.
//   - Bu sayfayi oldugu gibi gecmek, 200 donen bir sahte uc yaratir.
// Bu yuzden Worker cevabi denetler: guvenlik isareti gorulirse cevabi
// GECMEZ; 502 + hangi katmanin suclu oldugunu yazar.
//
// KATMAN ATFI (hata durumunda loglanan suclu)
//   vercel  -> origin Vercel katmaninda kesildi (checkpoint/mitigated)
//   worker  -> Worker'in kendi hatasi: origin tanimsiz, zaman asimi, hatali kod
//   app     -> Worker ve Vercel temiz, hata sunucudaki uygulamadan geldi
//
// ORTOK
// Cloudflare Worker edge'de calisir; sunucudaki uygulama 127.0.0.1'e bagli
// (bkz. fieldcast-api.service / fieldcast-gate-base.service) ve Edge oraya
// ULASAMAZ. Bu yuzden X402_ORIGIN her zaman PUBLIK bir https adresi olmak
// zorundadir. Deger verilmezse Worker "hangi uca gidecegimi bilmiyorum"
// diyerek 503 verir; yanlis adrese istek atmayi dener.

const VARSAYILAN_SITE = "https://fieldcast-peach.vercel.app"; // README'deki canli adres

// API yollari: sunucudaki uygulamaya aktarilir.
const API_ONEKLERI = ["/x402/", "/v1/", "/health", "/.well-known/x402"];

// Resmi site yollari: Vercel'de kalir, Worker burada ayirir ve isaretler.
const SITE_YOLLARI = ["/", "/docs"];

// Worker'in KENDI cevaplarinda kullandigi iz. Saglik probu (scripts/health_probe.py)
// bu basliga bakarak "Worker temizleniyor mu, temizlenmedi mi" ayirimi yapar.
export const KATMAN_BASLIK = "x-fieldcast-layer";
export const WORKER_DEGERI = "worker";

// Upstream'ten GECIRILMEYECEK basliklar.
//   - set-cookie: brief geregi cevapta olmamali; ayrica Worker paylasimli
//     onbellek arkasinda oldugu icin bir ajanin oturumu baskasina sizar.
//   - x-vercel-mitigated / x-vercel-sc-*: guvenlik katmani izleri; origin'de
//     kalirlarsa "bu cevap Vercel'den gecmis" demektir, o da gecmemeli.
//   - x-vercel-id/cache/error, x-matched-path: origin'in edge bilgisi, istemci
//     bunu gormemeli (ve probu bunlari hata sanabiliyor).
//   - server: upstream yiginini sizdirir.
// NOT: content-type, PAYMENT-REQUIRED, PAYMENT-RESPONSE, CORS basliklari
// KORUNUR. 402 sartlari bu yoldan gecer; silinirse odeme akisi kirilir.
const YASILAN_BASLIKLAR = new Set([
  "set-cookie",
  "x-vercel-mitigated",
  "x-vercel-sc-headers",
  "x-vercel-sc-cookies",
  "x-vercel-sc-host",
  "x-vercel-sc-failed",
  "x-vercel-id",
  "x-vercel-cache",
  "x-vercel-error",
  "x-vercel-deployment-url",
  "x-matched-path",
  "server",
]);

// Istemciden upstream'e ILETILMEYECEK basliklar.
//   - cookie: tarayici oturumu, origin'in WAF'ini tetikler; ajan istegi
//     oturum tasimaz.
//   - host: upstream kendi adi gormeli.
//   - accept-encoding: Worker govdeyi zaten cozuyor, gzip basligi yaniltir.
const GONDERILMEYEN_BASLIKLAR = new Set(["cookie", "host", "accept-encoding"]);

// Odeme akisinin ayakta olmasi icin gerekli basliklar. Bunlar korunur.
// content-length / transfer-encoding GECIRILMEZ: govde akis olarak iletilir,
// uzunlugu runtime yeniden hesaplar (upstream chunked alir). Eski
// content-length'i kopyalamak, govde akisi bir kez bozulursa istegi asili
// birakirdi.
export const KORUNAN_BASLIKLAR = [
  "payment",
  "x-payment",
  "x-payment-response",
  "content-type",
  "accept",
  "x-api-key",
];

// Guvenlik katmani tespiti. Govde metni kucuk harfe CEVRILMEZ: Vercel'in
// sayfasinda "Security Checkpoint" yaziyor, kucuk harf varyanti yok; ama
// govde 1 MB'a kadar olabilir, bu yuzden sadece basliga bakilir ve govde
// metni sadece ayri bir bayrak icin kucuk bir onizleme alir.
const CHECKPOINT_METNI = "Security Checkpoint";

export function siniflandir(yol) {
  // Yol hangi katmana ait? -> 'api' | 'site' | 'yok'
  const temiz = yol.split("?")[0];
  if (SITE_YOLLARI.includes(temiz)) return "site";
  for (const onek of API_ONEKLERI) {
    if (onek.endsWith("/") ? temiz.startsWith(onek) : temiz === onek) return "api";
  }
  return "yok";
}

export function baslikCiftleri(basliklar) {
  /*
   * Basliklari her zaman [[ad, deger], ...] dizisine indirger.
   *
   * NEDEN: bu yardimcilar iki tur girdiyle cagrilir.
   *   - Uretimde `Headers` nesnesi (fetch cevabi / istegi).
   *   - Testte [[ad, deger], ...] dizisi: testler Worker'i node icinde
   *     dogrudan cagirir, girdi JSON argv ile gecer ve `Headers` JSON'da
   *     `{}` olur; tek yol cift dizisi.
   *
   * DKKAT: diziye `.keys()` uygulanmaz. Array.prototype.keys() VAR ve INDEKS
   * dondurur (0, 1, 2...) -> `baslik.keys()` sessizce numara listeler, sonra
   * numara.toLowerCase() patlar: "ad.toLowerCase is not a function".
   * Object.keys(Headers) da dogru degil: her zaman BOS doner (alanlar
   * sembolik dizide), yani filtreler sessizce gecersiz kalirdi.
   * Bu yuzden girdi turu once ayirt edilir.
   */
  if (!basliklar) return [];
  if (Array.isArray(basliklar)) return basliklar;
  if (typeof basliklar.entries === "function") return [...basliklar.entries()];
  return Object.entries(basliklar);
}

export function yaslanacakBasliklar(basliklar) {
  /*
   * Upstream cevabindan cikis yapilacak basliklarin kucuk harf kumeesi.
   * Girdi turu baslikCiftleri()'ne birakilir (Headers veya cift dizisi).
   */
  const sonuc = new Set();
  for (const [ad] of baslikCiftleri(basliklar)) {
    const k = String(ad).toLowerCase();
    if (YASILAN_BASLIKLAR.has(k)) sonuc.add(k);
  }
  return sonuc;
}

export function temizleBasliklar(headers) {
  /*
   * Upstream cevabini istemciye gondermeden once arindirir.
   *
   * Testin kilitledigi iki sart burada saglanir: set-cookie ve
   * x-vercel-mitigated asla cikis yapmaz. PAYMENT-REQUIRED gibi odeme
   * basliklari KALIR (402 sartlari odeme akisinin kendisidir).
   */
  const cikti = new Headers();
  const yaslanan = yaslanacakBasliklar(headers);
  for (const [ad, deger] of baslikCiftleri(headers)) {
    const k = String(ad).toLowerCase();
    if (yaslanan.has(k)) continue;
    if (k === "set-cookie2") continue;
    cikti.append(ad, deger);
  }
  cikti.set(KATMAN_BASLIK, WORKER_DEGERI);
  return cikti;
}

export function istemciBasliklariniSec(headers) {
  // Istemciden upstream'e gonderilecek basliklar (korunan odeme + CORS basliklari).
  const cikti = new Headers();
  for (const [ad, deger] of baslikCiftleri(headers)) {
    const k = String(ad).toLowerCase();
    if (GONDERILMEYEN_BASLIKLAR.has(k)) continue;
    if (KORUNAN_BASLIKLAR.includes(k)) cikti.set(ad, deger);
  }
  return cikti;
}

export function guvenlikIsareti(kod, basliklar, govdeMetni) {
  /*
   * Cevap Vercel guvenlik katmanindan mi gecti?
   *
   * Doner: null | {tur, ...}. tur 'baslik' | 'govde'.
   * DIKKAT: x-vercel-id / x-vercel-cache BASARILI cevaplarda da gelir; onlar
   * guvenlik izi DEGILDIR. Yalnizca mitigation/checkpoint izleri sayilir.
   */
  const kucuk = new Map();
  for (const [ad, deger] of baslikCiftleri(basliklar)) kucuk.set(String(ad).toLowerCase(), deger);
  for (const ad of ["x-vercel-mitigated", "x-vercel-sc-headers", "x-vercel-sc-cookies"]) {
    if (kucuk.get(ad)) return { tur: "baslik", ad };
  }
  if (govdeMetni && govdeMetni.includes(CHECKPOINT_METNI)) {
    return { tur: "govde", ad: "govde:'" + CHECKPOINT_METNI + "'" };
  }
  return null;
}

export function kesifManifesti(env, temelUrl) {
  /*
   * Kesif manifestini Worker'in ortam degiskenlerinden uretir.
   *
   * Ayni sozlesme api/pay.py ile: X402_PAY_TO bosken 200 donulur ama
   * `resources` BOSTUR. Boylece kesif motoru var-olmayan bir odemeli ucu
   * listelemez; odeme yapilandirilana kadar manifest ucu ilan etmez.
   */
  const payTo = (env.X402_PAY_TO || "").trim();
  const ag = (env.X402_NETWORK || "eip155:8453").trim();
  const fiyat = (env.X402_PRICE || "$0.01").trim();
  const facilitator = (env.X402_FACILITATOR_URL || "").trim();
  const temel = (temelUrl || "").replace(/\/+$/, "");

  const govde = {
    x402Version: 2,
    service: {
      name: "Fieldcast",
      url: temel,
      description: "Turn PDFs and raw text into structured JSON. Pay per call in USDC.",
    },
    configured: Boolean(payTo),
    facilitator,
    health: "/x402/health",
    resources: [],
  };

  if (!payTo) {
    govde.not = "X402_PAY_TO is not set on this Worker; no paid endpoint is published here.";
    return govde;
  }

  govde.resources = [
    {
      method: "POST",
      path: "/x402/extract",
      mimeType: "application/json",
      description:
        "Extract structured data from a document. Send raw text or a PDF plus the " +
        "list of field names you want, and receive those fields back as typed JSON. " +
        "Fields that do not appear in the document are returned as null rather than invented.",
      accepts: [{ scheme: "exact", network: ag, payTo, price: fiyat }],
    },
  ];
  return govde;
}

export function originUrl(env, yol) {
  /*
   * Origin adresi + yoldan tam upstream adresi.
   *
   * X402_ORIGIN verilmemisse null doner: Worker "nereye gidecegimi
   * bilmiyorum" der ve cagiran tarafa 503 + layer=worker doner. Yanlis ya da
   * uydurma bir adrese istek atmaktan iyidir.
   */
  const origin = (env.X402_ORIGIN || "").trim().replace(/\/+$/, "");
  if (!origin) return null;
  const yolTemiz = yol.split("?")[0];
  return origin + (yolTemiz === "/" ? "" : yolTemiz);
}

export function siteUrl(env) {
  return (env.SITE_URL || VARSAYILAN_SITE).trim().replace(/\/+$/, "");
}

/*
 * Upstream cevabindan suclu katmani okur. Guvenlik checkpoint'i YOKSA bile
 * 5xx/403 gelmis olabilir; o zaman Vercel kimlik basligi varsa katman
 * 'vercel' (edge uretti), yoksa 'app' (sunucudaki uygulama uretti).
 * x-vercel-id/x-vercel-cache BASARILI cevaplarda da oldugu icin burada
 * yalnizca HATA kodlarinda bakilir.
 */
export function hataKatmani(kod, basliklar) {
  const kucuk = new Map();
  for (const [ad, deger] of baslikCiftleri(basliklar)) kucuk.set(String(ad).toLowerCase(), deger);
  const vercelIz =
    kucuk.get("x-vercel-id") || kucuk.get("x-vercel-cache") || kucuk.get("x-vercel-error");
  return vercelIz ? "vercel" : "app";
}

export const HATA_BASLIK = "x-fieldcast-error";

function json(governe, kod, ek = {}) {
  return new Response(JSON.stringify(governe), {
    status: kod,
    headers: {
      "content-type": "application/json; charset=utf-8",
      [KATMAN_BASLIK]: WORKER_DEGERI,
      "access-control-allow-origin": "*",
      "access-control-allow-headers": "Content-Type, X-PAYMENT, PAYMENT, X-API-Key",
      "access-control-allow-methods": "GET, POST, OPTIONS",
      ...ek,
    },
  });
}

/*
 * Bir katmani suclu ilan eden 502. Hata durumunda her zaman bu yol kullanilir.
 * console.error ile yazilir: "hangi katman suclu" bilgisi yalnizca cevapta
 * degil, Worker'in kendi logunda da gorunmelidir (Islem 4).
 */
function katmanHatasi(katman, hata, detay) {
  const govde = {
    error: "upstream_unreachable",
    layer: katman,
    culprit: katman,
    detail: String(hata).slice(0, 200),
    ...(detay || {}),
  };
  console.error(
    `[x402-proxy] katman=${katman} yol=${(detay && detay.path) || "-"} hata=${String(hata).slice(0, 160)}`,
  );
  return json(govde, 502, { [HATA_BASLIK]: katman });
}

export default {
  async fetch(istek, env, ctx) {
    const url = new URL(istek.url);
    const tur = siniflandir(url.pathname);

    // CORS on kontrolu: tarayici tabanli ajanlar OPTIONS ile gelir.
    if (istek.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          [KATMAN_BASLIK]: WORKER_DEGERI,
          "access-control-allow-origin": "*",
          "access-control-allow-headers": "Content-Type, X-PAYMENT, PAYMENT, X-API-Key",
          "access-control-allow-methods": "GET, POST, OPTIONS",
          "access-control-max-age": "86400",
        },
      });
    }

    // --- RESMI SITE: / ve /docs ---------------------------------------------
    // Bunlar API degil. Worker resmi site oldugunu isaretler ve SITE_URL'e
    // yonlendirir. Boylece API adresi acilan bir alan adinda "/" gordugunde
    // "bu uc ne?" degil "site burada" dersin.
    if (tur === "site") {
      const hedef = siteUrl(env) + url.pathname.replace(/\/$/, "");
      return new Response(null, {
        status: 302,
        headers: {
          location: hedef,
          [KATMAN_BASLIK]: WORKER_DEGERI,
          "x-fieldcast-route": "official-site",
          "cache-control": "public, max-age=300",
        },
      });
    }

    if (tur === "yok") {
      return json(
        {
          error: "not_a_fieldcast_route",
          layer: WORKER_DEGERI,
          detail:
            "Bu Worker yalnizca /x402/*, /v1/*, /health, /.well-known/x402 " +
            "ve resmi site yollarini (/, /docs) tanir.",
          path: url.pathname,
        },
        404,
      );
    }

    // --- KESIF: /.well-known/x402 ------------------------------------------
    // Worker'in kendi ortam degiskenlerinden uretilir; origin'e gidilmez.
    // Boylece origin cokertiginde bile ajanlar odemeli ucu gorebilir.
    if (url.pathname === "/.well-known/x402") {
      return json(kesifManifesti(env, url.origin), 200);
    }

    // --- API: origin'e aktar -------------------------------------------------
const hedef = originUrl(env, url.pathname + url.search);
    if (!hedef) {
      // Bu bir Worker hatasidir (yapilandirma), uygulamanin degil.
      const mesaj =
        "X402_ORIGIN ayarli degil. Worker ucun nereye aktaracagini bilmiyor; " +
        "sunucudaki Fieldcast uygulamasinin PUBLIK https adresi verilmeli " +
        "(127.0.0.1 Edge'den ulasilamaz).";
      console.error(`[x402-proxy] katman=${WORKER_DEGERI} yol=${url.pathname} hata=origin_not_configured`);
      return json(
        {
          error: "origin_not_configured",
          layer: WORKER_DEGERI,
          culprit: WORKER_DEGERI,
          detail: mesaj,
          path: url.pathname,
        },
        503,
        { [HATA_BASLIK]: WORKER_DEGERI },
      );
    }

    const govdeVar = istek.method !== "GET" && istek.method !== "HEAD";
    let yanit;
    try {
      yanit = await fetch(hedef, {
        method: istek.method,
        headers: istemciBasliklariniSec(istek.headers),
        body: govdeVar ? istek.body : undefined,
        // Govde akis olarak (ReadableStream) gonderilir: PDF yuklemelerini
        // bellege almak Worker'in 128 MB sinirini yer. `duplex: "half"` bu
        // akisin gonderilebilmesi icin fetch spec'inde sarttir; Node/undici
        // bunu zorunlu tutar, Cloudflare Workers yok sayar. Eksik birakilirsa
        // Node/undici POST'u upstream'e HIC gondermeden TypeError atar ve
        // Worker 502 doner (502 != 402: odemesiz istek odeme sartlarini goremez).
        ...(govdeVar ? { duplex: "half" } : {}),
        redirect: "manual",
        signal: AbortSignal.timeout(Number(env.X402_TIMEOUT_MS || 90000)),
      });
    } catch (hata) {
      // Worker'in upstream'e ulasamamasi: zaman asimi / DNS / baglanti.
      // Bu katman Worker'in; upstream'in sagligi bu veriden anlasilmaz.
      return katmanHatasi(WORKER_DEGERI, hata, { path: url.pathname });
    }

    const govdeMetni = await yanit.text();
    const isaret = guvenlikIsareti(yanit.status, yanit.headers, govdeMetni);

    if (isaret) {
      // Su an en onemli dal: upstream Vercel guvenlik katmaninda kesildi.
      // Bu sayfayi GECMIYORUZ. Gecseydik 200 + HTML donen sahte uc olurdu;
      // ajan odemeyi kabul eder, cevap gelmez.
      // Suclu: Worker degil, upstream Vercel. Worker'in isareti (x-fieldcast-layer)
      // eklenerek probun "worker" dememesi saglanir.
      return json(
        {
          error: "upstream_security_checkpoint",
          layer: "vercel",
          culprit: "vercel",
          detail:
            "Upstream Vercel guvenlik katmani istegi kesmis (bot sinyali). " +
            "Bu bir Worker hatasi degil; sayfa gecirilmedi.",
          marker: isaret.ad,
          path: url.pathname,
        },
        502,
        { "x-fieldcast-upstream": "vercel" },
      );
    }

    // 402 SARTLARI OLDUGU GIBI GECER: status + PAYMENT-REQUIRED aynen korunur.
    // Odeme dogrulamasi sunucuda olur; Worker sadece tasir.
    const cikti = temizleBasliklar(yanit.headers);
    if (yanit.status === 402) {
      cikti.set("cache-control", "no-store");
      cikti.set("x-fieldcast-route", "x402-payment-required");
      return new Response(govdeMetni, { status: yanit.status, headers: cikti });
    }

    // Hata kodlarinda suclu katman cevapta ve logda gorunur. 403 ve 5xx
    // gecirilir (yoksa ajan hatayi gormez) ama x-fieldcast-error ile
    // "bunu Worker mi yapti, uygulama mi, Vercel mi" ayrimi acilir.
    if (yanit.status === 403 || yanit.status >= 500) {
      const suclu = hataKatmani(yanit.status, yanit.headers);
      cikti.set(HATA_BASLIK, suclu);
      console.error(
        `[x402-proxy] katman=${suclu} upstream_http=${yanit.status} yol=${url.pathname}`,
      );
    }
    return new Response(govdeMetni, { status: yanit.status, headers: cikti });
  },
};