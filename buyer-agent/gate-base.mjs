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
// JSON (text + fields) and multipart PDF share one ceiling. Multipart is kept raw so the
// boundary reaches upstream unchanged.
const BODY_LIMIT = "5mb";
const jsonParser = express.json({ limit: BODY_LIMIT });
const multipartParser = express.raw({ type: () => true, limit: BODY_LIMIT });

app.use((req, res, next) => {
  const type = String(req.headers["content-type"] || "");
  if (type.toLowerCase().includes("multipart/form-data")) return multipartParser(req, res, next);
  return jsonParser(req, res, next);
});

app.get("/base/health", (_req, res) => res.json({ ok: true, networks: NETWORKS, price: PRICE }));

app.use(
  paymentMiddleware(
    {
      "POST /base/v1/extract": {
        accepts: NETWORKS.map((network) => ({ scheme: "exact", price: PRICE, network, payTo: PAY_TO })),
        description: "Fieldcast: send document text (JSON) or a PDF (multipart file + fields), get those fields back as typed JSON.",
        mimeType: "application/json",
      },
    },
    NETWORKS.reduce(
      (server, network) => server.register(network, new ExactEvmScheme()),
      new x402ResourceServer(new HTTPFacilitatorClient({ url: FACILITATOR_URL })),
    ),
  ),
);

app.post("/base/v1/extract", async (req, res) => {
  const type = String(req.headers["content-type"] || "");
  const multipart = type.toLowerCase().includes("multipart/form-data");
  try {
    const headers = { "X-API-Key": UPSTREAM_KEY };
    let body;
    if (multipart) {
      headers["Content-Type"] = type;
      body = Buffer.isBuffer(req.body) ? req.body : Buffer.alloc(0);
    } else {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify({ text: req.body?.text, fields: req.body?.fields });
    }
    const upstream = await fetch(`${UPSTREAM}/v1/extract`, {
      method: "POST",
      headers,
      body,
      signal: AbortSignal.timeout(90_000),
    });
    const raw = Buffer.from(await upstream.arrayBuffer());
    // Non-2xx here means the middleware does not settle, so a failed extraction is not charged.
    res.status(upstream.status);
    res.setHeader("Content-Type", upstream.headers.get("content-type") || "application/json");
    res.end(raw);
  } catch (err) {
    res.status(502).json({ error: "upstream_unreachable", detail: String(err).slice(0, 200) });
  }
});

app.use((err, req, res, next) => {
  if (err && (err.status === 413 || err.statusCode === 413 || err.type === "entity.too.large")) {
    res.status(413).json({ error: "payload_too_large" });
    return;
  }
  next(err);
});

app.listen(PORT, "127.0.0.1", () =>
  console.log(`fieldcast gate on 127.0.0.1:${PORT} networks=${NETWORKS.join(",")} payTo=${PAY_TO} facilitator=${FACILITATOR_URL}`),
);
