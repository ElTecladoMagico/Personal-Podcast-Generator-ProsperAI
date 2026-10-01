# Personal Podcast Generator ProsperAI

Your news, as a podcast made for you. Overview and architectural decisions: `solution.md` (final), [`docs/decisiones/`](docs/decisiones/README.md) (ADRs) and [`docs/plans/`](docs/plans/README.md) (implementation plans).

## Desarrollo local

Requisitos: Docker, [uv](https://docs.astral.sh/uv/), Node 22+ y ffmpeg.

```bash
docker compose up -d                 # Postgres en localhost:5433 (bases podcast y podcast_test)
cp .env.example .env                 # y rellenar las claves (OPENAI, ELEVENLABS, CLERK_ISSUER)
cd backend
uv sync
uv run alembic upgrade head          # crea las tablas
uv run fastapi dev app/main.py       # API en http://localhost:8000 (docs en /docs)
```

Comprobaciones del backend:

```bash
uv run pytest                        # usa la base podcast_test (sin red)
uv run pytest -m live                # tests contra APIs reales (Google News, Exa)
uv run python -m scripts.candidates_cli --extract 10   # candidatos reales para scripts/sample_prefs.json
uv run ruff check . && uv run ruff format --check .
```

Frontend (en otra terminal):

```bash
cd frontend
npm install
cp .env.example .env.local           # o `clerk env pull` (luego borrar CLERK_SECRET_KEY: el frontend no la usa)
npm run dev                          # http://localhost:5173
npm test && npm run lint && npm run build
npm run gen:api                      # regenera src/lib/api-types.ts (con la API en marcha)
```

### Clerk
`CLERK_ISSUER` es la *Frontend API URL* de la aplicación de Clerk. Los *custom claims* del token de sesión (`metadata`, `email`, `name`) se configuran una vez con el [CLI de Clerk](https://clerk.com/docs/cli):

```bash
clerk auth login && clerk link --app <app_id>
clerk config patch --json '{"session":{"claims":{"metadata":"{{user.public_metadata}}","email":"{{user.primary_email_address}}","name":"{{user.first_name}}"}}}'
```
