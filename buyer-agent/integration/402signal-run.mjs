// Synthetic runner: exercises the adapter's boundary with a counting signer (fake callback).
// No wallet, no network, no real documents. node integration/402signal-run.mjs
import { authorize } from "./402signal-adapter.mjs";

const NET = "eip155:8453";
const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const PAYTO = "0x1111111111111111111111111111111111111111";
const approved = { amount: 10000n, payTo: PAYTO, asset: USDC, network: NET };
const requestBody = '{"text":"Invoice DEMO-1. Total USD 10.00","fields":["invoice_number","total"]}';

const b64 = (o) => Buffer.from(JSON.stringify(o)).toString("base64");
const accept = (o = {}) => ({ scheme: "exact", network: NET, amount: "10000", asset: USDC, payTo: PAYTO,
  maxTimeoutSeconds: 300, extra: { name: "USD Coin", version: "2" }, ...o });
const challenge = (acc) => ({ status: 402, bodyText: "{}",
  paymentHeaders: { "PAYMENT-REQUIRED": b64({ x402Version: 2, error: "Payment required", accepts: acc ? [acc] : [] }) } });

const cases = [
  ["same_terms",        challenge(accept())],
  ["amount_changed",    challenge(accept({ amount: "20000" }))],
  ["recipient_changed", challenge(accept({ payTo: "0x2222222222222222222222222222222222222222" }))],
  ["asset_changed",     challenge(accept({ asset: "0xdeaddeaddeaddeaddeaddeaddeaddeaddeaddead" }))],
  ["missing_terms",     challenge(accept({ network: "eip155:1" }))],
];

const out = [];
for (const [name, paidChallenge] of cases) {
  let signer_calls = 0;
  let refusal_code = null;
  try {
    await authorize({ approved, url: "https://seller.test/base/v1/extract", requestBody, paidChallenge },
      () => { signer_calls++; return { signature: "0x" + "ab".repeat(65) }; });
  } catch (e) { refusal_code = e.code || e.message; }
  out.push({ case: name, signer_calls, refusal_code });
}
console.log(JSON.stringify(out, null, 2));
