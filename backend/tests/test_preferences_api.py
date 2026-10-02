from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlmodel import Session, select

from app.db import engine
from app.importer import extract_json
from app.models import Event
from app.voices import VOICES, default_hosts

SARA, MARTIN = "gD1IexrzCvsXPHUuT0s3", "LlZr3QuzbW4WrPjgATHG"


def prefs(**kw) -> dict:
    return {
        "interests": [{"topic": "IA", "weight": 4}],
        "language": "es",
        "hosts": [{"name": "Sara", "voice_id": SARA}, {"name": "Martín", "voice_id": MARTIN}],
        "schedule": {"frequency": "daily", "time": "07:00", "timezone": "Europe/Madrid"},
    } | kw


def events(kind: str) -> list[Event]:
    with Session(engine) as s:
        return list(s.exec(select(Event).where(Event.type == kind)))


def test_first_save_onboards_and_schedules(client):
    r = client.put("/me/preferences", json={"preferences": prefs(), "method": "import"})
    assert r.status_code == 200
    me = r.json()
    assert me["onboarded"] is True
    next_at = datetime.fromisoformat(me["next_episode_at"]).astimezone(ZoneInfo("Europe/Madrid"))
    assert next_at.strftime("%H:%M") == "07:00"  # the listener's time, not the earlier start
    assert me["preferences"]["interests"][0]["topic"] == "IA"
    assert [e.props for e in events("onboarding_completed")] == [{"method": "import"}]

    client.put("/me/preferences", json={"preferences": prefs(schedule={"frequency": "off"})})
    assert client.get("/me").json()["next_episode_at"] is None
    assert len(events("preferences_updated")) == 1 and len(events("onboarding_completed")) == 1


@pytest.mark.parametrize(
    "bad",
    [
        {"hosts": [{"name": "X", "voice_id": "not-a-catalog-voice"}], "format": "solo"},
        {"interests": []},
        {"schedule": {"timezone": "Mars/Base"}},
    ],
)
def test_invalid_preferences_are_422(client, bad):
    assert client.put("/me/preferences", json={"preferences": prefs(**bad)}).status_code == 422


def test_voices_catalog_and_defaults(client):
    voices = client.get("/voices").json()
    assert {v["id"] for v in voices} == {v.id for v in VOICES}
    assert all(
        v["preview"].startswith("/voices/") and v["language"] in ("es", "en") for v in voices
    )
    assert [h.voice_id for h in default_hosts("es")] == [SARA, MARTIN]
    assert {h.voice_id for h in default_hosts("fr")} <= {v.id for v in VOICES}


# --- importing what the user's AI answered ---------------------------------------

CLEAN = '{"interests":[{"topic":"EU AI regulation","why":"my job","weight":5}],"language":"en"}'


@pytest.mark.parametrize(
    "text",
    [
        CLEAN,
        f"Sure! Here is your JSON:\n```json\n{CLEAN}\n```\nLet me know if you want changes.",
        f"```\n{CLEAN}\n```",
        f"Based on our chats: {CLEAN} Hope it helps {{smile}}",
        '{"interests":[{"topic":"Brace } inside a string","weight":3}]}',
    ],
)
def test_extract_json_finds_the_object(text):
    assert extract_json(text)["interests"][0]["topic"] in (
        "EU AI regulation",
        "Brace } inside a string",
    )


@pytest.mark.parametrize(
    "text", ["", "I don't know enough about you yet.", '{"interests": [1, 2,]}']
)
def test_extract_json_fails_clearly(text):
    with pytest.raises(ValueError):
        extract_json(text)


def test_import_is_tolerant_with_what_ais_produce(client):
    messy = {
        "interests": [
            {"topic": f"  Topic {i}  ", "weight": w} for i, w in enumerate([9, 0, 3] + [2] * 12)
        ],
        "tone": "sarcastic",  # unknown → dropped
        "language": "ES",
        "favourite_colour": "blue",  # unknown field → ignored
    }
    import json

    r = client.post("/me/preferences/import", json={"text": "Here: " + json.dumps(messy)})
    assert r.status_code == 200
    got = r.json()
    assert len(got["interests"]) == 12 and got["interests"][0] == {
        "topic": "Topic 0",
        "why": None,
        "weight": 5,
    }
    assert got["interests"][1]["weight"] == 1 and got["language"] == "es" and got["tone"] is None


def test_import_without_json_gives_a_helpful_422(client):
    r = client.post("/me/preferences/import", json={"text": "Sorry, I can't help with that."})
    assert r.status_code == 422 and "JSON" in r.json()["detail"]


def test_import_ignores_languages_we_cannot_voice(client):
    text = '{"interests": [{"topic": "Cine"}], "language": "fr-FR"}'
    r = client.post("/me/preferences/import", json={"text": text})
    assert r.status_code == 200 and r.json()["language"] is None  # keeps what the user chose
