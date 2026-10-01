"""Step 5 · Fact-checker (gpt-6-sol): flag unsupported turns, one rewrite, drop leftovers."""

import json
from collections.abc import Callable
from pathlib import Path

from sqlmodel import Session

from app import llm
from app.models import Episode
from app.pipeline import writer
from app.pipeline.run import add_cost, save_work
from app.schemas import Article, CheckerReport, CheckIssue, Preferences, Script

PROMPT = (Path(__file__).parent / "prompts" / "checker.md").read_text()


def check_script(script: Script, articles: list[Article]) -> tuple[CheckerReport, dict]:
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
    check: Callable[[Script], tuple[CheckerReport, dict]],
    revise: Callable[[Script, list[CheckIssue]], tuple[Script, dict]],
) -> tuple[Script, dict, list[dict]]:
    """At most two checks and one revision, so cost and time stay bounded (ADR 0009)."""
    first, usage = check(draft)
    usages = [usage]
    report = {
        "first": first.model_dump(),
        "issues_found": len(first.issues),
        "issues_fixed": 0,
        "turns_removed": 0,
    }
    if not first.issues:
        return draft, report, usages

    revised, usage = revise(draft, first.issues)
    usages.append(usage)
    second, usage = check(revised)
    usages.append(usage)
    final, removed = remove_flagged(revised, second.issues)
    report |= {
        "second": second.model_dump(),
        "issues_fixed": max(len(first.issues) - len(second.issues), 0),
        "turns_removed": removed,
    }
    return final, report, usages


def step(ep: Episode, prefs: Preferences, session: Session) -> None:
    articles = [Article.model_validate(a) for a in ep.work["articles"]]
    draft = Script.model_validate(ep.work["draft_script"])
    ids, hosts = {a.id for a in articles}, len(prefs.hosts)
    final, report, usages = verify(
        draft,
        lambda s: check_script(s, articles),
        lambda s, issues: writer.revise_script(s, issues, articles, ids, hosts),
    )
    for usage in usages:
        add_cost(ep, usage)
    save_work(ep, "checker_report", report)
    save_work(ep, "final_script", final.model_dump())
