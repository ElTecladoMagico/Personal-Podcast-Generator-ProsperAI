from sqlmodel import Session

from app import jobs
from app.db import engine
from app.models import Episode, User


def test_recovery_resubmits_only_unfinished_episodes():
    with Session(engine) as s:
        user = User(clerk_id="user_jobs")
        s.add(user)
        s.flush()
        eps = {
            status: Episode(
                user_id=user.id, trigger="manual", language="en", prefs_snapshot={}, status=status
            )
            for status in ["queued", "writing", "recording", "ready", "failed"]
        }
        s.add_all(eps.values())
        s.commit()
        expected = {eps["queued"].id, eps["writing"].id, eps["recording"].id}

    submitted = []
    assert set(jobs.recover_interrupted(submit=submitted.append)) == expected
    assert set(submitted) == expected


def test_errors_outside_the_steps_are_logged_not_swallowed(monkeypatch, caplog):
    import uuid

    def boom(episode_id):
        raise RuntimeError("database down")

    monkeypatch.setattr(jobs, "generate_episode", boom)
    jobs.run_in_pool(uuid.uuid4()).result()  # the thread logs it and finishes cleanly
    assert "database down" in caplog.text
