"""Listening events sent by the web player (contract §8). They feed the editor (feedback
and skips per interest) and the usage dashboard."""

import json
import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.auth import CurrentUser
from app.db import DbSession
from app.models import Episode, Event

router = APIRouter()
MAX_PROPS_BYTES = 2048


class EventIn(BaseModel):
    # Only what the player may send; backend events (episode_ready…) are never trusted from here.
    type: Literal[
        "play_started", "chapter_started", "chapter_skipped", "listen_progress", "feedback"
    ]
    episode_id: uuid.UUID
    props: dict = {}


@router.post("/events", status_code=204)
def track(body: EventIn, user: CurrentUser, session: DbSession) -> Response:
    if len(json.dumps(body.props)) > MAX_PROPS_BYTES:
        raise HTTPException(413, "Event props are too large")
    ep = session.get(Episode, body.episode_id)
    if not ep or ep.user_id != user.id:
        raise HTTPException(404, "Episode not found")
    session.add(Event(user_id=user.id, type=body.type, episode_id=ep.id, props=body.props))
    session.commit()
    return Response(status_code=204)
