const TEMA_INDEX_HTML = "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n<title>Fieldcast \u2014 Documents to structured JSON in one API call</title>\n<meta name=\"description\" content=\"Fieldcast turns invoices, receipts and contracts into structured JSON with a single API call. You name the fields, it returns them typed. Free tier, no setup, no training data.\">\n<meta name=\"color-scheme\" content=\"dark light\">\n<link rel=\"icon\" href=\"/favicon.ico\" sizes=\"any\">\n<link rel=\"icon\" href=\"/logo.svg\" type=\"image/svg+xml\">\n<link rel=\"apple-touch-icon\" href=\"/apple-touch-icon.png\">\n<meta property=\"og:image\" content=\"https://fieldcast-kopya.muhammetkarakurt1234.workers.dev/logo-1024.png\">\n<meta property=\"og:title\" content=\"Fieldcast \u2014 Documents to structured JSON in one API call\">\n<meta property=\"og:description\" content=\"You name the fields, Fieldcast returns them typed. No templates, no training data.\">\n<meta property=\"og:type\" content=\"website\">\n<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">\n<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>\n<link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap\" rel=\"stylesheet\">\n<style>\n:root{--bg:#0a0b0f;--bg2:#101218;--card:#13151c;--line:#23262f;--ink:#eef0f4;--mut:#a1a7b4;--dim:#7b8190;--acc:#3ddc84;--acc2:#7aa2ff;--accink:#04140a;--code:#0d0f14;--k:#7aa2ff;--s:#9fe7b8;--n:#f5c36b;--c:#6b7280;--shadow:0 1px 0 rgba(255,255,255,.04) inset,0 20px 50px -30px rgba(0,0,0,.8)}\n@media (prefers-color-scheme:light){:root{--bg:#fbfbfc;--bg2:#f3f4f6;--card:#fff;--line:#e4e6eb;--ink:#0f1115;--mut:#4a5160;--dim:#5f6675;--acc:#0f9d58;--acc2:#3b5bdb;--accink:#fff;--shadow:0 1px 2px rgba(16,24,40,.05),0 12px 32px -18px rgba(16,24,40,.18)}}\n*{box-sizing:border-box}html{scroll-behavior:smooth}\nbody{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 Inter,system-ui,-apple-system,Segoe UI,sans-serif;-webkit-font-smoothing:antialiased}\na{color:inherit}code,pre{font-family:\"JetBrains Mono\",ui-monospace,Menlo,monospace}\n.wrap{max-width:1120px;margin:0 auto;padding:0 24px}\nnav{position:sticky;top:0;z-index:20;backdrop-filter:saturate(1.4) blur(12px);background:color-mix(in srgb,var(--bg) 80%,transparent);border-bottom:1px solid var(--line)}\nnav .wrap{display:flex;align-items:center;gap:20px;height:60px}\n.brand{display:flex;align-items:center;gap:9px;font-weight:700;text-decoration:none;margin-right:auto;letter-spacing:-.01em}\n.links{display:flex;gap:22px;font-size:14px}.links a{color:var(--mut);text-decoration:none}.links a:hover{color:var(--ink)}\n.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;font-weight:600;font-size:14px;padding:9px 16px;border-radius:10px;text-decoration:none;border:1px solid var(--line);background:var(--card);transition:border-color .15s,transform .15s}\n.btn:hover{border-color:var(--dim)}.btn.pri{background:var(--acc);color:var(--accink);border-color:transparent}.btn.pri:hover{filter:brightness(1.07)}\n.btn.lg{padding:13px 22px;font-size:15px}\n.hero{position:relative;padding:96px 0 72px;text-align:center;overflow:hidden}\n.hero::before{content:\"\";position:absolute;inset:-40% -10% auto;height:620px;background:radial-gradient(50% 50% at 50% 0,color-mix(in srgb,var(--acc) 22%,transparent),transparent 70%);pointer-events:none}\n.pill{display:inline-flex;gap:8px;align-items:center;font-size:13px;color:var(--mut);border:1px solid var(--line);background:var(--card);padding:5px 12px;border-radius:99px;margin-bottom:26px}\n.pill i{width:7px;height:7px;border-radius:50%;background:var(--acc)}\nh1{font-size:clamp(38px,6.4vw,68px);line-height:1.04;letter-spacing:-.035em;font-weight:700;margin:0 auto 20px;max-width:860px}\nh1 span{color:var(--acc)}\n.lead{font-size:clamp(17px,2vw,20px);color:var(--mut);max-width:640px;margin:0 auto 34px}\n.ctas{display:flex;gap:12px;justify-content:center;flex-wrap:wrap}\n.facts{display:flex;justify-content:center;flex-wrap:wrap;gap:10px 28px;margin-top:40px;color:var(--dim);font-size:14px}.facts b{color:var(--ink);font-weight:600}\nsection{padding:80px 0;border-top:1px solid var(--line)}\n.eyebrow{font:500 12px/1 \"JetBrains Mono\",monospace;color:var(--acc);text-transform:uppercase;letter-spacing:.12em;margin-bottom:14px}\nh2{font-size:clamp(28px,3.6vw,40px);letter-spacing:-.025em;line-height:1.15;margin:0 0 12px}\n.sub{color:var(--mut);font-size:17px;max-width:620px;margin:0 0 40px}\n.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}\n.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:24px;box-shadow:var(--shadow)}\n.card h3{font-size:16px;margin:0 0 6px;letter-spacing:-.01em}.card p{color:var(--mut);font-size:14.5px;margin:0}\n.ic{width:36px;height:36px;border-radius:9px;display:grid;place-items:center;background:color-mix(in srgb,var(--acc) 14%,transparent);color:var(--acc);margin-bottom:16px}\n.term{background:var(--code);border:1px solid var(--line);border-radius:14px;overflow:hidden;box-shadow:var(--shadow);text-align:left}\n@media (prefers-color-scheme:light){.term{--code:#0f1117;--line2:#262a33;color:#e6e8ee}}\n.term .bar{display:flex;align-items:center;gap:8px;padding:11px 14px;border-bottom:1px solid #22252e;font:12px \"JetBrains Mono\",monospace;color:#8a90a0}\n.term .bar s{width:10px;height:10px;border-radius:50%;background:#3a3e48;text-decoration:none}\n.term pre{margin:0;padding:18px 20px;font-size:13px;line-height:1.7;overflow-x:auto;color:#d9dde6}\n.k{color:#7aa2ff}.s{color:#9fe7b8}.n{color:#f5c36b}.c{color:#6b7280}.r{color:#ff8f8f}\n.tabs{display:flex;gap:4px;padding:6px;border-bottom:1px solid #22252e}\n.tabs button{all:unset;cursor:pointer;font:500 12.5px \"JetBrains Mono\",monospace;color:#8a90a0;padding:6px 12px;border-radius:7px}\n.tabs button[aria-selected=true]{background:#1b1e26;color:#eef0f4}.tabs button:focus-visible{outline:2px solid #7aa2ff}\n.panel[hidden]{display:none}\n.hero .term{max-width:780px;margin:56px auto 0}\n.steps{counter-reset:s;display:grid;grid-template-columns:repeat(3,1fr);gap:16px}\n.steps .card{position:relative;padding-top:56px}.steps .card::before{counter-increment:s;content:counter(s,decimal-leading-zero);position:absolute;top:22px;left:24px;font:500 13px \"JetBrains Mono\",monospace;color:var(--acc)}\n.note{color:var(--dim);font-size:14px;margin-top:18px}.note code,.card code{font-size:.9em;padding:1px 6px;border-radius:6px;background:var(--bg2);border:1px solid var(--line)}\n.price{display:flex;flex-direction:column}.price .amt{font-size:36px;font-weight:700;letter-spacing:-.03em;margin:14px 0 4px}.price .amt small{font-size:15px;color:var(--dim);font-weight:500}\n.price .meta{color:var(--dim);font-size:13.5px}.price ul{list-style:none;padding:0;margin:16px 0 24px;color:var(--mut);font-size:14px}.price li{padding:4px 0}.price li::before{content:\"\u2713  \";color:var(--acc)}\n.price .btn{margin-top:auto}\n.price.hl{border-color:color-mix(in srgb,var(--acc) 55%,var(--line));box-shadow:0 0 0 1px color-mix(in srgb,var(--acc) 30%,transparent),var(--shadow)}\n.tag{display:inline-block;font:500 11px \"JetBrains Mono\",monospace;color:var(--acc);border:1px solid color-mix(in srgb,var(--acc) 40%,transparent);padding:2px 8px;border-radius:99px;margin-left:6px;vertical-align:middle}\n.faq{max-width:760px}\ndetails{border-bottom:1px solid var(--line);padding:18px 0}details summary{cursor:pointer;font-weight:600;list-style:none;display:flex;justify-content:space-between;gap:16px}\ndetails summary::-webkit-details-marker{display:none}details summary::after{content:\"+\";color:var(--dim);font-family:\"JetBrains Mono\",monospace}details[open] summary::after{content:\"\u2013\"}\ndetails p{color:var(--mut);margin:10px 0 0;font-size:15px}\n.cta{text-align:center}.cta .sub{margin:0 auto 30px}\nfooter{border-top:1px solid var(--line);padding:48px 0;color:var(--dim);font-size:14px}\nfooter .cols{display:flex;justify-content:space-between;gap:32px;flex-wrap:wrap}footer a{color:var(--mut);text-decoration:none}footer a:hover{color:var(--ink);text-decoration:underline}\nfooter p{margin:6px 0}.badges{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}\n.badge{display:inline-flex;gap:8px;align-items:center;border:1px solid var(--line);background:var(--card);border-radius:9px;padding:7px 11px}.badge small{display:block;font-size:10.5px;color:var(--dim);line-height:1.2}.badge span{font-size:13px;color:var(--ink);font-weight:600;line-height:1.2}\n:focus-visible{outline:2px solid var(--acc2);outline-offset:2px}\n@media (max-width:900px){.grid4{grid-template-columns:1fr 1fr}.grid3,.steps{grid-template-columns:1fr}.links{display:none}}\n@media (max-width:620px){.grid2,.grid4{grid-template-columns:1fr}.hero{padding:64px 0 56px}section{padding:60px 0}nav .btn:not(.pri){display:none}}\n@media (prefers-reduced-motion:reduce){*{transition:none!important;scroll-behavior:auto!important}}\n</style>\n</head>\n<body>\n<nav aria-label=\"Main\">\n  <div class=\"wrap\">\n    <a href=\"/\" class=\"brand\"><svg width=\"22\" height=\"22\" viewBox=\"0 0 24 24\" fill=\"none\" aria-hidden=\"true\"><path d=\"M6 2h8l4 4v16H6z\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linejoin=\"round\"/><path d=\"M14 2v4h4\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linejoin=\"round\"/><path d=\"M9 12h6M9 16h4\" stroke=\"var(--acc)\" stroke-width=\"1.8\" stroke-linecap=\"round\"/></svg>Fieldcast</a>\n    <div class=\"links\">\n      <a href=\"#how\">How it works</a><a href=\"#agents\">For agents</a><a href=\"#pricing\">Pricing</a><a href=\"/for/\">Use cases</a><a href=\"#faq\">FAQ</a>\n    </div>\n    <a href=\"/dene.html\" class=\"btn\">Try it</a>\n    <a href=\"#how\" class=\"btn pri\">Quickstart</a>\n  </div>\n</nav>\n\n<main>\n<header class=\"hero\">\n  <div class=\"wrap\">\n    <div class=\"pill\"><i></i>Document extraction API \u00b7 x402 on Base mainnet</div>\n    <h1>Data you can trust from <span>every document.</span></h1>\n    <p class=\"lead\">Send a PDF or raw text and name the fields you need. Fieldcast returns clean, typed JSON for your workflow, database, or AI agent.</p>\n    <div class=\"ctas\">\n      <a href=\"/dene.html\" class=\"btn pri lg\">Get a live demo</a>\n      <a href=\"#pricing\" class=\"btn lg\">See pricing</a>\n    </div>\n    <div class=\"facts\"><span><b>1</b> API call</span><span><b>\u226440</b> fields you name</span><span><b>$0.01</b> per x402 call</span><span><b>0</b> templates to draw</span></div>\n\n    <div class=\"term\" aria-label=\"Code sample\">\n      <div class=\"tabs\" role=\"tablist\">\n        <button role=\"tab\" aria-selected=\"true\" aria-controls=\"p1\" id=\"t1\">API key</button>\n        <button role=\"tab\" aria-selected=\"false\" aria-controls=\"p2\" id=\"t2\" tabindex=\"-1\">x402 \u00b7 agents</button>\n      </div>\n      <div class=\"panel\" id=\"p1\" role=\"tabpanel\" aria-labelledby=\"t1\">\n<pre><span class=\"c\"># Free demo key \u2014 works right now</span>\ncurl -X POST https://fieldcast-kopya.muhammetkarakurt1234.workers.dev/v1/extract \\\n  -H <span class=\"s\">\"X-API-Key: demo_key_public\"</span> \\\n  -H <span class=\"s\">\"Content-Type: application/json\"</span> \\\n  -d <span class=\"s\">'{\n    \"text\": \"INVOICE INV-2043 ... Total: 1,240.50 EUR\",\n    \"fields\": [\"invoice_number\",\"date\",\"total\",\"currency\"]\n  }'</span>\n\n<span class=\"c\"># \u2192 200 OK</span>\n{ <span class=\"k\">\"invoice_number\"</span>: <span class=\"s\">\"INV-2043\"</span>, <span class=\"k\">\"date\"</span>: <span class=\"s\">\"2026-08-14\"</span>, <span class=\"k\">\"total\"</span>: <span class=\"n\">1240.5</span>, <span class=\"k\">\"currency\"</span>: <span class=\"s\">\"EUR\"</span> }</pre>\n      </div>\n      <div class=\"panel\" id=\"p2\" role=\"tabpanel\" aria-labelledby=\"t2\" hidden>\n<pre><span class=\"c\"># 1. Call without a key</span>\nPOST /x402/extract\n<span class=\"r\">\u2190 402 Payment Required</span>   <span class=\"c\"># payment terms: $0.01 \u00b7 USDC \u00b7 Base mainnet</span>\n\n<span class=\"c\"># 2. Agent signs a $0.01 USDC payment and retries</span>\nPOST /x402/extract\n  X-PAYMENT: &lt;signed payment&gt;\n\n<span class=\"c\"># 3. Same flow, extraction returned</span>\n<span class=\"s\">\u2190 200 OK</span>\n{ <span class=\"k\">\"invoice_number\"</span>: <span class=\"s\">\"INV-2043\"</span>, <span class=\"k\">\"total\"</span>: <span class=\"n\">1240.5</span>, <span class=\"k\">\"currency\"</span>: <span class=\"s\">\"EUR\"</span> }</pre>\n      </div>\n    </div>\n    <p class=\"note\">Built for the documents your business already runs on: invoices, receipts, purchase orders, contracts, bank statements, delivery notes, tax forms.</p>\n  </div>\n</header>\n\n<section id=\"how\">\n  <div class=\"wrap\">\n    <div class=\"eyebrow\">How it works</div>\n    <h2>One request, one response</h2>\n    <p class=\"sub\">Name the fields. Get them back. That is the entire interface.</p>\n    <div class=\"steps\">\n      <div class=\"card\"><h3>Send a document</h3><p>Post raw text as JSON, or a PDF as multipart with <code>fields=a,b,c</code>.</p></div>\n      <div class=\"card\"><h3>Name your fields</h3><p>Up to 40 fields, named however your database already names them.</p></div>\n      <div class=\"card\"><h3>Get typed JSON</h3><p>Totals as numbers, dates as ISO-8601. Any field the document does not contain comes back <code>null</code> rather than invented.</p></div>\n    </div>\n  </div>\n</section>\n\n<section>\n  <div class=\"wrap\">\n    <div class=\"eyebrow\">Why teams pick it</div>\n    <h2>Built for real-world documents</h2>\n    <p class=\"sub\">Built to survive real-world documents, not just the happy path.</p>\n    <div class=\"grid4\">\n      <div class=\"card\"><div class=\"ic\"><svg width=\"18\" height=\"18\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\"><path stroke-linecap=\"round\" d=\"M4 7h16M4 12h10M4 17h7\"/></svg></div><h3>No template drawing</h3><p>Template parsers break the moment a supplier changes layout. Fieldcast reads the document, so a new layout is not a new project.</p></div>\n      <div class=\"card\"><div class=\"ic\"><svg width=\"18\" height=\"18\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\"><path stroke-linecap=\"round\" d=\"M12 4v16m8-8H4\"/></svg></div><h3>Fields you choose</h3><p>Not a fixed invoice schema. Ask for up to 40 fields, named however your database already names them.</p></div>\n      <div class=\"card\"><div class=\"ic\"><svg width=\"18\" height=\"18\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\"><path stroke-linecap=\"round\" stroke-linejoin=\"round\" d=\"M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z\"/></svg></div><h3>null, not a guess</h3><p>Missing data comes back as null. A parser that invents a total is worse than one that admits it did not find one.</p></div>\n      <div class=\"card\"><div class=\"ic\"><svg width=\"18\" height=\"18\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\"><path stroke-linecap=\"round\" stroke-linejoin=\"round\" d=\"m7 8-4 4 4 4m10-8 4 4-4 4M14 4l-4 16\"/></svg></div><h3>Typed output</h3><p>Totals come back as numbers, dates as ISO-8601. No downstream string cleanup.</p></div>\n    </div>\n  </div>\n</section>\n\n<section id=\"agents\">\n  <div class=\"wrap\">\n    <div class=\"eyebrow\">x402 \u00b7 pay-per-call</div>\n    <h2>Pay-per-call for AI agents</h2>\n    <p class=\"sub\">Fieldcast also exposes an <strong>x402</strong> endpoint: no signup, no API key. An agent calls it, receives HTTP 402 with payment terms, pays in USDC, and gets the extraction back in the same flow. Live on Base mainnet today.</p>\n    <div class=\"grid3\">\n      <div class=\"card\"><h3>No account needed</h3><p>An autonomous agent cannot fill in a signup form. It can pay per call.</p></div>\n      <div class=\"card\"><h3>Settlement in cents</h3><p>$0.01 per document, paid in USDC on Base mainnet.</p></div>\n      <div class=\"card\"><h3>Discoverable</h3><p>Declared to the x402 Bazaar so agents searching for document extraction find it on their own.</p></div>\n    </div>\n  </div>\n</section>\n\n<section id=\"pricing\">\n  <div class=\"wrap\">\n    <div class=\"eyebrow\">Pricing</div>\n    <h2>Simple, honest pricing</h2>\n    <p class=\"sub\">Every plan uses the same endpoint and the same engine. Nothing held back behind a higher tier.</p>\n    <div class=\"grid4\">\n      <div class=\"card price\"><h3>Free</h3><div class=\"meta\">While in beta</div><div class=\"amt\">$0</div><ul><li>50 extractions / month</li></ul><a href=\"#how\" class=\"btn\">Start free</a></div>\n      <div class=\"card price\"><h3>Starter</h3><div class=\"meta\">For small teams</div><div class=\"amt\">$19<small>/mo</small></div><ul><li>1,000 extractions / month</li></ul><a href=\"#how\" class=\"btn\">Choose Starter</a></div>\n      <div class=\"card price\"><h3>Pro</h3><div class=\"meta\">For scaling volume</div><div class=\"amt\">$49<small>/mo</small></div><ul><li>5,000 extractions / month</li></ul><a href=\"#how\" class=\"btn\">Choose Pro</a></div>\n      <div class=\"card price hl\"><h3>Agents \u00b7 x402 <span class=\"tag\">For agents</span></h3><div class=\"meta\">No signup, per call</div><div class=\"amt\">$0.01<small>/call</small></div><ul><li>Unmetered</li><li>USDC on Base mainnet</li></ul><a href=\"#agents\" class=\"btn pri\">How x402 works</a></div>\n    </div>\n  </div>\n</section>\n\n<section id=\"faq\">\n  <div class=\"wrap faq\">\n    <div class=\"eyebrow\">FAQ</div>\n    <h2>Frequently asked questions</h2>\n    <details><summary>Do I have to define a template for each document layout?</summary><p>No. You pass a list of field names with the request. Fieldcast reads the document and returns those fields. A supplier changing their invoice layout requires no change on your side.</p></details>\n    <details><summary>What file types are supported?</summary><p>PDF and plain text today. PDFs are converted to text server-side before extraction. Scanned image-only documents need OCR, which is not yet available.</p></details>\n    <details><summary>What happens if a field is missing from the document?</summary><p>It is returned as null. Fieldcast does not invent values to fill a schema, because a plausible wrong total is more expensive than a missing one.</p></details>\n    <details><summary>How accurate is it?</summary><p>On the reference ten-field invoice test, all ten fields were extracted correctly, with dates normalised to ISO-8601 and monetary values returned as numbers. Measure accuracy on your own documents \u2014 that is what the free tier is for.</p></details>\n    <details><summary>Can an AI agent use Fieldcast without an account?</summary><p>Yes. The x402 endpoint requires no API key. The agent receives payment terms as an HTTP 402 response, settles in USDC, and receives the extraction in the same request flow. It runs on Base mainnet: $0.01 per document in USDC.</p></details>\n    <details><summary>Is my document stored?</summary><p>Document contents are not persisted. Only a usage counter \u2014 API key, month, call count, character count \u2014 is recorded for billing.</p></details>\n  </div>\n</section>\n\n<section class=\"cta\">\n  <div class=\"wrap\">\n    <h2>Try it on your own documents.</h2>\n    <p class=\"sub\">The free tier is 50 extractions a month, no credit card. Point it at a real invoice and see the JSON.</p>\n    <div class=\"ctas\"><a href=\"#how\" class=\"btn pri lg\">Read the quickstart</a><a href=\"/for/\" class=\"btn lg\">See use cases</a></div>\n  </div>\n</section>\n</main>\n\n<footer>\n  <div class=\"wrap\">\n    <div class=\"cols\">\n      <div>\n        <a href=\"/\" class=\"brand\" style=\"margin-bottom:8px\">Fieldcast</a>\n        <p>Document extraction API.</p>\n      </div>\n      <div>\n        <p><a href=\"/for/\">Use cases</a> \u00b7 <a href=\"/alternatives/\">Comparisons</a> \u00b7 <a href=\"/privacy.html\">Privacy</a> \u00b7 <a href=\"/terms.html\">Terms</a></p>\n        <p>Built for <a href=\"/for/bookkeepers\">bookkeepers</a>, <a href=\"/for/agencies\">agencies</a> and <a href=\"/for/agent-builders\">AI agent builders</a>.</p>\n        <p>Compared with <a href=\"/alternatives/docparser\">Docparser</a>, <a href=\"/alternatives/mindee\">Mindee</a> and <a href=\"/alternatives/nanonets\">Nanonets</a>.</p>\n      </div>\n    </div>\n    <div class=\"badges\">\n      <a class=\"badge\" href=\"https://aiagentsdirectory.com/agent/fieldcast\" target=\"_blank\" rel=\"noopener noreferrer\"><svg width=\"18\" height=\"18\" viewBox=\"0 0 24 24\" fill=\"none\" aria-hidden=\"true\"><circle cx=\"12\" cy=\"12\" r=\"10\" fill=\"#22c55e\"/><path d=\"M8 12.4l2.6 2.6L16 9.6\" stroke=\"#04140a\" stroke-width=\"2.2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg><div><small>FEATURED ON</small><span>AI Agents Directory</span></div></a>\n      <a class=\"badge\" href=\"https://www.agenthunter.io?utm_source=badge&utm_medium=embed&utm_campaign=Fieldcast\" target=\"_blank\" rel=\"noopener noreferrer\"><img src=\"https://www.agenthunter.io/logo-light.svg\" alt=\"\" width=\"18\" height=\"18\"><div><small>AgentHunter</small><span>Featured AI Agent</span></div></a>\n    </div>\n  </div>\n</footer>\n<script>\n(function(){var t=[document.getElementById('t1'),document.getElementById('t2')],p=[document.getElementById('p1'),document.getElementById('p2')];\nfunction sel(i){t.forEach(function(b,j){b.setAttribute('aria-selected',i===j);b.tabIndex=i===j?0:-1;p[j].hidden=i!==j;});t[i].focus();}\nt.forEach(function(b,i){b.addEventListener('click',function(){sel(i)});b.addEventListener('keydown',function(e){if(e.key==='ArrowRight'||e.key==='ArrowLeft')sel(1-i);});});})();\n</script>\n<script type=\"application/ld+json\">\n{\"@context\":\"https://schema.org\",\"@type\":\"SoftwareApplication\",\"name\":\"Fieldcast\",\"applicationCategory\":\"DeveloperApplication\",\"operatingSystem\":\"Any\",\"description\":\"API that turns PDFs and text documents into structured JSON. Callers specify the fields they want and receive them typed, with missing fields returned as null.\",\"offers\":[{\"@type\":\"Offer\",\"name\":\"Free\",\"price\":\"0\",\"priceCurrency\":\"USD\"},{\"@type\":\"Offer\",\"name\":\"Starter\",\"price\":\"19\",\"priceCurrency\":\"USD\"},{\"@type\":\"Offer\",\"name\":\"Pro\",\"price\":\"49\",\"priceCurrency\":\"USD\"}]}\n</script>\n<script type=\"application/ld+json\">\n{\"@context\":\"https://schema.org\",\"@type\":\"FAQPage\",\"mainEntity\":[\n{\"@type\":\"Question\",\"name\":\"Do I have to define a template for each document layout?\",\"acceptedAnswer\":{\"@type\":\"Answer\",\"text\":\"No. You pass a list of field names with the request and Fieldcast reads the document and returns those fields. A supplier changing their invoice layout does not require any change on your side.\"}},\n{\"@type\":\"Question\",\"name\":\"What file types are supported?\",\"acceptedAnswer\":{\"@type\":\"Answer\",\"text\":\"PDF and plain text. PDFs are converted to text server-side before extraction. Scanned image-only documents need OCR, which is not yet available.\"}},\n{\"@type\":\"Question\",\"name\":\"What happens if a field is missing from the document?\",\"acceptedAnswer\":{\"@type\":\"Answer\",\"text\":\"It is returned as null. Fieldcast does not invent values to fill a schema.\"}},\n{\"@type\":\"Question\",\"name\":\"How accurate is it?\",\"acceptedAnswer\":{\"@type\":\"Answer\",\"text\":\"On the reference ten-field invoice test all ten fields were extracted correctly, with dates normalised to ISO-8601 and monetary values returned as numbers.\"}},\n{\"@type\":\"Question\",\"name\":\"Can an AI agent use Fieldcast without an account?\",\"acceptedAnswer\":{\"@type\":\"Answer\",\"text\":\"Yes. The x402 endpoint requires no API key. The agent receives payment terms as an HTTP 402 response, settles in USDC on Base, and receives the extraction in the same request flow.\"}},\n{\"@type\":\"Question\",\"name\":\"Is my document stored?\",\"acceptedAnswer\":{\"@type\":\"Answer\",\"text\":\"Document contents are not persisted. Only a usage counter is recorded for billing.\"}}]}\n</script>\n</body>\n</html>\n";
// Fieldcast Cloudflare Worker: Cloudflare only.
// Statik site ../public'ten (Workers assets). API burada:
//   POST /v1/extract  -> json {text, fields[]} veya multipart file + fields (api/index.py ile ayni sozlesme)
//   GET  /health
//   /x402/extract, /x402/health -> sunucudaki x402 kapisi (Base USDC, PayAI facilitator)
// PDF metni Workers AI toMarkdown ile okunur; alanlar NVIDIA modellerinden, NVIDIA duserse Workers AI'dan.

const NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions";
// 26 Eki olcumu (3 zor ornek, 16 alan): ikisi de 16/16. Eski 4 model NVIDIA'da EOL (410).
const NVIDIA_MODELS = ["nvidia/nemotron-3.5-bolt-e4b", "minimaxai/minimax-m3.1-flash"];
const CF_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
const API_KEYS = { demo_key_public: "demo" };
const MAX_CHARS = 20000;
const MAX_FIELDS = 40;
const X402_GATE = "https://157-173-122-86.sslip.io/base";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Content-Type, X-API-Key, X-PAYMENT, PAYMENT-SIGNATURE",
  "Access-Control-Expose-Headers": "X-PAYMENT-RESPONSE, PAYMENT-RESPONSE, PAYMENT-REQUIRED",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
};

function json(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...CORS } });
}

function track(ctx, env, event, durationMs = 0, chars = 0) {
  if (!env.ANALYTICS || !ctx?.waitUntil) return;
  ctx.waitUntil(Promise.resolve().then(() => env.ANALYTICS.writeDataPoint({
    blobs: ["/v1/extract", event],
    doubles: [durationMs, chars],
    indexes: [event],
  })).catch(() => {}));
}

function prompt(text, fields) {
  return (
    "Extract the requested fields from the document text below.\n" +
    "Return ONLY a JSON object, no explanation, no markdown fence.\n" +
    "Use exactly these keys: " + fields.join(", ") + "\n" +
    "Normalise dates to ISO-8601 (YYYY-MM-DD). Keep monetary values as numbers.\n" +
    "If a field is not present in the document, set it to null. Do not invent values.\n\n" +
    "DOCUMENT:\n" + text.slice(0, MAX_CHARS)
  );
}

function jsonAyikla(content) {
  if (!content) throw new Error("empty response from model");
  if (content.includes("</think>")) content = content.split("</think>").pop();
  content = content.trim().replace(/^```(?:json)?|```$/gm, "").trim();
  try {
    return JSON.parse(content);
  } catch {
    const m = content.match(/\{[\s\S]*\}/);
    if (!m) throw new Error("model did not return JSON");
    return JSON.parse(m[0]);
  }
}

async function nvidia(key, model, p) {
  const r = await fetch(NVIDIA_URL, {
    method: "POST",
    headers: { Authorization: "Bearer " + key, "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ model, messages: [{ role: "user", content: p }], temperature: 0, max_tokens: 900 }),
    signal: AbortSignal.timeout(45000),
  });
  if (!r.ok) throw new Error("HTTP " + r.status);
  const d = await r.json();
  return (d.choices?.[0]?.message?.content || "").trim();
}

async function extractFields(env, text, fields) {
  const p = prompt(text, fields);
  const hatalar = [];
  if (env.NVIDIA_API_KEY) {
    for (const m of NVIDIA_MODELS) {
      try {
        return jsonAyikla(await nvidia(env.NVIDIA_API_KEY, m, p));
      } catch (e) {
        hatalar.push("nvidia/" + m + ": " + String(e.message).slice(0, 80));
      }
    }
  }
  try {
    const r = await env.AI.run(CF_MODEL, { messages: [{ role: "user", content: p }], temperature: 0, max_tokens: 900 });
    return jsonAyikla(typeof r.response === "string" ? r.response : JSON.stringify(r.response));
  } catch (e) {
    hatalar.push("workers-ai: " + String(e.message).slice(0, 80));
  }
  throw new Error("all providers failed -> " + hatalar.join(" | "));
}

async function belgeOku(env, req) {
  const tip = req.headers.get("Content-Type") || "";
  let text = "", fields = [];
  if (tip.includes("multipart/form-data")) {
    const form = await req.formData();
    const file = form.get("file");
    fields = String(form.get("fields") || "").split(",").map((s) => s.trim()).filter(Boolean);
    if (file && typeof file !== "string") {
      try {
        if (/\.pdf$/i.test(file.name) || file.type === "application/pdf") {
          const [md] = await env.AI.toMarkdown([{ name: file.name || "doc.pdf", blob: file }]);
          if (md.format === "error") throw new Error(md.error || "pdf could not be read");
          text = (md.data || "").trim();
        } else {
          text = (await file.text()).trim();
        }
      } catch (e) {
        return { hata: json({ error: "file_unreadable", detail: String(e.message).slice(0, 200) }, 400) };
      }
    } else {
      text = String(form.get("text") || "").trim();
    }
  } else {
    const d = await req.json().catch(() => ({}));
    text = String(d.text || "").trim();
    fields = Array.isArray(d.fields) ? d.fields.map(String) : [];
  }
  if (!text) return { hata: json({ error: "no_document_text" }, 400) };
  if (!fields.length) return { hata: json({ error: "no_fields_requested" }, 400) };
  if (fields.length > MAX_FIELDS) return { hata: json({ error: "too_many_fields", max: MAX_FIELDS }, 400) };
  return { text, fields };
}

async function gate(req, yol) {
  const h = new Headers(req.headers);
  for (const k of ["host", "cf-connecting-ip", "x-forwarded-for", "x-real-ip", "cookie"]) h.delete(k);
  const r = await fetch(X402_GATE + yol, {
    method: req.method, headers: h,
    body: req.method === "GET" || req.method === "HEAD" ? undefined : req.body, duplex: "half",
  });
  const out = new Headers(r.headers);
  for (const [k, v] of Object.entries(CORS)) out.set(k, v);
  return new Response(r.body, { status: r.status, headers: out });
}

async function extract(env, req, ctx) {
  const started = Date.now();
  const key = req.headers.get("X-API-Key") || "";
  const plan = API_KEYS[key];
  if (!plan) {
    // No valid API key -> paid x402 path (Base mainnet USDC) via the gate.
    track(ctx, env, "x402", Date.now() - started);
    return gate(req, "/v1/extract" + new URL(req.url).search);
  }
  // ponytail: kalici aylik kota yok; IP basina dakikada 10 cagri (Cloudflare rate limit, depolama yok).
  // Gercek musteri anahtarlari gelince KV/D1'de aylik sayac.
  const ip = req.headers.get("CF-Connecting-IP") || "?";
  if (env.DENEME_SINIRI && !(await env.DENEME_SINIRI.limit({ key: ip })).success) {
    track(ctx, env, "quota_exceeded", Date.now() - started);
    return json({ error: "quota_exceeded", plan, detail: "rate limit: 10 calls per minute" }, 429);
  }
  const { text, fields, hata } = await belgeOku(env, req);
  if (hata) return hata;
  try {
    const data = await extractFields(env, text, fields);
    track(ctx, env, "ok", Date.now() - started, text.length);
    return json({ data, chars_processed: text.length });
  } catch (e) {
    track(ctx, env, "extraction_failed", Date.now() - started, text.length);
    return json({ error: "extraction_failed", detail: String(e.message).slice(0, 200) }, 502);
  }
}

export default {
  async fetch(req, env, ctx) {
    { const _u = new URL(req.url);
      if ((req.method === "GET" || req.method === "HEAD") && _u.pathname === "/") {
        return new Response(req.method === "HEAD" ? null : TEMA_INDEX_HTML, { status: 200, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "public, max-age=0, must-revalidate" } });
      } }
    const u = new URL(req.url);
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    if (u.pathname === "/health") {
      try {
        const r = await fetch(X402_GATE + "/health", { signal: AbortSignal.timeout(8000) });
        const g = await r.json();
        return json({ status: r.ok ? "ok" : "degraded", time: new Date().toISOString().slice(0, 19), x402: g });
      } catch (e) {
        return json({ status: "degraded", time: new Date().toISOString().slice(0, 19), x402: "unreachable" }, 503);
      }
    }
    if (u.pathname === "/v1/extract") {
      return req.method === "POST" ? extract(env, req, ctx) : json({ error: "method_not_allowed" }, 405);
    }
    if (u.pathname === "/x402/extract" || u.pathname === "/x402/health") {
      const yol = u.pathname === "/x402/extract" ? "/v1/extract" : "/health";
      return gate(req, yol + u.search);
    }
    return env.ASSETS.fetch(req);
  },
};
