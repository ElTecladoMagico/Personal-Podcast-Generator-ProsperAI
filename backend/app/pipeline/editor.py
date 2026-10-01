"""Step 2 · Editor: choose today's stories from the candidates (ADR 0009)."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlmodel import Session, select

from app import llm
from app.models import Episode, Event, Story
from app.pipeline.run import add_cost, effective_minutes, save_work
from app.schemas import Candidate, EditorSelection, Preferences

PROMPT = (Path(__file__).parent / "prompts" / "editor.md").read_text()
STORIES_BY_MINUTES = {2: 2, 5: 3, 10: 5, 20: 7}


def story_count(minutes: int) -> int:
    return STORIES_BY_MINUTES[minutes]


def validate_selection(selection: EditorSelection, candidate_ids: set[str], wanted: int) -> None:
    """The model's answer must make sense before we spend money researching it."""
    if len(selection.picks) != wanted:
        raise ValueError(f"expected {wanted} stories, got {len(selection.picks)}")
    stories = selection.picks + selection.backups
    if len({p.story_id for p in stories}) != len(stories):
        raise ValueError("duplicate story id")
    used: set[str] = set()
    for p in stories:
        if not p.candidate_ids:
            raise ValueError(f"story {p.story_id} has no candidates")
        if unknown := set(p.candidate_ids) - candidate_ids:
            raise ValueError(f"unknown candidate ids {sorted(unknown)}")
        if used & set(p.candidate_ids):
            raise ValueError("a candidate is used in more than one story")
        used |= set(p.candidate_ids)


def feedback_by_interest(session: Session, user_id: uuid.UUID, days: int = 30) -> dict:
    """{interest: {"up", "down", "skipped"}} from the player's events of the last `days`."""
    since = datetime.now(UTC) - timedelta(days=days)
    rows = session.exec(
        select(Event, Episode.work)
        .join(Episode, Episode.id == Event.episode_id)
        .where(Event.user_id == user_id, Event.ts >= since)
        .where(Event.type.in_(["feedback", "chapter_skipped"]))
    ).all()
    result: dict[str, dict[str, int]] = {}
    for event, work in rows:
        picks = work.get("selection", {}).get("picks", [])
        interest = next(
            (p["interest"] for p in picks if p["story_id"] == event.props.get("story_id")), None
        )
        if interest is None:
            continue
        kind = event.props.get("value") if event.type == "feedback" else "skipped"
        counts = result.setdefault(interest, {"up": 0, "down": 0, "skipped": 0})
        if kind in counts:
            counts[kind] += 1
    return result


def recent_memory(session: Session, user_id: uuid.UUID, days: int = 14) -> list[dict]:
    since = datetime.now(UTC) - timedelta(days=days)
    stories = session.exec(
        select(Story).where(Story.user_id == user_id, Story.covered_at >= since)
    ).all()
    return [
        {
            "title": s.title,
            "summary": s.summary,
            "interest": s.topic,
            "date": s.covered_at.date().isoformat(),
        }
        for s in stories
    ]


def pick_stories(
    prefs: Preferences, candidates: list[Candidate], memory: list[dict], feedback: dict, wanted: int
) -> tuple[EditorSelection, dict]:
    payload = {
        "language": prefs.language,
        "interests": [
            {"topic": i.topic, "why": i.why, "weight": i.weight} for i in prefs.interests
        ],
        "avoid": prefs.avoid,
        "sources_i_trust": prefs.sources_i_trust,
        "depth": prefs.depth,
        "stories": wanted,
        "candidates": [
            {
                "id": c.id,
                "title": c.title,
                "outlet": c.source,
                "date": c.published_at.date().isoformat() if c.published_at else None,
                "snippet": (c.snippet or "")[:300] or None,
                "interest": c.interest,
            }
            for c in candidates
        ],
        "memory": memory,
        "feedback": feedback,
    }
    selection, usage = llm.parse(
        llm.EDITOR_MODEL, PROMPT, json.dumps(payload, ensure_ascii=False), EditorSelection
    )
    validate_selection(selection, {c.id for c in candidates}, wanted)
    return selection, usage


def step(ep: Episode, prefs: Preferences, session: Session) -> None:
    candidates = [Candidate.model_validate(c) for c in ep.work["candidates"]]
    wanted = min(story_count(effective_minutes(prefs)), len(candidates) // 2)
    selection, usage = pick_stories(
        prefs,
        candidates,
        recent_memory(session, ep.user_id),
        feedback_by_interest(session, ep.user_id),
        wanted,
    )
    save_work(ep, "selection", selection.model_dump())
    add_cost(ep, usage)
