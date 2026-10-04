# Personal Podcast Generator

Your news, as a podcast made for you. Tell it what you care about; every day at your time, two hosts
tell you the stories that matter, every fact tied to its source, in the web player or in your
podcast app. Built for the ProsperAI challenge.

- **Live demo:** <https://podcast.scuda.es>
- **Overview, architecture and decisions:** [`solution.md`](solution.md)
- **Best episode:** [`sample.mp3`](sample.mp3) (English, [transcript with sources](docs/sample-transcript.md)) · [`sample-es.mp3`](sample-es.mp3) (Spain Spanish, 5 min, [transcript](docs/sample-transcript-es.md))
- **Design records:** [`docs/decisiones/`](docs/decisiones/README.md) (ADRs) · [`docs/plans/`](docs/plans/README.md) (one plan per branch) · [`docs/testing/`](docs/testing) (TDD evidence) — in Spanish

## Repository

```text
backend/            FastAPI app (Python 3.13, uv)
  app/pipeline/     the 6-step newsroom: reporter, editor, research, writer, checker, voice (+ ask)
  app/routers/      REST API, private RSS feeds, audio, admin metrics
  app/metrics.py    dashboard metrics (SQL)
  migrations/       Alembic
  scripts/          CLIs: generate an episode, seed mock metrics, cover art…
  tests/            pytest (real Postgres, external APIs faked)
frontend/           React + Vite + TypeScript + shadcn/ui
  src/pages/        Landing, Home, Onboarding, Episode (player), Settings, Admin
deploy/             production compose, edge proxy, deploy and backup scripts (runbook inside)
docs/               ADRs, plans, TDD reports, architecture diagram, screenshots
```

## Run it locally

Requirements: Docker, [uv](https://docs.astral.sh/uv/), Node 22+ and ffmpeg. You need an OpenAI key,
an ElevenLabs key, an Exa key and a Clerk application.

```bash
docker compose up -d                 # Postgres on localhost:5433 (databases podcast and podcast_test)
cp .env.example .env                 # fill in the keys (OPENAI, ELEVENLABS, EXA, CLERK_ISSUER)
cd backend
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py       # API on http://localhost:8000 (docs at /docs)
```

In another terminal:

```bash
cd frontend
npm install
cp .env.example .env.local           # VITE_CLERK_PUBLISHABLE_KEY (or `clerk env pull`)
npm run dev                          # http://localhost:5173
```

> The scheduler runs inside the API (`SCHEDULER_ENABLED=true`): local users with a schedule get real
> episodes every day. `EPISODE_MAX_MINUTES=2` keeps local episodes short and cheap.

**Clerk.** `CLERK_ISSUER` is the application's *Frontend API URL*. The session token needs three
custom claims, set once with the [Clerk CLI](https://clerk.com/docs/cli):

```bash
clerk auth login && clerk link --app <app_id>
clerk config patch --json '{"session":{"claims":{"metadata":"{{user.public_metadata}}","email":"{{user.primary_email_address}}","name":"{{user.first_name}}"}}}'
```

To open the dashboard (`/admin`), give a user `{"role": "admin"}` in its public metadata (Clerk
dashboard → Users → Metadata, or `clerk api /users/<id>/metadata -X PATCH -d '{"public_metadata":{"role":"admin"}}'`).

## Useful commands

```bash
# backend/
uv run pytest                                        # 163 tests, no network
uv run pytest -m live                                # against the real news APIs
uv run ruff check . && uv run ruff format --check .
uv run python -m scripts.generate_episode_cli --minutes 10 --prefs scripts/sample_prefs_en.json
uv run python -m scripts.seed_mock_metrics           # 200 simulated listeners × 90 days for /admin
uv run python -m scripts.candidates_cli --extract 10 # step 1 only: today's candidates

# frontend/
npm test && npm run lint && npm run build
npm run gen:api                                      # regenerate API types (with the API running)
```

## Deploy

Frontend: Netlify builds `main` on every push. Backend: `deploy/deploy.sh` (pull on the VPS, rebuild,
migrate, health check). Details and first-time setup in [`deploy/README.md`](deploy/README.md).
