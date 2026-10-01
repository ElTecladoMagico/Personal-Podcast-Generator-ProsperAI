from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.db import engine
from app.models import Episode, Event, User
from app.pipeline.editor import feedback_by_interest, story_count, validate_selection
from app.schemas import EditorPick, EditorSelection


def pick(story_id: str, *candidate_ids: str, interest: str = "AI") -> EditorPick:
    return EditorPick(
        story_id=story_id,
        headline="h",
        candidate_ids=list(candidate_ids),
        interest=interest,
        why_it_matters="w",
        follow_up_of=None,
    )


CANDIDATES = {"c1", "c2", "c3", "c4", "c5"}


def test_story_count_follows_minutes():
    assert [story_count(m) for m in (2, 5, 10, 20)] == [2, 3, 5, 7]


def test_valid_selection_passes():
    sel = EditorSelection(
        picks=[pick("s1", "c1", "c2"), pick("s2", "c3")], backups=[pick("s3", "c4")]
    )
    validate_selection(sel, CANDIDATES, wanted=2)


@pytest.mark.parametrize(
    ("picks", "backups", "message"),
    [
        ([pick("s1", "c1"), pick("s2", "c9")], [], "unknown candidate"),
        ([pick("s1", "c1"), pick("s2", "c1")], [], "more than one story"),
        ([pick("s1", "c1"), pick("s2", "c2")], [pick("s3", "c2")], "more than one story"),
        ([pick("s1", "c1")], [], "expected 2 stories"),
        ([pick("s1", "c1"), pick("s1", "c2")], [], "duplicate story id"),
        ([pick("s1"), pick("s2", "c2")], [], "no candidates"),
    ],
)
def test_invalid_selections_are_rejected(picks, backups, message):
    with pytest.raises(ValueError, match=message):
        validate_selection(EditorSelection(picks=picks, backups=backups), CANDIDATES, wanted=2)


def test_feedback_is_grouped_by_the_interest_of_each_story():
    with Session(engine) as s:
        user = User(clerk_id="user_fb")
        s.add(user)
        s.flush()
        selection = {
            "picks": [
                pick("s1", "c1", interest="AI").model_dump(),
                pick("s2", "c2", interest="F1").model_dump(),
            ],
            "backups": [],
        }
        ep = Episode(
            user_id=user.id,
            trigger="manual",
            language="en",
            prefs_snapshot={},
            work={"selection": selection},
        )
        s.add(ep)
        s.flush()
        old = datetime.now(UTC) - timedelta(days=40)
        s.add_all(
            [
                Event(
                    user_id=user.id,
                    episode_id=ep.id,
                    type="feedback",
                    props={"story_id": "s1", "value": "up"},
                ),
                Event(
                    user_id=user.id,
                    episode_id=ep.id,
                    type="feedback",
                    props={"story_id": "s2", "value": "down"},
                ),
                Event(
                    user_id=user.id,
                    episode_id=ep.id,
                    type="chapter_skipped",
                    props={"story_id": "s2"},
                ),
                Event(
                    user_id=user.id,
                    episode_id=ep.id,
                    type="feedback",
                    ts=old,
                    props={"story_id": "s2", "value": "down"},
                ),  # older than 30 days: ignored
            ]
        )
        s.commit()
        assert feedback_by_interest(s, user.id) == {
            "AI": {"up": 1, "down": 0, "skipped": 0},
            "F1": {"up": 0, "down": 1, "skipped": 1},
        }
