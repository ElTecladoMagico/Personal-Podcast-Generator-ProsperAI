import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import storage
from app.db import engine
from app.main import app
from app.models import Episode, User


@pytest.fixture
def episode(tmp_path, monkeypatch):
    monkeypatch.setattr(storage.settings, "audio_dir", str(tmp_path))
    with Session(engine) as s:
        user = User(clerk_id="user_audio")
        s.add(user)
        s.flush()
        ep = Episode(user_id=user.id, trigger="manual", language="en", prefs_snapshot={})
        ep.audio_path = storage.audio_relpath(user.id, ep.id)
        s.add(ep)
        s.commit()
        path = storage.audio_file(ep.audio_path)
        path.parent.mkdir(parents=True)
        path.write_bytes(b"ID3" + bytes(997))
        return ep.id, user.feed_token


def test_audio_is_served_with_range_support(episode):
    ep_id, token = episode
    client = TestClient(app)
    full = client.get(f"/audio/{ep_id}.mp3", params={"k": token})
    assert full.status_code == 200 and full.headers["content-type"] == "audio/mpeg"
    assert len(full.content) == 1000

    part = client.get(f"/audio/{ep_id}.mp3", params={"k": token}, headers={"Range": "bytes=0-1"})
    assert part.status_code == 206 and part.content == b"ID"
    assert part.headers["content-range"] == "bytes 0-1/1000"


def test_wrong_token_or_unknown_episode_is_404(episode):
    ep_id, _ = episode
    client = TestClient(app)
    assert client.get(f"/audio/{ep_id}.mp3", params={"k": "nope"}).status_code == 404
    assert (
        client.get("/audio/00000000-0000-0000-0000-000000000000.mp3", params={"k": "x"}).status_code
        == 404
    )
    assert client.get(f"/audio/{ep_id}.mp3").status_code == 422  # token is required


def test_expired_audio_is_410(episode):
    ep_id, token = episode
    with Session(engine) as s:
        ep = s.get(Episode, ep_id)
        ep.audio_expired = True
        s.commit()
    assert TestClient(app).get(f"/audio/{ep_id}.mp3", params={"k": token}).status_code == 410
