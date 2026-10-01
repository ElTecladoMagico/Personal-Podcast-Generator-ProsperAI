from app.pipeline.checker import remove_flagged, verify
from app.schemas import Chapter, CheckerReport, CheckIssue, Script, Turn


def t(text: str, sources=("a1",)) -> Turn:
    return Turn(speaker=0, text=text, source_ids=list(sources))


def script() -> Script:
    return Script(
        title="T",
        summary="S",
        chapters=[
            Chapter(story_id=None, title="Intro", turns=[t("Hi", ())]),
            Chapter(story_id="s1", title="A", turns=[t("fact 1"), t("wow", ()), t("fact 2")]),
            Chapter(story_id="s2", title="B", turns=[t("only fact"), t("reaction", ())]),
        ],
    )


def issue(chapter: int, turn: int) -> CheckIssue:
    return CheckIssue(
        chapter_index=chapter, turn_index=turn, problem="unsupported", explanation="x"
    )


def test_remove_flagged_drops_turns_and_chapters_left_without_facts():
    cleaned, removed = remove_flagged(script(), [issue(1, 0), issue(2, 0), issue(9, 9)])
    assert [c.title for c in cleaned.chapters] == ["Intro", "A"]  # B kept only a reaction
    assert [x.text for x in cleaned.chapters[1].turns] == ["wow", "fact 2"]
    assert removed == 2  # out-of-range issue ignored; B's leftover reaction goes with its chapter


def test_clean_draft_needs_a_single_check():
    calls = []

    def check(s):
        calls.append("check")
        return CheckerReport(issues=[], verdict="ok"), {"usd": 0.01}

    def revise(s, issues):
        raise AssertionError("no revision needed")

    final, report, usages = verify(script(), check, revise)
    assert final == script() and calls == ["check"] and len(usages) == 1
    assert report["issues_found"] == 0 and report["turns_removed"] == 0


def test_flagged_draft_is_revised_once_and_leftovers_removed():
    reports = iter(
        [
            CheckerReport(issues=[issue(1, 0), issue(1, 2)], verdict="fix"),
            CheckerReport(issues=[issue(1, 2)], verdict="fix"),
        ]
    )
    revised = script()
    revised.chapters[1].turns[0].text = "fact 1, corrected"

    final, report, usages = verify(
        script(),
        lambda s: (next(reports), {"usd": 0.01}),
        lambda s, issues: (revised, {"usd": 0.02}),
    )
    assert [x.text for x in final.chapters[1].turns] == ["fact 1, corrected", "wow"]
    assert (report["issues_found"], report["issues_fixed"], report["turns_removed"]) == (2, 1, 1)
    assert len(usages) == 3  # check, revise, check
