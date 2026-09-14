# Fieldcast Buyer Agent

An agent that decides whether a document is worth paying to process, and pays for it itself
from a Dynamic server wallet, over x402, in USDC on Base.

Built for RUNTIME Agent Week (Bankr, September 2026). Tracks: Bankr grand prize, Dynamic
"Best Agentic Wallet or Payment Experience".

## What it does

Give the agent a document and the fields you need (invoice number, date, total, VAT ID…).

1. **Free pass first.** A regex pass pulls whatever is plainly labelled. If every field is
   found, the agent stops. No money moves.
2. **Price check without paying.** It calls the paid endpoint once, reads the HTTP 402
   payment requirement (network, asset, amount, payee) and checks it against two hard limits
   the model cannot override: a per-call price cap (0.02 USDC) and a daily budget (0.10 USDC).
3. **Evidence, not opinion.** For each still-missing field, a model reports whether the value
   is written in the document and copies it verbatim. The code then checks that each quote
   really occurs in the text. The agent pays only if at least one missing field is verified.
   A model that hallucinates a field, or talks itself into paying, cannot spend money.
4. **Pay and collect.** The Dynamic server wallet signs an EIP-3009 transfer authorization;
   `@x402/fetch` retries the request with the payment; the facilitator settles on Base; the
   extraction comes back. Every decision, reason, price and transaction goes to a ledger.
5. **Fail closed.** If no model answers, the agent does not pay.

## Proof

First paid call, 14 September 2026:
[`0xb80edfd840b9904dff321c9c26150038cd19fa5847290b4d97bb0cd6a4a388bd`](https://basescan.org/tx/0xb80edfd840b9904dff321c9c26150038cd19fa5847290b4d97bb0cd6a4a388bd)
— 0.01 USDC from the agent wallet `0x126c57A501226D0f6dfc63E093A9aa928425333d` to the seller
`0x3f425d6ffd2855585483d65da684651e330759e0`, gas paid by the facilitator, extraction 4/4 correct.

Honest note: both wallets are ours. The agent wallet was funded by the builder for this demo;
this shows a working agent-to-API payment, not outside customers.

## Demo documents

| Document | Fields asked | What the agent does |
|---|---|---|
| `demo/clean_invoice.txt` | invoice_number, date, total | finds all three for free, does not pay |
| `demo/shipping_notice.txt` | + vendor_tax_id | model finds none of them in the text, does not pay |
| `demo/messy_receipt.txt` | + vendor_tax_id | "receipt ref", written-out date, "amount payable", "USt-IdNr": all four verified, pays 0.01 USDC |

## Pieces

- `buyer.mjs` — the agent. `selftest`, `setup` (create the Dynamic server wallet), `balance`, `run <file> --fields a,b`.
- `gate-base.mjs` — the seller: an x402 v2 paywall (`@x402/express`) in front of the Fieldcast extraction API,
  USDC on Base (`eip155:8453`), PayAI facilitator. Live at `https://157-173-122-86.sslip.io/base/v1/extract`.
- `fieldcast-gate-base.service` — systemd unit for the gate.

## Decision engines

Measured 14 September 2026 on the demo documents:

| Engine | Result | Latency |
|---|---|---|
| `nvidia/nemotron-3-super-120b-a12b`, thinking off | 5/6 correct, 1 no-answer (did not pay) | 1.2–2.3 s |
| `nvidia/nemotron-3.5-lightning-30b-a3b`, thinking off | 6/6 | 1.5–6.9 s |
| `deepseek-chat` | 6/6 | 1.5–2.5 s |

Tried in that order. With thinking on, the NVIDIA reasoning models spent their whole token
budget thinking and never printed JSON. Force one engine with `DECISION_ENGINES=<name>`.

## Run it

```bash
npm install
cp .env.example .env          # fill in the values
set -a && . ./.env && set +a
node buyer.mjs selftest
node buyer.mjs setup          # prints the agent wallet address; send it a little USDC on Base
node buyer.mjs run demo/messy_receipt.txt --fields invoice_number,date,total,vendor_tax_id
```

Dynamic setup: create an environment, enable *Embedded Wallets* and *Allow multiple embedded
wallets per chain*, create an API token. The wallet needs no ETH: the payment is a signed
authorization and the facilitator pays gas.

## Two things the Dynamic docs did not tell us

- `createWalletAccount({ backUpToDynamic: true })` failed five times with HTTP 500 from the
  key-share backup relay, which aborts wallet creation. The SDK default (`false`) works; you
  then store the key share yourself. Here it is a mode-600 file, fine for a demo balance,
  not for real funds.
- In `@dynamic-labs-wallet/node-evm` 1.1.10, `getWalletClient` takes `walletMetadata`. The docs
  example passes `accountAddress`, which throws `Cannot read properties of undefined (reading 'accountAddress')`.

## License

MIT
