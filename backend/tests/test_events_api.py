import pytest
from sqlmodel import Session, select

from app.db import engine
from app.models import Episode, Event, User


@pytest.fixture
def episode_id(client):
    client.get("/me")
    with Session(engine) as s:
        user = s.exec(select(User)).one()
        ep = Episode(
            user_id=user.id, trigger="manual", language="es", prefs_snapshot={}, status="ready"
        )
        s.add(ep)
        s.commit()
        return str(ep.id)


def stored(kind: str) -> list[Event]:
    with Session(engine) as s:
        return list(s.exec(select(Event).where(Event.type == kind)))


def test_player_events_are_stored(client, episode_id):
    body = {
        "type": "feedback",
        "episode_id": episode_id,
        "props": {"story_id": "s1", "value": "up"},
    }
    assert client.post("/events", json=body).status_code == 204
    [event] = stored("feedback")
    assert event.props == {"story_id": "s1", "value": "up"} and str(event.episode_id) == episode_id


@pytest.mark.parametrize("kind", ["episode_ready", "user_signed_up", "made_up"])
def test_only_frontend_event_types_are_accepted(client, episode_id, kind):
    r = client.post("/events", json={"type": kind, "episode_id": episode_id, "props": {}})
    assert r.status_code == 422
    assert [e for e in stored(kind) if e.episode_id is not None] == []  # nothing forged


def test_someone_elses_episode_is_404(client, episode_id, claims):
    claims["sub"] = "intruder"
    r = client.post("/events", json={"type": "play_started", "episode_id": episode_id, "props": {}})
    assert r.status_code == 404


def test_props_over_2kb_are_rejected(client, episode_id):
    r = client.post(
        "/events",
        json={"type": "listen_progress", "episode_id": episode_id, "props": {"junk": "x" * 3000}},
    )
    assert r.status_code == 413
