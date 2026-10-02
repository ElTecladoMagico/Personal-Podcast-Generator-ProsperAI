from fastapi.testclient import TestClient
from sqlmodel import Session, func, select

from app.db import engine
from app.main import app
from app.models import Event, User


def count(model) -> int:
    with Session(engine) as s:
        return s.exec(select(func.count()).select_from(model)).one()


def test_me_requires_a_token():
    assert TestClient(app).get("/me").status_code == 401


def test_me_rejects_a_malformed_token():
    r = TestClient(app).get("/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401
    assert r.json() == {"detail": "Invalid or expired session token"}


def test_first_call_creates_user_once(client):
    first = client.get("/me").json()
    second = client.get("/me").json()

    assert first["id"] == second["id"]
    assert (count(User), count(Event)) == (1, 1)
    with Session(engine) as s:
        assert s.exec(select(Event.type)).one() == "user_signed_up"


def test_me_shape_for_new_user(client):
    me = client.get("/me").json()
    with Session(engine) as s:
        token = s.exec(select(User.feed_token)).one()

    assert me["email"] == "ana@example.com" and me["display_name"] == "Ana"
    assert me["onboarded"] is False and me["is_admin"] is False
    assert me["preferences"] is None and me["next_episode_at"] is None
    assert me["feed_url"] == f"http://localhost:8000/feeds/{token}.xml"


def test_profile_follows_token_claims(client, claims):
    client.get("/me")
    claims |= {"email": "new@example.com", "name": "Ana B", "metadata": {"role": "admin"}}
    me = client.get("/me").json()
    assert (me["email"], me["display_name"], me["is_admin"]) == ("new@example.com", "Ana B", True)
