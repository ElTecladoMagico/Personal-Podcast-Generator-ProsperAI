import pytest
from sqlmodel import Session, select

from app import storage
from app.db import engine
from app.models import Episode, Event, User
from app.pipeline import ask
from app.schemas import Usage

HOSTS = [{"name": "Sara", "voice_id": "v1"}, {"name": "Martín", "voice_id": "v2"}]
PREFS = {"language": "es", "format": "duo", "hosts": HOSTS}
SCRIPT = {"title": "T", "summary": "S", "chapters": [
    {"story_id": None, "title": "Intro", "start_s": 0, "end_s": 10,
     "turns": [{"speaker": 0, "text": "Hola", "source_ids": []}]},
    {"story_id": "s1", "title": "IA", "start_s": 10, "end_s": 60,
     "turns": [{"speaker": 1, "text": "Europa regula la IA", "source_ids": ["a1"]}]},
]}  # fmt: skip
ARTICLE = {"id": "a1", "story_id": "s1", "url": "https://x.test/a", "source": "x.test",
           "title": "A", "text": "La UE aprueba la ley.", "image_url": None}  # fmt: skip
WORK = {"articles": [ARTICLE]}


@pytest.fixture
def episode(client, tmp_path, monkeypatch):
    monkeypatch.setattr(storage.settings, "audio_dir", str(tmp_path))
    client.get("/me")
    with Session(engine) as s:
        user = s.exec(select(User)).one()
        ep = Episode(user_id=user.id, trigger="manual", language="es", prefs_snapshot=PREFS,
                     status="ready", script=SCRIPT, work=WORK, audio_path="u/e.mp3")  # fmt: skip
        s.add(ep)
        s.commit()
        return ep.id, user.feed_token


@pytest.fixture
def fakes(monkeypatch):
    seen = {}

    def fake_parse(model, system, user, schema):
        seen["prompt"] = user
        return ask.AskAnswer(turns=[
            ask.AskTurn(speaker=1, text="Buena pregunta, Lucía.", source_ids=[]),
            ask.AskTurn(speaker=0, text="La UE aprobó la ley.", source_ids=["a1"]),
        ]), Usage(llm_usd=0.001)  # fmt: skip

    def fake_synth(inputs, language, seed):
        seen["voices"] = [voice for _, voice in inputs]
        return b"mp3", {}

    monkeypatch.setattr(ask, "parse", fake_parse)
    monkeypatch.setattr(ask, "synthesize", fake_synth)
    monkeypatch.setattr(
        ask, "change_tempo", lambda src, out, factor: out.write_bytes(src.read_bytes())
    )
    return seen


def test_hosts_answer_with_their_voices_from_the_chapter_sources(client, episode, fakes):
    ep_id, token = episode
    r = client.post(
        f"/episodes/{ep_id}/ask", json={"question": "¿Qué cambia para mí?", "position_s": 30}
    )
    assert r.status_code == 200
    body = r.json()
    assert [t["speaker"] for t in body["turns"]] == [1, 0] and fakes["voices"] == ["v2", "v1"]
    assert "La UE aprueba la ley." in fakes["prompt"] and "¿Qué cambia para mí?" in fakes["prompt"]

    audio = client.get(body["audio_url"].split("8000")[-1])
    assert audio.status_code == 200 and audio.content == b"mp3"
    with Session(engine) as s:
        [e] = s.exec(select(Event).where(Event.type == "ask_asked")).all()
    assert e.props["chapter_index"] == 1 and e.props["latency_s"] >= 0 and e.props["chars"] > 0


def test_the_answer_audio_needs_the_feed_token(client, episode, fakes):
    ep_id, _ = episode
    qid = client.post(
        f"/episodes/{ep_id}/ask", json={"question": "¿Y ahora?", "position_s": 30}
    ).json()["qid"]
    assert client.get(f"/audio/{ep_id}/ask-{qid}.mp3", params={"k": "wrong"}).status_code == 404
    assert client.get(f"/audio/{ep_id}/ask-../../x.mp3", params={"k": "x"}).status_code == 404


def test_only_ready_episodes_and_short_questions(client, episode, fakes):
    ep_id, _ = episode
    assert (
        client.post(f"/episodes/{ep_id}/ask", json={"question": "?", "position_s": 3}).status_code
        == 422
    )
    with Session(engine) as s:
        s.get(Episode, ep_id).status = "writing"
        s.commit()
    assert (
        client.post(
            f"/episodes/{ep_id}/ask", json={"question": "¿Y ahora?", "position_s": 3}
        ).status_code
        == 409
    )


def test_ten_questions_per_episode_and_hour(client, episode, fakes):
    ep_id, _ = episode
    question = {"question": "¿Y ahora?", "position_s": 30}
    codes = [client.post(f"/episodes/{ep_id}/ask", json=question).status_code for _ in range(11)]
    assert codes[:10] == [200] * 10 and codes[10] == 429
