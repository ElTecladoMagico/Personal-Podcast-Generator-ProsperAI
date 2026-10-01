"""JSON shapes shared by the API and the pipeline (docs/plans/00-contratos.md §5)."""

from datetime import datetime
from typing import Annotated, Literal
from zoneinfo import available_timezones

from pydantic import BaseModel, Field, field_validator, model_validator

# --- User preferences -------------------------------------------------------


class Interest(BaseModel):
    topic: Annotated[str, Field(min_length=1, max_length=80)]
    why: str | None = None
    weight: Annotated[int, Field(ge=1, le=5)] = 3


class Host(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=30)]
    voice_id: str


class Schedule(BaseModel):
    frequency: Literal["off", "daily", "weekdays", "weekly"] = "daily"
    time: Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")] = "07:00"  # local HH:MM
    weekday: Annotated[int, Field(ge=0, le=6)] | None = None  # 0 = Monday, weekly only
    timezone: str = "Europe/Madrid"

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str) -> str:
        if value not in available_timezones():
            raise ValueError(f"unknown timezone: {value}")
        return value

    @model_validator(mode="after")
    def weekly_needs_weekday(self) -> "Schedule":
        if self.frequency == "weekly" and self.weekday is None:
            raise ValueError("weekly schedule needs a weekday")
        return self


class Preferences(BaseModel):
    interests: Annotated[list[Interest], Field(min_length=1, max_length=12)]
    avoid: list[str] = []
    sources_i_trust: list[str] = []
    language: str = "en"  # ISO 639-1
    tone: Literal["casual", "serious", "nerdy"] = "casual"
    depth: Literal["headlines", "analysis"] = "analysis"
    format: Literal["solo", "duo", "debate"] = "duo"
    duration_min: Literal[5, 10, 20] = 10
    hosts: list[Host]
    schedule: Schedule = Schedule()

    @model_validator(mode="after")
    def hosts_match_format(self) -> "Preferences":
        expected = 1 if self.format == "solo" else 2
        if len(self.hosts) != expected:
            raise ValueError(f"format '{self.format}' needs {expected} host(s)")
        return self


# --- Pipeline ---------------------------------------------------------------


class Candidate(BaseModel):  # step 1
    id: str  # "c1".."cN"
    title: str
    source: str
    url: str
    published_at: datetime | None
    snippet: str | None
    origin: Literal["google_news", "exa", "hn"]
    interest: str
    text: str | None = None  # Exa already includes the body


class EditorPick(BaseModel):  # step 2
    story_id: str  # "s1".."s7"
    headline: str
    candidate_ids: list[str]
    interest: str
    why_it_matters: str
    follow_up_of: str | None


class EditorSelection(BaseModel):
    picks: list[EditorPick]
    backups: list[EditorPick]


class Article(BaseModel):  # step 3
    id: str  # "a1".."aN"
    story_id: str
    url: str
    source: str
    title: str
    text: str  # trimmed to 6,000 chars
    image_url: str | None


class Turn(BaseModel):
    speaker: int  # index into hosts
    text: str  # may contain eleven_v3 audio tags: [laughs], [curious]…
    source_ids: list[str]  # Article ids; empty only for intro, outro and transitions
    start_s: float | None = None  # filled in step 6
    end_s: float | None = None
    words: list[tuple[float, str]] | None = None  # (start_s, word) for karaoke


class Chapter(BaseModel):
    story_id: str | None  # None = intro or outro
    title: str
    turns: list[Turn]
    start_s: float | None = None
    end_s: float | None = None


class Script(BaseModel):
    title: str
    summary: str
    chapters: list[Chapter]


class CheckIssue(BaseModel):  # step 5
    chapter_index: int
    turn_index: int
    problem: Literal["unsupported", "exaggerated", "misattributed", "outdated"]
    explanation: str


class CheckerReport(BaseModel):
    issues: list[CheckIssue]
    verdict: Literal["ok", "fix"]
