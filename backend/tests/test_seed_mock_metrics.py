from datetime import date

from sqlmodel import Session, func, select

from app import metrics
from app.db import engine
from app.models import Episode, Event, User
from scripts.seed_mock_metrics import reset, seed

TODAY = date(2026, 10, 2)


def counts() -> tuple[int, int, int]:
    with Session(engine) as s:
        return tuple(s.exec(select(func.count()).select_from(t)).one() for t in (User, Episode, Event))


def test_seed_is_deterministic_mock_only_and_leaves_real_users_alone():
    with Session(engine) as s:
        s.add(User(clerk_id="real_listener"))
        s.commit()

    seed(users=30, days=21, rng_seed=7, today=TODAY)
    first = counts()
    reset()
    seed(users=30, days=21, rng_seed=7, today=TODAY)
    assert counts() == first  # same seed, same data
    with Session(engine) as s:
        assert s.exec(select(func.count()).where(User.is_mock)).one() == 30
        assert not s.exec(select(Episode).where(Episode.audio_path.is_not(None))).first()  # no MP3s

    reset()
    assert counts() == (1, 0, 0)  # only the real listener is left


def test_seeded_data_fills_every_block_of_the_dashboard():
    seed(users=60, days=30, rng_seed=42, today=TODAY)
    d = metrics.dashboard(TODAY, days=30, include_mock=True)
    k = d["kpis"]
    assert k["mau"] > 10 and 0 < k["activation"] < 1 and 0 < k["completion"] < 1
    assert 0 < k["thumbs_up"] < 1 and k["cost_per_episode"] > 0
    assert d["growth"]["retention"] and d["content"]["topics"] and d["operations"]["stages"]
    assert metrics.dashboard(TODAY, days=30, include_mock=False)["kpis"]["mau"] == 0
