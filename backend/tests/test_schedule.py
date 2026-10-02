from datetime import UTC, datetime

from app.schedule import compute_next_run
from app.schemas import Schedule

MADRID = "Europe/Madrid"


def at(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


def test_off_never_runs():
    assert compute_next_run(Schedule(frequency="off"), at(2026, 10, 2, 6, 0)) is None


def test_daily_runs_lead_minutes_before_the_local_time():
    # 07:00 in Madrid (UTC+2 in October) = 05:00 UTC, minus 20 min of lead
    s = Schedule(frequency="daily", time="07:00", timezone=MADRID)
    assert compute_next_run(s, at(2026, 10, 2, 4, 0)) == at(2026, 10, 2, 4, 40)


def test_daily_after_todays_slot_goes_to_tomorrow():
    s = Schedule(frequency="daily", time="07:00", timezone=MADRID)
    assert compute_next_run(s, at(2026, 10, 2, 4, 41)) == at(2026, 10, 3, 4, 40)


def test_lead_that_falls_in_the_past_skips_to_the_next_occurrence():
    s = Schedule(frequency="daily", time="07:00", timezone=MADRID)
    # 06:50 Madrid: the episode is due in 10 min but generation should have started at 06:40
    assert compute_next_run(s, at(2026, 10, 2, 4, 50)) == at(2026, 10, 3, 4, 40)


def test_weekdays_jump_over_the_weekend():
    s = Schedule(frequency="weekdays", time="08:30", timezone=MADRID)
    friday_evening = at(2026, 10, 2, 18, 0)  # 2026-10-02 is a Friday
    assert compute_next_run(s, friday_evening) == at(2026, 10, 5, 6, 10)  # Monday 08:10 Madrid


def test_weekly_runs_on_its_weekday():
    s = Schedule(frequency="weekly", weekday=6, time="10:00", timezone=MADRID)  # Sundays
    assert compute_next_run(s, at(2026, 10, 2, 12, 0)) == at(2026, 10, 4, 7, 40)


def test_daylight_saving_change_keeps_the_local_hour():
    # Madrid leaves summer time on 2026-10-25: 07:00 local is 05:00 UTC before, 06:00 UTC after
    s = Schedule(frequency="daily", time="07:00", timezone=MADRID)
    assert compute_next_run(s, at(2026, 10, 24, 12, 0)) == at(2026, 10, 25, 5, 40)
    assert compute_next_run(s, at(2026, 10, 25, 12, 0)) == at(2026, 10, 26, 5, 40)


def test_midnight_in_another_timezone():
    s = Schedule(frequency="daily", time="00:10", timezone="America/New_York")
    # 00:10 New York (UTC-4) = 04:10 UTC; lead → 03:50 UTC
    assert compute_next_run(s, at(2026, 10, 2, 3, 0)) == at(2026, 10, 2, 3, 50)
