"""Metrics on a tiny hand-written dataset, so every expected number can be checked by eye.

Range: the 7 days 2026-09-26 … 2026-10-02 (UTC).
- Ana (real): signs up 09-28, listens 90 % of her first episode an hour later (activated), 👍 the
  AI story, skips the F1 one; downloads it from her podcast app on 09-30.
- Bea (real): signs up 09-29, listens 25 % on 10-01, 👎 the AI story.
- Cris (real): signs up 09-30, never finishes onboarding.
- Dani (real): signs up 09-30, her scheduled episode fails while recording.
- Mock (simulated): signs up 09-27 and listens to everything. Only with include_mock.
"""

from datetime import UTC, date, datetime

import pytest
from sqlmodel import Session

from app import metrics
from app.db import engine
from app.models import Episode, Event, User

TODAY = date(2026, 10, 2)
PICKS = {
    "selection": {
        "picks": [{"story_id": "s1", "interest": "IA"}, {"story_id": "s2", "interest": "F1"}]
    }
}


def at(day: int, hour: int = 10, month: int = 9) -> datetime:
    return datetime(2026, month, day, hour, tzinfo=UTC)


@pytest.fixture(autouse=True)
def dataset():
    with Session(engine) as s:

        def user(name, created, onboarded=True, mock=False):
            u = User(
                clerk_id=name,
                created_at=created,
                onboarded_at=created if onboarded else None,
                is_mock=mock,
            )
            s.add(u)
            s.flush()
            return u

        def episode(u, created, **fields):
            ep = Episode(
                user_id=u.id,
                trigger="manual",
                language="es",
                prefs_snapshot={},
                created_at=created,
                work=PICKS,
                **fields,
            )
            s.add(ep)
            s.flush()
            return ep

        def event(u, kind, ts, ep=None, **props):
            s.add(
                Event(user_id=u.id, type=kind, ts=ts, episode_id=ep.id if ep else None, props=props)
            )

        ana, bea = user("ana", at(28)), user("bea", at(29))
        user("cris", at(30), onboarded=False)
        dani = user("dani", at(30))
        mock = user("mock", at(27), mock=True)

        e1 = episode(
            ana,
            at(28),
            status="ready",
            duration_s=100,
            stage_timings={"fetching": 2, "writing": 10},
            cost={"llm_usd": 0.02, "tts_chars": 1000},
        )
        e2 = episode(
            bea,
            at(29),
            status="ready",
            duration_s=200,
            stage_timings={"fetching": 4, "writing": 20},
            cost={"llm_usd": 0.04, "tts_chars": 2000},
        )
        episode(dani, at(30), status="failed", failed_stage="recording", trigger="scheduled")
        e4 = episode(
            mock,
            at(27),
            status="ready",
            duration_s=100,
            stage_timings={"fetching": 9},
            cost={"llm_usd": 0.10, "tts_chars": 9000},
        )

        event(ana, "onboarding_completed", at(28), method="import")
        event(bea, "onboarding_completed", at(29), method="manual")
        event(dani, "onboarding_completed", at(30), method="manual")
        event(ana, "episode_ready", at(28), e1, issues_found=2, issues_fixed=1)
        event(bea, "episode_ready", at(29), e2, issues_found=0, issues_fixed=0)
        event(ana, "play_started", at(28, 11), e1, position_s=0)
        event(ana, "chapter_started", at(28, 11), e1, chapter_index=1, story_id="s1")
        event(ana, "feedback", at(28, 11), e1, story_id="s1", value="up")
        event(ana, "chapter_started", at(28, 11), e1, chapter_index=2, story_id="s2")
        event(ana, "chapter_skipped", at(28, 11), e1, chapter_index=2, story_id="s2", after_s=3)
        event(ana, "listen_progress", at(28, 11), e1, max_position_s=90, duration_s=100)
        event(ana, "feed_download", at(30), e1)
        event(bea, "listen_progress", at(1, month=10), e2, max_position_s=50, duration_s=200)
        event(bea, "feedback", at(1, month=10), e2, story_id="s1", value="down")
        event(mock, "listen_progress", at(27), e4, max_position_s=100, duration_s=100)
        s.commit()


def real() -> dict:
    return metrics.dashboard(TODAY, days=7, include_mock=False)


def test_growth_counts_signups_and_listeners_per_day():
    growth = real()["growth"]
    daily = {d["day"]: d for d in growth["daily"]}
    assert len(daily) == 7 and daily["2026-09-30"]["signups"] == 2
    assert [daily[f"2026-{d}"]["dau"] for d in ("09-28", "09-29", "09-30", "10-01")] == [1, 0, 1, 1]
    assert daily["2026-10-01"]["wau"] == 2  # Ana (09-30) and Bea in the 7 days up to 10-01
    assert growth["funnel"] == [
        {"step": "signed_up", "users": 4},
        {"step": "onboarded", "users": 3},
        {"step": "first_episode", "users": 2},
        {"step": "listened_80", "users": 1},
    ]


def test_kpis():
    k = real()["kpis"]
    assert k["mau"] == 2 and k["activation"] == 0.25  # only Ana, within 48 h of signing up
    assert k["stickiness"] == pytest.approx((3 / 7) / 2)
    assert k["completion"] == pytest.approx((0.9 + 0.25) / 2)
    assert k["thumbs_up"] == 0.5
    assert k["cost_per_episode"] == pytest.approx(0.03 + 1500 * metrics.TTS_USD_PER_CHAR)


def test_retention_follows_each_cohort_week_by_week():
    [cohort] = real()["growth"]["retention"]  # all four signed up in the week of 09-28
    assert cohort["cohort"] == "2026-09-28" and cohort["users"] == 4
    assert cohort["weeks"][0] == 0.5  # Ana and Bea listened in their first 7 days


def test_content_completion_skips_topics_and_rss():
    c = real()["content"]
    assert {b["bucket"]: b["listens"] for b in c["completion"] if b["listens"]} == {2: 1, 9: 1}
    assert {p["position"]: p["skip_rate"] for p in c["skips_by_position"]} == {1: 0.0, 2: 1.0}
    topics = {t["topic"]: t for t in c["topics"]}
    assert topics["IA"]["thumbs_up"] == 0.5 and topics["F1"]["skip_rate"] == 1.0
    assert c["rss_adoption"] == 0.5 and c["import_share"] == pytest.approx(1 / 3)


def test_operations_latency_failures_cost_and_fact_checking():
    ops = real()["operations"]
    stages = {s["stage"]: s for s in ops["stages"]}
    assert stages["fetching"]["p50"] == 3.0 and stages["writing"]["p50"] == 15.0
    assert stages["recording"]["failures"] == 1 and ops["requested"] == 3
    day = {d["day"]: d for d in ops["daily"]}["2026-09-30"]
    assert (day["manual"], day["scheduled"], day["failed"]) == (0, 1, 1)
    assert ops["checker"] == {"episodes": 2, "with_issues": 1, "issues_found": 2, "issues_fixed": 1}


def test_mock_data_only_when_asked():
    with_mock = metrics.dashboard(TODAY, days=7, include_mock=True)
    assert with_mock["kpis"]["mau"] == 3 and real()["kpis"]["mau"] == 2
    assert {d["day"]: d["signups"] for d in with_mock["growth"]["daily"]}["2026-09-27"] == 1
