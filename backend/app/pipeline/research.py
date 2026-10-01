"""Step 3 · Research: read the articles behind each chosen story (the scraping part, ADR 0006)."""

from collections.abc import Callable

from sqlmodel import Session

from app.extract import get_article
from app.models import Article as ArticleRow
from app.models import Episode
from app.pipeline.run import save_work
from app.schemas import Article, Candidate, EditorSelection, Preferences

MIN_TEXT = 800  # a story needs at least one article this long, or a backup takes its place
MAX_TEXT = 6000  # per article, to keep the writer's prompt (and its cost) bounded
PER_STORY = 2  # articles from different outlets, so the hosts can compare coverage
MIN_STORIES = 2


def research(
    selection: EditorSelection,
    candidates: list[Candidate],
    read: Callable[[str], ArticleRow | None],
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
        for cid in pick.candidate_ids:
            c = by_id[cid]
            if c.source in outlets:
                continue
            if c.text:
                url, title, text, image = c.url, c.title, c.text, c.image_url
            elif page := read(c.url):
                url, title, text, image = page.url, page.title or c.title, page.text, page.image_url
            else:
                continue
            if len(text) < MIN_TEXT:
                continue
            found.append(
                Article(
                    id="",
                    story_id=pick.story_id,
                    url=url,
                    source=c.source,
                    title=title,
                    text=text[:MAX_TEXT],
                    image_url=image,
                )
            )
            outlets.add(c.source)
            if len(found) == PER_STORY:
                break
        if found:
            stories.append(pick.story_id)
            articles += found
    if len(stories) < minimum:
        raise RuntimeError("Could not read enough articles for today's stories")
    for n, a in enumerate(articles, start=1):
        a.id = f"a{n}"
    return articles, stories


def step(ep: Episode, prefs: Preferences, session: Session) -> None:
    selection = EditorSelection.model_validate(ep.work["selection"])
    candidates = [Candidate.model_validate(c) for c in ep.work["candidates"]]
    articles, stories = research(selection, candidates, lambda url: get_article(url, session))
    save_work(ep, "articles", [a.model_dump() for a in articles])
    save_work(ep, "stories", stories)
