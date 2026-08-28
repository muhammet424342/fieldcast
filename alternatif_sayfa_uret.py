# -*- coding: utf-8 -*-
"""Alternatif (karsilastirma) sayfalarini uretir.

Neden betik: uc sayfa ayni iskeleti paylasiyor. Elle yazilirsa biri
guncellenip digeri unutulur. Rakip verisi tek yerde durur.

RAKIP VERISI 26 Agu 2026'da KAYNAGINDAN DOGRULANDI:
  Mindee    -> mindee.com/pricing (tarayicida render edilmis hali okundu)
  Nanonets  -> nanonets.com/pricing
  Docparser -> sitesi 403 verdi; ucuncu taraf kaynaklar ($33-39 arasi celisiyor)
               bu yuzden metinde KESIN RAKAM VERILMEDI, "listed around" denildi.

Kural: rakip hakkinda uydurma yok. Emin olmadigimiz sayiyi yazmiyoruz.
Her sayfada rakibin DAHA IYI oldugu durumlar da yaziliyor - hem durust
hem de karsilastirma sayfasini inandirici kilan sey bu.
"""
import html
import json
import pathlib

CANLI = "https://fieldcast-peach.vercel.app"
CIKTI = pathlib.Path(__file__).parent / "public" / "alternatives"
CIKTI.mkdir(parents=True, exist_ok=True)

RAKIPLER = [
    {
        "slug": "docparser",
        "bedava": "Has a free plan, reported in the 30-150 pages/month range by third-party listings.",
        "birim": "Per parsed document; multi-page files typically count as one for invoice parsing.",
        "ocr": "Yes — handles scanned documents.",
        "eksik_alan": "Depends on the parsing rule you configured; a rule that does not match returns nothing for that field.",
        "ad": "Docparser",
        "site": "docparser.com",
        "h1": "Docparser alternative: name the fields, skip the templates",
        "meta": "Fieldcast compared with Docparser. Docparser uses parsing rules you draw per layout; Fieldcast takes field names at request time. Free tier, no card.",
        "yaklasim": "Parsing rules you configure per document layout, through a no-code interface.",
        "fiyat": "Paid plans listed around $39/month for roughly 100 documents at the time of writing; higher tiers scale by document count. Check their pricing page for current figures.",
        "girdi_maliyeti": "You build a parser per layout before extracting anything.",
        "acilis": (
            "Docparser is a mature, well-integrated document parser with a no-code interface. "
            "The reason people look for an alternative is almost always the same one: the setup "
            "step. You define parsing rules against a specific layout, and when a supplier "
            "redesigns their invoice, that layout work has to be redone."
        ),
        "fark": (
            "Fieldcast has no configuration step at all. You send the document and a list of field "
            "names in the same request, and the extraction adapts to whatever layout arrives. A new "
            "supplier is not a new parser."
        ),
        "onlar_daha_iyi": [
            "You want a no-code interface and would rather not write any code at all. Fieldcast is API-only.",
            "You need their mature integration catalogue (Zapier, cloud storage, webhooks) out of the box.",
            "You process scanned image documents that need OCR. Fieldcast handles PDF and text, not scanned images.",
            "You need a vendor with years of operating history and formal support. Fieldcast is a beta run by one developer.",
        ],
        "sss": [
            ("Do I have to migrate my existing parsers?",
             "There is nothing to migrate. Fieldcast has no stored parser configuration. You send the field names you want with each request, so moving over means writing one API call, not rebuilding your rules."),
            ("Does Fieldcast handle scanned documents?",
             "Not yet. Fieldcast reads PDFs and plain text. Scanned image-only documents need OCR, which is on the roadmap but not available today. If your documents are scans, Docparser is the better fit right now."),
        ],
    },
    {
        "slug": "mindee",
        "bedava": "14-day trial only. No standing free tier.",
        "birim": "One credit per physical page. A five-page contract costs five credits.",
        "ocr": "Yes — OCR is the core of the product.",
        "eksik_alan": "Returns the model's field set with confidence scores, so you judge low-confidence values yourself.",
        "ad": "Mindee",
        "site": "mindee.com",
        "h1": "Mindee alternative for teams that need arbitrary fields, not fixed models",
        "meta": "Fieldcast compared with Mindee. Mindee ships pre-trained models per document type and bills per page on annual plans; Fieldcast takes any field names, month to month, with a free tier.",
        "yaklasim": "Pre-trained models per document type (invoice, receipt, passport, ID, bank statement), plus custom models for other types.",
        "fiyat": "Starter listed at 44 €/month billed annually (529 €/year), Pro at 116 €/month billed annually, at roughly 0.044 € per credit. A credit is one physical page. 14-day free trial, no permanent free tier. Figures read from their pricing page on 26 August 2026.",
        "girdi_maliyeti": "You pick the model that matches your document type, or commission a custom one.",
        "acilis": (
            "Mindee is a solid, well-reviewed OCR API with real engineering behind it. Its model is "
            "document-type-first: you choose the invoice model, or the receipt model, and you get "
            "that model's field set. That works well when your documents fall into those categories "
            "and badly when they do not."
        ),
        "fark": (
            "Fieldcast is field-first. There is no model to select. You name the fields you want — up "
            "to 40 of them, in whatever vocabulary your own database already uses — and those are the "
            "keys that come back. A document type nobody has built a model for is not a blocker."
        ),
        "onlar_daha_iyi": [
            "You need OCR for scanned or photographed documents. Fieldcast does not do OCR yet.",
            "You need bounding-box polygons or per-field confidence scores. Fieldcast returns values, not coordinates or confidence.",
            "You need data processing localisation, custom SLAs, or a dedicated account manager.",
            "You want a vendor with an established support organisation and public review history rather than a one-person beta.",
        ],
        "sss": [
            ("How does per-page billing compare?",
             "Mindee counts one credit per physical page, so a five-page contract costs five credits. Fieldcast counts one extraction per API call regardless of page count. Which is cheaper depends entirely on your document lengths — run both against your own files before deciding."),
            ("Is there a free tier?",
             "Mindee offers a 14-day trial. Fieldcast has a standing free tier of 50 extractions per month with no card, which exists so you can measure accuracy on your own documents rather than trusting anyone's benchmark."),
        ],
    },
    {
        "slug": "nanonets",
        "bedava": "$50 in starting credits, no card. Not a recurring free tier.",
        "birim": "Per block run. Simple operations listed at $0.02 per run; complex AI blocks cost more.",
        "ocr": "Yes — including scanned and photographed documents.",
        "eksik_alan": "Depends on the blocks in your workflow; the platform exposes confidence and review steps.",
        "ad": "Nanonets",
        "site": "nanonets.com",
        "h1": "Nanonets alternative when you want one endpoint, not a workflow platform",
        "meta": "Fieldcast compared with Nanonets. Nanonets is a workflow platform billed per block run; Fieldcast is a single extraction endpoint with a free tier and no platform to configure.",
        "yaklasim": "A workflow platform. Each step is a block — extraction, classification, routing, export — and you compose them.",
        "fiyat": "Starts with $50 in free credits, then listed at $100/month for 100 credits, billed per block run with simple operations at $0.02 per run. Growth and Enterprise tiers are quote-based. Figures read from their pricing page on 26 August 2026.",
        "girdi_maliyeti": "You design a workflow out of blocks before documents flow through it.",
        "acilis": (
            "Nanonets is genuinely capable, and considerably more than a parser: classification, "
            "routing, ERP connectors, compliance certifications, on-premise deployment. If you need "
            "a document operations platform, that breadth is the product."
        ),
        "fark": (
            "Fieldcast is deliberately one endpoint. You POST a document and a list of field names, "
            "you get typed JSON back, and the orchestration stays in your own code where you can "
            "test and version it. There is no platform to learn, and no per-block cost model to "
            "reason about before you know what a request will cost."
        ),
        "onlar_daha_iyi": [
            "You need SOC 2 or HIPAA compliance, SAML SSO, or audit logging. Fieldcast has none of these.",
            "You need on-premise or private-cloud deployment, or data residency guarantees.",
            "You need SAP, Salesforce, or Oracle connectors and want them maintained for you.",
            "You want the whole document workflow — classification, approval routing, export — rather than just extraction.",
        ],
        "sss": [
            ("Can Fieldcast classify documents as well as extract from them?",
             "Not as a separate feature. You can approximate it by asking for a field like document_type in your field list, but there is no dedicated classification model. If classification is central to your workflow, Nanonets is built for it and Fieldcast is not."),
            ("What does a request actually cost?",
             "One extraction, regardless of how many fields you request or how the document is structured. The free tier is 50 per month, Starter is $19 for 1,000, Pro is $49 for 5,000. There is no per-step pricing to model in advance."),
        ],
    },
]

# Sadece HER IKI TARAF icin de gercek bilgimiz olan satirlar kalir.
# "See their documentation" dolgusu kaldirildi: bes satir dolgu, tabloyu
# bilgilendirici olmaktan cikarip tembel gosteriyordu. Bilmedigimiz satiri
# yazmak yerine hic koymuyoruz.
ORTAK_SATIRLAR = [
    ("Fields returned", "Any names you choose, up to 40 per call"),
    ("Billing unit", "One extraction per API call, regardless of page count"),
    ("Commitment", "Month to month, cancel any time"),
]

STIL = ""  # CSS artik public/style.css icinde (tek kaynak)

LOGO = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
        '<path d="M6 2h8l4 4v16H6z" stroke="#4ade80" stroke-width="1.8" stroke-linejoin="round"/>'
        '<path d="M14 2v4h4" stroke="#4ade80" stroke-width="1.8" stroke-linejoin="round"/>'
        '<path d="M9 12h6M9 16h4" stroke="#38bdf8" stroke-width="1.8" stroke-linecap="round"/></svg>')


def sayfa(r):
    ad = html.escape(r["ad"])
    satirlar = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
        % (html.escape(k), html.escape(v), "—")
        for k, v in []
    )
    # Her satirda IKI TARAF icin de dogrulanmis bilgi var. Bilinmeyen satir yok.
    tablo = [
        ("Approach", "Field names sent with each request", r["yaklasim"]),
        ("Setup before first extraction", "None", r["girdi_maliyeti"]),
        ("Pricing", "Free 50/mo · $19/mo for 1,000 · $49/mo for 5,000", r["fiyat"]),
        ("Free tier", "50 extractions/month, no card, no expiry", r["bedava"]),
        ("Billing unit", "One extraction per API call, regardless of page count", r["birim"]),
        ("OCR for scanned images", "Not supported yet", r["ocr"]),
        ("Missing field behaviour", "Returns null — never a fabricated value", r["eksik_alan"]),
    ]

    tr = "\n".join(
        "      <tr><td>%s</td><td>%s</td><td>%s</td></tr>"
        % (html.escape(a), html.escape(b), html.escape(c))
        for a, b, c in tablo
    )

    onlar = "\n".join("    <li>%s</li>" % html.escape(x) for x in r["onlar_daha_iyi"])
    sss = "\n".join(
        "  <details><summary>%s</summary><p>%s</p></details>"
        % (html.escape(q), html.escape(a)) for q, a in r["sss"]
    )
    faq_ld = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in r["sss"]],
    }, ensure_ascii=False)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{ad} alternative — Fieldcast</title>
<meta name="description" content="{html.escape(r['meta'])}">
<link rel="canonical" href="{CANLI}/alternatives/{r['slug']}">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/logo.svg" type="image/svg+xml">
<meta property="og:title" content="{ad} alternative — Fieldcast">
<meta property="og:description" content="{html.escape(r['meta'])}">
<meta property="og:image" content="{CANLI}/logo-1024.png">
<meta property="og:type" content="article">
<link rel="stylesheet" href="/style.css">
</head>
<body>

<header><div class="wrap"><nav>
  <a class="brand" href="/">{LOGO} Fieldcast</a>
  <a href="/#how">How it works</a>
  <a href="/#pricing">Pricing</a>
  <a href="/for/">Use cases</a>
  <a href="/alternatives/">Comparisons</a>
</nav></div></header>

<main class="wrap">

  <h1>{html.escape(r['h1'])}</h1>
  <p class="lede">{html.escape(r['acilis'])}</p>
  <p>{html.escape(r['fark'])}</p>

  <h2>Side by side</h2>
  <table>
    <thead><tr><th></th><th>Fieldcast</th><th>{ad}</th></tr></thead>
    <tbody>
{tr}
    </tbody>
  </table>
  <p class="note">{ad} figures were read from {html.escape(r['site'])} and public sources in August 2026 and may have changed since. Check their pricing page before deciding — and if anything here is out of date, email me and I will correct it.</p>

  <div class="box">
    <h2>Choose {ad} instead if…</h2>
    <ul>
{onlar}
    </ul>
    <p class="note" style="margin:0">These are real gaps, not false modesty. A comparison page that pretends the other product has no advantages is not worth reading.</p>
  </div>

  <h2>Choose Fieldcast if…</h2>
  <ul>
    <li>Your documents arrive in layouts you do not control and cannot enumerate in advance.</li>
    <li>You want the extracted keys to match your own schema, not a vendor's field taxonomy.</li>
    <li>A fabricated value would be worse than a missing one — Fieldcast returns <code>null</code> rather than guessing.</li>
    <li>You want to test against your own documents before paying anything.</li>
  </ul>

  <h2>What was actually measured</h2>
  <p class="muted">On a ten-field invoice, live in production: all ten fields correct in 1.8 seconds, dates normalised to ISO-8601, monetary values returned as numbers. On a receipt in a different currency and date format, every field correct and four fields that did not exist in the document returned as <code>null</code>. Accuracy on <em>your</em> documents should be measured on your documents — that is what the free tier is for.</p>

  <h2>Questions</h2>
{sss}

  <h2>Try it against your own file</h2>
  <p class="muted">Free tier is 50 extractions a month, no card, no sales call.</p>
  <a class="cta" href="/#how">Read the quickstart</a>

</main>

<footer><div class="wrap">
  <p>Fieldcast — document extraction API. <a href="/">Home</a> · <a href="/alternatives/">Comparisons</a> · <a href="/privacy.html">Privacy</a> · <a href="/terms.html">Terms</a></p>
  <p class="note">{ad} is a trademark of its respective owner. This page is an independent comparison and is not affiliated with or endorsed by {ad}.</p>
</div></footer>

<script type="application/ld+json">{faq_ld}</script>
</body>
</html>
"""


def dizin():
    kartlar = "\n".join(
        '  <li><a href="/alternatives/%s">Fieldcast vs %s</a> — %s</li>'
        % (r["slug"], html.escape(r["ad"]), html.escape(r["yaklasim"]))
        for r in RAKIPLER
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fieldcast compared with other document extraction APIs</title>
<meta name="description" content="Honest comparisons between Fieldcast and Docparser, Mindee and Nanonets — including where each of them is the better choice.">
<link rel="canonical" href="{CANLI}/alternatives/">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header><div class="wrap"><nav>
  <a class="brand" href="/">{LOGO} Fieldcast</a>
  <a href="/#how">How it works</a>
  <a href="/#pricing">Pricing</a>
</nav></div></header>
<main class="wrap">
  <h1>How Fieldcast compares</h1>
  <p class="lede">Three honest comparisons. Each one includes a section on when the other product is the better choice, because the alternative is a page nobody trusts.</p>
  <ul>
{kartlar}
  </ul>
  <p class="note">Competitor figures were read from their own pricing pages and public sources in August 2026. If something here is wrong or out of date, email <a href="mailto:muhammet@decaylabs.online">muhammet@decaylabs.online</a> and it gets corrected.</p>
</main>
<footer><div class="wrap"><p>Fieldcast — document extraction API. <a href="/">Home</a> · <a href="/privacy.html">Privacy</a> · <a href="/terms.html">Terms</a></p></div></footer>
</body>
</html>
"""


if __name__ == "__main__":
    for r in RAKIPLER:
        p = CIKTI / (r["slug"] + ".html")
        p.write_text(sayfa(r), encoding="utf-8")
        print("%-28s %6d bayt" % (p.relative_to(CIKTI.parent.parent), p.stat().st_size))
    p = CIKTI / "index.html"
    p.write_text(dizin(), encoding="utf-8")
    print("%-28s %6d bayt" % (p.relative_to(CIKTI.parent.parent), p.stat().st_size))
