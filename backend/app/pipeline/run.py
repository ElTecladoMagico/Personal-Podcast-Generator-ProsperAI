"""Episode orchestration (ADR 0009): six stages in order, each one resumable.

Each step gets the typed `Work` of earlier stages, fills in its part and returns its `Usage`.
The runner saves work and cost only when the step succeeds. When a step raises, the episode
is left `failed` with `failed_stage`; a retry starts right there and reuses what came before.
"""

import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime

from sqlmodel import Session

from app.db import engine
from app.models import Episode, Event, Story, User
from app.pipeline import checker, editor, reporter, research, voice, writer
from app.pipeline.state import Work, store
from app.schemas import Preferences, Usage

log = logging.getLogger(__name__)

Step = Callable[[Episode, Preferences, Work, Session], Usage]
STEPS: dict[str, Step] = {
    "fetching": reporter.step,
    "editing": editor.step,
    "researching": research.step,
    "writing": writer.step,
    "verifying": checker.step,
    "recording": voice.step,
}
STAGES = list(STEPS)


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


def generate_episode(episode_id: uuid.UUID, steps: dict[str, Step] = STEPS) -> None:
    with Session(engine) as session:
        ep = session.get(Episode, episode_id)
        prefs = Preferences.model_validate(ep.prefs_snapshot)
        work = Work.model_validate(ep.work)
        # Resume where it stopped: the failed stage, or the stage a crash interrupted.
        start = ep.failed_stage or (ep.status if ep.status in STAGES else STAGES[0])
        ep.failed_stage = ep.error = None
        ep.started_at = ep.started_at or datetime.now(UTC)

        for name in STAGES[STAGES.index(start) :]:
            ep.status = name
            session.commit()
            t0 = time.perf_counter()
            try:
                usage = steps[name](ep, prefs, work, session)
            except Exception as err:  # any failure: record it, keep earlier work, stop
                log.exception("episode %s failed at %s", episode_id, name)
                session.rollback()
                fail(session, session.get(Episode, episode_id), name, err)
                return
            store(ep, work)
            ep.cost = (Usage.model_validate(ep.cost) + usage).model_dump()
            ep.stage_timings = {**ep.stage_timings, name: round(time.perf_counter() - t0, 1)}
            session.commit()

        finish(session, ep, work)


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


def finish(session: Session, ep: Episode, work: Work) -> None:
    ep.status, ep.title, ep.summary = "ready", ep.script["title"], ep.script["summary"]
    ep.finished_at = datetime.now(UTC)

    # Memory for the editor (no repeats, follow-ups): one row per story the hosts told.
    stories = {p.story_id: p for p in work.selection.picks + work.selection.backups}
    urls = defaultdict(list)
    for article in work.articles:
        urls[article.story_id].append(article.url)
    told = [c.story_id for c in work.final_script.chapters if c.story_id]
    for story_id in told:
        pick = stories[story_id]
        session.add(
            Story(
                user_id=ep.user_id,
                episode_id=ep.id,
                title=pick.headline,
                summary=pick.why_it_matters[:400],
                topic=pick.interest,
                urls=urls[story_id],
            )
        )

    check = work.checker_report
    props = {
        "duration_s": ep.duration_s,
        "cost": ep.cost,
        "stage_timings": ep.stage_timings,
        "issues_found": check.issues_found if check else 0,
        "issues_fixed": check.issues_fixed if check else 0,
    }
    session.add(Event(user_id=ep.user_id, type="episode_ready", episode_id=ep.id, props=props))
    session.commit()
