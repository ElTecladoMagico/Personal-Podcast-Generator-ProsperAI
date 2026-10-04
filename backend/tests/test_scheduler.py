from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app import jobs, storage
from app.db import engine
from app.models import Episode, User

NOW = datetime(2026, 10, 2, 4, 45, tzinfo=UTC)  # 06:45 in Madrid, just past the 06:40 start
PREFS = {
    "interests": [{"topic": "AI"}],
    "format": "solo",
    "hosts": [{"name": "Sara", "voice_id": "v1"}],
}


def user(name: str, **fields) -> User:
    defaults = {
        "preferences": PREFS,
        "onboarded_at": NOW,
        "next_run_at": NOW - timedelta(minutes=5),
    }
    with Session(engine) as s:
        u = User(clerk_id=name, **(defaults | fields))
        s.add(u)
        s.commit()
        s.refresh(u)
        return u


def test_due_user_gets_one_scheduled_episode_and_the_next_slot():
    u = user("due")
    submitted = []
    created = jobs.enqueue_due(NOW, submit=submitted.append)
    with Session(engine) as s:
        ep = s.exec(select(Episode)).one()
        assert ep.trigger == "scheduled" and ep.user_id == u.id
        assert s.get(User, u.id).next_run_at == datetime(2026, 10, 3, 4, 40, tzinfo=UTC)
    assert created == submitted == [ep.id]


def test_user_with_an_episode_in_progress_is_skipped_but_still_advances():
    u = user("busy")
    with Session(engine) as s:
        s.add(
            Episode(
                user_id=u.id, trigger="manual", language="en", prefs_snapshot={}, status="writing"
            )
        )
        s.commit()
    assert jobs.enqueue_due(NOW, submit=lambda _: None) == []
    with Session(engine) as s:
        assert len(s.exec(select(Episode)).all()) == 1
        assert s.get(User, u.id).next_run_at > NOW


def test_mock_not_onboarded_and_future_users_are_ignored():
    user("mock", is_mock=True)
    user("new", onboarded_at=None)
    user("later", next_run_at=NOW + timedelta(minutes=1))
    user("off", next_run_at=None)
    assert jobs.enqueue_due(NOW, submit=lambda _: None) == []


def test_audio_older_than_30_days_is_deleted_but_the_episode_stays(tmp_path, monkeypatch):
    monkeypatch.setattr(storage.settings, "audio_dir", str(tmp_path))
    u = user("listener")
    files = {}
    with Session(engine) as s:
        for name, age in [("old", 31), ("recent", 29)]:
            ep = Episode(
                user_id=u.id,
                trigger="manual",
                language="en",
                prefs_snapshot={},
                status="ready",
                finished_at=NOW - timedelta(days=age),
            )
            relpath, path = storage.new_audio_file(u.id, ep.id)
            path.write_bytes(b"mp3")
            answer = storage.audio_file(storage.ask_relpath(u.id, ep.id, "abcd1234"))
            answer.parent.mkdir(parents=True)
            answer.write_bytes(b"answer")  # an "Ask the hosts" reply
            ep.audio_path, files[name] = relpath, (ep.id, path)
            s.add(ep)
        s.commit()

    assert jobs.cleanup_audio(NOW) == 1
    with Session(engine) as s:
        old_id, old_path = files["old"]
        assert not old_path.exists() and s.get(Episode, old_id).audio_expired
        assert not old_path.with_suffix("").exists()  # its answers folder too
        recent_id, recent_path = files["recent"]
        assert recent_path.exists() and not s.get(Episode, recent_id).audio_expired
    assert jobs.cleanup_audio(NOW) == 0  # already expired ones are not touched again
