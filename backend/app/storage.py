"""Where episode audio lives on disk (ADR 0004): AUDIO_DIR/<user_id>/<episode_id>.mp3."""

import uuid
from pathlib import Path

from app.config import settings


def audio_relpath(user_id: uuid.UUID, episode_id: uuid.UUID) -> str:
    """Stored in episodes.audio_path, relative so AUDIO_DIR can move."""
    return f"{user_id}/{episode_id}.mp3"


def audio_file(relpath: str) -> Path:
    return Path(settings.audio_dir) / relpath


def new_audio_file(user_id: uuid.UUID, episode_id: uuid.UUID) -> tuple[str, Path]:
    """(relpath for the database, absolute path ready to be written)."""
    relpath = audio_relpath(user_id, episode_id)
    path = audio_file(relpath)
    path.parent.mkdir(parents=True, exist_ok=True)
    return relpath, path


def audio_url(episode_id: uuid.UUID, feed_token: str) -> str:
    """Public MP3 link: the owner's feed token is the credential (see routers/audio.py)."""
    return f"{settings.public_base_url}/audio/{episode_id}.mp3?k={feed_token}"


def ask_relpath(user_id: uuid.UUID, episode_id: uuid.UUID, qid: str) -> str:
    """Answers to "Ask the hosts" live next to the episode, in a folder of its own."""
    return f"{user_id}/{episode_id}/ask-{qid}.mp3"
