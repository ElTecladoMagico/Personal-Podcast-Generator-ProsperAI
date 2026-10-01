"""Spike (plan 04): can Google News RSS links be resolved to the publisher URL and scraped?

Run: uv run --with feedparser --with trafilatura --with googlenewsdecoder \
         python scripts/spike_google_news.py
"""

import json
import re
import time
from urllib.parse import quote_plus

import feedparser
import httpx
import trafilatura
from googlenewsdecoder import gnewsdecoder

FEEDS = [
    ("inteligencia artificial", "es", "ES"),
    ("Real Madrid", "es", "ES"),
    ("vivienda", "es", "ES"),
    ("AI regulation", "en", "US"),
    ("Formula 1", "en", "US"),
    ("climate tech", "en", "US"),
]
PER_FEED = 10
MIN_TEXT = 1500
# "Consent already given" cookie: from the EU, Google redirects to consent.google.com otherwise.
SOCS = {"SOCS": "CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg"}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) Chrome/130 Safari/537.36"}


def feed_url(q: str, lang: str, country: str) -> str:
    return (
        f"https://news.google.com/rss/search?q={quote_plus(q)}+when:2d"
        f"&hl={lang}-{country}&gl={country}&ceid={country}:{lang}"
    )


def via_redirect(link: str) -> str | None:
    """a) plain HTTP redirects."""
    try:
        r = httpx.get(link, follow_redirects=True, timeout=10, headers=UA)
        return None if r.url.host.endswith("google.com") else str(r.url)
    except httpx.HTTPError:
        return None


def via_decoder(link: str) -> tuple[str | None, bool]:
    """b) googlenewsdecoder. Returns (url, rate_limited)."""
    try:
        r = gnewsdecoder(link)
    except Exception as err:  # the package raises plain exceptions
        return None, "429" in str(err)
    if r.get("status") or r.get("success"):
        return r["decoded_url"], False
    return None, "429" in str(r.get("message", ""))


def via_batchexecute(link: str, client: httpx.Client) -> str | None:
    """c) what the browser does: read the signature from the article page, then ask
    Google's batchexecute endpoint for the publisher URL. Needs the SOCS cookie."""
    try:
        art_id = link.split("/articles/")[1].split("?")[0]
        page = client.get(f"https://news.google.com/rss/articles/{art_id}").text
        sg = re.search(r'data-n-a-sg="([^"]+)"', page).group(1)
        ts = re.search(r'data-n-a-ts="([^"]+)"', page).group(1)
        req = (
            '["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,'
            f'null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{art_id}",{ts},"{sg}"]'
        )
        r = client.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            data={"f.req": json.dumps([[["Fbv4je", req, None, "generic"]]])},
        )
        return json.loads(json.loads(r.text.split("\n\n")[1])[0][2])[1]
    except (httpx.HTTPError, AttributeError, IndexError, ValueError, TypeError):
        return None


def extract_len(url: str) -> int:
    try:
        r = httpx.get(url, follow_redirects=True, timeout=15, headers=UA)
        text = trafilatura.extract(r.text, url=str(r.url)) or ""
        return len(text)
    except httpx.HTTPError:
        return 0


def main() -> None:
    rows = []
    client = httpx.Client(cookies=SOCS, follow_redirects=True, timeout=10, headers=UA)
    for q, lang, country in FEEDS:
        entries = feedparser.parse(feed_url(q, lang, country)).entries[:PER_FEED]
        print(f"\n## {q} ({lang}-{country}): {len(entries)} items")
        for e in entries:
            t0 = time.perf_counter()
            redirect = via_redirect(e.link)
            t_redirect = time.perf_counter() - t0
            t0 = time.perf_counter()
            decoded, limited = via_decoder(e.link)
            t_decode = time.perf_counter() - t0
            t0 = time.perf_counter()
            own = via_batchexecute(e.link, client)
            t_own = time.perf_counter() - t0
            url = own or decoded or redirect
            chars = extract_len(url) if url else 0
            row = (lang, bool(redirect), bool(decoded), limited, t_redirect, t_decode, chars)
            rows.append((*row, bool(own), t_own))
            source = e.get("source", {}).get("title", "?")
            status = f"{chars:>6} chars" if url else "  unresolved"
            flags = f"{'R' if redirect else '-'}{'D' if decoded else '-'}{'B' if own else '-'}"
            print(f"  {flags} {t_own:4.2f}s {status}  {source}")

    n = len(rows)
    resolved = sum(r[1] or r[2] or r[7] for r in rows)
    with_text = sum(r[6] >= MIN_TEXT for r in rows)
    print("\n## Summary")
    print(f"items: {n}")
    print(f"a) resolved by plain redirects: {sum(r[1] for r in rows)}/{n}")
    print(f"b) resolved by googlenewsdecoder: {sum(r[2] for r in rows)}/{n}")
    print(f"c) resolved by batchexecute + SOCS cookie: {sum(r[7] for r in rows)}/{n}")
    print(f"resolved (any): {resolved}/{n} = {resolved / n:.0%}")
    print(f"text >= {MIN_TEXT} chars: {with_text}/{n} = {with_text / n:.0%}")
    mean_b, mean_c = sum(r[5] for r in rows) / n, sum(r[8] for r in rows) / n
    print(f"mean time: b) {mean_b:.2f} s/item, c) {mean_c:.2f} s/item")
    print(f"rate limited (429): {sum(r[3] for r in rows)}")
    for lang in ("es", "en"):
        sub = [r for r in rows if r[0] == lang]
        ok, text = sum(r[7] for r in sub), sum(r[6] >= MIN_TEXT for r in sub)
        print(f"  {lang}: resolved {ok}/{len(sub)}, text {text}/{len(sub)}")


if __name__ == "__main__":
    main()
