"""Database tables (docs/plans/00-contratos.md §4)."""

import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

TZ = DateTime(timezone=True)


def now() -> datetime:
    return datetime.now(UTC)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    clerk_id: str = Field(unique=True)
    email: str | None = None
    display_name: str | None = None
    preferences: dict = Field(default_factory=dict, sa_type=JSONB)
    onboarded_at: datetime | None = Field(default=None, sa_type=TZ)
    feed_token: str = Field(default_factory=lambda: secrets.token_urlsafe(32), unique=True)
    next_run_at: datetime | None = Field(default=None, sa_type=TZ)
    is_mock: bool = False
    created_at: datetime = Field(default_factory=now, sa_type=TZ)


class Episode(SQLModel, table=True):
    __tablename__ = "episodes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    trigger: str  # manual | scheduled
    status: str = "queued"  # see contracts §6
    failed_stage: str | None = None
    error: str | None = None
    language: str
    prefs_snapshot: dict = Field(sa_type=JSONB)
    work: dict = Field(default_factory=dict, sa_type=JSONB)  # intermediate results per stage
    title: str | None = None
    summary: str | None = None
    script: dict | None = Field(default=None, sa_type=JSONB)
    audio_path: str | None = None  # relative to AUDIO_DIR
    duration_s: float | None = None
    audio_expired: bool = False
    cost: dict = Field(default_factory=dict, sa_type=JSONB)
    stage_timings: dict = Field(default_factory=dict, sa_type=JSONB)
    created_at: datetime = Field(default_factory=now, sa_type=TZ)
    started_at: datetime | None = Field(default=None, sa_type=TZ)
    finished_at: datetime | None = Field(default=None, sa_type=TZ)


class Story(SQLModel, table=True):
    """Memory of what each user has already heard (editor avoids repeats)."""

    __tablename__ = "stories"
    __table_args__ = (Index("ix_stories_user_covered", "user_id", "covered_at"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id")
    episode_id: uuid.UUID = Field(foreign_key="episodes.id")
    title: str
    summary: str  # <= 400 chars
    topic: str
    urls: list[str] = Field(default_factory=list, sa_type=JSONB)
    covered_at: datetime = Field(default_factory=now, sa_type=TZ)


class Article(SQLModel, table=True):
    """Extraction cache shared by all users; reused while younger than 48 h."""

    __tablename__ = "articles"

    url: str = Field(primary_key=True)  # normalized final URL
    title: str | None = None
    text: str | None = None
    image_url: str | None = None  # og:image, for the player card
    ok: bool
    fetched_at: datetime = Field(default_factory=now, sa_type=TZ)


class Event(SQLModel, table=True):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_type_ts", "type", "ts"),
        Index("ix_events_user_ts", "user_id", "ts"),
    )

    id: int | None = Field(default=None, primary_key=True, sa_type=BigInteger)
    user_id: uuid.UUID = Field(foreign_key="users.id")
    type: str  # see contracts §8
    episode_id: uuid.UUID | None = Field(default=None, foreign_key="episodes.id")
    props: dict = Field(default_factory=dict, sa_type=JSONB)
    ts: datetime = Field(default_factory=now, sa_type=TZ)
