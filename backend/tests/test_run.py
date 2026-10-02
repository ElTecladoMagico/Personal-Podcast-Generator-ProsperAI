from sqlmodel import Session, select

from app.db import engine
from app.models import Episode, Event, Story, User
from app.pipeline import run
from app.pipeline.state import FactCheck
from app.schemas import Article, CheckerReport, EditorPick, EditorSelection, Script, Usage

PREFS = {
    "interests": [{"topic": "AI"}],
    "hosts": [{"name": "Sarah", "voice_id": "v1"}, {"name": "George", "voice_id": "v2"}],
}
SCRIPT = {
    "title": "Chips and chatbots",
    "summary": "Two stories about AI.",
    "chapters": [
        {"story_id": None, "title": "Intro", "turns": []},
        {"story_id": "s1", "title": "New chip", "turns": []},
    ],
}


def new_episode() -> Episode:
    with Session(engine) as s:
        user = User(clerk_id="user_run", preferences=PREFS)
        s.add(user)
        s.flush()
        ep = run.new_episode(s, user, trigger="manual")
        s.refresh(ep)
        s.expunge(ep)
        return ep


PICK = EditorPick(
    story_id="s1",
    headline="Chip",
    candidate_ids=["c1"],
    interest="AI",
    why_it_matters="Faster phones.",
    follow_up_of=None,
)
ARTICLE = Article(
    id="a1",
    story_id="s1",
    url="https://x.test/chip",
    source="x.test",
    title="Chip",
    text="t",
    image_url=None,
)


def fake_steps(calls: list[str], fail_at: str | None = None):
    """Steps that fill the Work like the real ones would, spending 0.01 USD each."""

    def step(name):
        def fn(ep, prefs, work, session):
            calls.append(name)
            if name == fail_at:
                raise RuntimeError(f"{name} exploded")
            if name == "editing":
                work.selection = EditorSelection(picks=[PICK], backups=[])
            if name == "researching":
                work.articles, work.stories = [ARTICLE], ["s1"]
            if name == "verifying":
                work.final_script = Script.model_validate(SCRIPT)
                work.checker_report = FactCheck(
                    first=CheckerReport(issues=[], verdict="fix"), issues_found=2, issues_fixed=1
                )
            usage = Usage(llm_usd=0.01, tokens_in=100, tokens_out=10)
            if name == "recording":
                ep.script, ep.audio_path, ep.duration_s = SCRIPT, "u/e.mp3", 120.0
                usage += Usage(tts_chars=1800)
            return usage

        return fn

    return {name: step(name) for name in run.STAGES}


def load(ep_id) -> Episode:
    with Session(engine) as s:
        ep = s.get(Episode, ep_id)
        s.expunge(ep)
        return ep


def events(ep_id) -> list[Event]:
    with Session(engine) as s:
        return list(s.exec(select(Event).where(Event.episode_id == ep_id)))


def test_new_episode_snapshots_prefs_and_logs_the_request():
    ep = new_episode()
    assert ep.status == "queued" and ep.trigger == "manual" and ep.language == "en"
    assert ep.prefs_snapshot["interests"] == [{"topic": "AI", "why": None, "weight": 3}]
    assert [e.type for e in events(ep.id)] == ["episode_requested"]


def test_happy_path_runs_every_stage_and_finishes_ready():
    ep, calls = new_episode(), []
    run.generate_episode(ep.id, steps=fake_steps(calls))
    done = load(ep.id)

    assert calls == run.STAGES
    assert done.status == "ready" and done.failed_stage is None
    assert (done.title, done.summary) == ("Chips and chatbots", "Two stories about AI.")
    assert set(done.stage_timings) == set(run.STAGES)
    assert done.cost == {"llm_usd": 0.06, "tokens_in": 600, "tokens_out": 60, "tts_chars": 1800}
    assert done.started_at and done.finished_at
    ready = [e for e in events(ep.id) if e.type == "episode_ready"][0]
    assert ready.props["issues_found"] == 2 and ready.props["duration_s"] == 120.0
    with Session(engine) as s:  # one memory row per story chapter
        story = s.exec(select(Story).where(Story.episode_id == ep.id)).one()
    assert (story.title, story.topic, story.urls) == ("Chip", "AI", ["https://x.test/chip"])


def test_a_failing_stage_marks_failed_and_retry_resumes_there():
    ep, calls = new_episode(), []
    run.generate_episode(ep.id, steps=fake_steps(calls, fail_at="writing"))
    failed = load(ep.id)
    assert failed.status == "failed" and failed.failed_stage == "writing"
    assert failed.error == "writing exploded"
    assert failed.work["selection"] and failed.work["draft_script"] is None
    assert events(ep.id)[-1].type == "episode_failed"
    assert events(ep.id)[-1].props == {"stage": "writing", "error": "writing exploded"}

    calls.clear()
    run.generate_episode(ep.id, steps=fake_steps(calls))
    assert calls == ["writing", "verifying", "recording"]  # earlier work is reused
    assert load(ep.id).status == "ready"


def test_effective_minutes_are_capped_by_settings(monkeypatch):
    from app.schemas import Preferences

    prefs = Preferences.model_validate(PREFS | {"duration_min": 20})
    from app.pipeline import state

    monkeypatch.setattr(state.settings, "episode_max_minutes", 2)
    assert state.effective_minutes(prefs) == 2
    monkeypatch.setattr(state.settings, "episode_max_minutes", 10)
    assert state.effective_minutes(prefs) == 10


def test_news_window_starts_at_last_episode_but_stays_between_one_day_and_the_default():
    from datetime import UTC, datetime, timedelta

    from app.pipeline.reporter import news_window_start
    from app.schemas import Preferences

    now = datetime(2026, 10, 1, 7, 0, tzinfo=UTC)
    daily = Preferences.model_validate(PREFS)
    weekly = Preferences.model_validate(PREFS | {"schedule": {"frequency": "weekly", "weekday": 0}})
    assert news_window_start(None, daily, now) == now - timedelta(days=2)
    assert news_window_start(None, weekly, now) == now - timedelta(days=8)
    assert news_window_start(now - timedelta(hours=30), daily, now) == now - timedelta(hours=30)
    assert news_window_start(now - timedelta(hours=3), daily, now) == now - timedelta(days=1)
    assert news_window_start(now - timedelta(days=20), daily, now) == now - timedelta(days=2)


def test_an_interrupted_episode_resumes_at_the_stage_it_was_in():
    ep, calls = new_episode(), []
    run.generate_episode(ep.id, steps=fake_steps(calls, fail_at="recording"))
    with Session(engine) as s:  # simulate a crash during recording: no failed_stage recorded
        row = s.get(Episode, ep.id)
        row.status, row.failed_stage, row.error = "recording", None, None
        s.commit()
    calls.clear()
    run.generate_episode(ep.id, steps=fake_steps(calls))
    assert calls == ["recording"] and load(ep.id).status == "ready"
