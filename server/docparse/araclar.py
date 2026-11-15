"""Fieldcast yardimci araclari: cron sonraki calismalar + link durum denetimi.

Fikir prototiplerinden (fikir_isleri) uyarlandi; x402 gecidinin arkasinda,
gateway anahtariyla korunur. Calistir: python araclar.py  (self-check)
"""
import ipaddress
import socket
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse

from cron_arac import cron_coz  # fikir_isleri/sysadmin-...-cron-job-zama.py kopyasi

MAX_RUNS = 50
MAX_URLS = 25
MAX_HOPS = 5
TIMEOUT = 6


def _gun_eslesir(c, gun):
    if gun.month not in c["ay"]:
        return False
    dom = gun.day in c["gun"]
    dow = gun.weekday() in c["hafta_gunu"]
    if c["gun_serbest"] and c["hafta_gunu_serbest"]:
        return True
    if c["gun_serbest"]:
        return dow
    if c["hafta_gunu_serbest"]:
        return dom
    return dom or dow


def cron_next(ifade, count=10, start=None):
    """UTC'de start'tan sonraki ilk `count` calisma zamani (ISO)."""
    c = cron_coz(ifade)  # gecersizse ValueError
    count = max(1, min(int(count), MAX_RUNS))
    start = (start or datetime.now(timezone.utc)).replace(second=0, microsecond=0)
    saatler, dakikalar = sorted(c["saat"]), sorted(c["dakika"])
    runs, gun = [], start.date()
    for _ in range(366 * 5):  # ponytail: 5 yil tarama; 29 Subat gibi seyrek ifadeler icin yeter
        if _gun_eslesir(c, gun):
            for h in saatler:
                for m in dakikalar:
                    t = datetime(gun.year, gun.month, gun.day, h, m, tzinfo=timezone.utc)
                    if t > start:
                        runs.append(t.isoformat().replace("+00:00", "Z"))
                        if len(runs) == count:
                            return runs
        gun += timedelta(days=1)
    if not runs:
        raise ValueError("cron expression never fires")
    return runs


def _guvenli_mi(url):
    """SSRF kalkani: yalniz http(s) ve sadece genel (public) IP'lere cozulen hostlar."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    try:
        adresler = {a[4][0] for a in socket.getaddrinfo(p.hostname, p.port or 80)}
    except OSError:
        return False
    return all(ipaddress.ip_address(a.split("%")[0]).is_global for a in adresler)


def link_check(url, getir=None):
    """Yonlendirmeleri tek tek (her hop SSRF kontrolunden gecerek) izler."""
    if getir is None:
        import requests

        def getir(u):
            r = requests.get(u, timeout=TIMEOUT, stream=True, allow_redirects=False,
                             headers={"User-Agent": "fieldcast-linkcheck/1.0"})
            r.close()
            return r.status_code, r.headers.get("Location")

    hops, cur = 0, url
    while True:
        if not _guvenli_mi(cur):
            return {"url": url, "ok": False, "status": None, "error": "blocked_or_unresolvable", "final_url": cur}
        try:
            status, loc = getir(cur)
        except Exception as exc:
            return {"url": url, "ok": False, "status": None, "error": type(exc).__name__, "final_url": cur}
        if 300 <= status < 400 and loc and hops < MAX_HOPS:
            cur, hops = urljoin(cur, loc), hops + 1
            continue
        return {"url": url, "ok": 200 <= status < 400, "status": status, "redirects": hops, "final_url": cur}


def register(app, yetkili):
    """docparse_app'e iki ucu ekler. yetkili(request) -> hata yaniti ya da None."""
    from flask import jsonify, request

    @app.post("/v1/cron-next")
    def cron_next_ucu():
        hata = yetkili(request)
        if hata:
            return hata
        body = request.get_json(silent=True) or {}
        try:
            start = body.get("from")
            start = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(timezone.utc) if start else None
            runs = cron_next(body.get("cron"), body.get("count", 10), start)
        except (ValueError, TypeError, AttributeError) as exc:
            return jsonify({"error": "invalid_cron", "detail": str(exc)[:200]}), 400
        return jsonify({"cron": " ".join(body["cron"].split()), "timezone": "UTC", "next_runs": runs})

    @app.post("/v1/link-check")
    def link_check_ucu():
        hata = yetkili(request)
        if hata:
            return hata
        urls = (request.get_json(silent=True) or {}).get("urls")
        if not isinstance(urls, list) or not urls or len(urls) > MAX_URLS or not all(isinstance(u, str) for u in urls):
            return jsonify({"error": "invalid_urls", "detail": "urls must be a list of 1-%d strings" % MAX_URLS}), 400
        sonuc = [link_check(u.strip()) for u in urls]
        return jsonify({"checked": len(sonuc), "broken": sum(not s["ok"] for s in sonuc), "results": sonuc})


if __name__ == "__main__":
    s = datetime(2026, 11, 15, 10, 0, tzinfo=timezone.utc)
    assert cron_next("30 2 * * *", 2, s) == ["2026-11-16T02:30:00Z", "2026-11-17T02:30:00Z"]
    assert cron_next("0 9 * * 1", 1, s) == ["2026-11-16T09:00:00Z"]  # 16 Kas 2026 Pazartesi
    assert cron_next("0 0 29 2 *", 1, s) == ["2028-02-29T00:00:00Z"]
    for bozuk in ("61 * * * *", "* * *", None):
        try:
            cron_next(bozuk)
            raise AssertionError(bozuk)
        except (ValueError, TypeError):
            pass
    for ic in ("http://127.0.0.1:8010/", "http://localhost/", "http://10.0.0.1/", "http://169.254.169.254/", "file:///etc/passwd"):
        assert link_check(ic, getir=lambda u: (200, None))["error"] == "blocked_or_unresolvable", ic
    # dis -> ic yonlendirme engellenir
    yol = {"http://1.1.1.1/": (302, "http://127.0.0.1/admin")}
    r = link_check("http://1.1.1.1/", getir=lambda u: yol[u])
    assert r["error"] == "blocked_or_unresolvable" and r["final_url"] == "http://127.0.0.1/admin"
    assert link_check("http://1.1.1.1/", getir=lambda u: (404, None))["ok"] is False
    print("ok")
