"""Episodes for the signed-in user: generate now, list, follow progress, retry."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from app.auth import CurrentUser
from app.config import settings
from app.db import DbSession
from app.jobs import run_in_pool
from app.models import Episode, User
from app.pipeline.run import new_episode
from app.pipeline.state import Progress, Work
from app.schemas import Script

router = APIRouter(prefix="/episodes")


class EpisodeSummary(BaseModel):
    id: uuid.UUID
    status: str
    title: str | None
    summary: str | None
    created_at: datetime
    duration_s: float | None
    topics: list[str]  # interests of the stories told, for the generative cover


class GenerationProgress(BaseModel):
    """Real numbers from each finished stage, so the UI can show the newsroom at work."""

    candidates: int
    outlets: int
    stories: list[str]  # headlines picked by the editor
    articles: int
    issues_found: int | None
    issues_fixed: int | None
    recording: Progress | None


class Source(BaseModel):
    title: str
    url: str
    source: str
    image_url: str | None


class EpisodeDetail(EpisodeSummary):
    failed_stage: str | None
    error: str | None
    progress: GenerationProgress
    hosts: list[str]
    script: Script | None  # with timings, once ready
    sources: dict[str, Source]  # article id → where it came from (no article text)
    audio_url: str | None


def topics(work: Work, ep: Episode) -> list[str]:
    if work.selection:
        return list(dict.fromkeys(p.interest for p in work.selection.picks))
    return [i["topic"] for i in ep.prefs_snapshot.get("interests", [])]


SUMMARY_FIELDS = {"id", "status", "title", "summary", "created_at", "duration_s"}


def summary(ep: Episode) -> EpisodeSummary:
    fields = ep.model_dump(include=SUMMARY_FIELDS)
    return EpisodeSummary(**fields, topics=topics(Work.model_validate(ep.work), ep))


def detail(ep: Episode, owner: User) -> EpisodeDetail:
    work = Work.model_validate(ep.work)
    check = work.checker_report
    ready = ep.status == "ready"
    return EpisodeDetail(
        **ep.model_dump(include=SUMMARY_FIELDS | {"failed_stage", "error"}),
        topics=topics(work, ep),
        progress=GenerationProgress(
            candidates=len(work.candidates),
            outlets=len({c.source for c in work.candidates}),
            stories=[p.headline for p in work.selection.picks] if work.selection else [],
            articles=len(work.articles),
            issues_found=check.issues_found if check else None,
            issues_fixed=check.issues_fixed if check else None,
            recording=work.recording,
        ),
        hosts=[h["name"] for h in ep.prefs_snapshot.get("hosts", [])],
        script=Script.model_validate(ep.script) if ready and ep.script else None,
        sources={a.id: Source(**a.model_dump()) for a in work.articles} if ready else {},
        audio_url=(
            f"{settings.public_base_url}/audio/{ep.id}.mp3?k={owner.feed_token}"
            if ready and ep.audio_path and not ep.audio_expired
            else None
        ),
    )


def own_episode(session: Session, user: User, episode_id: uuid.UUID) -> Episode:
    ep = session.get(Episode, episode_id)
    if not ep or ep.user_id != user.id:
        raise HTTPException(404, "Episode not found")
    return ep


@router.post("", status_code=201)
def generate_now(user: CurrentUser, session: DbSession) -> EpisodeDetail:
    if user.onboarded_at is None:
        raise HTTPException(400, "Set up your show first")
    since = datetime.now(UTC) - timedelta(days=1)
    today = session.exec(
        select(func.count()).where(
            Episode.user_id == user.id,
            Episode.trigger == "manual",
            Episode.status != "failed",
            Episode.created_at >= since,
        )
    ).one()
    limit = settings.max_manual_episodes_per_day
    if today >= limit:
        raise HTTPException(429, f"Daily limit of {limit} episodes reached")
    try:
        ep = new_episode(session, user, trigger="manual")
    except IntegrityError:  # the unique partial index: one episode in production per user
        raise HTTPException(409, "An episode is already being produced") from None
    run_in_pool(ep.id)
    return detail(ep, user)


@router.get("")
def list_episodes(user: CurrentUser, session: DbSession) -> list[EpisodeSummary]:
    eps = session.exec(
        select(Episode).where(Episode.user_id == user.id).order_by(Episode.created_at.desc())
    ).all()
    return [summary(ep) for ep in eps]


@router.get("/{episode_id}")
def get_episode(episode_id: uuid.UUID, user: CurrentUser, session: DbSession) -> EpisodeDetail:
    return detail(own_episode(session, user, episode_id), user)


@router.post("/{episode_id}/retry")
def retry(episode_id: uuid.UUID, user: CurrentUser, session: DbSession) -> EpisodeDetail:
    ep = own_episode(session, user, episode_id)
    if ep.status != "failed":
        raise HTTPException(409, "Only failed episodes can be retried")
    ep.status, ep.error = "queued", None  # failed_stage stays: the pipeline resumes there
    try:
        session.commit()
    except IntegrityError:
        raise HTTPException(409, "An episode is already being produced") from None
    run_in_pool(ep.id)
    return detail(ep, user)
