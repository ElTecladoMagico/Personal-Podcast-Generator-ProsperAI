# 00 · Contratos compartidos

Lo que todas las ramas deben respetar. Cambiar algo aquí = cambiarlo en el mismo commit que el código que lo usa.

## 1. Estructura del repositorio
```
.
├── .env                      # secretos backend (NO versionado). Leído por backend y compose
├── .env.example              # plantilla versionada
├── backend/
│   ├── pyproject.toml        # uv; Python 3.13
│   ├── Dockerfile            # python:3.13-slim + ffmpeg + uv
│   ├── alembic.ini
│   ├── migrations/           # Alembic
│   ├── app/
│   │   ├── main.py           # FastAPI app, CORS, routers, lifespan (scheduler + executor)
│   │   ├── config.py         # Settings (pydantic-settings)
│   │   ├── db.py             # engine, get_session()
│   │   ├── models.py         # tablas SQLModel
│   │   ├── schemas.py        # modelos Pydantic de JSON (Preferences, Script…)
│   │   ├── auth.py           # verificación JWT Clerk, current_user, require_admin
│   │   ├── voices.py         # catálogo de voces (constante)
│   │   ├── schedule.py       # compute_next_run()
│   │   ├── llm.py            # wrapper fino de OpenAI: parse() + coste
│   │   ├── storage.py        # rutas de audio, save/delete, limpieza 30 días
│   │   ├── audio.py          # ffmpeg: concat + duración (ffprobe)
│   │   ├── sources.py        # fetch_google_news, fetch_exa, fetch_hn, resolve_google_news
│   │   ├── extract.py        # descarga + trafilatura + caché en tabla articles
│   │   ├── pipeline/
│   │   │   ├── run.py        # generate_episode(): orquesta los 6 pasos y estados
│   │   │   ├── editor.py     # paso 2
│   │   │   ├── research.py   # paso 3
│   │   │   ├── writer.py     # paso 4 (y reescritura tras verificación)
│   │   │   ├── checker.py    # paso 5
│   │   │   ├── voice.py      # paso 6 (ElevenLabs + timeline)
│   │   │   └── prompts/      # editor.md, writer.md, checker.md, ask.md
│   │   ├── jobs.py           # ThreadPoolExecutor + APScheduler + recuperación al arrancar
│   │   ├── rss.py            # construcción del feed
│   │   ├── metrics.py        # consultas del dashboard
│   │   ├── static/cover.png  # portada del RSS
│   │   └── routers/          # me.py, episodes.py, events.py, audio.py, feeds.py, voices.py, admin.py
│   ├── scripts/              # generate_episode_cli.py, seed_mock_metrics.py, voice_previews.py
│   └── tests/
├── frontend/
│   ├── package.json  vite.config.ts  index.html  components.json
│   ├── .env.local            # NO versionado (VITE_*)
│   ├── .env.example
│   ├── public/voices/*.mp3   # muestras de voz pregeneradas (rama 8)
│   └── src/
│       ├── main.tsx  App.tsx  index.css
│       ├── lib/api.ts        # fetch con token + tipos generados
│       ├── lib/api-types.ts  # generado con openapi-typescript (versionado)
│       ├── lib/i18n.tsx      # diccionario EN/ES + provider + hook
│       ├── components/ui/    # shadcn
│       ├── components/…      # por feature
│       └── pages/            # Landing, Onboarding, Home, Episode, Settings, Admin
├── deploy/
│   ├── docker-compose.yml    # producción (VPS)
│   ├── Caddyfile.snippet     # bloque a añadir al Caddy de instanta
│   └── README.md             # runbook
├── docker-compose.yml        # desarrollo local: solo Postgres
├── netlify.toml              # build del frontend (base = frontend/); en la raíz para no configurar nada en Netlify
├── docs/  solution.md  sample.mp3  README.md
```

## 2. Convenciones
- **Commits:** Conventional Commits en inglés (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`), atómicos (un cambio lógico por commit, que compile y pase los tests).
- **Ramas:** `feat/…`, `chore/…`, `spike/…`, `docs/…`. Merge a `main` con `--no-ff`.
- **Python:** 3.13, `uv`, `ruff` (lint + format), type hints, **código síncrono** (ver §10). Sin clases salvo modelos de datos.
- **TypeScript:** `strict`, componentes funcionales, sin estado global (TanStack Query para el estado del servidor).
- **Idioma:** código, commits e identificadores en inglés; documentación en español; UI en EN y ES.
- **Tests:** `pytest` para la lógica no trivial; sin mocks de red en los tests unitarios (se testean funciones puras con fixtures en `tests/fixtures/`). Los tests que llaman a APIs reales llevan `@pytest.mark.live` y no corren por defecto.

## 3. Variables de entorno

**Backend (`.env` en la raíz):**

| Variable | Ejemplo | Uso |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://podcast:podcast@localhost:5433/podcast` | SQLAlchemy |
| `OPENAI_API_KEY` | `sk-…` | LLM |
| `ELEVENLABS_API_KEY` | `…` | TTS |
| `EXA_API_KEY` | `…` | Fuente de noticias (Exa). Vacía = la fuente se salta |
| `CLERK_ISSUER` | `https://xxx.clerk.accounts.dev` | `iss` del JWT; JWKS en `{issuer}/.well-known/jwks.json` |
| `CLERK_AUTHORIZED_PARTIES` | `http://localhost:5173,https://podcast.scuda.es` | Validación del claim `azp` |
| `CORS_ORIGINS` | igual que el anterior | CORS |
| `PUBLIC_BASE_URL` | `http://localhost:8000` / `https://api.podcast.scuda.es` | URLs absolutas en RSS y audio |
| `AUDIO_DIR` | `./data/audio` / `/data/audio` | Ficheros MP3 |
| `SCHEDULER_ENABLED` | `true` | Desactivar en tests |
| `MAX_CONCURRENT_GENERATIONS` | `3` | Tamaño del pool de hilos |
| `EPISODE_MAX_MINUTES` | `2` en desarrollo, `10` en producción (20 en la rama 13 si hay créditos) | Tope para ahorrar créditos |
| `MAX_MANUAL_EPISODES_PER_DAY` | `5` | Protección de créditos frente a abusos (también los evaluadores) |

**Frontend (`frontend/.env.local`):** `VITE_CLERK_PUBLISHABLE_KEY`, `VITE_API_URL` (`http://localhost:8000`).

Puertos locales: API `8000`, Vite `5173`, Postgres `5433` (para no chocar con otros Postgres locales).

## 4. Modelo de datos (Postgres)

**`users`**

| Columna | Tipo | Notas |
|---|---|---|
| `id` | uuid PK | |
| `clerk_id` | text unique | `sub` del JWT |
| `email` | text null | claim `email` del JWT |
| `display_name` | text null | claim `name` del JWT (saludo personalizado en la UI y en el podcast) |
| `preferences` | jsonb | `Preferences` (§5). Por defecto `{}` hasta el onboarding |
| `onboarded_at` | timestamptz null | |
| `feed_token` | text unique | `secrets.token_urlsafe(32)`. RSS y URLs de audio |
| `next_run_at` | timestamptz null | Próxima generación programada (UTC). null = sin programación |
| `is_mock` | bool default false | Usuarios del seed: nunca se programan |
| `created_at` | timestamptz | |

**`episodes`**

| Columna | Tipo | Notas |
|---|---|---|
| `id` | uuid PK | |
| `user_id` | uuid FK users | índice |
| `trigger` | text | `manual` \| `scheduled` |
| `status` | text | ver §6 |
| `failed_stage` | text null | etapa en la que falló |
| `error` | text null | mensaje corto |
| `language` | text | copia de las preferencias en el momento de crear |
| `prefs_snapshot` | jsonb | `Preferences` usadas (reproducibilidad) |
| `work` | jsonb | resultados intermedios: `candidates`, `selection`, `articles`, `draft_script`, `checker_report`, `final_script`, `recording` (`{done, total}`) |
| `title`, `summary` | text null | del guion final |
| `script` | jsonb null | `Script` final con tiempos (§5) |
| `audio_path` | text null | relativo a `AUDIO_DIR` |
| `duration_s` | float null | |
| `audio_expired` | bool default false | tras la limpieza de 30 días |
| `cost` | jsonb | `{"llm_usd":…, "tts_chars":…, "tokens":{"in":…,"out":…}}` |
| `stage_timings` | jsonb | `{"fetching": 3.2, "editing": 8.1, …}` en segundos |
| `created_at`, `started_at`, `finished_at` | timestamptz | |

**`stories`** (memoria): `id` uuid, `user_id`, `episode_id`, `title`, `summary` (≤400 caracteres), `topic`, `urls` jsonb (list), `covered_at`. Índice `(user_id, covered_at)`.

**`articles`** (caché de extracción, compartida entre usuarios): `url` text PK (URL del artículo normalizada; si era de Google News, ya resuelta), `title`, `text` (texto completo o null), `image_url` (og:image, para la tarjeta del reproductor; añadida en la rama 5), `ok` bool, `fetched_at`. Se reutiliza si tiene menos de 48 h.

**`events`**: `id` bigserial, `user_id` uuid FK, `type` text, `episode_id` uuid null, `props` jsonb, `ts` timestamptz default now(). Índices `(type, ts)` y `(user_id, ts)`.

> El ADR 0003 hablaba de 4 tablas; `articles` es la caché anunciada en el ADR 0006. ADR 0003 actualizado.

## 5. Esquemas JSON (Pydantic en `app/schemas.py`)

```python
class Interest(BaseModel):
    topic: str                       # 1..80 caracteres
    why: str | None = None
    weight: int = 3                  # 1..5

class Host(BaseModel):
    name: str                        # 1..30
    voice_id: str                    # del catálogo §9

class Schedule(BaseModel):
    frequency: Literal["off", "daily", "weekdays", "weekly"] = "daily"
    time: str = "07:00"              # HH:MM local
    weekday: int | None = None       # 0=lunes, solo si weekly
    timezone: str = "Europe/Madrid"  # IANA, validado con zoneinfo

class Preferences(BaseModel):
    interests: list[Interest]        # 1..12
    avoid: list[str] = []
    sources_i_trust: list[str] = []
    language: str = "en"             # ISO 639-1: en, es, fr, de, it, pt…
    tone: Literal["casual", "serious", "nerdy"] = "casual"
    depth: Literal["headlines", "analysis"] = "analysis"
    format: Literal["solo", "duo", "debate"] = "duo"
    duration_min: Literal[5, 10, 20] = 10
    hosts: list[Host]                # 1 si solo; 2 si duo o debate
    schedule: Schedule = Schedule()
```
El **prompt de importación** (rama 8) produce el subconjunto `interests, avoid, sources_i_trust, language, tone, depth`; el resto se rellena con valores por defecto en la UI.

```python
class Candidate(BaseModel):          # paso 1
    id: str                          # "c1".."cN" (único en el episodio)
    title: str; source: str; url: str
    published_at: datetime | None; snippet: str | None
    origin: Literal["google_news", "exa", "hn"]
    interest: str                    # tema que lo trajo
    text: str | None = None          # Exa ya trae el cuerpo

class EditorPick(BaseModel):         # paso 2
    story_id: str                    # "s1".."s7"
    headline: str
    candidate_ids: list[str]         # 1+ (varios medios = misma historia)
    interest: str
    why_it_matters: str
    follow_up_of: str | None         # título de una historia de `stories` si es seguimiento
class EditorSelection(BaseModel):
    picks: list[EditorPick]          # 2..7 según la duración
    backups: list[EditorPick]        # 2 reservas por si falla la documentación

class Article(BaseModel):            # paso 3
    id: str                          # "a1".."aN"
    story_id: str; url: str; source: str; title: str
    text: str                        # recortado a 6.000 caracteres
    image_url: str | None            # og:image para la tarjeta del reproductor

class Turn(BaseModel):
    speaker: int                     # índice en hosts (0 o 1)
    text: str                        # puede llevar etiquetas de audio v3: [laughs], [curious]…
    source_ids: list[str]            # ids de Article; vacío solo en intro, outro y transiciones
    start_s: float | None = None     # rellenado en el paso 6
    end_s: float | None = None
    words: list[tuple[float, str]] | None = None   # [(start_s, palabra)] para el karaoke; None = resaltar por turno
class Chapter(BaseModel):
    story_id: str | None             # None = intro u outro
    title: str
    turns: list[Turn]
    start_s: float | None = None
    end_s: float | None = None
class Script(BaseModel):
    title: str                       # creativo, ≤70 caracteres
    summary: str                     # ≤280 caracteres, para el RSS
    chapters: list[Chapter]

class CheckIssue(BaseModel):         # paso 5
    chapter_index: int; turn_index: int
    problem: Literal["unsupported", "exaggerated", "misattributed", "outdated"]
    explanation: str
class CheckerReport(BaseModel):
    issues: list[CheckIssue]
    verdict: Literal["ok", "fix"]
```

## 6. Estados del episodio
```
queued → fetching → editing → researching → writing → verifying → recording → ready
   cualquier etapa ──error──▶ failed (failed_stage = etapa)
failed ──reintento──▶ <failed_stage> (reutiliza `work` de las etapas anteriores)
```
El frontend solo lee `status`. Etiquetas UI: queued "En cola", fetching "📡 Reuniendo noticias", editing "🧠 Eligiendo historias", researching "📚 Leyendo los artículos", writing "✍️ Escribiendo el guion", verifying "🔎 Comprobando los hechos", recording "🎙️ Grabando", ready, failed.

## 7. API (FastAPI, prefijo sin versión)

| Método | Ruta | Auth | Rama | Descripción |
|---|---|---|---|---|
| GET | `/health` | — | 1 | `{"ok": true}` |
| GET | `/me` | JWT | 1 | Usuario (upsert por `clerk_id`), preferencias, `feed_url`, `is_admin` |
| PUT | `/me/preferences` | JWT | 8 | Body `{preferences: Preferences, method?: "import"\|"manual"}`. Valida, recalcula `next_run_at`, marca `onboarded_at` |
| POST | `/me/preferences/import` | JWT | 8 | Body `{text}` → extrae y valida el JSON pegado; devuelve el `Preferences` parcial o 422 con un mensaje claro |
| POST | `/me/feed-token/rotate` | JWT | 10 | Nuevo `feed_token` |
| GET | `/voices` | — | 8 | Catálogo §9 |
| POST | `/episodes` | JWT | 7 | Crea un episodio `manual` (409 si ya hay uno en curso; 429 si supera `MAX_MANUAL_EPISODES_PER_DAY`) |
| GET | `/episodes` | JWT | 7 | Lista del usuario, ligera: `id, status, title, summary, created_at, duration_s, topics, cover_seed` |
| GET | `/episodes/{id}` | JWT | 7 | Detalle: `status`, `progress`, `script`, `sources` (sin textos), `audio_url` firmado, `prefs_snapshot.hosts`. El frontend lo consulta cada 1,5 s mientras no sea terminal |
| POST | `/episodes/{id}/retry` | JWT | 7 | Solo si `failed` |
| POST | `/episodes/{id}/ask` | JWT | 11 | `{question, position_s}` → `{turns, audio_url}` |
| POST | `/events` | JWT | 9 | `{type, episode_id?, props}`; tipos permitidos en §8 |
| GET | `/audio/{episode_id}.mp3?k=<feed_token>` | token | 6 | MP3 con soporte de `Range` |
| GET | `/audio/{episode_id}/ask-{qid}.mp3?k=…` | token | 11 | Respuesta de "Preguntar" |
| GET | `/feeds/{feed_token}.xml` | token | 10 | RSS de podcast |
| GET | `/feeds/{feed_token}/chapters/{episode_id}.json` | token | 10 | JSON Chapters (Podcasting 2.0) |
| GET | `/static/cover.png` | — | 10 | Portada del podcast |
| GET | `/admin/metrics?range=30d` | admin | 12 | JSON del dashboard |

Errores: `{"detail": "<mensaje legible>"}` con el código HTTP adecuado.

**Por qué el audio va con `?k=`:** el elemento `<audio>` y las apps de podcasts no pueden enviar `Authorization`. El `feed_token` del dueño del episodio sirve como credencial de lectura (revocable).

## 8. Eventos (`events.type`)

| Tipo | Origen | `props` |
|---|---|---|
| `user_signed_up` | backend (primer `/me`) | — |
| `onboarding_completed` | backend | `{"method": "import"\|"manual"}` |
| `preferences_updated` | backend | — |
| `episode_requested` | backend | `{"trigger"}` |
| `episode_ready` | backend | `{"duration_s", "cost", "stage_timings", "issues_found", "issues_fixed"}` |
| `episode_failed` | backend | `{"stage", "error"}` |
| `play_started` | frontend | `{"position_s"}` |
| `chapter_started` | frontend | `{"chapter_index", "story_id"}` |
| `chapter_skipped` | frontend | `{"chapter_index", "story_id", "after_s"}` |
| `listen_progress` | frontend (pausa, fin, salida de página) | `{"max_position_s", "duration_s"}` |
| `feedback` | frontend | `{"story_id", "value": "up"\|"down"}` |
| `ask_asked` | backend | `{"question", "position_s", "chapter_index", "latency_s", "chars"}` |
| `feed_download` | backend | `{"user_agent"}` |

El frontend usa `fetch(…, {keepalive: true})` para `listen_progress` al salir de la página (`sendBeacon` no permite cabeceras).

## 9. Catálogo de voces (`app/voices.py`)
Voces *premade* de ElevenLabs **verificadas el 2026-10-01** con la key del proyecto (TTS `eleven_v3` → 200). La key **no tiene `voices_read`**, así que el catálogo es una constante y las muestras se pregeneran (rama 8).

| Nombre | voice_id | Nombre | voice_id |
|---|---|---|---|
| Rachel | `21m00Tcm4TlvDq8ikWAM` | Brian | `nPczCjzI2devNBz1zQrb` |
| Sarah | `EXAVITQu4vr4xnSDxMaL` | Laura | `FGY2WhTYpPnrIDTdsKH5` |
| Adam | `pNInz6obpgDQGcFmaJgB` | Liam | `TX3LPaxmHKxFdv7VOQHJ` |
| Daniel | `onwK4e9ZLuTAKqWW03F9` | Jessica | `cgSgspJ2msm6clMCkdW9` |
| Charlotte | `XB0fDUnXU5powFXDhCwa` | George | `JBFqnCBsd6RMkjVDRZzb` |
| Matilda | `XrExE9yKIg1WjnnlVkGX` | Roger | `CwhRBWXzGAHq8TQ4Fs17` |

Los descriptores (género, tono) se completan en la rama 8 escuchando las muestras. Pareja por defecto: Sarah (0) + George (1).

## 10. Decisiones menores de implementación
- **Todo síncrono.** Endpoints `def` (FastAPI los corre en su pool de hilos). El pipeline es una función síncrona que se ejecuta en un `ThreadPoolExecutor(max_workers=MAX_CONCURRENT_GENERATIONS)`: el propio pool **es la cola y el límite de concurrencia**. Sin `async` en nuestro código. Ver ADR 0010.
- **Un único worker de uvicorn** (`--workers 1`): el programador vive en el proceso y con dos workers se duplicaría.
- **Progreso por polling**, no SSE: `EventSource` no permite la cabecera `Authorization` y polling cada 1,5 s es trivial con TanStack Query. Ver ADR 0010.
- **SDKs:** `openai` (`client.responses.parse(model=…, input=…, text_format=PydanticModel)` → `.output_parsed`, `.usage`), `elevenlabs` (`client.text_to_dialogue.convert_with_timestamps(…)`), `httpx`, `feedparser`, `trafilatura`, `apscheduler` 3.x, `pyjwt[crypto]` (`PyJWKClient`), `sqlmodel`, `alembic`, `psycopg[binary]`, `pydantic-settings`.
- **Frontend:** `@clerk/react` (Core 3), `react-router` 7, `@tanstack/react-query`, `motion` (animaciones), shadcn/ui + Tailwind 4, `recharts` (vía shadcn charts), `openapi-typescript` (dev).
- **Antelación de la programación:** `GENERATION_LEAD_MIN = 20`. `next_run_at` = hora del usuario − 20 min, para que el episodio esté listo a la hora pedida. La UI muestra `next_run_at + 20 min`.
- **Modelos LLM** (constantes en `llm.py`): `EDITOR_MODEL = "gpt-5.4-mini"`, `WRITER_MODEL = "gpt-5.4"`, `CHECKER_MODEL = "gpt-5.4"`, `ASK_MODEL = "gpt-5.4-mini"`. Disponibilidad comprobada con `/v1/models` el 2026-10-01. Precios en una tabla `PRICES` en `llm.py`, a verificar en la web de OpenAI al implementar.
- **ElevenLabs:** `model_id="eleven_v3"`, `output_format="mp3_44100_128"` (192 kbps exige plan Creator), `language_code=prefs.language`, `seed` por episodio. 1 crédito por carácter (cabecera `character-cost`).
