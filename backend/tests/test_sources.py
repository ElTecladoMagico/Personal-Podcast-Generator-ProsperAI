from datetime import UTC, datetime

import pytest

from app.schemas import Candidate
from app.sources import dedupe, normalize_title, normalize_url


def cand(url: str, title: str, **kw) -> Candidate:
    base = dict(
        id="",
        source="X",
        published_at=datetime(2026, 10, 1, tzinfo=UTC),
        snippet=None,
        origin="hn",
        interest="AI",
    )
    return Candidate(url=url, title=title, **(base | kw))


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("https://WWW.Example.com/a/?utm_source=x&id=7#top", "https://www.example.com/a?id=7"),
        ("https://example.com/a/?fbclid=1&gclid=2", "https://example.com/a"),
        ("https://example.com/", "https://example.com"),
    ],
)
def test_normalize_url_drops_tracking_fragment_and_trailing_slash(raw, clean):
    assert normalize_url(raw) == clean


def test_normalize_title_ignores_case_punctuation_and_spacing():
    title = "  ¡El Gobierno aprueba  el decreto!  "
    assert normalize_title(title) == "el gobierno aprueba el decreto"


def test_dedupe_by_url_or_title_keeps_first():
    items = [
        cand("https://a.com/x?utm_medium=rss", "Big news"),
        cand("https://a.com/x", "Other title"),  # same URL
        cand("https://b.com/y", "BIG NEWS!"),  # same title
        cand("https://c.com/z", "Different story"),
    ]
    assert [c.url for c in dedupe(items)] == ["https://a.com/x?utm_medium=rss", "https://c.com/z"]
