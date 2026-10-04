import re
import secrets
import uuid
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import FileResponse

from app.db import DbSession
from app.models import Episode, Event, User
from app.storage import ask_relpath, audio_file

router = APIRouter()


def playable(session: DbSession, episode_id: uuid.UUID, k: str) -> tuple[Episode, User]:
    """The episode, if `k` is its owner's feed token and its audio hasn't expired."""
    ep = session.get(Episode, episode_id)
    owner = session.get(User, ep.user_id) if ep else None
    if not ep or not ep.audio_path or not secrets.compare_digest(owner.feed_token, k):
        raise HTTPException(404, "Episode not found")
    if ep.audio_expired:
        raise HTTPException(410, "This episode's audio was removed after 30 days")
    return ep, owner


def existing(path: Path) -> Path:
    if not path.is_file():
        raise HTTPException(404, "Episode not found")
    return path


# Podcast apps check the file with HEAD before downloading it.
# Not in OpenAPI: GET+HEAD would duplicate the operation id, and only <audio> and apps use it.
@router.api_route(
    "/audio/{episode_id}.mp3",
    methods=["GET", "HEAD"],
    response_class=FileResponse,
    include_in_schema=False,
)
def get_audio(
    episode_id: uuid.UUID,
    k: str,
    request: Request,
    session: DbSession,
    src: str | None = None,
    byte_range: str | None = Header(None, alias="range"),
) -> FileResponse:
    """MP3 for <audio> and podcast apps, which cannot send a JWT: the owner's feed token in
    `?k=` is the credential (revocable). FileResponse answers Range requests with 206."""
    ep, owner = playable(session, episode_id, k)
    path = existing(audio_file(ep.audio_path))
    # A podcast app fetching from the start is one listen; its later Range chunks are not.
    if (
        request.method == "GET"
        and src == "rss"
        and (byte_range is None or byte_range.startswith("bytes=0-"))
    ):
        session.add(Event(user_id=owner.id, type="feed_download", episode_id=ep.id))
        session.commit()
    return FileResponse(path, media_type="audio/mpeg")


@router.get("/audio/{episode_id}/ask-{qid}.mp3", include_in_schema=False)
def get_answer_audio(episode_id: uuid.UUID, qid: str, k: str, session: DbSession) -> FileResponse:
    """The hosts' answer to a question about this episode (same credential as the episode)."""
    if not re.fullmatch(r"[0-9a-f]{8}", qid):
        raise HTTPException(404, "Episode not found")
    ep, _ = playable(session, episode_id, k)
    return FileResponse(
        existing(audio_file(ask_relpath(ep.user_id, ep.id, qid))), media_type="audio/mpeg"
    )
