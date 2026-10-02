"""Step 4 · Scriptwriter (gpt-6-sol): stories + articles → a script written for the ear."""

import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from sqlmodel import Session

from app import llm
from app.models import Episode, User
from app.pipeline.state import Work, effective_minutes
from app.schemas import Article, Chapter, EditorPick, Preferences, Script, Turn, Usage

PROMPT = (Path(__file__).parent / "prompts" / "writer.md").read_text()
CHARS_PER_MINUTE = 1000  # measured 2026-10-02 with creative stability at ×1.1 (1,786 chars, 107 s)
MAX_OVERSHOOT = 1.15  # beyond +15 % we cut closing turns instead of paying for the audio
AUDIO_TAGS = {
    "laughs",
    "chuckles",
    "sighs",
    "curious",
    "excited",
    "surprised",
    "thoughtful",
    "serious",
    "whispers",
    "pause",
}
TAG = re.compile(r"\[([a-z ]+)\]")


# What the model writes: the final Script minus the timing fields filled in step 6.
class WriterTurn(BaseModel):
    speaker: int
    text: str
    source_ids: list[str]


class WriterChapter(BaseModel):
    story_id: str | None
    title: str
    turns: list[WriterTurn]


class WriterScript(BaseModel):
    title: str
    summary: str
    chapters: list[WriterChapter]


def clean_text(text: str) -> str:
    """Only what the voices should read: allowed audio tags, no URLs or markdown."""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[*_`#]+", "", text)
    text = TAG.sub(lambda m: m.group(0) if m.group(1) in AUDIO_TAGS else "", text)
    return " ".join(text.split())


def spoken_chars(script: WriterScript | Script) -> int:
    return sum(len(TAG.sub("", t.text).strip()) for c in script.chapters for t in c.turns)


def trim_to(draft: WriterScript, max_chars: int) -> WriterScript:
    """Drop the last turn of story chapters, one chapter at a time, until it fits.
    Intro and outro are kept, and every chapter keeps at least one turn."""
    script = draft.model_copy(deep=True)
    while spoken_chars(script) > max_chars:
        cuttable = [c for c in script.chapters if c.story_id and len(c.turns) > 1]
        if not cuttable:
            break
        for chapter in cuttable:
            chapter.turns.pop()
            if spoken_chars(script) <= max_chars:
                break
    return script


def to_script(draft: WriterScript, article_ids: set[str], hosts: int) -> Script:
    """Sanitize what the model wrote: known sources only, valid speakers, clean text."""

    def turn(t: WriterTurn) -> Turn:
        return Turn(
            speaker=min(max(t.speaker, 0), hosts - 1),
            text=clean_text(t.text),
            source_ids=[s for s in t.source_ids if s in article_ids],
        )

    chapters = [
        Chapter(story_id=c.story_id, title=c.title, turns=[x for x in map(turn, c.turns) if x.text])
        for c in draft.chapters
    ]
    return Script(title=draft.title, summary=draft.summary, chapters=chapters)


def writer_input(
    prefs: Preferences,
    picks: list[EditorPick],
    articles: list[Article],
    listener: str | None,
    minutes: int,
) -> dict:
    today = datetime.now(ZoneInfo(prefs.schedule.timezone))
    return {
        "language": prefs.language,
        "format": prefs.format,
        "tone": prefs.tone,
        "depth": prefs.depth,
        "hosts": [h.name for h in prefs.hosts],
        "listener": listener,
        "today": today.date().isoformat(),
        "weekday": today.strftime("%A"),
        "frequency": prefs.schedule.frequency,
        "target_chars": minutes * CHARS_PER_MINUTE,
        "stories": [
            {
                "id": p.story_id,
                "headline": p.headline,
                "why_it_matters": p.why_it_matters,
                "follow_up_of": p.follow_up_of,
                "articles": [
                    {"id": a.id, "outlet": a.source, "title": a.title, "text": a.text}
                    for a in articles
                    if a.story_id == p.story_id
                ],
            }
            for p in picks
        ],
    }


def write_script(payload: dict, article_ids: set[str], hosts: int) -> tuple[Script, Usage]:
    draft, usage = llm.parse(
        llm.WRITER_MODEL, PROMPT, json.dumps(payload, ensure_ascii=False), WriterScript
    )
    draft = trim_to(draft, int(payload["target_chars"] * MAX_OVERSHOOT))
    return to_script(draft, article_ids, hosts), usage


def step(ep: Episode, prefs: Preferences, work: Work, session: Session) -> Usage:
    # The stories that survived research, in order (a backup when it replaced a pick).
    by_id = {p.story_id: p for p in work.selection.picks + work.selection.backups}
    picks = [by_id[s] for s in work.stories]
    listener = session.get(User, ep.user_id).display_name
    payload = writer_input(prefs, picks, work.articles, listener, effective_minutes(prefs))
    work.draft_script, usage = write_script(
        payload, {a.id for a in work.articles}, len(prefs.hosts)
    )
    return usage


REVISE = """

## Revision
You are now correcting a script you wrote. The fact-checker flagged some turns. Rewrite ONLY
those turns so they say what the articles support (or soften/remove the claim); keep every
other turn word for word, and keep the same chapters and turns in the same order."""


def revise_script(
    script: Script, issues: list, articles: list[Article], article_ids: set[str], hosts: int
) -> tuple[Script, Usage]:
    payload = {
        "script": script.model_dump(include={"title", "summary", "chapters"}),
        "issues": [i.model_dump() for i in issues],
        "articles": [{"id": a.id, "outlet": a.source, "text": a.text} for a in articles],
    }
    draft, usage = llm.parse(
        llm.WRITER_MODEL, PROMPT + REVISE, json.dumps(payload, ensure_ascii=False), WriterScript
    )
    return to_script(draft, article_ids, hosts), usage
