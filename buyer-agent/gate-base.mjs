// Fieldcast Gate on Base: x402 v2 paywall in front of the Fieldcast extraction API.
// Unpaid POST gets HTTP 402; a paid call is proxied upstream and settled in USDC on Base mainnet.
import express from "express";
import { paymentMiddleware, x402ResourceServer } from "@x402/express";
import { HTTPFacilitatorClient } from "@x402/core/server";
import { ExactEvmScheme } from "@x402/evm/exact/server";

const NETWORK = "eip155:8453"; // Base mainnet
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

app.get("/base/health", (_req, res) => res.json({ ok: true, network: NETWORK, price: PRICE }));

app.use(
  paymentMiddleware(
    {
      "POST /base/v1/extract": {
        accepts: [{ scheme: "exact", price: PRICE, network: NETWORK, payTo: PAY_TO }],
        description: "Fieldcast: send document text and a list of field names, get those fields back as typed JSON.",
        mimeType: "application/json",
      },
    },
    new x402ResourceServer(new HTTPFacilitatorClient({ url: FACILITATOR_URL })).register(
      NETWORK,
      new ExactEvmScheme(),
    ),
  ),
);

// ponytail: JSON body only (text + fields); add multipart passthrough when a buyer needs PDF upload.
app.post("/base/v1/extract", async (req, res) => {
  try {
    const upstream = await fetch(`${UPSTREAM}/v1/extract`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": UPSTREAM_KEY },
      body: JSON.stringify({ text: req.body?.text, fields: req.body?.fields }),
      signal: AbortSignal.timeout(90_000),
    });
    // Non-2xx here means the middleware does not settle, so a failed extraction is not charged.
    res.status(upstream.status).json(await upstream.json());
  } catch (err) {
    res.status(502).json({ error: "upstream_unreachable", detail: String(err).slice(0, 200) });
  }
});

app.listen(PORT, "127.0.0.1", () =>
  console.log(`fieldcast gate (base) on 127.0.0.1:${PORT} payTo=${PAY_TO} facilitator=${FACILITATOR_URL}`),
);
