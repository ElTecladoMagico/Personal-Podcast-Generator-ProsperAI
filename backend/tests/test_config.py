from app.config import Settings


def test_comma_separated_lists_are_split_and_trimmed(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", "http://a.test")
    s = Settings()
    assert s.cors_origins == ["http://a.test", "http://b.test"]
    assert s.clerk_authorized_parties == ["http://a.test"]
