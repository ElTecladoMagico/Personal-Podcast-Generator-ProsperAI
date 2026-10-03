from app.pipeline.writer import (
    WriterChapter,
    WriterScript,
    WriterTurn,
    clean_text,
    spoken_chars,
    to_script,
    trim_to,
)


def turn(text: str, speaker: int = 0, sources=("a1",)) -> WriterTurn:
    return WriterTurn(speaker=speaker, text=text, source_ids=list(sources))


def test_clean_text_keeps_allowed_audio_tags_only_and_strips_markup():
    raw = "[laughs] **Wow**, read it at https://x.com/a [shouting] — really? [pause] `ok`"
    assert clean_text(raw) == "[laughs] Wow, read it at — really? [pause] ok"


def test_spoken_chars_ignore_audio_tags():
    script = WriterScript(
        title="t",
        summary="s",
        chapters=[
            WriterChapter(story_id=None, title="Intro", turns=[turn("[excited] Hello"), turn("Hi")])
        ],
    )
    assert spoken_chars(script) == len("Hello") + len("Hi")


def test_to_script_drops_unknown_sources_and_clamps_speakers():
    draft = WriterScript(
        title="t",
        summary="s",
        chapters=[
            WriterChapter(
                story_id="s1",
                title="Chip",
                turns=[turn("A [whispers] fact", speaker=3, sources=("a1", "a9"))],
            )
        ],
    )
    script = to_script(draft, article_ids={"a1"}, hosts=2)
    t = script.chapters[0].turns[0]
    assert (t.speaker, t.source_ids, t.start_s, t.words) == (1, ["a1"], None, None)


def test_trim_removes_closing_turns_of_story_chapters_first():
    long = "x" * 100
    draft = WriterScript(
        title="t",
        summary="s",
        chapters=[
            WriterChapter(story_id=None, title="Intro", turns=[turn(long)]),
            WriterChapter(story_id="s1", title="A", turns=[turn(long), turn(long), turn(long)]),
            WriterChapter(story_id="s2", title="B", turns=[turn(long), turn(long)]),
            WriterChapter(story_id=None, title="Outro", turns=[turn(long)]),
        ],
    )
    trimmed = trim_to(draft, max_chars=500)
    assert spoken_chars(trimmed) <= 500
    assert [len(c.turns) for c in trimmed.chapters] == [1, 2, 1, 1]  # intro/outro untouched
    assert trim_to(draft, max_chars=10_000) == draft


def test_writer_knows_the_listeners_local_time_to_greet_right():
    import re

    from app.pipeline.writer import writer_input
    from app.schemas import Preferences

    prefs = Preferences.model_validate(
        {
            "interests": [{"topic": "IA"}],
            "format": "solo",
            "hosts": [{"name": "Sara", "voice_id": "v"}],
        }
    )
    payload = writer_input(prefs, [], [], "Ana", 5)
    assert re.fullmatch(r"\d{2}:\d{2}", payload["local_time"])  # "buenas noches" at 23:00
    assert payload["weekday"] and payload["listener"] == "Ana"
