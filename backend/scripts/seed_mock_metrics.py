"""Simulated listeners for the internal dashboard (ADR 0013): believable trends, reproducible.

Run from backend/:  uv run python -m scripts.seed_mock_metrics [--users 200] [--days 90] [--seed 42]
It replaces the previous simulated data. Every row it writes belongs to a user with
is_mock = true, so the dashboard can show or hide it and the scheduler never picks them up.

The shape of the simulation (all tunable below):
- sign-ups grow over time; 80 % finish onboarding, 45 % of them by importing from their AI;
- each listener has an engagement level that fades with the days;
- episodes follow each listener's schedule; 3 % fail, mostly while recording or fetching;
- listeners skip low-priority topics and late stories more, and 👍 about 70 % of their votes;
- a third of them listen in a podcast app (feed_download) instead of the web player.
"""

import argparse
import math
import random
import secrets
import uuid
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import delete, insert, select
from sqlmodel import Session

from app.db import engine
from app.models import Episode, Event, Story, User
from app.pipeline.run import STAGES

TOPICS = [
    "Inteligencia artificial", "Startups", "Ciberseguridad", "Vivienda", "Bolsa", "Fórmula 1",
    "LaLiga", "Tenis", "Espacio", "Cambio climático", "Medicina", "Cine y series", "Música",
    "Política española", "Unión Europea", "Geopolítica", "Videojuegos", "Economía",
]  # fmt: skip
FREQUENCIES = {"daily": 0.6, "weekdays": 0.25, "weekly": 0.1, "off": 0.05}
STAGE_MEDIAN_S = {"fetching": 2, "editing": 12, "researching": 6, "writing": 15,
                  "verifying": 4, "recording": 25}  # fmt: skip
FAILURE_STAGE = {"recording": 0.4, "fetching": 0.3, "writing": 0.15, "editing": 0.1,
                 "verifying": 0.05}  # fmt: skip
FAILURE_RATE = 0.03
FIRST_LISTEN = 0.75  # share who play the first episode they asked for
ASKERS = 0.2  # listeners who ask the hosts at all; they ask in 30 % of their listens
CHARS_PER_SECOND = 14  # what the voices read: ~8,500 characters for 10 minutes


def pick(rng: random.Random, weights: dict[str, float]) -> str:
    return rng.choices(list(weights), list(weights.values()))[0]


def runs_on(frequency: str, day: date, weekday: int) -> bool:
    if frequency == "daily":
        return True
    if frequency == "weekdays":
        return day.weekday() < 5
    return frequency == "weekly" and day.weekday() == weekday


def reset() -> None:
    """Delete every simulated row (children first)."""
    mock = select(User.id).where(User.is_mock)
    with Session(engine) as s:
        for table in (Event, Story, Episode):
            s.execute(delete(table).where(table.user_id.in_(mock)))
        s.execute(delete(User).where(User.is_mock))
        s.commit()


def seed(users: int = 200, days: int = 90, rng_seed: int = 42, today: date | None = None) -> None:
    rng = random.Random(rng_seed)
    today = today or datetime.now(UTC).date()
    first_day = today - timedelta(days=days - 1)
    rows = {User: [], Episode: [], Event: []}

    def event(user_id, kind, ts, episode_id=None, **props):
        rows[Event].append(
            {"user_id": user_id, "type": kind, "ts": ts, "episode_id": episode_id, "props": props}
        )

    for n in range(users):
        user_id = uuid.UUID(int=rng.getrandbits(128))
        # More sign-ups lately: sqrt pushes the draw towards the end of the range.
        signup_day = first_day + timedelta(days=int(days * math.sqrt(rng.random())))
        signed_up = datetime.combine(signup_day, time(rng.randrange(7, 23), rng.randrange(60)), UTC)
        onboarded = rng.random() < 0.8
        interests = [
            {"topic": t, "weight": rng.randint(1, 5)} for t in rng.sample(TOPICS, rng.randint(3, 5))
        ]
        frequency = pick(rng, FREQUENCIES)
        weekday = rng.randrange(7)
        rows[User].append({
            "id": user_id, "clerk_id": f"mock_{rng_seed}_{n}", "email": None,
            "display_name": f"Oyente {n}", "is_mock": True, "created_at": signed_up,
            "onboarded_at": signed_up + timedelta(minutes=2) if onboarded else None,
            "feed_token": secrets.token_urlsafe(32), "next_run_at": None,
            "preferences": {"interests": interests, "schedule": {"frequency": frequency}},
        })  # fmt: skip
        event(user_id, "user_signed_up", signed_up)
        if not onboarded:
            continue
        method = "import" if rng.random() < 0.45 else "manual"
        event(user_id, "onboarding_completed", signed_up + timedelta(minutes=2), method=method)

        engagement = rng.betavariate(2, 3)  # how much this listener cares, 0..1
        half_life = rng.uniform(4, 30)  # days until their habit halves
        podcast_app = rng.random() < 0.35
        ask_rate = 0.3 if rng.random() < ASKERS else 0.0
        # The first episode right after onboarding, then whatever their schedule says.
        add_episode(rng, rows, event, user_id, signed_up + timedelta(minutes=3), "manual",
                    interests, rng.random() < FIRST_LISTEN, podcast_app, ask_rate)  # fmt: skip
        for offset in range(1, (today - signup_day).days + 1):
            day = signup_day + timedelta(days=offset)
            if runs_on(frequency, day, weekday):
                habit = engagement * 0.5 ** (offset / half_life)
                add_episode(rng, rows, event, user_id, datetime.combine(day, time(6, 40), UTC),
                            "scheduled", interests, rng.random() < habit, podcast_app,
                            ask_rate)  # fmt: skip

    with Session(engine) as s:
        for table, values in rows.items():
            if values:
                s.execute(insert(table), values)
        s.commit()


def add_episode(rng, rows, event, user_id, at, trigger, interests, listens, podcast_app, ask_rate):
    episode_id = uuid.UUID(int=rng.getrandbits(128))
    stories = [
        {"story_id": f"s{i + 1}", "interest": t["topic"]}
        for i, t in enumerate(rng.sample(interests, 3))
    ]
    failed = rng.random() < FAILURE_RATE
    duration = rng.uniform(300, 640)
    timings = {s: round(STAGE_MEDIAN_S[s] * rng.lognormvariate(0, 0.35), 1) for s in STAGES}
    failed_stage = pick(rng, FAILURE_STAGE) if failed else None
    finished = at + timedelta(seconds=sum(timings.values()))
    rows[Episode].append({
        "id": episode_id, "user_id": user_id, "trigger": trigger, "language": "es",
        "status": "failed" if failed else "ready", "failed_stage": failed_stage,
        "error": "simulated failure" if failed else None, "prefs_snapshot": {},
        "work": {"selection": {"picks": stories, "backups": []}}, "title": "Episodio simulado",
        "summary": None, "script": None, "audio_path": None, "audio_expired": True,
        "duration_s": None if failed else duration,
        "cost": {"llm_usd": round(max(rng.gauss(0.09, 0.02), 0.02), 4),
                 "tts_chars": int(duration * CHARS_PER_SECOND), "tokens_in": 0, "tokens_out": 0},
        "stage_timings": {} if failed else timings, "created_at": at, "started_at": at,
        "finished_at": finished,
    })  # fmt: skip
    event(user_id, "episode_requested", at, episode_id, trigger=trigger)
    if failed:
        event(
            user_id, "episode_failed", finished, episode_id, stage=failed_stage, error="simulated"
        )
        return
    found = min(int(rng.expovariate(1.4)), 4)
    event(user_id, "episode_ready", finished, episode_id, duration_s=duration,
          issues_found=found, issues_fixed=rng.randint(0, found))  # fmt: skip
    if not listens:
        return

    t = finished + timedelta(minutes=rng.randint(5, 180))
    if podcast_app:  # the app downloads it; we never see what happens inside it
        event(user_id, "feed_download", t, episode_id)
        return
    event(user_id, "play_started", t, episode_id, position_s=0)
    weights = {i["topic"]: i["weight"] for i in interests}
    reached = 0.0
    for position, story in enumerate(stories, start=1):
        story_id, weight = story["story_id"], weights[story["interest"]]
        event(user_id, "chapter_started", t, episode_id, chapter_index=position, story_id=story_id)
        if rng.random() < 0.15:
            up = rng.random() < 0.55 + 0.05 * weight
            event(
                user_id, "feedback", t, episode_id, story_id=story_id, value="up" if up else "down"
            )
        # Low-priority topics and later stories get skipped more.
        if rng.random() < 0.05 + 0.04 * position + 0.06 * (3 - weight):
            event(user_id, "chapter_skipped", t, episode_id, chapter_index=position,
                  story_id=story_id, after_s=rng.randint(5, 40))  # fmt: skip
        reached = position / len(stories)
        if rng.random() < 0.12:  # stopped listening here
            break
    if rng.random() < ask_rate:  # paused to ask the hosts about one of the stories
        latency = round(10 * rng.lognormvariate(0, 0.25), 2)  # ~10 s, as measured: LLM + voice
        event(user_id, "ask_asked", t, episode_id, chapter_index=rng.randint(1, len(stories)),
              latency_s=latency, chars=rng.randint(250, 450))  # fmt: skip
    completion = min(reached * rng.betavariate(8, 1.5), 1)
    event(user_id, "listen_progress", t + timedelta(seconds=duration * completion), episode_id,
          max_position_s=round(duration * completion), duration_s=round(duration))  # fmt: skip


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--users", type=int, default=200)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    reset()
    seed(args.users, args.days, args.seed)
    print(f"Seeded {args.users} simulated listeners over {args.days} days (seed {args.seed}).")
