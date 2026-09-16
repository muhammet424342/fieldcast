// Fieldcast buyer <-> 402Signal route-guard 0.7.6.
// authorize() delegates to the published withVerifiedRoute; its RouteGuardError propagates unchanged.
// vendor/route-guard-0.7.6 must be the reviewed checkout of 402signalhq/402signal tag route-guard-v0.7.6
// (commit 5ea0df9), linked to that checkout's sdk/route-guard so RouteGuardError is the same class the
// buyer-checks runner imports:  ln -s <402signal>/sdk/route-guard vendor/route-guard-0.7.6
import { withVerifiedRoute } from "../vendor/route-guard-0.7.6/index.mjs";

// Buyer-side per-call cap in atomic USDC. The daily budget stays in buyer.mjs / AgentBudgetVault.
const PER_CALL_CAP = 20000n;

export class BuyerCapError extends Error {
  constructor(code) { super(code); this.name = "BuyerCapError"; this.code = code; }
}

export async function authorize(options, fakeCallback) {
  return withVerifiedRoute(options, (action) => {
    if (BigInt(action.accepted.amount) > PER_CALL_CAP) throw new BuyerCapError("over_per_call_cap");
    return fakeCallback(action);
  });
}

// POST wiring for Fieldcast (not exercised by the Base fixture runner).
// bodyFor: the exact bytes sent to Fieldcast, never parsed and reserialized.
export function bodyFor(rawBody) {
  if (typeof rawBody === "string") return new TextEncoder().encode(rawBody);
  if (rawBody instanceof Uint8Array) return rawBody;
  throw new TypeError("body must be the raw string or bytes");
}

// challengeFor: the raw 402 already received for that same POST, header values untouched.
export function challengeFor(res, bodyText) {
  return {
    status: res.status,
    bodyText,
    paymentRequired: res.headers.get("payment-required") ?? undefined,
    xPaymentRequired: res.headers.get("x-payment-required") ?? undefined,
  };
}

// requestFor: the 402Signal /route request. Constraints are top-level.
export function requestFor(url) {
  return { url, require_route_binding: true, networks: ["eip155:8453"], max_amount_atomic: PER_CALL_CAP.toString() };
}
