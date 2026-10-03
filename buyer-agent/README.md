# Fieldcast Buyer Agent

An agent that decides whether a document is worth paying to process, and pays for it itself
from a Dynamic server wallet, over x402, in USDC. The same buyer runs on **Base** (RUNTIME Agent
Week) and on **Arbitrum Sepolia** behind `AgentBudgetVault` (Arbitrum Open House Singapore,
Promising Products).

Built for RUNTIME Agent Week (Bankr, September 2026) and the Arbitrum Open House Singapore
Buildathon. Tracks: Bankr grand prize, Dynamic "Best Agentic Wallet or Payment Experience",
Arbitrum Promising Products.

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

- `buyer.mjs` — the agent. `selftest`, `setup` (create the Dynamic server wallet), `balance`, `fund` (sweep USDC into the vault), `run <file> --fields a,b`.
- `gate-base.mjs` — the seller: an x402 v2 paywall (`@x402/express`) in front of the Fieldcast extraction API.
  Networks: Base (`eip155:8453`), Arbitrum One (`eip155:42161`), Arbitrum Sepolia (`eip155:421614`).
  PayAI facilitator. Live at `https://157-173-122-86.sslip.io/base/v1/extract`.
- `contracts/src/AgentBudgetVault.sol` — Ownable2Step vault: `perCallCap` 0.02 / `dailyCap` 0.10 / `floatCap` 0.03 USDC, allowlisted payee, `evidenceHash` on `Released`. Foundry tests 20/20, coverage 100% of lines/branches.
- `fieldcast-gate-base.service` — systemd unit for the gate.

## Arbitrum Sepolia (Open House Singapore)

The agent cannot hold a working balance. `floatCap` forces USDC into the vault; each paid call does
`vault.release` then the x402 payment. Caps are on-chain, the model cannot override them.

- Vault: [`0x2c48d7f3bd378d64b0ebe7f85d3ae94fcf3d004c`](https://arbitrum-sepolia.blockscout.com/address/0x2c48d7f3bd378d64b0ebe7f85d3ae94fcf3d004c) (deploy tx [`0x523a66d1…187d`](https://arbitrum-sepolia.blockscout.com/tx/0x523a66d1011b24e9393d56a4ff6b08bfa50c8ccbf075c7884f554d48d017187d))
- Demo skip (shipping notice, no fields in the text) then pay (messy receipt, 4/4 verified):
  vault release [`0x940965bf…0d86d`](https://arbitrum-sepolia.blockscout.com/tx/0x940965bf323e56f938d96663d24043ca5988548feb3841234e10a6a954a0d86d)
  · x402 payment [`0x2c98152a…af3ad`](https://arbitrum-sepolia.blockscout.com/tx/0x2c98152a0ee5e826de3ec383171fb91ebd09d957685358be3b0bf80bfbaaf3ad)
- Run: `PAY_NETWORK=arbitrum-sepolia VAULT_ADDRESS=0x2c48d7f3bd378d64b0ebe7f85d3ae94fcf3d004c node buyer.mjs run demo/messy_receipt.txt --fields invoice_number,date,total,vendor_tax_id`
- This is **testnet**. Both wallets are ours. It shows a working vault-gated agent payment, not outside customers.

## Architecture

```
document ──> buyer.mjs ──(1) regex, free──> done if every field found
                 │
                 ├─(2) POST gate, no payment ──> HTTP 402 {network, asset, amount, payTo}
                 ├─(3) hard guards: price cap, daily budget
                 ├─(4) model: {present, quote} per missing field ──> code verifies quote is in the text
                 └─(5) Dynamic server wallet signs EIP-3009 ──> @x402/fetch retries
                                                                  │
nginx (TLS, rate limit) ──> gate-base.mjs (@x402/express, PayAI facilitator settles on Base)
                                   └──> Fieldcast extraction API (firewalled, not reachable from outside) ──> JSON
```

## Security limits

What this is and is not, stated plainly:

- **Documents go to a model provider.** The seller sends the document text to its extraction model
  (DeepSeek) and the buyer sends it to its decision model (NVIDIA, DeepSeek fallback). Do not send
  documents you are not allowed to share with those providers.
- **No raw documents in server logs.** The extraction API stores per call only: the API key used (the gate's own key or the public demo key), timestamp,
  number of fields, number of characters, success flag. nginx keeps its default access log (IP, time, request line,
  status, user agent), no request bodies. The buyer's local `state/ledger.jsonl` does keep the extracted values;
  it is the buyer's own file.
- **Limits:** 30 requests/minute per IP (burst 20) and 2 MB body at nginx; document text is cut at
  20,000 characters before extraction; a failed extraction returns HTTP 4xx/5xx, and `@x402/express` cancels settlement for those responses, so it is not charged.
- **Wallet:** the key share lives in a mode-600 file on one server with no backup (see below). Keep
  only a demo balance in it.

## Usage so far

Counted from on-chain stablecoin transfers to the seller (USDC on Base, USDT on the earlier Celo gate), not from our own logs, and kept in three
separate buckets that are never added together:

| Bucket | Meaning | Paid calls | Wallets |
|---|---|---|---|
| `internal_test` | our own wallets | 3 | 2 |
| `subsidized_external` | outside person, we funded their wallet | 0 | 0 |
| `externally_paid` | outside person, their own money | 0 | 0 |

As of 14 September 2026. There are no outside users yet.

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
