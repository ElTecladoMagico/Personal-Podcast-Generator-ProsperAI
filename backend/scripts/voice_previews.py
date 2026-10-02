"""Pre-record one short preview per catalog voice (run once; the MP3s are versioned).

Same settings as the episodes (dialogue, eleven_v3, creative, 1.1x) so a preview sounds like
the show. Run from backend/: uv run python -m scripts.voice_previews [--force]
"""

import argparse
import tempfile
from pathlib import Path

from app.audio import change_tempo
from app.pipeline.voice import SPEED, synthesize
from app.voices import VOICES

OUT = Path(__file__).resolve().parents[2] / "frontend" / "public" / "voices"
LINES = {
    "es": "Hola, soy {name}. Cada mañana te cuento las noticias que te importan, "
    "en tu propio podcast.",
    "en": "Hi, I'm {name}. Every morning I'll bring you the news you care about, "
    "in your own podcast.",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-record existing previews")
    force = parser.parse_args().force
    OUT.mkdir(parents=True, exist_ok=True)
    for v in VOICES:
        out = OUT / f"{v.id}.mp3"
        if out.exists() and not force:
            continue
        text = LINES[v.language].format(name=v.name)
        mp3, _ = synthesize([(text, v.id)], v.language, seed=7)
        with tempfile.NamedTemporaryFile(suffix=".mp3") as raw:
            raw.write(mp3)
            raw.flush()
            change_tempo(Path(raw.name), out, SPEED)
        print(f"{v.name:<10} {len(text)} chars → {out.name}")


if __name__ == "__main__":
    main()
