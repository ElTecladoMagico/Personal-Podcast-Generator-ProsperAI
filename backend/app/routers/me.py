import uuid
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.auth import Claims, CurrentUser
from app.config import settings

router = APIRouter()


class MeOut(BaseModel):
    id: uuid.UUID
    email: str | None
    display_name: str | None
    preferences: dict  # Preferences once onboarded, {} before
    onboarded: bool
    is_admin: bool
    feed_url: str
    next_run_at: datetime | None


@router.get("/me")
def get_me(user: CurrentUser, claims: Claims) -> MeOut:
    return MeOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        preferences=user.preferences,
        onboarded=user.onboarded_at is not None,
        is_admin=(claims.get("metadata") or {}).get("role") == "admin",
        feed_url=f"{settings.public_base_url}/feeds/{user.feed_token}.xml",
        next_run_at=user.next_run_at,
    )
