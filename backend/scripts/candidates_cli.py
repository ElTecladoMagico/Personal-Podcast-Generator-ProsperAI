"""Print the step-1 candidates for a preferences file (real network). Useful to tune and demo.

Run from backend/: uv run python -m scripts.candidates_cli [--prefs FILE] [--extract 10]
"""

import argparse
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlmodel import Session

from app.db import engine
from app.extract import get_article
from app.schemas import Preferences
from app.sources import gather_candidates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefs", default=Path(__file__).with_name("sample_prefs.json"))
    parser.add_argument("--hours", type=int, default=48)
    parser.add_argument("--extract", type=int, default=0, help="try extracting the first N")
    args = parser.parse_args()

    prefs = Preferences.model_validate_json(Path(args.prefs).read_text())
    since = datetime.now(UTC) - timedelta(hours=args.hours)
    t0 = time.perf_counter()
    candidates = gather_candidates(prefs, since)
    elapsed = time.perf_counter() - t0

    for c in candidates:
        date = c.published_at.strftime("%m-%d %H:%M") if c.published_at else "     ?     "
        text = "T" if c.text else " "
        print(f"{c.id:>4} {c.origin:<11} {text} {date}  {c.interest[:18]:<18} {c.title[:70]}")
    by_source = dict(Counter(c.origin for c in candidates))
    print(f"\n{len(candidates)} candidates in {elapsed:.1f}s · by source {by_source}")

    if args.extract:
        ok, t0 = 0, time.perf_counter()
        with Session(engine) as session:
            for c in candidates[: args.extract]:
                article = get_article(c.url, session)
                ok += bool(article)
                print(f"  {'✓' if article else '✗'} {c.origin:<11} {c.source[:30]}")
        print(f"extracted {ok}/{args.extract} in {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
