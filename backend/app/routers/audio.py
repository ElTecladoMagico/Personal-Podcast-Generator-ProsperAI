import secrets
import uuid

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import FileResponse

from app.db import DbSession
from app.models import Episode, Event, User
from app.storage import audio_file

router = APIRouter()


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
    ep = session.get(Episode, episode_id)
    owner = session.get(User, ep.user_id) if ep else None
    if not ep or not ep.audio_path or not secrets.compare_digest(owner.feed_token, k):
        raise HTTPException(404, "Episode not found")
    if ep.audio_expired:
        raise HTTPException(410, "This episode's audio was removed after 30 days")
    path = audio_file(ep.audio_path)
    if not path.is_file():
        raise HTTPException(404, "Episode not found")
    # A podcast app fetching from the start is one listen; its later Range chunks are not.
    if (
        request.method == "GET"
        and src == "rss"
        and (byte_range is None or byte_range.startswith("bytes=0-"))
    ):
        session.add(Event(user_id=owner.id, type="feed_download", episode_id=ep.id))
        session.commit()
    return FileResponse(path, media_type="audio/mpeg")
