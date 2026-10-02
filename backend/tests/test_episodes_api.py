from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app.db import engine
from app.models import Episode, User
from app.routers import episodes as episodes_router

PREFS = {
    "interests": [{"topic": "AI"}],
    "hosts": [{"name": "Sara", "voice_id": "v1"}, {"name": "Martín", "voice_id": "v2"}],
}


@pytest.fixture
def submitted(monkeypatch):
    calls = []
    monkeypatch.setattr(episodes_router, "run_in_pool", calls.append)
    return calls


@pytest.fixture
def onboarded(client):
    client.get("/me")  # creates the user
    with Session(engine) as s:
        user = s.exec(select(User)).one()
        user.preferences, user.onboarded_at = PREFS, datetime.now(UTC)
        s.commit()
        return user.id


def set_status(ep_id, **fields):
    with Session(engine) as s:
        ep = s.get(Episode, ep_id)
        for k, v in fields.items():
            setattr(ep, k, v)
        s.commit()


def test_generate_now_queues_an_episode(client, onboarded, submitted):
    r = client.post("/episodes")
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "queued" and submitted == [__import__("uuid").UUID(body["id"])]
    assert client.get("/episodes").json()[0]["id"] == body["id"]


def test_requires_onboarding(client, submitted):
    client.get("/me")
    assert client.post("/episodes").status_code == 400


def test_one_episode_in_progress_at_a_time(client, onboarded, submitted):
    first = client.post("/episodes").json()
    assert client.post("/episodes").status_code == 409
    set_status(first["id"], status="ready")
    assert client.post("/episodes").status_code == 201


def test_daily_limit_counts_manual_episodes_but_not_failed_ones(
    client, onboarded, submitted, monkeypatch
):
    monkeypatch.setattr(episodes_router.settings, "max_manual_episodes_per_day", 2)
    for status in ["ready", "failed", "ready"]:
        ep = client.post("/episodes").json()
        set_status(ep["id"], status=status)
    r = client.post("/episodes")
    assert r.status_code == 429
    ep_id = client.get("/episodes").json()[0]["id"]
    set_status(ep_id, created_at=datetime.now(UTC) - timedelta(hours=25))
    assert client.post("/episodes").status_code == 201


def test_progress_reports_real_numbers_while_generating(client, onboarded, submitted):
    ep = client.post("/episodes").json()
    work = {
        "candidates": [
            {
                "id": f"c{i}",
                "title": "t",
                "source": f"outlet{i % 3}",
                "url": "u",
                "published_at": None,
                "snippet": None,
                "origin": "hn",
                "interest": "AI",
            }
            for i in range(7)
        ],
        "selection": {
            "picks": [
                {
                    "story_id": "s1",
                    "headline": "Chips",
                    "candidate_ids": ["c1"],
                    "interest": "AI",
                    "why_it_matters": "w",
                    "follow_up_of": None,
                }
            ],
            "backups": [],
        },
        "recording": {"done": 2, "total": 5},
    }
    set_status(ep["id"], status="recording", work=work)
    p = client.get(f"/episodes/{ep['id']}").json()["progress"]
    assert (p["candidates"], p["outlets"], p["stories"]) == (7, 3, ["Chips"])
    assert p["recording"] == {"done": 2, "total": 5}


def test_ready_episode_has_signed_audio_and_sources(client, onboarded, submitted):
    ep = client.post("/episodes").json()
    work = {
        "articles": [
            {
                "id": "a1",
                "story_id": "s1",
                "url": "https://x.test/a",
                "source": "x.test",
                "title": "A",
                "text": "secret long text",
                "image_url": None,
            }
        ]
    }
    script = {"title": "T", "summary": "S", "chapters": []}
    set_status(
        ep["id"],
        status="ready",
        work=work,
        script=script,
        audio_path="u/e.mp3",
        title="T",
        duration_s=120.0,
    )
    detail = client.get(f"/episodes/{ep['id']}").json()
    with Session(engine) as s:
        token = s.get(User, onboarded).feed_token
    assert detail["audio_url"].endswith(f"/audio/{ep['id']}.mp3?k={token}")
    assert detail["sources"] == {
        "a1": {"title": "A", "url": "https://x.test/a", "source": "x.test", "image_url": None}
    }
    assert detail["script"]["title"] == "T" and "secret" not in str(detail)


def test_other_users_episodes_are_404(client, onboarded, submitted, claims):
    ep = client.post("/episodes").json()
    claims["sub"] = "someone_else"
    assert client.get(f"/episodes/{ep['id']}").status_code == 404
    assert client.post(f"/episodes/{ep['id']}/retry").status_code == 404


def test_retry_only_failed_and_resumes_at_failed_stage(client, onboarded, submitted):
    ep = client.post("/episodes").json()
    assert client.post(f"/episodes/{ep['id']}/retry").status_code == 409  # still queued
    set_status(ep["id"], status="failed", failed_stage="recording", error="boom")
    r = client.post(f"/episodes/{ep['id']}/retry")
    assert r.status_code == 200 and r.json()["status"] == "queued"
    with Session(engine) as s:
        assert s.get(Episode, ep["id"]).failed_stage == "recording"
    assert len(submitted) == 2
