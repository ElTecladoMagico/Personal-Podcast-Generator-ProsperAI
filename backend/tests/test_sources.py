from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.schemas import Candidate
from app.sources import (
    dedupe,
    google_news_feed_url,
    normalize_title,
    normalize_url,
    parse_article_signature,
    parse_batchexecute,
    parse_google_news,
)

FIXTURES = Path(__file__).parent / "fixtures"


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


# --- Google News -------------------------------------------------------------


def test_google_news_feed_url_uses_language_edition():
    since = datetime(2026, 9, 28, tzinfo=UTC)
    url = google_news_feed_url("vivienda", "es", since, now=datetime(2026, 10, 1, tzinfo=UTC))
    assert url.startswith("https://news.google.com/rss/search?")
    assert "q=vivienda+when%3A3d" in url and "hl=es-ES" in url and "ceid=ES%3Aes" in url
    other = google_news_feed_url("x", "sv", since, now=datetime(2026, 10, 1, tzinfo=UTC))
    assert "hl=en-US" in other  # unknown language → English edition


def test_parse_google_news_strips_source_suffix_and_filters_by_date():
    xml = (FIXTURES / "google_news_es.xml").read_bytes()
    since = datetime(2026, 10, 1, 13, 0, tzinfo=UTC)  # drops the 11:29 item
    items = parse_google_news(xml, "vivienda", since)

    assert len(items) == 4
    first = items[0]
    assert first.title.startswith("Junts se aleja de los dos decretos")
    assert not first.title.endswith("El Mundo")
    assert first.source == "El Mundo"
    assert first.origin == "google_news" and first.interest == "vivienda"
    assert first.url.startswith("https://news.google.com/rss/articles/")
    assert first.published_at == datetime(2026, 10, 1, 13, 1, 48, tzinfo=UTC)


def test_resolver_parses_signature_and_batchexecute_reply():
    sg, ts = parse_article_signature((FIXTURES / "google_article_page.html").read_text())
    assert sg and ts.isdigit()
    url = parse_batchexecute((FIXTURES / "google_batchexecute.txt").read_text())
    assert url == (
        "https://www.lamoncloa.gob.es/serviciosdeprensa/notasprensa/vivienda-agenda-urbana"
        "/Paginas/2026/decreto-vivienda-medidas.aspx"
    )
    assert parse_article_signature("<html>consent wall</html>") is None
    assert parse_batchexecute(")]}'\n\nnot json") is None


@pytest.mark.live
def test_live_google_news_link_resolves_to_publisher():
    from app.sources import fetch_google_news, resolve_google_news

    since = datetime.now(UTC).replace(hour=0, minute=0)
    items = fetch_google_news("Formula 1", "en", since)
    assert items, "Google News returned nothing"
    url = resolve_google_news(items[0].url)
    assert url and "google.com" not in url
