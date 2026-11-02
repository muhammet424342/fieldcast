// Fieldcast Gate: x402 v2 paywall in front of the Fieldcast extraction API.
// Unpaid POST gets HTTP 402 listing every network it accepts; a paid call is proxied upstream and
// settled in USDC on the network the buyer chose (Base mainnet by default, Arbitrum One when enabled).
import express from "express";
import { paymentMiddleware, x402ResourceServer } from "@x402/express";
import { HTTPFacilitatorClient } from "@x402/core/server";
import { ExactEvmScheme } from "@x402/evm/exact/server";

// eip155:8453 Base mainnet, eip155:42161 Arbitrum One. Both are supported by the PayAI facilitator.
const NETWORKS = (process.env.GATE_NETWORKS || "eip155:8453").split(",").map((n) => n.trim()).filter(Boolean);
const PORT = Number(process.env.GATE_PORT || 4403);
const PAY_TO = process.env.PAY_TO;
const UPSTREAM = process.env.UPSTREAM || "http://127.0.0.1:8010";
const UPSTREAM_KEY = process.env.DOCPARSE_GATEWAY_KEY;
const FACILITATOR_URL = process.env.FACILITATOR_URL || "https://facilitator.payai.network";
const PRICE = process.env.PRICE || "$0.01";

for (const [name, value] of Object.entries({ PAY_TO, DOCPARSE_GATEWAY_KEY: UPSTREAM_KEY })) {
  if (!value) {
    console.error(`missing env ${name}`);
    process.exit(1);
  }
}

const app = express();
app.set("trust proxy", true); // nginx terminates TLS; keep https in the advertised resource URL
app.use(express.json({ limit: "2mb" }));
// PDF uploads: keep multipart and raw PDF bodies as bytes so they can be forwarded after payment.
app.use(express.raw({ type: ["multipart/form-data", "application/pdf"], limit: "2mb" }));
const RESOURCE = process.env.GATE_RESOURCE || undefined;

app.get("/base/health", (_req, res) => res.json({ ok: true, networks: NETWORKS, price: PRICE }));

app.use(
  paymentMiddleware(
    {
      "POST /base/v1/extract": {
        resource: RESOURCE,
        accepts: NETWORKS.map((network) => ({ scheme: "exact", price: PRICE, network, payTo: PAY_TO })),
        description: "Fieldcast: send document text (JSON), a PDF (multipart file + fields, or application/pdf with ?fields=a,b), get those fields back as typed JSON.",
        mimeType: "application/json",
      },
    },
    NETWORKS.reduce(
      (server, network) => server.register(network, new ExactEvmScheme()),
      new x402ResourceServer(new HTTPFacilitatorClient({ url: FACILITATOR_URL })),
    ),
  ),
);

// Builds the upstream request: JSON {text, fields}, multipart passthrough, or raw PDF wrapped as multipart.
export function upstreamRequest(req) {
  const ct = String(req.headers["content-type"] || "");
  const headers = { "X-API-Key": UPSTREAM_KEY };
  if (Buffer.isBuffer(req.body) && ct.startsWith("multipart/form-data")) {
    return { headers: { ...headers, "Content-Type": ct }, body: req.body };
  }
  if (Buffer.isBuffer(req.body) && ct.startsWith("application/pdf")) {
    const form = new FormData();
    form.append("file", new Blob([req.body], { type: "application/pdf" }), String(req.query.filename || "document.pdf"));
    form.append("fields", String(req.query.fields || ""));
    return { headers, body: form };
  }
  return { headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ text: req.body?.text, fields: req.body?.fields }) };
}

app.post("/base/v1/extract", async (req, res) => {
  try {
    const { headers, body } = upstreamRequest(req);
    const upstream = await fetch(`${UPSTREAM}/v1/extract`, {
      method: "POST",
      headers,
      body,
      signal: AbortSignal.timeout(90_000),
    });
    // Non-2xx here means the middleware does not settle, so a failed extraction is not charged.
    res.status(upstream.status).json(await upstream.json());
  } catch (err) {
    res.status(502).json({ error: "upstream_unreachable", detail: String(err).slice(0, 200) });
  }
});

if (process.env.GATE_NO_LISTEN !== "1") app.listen(PORT, "127.0.0.1", () =>
  console.log(`fieldcast gate on 127.0.0.1:${PORT} networks=${NETWORKS.join(",")} payTo=${PAY_TO} facilitator=${FACILITATOR_URL}`),
);
