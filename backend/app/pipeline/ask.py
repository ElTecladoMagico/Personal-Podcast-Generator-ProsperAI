"""Ask the hosts (ADR 0014): the listener pauses, asks, and the hosts answer out loud from the
sources of the story being played. Same voices, seed and tempo as the episode."""

import json
import tempfile
import uuid
from pathlib import Path

from pydantic import BaseModel

from app.audio import change_tempo
from app.llm import ASK_MODEL, parse
from app.pipeline.voice import SPEED, synthesize
from app.pipeline.writer import clean_text
from app.schemas import Article, Host, Script, Turn, Usage
from app.storage import ask_relpath, audio_file

PROMPT = (Path(__file__).parent / "prompts" / "ask.md").read_text()
MAX_CHARS = 600  # the prompt asks for 450; a little slack before cutting turns
ARTICLE_CHARS = 4000


class AskTurn(BaseModel):
    speaker: int
    text: str
    source_ids: list[str]


class AskAnswer(BaseModel):
    turns: list[AskTurn]


def chapter_at(script: Script, t: float) -> int:
    """The story chapter playing at `t`; in the intro or outro, the closest story."""
    playing = max((i for i, c in enumerate(script.chapters) if (c.start_s or 0) <= t), default=0)
    stories = [i for i, c in enumerate(script.chapters) if c.story_id]
    if script.chapters[playing].story_id or not stories:
        return playing
    return min(stories, key=lambda i: abs(i - playing))


def to_turns(answer: AskAnswer, article_ids: set[str], hosts: int) -> list[Turn]:
    """Clean like the script (valid speakers, known sources, readable text) and keep it short."""
    turns, total = [], 0
    for t in answer.turns:
        text = clean_text(t.text)
        if not text or total + len(text) > MAX_CHARS:
            break
        total += len(text)
        speaker = min(max(t.speaker, 0), hosts - 1)
        turns.append(
            Turn(
                speaker=speaker, text=text, source_ids=[s for s in t.source_ids if s in article_ids]
            )
        )
    return turns


def answer(
    *,
    question: str,
    script: Script,
    chapter: int,
    articles: list[Article],
    hosts: list[Host],
    fmt: str,
    language: str,
    listener: str | None,
    seed: int,
    user_id: uuid.UUID,
    episode_id: uuid.UUID,
) -> tuple[str, list[Turn], Usage]:
    """Write and voice the answer: (qid, turns, usage). The MP3 is saved next to the episode."""
    story = script.chapters[chapter]
    sources = [a for a in articles if a.story_id == story.story_id]
    payload = {
        "language": language,
        "format": fmt,
        "hosts": [h.name for h in hosts],
        "listener": listener,
        "question": question,
        "chapter_title": story.title,
        "turns": [{"speaker": t.speaker, "text": t.text} for t in story.turns],
        "articles": [
            {"id": a.id, "outlet": a.source, "title": a.title, "text": a.text[:ARTICLE_CHARS]}
            for a in sources
        ],
    }
    draft, usage = parse(ASK_MODEL, PROMPT, json.dumps(payload, ensure_ascii=False), AskAnswer)
    turns = to_turns(draft, {a.id for a in sources}, len(hosts))
    if not turns:
        raise RuntimeError("The hosts had nothing to say")

    mp3, _ = synthesize([(t.text, hosts[t.speaker].voice_id) for t in turns], language, seed)
    qid = uuid.uuid4().hex[:8]
    out = audio_file(ask_relpath(user_id, episode_id, qid))
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.mp3"
        raw.write_bytes(mp3)
        change_tempo(raw, out, SPEED)
    usage.tts_chars = sum(len(t.text) for t in turns)
    return qid, turns, usage
