"""Episodes for the signed-in user: generate now, list, follow progress, retry."""

import logging
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, StringConstraints
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from app.auth import CurrentUser
from app.config import settings
from app.db import DbSession
from app.jobs import run_in_pool
from app.models import Episode, Event, User
from app.pipeline import ask
from app.pipeline.run import new_episode
from app.pipeline.state import Progress, Work
from app.schemas import Host, Script, Turn
from app.storage import audio_url

router = APIRouter(prefix="/episodes")
log = logging.getLogger(__name__)

Vote = Literal["up", "down"]


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
    story_id: str
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
    votes: dict[str, Vote]  # story id → the listener's last 👍/👎


def topics(work: Work, ep: Episode) -> list[str]:
    if work.selection:
        return list(dict.fromkeys(p.interest for p in work.selection.picks))
    return [i["topic"] for i in ep.prefs_snapshot.get("interests", [])]


SUMMARY_FIELDS = {"id", "status", "title", "summary", "created_at", "duration_s"}


def summary(ep: Episode) -> EpisodeSummary:
    fields = ep.model_dump(include=SUMMARY_FIELDS)
    return EpisodeSummary(**fields, topics=topics(Work.model_validate(ep.work), ep))


def votes(session: Session, ep: Episode) -> dict[str, Vote]:
    events = session.exec(
        select(Event).where(Event.episode_id == ep.id, Event.type == "feedback").order_by(Event.ts)
    ).all()
    # props come from the client: keep only well-formed votes
    return {
        e.props["story_id"]: e.props["value"]
        for e in events
        if isinstance(e.props.get("story_id"), str) and e.props.get("value") in ("up", "down")
    }


def detail(session: Session, ep: Episode, owner: User) -> EpisodeDetail:
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
            audio_url(ep.id, owner.feed_token)
            if ready and ep.audio_path and not ep.audio_expired
            else None
        ),
        votes=votes(session, ep),
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
    return detail(session, ep, user)


@router.get("")
def list_episodes(user: CurrentUser, session: DbSession) -> list[EpisodeSummary]:
    eps = session.exec(
        select(Episode).where(Episode.user_id == user.id).order_by(Episode.created_at.desc())
    ).all()
    return [summary(ep) for ep in eps]


@router.get("/{episode_id}")
def get_episode(episode_id: uuid.UUID, user: CurrentUser, session: DbSession) -> EpisodeDetail:
    return detail(session, own_episode(session, user, episode_id), user)


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
    return detail(session, ep, user)


class AskIn(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=300)]
    position_s: float = 0


class AskOut(BaseModel):
    qid: str
    turns: list[Turn]
    audio_url: str


ASKS_PER_HOUR = 10  # per episode: each answer costs an LLM call and some voice


@router.post("/{episode_id}/ask")
def ask_hosts(episode_id: uuid.UUID, body: AskIn, user: CurrentUser, session: DbSession) -> AskOut:
    """The hosts answer a question about the story being played, out loud (ADR 0014)."""
    ep = own_episode(session, user, episode_id)
    if ep.status != "ready" or not ep.script:
        raise HTTPException(409, "The episode isn't ready yet")
    asked = session.exec(
        select(func.count()).where(
            Event.episode_id == ep.id,
            Event.type == "ask_asked",
            Event.ts >= datetime.now(UTC) - timedelta(hours=1),
        )
    ).one()
    if asked >= ASKS_PER_HOUR:
        raise HTTPException(429, "That's a lot of questions! Try again in a while.")

    script, snapshot = Script.model_validate(ep.script), ep.prefs_snapshot
    chapter = ask.chapter_at(script, body.position_s)
    t0 = time.perf_counter()
    try:
        qid, turns, usage = ask.answer(
            question=body.question,
            script=script,
            chapter=chapter,
            articles=Work.model_validate(ep.work).articles,
            hosts=[Host.model_validate(h) for h in snapshot["hosts"]],
            fmt=snapshot.get("format", "duo"),
            language=ep.language,
            listener=user.display_name,
            seed=ep.id.int % 2**31,  # the episode's seed: the same voices
            user_id=user.id,
            episode_id=ep.id,
        )
    except Exception as err:
        log.exception("ask failed for episode %s", ep.id)
        raise HTTPException(502, "The hosts couldn't answer right now. Try again.") from err
    session.add(
        Event(
            user_id=user.id,
            type="ask_asked",
            episode_id=ep.id,
            props={
                "question": body.question,
                "position_s": body.position_s,
                "chapter_index": chapter,
                "latency_s": round(time.perf_counter() - t0, 2),
                "chars": usage.tts_chars,
                "llm_usd": usage.llm_usd,
            },
        )
    )
    session.commit()
    url = f"{settings.public_base_url}/audio/{ep.id}/ask-{qid}.mp3?k={user.feed_token}"
    return AskOut(qid=qid, turns=turns, audio_url=url)
