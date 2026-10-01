"""Background work in the API process (ADR 0010): a thread pool is the queue and the limit.

No broker, no worker containers: `MAX_CONCURRENT_GENERATIONS` threads run episodes; extra ones
wait in the pool's queue. One uvicorn worker only, so there is exactly one pool. The
scheduler joins this module in branch 10.
"""

import logging
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor

from sqlmodel import Session, select

from app.config import settings
from app.db import engine
from app.models import Episode
from app.pipeline.run import STAGES, generate_episode

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
