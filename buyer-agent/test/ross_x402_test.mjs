// Synthetic x402 second-challenge test for Ross / 402Signal.
// Real wrapFetchWithPayment + real makeGuardedFetch + counting signer + fake fetch.
// No wallet client, no network calls, no real documents. PAY_NETWORK=base.
import { makeGuardedFetch } from "../buyer.mjs";
const { x402Client, wrapFetchWithPayment } = await import("@x402/fetch");
const { ExactEvmScheme } = await import("@x402/evm/exact/client");

const NET = "eip155:8453";
const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const APPROVED_PAYTO = "0x1111111111111111111111111111111111111111";
// approved terms from the free probe (Ross's fixture)
const approved = { amount: 10000n, payTo: APPROVED_PAYTO, asset: USDC };

function b64(o) { return Buffer.from(JSON.stringify(o)).toString("base64"); }
function accept(o = {}) {
  return { scheme: "exact", network: NET, amount: "10000", asset: USDC, payTo: APPROVED_PAYTO,
           maxTimeoutSeconds: 300, extra: { name: "USD Coin", version: "2" }, ...o };
}
function fakeFetch(acc) {
  let n = 0;
  return async () => {
    n++;
    if (n === 1) {
      return new Response("{}", { status: 402, headers: {
        "PAYMENT-REQUIRED": b64({ x402Version: 2, error: "Payment required", accepts: [acc] }),
        "content-type": "application/json" } });
    }
    return new Response(JSON.stringify({ data: { invoice_number: "DEMO-1", total: 10 } }), { status: 200, headers: {
      "PAYMENT-RESPONSE": b64({ success: true, transaction: "0xtest", network: NET, payer: APPROVED_PAYTO }),
      "content-type": "application/json" } });
  };
}

let signerCalls = 0;
const account = { address: APPROVED_PAYTO, type: "local",
  async signTypedData() { signerCalls++; return "0x" + "ab".repeat(65); } };
const x402 = new x402Client();
x402.register(NET, new ExactEvmScheme(account));

const cases = [
  { name: "same_terms",        acc: accept() },
  { name: "amount_changed",    acc: accept({ amount: "20000" }) },
  { name: "recipient_changed", acc: accept({ payTo: "0x2222222222222222222222222222222222222222" }) },
  { name: "asset_changed",     acc: accept({ asset: "0xdeaddeaddeaddeaddeaddeaddeaddeaddeaddead" }) },
  { name: "missing_terms",     acc: accept({ network: "eip155:1" }) }, // no accept for our network -> unreadable
];

const body = JSON.stringify({ text: "Invoice DEMO-1. Total USD 10.00", fields: ["invoice_number", "total"] });
const results = [];
for (const c of cases) {
  signerCalls = 0;
  let refusal = null;
  try {
    const guarded = makeGuardedFetch(approved, fakeFetch(c.acc));
    const fetchPaid = wrapFetchWithPayment(guarded, x402);
    await fetchPaid("https://seller.test/base/v1/extract", {
      method: "POST", headers: { "content-type": "application/json" }, body });
  } catch (e) { refusal = e.code || (e.message || "").slice(0, 48); }
  results.push({ case: c.name, signer_calls: signerCalls, refusal_code: refusal });
}
console.log(JSON.stringify(results, null, 2));
