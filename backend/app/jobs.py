"""Background work in the API process (ADR 0010): a thread pool is the queue and the limit.

No broker, no worker containers: `MAX_CONCURRENT_GENERATIONS` threads run episodes; extra ones
wait in the pool's queue. One uvicorn worker only, so there is exactly one pool, and one
scheduler thread that starts the episodes that are due and removes old audio.
"""

import logging
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.config import settings
from app.db import engine
from app.models import Episode, User
from app.pipeline.run import STAGES, generate_episode, new_episode
from app.schedule import compute_next_run
from app.schemas import Preferences
from app.storage import audio_file

TICK_S = 60  # how often the scheduler looks for due episodes (a cheap indexed query)
AUDIO_KEEP_DAYS = 30

log = logging.getLogger(__name__)
executor = ThreadPoolExecutor(
    max_workers=settings.max_concurrent_generations, thread_name_prefix="episode"
)


def run_in_pool(episode_id: uuid.UUID) -> Future:
    return executor.submit(_generate_logged, episode_id)


def _generate_logged(episode_id: uuid.UUID) -> None:
    # The pool keeps exceptions inside the Future, where nobody reads them. Steps already
    # record their failures; this catches the rest (bad snapshot, database down…).
    try:
        generate_episode(episode_id)
    except Exception:
        log.exception("episode %s crashed outside its steps", episode_id)


def recover_interrupted(submit: Callable[[uuid.UUID], None] = run_in_pool) -> list[uuid.UUID]:
    """After a restart, resubmit every episode left queued or mid-stage. generate_episode
    resumes each one at the stage it was in, reusing the work already saved."""
    with Session(engine) as session:
        ids = list(session.exec(select(Episode.id).where(Episode.status.in_(["queued", *STAGES]))))
    for episode_id in ids:
        log.warning("resuming interrupted episode %s", episode_id)
        submit(episode_id)
    return ids


def enqueue_due(
    now: datetime, submit: Callable[[uuid.UUID], None] = run_in_pool
) -> list[uuid.UUID]:
    """Start the episode of every listener whose slot has come. The slot always moves on first,
    so a missed one (API down, an episode still in production) is skipped, never piled up."""
    # ponytail: no row locks; one API process runs this loop (ADR 0010). Several instances
    # would need SELECT … FOR UPDATE SKIP LOCKED here.
    created = []
    with Session(engine) as session:
        due = session.exec(
            select(User).where(
                User.next_run_at <= now, User.onboarded_at.is_not(None), User.is_mock.is_(False)
            )
        ).all()
        for user in due:
            schedule = Preferences.model_validate(user.preferences).schedule
            user.next_run_at = compute_next_run(schedule, now)
            session.commit()
            try:
                ep = new_episode(session, user, trigger="scheduled")
            except IntegrityError:  # one already in production (the unique partial index)
                session.rollback()
                continue
            submit(ep.id)
            created.append(ep.id)
    return created


def cleanup_audio(now: datetime) -> int:
    """Delete MP3s older than 30 days; the episode and its transcript stay (ADR 0004)."""
    cutoff = now - timedelta(days=AUDIO_KEEP_DAYS)
    with Session(engine) as session:
        old = session.exec(
            select(Episode).where(
                Episode.status == "ready",
                Episode.finished_at < cutoff,
                Episode.audio_expired.is_(False),
            )
        ).all()
        for ep in old:
            if ep.audio_path:
                audio_file(ep.audio_path).unlink(missing_ok=True)
            ep.audio_expired = True
        session.commit()
        return len(old)


def schedule_forever(stop: threading.Event) -> None:
    while True:
        try:
            now = datetime.now(UTC)
            enqueue_due(now)
            cleanup_audio(now)
        except Exception:
            log.exception("scheduler tick failed")
        if stop.wait(TICK_S):
            return
