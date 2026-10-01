import secrets
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.db import DbSession
from app.models import Episode, User
from app.storage import audio_file

router = APIRouter()


@router.get("/audio/{episode_id}.mp3", response_class=FileResponse)
def get_audio(episode_id: uuid.UUID, k: str, session: DbSession) -> FileResponse:
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
    return FileResponse(path, media_type="audio/mpeg")
