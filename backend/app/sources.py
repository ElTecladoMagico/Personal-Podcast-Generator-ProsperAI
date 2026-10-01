"""Pipeline step 1: candidate stories from Google News RSS, Exa and Hacker News (ADR 0006)."""

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.schemas import Candidate

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
