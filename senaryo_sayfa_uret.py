# -*- coding: utf-8 -*-
"""Kullanim senaryosu (/for/...) sayfalarini uretir.

Alternatif sayfalari "X yerine neden biz" sorusuna cevap veriyor.
Bunlar "benim isim icin ne yapiyor" sorusuna cevap veriyor - dizin
linklerinden gelen trafigin inecegi ikinci hedef.

Kural: sadece OLCULEN iddia. Musteri sayisi 0, o yuzden referans/vaka yok.
x402 ucu CANLI DEGIL -> ajan sayfasinda satis argumani yapilmiyor, durumu
acikca yaziliyor. Olmayan ozelligi satmak ilk musteriyi kaybettirir.
"""
import html
import json
import pathlib

CANLI = "https://fieldcast-peach.vercel.app"
CIKTI = pathlib.Path(__file__).parent / "public" / "for"
CIKTI.mkdir(parents=True, exist_ok=True)

SENARYOLAR = [
    {
        "slug": "bookkeepers",
        "kisa": "Bookkeepers & accounts payable",
        "h1": "Supplier invoices into your ledger, without a parser per supplier",
        "meta": "Fieldcast for bookkeepers and accounts payable teams: extract supplier, invoice number, dates, net, VAT and gross from any invoice layout as typed JSON. Free tier, no card.",
        "acilis": (
            "Every supplier formats their invoice differently, and the ones who do not change "
            "it eventually will. If you are keying invoice totals in by hand, or maintaining a "
            "parser template per supplier, the work never actually finishes — it just moves."
        ),
        "nasil": (
            "Fieldcast takes the field names you want with each request. A new supplier with a "
            "layout nobody has seen before goes through the same call as the ones you already "
            "handle. Nothing to configure per vendor."
        ),
        "alanlar": ["supplier_name", "invoice_number", "invoice_date", "due_date",
                    "net_amount", "vat_amount", "gross_amount", "currency",
                    "po_number", "payment_terms"],
        "cikti": {
            "supplier_name": "ACME SUPPLIES LTD",
            "invoice_number": "INV-2026-0431",
            "invoice_date": "2026-08-14",
            "due_date": "2026-09-13",
            "net_amount": 452.5,
            "vat_amount": 90.5,
            "gross_amount": 543.0,
            "currency": "GBP",
            "po_number": None,
            "payment_terms": "Net 30",
        },
        "neden_onemli": [
            ("It says null instead of guessing",
             "There was no purchase order number on that invoice, so <code>po_number</code> came back "
             "<code>null</code>. In bookkeeping a missing value is a queue item; a confidently wrong "
             "total is a reconciliation problem you find three months later."),
            ("Totals arrive as numbers",
             "<code>452.5</code>, not <code>\"452,50 GBP\"</code>. No thousands separators, no currency "
             "symbols glued to the figure, no locale guessing before it reaches your ledger."),
            ("Dates arrive as ISO-8601",
             "<code>2026-08-14</code> whether the invoice said <em>14 August 2026</em>, <em>14/08/2026</em> "
             "or <em>08/14/2026</em>. The ambiguity is resolved before it becomes a wrong due date."),
        ],
        "yapmaz": [
            "It does not read scanned or photographed invoices — PDF and text only, no OCR yet.",
            "It does not push into Xero, QuickBooks or Sage. It returns JSON; the posting is your code.",
            "It does not do three-way matching or approval routing.",
            "It is not a certified system of record. Validate values before they hit your books.",
        ],
        "sss": [
            ("What happens when a supplier changes their invoice layout?",
             "Nothing on your side. There is no stored template tied to that supplier, so a redesigned invoice goes through the same request as before."),
            ("Can I get line items, not just totals?",
             "You can ask for a field like line_items and it will be returned, but structured repeating rows are the weakest part of any extraction system. Test it against your own invoices on the free tier before you depend on it."),
            ("Is it accurate enough for accounting?",
             "On a ten-field invoice test, live in production, all ten fields were correct. That is one document, not a benchmark. The free tier is 50 extractions a month specifically so you can measure it on your own invoices instead of trusting that number."),
        ],
        "ilgili": [("Compared with Docparser", "/alternatives/docparser"),
                   ("Compared with Mindee", "/alternatives/mindee")],
    },
    {
        "slug": "agencies",
        "kisa": "Agencies & freelance developers",
        "h1": "One endpoint you can resell across every client, whatever their documents look like",
        "meta": "Fieldcast for agencies and freelance developers: one document extraction endpoint that adapts per client by changing a field list, not by building a new parser.",
        "acilis": (
            "Client A wants purchase orders. Client B wants shipping manifests. Client C wants "
            "insurance claim forms. With a template-based parser each of those is a separate "
            "configuration project you have to build, bill for, and then maintain for years."
        ),
        "nasil": (
            "With Fieldcast the difference between those three clients is the contents of one "
            "array. Same endpoint, same integration code, different field names. What you built "
            "for the first client is most of what you ship to the third."
        ),
        "alanlar": ["po_number", "vendor", "ship_to", "delivery_date",
                    "total_units", "incoterms"],
        "cikti": {
            "po_number": "PO-55120",
            "vendor": "Northwind Trading Co.",
            "ship_to": "Warehouse 4, Rotterdam",
            "delivery_date": "2026-09-02",
            "total_units": 1840,
            "incoterms": "DAP",
        },
        "neden_onemli": [
            ("Onboarding a client is a config change, not a project",
             "No parser to draw, no model to train, no per-client setup fee you have to justify. "
             "The margin on the second client is much better than on the first."),
            ("Your integration code stays identical",
             "One request shape, one response shape. You write the error handling, retry logic and "
             "queueing once and reuse it across the whole client book."),
            ("Predictable cost per client",
             "One extraction per call regardless of how many fields that client wants or how many "
             "pages the document has. Easy to price a retainer against."),
        ],
        "yapmaz": [
            "There is no white-label or reseller programme yet. You would be integrating an API, not rebranding a product.",
            "There is no per-client dashboard, usage split, or sub-account structure — usage is tracked against one API key.",
            "No OCR for scanned documents yet.",
            "No SLA. It is a beta run by one developer, which matters if you are signing client contracts against it.",
        ],
        "sss": [
            ("Can I put my own margin on top?",
             "Nothing stops you billing your client for the workflow you build. But there is no formal reseller agreement or white-label tier today, so do not promise a client something the terms do not cover."),
            ("How do I separate usage per client?",
             "Today you cannot — one key, one counter. If you need per-client attribution you would have to track it on your side. Multiple keys are a reasonable request; email me if you need it."),
            ("What if it gets a field wrong for a client?",
             "Validate before you write. Fieldcast returns null rather than inventing values, but it does not guarantee the values it does return. For client work, put a review step on anything financial."),
        ],
        "ilgili": [("Compared with Nanonets", "/alternatives/nanonets"),
                   ("Compared with Docparser", "/alternatives/docparser")],
    },
    {
        "slug": "agent-builders",
        "kisa": "AI agent builders",
        "h1": "A document-extraction tool your agent can call in one step",
        "meta": "Fieldcast for AI agent builders: a single-call document extraction tool with a stable JSON contract, nulls instead of hallucinated values, and no multi-step workflow to orchestrate.",
        "acilis": (
            "An agent that has to read a document usually ends up with the whole document dumped "
            "into its context, then guesses the fields itself. That burns tokens, and worse, a "
            "model asked to fill a schema will fill it — including the parts that were never in "
            "the document."
        ),
        "nasil": (
            "Fieldcast gives your agent one tool with a stable contract: pass the document and the "
            "field names, get typed JSON back. Fields that are genuinely absent come back "
            "<code>null</code> rather than being invented, so your agent can branch on missing data "
            "instead of acting on a plausible fiction."
        ),
        "alanlar": ["document_type", "counterparty", "effective_date",
                    "termination_date", "notice_period_days", "governing_law"],
        "cikti": {
            "document_type": "service agreement",
            "counterparty": "Northwind Trading Co.",
            "effective_date": "2026-09-01",
            "termination_date": None,
            "notice_period_days": 30,
            "governing_law": "England and Wales",
        },
        "neden_onemli": [
            ("Null is a branch your agent can take",
             "<code>termination_date</code> was not in that contract, so it came back <code>null</code>. "
             "Your agent can ask a human, or flag it. An agent that received a plausible invented date "
             "would proceed confidently and be wrong."),
            ("One call, not a workflow",
             "No pipeline to orchestrate, no intermediate state to hold. It fits a single tool "
             "definition, which is what an agent loop can actually reason about."),
            ("The document does not enter your agent's context",
             "Extraction happens server-side. Your agent receives a small typed object instead of "
             "twenty pages of raw text competing for context."),
        ],
        "yapmaz": [
            "No OCR — scanned or photographed documents are not supported yet.",
            "No MCP server yet. Today it is a plain HTTP tool; an MCP wrapper is not written.",
            "Extraction runs on a third-party model provider, so documents leave the service. Check your confidentiality obligations first.",
            "It is a beta run by one developer, with no uptime guarantee.",
        ],
        "x402_notu": (
            "An x402 endpoint — pay-per-call in USDC on Base with no account and no API key — is "
            "written in the codebase but is <strong>not deployed yet</strong>, so it cannot be used "
            "today. It is listed here as roadmap, not as a feature. Use the API-key endpoint for now."
        ),
        "sss": [
            ("Is there an MCP server?",
             "Not yet. Fieldcast is a plain HTTP endpoint today, which most agent frameworks wrap as a tool without difficulty. An MCP server is on the list but is not written, so do not plan around it."),
            ("Can an agent pay per call without an account?",
             "Not today. The x402 endpoint exists in the codebase but has not been deployed and has no wallet configured, so agents currently need an API key like any other caller."),
            ("What does the tool definition look like?",
             "Two parameters: the document (text or a file) and an array of field names. The response is a flat JSON object whose keys are exactly the field names you asked for, with null for anything absent. That stability is the point — the shape does not change between calls."),
        ],
        "ilgili": [("Compared with Nanonets", "/alternatives/nanonets"),
                   ("Compared with Mindee", "/alternatives/mindee")],
    },
]

STIL = ""  # CSS artik public/style.css icinde (tek kaynak)

LOGO = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
        '<path d="M6 2h8l4 4v16H6z" stroke="#4ade80" stroke-width="1.8" stroke-linejoin="round"/>'
        '<path d="M14 2v4h4" stroke="#4ade80" stroke-width="1.8" stroke-linejoin="round"/>'
        '<path d="M9 12h6M9 16h4" stroke="#38bdf8" stroke-width="1.8" stroke-linecap="round"/></svg>')

NAV = f"""<header><div class="wrap"><nav>
  <a class="brand" href="/">{LOGO} Fieldcast</a>
  <a href="/#how">How it works</a>
  <a href="/#pricing">Pricing</a>
  <a href="/for/">Use cases</a>
  <a href="/alternatives/">Comparisons</a>
</nav></div></header>"""


def sayfa(s):
    alanlar = json.dumps(s["alanlar"], indent=2).replace("\n", "\n  ")
    cikti = json.dumps(s["cikti"], indent=2)
    onem = "\n".join(
        '  <h3>%s</h3>\n  <p class="muted">%s</p>' % (html.escape(b), g)
        for b, g in s["neden_onemli"]
    )
    yapmaz = "\n".join("    <li>%s</li>" % html.escape(x) for x in s["yapmaz"])
    sss = "\n".join(
        "  <details><summary>%s</summary><p>%s</p></details>"
        % (html.escape(q), html.escape(a)) for q, a in s["sss"]
    )
    faq_ld = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in s["sss"]],
    }, ensure_ascii=False)
    ilgili = " · ".join('<a href="%s">%s</a>' % (u, html.escape(t)) for t, u in s["ilgili"])

    x402 = ""
    if s.get("x402_notu"):
        x402 = ('\n  <div class="box warn">\n    <h2>One thing that is not live yet</h2>\n'
                '    <p class="muted" style="margin:0">%s</p>\n  </div>\n' % s["x402_notu"])

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fieldcast for {html.escape(s['kisa'].lower())}</title>
<meta name="description" content="{html.escape(s['meta'])}">
<link rel="canonical" href="{CANLI}/for/{s['slug']}">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/logo.svg" type="image/svg+xml">
<meta property="og:title" content="Fieldcast for {html.escape(s['kisa'].lower())}">
<meta property="og:description" content="{html.escape(s['meta'])}">
<meta property="og:image" content="{CANLI}/logo-1024.png">
<meta property="og:type" content="article">
<link rel="stylesheet" href="/style.css">
</head>
<body>

{NAV}

<main class="wrap">

  <p class="note" style="margin:40px 0 0">{html.escape(s['kisa'])}</p>
  <h1>{html.escape(s['h1'])}</h1>
  <p class="lede">{html.escape(s['acilis'])}</p>
  <p>{s['nasil']}</p>

  <h2>What the call looks like</h2>
  <p class="note">The fields below are an example for this use case. Yours can be any names you like, up to 40 per call.</p>
<pre><code>{{
  "fields": {html.escape(alanlar)}
}}</code></pre>
  <p class="note">And what comes back:</p>
<pre><code>{html.escape(cikti)}</code></pre>

  <h2>Why the details matter here</h2>
{onem}
{x402}
  <div class="box">
    <h2>What it does not do</h2>
    <ul>
{yapmaz}
    </ul>
    <p class="note" style="margin:0">Listed plainly so you find out now rather than after integrating.</p>
  </div>

  <h2>Questions</h2>
{sss}

  <h2>Test it on your own documents</h2>
  <p class="muted">Free tier is 50 extractions a month, no card, no sales call. That is deliberately enough to check accuracy on real files before you commit to anything.</p>
  <a class="cta" href="/#how">Read the quickstart</a>
  <p class="note" style="margin-top:22px">{ilgili}</p>

</main>

<footer><div class="wrap">
  <p>Fieldcast — document extraction API. <a href="/">Home</a> · <a href="/for/">Use cases</a> · <a href="/alternatives/">Comparisons</a> · <a href="/privacy.html">Privacy</a> · <a href="/terms.html">Terms</a></p>
</div></footer>

<script type="application/ld+json">{faq_ld}</script>
</body>
</html>
"""


def dizin():
    kartlar = "\n".join(
        '  <li><a href="/for/%s">%s</a> — %s</li>'
        % (s["slug"], html.escape(s["kisa"]), html.escape(s["h1"]))
        for s in SENARYOLAR
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Who Fieldcast is for</title>
<meta name="description" content="How Fieldcast is used by bookkeeping teams, agencies building client integrations, and AI agent builders.">
<link rel="canonical" href="{CANLI}/for/">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="stylesheet" href="/style.css">
</head>
<body>
{NAV}
<main class="wrap">
  <h1>Who Fieldcast is for</h1>
  <p class="lede">Same endpoint in every case. What changes is the list of field names you send with the request.</p>
  <ul>
{kartlar}
  </ul>
  <p class="note">Each page includes a "what it does not do" section. Fieldcast is a beta with no OCR and no uptime guarantee, and it is better that you learn that here than after integrating.</p>
</main>
<footer><div class="wrap"><p>Fieldcast — document extraction API. <a href="/">Home</a> · <a href="/alternatives/">Comparisons</a> · <a href="/privacy.html">Privacy</a> · <a href="/terms.html">Terms</a></p></div></footer>
</body>
</html>
"""


if __name__ == "__main__":
    for s in SENARYOLAR:
        p = CIKTI / (s["slug"] + ".html")
        p.write_text(sayfa(s), encoding="utf-8")
        print("%-34s %6d bayt" % (p.relative_to(CIKTI.parent.parent), p.stat().st_size))
    p = CIKTI / "index.html"
    p.write_text(dizin(), encoding="utf-8")
    print("%-34s %6d bayt" % (p.relative_to(CIKTI.parent.parent), p.stat().st_size))
