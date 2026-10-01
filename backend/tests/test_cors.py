from fastapi.testclient import TestClient

from app.main import app

PREFLIGHT = {
    "Access-Control-Request-Method": "GET",
    "Access-Control-Request-Headers": "authorization",
}


def test_allowed_origin_gets_cors_headers():
    r = TestClient(app).options("/me", headers={"Origin": "http://localhost:5173"} | PREFLIGHT)
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_unknown_origin_is_refused():
    r = TestClient(app).options("/me", headers={"Origin": "https://evil.example"} | PREFLIGHT)
    assert "access-control-allow-origin" not in r.headers
