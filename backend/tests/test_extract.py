from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlmodel import Session

from app import extract
from app.db import engine
from app.models import Article

FIXTURES = Path(__file__).parent / "fixtures"
URL = "https://example.com/news/offices"


def test_extract_text_gets_body_title_and_image():
    row = extract.extract_text((FIXTURES / "article.html").read_text(), URL)
    assert row.ok and row.url == URL
    assert "420 rental homes" in row.text and len(row.text) >= extract.MIN_TEXT
    assert "Subscribe" not in row.text and "Home" not in row.text.split()[0]
    assert row.title == "Three empty office blocks will become 420 rental homes"
    assert row.image_url == "https://example.com/img/offices.jpg"


def test_extract_text_without_article_is_not_ok():
    row = extract.extract_text((FIXTURES / "no_article.html").read_text(), URL)
    assert row.ok is False and row.text is None


def fetch_fixture(calls: list):
    def fetch(url: str):
        calls.append(url)
        return url, (FIXTURES / "article.html").read_text()

    return fetch


def test_get_article_downloads_once_then_uses_the_cache():
    calls: list[str] = []
    with Session(engine) as s:
        first = extract.get_article(URL + "?utm_source=rss", s, fetch=fetch_fixture(calls))
        again = extract.get_article(URL, s, fetch=fetch_fixture(calls))
    assert first and again and first.text == again.text
    assert len(calls) == 1  # same normalized URL → cached


def test_stale_cache_is_refreshed_and_failures_are_remembered():
    calls: list[str] = []
    with Session(engine) as s:
        s.add(
            Article(url=URL, ok=True, text="old", fetched_at=datetime.now(UTC) - timedelta(days=3))
        )
        s.add(Article(url="https://paywall.test/x", ok=False, fetched_at=datetime.now(UTC)))
        s.commit()
        fresh = extract.get_article(URL, s, fetch=fetch_fixture(calls))
        blocked = extract.get_article("https://paywall.test/x", s, fetch=fetch_fixture(calls))
    assert fresh and fresh.text != "old" and calls == [URL]
    assert blocked is None  # failed recently: not retried for 48 h


def test_google_news_links_are_resolved_first_and_unresolvable_ones_skipped():
    calls: list[str] = []
    gn = "https://news.google.com/rss/articles/CBMiabc"
    with Session(engine) as s:
        got = extract.get_article(gn, s, fetch=fetch_fixture(calls), resolve=lambda _: URL)
        lost = extract.get_article(gn + "x", s, fetch=fetch_fixture(calls), resolve=lambda _: None)
    assert got and got.url == URL and calls == [URL]
    assert lost is None


def test_download_failure_returns_none_and_is_cached_as_not_ok():
    with Session(engine) as s:
        assert extract.get_article("https://down.test/a", s, fetch=lambda url: None) is None
        assert s.get(Article, "https://down.test/a").ok is False
