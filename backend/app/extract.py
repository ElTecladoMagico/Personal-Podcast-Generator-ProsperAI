"""Download a story's article and extract its text (the scraping part of step 3), cached 48 h.

The cache is the `articles` table, shared by all users: two listeners with similar interests
never download the same page twice. Paywalls and blocks are not worked around: `ok=False`.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

import httpx
import trafilatura
from sqlmodel import Session

from app.models import Article
from app.sources import http, normalize_url, resolve_google_news

CACHE_FOR = timedelta(hours=48)
MAX_BYTES = 2_000_000
MIN_TEXT = 500  # below this it is a teaser, a paywall or a listing, not an article


def fetch_html(url: str) -> tuple[str, str] | None:
    """(final_url, html), or None if it is not a reachable HTML page under 2 MB."""
    try:
        with http.stream("GET", url) as r:
            if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
                return None
            body = b""
            for chunk in r.iter_bytes():
                body += chunk
                if len(body) > MAX_BYTES:
                    return None
            return str(r.url), body.decode(r.charset_encoding or "utf-8", errors="replace")
    except httpx.HTTPError:
        return None


def extract_text(html: str, url: str) -> Article:
    text = trafilatura.extract(html, url=url, favor_precision=True)
    meta = trafilatura.extract_metadata(html, default_url=url)
    ok = bool(text) and len(text) >= MIN_TEXT
    return Article(
        url=normalize_url(url),
        title=meta.title if meta else None,
        text=text if ok else None,
        image_url=meta.image if meta else None,
        ok=ok,
        fetched_at=datetime.now(UTC),
    )


def get_article(
    url: str,
    session: Session,
    fetch: Callable[[str], tuple[str, str] | None] = fetch_html,
    resolve: Callable[[str], str | None] = resolve_google_news,
) -> Article | None:
    """The article behind `url` (a Google News link is resolved first), or None if unusable."""
    if urlsplit(url).netloc == "news.google.com":
        url = resolve(url)
        if not url:
            return None
    key = normalize_url(url)  # cache key: the article URL we were asked for
    cached = session.get(Article, key)
    if cached and datetime.now(UTC) - cached.fetched_at < CACHE_FOR:
        return cached if cached.ok else None

    page = fetch(url)
    row = extract_text(page[1], page[0]) if page else Article(url=key, ok=False)
    row.url = key
    row = session.merge(row)
    session.commit()
    return row if row.ok else None
