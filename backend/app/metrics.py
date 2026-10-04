"""Product metrics for the internal dashboard (ADR 0013): is the product working?

Everything comes from two tables: `events` (what listeners did) and `episodes` (what the
newsroom produced). Each block is a few readable SQL queries, computed on the fly for a range of
whole UTC days. Simulated users (`users.is_mock`) are left out unless asked for.

ponytail: no cache or materialized views; the seeded ~150k events answer in well under a second.
Add them when that stops being true.
"""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import text
from sqlmodel import Session

from app.db import engine
from app.pipeline.run import STAGES

# ElevenLabs Creator plan: 100k credits for 22 USD; eleven_v3 spends 1 credit per character.
TTS_USD_PER_CHAR = 22 / 100_000
# A listener is "active" on a day they did anything with an episode, in the app or a podcast app.
ACTIVE_EVENTS = [
    "play_started",
    "chapter_started",
    "chapter_skipped",
    "listen_progress",
    "feedback",
    "feed_download",
    "ask_asked",
]
COMPLETED = 0.8  # share of an episode that counts as "listened"
ACTIVATION_HOURS = 48

# --- Shared building blocks (CTEs) -------------------------------------------------------

SCOPED = "scoped AS (SELECT * FROM users WHERE :mock OR NOT is_mock)"
ACTIVE = """active AS (  -- one row per listener and day they were active
  SELECT DISTINCT e.user_id, (e.ts AT TIME ZONE 'UTC')::date AS day
  FROM events e JOIN scoped u ON u.id = e.user_id
  WHERE e.type = ANY(:active_events) AND e.ts >= :since AND e.ts < :end)"""
LISTENS = """listens AS (  -- one row per listener and episode: how far they got, and when
  SELECT e.user_id, e.episode_id,
    least(max((e.props->>'max_position_s')::float) / ep.duration_s, 1) AS completion,
    min(e.ts) FILTER (
      WHERE (e.props->>'max_position_s')::float >= :completed * ep.duration_s) AS completed_at,
    max(e.ts) AS last_ts
  FROM events e JOIN scoped u ON u.id = e.user_id JOIN episodes ep ON ep.id = e.episode_id
  WHERE e.type = 'listen_progress' AND ep.duration_s > 0
  GROUP BY e.user_id, e.episode_id, ep.duration_s)"""
DAYS = """days AS (
  SELECT d::date AS day FROM generate_series(CAST(:first_day AS date), CAST(:last_day AS date),
                                             interval '1 day') d)"""
IN_RANGE_EVENTS = """ev AS (
  SELECT e.* FROM events e JOIN scoped u ON u.id = e.user_id
  WHERE e.ts >= :start AND e.ts < :end)"""
IN_RANGE_EPISODES = """eps AS (
  SELECT ep.* FROM episodes ep JOIN scoped u ON u.id = ep.user_id
  WHERE ep.created_at >= :start AND ep.created_at < :end)"""
STORIES = """stories AS (  -- which interest each story of each episode belongs to
  SELECT ep.id AS episode_id, p->>'story_id' AS story_id, p->>'interest' AS topic
  FROM episodes ep, jsonb_array_elements(
    coalesce(ep.work->'selection'->'picks', '[]') || coalesce(ep.work->'selection'->'backups', '[]')
  ) p)"""


def with_(*ctes: str) -> str:
    return "WITH " + ",\n".join(ctes) + "\n"


# --- Growth and habit --------------------------------------------------------------------

DAILY_GROWTH = (
    with_(SCOPED, ACTIVE, DAYS)
    + """
SELECT d.day::text AS day,
  (SELECT count(*) FROM active a WHERE a.day = d.day) AS dau,
  (SELECT count(DISTINCT a.user_id) FROM active a WHERE a.day BETWEEN d.day - 6 AND d.day) AS wau,
  (SELECT count(*) FROM scoped u WHERE (u.created_at AT TIME ZONE 'UTC')::date = d.day) AS signups
FROM days d ORDER BY d.day"""
)

# MAU, and the listener-days behind the average DAU of the same 28 days (for DAU/MAU).
MAU = (
    with_(SCOPED, ACTIVE)
    + """
SELECT count(DISTINCT user_id) AS mau, count(*) AS listener_days
FROM active WHERE day > CAST(:last_day AS date) - 28"""
)

# The listeners who signed up in the range, step by step to their first full listen.
FUNNEL = (
    with_(SCOPED, LISTENS)
    + """,
cohort AS (SELECT * FROM scoped WHERE created_at >= :start AND created_at < :end)
SELECT count(*) AS signed_up,
  count(*) FILTER (WHERE onboarded_at IS NOT NULL) AS onboarded,
  count(*) FILTER (WHERE EXISTS (
    SELECT 1 FROM episodes ep WHERE ep.user_id = c.id AND ep.status = 'ready')) AS first_episode,
  count(*) FILTER (WHERE EXISTS (
    SELECT 1 FROM listens l WHERE l.user_id = c.id AND l.completed_at IS NOT NULL)) AS listened_80,
  count(*) FILTER (WHERE EXISTS (
    SELECT 1 FROM listens l WHERE l.user_id = c.id
      AND l.completed_at < c.created_at + make_interval(hours => :activation_hours))) AS activated
FROM cohort c"""
)

# Week N after signing up (days 7N … 7N+6): who of each weekly cohort was active.
RETENTION = (
    with_(SCOPED, ACTIVE)
    + """,
cohort AS (
  SELECT id, (created_at AT TIME ZONE 'UTC')::date AS signup FROM scoped
  WHERE created_at >= :start AND created_at < :end)
SELECT date_trunc('week', c.signup)::date::text AS cohort, w.n AS week,
  count(*) FILTER (WHERE c.signup + 7 * w.n <= CAST(:last_day AS date)) AS eligible,
  count(*) FILTER (WHERE EXISTS (
    SELECT 1 FROM active a WHERE a.user_id = c.id
      AND a.day >= c.signup + 7 * w.n AND a.day < c.signup + 7 * (w.n + 1))) AS retained
FROM cohort c CROSS JOIN generate_series(0, 8) AS w(n)
GROUP BY 1, 2 ORDER BY 1, 2"""
)

# --- Content -----------------------------------------------------------------------------

COMPLETION = (
    with_(SCOPED, LISTENS)
    + """
SELECT completion FROM listens WHERE last_ts >= :start AND last_ts < :end"""
)

SKIPS_BY_POSITION = (
    with_(SCOPED, IN_RANGE_EVENTS)
    + """
SELECT (props->>'chapter_index')::int AS position,
  count(*) FILTER (WHERE type = 'chapter_started') AS started,
  count(*) FILTER (WHERE type = 'chapter_skipped') AS skipped
FROM ev
WHERE type IN ('chapter_started', 'chapter_skipped') AND props->>'story_id' IS NOT NULL
GROUP BY 1 ORDER BY 1"""
)

TOPICS = (
    with_(SCOPED, IN_RANGE_EVENTS, STORIES)
    + """
SELECT s.topic,
  count(*) FILTER (WHERE e.type = 'chapter_started') AS plays,
  count(*) FILTER (WHERE e.type = 'chapter_skipped') AS skips,
  count(*) FILTER (WHERE e.type = 'feedback' AND e.props->>'value' = 'up') AS ups,
  count(*) FILTER (WHERE e.type = 'feedback' AND e.props->>'value' = 'down') AS downs
FROM ev e JOIN stories s ON s.episode_id = e.episode_id AND s.story_id = e.props->>'story_id'
WHERE e.type IN ('chapter_started', 'chapter_skipped', 'feedback')
GROUP BY 1 ORDER BY plays DESC, 1 LIMIT 12"""
)

FEATURES = (
    with_(SCOPED, IN_RANGE_EVENTS)
    + """
SELECT
  (SELECT count(DISTINCT user_id) FROM ev WHERE type = ANY(:active_events)) AS active_users,
  (SELECT count(DISTINCT user_id) FROM ev WHERE type = 'feed_download') AS rss_users,
  (SELECT count(*) FROM ev WHERE type = 'onboarding_completed') AS onboarded,
  (SELECT count(*) FROM ev
   WHERE type = 'onboarding_completed' AND props->>'method' = 'import') AS imported,
  (SELECT count(*) FROM ev WHERE type = 'feedback' AND props->>'value' = 'up') AS ups,
  (SELECT count(*) FROM ev WHERE type = 'feedback' AND props->>'value' = 'down') AS downs"""
)

ASK = (
    with_(SCOPED, IN_RANGE_EVENTS)
    + """
SELECT count(*) AS questions, count(DISTINCT user_id) AS askers,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY (props->>'latency_s')::float) AS p50,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY (props->>'latency_s')::float) AS p95
FROM ev WHERE type = 'ask_asked'"""
)

# --- Operations --------------------------------------------------------------------------

DAILY_EPISODES = (
    with_(SCOPED, DAYS, IN_RANGE_EPISODES)
    + """
SELECT d.day::text AS day,
  count(ep.id) FILTER (WHERE ep.trigger = 'manual') AS manual,
  count(ep.id) FILTER (WHERE ep.trigger = 'scheduled') AS scheduled,
  count(ep.id) FILTER (WHERE ep.status = 'failed') AS failed
FROM days d LEFT JOIN eps ep ON (ep.created_at AT TIME ZONE 'UTC')::date = d.day
GROUP BY d.day ORDER BY d.day"""
)

STAGES_SQL = (
    with_(SCOPED, IN_RANGE_EPISODES)
    + """,
timings AS (
  SELECT t.key AS stage, t.value::float AS seconds
  FROM eps, jsonb_each_text(eps.stage_timings) t WHERE eps.status = 'ready'),
latency AS (
  SELECT stage, percentile_cont(0.5) WITHIN GROUP (ORDER BY seconds) AS p50,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY seconds) AS p95
  FROM timings GROUP BY 1),
failures AS (SELECT failed_stage AS stage, count(*) AS failures FROM eps
             WHERE status = 'failed' GROUP BY 1)
SELECT coalesce(l.stage, f.stage) AS stage, l.p50, l.p95, coalesce(f.failures, 0) AS failures
FROM latency l FULL JOIN failures f ON f.stage = l.stage"""
)

REQUESTED = with_(SCOPED, IN_RANGE_EPISODES) + "SELECT count(*) AS requested FROM eps"

DAILY_COST = (
    with_(SCOPED, IN_RANGE_EPISODES)
    + """
SELECT (created_at AT TIME ZONE 'UTC')::date::text AS day,
  avg((cost->>'llm_usd')::float) AS llm_usd,
  avg((cost->>'tts_chars')::float) * :tts_price AS tts_usd
FROM eps WHERE status = 'ready' GROUP BY 1 ORDER BY 1"""
)

COST_PER_EPISODE = (
    with_(SCOPED, IN_RANGE_EPISODES)
    + """
SELECT avg((cost->>'llm_usd')::float) + avg((cost->>'tts_chars')::float) * :tts_price AS usd
FROM eps WHERE status = 'ready'"""
)

CHECKER = (
    with_(SCOPED, IN_RANGE_EVENTS)
    + """
SELECT count(*) AS episodes,
  count(*) FILTER (WHERE (props->>'issues_found')::int > 0) AS with_issues,
  coalesce(sum((props->>'issues_found')::int), 0) AS issues_found,
  coalesce(sum((props->>'issues_fixed')::int), 0) AS issues_fixed
FROM ev WHERE type = 'episode_ready'"""
)


def ratio(part: float, whole: float) -> float | None:
    return part / whole if whole else None


def retention(rows: list[dict]) -> list[dict]:
    """[{cohort, users, weeks: [share active in week 0, 1, …]}], stopping at the weeks to come."""
    cohorts: dict[str, dict] = {}
    for r in rows:
        c = cohorts.setdefault(r["cohort"], {"cohort": r["cohort"], "users": 0, "weeks": []})
        if r["week"] == 0:
            c["users"] = r["eligible"]
        if r["eligible"]:
            c["weeks"].append(r["retained"] / r["eligible"])
    return list(cohorts.values())


def dashboard(today: date, days: int, include_mock: bool) -> dict:
    """All the dashboard's numbers for the `days` whole UTC days ending `today`."""
    first_day = today - timedelta(days=days - 1)
    start = datetime.combine(first_day, time(), UTC)
    end = datetime.combine(today + timedelta(days=1), time(), UTC)
    params = {
        "mock": include_mock,
        "start": start,
        "end": end,
        "since": min(start - timedelta(days=6), end - timedelta(days=28)),  # WAU and MAU windows
        "first_day": first_day,
        "last_day": today,
        "active_events": ACTIVE_EVENTS,
        "completed": COMPLETED,
        "activation_hours": ACTIVATION_HOURS,
        "tts_price": TTS_USD_PER_CHAR,
    }
    with Session(engine) as session:

        def rows(sql: str) -> list[dict]:
            return [dict(r) for r in session.execute(text(sql), params).mappings()]

        daily, month = rows(DAILY_GROWTH), rows(MAU)[0]
        funnel, features = rows(FUNNEL)[0], rows(FEATURES)[0]
        completions = [r["completion"] for r in rows(COMPLETION)]
        stages = {r["stage"]: r for r in rows(STAGES_SQL)}
        growth_retention, skips, topics = rows(RETENTION), rows(SKIPS_BY_POSITION), rows(TOPICS)
        ops = {
            "daily": rows(DAILY_EPISODES),
            "requested": rows(REQUESTED)[0]["requested"],
            "cost": rows(DAILY_COST),
            "checker": rows(CHECKER)[0],
        }
        cost = rows(COST_PER_EPISODE)[0]["usd"]
        asks = rows(ASK)[0]

    buckets = [0] * 10
    for c in completions:
        buckets[min(int(c * 10), 9)] += 1

    return {
        "range": {"first_day": first_day.isoformat(), "last_day": today.isoformat(), "days": days},
        "include_mock": include_mock,
        "kpis": {
            "mau": month["mau"],
            "stickiness": ratio(month["listener_days"] / 28, month["mau"]),
            "activation": ratio(funnel["activated"], funnel["signed_up"]),
            "completion": ratio(sum(completions), len(completions)),
            "thumbs_up": ratio(features["ups"], features["ups"] + features["downs"]),
            "cost_per_episode": cost,
        },
        "growth": {
            "daily": daily,
            "funnel": [
                {"step": step, "users": funnel[step]}
                for step in ("signed_up", "onboarded", "first_episode", "listened_80")
            ],
            "retention": retention(growth_retention),
        },
        "content": {
            "completion": [{"bucket": b, "listens": n} for b, n in enumerate(buckets)],
            "skips_by_position": [
                {**r, "skip_rate": ratio(r["skipped"], r["started"]) or 0.0} for r in skips
            ],
            "topics": [
                {
                    **t,
                    "thumbs_up": ratio(t["ups"], t["ups"] + t["downs"]),
                    "skip_rate": ratio(t["skips"], t["plays"]),
                }
                for t in topics
            ],
            "rss_adoption": ratio(features["rss_users"], features["active_users"]),
            "import_share": ratio(features["imported"], features["onboarded"]),
            "ask": {
                "questions": asks["questions"],
                "askers_share": ratio(asks["askers"], features["active_users"]),
                "p50_latency_s": asks["p50"],
                "p95_latency_s": asks["p95"],
            },
        },
        "operations": {
            **ops,
            # in pipeline order; a stage with no data yet is left out
            "stages": [stages[s] for s in STAGES if s in stages],
        },
    }
