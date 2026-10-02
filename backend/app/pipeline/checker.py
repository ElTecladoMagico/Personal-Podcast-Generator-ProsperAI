"""Step 5 · Fact-checker (gpt-6-sol): flag unsupported turns, one rewrite, drop leftovers."""

import json
from collections.abc import Callable
from pathlib import Path

from sqlmodel import Session

from app import llm
from app.models import Episode
from app.pipeline import writer
from app.pipeline.state import FactCheck, Work
from app.schemas import Article, CheckerReport, CheckIssue, Preferences, Script, Usage

PROMPT = (Path(__file__).parent / "prompts" / "checker.md").read_text()


def check_script(script: Script, articles: list[Article]) -> tuple[CheckerReport, Usage]:
    payload = {
        "articles": [{"id": a.id, "outlet": a.source, "text": a.text} for a in articles],
        "turns": [
            {"chapter_index": ci, "turn_index": ti, "text": t.text, "source_ids": t.source_ids}
            for ci, c in enumerate(script.chapters)
            for ti, t in enumerate(c.turns)
        ],
    }
    return llm.parse(
        llm.CHECKER_MODEL, PROMPT, json.dumps(payload, ensure_ascii=False), CheckerReport
    )


def remove_flagged(script: Script, issues: list[CheckIssue]) -> tuple[Script, int]:
    """Drop the turns still flagged; a story chapter left without factual turns goes too."""
    flagged = {(i.chapter_index, i.turn_index) for i in issues}
    removed, chapters = 0, []
    for ci, chapter in enumerate(script.chapters):
        kept = [t for ti, t in enumerate(chapter.turns) if (ci, ti) not in flagged]
        removed += len(chapter.turns) - len(kept)
        if chapter.story_id and not any(t.source_ids for t in kept):
            continue
        chapters.append(chapter.model_copy(update={"turns": kept}))
    return script.model_copy(update={"chapters": chapters}), removed


def verify(
    draft: Script,
    check: Callable[[Script], tuple[CheckerReport, Usage]],
    revise: Callable[[Script, list[CheckIssue]], tuple[Script, Usage]],
) -> tuple[Script, FactCheck, Usage]:
    """At most two checks and one revision, so cost and time stay bounded (ADR 0009)."""
    first, usage = check(draft)
    if not first.issues:
        return draft, FactCheck(first=first, issues_found=0), usage

    revised, revise_usage = revise(draft, first.issues)
    second, second_usage = check(revised)
    final, removed = remove_flagged(revised, second.issues)
    report = FactCheck(
        first=first,
        second=second,
        issues_found=len(first.issues),
        issues_fixed=max(len(first.issues) - len(second.issues), 0),
        turns_removed=removed,
    )
    return final, report, usage + revise_usage + second_usage


def step(ep: Episode, prefs: Preferences, work: Work, session: Session) -> Usage:
    ids, hosts = {a.id for a in work.articles}, len(prefs.hosts)
    work.final_script, work.checker_report, usage = verify(
        work.draft_script,
        lambda s: check_script(s, work.articles),
        lambda s, issues: writer.revise_script(s, issues, work.articles, ids, hosts),
    )
    return usage
