from app.pipeline.ask import AskAnswer, AskTurn, chapter_at, to_turns
from app.schemas import Chapter, Script, Turn


def script() -> Script:
    def ch(story, start, end):
        return Chapter(story_id=story, title=story or "x", start_s=start, end_s=end,
                       turns=[Turn(speaker=0, text="t", source_ids=[])])  # fmt: skip

    return Script(title="T", summary="S", chapters=[
        ch(None, 0, 10), ch("s1", 10, 60), ch("s2", 60, 120), ch(None, 120, 130),
    ])  # fmt: skip


def test_the_question_is_about_the_story_being_played():
    assert chapter_at(script(), 30) == 1 and chapter_at(script(), 61) == 2


def test_in_the_intro_or_outro_it_is_about_the_closest_story():
    assert chapter_at(script(), 2) == 1  # intro → the first story
    assert chapter_at(script(), 125) == 2  # outro → the last one


def test_answer_is_cleaned_like_the_script_and_kept_short():
    answer = AskAnswer(turns=[
        AskTurn(speaker=5, text="**Buena pregunta** https://x.test", source_ids=["a1", "zz"]),
        AskTurn(speaker=0, text="a" * 600, source_ids=[]),
    ])  # fmt: skip
    turns = to_turns(answer, article_ids={"a1"}, hosts=2)
    assert turns[0].speaker == 1 and turns[0].text == "Buena pregunta"
    assert turns[0].source_ids == ["a1"]  # unknown sources dropped
    assert len(turns) == 1  # the long second turn would go over the limit
