"""Step 3 · Research: read the articles behind each chosen story (the scraping part, ADR 0006)."""

from collections.abc import Callable

from sqlmodel import Session

from app.extract import get_article
from app.models import Article as ArticleRow
from app.models import Episode
from app.pipeline.state import Work
from app.schemas import Article, Candidate, EditorSelection, Preferences, Usage

MIN_TEXT = 800  # a story needs at least one article this long, or a backup takes its place
MAX_TEXT = 6000  # per article, to keep the writer's prompt (and its cost) bounded
PER_STORY = 2  # articles from different outlets, so the hosts can compare coverage
MIN_STORIES = 2

Reader = Callable[[str], ArticleRow | None]


def article_for(candidate: Candidate, story_id: str, read: Reader) -> Article | None:
    """The candidate's article if it is long enough: Exa's text as-is, otherwise scraped."""
    if candidate.text:
        url, title, text, image = (
            candidate.url,
            candidate.title,
            candidate.text,
            candidate.image_url,
        )
    elif page := read(candidate.url):
        url, title, text, image = page.url, page.title or candidate.title, page.text, page.image_url
    else:
        return None
    if len(text) < MIN_TEXT:
        return None
    return Article(
        id="",
        story_id=story_id,
        url=url,
        source=candidate.source,
        title=title,
        text=text[:MAX_TEXT],
        image_url=image,
    )


def research(
    selection: EditorSelection,
    candidates: list[Candidate],
    read: Reader,
    minimum: int = MIN_STORIES,
) -> tuple[list[Article], list[str]]:
    """(articles a1..aN, story ids that made it). Backups replace stories we cannot read."""
    by_id = {c.id: c for c in candidates}
    wanted = len(selection.picks)
    articles: list[Article] = []
    stories: list[str] = []
    for pick in selection.picks + selection.backups:
        if len(stories) == wanted:
            break
        found: list[Article] = []
        outlets: set[str] = set()
        for c in (by_id[cid] for cid in pick.candidate_ids):
            if len(found) == PER_STORY:
                break
            if c.source not in outlets and (article := article_for(c, pick.story_id, read)):
                found.append(article)
                outlets.add(c.source)
        if found:
            stories.append(pick.story_id)
            articles += found
    if len(stories) < minimum:
        raise RuntimeError("Could not read enough articles for today's stories")
    for n, a in enumerate(articles, start=1):
        a.id = f"a{n}"
    return articles, stories


def step(ep: Episode, prefs: Preferences, work: Work, session: Session) -> Usage:
    work.articles, work.stories = research(
        work.selection, work.candidates, lambda url: get_article(url, session)
    )
    return Usage()
