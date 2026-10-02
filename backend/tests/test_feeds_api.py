import xml.etree.ElementTree as ET
from datetime import UTC, datetime

import pytest
from sqlmodel import Session, select

from app import storage
from app.db import engine
from app.models import Episode, Event, User

NS = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}
ARTICLE = {
    "id": "a1",
    "story_id": "s1",
    "url": "https://elpais.com/x",
    "source": "elpais.com",
    "title": "Una noticia",
    "text": "…",
    "image_url": None,
}


def add_episode(user_id, **fields) -> Episode:
    with Session(engine) as s:
        ep = Episode(
            user_id=user_id, trigger="scheduled", language="es", prefs_snapshot={}, **fields
        )
        s.add(ep)
        s.commit()
        s.refresh(ep)
        return ep


@pytest.fixture
def feed(client, tmp_path, monkeypatch):
    """Ana's feed: one playable episode, plus others that must not appear."""
    monkeypatch.setattr(storage.settings, "audio_dir", str(tmp_path))
    client.get("/me")
    with Session(engine) as s:
        ana = s.exec(select(User)).one()
        ana.preferences = {"language": "es"}
        other = User(clerk_id="user_other")
        s.add(other)
        s.commit()
        ana_id, token, other_id = ana.id, ana.feed_token, other.id

    ready = add_episode(
        ana_id,
        status="ready",
        title="Lunes",
        summary="Resumen",
        duration_s=133.4,
        finished_at=datetime(2026, 10, 2, 5, tzinfo=UTC),
        work={"articles": [ARTICLE]},
    )
    relpath, path = storage.new_audio_file(ana_id, ready.id)
    path.write_bytes(b"x" * 1234)
    with Session(engine) as s:
        s.get(Episode, ready.id).audio_path = relpath
        s.commit()
    add_episode(ana_id, status="ready", title="Caducado", audio_path="gone.mp3", audio_expired=True)
    add_episode(ana_id, status="writing", title="En curso")
    add_episode(other_id, status="ready", title="De otro", audio_path="other.mp3")
    return token, ready.id


def test_feed_lists_only_the_owners_playable_episodes(client, feed):
    token, ep_id = feed
    r = client.get(f"/feeds/{token}.xml")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/rss+xml")
    channel = ET.fromstring(r.content).find("channel")
    assert channel.findtext("title") == "El podcast de Ana"
    assert channel.findtext("language") == "es"
    assert channel.findtext("link") == "https://podcast.scuda.es"  # the app, not the API
    assert channel.findtext("itunes:block", namespaces=NS) == "Yes"
    assert channel.find("itunes:image", NS).get("href").endswith("/static/cover.png")

    [item] = channel.findall("item")
    assert item.findtext("title") == "Lunes"
    assert item.findtext("guid") == str(ep_id)
    assert item.findtext("pubDate") == "Fri, 02 Oct 2026 05:00:00 +0000"
    assert item.findtext("itunes:duration", namespaces=NS) == "133"
    assert "elpais.com" in item.findtext("description")
    enclosure = item.find("enclosure")
    assert enclosure.get("length") == "1234" and enclosure.get("type") == "audio/mpeg"
    assert enclosure.get("url").endswith(f"/audio/{ep_id}.mp3?k={token}&src=rss")


def test_unknown_feed_is_404(client):
    assert client.get("/feeds/nope.xml").status_code == 404


def downloads() -> int:
    with Session(engine) as s:
        return len(s.exec(select(Event).where(Event.type == "feed_download")).all())


def test_feed_download_counts_once_per_listen(client, feed):
    token, ep_id = feed
    url = f"/audio/{ep_id}.mp3"
    client.get(url, params={"k": token, "src": "rss"})
    client.get(url, params={"k": token, "src": "rss"}, headers={"Range": "bytes=0-99"})
    assert downloads() == 2
    client.get(url, params={"k": token, "src": "rss"}, headers={"Range": "bytes=100-"})
    client.get(url, params={"k": token})  # the web player
    client.head(url, params={"k": token, "src": "rss"})  # an app checking the file
    assert downloads() == 2


def test_podcast_apps_can_check_feed_and_audio_with_head(client, feed):
    token, ep_id = feed
    assert client.head(f"/feeds/{token}.xml").status_code == 200
    audio = client.head(f"/audio/{ep_id}.mp3", params={"k": token, "src": "rss"})
    assert audio.status_code == 200 and audio.headers["content-length"] == "1234"


def test_rotating_the_token_kills_the_old_feed(client, feed):
    token, _ = feed
    new_url = client.post("/me/feed-token/rotate").json()["feed_url"]
    assert token not in new_url
    assert client.get(f"/feeds/{token}.xml").status_code == 404
    assert client.get(new_url.split("8000")[-1]).status_code == 200
