"""When the next scheduled episode must start (ADR 0010)."""

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.schemas import Schedule

# Generation starts this early so the episode is ready at the time the listener asked for.
GENERATION_LEAD_MIN = 20


def runs_on(schedule: Schedule, weekday: int) -> bool:
    match schedule.frequency:
        case "daily":
            return True
        case "weekdays":
            return weekday < 5
        case "weekly":
            return weekday == schedule.weekday
    return False


def compute_next_run(schedule: Schedule, now: datetime, lead_min: int = GENERATION_LEAD_MIN):
    """Next UTC instant to start generating, or None if the schedule is off.

    Works in the listener's time zone, so 07:00 stays 07:00 across daylight-saving changes.
    """
    if schedule.frequency == "off":
        return None
    zone = ZoneInfo(schedule.timezone)
    hour, minute = map(int, schedule.time.split(":"))
    today = now.astimezone(zone).date()
    for days in range(8):
        day = today + timedelta(days=days)
        if not runs_on(schedule, day.weekday()):
            continue
        local = datetime.combine(day, time(hour, minute), tzinfo=zone)
        start = local.astimezone(UTC) - timedelta(minutes=lead_min)
        if start > now:
            return start
    return None  # unreachable for a valid schedule
