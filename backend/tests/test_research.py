import pytest

from app.models import Article as ArticleRow
from app.pipeline.research import research
from app.schemas import Candidate, EditorPick, EditorSelection

LONG = "x" * 900


def cand(cid: str, source: str, text: str | None = None) -> Candidate:
    return Candidate(
        id=cid,
        title=f"title {cid}",
        source=source,
        url=f"https://{source}/{cid}",
        published_at=None,
        snippet=None,
        origin="google_news",
        interest="AI",
        text=text,
        image_url=f"https://{source}/{cid}.jpg" if text else None,
    )


def pick(story_id: str, *cids: str) -> EditorPick:
    return EditorPick(
        story_id=story_id,
        headline=story_id,
        candidate_ids=list(cids),
        interest="AI",
        why_it_matters="w",
        follow_up_of=None,
    )


def reader(pages: dict[str, str]):
    calls = []

    def get(url: str):
        calls.append(url)
        text = pages.get(url)
        return (
            ArticleRow(url=url, title="Scraped", text=text, image_url="https://img/x.jpg", ok=True)
            if text
            else None
        )

    get.calls = calls
    return get


def test_takes_up_to_two_articles_from_different_outlets():
    cands = [
        cand("c1", "a.com", LONG),
        cand("c2", "a.com", LONG),
        cand("c3", "b.com"),
        cand("c4", "c.com"),
    ]
    get = reader({"https://b.com/c3": LONG, "https://c.com/c4": LONG})
    sel = EditorSelection(picks=[pick("s1", "c1", "c2", "c3", "c4")], backups=[])
    articles, stories = research(sel, cands, get, minimum=1)

    assert [a.url for a in articles] == ["https://a.com/c1", "https://b.com/c3"]  # c2: same outlet
    assert [a.id for a in articles] == ["a1", "a2"] and stories == ["s1"]
    assert articles[0].image_url == "https://a.com/c1.jpg"  # Exa text and image used directly
    assert get.calls == ["https://b.com/c3"]  # no download for the candidate that had text


def test_fails_clearly_when_not_enough_stories_can_be_read():
    # c1 unreadable, c3 too short: only s2 survives, below the minimum of 2
    cands = [cand("c1", "a.com"), cand("c2", "b.com", LONG), cand("c3", "c.com", "too short")]
    sel = EditorSelection(picks=[pick("s1", "c1"), pick("s2", "c2")], backups=[pick("s3", "c3")])
    with pytest.raises(RuntimeError, match="enough"):
        research(sel, cands, reader({}), minimum=2)


def test_backup_fills_the_gap_and_text_is_trimmed():
    cands = [cand("c1", "a.com"), cand("c2", "b.com", "y" * 9000), cand("c3", "c.com", LONG)]
    sel = EditorSelection(picks=[pick("s1", "c1"), pick("s2", "c2")], backups=[pick("s3", "c3")])
    articles, stories = research(sel, cands, reader({}), minimum=2)
    assert stories == ["s2", "s3"]
    assert len(articles[0].text) == 6000
