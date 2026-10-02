"""What the pipeline carries between stages (stored in episodes.work and episodes.cost).

Steps receive a typed `Work`, fill in their part and return the `Usage` (app.schemas) they
spent; the runner persists both only when the step succeeds, so a stage is all-or-nothing.
"""

from pydantic import BaseModel

from app.config import settings
from app.models import Episode
from app.schemas import Article, Candidate, CheckerReport, EditorSelection, Preferences, Script


class FactCheck(BaseModel):
    first: CheckerReport
    second: CheckerReport | None = None  # only when the first check asked for a fix
    issues_found: int
    issues_fixed: int = 0
    turns_removed: int = 0


class Progress(BaseModel):
    done: int
    total: int


class Work(BaseModel):
    """Each stage's output, in pipeline order. Empty until that stage has run."""

    candidates: list[Candidate] = []  # fetching
    selection: EditorSelection | None = None  # editing
    articles: list[Article] = []  # researching
    stories: list[str] = []  # researching: story ids that made it, in order
    draft_script: Script | None = None  # writing
    checker_report: FactCheck | None = None  # verifying
    final_script: Script | None = None  # verifying
    recording: Progress | None = None  # recording, updated per chunk for the UI


def store(ep: Episode, work: Work) -> None:
    ep.work = work.model_dump(mode="json")


def effective_minutes(prefs: Preferences) -> int:
    """EPISODE_MAX_MINUTES caps the length to save credits (2 in dev, 10 in prod)."""
    return min(prefs.duration_min, settings.episode_max_minutes)
