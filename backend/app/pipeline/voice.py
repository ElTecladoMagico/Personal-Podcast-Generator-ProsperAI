"""Step 6 · Hosts: ElevenLabs text-to-dialogue per chunk, then one MP3 and a timeline.

The timeline (when each turn and word is spoken) comes from ElevenLabs' character alignment.
Chunk offsets use the real MP3 duration (ffprobe), not the last aligned character, so the
clock never drifts across chunks (ADR 0008, 0016).
"""

import base64
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from elevenlabs import DialogueInput
from elevenlabs.client import ElevenLabs
from sqlmodel import Session

from app.audio import assemble, duration
from app.config import settings
from app.models import Episode
from app.pipeline.state import Progress, Work, store
from app.schemas import Host, Preferences, Script, Usage
from app.storage import new_audio_file

CHUNK_CHARS = 1800  # below the per-request limit, and short enough to retry cheaply
MODEL = "eleven_v3"
FORMAT = "mp3_44100_128"  # 192 kbps needs a paid Creator plan
# Chunks are independent (eleven_v3 has no previous_text), so they are voiced in parallel.
# Kept low because every running episode does this; the SDK retries if we hit a 429.
PARALLEL_CHUNKS = 3
STABILITY = 0.0  # eleven_v3: 0.0 creative, 0.5 natural, 1.0 robust. Creative sounded liveliest
SPEED = 1.1  # dialogue has no speed setting, so the joined MP3 is sped up with ffmpeg
# Chunks come back with no silence at their edges. Without a pause, a new story started faster
# than a normal change of speaker (measured: ~0.7 s between turns, ≤0.27 s between chapters).
CHAPTER_GAP = 0.9  # seconds before the next chapter (before speeding up)
SPLIT_GAP = 0.35  # when a long chapter was split into two requests
# Both chosen by ear on 2026-10-02 (A/B in docs/plans/06b-voz-espana.md).

TurnRef = tuple[int, int]  # (chapter index, turn index)


@dataclass
class Chunk:
    turns: list[TurnRef]
    response: dict  # {"voice_segments": [...], "alignment": {...}}
    duration: float  # seconds of the chunk's MP3


def chunk_turns(script: Script, limit: int = CHUNK_CHARS) -> list[list[TurnRef]]:
    """Consecutive turns of one chapter, up to `limit` characters, never splitting a turn.
    Cutting at chapter borders keeps tone changes where the topic changes anyway."""
    chunks: list[list[TurnRef]] = []
    for ci, chapter in enumerate(script.chapters):
        current: list[TurnRef] = []
        size = 0
        for ti, turn in enumerate(chapter.turns):
            if current and size + len(turn.text) > limit:
                chunks.append(current)
                current, size = [], 0
            current.append((ci, ti))
            size += len(turn.text)
        if current:
            chunks.append(current)
    return chunks


def gaps(plan: list[list[TurnRef]]) -> list[float]:
    """The pause after each chunk: longer before a new chapter, none after the last one."""
    return [
        0.0 if i == len(plan) - 1 else CHAPTER_GAP if plan[i + 1][0][0] != refs[0][0] else SPLIT_GAP
        for i, refs in enumerate(plan)
    ]


def words_from_alignment(
    chars: list[str], starts: list[float], lo: int, hi: int, offset: float
) -> list[tuple[float, str]]:
    """(start second, word) for characters lo..hi, skipping audio tags like [laughs]."""
    words: list[tuple[float, str]] = []
    word, word_start, in_tag = "", 0.0, False
    for i in range(lo, hi):
        ch = chars[i]
        if ch == "[" or in_tag:
            in_tag = ch != "]"
            continue
        if ch.isspace():
            if word:
                words.append((round(offset + word_start, 3), word))
            word = ""
            continue
        if not word:
            word_start = starts[i]
        word += ch
    if word:
        words.append((round(offset + word_start, 3), word))
    return words


def build_timeline(script: Script, chunks: list[Chunk], speed: float = 1.0) -> Script:
    """Turn, word and chapter times on the episode clock. With `speed` > 1 the MP3 was sped
    up after joining, so every time is divided by it."""
    timed = script.model_copy(deep=True)
    offset = 0.0
    for chunk in chunks:
        alignment = chunk.response["alignment"]
        chars, starts = alignment["characters"], alignment["character_start_times_seconds"]
        spoken: dict[TurnRef, str] = {}
        words: dict[TurnRef, list] = {}
        for seg in chunk.response["voice_segments"]:
            ref = chunk.turns[seg["dialogue_input_index"]]
            turn = timed.chapters[ref[0]].turns[ref[1]]
            start = round(offset + seg["start_time_seconds"], 3)
            end = round(offset + seg["end_time_seconds"], 3)
            turn.start_s = start if turn.start_s is None else min(turn.start_s, start)
            turn.end_s = end if turn.end_s is None else max(turn.end_s, end)
            lo, hi = seg["character_start_index"], seg["character_end_index"]
            spoken[ref] = spoken.get(ref, "") + "".join(chars[lo:hi])
            words[ref] = words.get(ref, []) + words_from_alignment(chars, starts, lo, hi, offset)
        for ref, text in spoken.items():
            turn = timed.chapters[ref[0]].turns[ref[1]]
            # If ElevenLabs normalized the text, word positions are unreliable: highlight by turn.
            turn.words = words[ref] if text.strip() == turn.text.strip() else None
        offset += chunk.duration
    for chapter in timed.chapters:
        for t in chapter.turns:
            if t.start_s is not None:
                t.start_s, t.end_s = round(t.start_s / speed, 3), round(t.end_s / speed, 3)
            if t.words:
                t.words = [(round(s / speed, 3), w) for s, w in t.words]
        times = [(t.start_s, t.end_s) for t in chapter.turns if t.start_s is not None]
        if times:
            chapter.start_s = min(s for s, _ in times)
            chapter.end_s = max(e for _, e in times)
    return timed


@cache
def client() -> ElevenLabs:
    return ElevenLabs(api_key=settings.elevenlabs_api_key, timeout=180)


Synth = Callable[[list[tuple[str, str]], str, int], tuple[bytes, dict]]


def synthesize(inputs: list[tuple[str, str]], language: str, seed: int) -> tuple[bytes, dict]:
    """One dialogue request: [(text, voice_id)] → (mp3 bytes, segments + alignment)."""
    r = client().text_to_dialogue.convert_with_timestamps(
        inputs=[DialogueInput(text=text, voice_id=voice) for text, voice in inputs],
        model_id=MODEL,
        output_format=FORMAT,
        language_code=language,
        seed=seed,  # same seed for every chunk of an episode: steadier voices
        settings={"stability": STABILITY},
        request_options={"max_retries": 3},  # the SDK backs off on 429 and 5xx
    )
    data = r.model_dump()
    return base64.b64decode(data["audio_base_64"]), {
        "voice_segments": data["voice_segments"],
        "alignment": data["alignment"],
    }


def record(
    script: Script,
    hosts: list[Host],
    language: str,
    seed: int,
    out: Path,
    *,
    synth: Synth = synthesize,
    on_progress: Callable[[int, int], None] = lambda done, total: None,
) -> tuple[Script, int]:
    """Voice every chunk, join them into `out` and return (timed script, characters billed).
    `on_progress` is called from this thread, so it may use the caller's database session."""
    plan = chunk_turns(script)
    inputs = [
        [
            (t.text, hosts[t.speaker].voice_id)
            for t in (script.chapters[ci].turns[ti] for ci, ti in refs)
        ]
        for refs in plan
    ]
    with ThreadPoolExecutor(PARALLEL_CHUNKS) as pool:
        futures = [pool.submit(synth, chunk, language, seed) for chunk in inputs]
        for done, future in enumerate(as_completed(futures), start=1):
            future.result()  # fail fast if a chunk failed
            on_progress(done, len(plan))

    chunks, parts, pauses = [], [], gaps(plan)
    with tempfile.TemporaryDirectory() as tmp:
        for i, (refs, future) in enumerate(zip(plan, futures, strict=True)):
            mp3, response = future.result()
            part = Path(tmp) / f"chunk_{i:03}.mp3"
            part.write_bytes(mp3)
            parts.append(part)
            # the pause counts as part of the chunk, so the transcript timeline stays in sync
            chunks.append(Chunk(turns=refs, response=response, duration=duration(part) + pauses[i]))
        assemble(parts, pauses, out, SPEED)
    chars = sum(len(text) for chunk in inputs for text, _ in chunk)
    return build_timeline(script, chunks, SPEED), chars


def step(ep: Episode, prefs: Preferences, work: Work, session: Session) -> Usage:
    relpath, out = new_audio_file(ep.user_id, ep.id)

    def progress(done: int, total: int) -> None:  # the UI shows "recording 3/6"
        work.recording = Progress(done=done, total=total)
        store(ep, work)
        session.commit()

    timed, chars = record(
        work.final_script, prefs.hosts, prefs.language, ep.id.int % 2**31, out, on_progress=progress
    )
    ep.script = timed.model_dump()
    ep.audio_path = relpath
    ep.duration_s = round(duration(out), 2)
    return Usage(tts_chars=chars)
