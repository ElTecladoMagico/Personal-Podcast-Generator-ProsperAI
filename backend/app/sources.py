"""Pipeline step 1: candidate stories from Google News RSS, Exa and Hacker News (ADR 0006)."""

import calendar
import json
import math
import re
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import httpx

from app.config import settings
from app.schemas import Candidate

USER_AGENT = "PersonalPodcastBot/1.0 (+https://podcast.scuda.es)"
http = httpx.Client(timeout=10, follow_redirects=True, headers={"User-Agent": USER_AGENT})

TRACKING_PARAMS = {"fbclid", "gclid"}


def normalize_url(url: str) -> str:
    """Same article, same key: lowercase host, no tracking params, fragment or trailing slash."""
    parts = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query)
        if not k.startswith("utm_") and k not in TRACKING_PARAMS
    ]
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc.lower(), path, urlencode(query), ""))


def normalize_title(title: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", "", title.lower()).split())


def dedupe(candidates: list[Candidate]) -> list[Candidate]:
    """Drop repeats by normalized URL or normalized title; the first one wins."""
    seen: set[str] = set()
    unique = []
    for c in candidates:
        keys = {normalize_url(c.url), normalize_title(c.title)}
        if keys & seen:
            continue
        seen |= keys
        unique.append(c)
    return unique


# --- Google News RSS ------------------------------------------------------------

EDITIONS = {"es": "ES", "en": "US", "fr": "FR", "de": "DE", "it": "IT", "pt": "BR"}


def google_news_feed_url(interest: str, lang: str, since: datetime, now: datetime | None = None):
    days = max(1, math.ceil(((now or datetime.now(UTC)) - since).total_seconds() / 86400))
    if lang not in EDITIONS:
        lang = "en"
    country = EDITIONS[lang]
    params = {
        "q": f"{interest} when:{days}d",
        "hl": f"{lang}-{country}",
        "gl": country,
        "ceid": f"{country}:{lang}",
    }
    return "https://news.google.com/rss/search?" + urlencode(params)


def parse_google_news(xml: bytes, interest: str, since: datetime) -> list[Candidate]:
    candidates = []
    for e in feedparser.parse(xml).entries:
        parsed = e.get("published_parsed")
        published = datetime.fromtimestamp(calendar.timegm(parsed), UTC) if parsed else None
        if published and published < since:
            continue
        source = e.get("source", {}).get("title") or ""
        candidates.append(
            Candidate(
                id="",
                title=e.title.removesuffix(f" - {source}") if source else e.title,
                source=source,
                url=e.link,  # news.google.com link; resolved only if the editor picks it
                published_at=published,
                snippet=None,
                origin="google_news",
                interest=interest,
            )
        )
    return candidates


def fetch_google_news(interest: str, lang: str, since: datetime, limit: int = 8):
    r = http.get(google_news_feed_url(interest, lang, since))
    r.raise_for_status()
    return parse_google_news(r.content, interest, since)[:limit]


# Google News links are encoded redirects. From the EU they land on a cookie consent wall,
# so we do what the browser does (spike 04): send the "consent given" cookie, read the
# article signature from its page and ask Google's batchexecute endpoint for the real URL.
# ponytail: internal Google endpoint, may change; the live test catches it, Exa/HN cover it.
SOCS_COOKIE = {"SOCS": "CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg"}
google = httpx.Client(timeout=10, follow_redirects=True, cookies=SOCS_COOKIE)
BATCHEXECUTE = "https://news.google.com/_/DotsSplashUi/data/batchexecute"


def parse_article_signature(html: str) -> tuple[str, str] | None:
    sg = re.search(r'data-n-a-sg="([^"]+)"', html)
    ts = re.search(r'data-n-a-ts="([^"]+)"', html)
    return (sg.group(1), ts.group(1)) if sg and ts else None


def parse_batchexecute(text: str) -> str | None:
    try:
        return json.loads(json.loads(text.split("\n\n")[1])[0][2])[1]
    except (IndexError, ValueError, TypeError):
        return None


def resolve_google_news(link: str) -> str | None:
    article_id = urlsplit(link).path.rsplit("/", 1)[-1]
    try:
        page = google.get(f"https://news.google.com/rss/articles/{article_id}")
        signature = parse_article_signature(page.text)
        if not signature:
            return None
        sg, ts = signature
        request = (
            '["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,'
            f'null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{article_id}",{ts},"{sg}"]'
        )
        reply = google.post(
            BATCHEXECUTE, data={"f.req": json.dumps([[["Fbv4je", request, None, "generic"]]])}
        )
        return parse_batchexecute(reply.text)
    except httpx.HTTPError:
        return None


# --- Exa (semantic search with full text; ADR 0006 "Cambio") ----------------------

MIN_TEXT = 500  # shorter pages (live blogs, teasers) get scraped in step 3 instead


def parse_exa(data: dict, interest: str) -> list[Candidate]:
    candidates = []
    for r in data.get("results", []):
        text = (r.get("text") or "").strip()
        published = r.get("publishedDate")
        candidates.append(
            Candidate(
                id="",
                title=r.get("title") or r["url"],
                source=urlsplit(r["url"]).netloc.removeprefix("www."),
                url=r["url"],
                published_at=datetime.fromisoformat(published) if published else None,
                snippet=text[:300] or None,
                origin="exa",
                interest=interest,
                text=text if len(text) >= MIN_TEXT else None,
            )
        )
    return candidates


def fetch_exa(interest: str, since: datetime, limit: int = 4) -> list[Candidate]:
    if not settings.exa_api_key:
        return []
    # Request shape follows Exa's build-with-exa guidance: only fields the product needs.
    body = {
        "query": f"latest news on {interest}",
        "type": "auto",
        "numResults": limit,
        "startPublishedDate": since.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "contents": {"text": {"maxCharacters": 6000}},
    }
    r = http.post(
        "https://api.exa.ai/search",
        json=body,
        headers={"x-api-key": settings.exa_api_key},
        timeout=20,
    )
    r.raise_for_status()
    return parse_exa(r.json(), interest)
