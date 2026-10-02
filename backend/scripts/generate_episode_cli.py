"""Generate one real episode end to end (network, OpenAI, ElevenLabs), synchronously.

Run from backend/:
  uv run python -m scripts.generate_episode_cli [--prefs FILE] [--minutes 2] [--format solo]
  uv run python -m scripts.generate_episode_cli --resume <episode_id>
"""

import argparse
import json
import logging
import time
import uuid
from pathlib import Path

from sqlmodel import Session, select

from app.config import settings
from app.db import engine
from app.models import Episode, User
from app.pipeline.run import generate_episode, new_episode
from app.schemas import Preferences
from app.storage import audio_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefs", default=Path(__file__).with_name("sample_prefs.json"))
    parser.add_argument("--minutes", type=int, default=2, help="cap (EPISODE_MAX_MINUTES)")
    parser.add_argument("--format", choices=["solo", "duo", "debate"])
    parser.add_argument("--language")
    parser.add_argument("--resume", type=uuid.UUID, help="retry a failed episode")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    settings.episode_max_minutes = args.minutes

    with Session(engine) as session:
        if args.resume:
            episode_id = args.resume
        else:
            data = json.loads(Path(args.prefs).read_text())
            data |= {
                k: v for k, v in {"format": args.format, "language": args.language}.items() if v
            }
            if data.get("format") == "solo":
                data["hosts"] = data["hosts"][:1]
            prefs = Preferences.model_validate(data)
            user = session.exec(select(User).where(User.clerk_id == "cli")).first()
            if not user:
                user = User(clerk_id="cli", display_name="Pedro")
                session.add(user)
            user.preferences = prefs.model_dump()
            session.commit()
            episode_id = new_episode(session, user, trigger="manual").id

    t0 = time.perf_counter()
    generate_episode(episode_id)
    elapsed = time.perf_counter() - t0

    with Session(engine) as session:
        ep = session.get(Episode, episode_id)
        print(f"\nepisode {ep.id}: {ep.status} in {elapsed:.0f}s  stages {ep.stage_timings}")
        if ep.status != "ready":
            print(f"failed at {ep.failed_stage}: {ep.error}\nretry with --resume {ep.id}")
            return
        report = ep.work.get("checker_report", {})
        print(f"cost {ep.cost}")
        print(
            f"checker: found {report.get('issues_found')} fixed {report.get('issues_fixed')} "
            f"removed {report.get('turns_removed')}"
        )
        print(f"audio {audio_file(ep.audio_path).resolve()}  ({ep.duration_s}s)")
        print(f"\n# {ep.title}\n{ep.summary}")
        hosts = [h["name"] for h in ep.prefs_snapshot["hosts"]]
        for c in ep.script["chapters"]:
            print(f"\n## {c['title']}  [{c['start_s']}–{c['end_s']}]")
            for t in c["turns"]:
                words = "w" if t["words"] else "-"
                print(f"  {t['start_s']:>6} {words} {hosts[t['speaker']]}: {t['text']}")


if __name__ == "__main__":
    main()
