import json
from pathlib import Path

import pytest

from app.pipeline.voice import Chunk, build_timeline, chunk_turns, words_from_alignment
from app.schemas import Chapter, Script, Turn

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "eleven_dialogue.json").read_text())
T1, T2 = "[excited] Hola, Pedro. ¿Qué tal?", "Muy bien. Hoy, doce coma uno por ciento."


def turn(text: str, speaker: int = 0) -> Turn:
    return Turn(speaker=speaker, text=text, source_ids=[])


def test_chunks_never_split_turns_nor_cross_chapters():
    script = Script(
        title="t",
        summary="s",
        chapters=[
            Chapter(
                story_id=None,
                title="Intro",
                turns=[turn("a" * 1000), turn("b" * 700), turn("c" * 200)],
            ),
            Chapter(story_id="s1", title="A", turns=[turn("d" * 2000), turn("e" * 10)]),
        ],
    )
    assert chunk_turns(script, limit=1800) == [
        [(0, 0), (0, 1)],  # 1700
        [(0, 2)],  # +200 would exceed 1800
        [(1, 0)],  # a single turn longer than the limit goes alone
        [(1, 1)],
    ]


def test_words_skip_audio_tags_and_carry_the_offset():
    a = FIXTURE["alignment"]
    words = words_from_alignment(
        a["characters"], a["character_start_times_seconds"], 0, 32, offset=10.0
    )
    assert [w for _, w in words] == ["Hola,", "Pedro.", "¿Qué", "tal?"]
    assert all(t >= 10.0 for t, _ in words) and words == sorted(words)


def test_timeline_places_turns_and_chapters_on_the_episode_clock():
    script = Script(
        title="t",
        summary="s",
        chapters=[
            Chapter(story_id=None, title="Intro", turns=[turn(T1, 0), turn(T2, 1)]),
            Chapter(story_id="s1", title="A", turns=[turn(T1, 0), turn(T2, 1)]),
        ],
    )
    response = {"voice_segments": FIXTURE["voice_segments"], "alignment": FIXTURE["alignment"]}
    duration = FIXTURE["_mp3_duration_s"]
    chunks = [
        Chunk(turns=[(0, 0), (0, 1)], response=response, duration=duration),
        Chunk(turns=[(1, 0), (1, 1)], response=response, duration=duration),
    ]
    timed = build_timeline(script, chunks)

    intro, story = timed.chapters
    assert intro.turns[0].start_s == 0.0 and intro.turns[1].start_s == pytest.approx(2.16)
    assert story.turns[0].start_s == pytest.approx(duration)  # second chunk starts after the first
    assert story.end_s == pytest.approx(2 * duration)
    assert (intro.start_s, intro.end_s) == (intro.turns[0].start_s, intro.turns[1].end_s)
    assert story.turns[1].words[0][1] == "Muy" and story.turns[1].words[0][0] >= duration


def test_mismatched_alignment_falls_back_to_turn_highlighting():
    script = Script(
        title="t",
        summary="s",
        chapters=[
            Chapter(story_id=None, title="Intro", turns=[turn("Texto distinto", 0), turn(T2, 1)])
        ],
    )
    response = {"voice_segments": FIXTURE["voice_segments"], "alignment": FIXTURE["alignment"]}
    timed = build_timeline(
        script, [Chunk(turns=[(0, 0), (0, 1)], response=response, duration=5.36)]
    )
    first, second = timed.chapters[0].turns
    assert first.words is None and first.start_s == 0.0  # times kept, words dropped
    assert second.words


def test_record_voices_each_chunk_joins_them_and_reports_progress(tmp_path):
    import subprocess

    from app.audio import duration
    from app.pipeline.voice import record
    from app.schemas import Host

    tone = tmp_path / "tone.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=duration=5.36",
            "-c:a",
            "libmp3lame",
            "-ar",
            "44100",
            str(tone),
        ],
        check=True,
    )
    response = {"voice_segments": FIXTURE["voice_segments"], "alignment": FIXTURE["alignment"]}
    calls, progress = [], []

    def synth(inputs, language, seed):
        calls.append((inputs, language, seed))
        return tone.read_bytes(), response

    script = Script(
        title="t",
        summary="s",
        chapters=[
            Chapter(story_id=None, title="Intro", turns=[turn(T1, 0), turn(T2, 1)]),
            Chapter(story_id="s1", title="A", turns=[turn(T1, 0), turn(T2, 1)]),
        ],
    )
    hosts = [Host(name="Sarah", voice_id="v-sarah"), Host(name="George", voice_id="v-george")]
    out = tmp_path / "episode.mp3"
    timed, chars = record(
        script, hosts, "es", 7, out, synth=synth, on_progress=lambda d, t: progress.append((d, t))
    )

    assert calls[0] == ([(T1, "v-sarah"), (T2, "v-george")], "es", 7)
    assert progress == [(1, 2), (2, 2)] and chars == 2 * (len(T1) + len(T2))
    assert duration(out) == pytest.approx(2 * 5.36, abs=0.1)
    assert timed.chapters[1].start_s == pytest.approx(duration(tone), abs=0.01)
