// Fieldcast buyer <-> 402Signal route-guard adapter (0.7.6 shape), fully offline/synthetic.
// Contract mirrors integration/buyer-checks: export authorize(options, fakeCallback).
// The fake callback (the signer stand-in) is called at most once, only AFTER verification.
// On refusal we throw a RouteGuardError-style error with a stable code, never calling back.
//
// POST binding per Ross's 0.7.6 note:
//   - bodyFor    : the EXACT request bytes sent to Fieldcast, unchanged (no parse/reserialize)
//   - challengeFor: the raw 402 status, body text and payment headers already received for that POST
//   - requestFor : the 402Signal check request { resource_url, require_route_binding:true, limits }
import { termsChanged } from "../buyer.mjs";

export class RouteGuardError extends Error {
  constructor(code) { super(code); this.name = "RouteGuardError"; this.code = code; }
}

// Buyer's hard caps (same as AgentBudgetVault / buyer guard), in atomic USDC.
const LIMITS = { asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", network: "eip155:8453",
                 per_call_atomic: "20000", daily_atomic: "100000" };

// Exact bytes, unchanged. Accepts a string or Uint8Array and returns it as-is.
export function bodyFor(options) {
  const b = options.requestBody;
  if (typeof b !== "string" && !(b instanceof Uint8Array)) {
    throw new RouteGuardError("body_not_raw"); // never parse/reserialize the POST body
  }
  return b;
}

// The raw 402 exactly as received for THIS POST (no re-derivation).
export function challengeFor(options) {
  const c = options.paidChallenge || {};
  return { status: c.status, body_text: c.bodyText, payment_headers: c.paymentHeaders || {} };
}

export function requestFor(options) {
  return { resource_url: options.url, require_route_binding: true, limits: LIMITS };
}

// Parse the offered terms from the raw challenge's PAYMENT-REQUIRED header (base64 JSON).
function offeredTerms(paymentHeaders, network) {
  const h = paymentHeaders && (paymentHeaders["PAYMENT-REQUIRED"] || paymentHeaders["payment-required"]);
  if (!h) return null;
  let parsed;
  try { parsed = JSON.parse(Buffer.from(h, "base64").toString("utf8")); } catch { return null; }
  const a = (parsed?.accepts || []).find((x) => x.network === network);
  if (!a) return null;
  return { amount: BigInt(a.amount ?? a.maxAmountRequired), payTo: a.payTo, asset: a.asset };
}

// The trusted verification boundary. options.approved is the offer approved on the free probe.
export async function authorize(options, fakeCallback) {
  const approved = options.approved;                       // { amount(BigInt), payTo, asset }
  const req = requestFor(options);                          // require_route_binding + limits (for the record)
  const _body = bodyFor(options);                           // exact bytes preserved (throws if not raw)
  const ch = challengeFor(options);                         // raw 402 as received

  const offered = offeredTerms(ch.payment_headers, approved.network);
  if (!offered) throw new RouteGuardError("terms_missing");            // null side -> explicit refusal
  if (termsChanged(approved, offered)) throw new RouteGuardError("terms_changed");
  if (offered.amount > BigInt(req.limits.per_call_atomic)) throw new RouteGuardError("over_per_call_cap");

  // Verified: identical to the approved offer and within caps. Sign exactly once.
  return fakeCallback({ offered, request: req });
}
