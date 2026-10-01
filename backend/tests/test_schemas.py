import pytest
from pydantic import ValidationError

from app.schemas import Preferences

SARAH = {"name": "Sarah", "voice_id": "EXAVITQu4vr4xnSDxMaL"}
GEORGE = {"name": "George", "voice_id": "JBFqnCBsd6RMkjVDRZzb"}


def prefs(**overrides) -> dict:
    return {"interests": [{"topic": "AI"}], "hosts": [SARAH, GEORGE]} | overrides


def test_defaults_fill_everything_but_interests_and_hosts():
    p = Preferences.model_validate(prefs())
    assert (p.language, p.format, p.duration_min) == ("en", "duo", 10)
    assert p.schedule.frequency == "daily" and p.schedule.timezone == "Europe/Madrid"


@pytest.mark.parametrize(
    ("fmt", "hosts", "ok"),
    [
        ("solo", [SARAH], True),
        ("solo", [SARAH, GEORGE], False),
        ("duo", [SARAH, GEORGE], True),
        ("debate", [SARAH], False),
    ],
)
def test_host_count_must_match_format(fmt, hosts, ok):
    data = prefs(format=fmt, hosts=hosts)
    if ok:
        Preferences.model_validate(data)
    else:
        with pytest.raises(ValidationError, match="host"):
            Preferences.model_validate(data)


@pytest.mark.parametrize(
    "schedule",
    [
        {"timezone": "Mars/Olympus"},
        {"time": "25:00"},
        {"time": "7am"},
        {"frequency": "weekly"},
        {"frequency": "weekly", "weekday": 7},
    ],
)
def test_invalid_schedules_are_rejected(schedule):
    with pytest.raises(ValidationError):
        Preferences.model_validate(prefs(schedule=schedule))


def test_weekly_schedule_with_weekday_is_valid():
    p = Preferences.model_validate(prefs(schedule={"frequency": "weekly", "weekday": 0}))
    assert p.schedule.weekday == 0


@pytest.mark.parametrize(
    "interests",
    [[], [{"topic": ""}], [{"topic": "x", "weight": 6}], [{"topic": f"t{i}"} for i in range(13)]],
)
def test_interest_bounds(interests):
    with pytest.raises(ValidationError):
        Preferences.model_validate(prefs(interests=interests))
