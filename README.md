# Fieldcast

**Documents in, structured JSON out. One API call.**

Live: **https://fieldcast-peach.vercel.app**

## Hackathon submission

- **Buyer agent code:** [`buyer-agent/`](buyer-agent/) — the agent that decides whether a
  document is worth paying for and pays for it itself over x402. Its own README:
  [`buyer-agent/README.md`](buyer-agent/README.md).
- **Demo video:** https://youtu.be/WZyBKLm_svs

You send a PDF or raw text plus a list of field names. Fieldcast returns those fields
as typed JSON — numbers as numbers, dates normalised to ISO-8601. A field that is not
in the document comes back `null` rather than a fabricated value.

No templates to configure. No model to pick. No training data.

```bash
curl -X POST https://fieldcast-peach.vercel.app/v1/extract \
  -H "X-API-Key: demo_key_public" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "INVOICE INV-2043  Date: 14 August 2026  Total: 1,240.50 EUR",
    "fields": ["invoice_number", "date", "total", "currency"]
  }'
```

```json
{
  "data": {
    "invoice_number": "INV-2043",
    "date": "2026-08-14",
    "total": 1240.5,
    "currency": "EUR"
  }
}
```

PDFs work the same way — post the file as multipart with `fields=a,b,c`.

## Why `null` matters

A parser that invents a total looks like it worked. You find out during reconciliation
three months later. Fieldcast is instructed never to fill a field it cannot find, so a
missing value lands in a review queue the same day instead of quietly entering your books.

Measured on a live request: asked for ten fields on a real invoice, ten correct in 1.8s.
Asked for four fields that did not exist in the document, all four returned `null`.

## Endpoints

| Endpoint | Auth | Notes |
|---|---|---|
| `POST /v1/extract` | `X-API-Key` header | JSON `{text, fields[]}` or multipart `file` + `fields=a,b,c` |
| `GET /health` | none | liveness |
| `POST /x402/extract` | none — pay per call | x402: HTTP 402 with payment terms, settle in USDC, get the result |
| `GET /x402/health` | none | reports network and whether payments are configured |

Up to 40 fields per call. Documents are held in memory for the duration of the request
and are not persisted; only a usage counter is stored.

## Extraction engine

NVIDIA-hosted models first (free), DeepSeek as a paid last resort. Measured on the same
ten-field invoice:

| Model | Score | Time |
|---|---|---|
| `minimaxai/minimax-m3` (retired Sept 2026) | 10/10 | 1.5s |
| `moonshotai/kimi-k3` | 10/10 | 2.7s |
| `mistralai/mistral-nemotron` | 10/10 | 3.7s |
| `meta/llama-3.1-70b-instruct` | 10/10 | 4.2s |
| `meta/llama-3.1-8b-instruct` | 8/10 | 1.2s — misses date normalisation, excluded |

`minimaxai/minimax-m3` is retired: NVIDIA dropped it in September 2026. Its row is kept with
the score and time recorded while it was served. At runtime it is still tried first, fails, and
the next model takes over. The scores and times above are from that recorded run — they are not
re-measured here.

If a model fails the next one is tried. If every provider fails the request returns 502
with which provider failed and why — it does not silently degrade.

## x402 (pay-per-call for agents)

`api/pay.py` serves the same extraction behind an x402 paywall: an agent calls it,
receives HTTP 402 with machine-readable payment terms in the `PAYMENT-REQUIRED` header,
settles in USDC, and receives the extraction in the same flow. The route declares itself
to the x402 Bazaar for discovery.

**Status:** the public `x402.org` facilitator only advertises testnets
(`eip155:84532` yes, `eip155:8453` no). Base mainnet (`eip155:8453`) builds its
facilitator from `CDP_API_KEY_ID` and `CDP_API_KEY_SECRET`. If either is missing,
`POST /x402/extract` returns HTTP 503 with the detail `ana ag icin CDP anahtari gerekli`.
The network is not switched to Base Sepolia. An empty `X402_PAY_TO` also returns 503
and does not serve free extractions. CDP keys are not written into the source.

## Running locally

```bash
pip install -r requirements.txt
NVIDIA_API_KEY=... python api/index.py        # http://127.0.0.1:8010
NVIDIA_API_KEY=... X402_PAY_TO=0x... python api/pay.py
```

## Deploying

```bash
npx vercel --prod
```

Environment variables:

| Variable | Required | Purpose |
|---|---|---|
| `NVIDIA_API_KEY` | yes | primary extraction provider |
| `DEEPSEEK_API_KEY` | no | fallback provider |
| `X402_PAY_TO` | no | wallet that receives x402 payments; empty string disables the endpoint |
| `X402_NETWORK` | no | code default in `api/pay.py` is `eip155:8453` (Base). `eip155:84532` is Base Sepolia |

No key is ever committed — everything comes from the environment, including
`CDP_API_KEY_ID` and `CDP_API_KEY_SECRET`.

### Mainnet environment (`eip155:8453`)

The mainnet path and the testnet path are separate. Mainnet does not fall back to
`eip155:84532` when the CDP key is missing. Testnet uses `X402_FACILITATOR_URL`
(code default `https://facilitator.payai.network`) and does not read the CDP key.
Mainnet facilitator URL is `https://api.cdp.coinbase.com/platform/v2/x402`, built
from the two CDP variables. Changing these on Vercel is a separate step; this
table is the code contract.

| Variable | Required on mainnet | Role |
|---|---|---|
| `X402_NETWORK` | yes, `eip155:8453` | selects the mainnet path. `eip155:84532` stays on the testnet path |
| `CDP_API_KEY_ID` | yes | CDP API key id. The facilitator config is built from this |
| `CDP_API_KEY_SECRET` | yes | CDP API key secret paired with the id |
| `X402_PAY_TO` | yes | wallet that receives USDC. Empty string returns 503 |
| `X402_PRICE` | no | call price. Code default `$0.01` |
| `X402_FACILITATOR_URL` | no | testnet facilitator only. Ignored on the mainnet path |
| `X402_BAZAAR` | no | `1` installs the discovery extension. `0`, `false`, or `no` turns it off |

## Layout

```
api/index.py              extraction API
api/pay.py                x402 endpoint (same engine, pay-per-call)
public/                   site: landing, use cases, comparisons, legal
public/style.css          single shared stylesheet
alternatif_sayfa_uret.py  generates the /alternatives/ comparison pages
senaryo_sayfa_uret.py     generates the /for/ use-case pages
ekran_goruntusu_al.py     captures product screenshots from the live site
```

The comparison and use-case pages are generated rather than hand-written so competitor
figures and product claims live in one place instead of drifting across three files.

## Known limits

- No OCR — PDF and plain text only, scanned images are not supported.
- The usage counter lives in `/tmp` on Vercel and resets on cold start.
- Extraction runs on third-party model providers, so documents leave the service.
- Beta, run by one developer. No SLA.

## Licence

MIT
