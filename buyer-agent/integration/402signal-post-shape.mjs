// Offline check of the POST callbacks against a sanitized capture of Fieldcast's real unpaid 402.
// No wallet, no network, no paid call. node integration/402signal-post-shape.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { bodyFor, challengeFor, requestFor } from "./402signal-adapter.mjs";

const cap = JSON.parse(readFileSync(new URL("./fieldcast-402-capture.json", import.meta.url), "utf8"));
const headers = new Headers({ "payment-required": cap.challenge.paymentRequired });

const body = bodyFor(cap.request.body);
assert.equal(new TextDecoder().decode(body), cap.request.body);          // exact bytes, no reserialization
const ch = challengeFor({ status: 402, headers }, cap.challenge.bodyText);
assert.equal(ch.paymentRequired, cap.challenge.paymentRequired);          // raw header value untouched
assert.equal(ch.xPaymentRequired, undefined);
assert.deepEqual(Object.keys(requestFor(cap.request.url)), ["url", "require_route_binding", "networks", "max_amount_atomic"]);
console.log("post-shape ok");
