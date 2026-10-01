"""Episode orchestration (ADR 0009): six stages in order, each one resumable.

Every step reads the `work` of earlier stages and writes its own key, then commits. When a
step raises, the episode is left `failed` with `failed_stage`; a retry starts right there and
reuses everything before it.
"""

import logging
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlmodel import Session

from app.config import settings
from app.db import engine
from app.models import Episode, Event, Story, User
from app.schemas import Preferences, Script

log = logging.getLogger(__name__)

STAGES = ["fetching", "editing", "researching", "writing", "verifying", "recording"]
Step = Callable[[Episode, Preferences, Session], None]
STEPS: dict[str, Step] = {}  # filled by the step modules as they land


def new_episode(session: Session, user: User, trigger: str) -> Episode:
    prefs = Preferences.model_validate(user.preferences)
    ep = Episode(
        user_id=user.id,
        trigger=trigger,
        language=prefs.language,
        prefs_snapshot=prefs.model_dump(),
    )
    session.add(ep)
    session.flush()
    session.add(
        Event(
            user_id=user.id, type="episode_requested", episode_id=ep.id, props={"trigger": trigger}
        )
    )
    session.commit()
    return ep


def effective_minutes(prefs: Preferences) -> int:
    """EPISODE_MAX_MINUTES caps the length to save credits (2 in dev, 10 in prod)."""
    return min(prefs.duration_min, settings.episode_max_minutes)


def save_work(ep: Episode, key: str, value) -> None:
    ep.work = {**ep.work, key: value}  # reassign: SQLAlchemy only sees new JSONB objects


def add_cost(ep: Episode, usage: dict) -> None:
    cost = {"llm_usd": 0.0, "tts_chars": 0, "tokens": {"in": 0, "out": 0}} | ep.cost
    ep.cost = {
        "llm_usd": round(cost["llm_usd"] + usage.get("usd", 0), 6),
        "tts_chars": cost["tts_chars"] + usage.get("tts_chars", 0),
        "tokens": {
            "in": cost["tokens"]["in"] + usage.get("in", 0),
            "out": cost["tokens"]["out"] + usage.get("out", 0),
        },
    }


def generate_episode(episode_id: uuid.UUID, steps: dict[str, Step] | None = None) -> None:
    steps = steps or STEPS
    with Session(engine) as session:
        ep = session.get(Episode, episode_id)
        prefs = Preferences.model_validate(ep.prefs_snapshot)
        start = ep.failed_stage or STAGES[0]
        ep.failed_stage = ep.error = None
        ep.started_at = ep.started_at or datetime.now(UTC)

        for name in STAGES[STAGES.index(start) :]:
            ep.status = name
            session.commit()
            t0 = time.perf_counter()
            try:
                steps[name](ep, prefs, session)
            except Exception as err:  # any failure: record it, keep earlier work, stop
                log.exception("episode %s failed at %s", episode_id, name)
                session.rollback()
                fail(session, session.get(Episode, episode_id), name, err)
                return
            ep.stage_timings = {**ep.stage_timings, name: round(time.perf_counter() - t0, 1)}
            session.commit()

        finish(session, ep)


def fail(session: Session, ep: Episode, stage: str, err: Exception) -> None:
    error = str(err)[:300] or type(err).__name__
    ep.status, ep.failed_stage, ep.error = "failed", stage, error
    ep.finished_at = datetime.now(UTC)
    session.add(
        Event(
            user_id=ep.user_id,
            type="episode_failed",
            episode_id=ep.id,
            props={"stage": stage, "error": error},
        )
    )
    session.commit()


def finish(session: Session, ep: Episode) -> None:
    script = Script.model_validate(ep.script)
    ep.status, ep.title, ep.summary = "ready", script.title, script.summary
    ep.finished_at = datetime.now(UTC)

    # Memory for the editor (no repeats, follow-ups): one row per story chapter.
    picks = {p["story_id"]: p for p in ep.work.get("selection", {}).get("picks", [])}
    article_urls: dict[str, list[str]] = {}
    for a in ep.work.get("articles", []):
        article_urls.setdefault(a["story_id"], []).append(a["url"])
    candidate_urls = {c["id"]: c["url"] for c in ep.work.get("candidates", [])}
    for chapter in script.chapters:
        pick = picks.get(chapter.story_id)
        if not pick:
            continue
        urls = article_urls.get(chapter.story_id) or [
            candidate_urls[c] for c in pick["candidate_ids"] if c in candidate_urls
        ]
        session.add(
            Story(
                user_id=ep.user_id,
                episode_id=ep.id,
                title=pick["headline"],
                summary=pick["why_it_matters"][:400],
                topic=pick["interest"],
                urls=urls,
            )
        )

    report = ep.work.get("checker_report", {})
    props = {
        "duration_s": ep.duration_s,
        "cost": ep.cost,
        "stage_timings": ep.stage_timings,
        "issues_found": report.get("issues_found", 0),
        "issues_fixed": report.get("issues_fixed", 0),
    }
    session.add(Event(user_id=ep.user_id, type="episode_ready", episode_id=ep.id, props=props))
    session.commit()
