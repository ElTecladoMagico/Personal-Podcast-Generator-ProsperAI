import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from app.auth import Claims, CurrentUser
from app.config import settings
from app.db import DbSession
from app.importer import ImportedPreferences, extract_json
from app.models import Event, User
from app.schedule import compute_next_run
from app.schemas import Preferences
from app.voices import BY_ID

router = APIRouter()


class MeOut(BaseModel):
    id: uuid.UUID
    email: str | None
    display_name: str | None
    preferences: Preferences | None  # None until the onboarding is done
    onboarded: bool
    is_admin: bool
    feed_url: str
    next_run_at: datetime | None


def me_out(user: User, claims: dict) -> MeOut:
    return MeOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        preferences=Preferences.model_validate(user.preferences) if user.onboarded_at else None,
        onboarded=user.onboarded_at is not None,
        is_admin=(claims.get("metadata") or {}).get("role") == "admin",
        feed_url=f"{settings.public_base_url}/feeds/{user.feed_token}.xml",
        next_run_at=user.next_run_at,
    )


@router.get("/me")
def get_me(user: CurrentUser, claims: Claims) -> MeOut:
    return me_out(user, claims)


class PreferencesIn(BaseModel):
    preferences: Preferences
    method: Literal["import", "manual"] = "manual"


@router.put("/me/preferences")
def save_preferences(
    body: PreferencesIn, user: CurrentUser, claims: Claims, session: DbSession
) -> MeOut:
    prefs = body.preferences
    if unknown := [h.voice_id for h in prefs.hosts if h.voice_id not in BY_ID]:
        raise HTTPException(422, f"Unknown voice {unknown[0]}")
    first_time = user.onboarded_at is None
    user.preferences = prefs.model_dump()
    user.next_run_at = compute_next_run(prefs.schedule, datetime.now(UTC))
    if first_time:
        user.onboarded_at = datetime.now(UTC)
    kind = "onboarding_completed" if first_time else "preferences_updated"
    props = {"method": body.method} if first_time else {}
    session.add(Event(user_id=user.id, type=kind, props=props))
    session.commit()
    return me_out(user, claims)


class ImportIn(BaseModel):
    text: str


@router.post("/me/preferences/import")
def import_preferences(body: ImportIn, user: CurrentUser) -> ImportedPreferences:
    """Turns what the user's AI answered into a partial Preferences, without saving it."""
    try:
        return ImportedPreferences.model_validate(extract_json(body.text))
    except (ValueError, ValidationError) as err:
        raise HTTPException(
            422, "We couldn't find valid JSON with your interests. Did you paste the whole answer?"
        ) from err
