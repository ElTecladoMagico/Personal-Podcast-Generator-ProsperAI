"""Private podcast feed (RSS 2.0 + iTunes tags): subscribe once in any podcast app and new
episodes arrive on their own (ADR 0011). The feed token in the URL is the credential."""

import xml.etree.ElementTree as ET
from email.utils import format_datetime

from fastapi import APIRouter, HTTPException, Response
from sqlmodel import select

from app.config import settings
from app.db import DbSession
from app.models import Episode, User
from app.pipeline.state import Work
from app.storage import audio_file, audio_url

router = APIRouter()

ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ET.register_namespace("itunes", ITUNES)
MAX_ITEMS = 50


def sub(parent: ET.Element, tag: str, value: str | None = None, **attrs: str) -> ET.Element:
    el = ET.SubElement(parent, tag.replace("itunes:", f"{{{ITUNES}}}"), attrs)
    el.text = value
    return el


def feed_title(user: User, language: str) -> str:
    name = user.display_name
    if not name:
        return "Personal Podcast"
    return f"El podcast de {name}" if language == "es" else f"{name}'s Daily Brief"


def show_notes(ep: Episode) -> str:
    """Summary plus the articles it was built from (HTML, as podcast apps expect)."""
    links = "".join(
        f'<li><a href="{a.url}">{a.title}</a> ({a.source})</li>'
        for a in Work.model_validate(ep.work).articles
    )
    return f"<p>{ep.summary or ''}</p><ul>{links}</ul>"


def build_feed(user: User, episodes: list[Episode]) -> bytes:
    language = user.preferences.get("language", "en")
    rss = ET.Element("rss", version="2.0")
    channel = sub(rss, "channel")
    sub(channel, "title", feed_title(user, language))
    sub(channel, "link", settings.public_base_url)
    sub(channel, "description", "Your news, picked and told for you every day.")
    sub(channel, "language", language)
    sub(channel, "itunes:author", "Personal Podcast Generator")
    sub(channel, "itunes:image", href=f"{settings.public_base_url}/static/cover.png")
    sub(channel, "itunes:category", text="News")
    sub(channel, "itunes:explicit", "false")
    sub(channel, "itunes:block", "Yes")  # private: keep it out of the directories
    for ep in episodes:
        path = audio_file(ep.audio_path)
        if not path.is_file():
            continue
        item = sub(channel, "item")
        sub(item, "title", ep.title)
        sub(item, "description", show_notes(ep))
        url = f"{audio_url(ep.id, user.feed_token)}&src=rss"
        sub(item, "enclosure", url=url, length=str(path.stat().st_size), type="audio/mpeg")
        sub(item, "guid", str(ep.id), isPermaLink="false")
        sub(item, "pubDate", format_datetime(ep.finished_at or ep.created_at))
        sub(item, "itunes:duration", str(int(ep.duration_s or 0)))
    return ET.tostring(rss, encoding="utf-8", xml_declaration=True)


@router.get("/feeds/{feed_token}.xml")
def get_feed(feed_token: str, session: DbSession) -> Response:
    user = session.exec(select(User).where(User.feed_token == feed_token)).first()
    if not user:
        raise HTTPException(404, "Feed not found")
    episodes = session.exec(
        select(Episode)
        .where(
            Episode.user_id == user.id,
            Episode.status == "ready",
            Episode.audio_path.is_not(None),
            Episode.audio_expired.is_(False),
        )
        .order_by(Episode.finished_at.desc())
        .limit(MAX_ITEMS)
    ).all()
    return Response(build_feed(user, episodes), media_type="application/rss+xml; charset=utf-8")
