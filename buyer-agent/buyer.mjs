// Fieldcast buyer agent: decides whether a document is worth a paid extraction,
// and if so pays the x402 gate on Base from a Dynamic server wallet.
//
//   node buyer.mjs selftest                 offline checks of the decision guards
//   node buyer.mjs setup                    create the Dynamic server wallet once, print its address
//   node buyer.mjs balance                  USDC balance of the agent wallet on Base
//   node buyer.mjs run <file> --fields a,b  read a document, decide, maybe pay, print the result
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createPublicClient, http, erc20Abi, formatUnits } from "viem";
import { base } from "viem/chains";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const STATE = path.join(HERE, "state", "wallet.json"); // walletMetadata + key shares, mode 600, never printed
const LEDGER = path.join(HERE, "state", "ledger.jsonl");
const GATE = process.env.GATE_URL || "https://157-173-122-86.sslip.io/base/v1/extract";
const NETWORK = "eip155:8453";
const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const MAX_PRICE_ATOMIC = BigInt(process.env.MAX_PRICE_ATOMIC || 20000); // 0.02 USDC per call
const DAILY_BUDGET_ATOMIC = BigInt(process.env.DAILY_BUDGET_ATOMIC || 100000); // 0.10 USDC per day
const RPC = process.env.BASE_RPC || "https://mainnet.base.org";

// ---------- free first pass: what can we get without paying ----------
const PATTERNS = {
  invoice_number: /\b(?:invoice|inv|fatura)\s*(?:no|number|#|num)?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-\/]{2,})/i,
  date: /\b(\d{4}-\d{2}-\d{2}|\d{1,2}[./]\d{1,2}[./]\d{2,4})\b/,
  total: /\b(?:total|grand total|amount due|toplam)\s*[:=]?\s*[$€£₺]?\s*([\d.,]+\d)/i,
  currency: /\b(USD|EUR|GBP|TRY)\b|([$€£₺])/,
};

export function localExtract(text, fields) {
  const out = {};
  for (const f of fields) {
    const m = PATTERNS[f]?.exec(text);
    out[f] = m ? (m[1] ?? m[2]) : null;
  }
  return out;
}

// ---------- guards the LLM cannot override ----------
export function spentToday(ledgerLines, now = new Date()) {
  const day = now.toISOString().slice(0, 10);
  return ledgerLines
    .filter((l) => l.paid && l.at.slice(0, 10) === day)
    .reduce((sum, l) => sum + BigInt(l.amount_atomic), 0n);
}

export function guard({ missing, priceAtomic, spent }) {
  if (missing.length === 0) return { pay: false, reason: "all required fields found for free" };
  if (priceAtomic > MAX_PRICE_ATOMIC) return { pay: false, reason: `price ${priceAtomic} above cap ${MAX_PRICE_ATOMIC}` };
  if (spent + priceAtomic > DAILY_BUDGET_ATOMIC) return { pay: false, reason: "daily budget exhausted" };
  return null; // guards pass; the judgment call is left to the model
}

// x402 v2 puts requirements in the PAYMENT-REQUIRED header (base64 JSON); v1 put them in the body.
export function readRequirement(headers, body) {
  const header = headers.get?.("payment-required");
  const parsed = header ? JSON.parse(Buffer.from(header, "base64").toString("utf8")) : body;
  const accept = (parsed?.accepts || []).find((a) => a.network === NETWORK);
  if (!accept) return null;
  return { amount: BigInt(accept.amount ?? accept.maxAmountRequired), payTo: accept.payTo, asset: accept.asset };
}

// ---------- the judgment: is the missing data worth a cent? ----------
// The model does not say "pay". It reports, per missing field, whether the value is written in the
// document and quotes it; the code pays only if a quote really occurs in the text. A model that
// hallucinates a field, or talks itself into paying, cannot spend money that way.
//
// Measured 14 Sep 2026 on the demo documents with a free-form pay/skip prompt:
//   deepseek-chat (direct)                 0.8-1.2 s, correct every time
//   nemotron-3.5-lightning, thinking off   0.7-4.0 s, one wrong "pay" on the subtle case, one timeout
// Evidence-check prompt, 3 docs x 2: super-120b 1.2-2.3 s (5/6, one no-answer), lightning 1.5-6.9 s (6/6), deepseek-chat 6/6.
// With thinking on, NVIDIA reasoning models spent their token budget thinking and never printed
// JSON; deepseek-v4-flash and kimi-k3 hung for 45 s; minimax-m3 was retired (HTTP 410).
const NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions";
const ALL_ENGINES = [
  {
    name: "nvidia/nemotron-3-super-120b-a12b",
    url: NVIDIA_URL,
    keyEnv: "NVIDIA_API_KEY",
    extra: { chat_template_kwargs: { enable_thinking: false } },
    timeoutMs: 15_000,
  },
  {
    name: "nvidia/nemotron-3.5-lightning-30b-a3b",
    url: NVIDIA_URL,
    keyEnv: "NVIDIA_API_KEY",
    extra: { chat_template_kwargs: { enable_thinking: false } },
    timeoutMs: 10_000,
  },
  {
    name: "deepseek-chat",
    url: "https://api.deepseek.com/chat/completions",
    keyEnv: "DEEPSEEK_API_KEY",
    extra: {},
    timeoutMs: 15_000,
  },
];
const ENGINES = process.env.DECISION_ENGINES
  ? process.env.DECISION_ENGINES.split(",").map((n) => ALL_ENGINES.find((e) => e.name === n.trim())).filter(Boolean)
  : ALL_ENGINES;

export function decisionPrompt({ text, missing }) {
  const shape = Object.fromEntries(
    missing.map((f) => [f, { present: "true|false", quote: "value copied exactly from the document, or empty" }]),
  );
  return [
    "You are checking a document before a paid extraction.",
    `For each field below, decide whether its value is actually written in the document: ${missing.join(", ")}.`,
    "Field names are semantic: labels vary (a receipt or reference number, a written-out date, 'amount payable').",
    "Related information is not the field itself: a vendor name is not a tax ID, a delivery window is not an invoice date.",
    "If present, copy the value exactly as it appears in the document into quote. If absent, set present to false and quote to empty.",
    `Answer with JSON only, in this shape: ${JSON.stringify(shape)}`,
    "Document:",
    text.slice(0, 3000),
  ].join("\n");
}

// Take the outermost JSON object even if the model printed something around it.
export function parseJsonObject(content) {
  const start = content.indexOf("{");
  const end = content.lastIndexOf("}");
  if (start < 0 || end <= start) return null;
  try {
    return JSON.parse(content.slice(start, end + 1));
  } catch {
    return null;
  }
}

const squash = (s) => String(s).toLowerCase().replace(/\s+/g, " ").trim();

// A field counts only if the model says it is present AND its quote occurs in the document.
export function verifiedFields(report, missing, text) {
  if (!report || typeof report !== "object") return null;
  const haystack = squash(text);
  const found = [];
  const rejected = [];
  for (const f of missing) {
    const entry = report[f];
    if (!entry || !(entry.present === true || entry.present === "true")) continue;
    const quote = squash(entry.quote || "");
    (quote.length >= 2 && haystack.includes(quote) ? found : rejected).push(f);
  }
  return { found, rejected };
}

async function askModel(ctx) {
  for (const engine of ENGINES) {
    const key = process.env[engine.keyEnv];
    if (!key) continue;
    const check = verifiedFields(await askEngine(engine, key, decisionPrompt(ctx)), ctx.missing, ctx.text);
    if (!check) continue; // no usable answer from this engine: try the next one
    const tag = `[${engine.name}]`;
    if (check.found.length === 0) {
      const why = check.rejected.length
        ? `model claimed ${check.rejected.join(", ")} but its quotes are not in the document`
        : `none of ${ctx.missing.join(", ")} is written in the document`;
      return { pay: false, reason: `${why} ${tag}` };
    }
    const unverified = check.rejected.length ? `; unverified: ${check.rejected.join(", ")}` : "";
    return { pay: true, reason: `verified in text: ${check.found.join(", ")}${unverified} ${tag}` };
  }
  // Fail closed: an agent that cannot check the document does not pay for it.
  return { pay: false, reason: "no model answered; not paying blind" };
}

async function askEngine(engine, key, prompt) {
  try {
    const r = await fetch(engine.url, {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model: engine.name,
        messages: [{ role: "user", content: prompt }],
        temperature: 0,
        max_tokens: 400,
        ...engine.extra,
      }),
      signal: AbortSignal.timeout(engine.timeoutMs),
    });
    return parseJsonObject((await r.json()).choices?.[0]?.message?.content || "");
  } catch {
    return null; // timeout, retired model, or non-JSON answer
  }
}

// ---------- Dynamic server wallet ----------
async function dynamicClient() {
  const { DynamicEvmWalletClient } = await import("@dynamic-labs-wallet/node-evm");
  for (const k of ["DYNAMIC_ENVIRONMENT_ID", "DYNAMIC_AUTH_TOKEN"]) {
    if (!process.env[k]) throw new Error(`missing env ${k}`);
  }
  const client = new DynamicEvmWalletClient({ environmentId: process.env.DYNAMIC_ENVIRONMENT_ID });
  await client.authenticateApiToken(process.env.DYNAMIC_AUTH_TOKEN);
  return client;
}

function loadWallet() {
  if (!fs.existsSync(STATE)) throw new Error("no wallet yet: run `node buyer.mjs setup` first");
  return JSON.parse(fs.readFileSync(STATE, "utf8"));
}

async function setup() {
  if (fs.existsSync(STATE)) return console.log("wallet already exists:", loadWallet().address);
  const { ThresholdSignatureScheme } = await import("@dynamic-labs-wallet/core");
  const client = await dynamicClient();
  // Dynamic's key-share backup relay answered HTTP 500 five times in a row on 14 Sep 2026, which aborts
  // wallet creation. backUpToDynamic defaults to false in the SDK: every share comes back and we keep it.
  // ponytail: shares sit in a 600 file on one server; encrypt at rest (AES-GCM or a KMS) before real funds.
  const backup = process.env.BACKUP_TO_DYNAMIC === "true";
  const { walletMetadata, externalServerKeyShares } = await client.createWalletAccount({
    thresholdSignatureScheme: ThresholdSignatureScheme.TWO_OF_TWO,
    ...(backup ? { password: process.env.WALLET_PASSWORD, backUpToDynamic: true } : {}),
  });
  fs.mkdirSync(path.dirname(STATE), { recursive: true, mode: 0o700 });
  fs.writeFileSync(
    STATE,
    JSON.stringify({ address: walletMetadata.accountAddress, backup, walletMetadata, externalServerKeyShares }),
    { mode: 0o600 },
  );
  console.log("agent wallet (Base):", walletMetadata.accountAddress);
}

async function balance(address = loadWallet().address) {
  const pc = createPublicClient({ chain: base, transport: http(RPC) });
  const raw = await pc.readContract({ address: USDC_BASE, abi: erc20Abi, functionName: "balanceOf", args: [address] });
  console.log(`${address}  ${formatUnits(raw, 6)} USDC on Base`);
  return raw;
}

async function payingFetch() {
  const { x402Client, wrapFetchWithPayment } = await import("@x402/fetch");
  const { ExactEvmScheme } = await import("@x402/evm/exact/client");
  const w = loadWallet();
  const client = await dynamicClient();
  const walletClient = await client.getWalletClient({
    walletMetadata: w.walletMetadata, // SDK 1.1.x takes the full metadata; the docs example with accountAddress is stale
    externalServerKeyShares: w.externalServerKeyShares,
    ...(w.backup ? { password: process.env.WALLET_PASSWORD } : {}),
    chain: base,
  });
  const x402 = new x402Client();
  x402.register(NETWORK, new ExactEvmScheme(walletClient.account));
  return { fetchPaid: wrapFetchWithPayment(fetch, x402), x402 };
}

function ledger() {
  return fs.existsSync(LEDGER)
    ? fs.readFileSync(LEDGER, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l))
    : [];
}

async function run(file, fields) {
  const text = fs.readFileSync(file, "utf8");
  const found = localExtract(text, fields);
  const missing = fields.filter((f) => found[f] == null);
  const entry = { at: new Date().toISOString(), file: path.basename(file), fields, free: found, missing, paid: false };

  // Probe the price without paying.
  const body = JSON.stringify({ text, fields });
  const probe = await fetch(GATE, { method: "POST", headers: { "Content-Type": "application/json" }, body });
  const req = probe.status === 402 ? readRequirement(probe.headers, await probe.json().catch(() => ({}))) : null;
  if (!req) throw new Error(`gate did not return a Base payment requirement (HTTP ${probe.status})`);
  entry.price_atomic = String(req.amount);

  const blocked = guard({ missing, priceAtomic: req.amount, spent: spentToday(ledger()) });
  const decision = blocked ?? (await askModel({ text, fields, found, missing, priceAtomic: req.amount }));
  Object.assign(entry, { decision: decision.pay ? "pay" : "skip", reason: decision.reason });
  console.log(`decision: ${entry.decision} — ${decision.reason}`);

  if (decision.pay) {
    const { fetchPaid } = await payingFetch();
    const res = await fetchPaid(GATE, { method: "POST", headers: { "Content-Type": "application/json" }, body });
    const { decodePaymentResponseHeader } = await import("@x402/fetch");
    const settle = res.headers.get("payment-response");
    const receipt = settle ? decodePaymentResponseHeader(settle) : null;
    const data = await res.json();
    Object.assign(entry, {
      paid: res.ok && Boolean(receipt?.success ?? receipt),
      amount_atomic: String(req.amount),
      tx: receipt?.transaction || null,
      http: res.status,
      result: { ...found, ...(data.data || {}) },
    });
    console.log(`paid ${formatUnits(req.amount, 6)} USDC  tx: ${entry.tx ? `https://basescan.org/tx/${entry.tx}` : "n/a"}`);
  } else {
    entry.result = found;
  }
  fs.mkdirSync(path.dirname(LEDGER), { recursive: true, mode: 0o700 });
  fs.appendFileSync(LEDGER, JSON.stringify(entry) + "\n", { mode: 0o600 });
  console.log(JSON.stringify(entry.result, null, 2));
}

function selftest() {
  const assert = (c, m) => { if (!c) throw new Error(`selftest failed: ${m}`); };
  const doc = "INVOICE No: INV-2031\nDate: 2026-09-14\nTotal: $1,240.50 USD";
  const got = localExtract(doc, ["invoice_number", "date", "total", "vendor_tax_id"]);
  assert(got.invoice_number === "INV-2031" && got.date === "2026-09-14" && got.total === "1,240.50", "regex pass");
  assert(got.vendor_tax_id === null, "unknown field stays null");
  assert(guard({ missing: [], priceAtomic: 10000n, spent: 0n }).pay === false, "nothing missing -> skip");
  assert(guard({ missing: ["x"], priceAtomic: 30000n, spent: 0n }).pay === false, "over price cap -> skip");
  assert(guard({ missing: ["x"], priceAtomic: 10000n, spent: 95000n }).pay === false, "over daily budget -> skip");
  assert(guard({ missing: ["x"], priceAtomic: 10000n, spent: 0n }) === null, "within limits -> model decides");
  const today = new Date().toISOString();
  assert(spentToday([{ paid: true, at: today, amount_atomic: "10000" }, { paid: false, at: today }]) === 10000n, "ledger sum");
  const hdr = Buffer.from(JSON.stringify({ accepts: [{ network: NETWORK, amount: "10000", payTo: "0xabc", asset: USDC_BASE }] })).toString("base64");
  const r = readRequirement(new Map([["payment-required", hdr]]), null);
  assert(r.amount === 10000n && r.payTo === "0xabc", "v2 header parse");
  assert(parseJsonObject('noise {"a": {"present": true}} tail').a.present === true, "json object after noise");
  assert(parseJsonObject("Here's a thinking process: 1. analyze") === null, "no json -> null");
  const receipt = "receipt ref nw/88-4471-b\namount payable EUR 69,40";
  const v = verifiedFields(
    {
      invoice_number: { present: true, quote: "nw/88-4471-b" },
      total: { present: true, quote: "EUR 69.40" },
      vendor_tax_id: { present: false, quote: "" },
    },
    ["invoice_number", "total", "vendor_tax_id"],
    receipt,
  );
  assert(v.found.join() === "invoice_number" && v.rejected.join() === "total", "a quote must occur verbatim");
  assert(verifiedFields(null, ["x"], "t") === null, "no report -> null");
  console.log("selftest ok");
}

const [cmd, ...args] = process.argv.slice(2);
const fieldsArg = args.includes("--fields") ? args[args.indexOf("--fields") + 1].split(",") : [];
const commands = {
  selftest: async () => selftest(),
  setup,
  balance: () => balance(),
  run: () => run(args[0], fieldsArg),
};
if (!commands[cmd]) {
  console.log("usage: node buyer.mjs selftest | setup | balance | run <file> --fields a,b,c");
  process.exit(1);
}
commands[cmd]().catch((e) => {
  console.error("error:", e.message);
  process.exit(1);
});
