"""Where episode audio lives on disk (ADR 0004): AUDIO_DIR/<user_id>/<episode_id>.mp3."""

import uuid
from pathlib import Path

from app.config import settings


def audio_relpath(user_id: uuid.UUID, episode_id: uuid.UUID) -> str:
    """Stored in episodes.audio_path, relative so AUDIO_DIR can move."""
    return f"{user_id}/{episode_id}.mp3"


def audio_file(relpath: str) -> Path:
    return Path(settings.audio_dir) / relpath
