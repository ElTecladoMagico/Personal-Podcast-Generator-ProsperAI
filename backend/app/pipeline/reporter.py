"""Step 1 · Reporter: candidate stories from every source (app.sources)."""

from datetime import UTC, datetime, timedelta

from sqlmodel import Session, func, select

from app.models import Episode
from app.pipeline.state import Work
from app.schemas import Preferences, Usage
from app.sources import gather_candidates

MIN_CANDIDATES = 5


def news_window_start(last_ready: datetime | None, prefs: Preferences, now: datetime) -> datetime:
    """News since the last episode, but never less than 1 day nor more than the default window."""
    default = timedelta(days=8 if prefs.schedule.frequency == "weekly" else 2)
    since = last_ready or now - default
    return min(max(since, now - default), now - timedelta(days=1))


def step(ep: Episode, prefs: Preferences, work: Work, session: Session) -> Usage:
    last_ready = session.exec(
        select(func.max(Episode.finished_at)).where(
            Episode.user_id == ep.user_id, Episode.status == "ready"
        )
    ).one()
    since = news_window_start(last_ready, prefs, datetime.now(UTC))
    work.candidates = gather_candidates(prefs, since)
    if len(work.candidates) < MIN_CANDIDATES:
        raise RuntimeError("No recent news found about your interests")
    return Usage()
