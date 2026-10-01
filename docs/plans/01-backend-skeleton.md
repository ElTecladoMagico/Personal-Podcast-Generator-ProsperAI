# 01 · `feat/backend-skeleton`

**Objetivo:** API FastAPI funcionando en local contra Postgres, con las tablas del producto, autenticación Clerk verificada y `GET /me`.
**Depende de:** nada. **Prerrequisito manual:** app de Clerk creada (ver README) para tener `CLERK_ISSUER`.
**ADRs:** 0001, 0003, 0005.

## Alcance
**Incluye:** proyecto `uv`, configuración, conexión a BD, modelos y migración inicial de las 5 tablas, verificación de JWT, upsert de usuario, CORS, tests y README de arranque.
**No incluye:** pipeline, fuentes, programador ni endpoints de episodios (ramas 5–10).

## Commits (en orden)
1. **`chore(backend): scaffold FastAPI project with uv`**
   - `uv init backend --app --python 3.13`.
   - Dependencias: `fastapi[standard] sqlmodel alembic "psycopg[binary]" pydantic-settings "pyjwt[crypto]" httpx`. Dev: `pytest ruff`.
   - `pyproject.toml`: `[tool.ruff] line-length = 100`, reglas `E,F,I,UP,B`.
   - `app/main.py` con `app = FastAPI(title="Personal Podcast API")` y `GET /health → {"ok": True}`.
   - Verificación: `uv run fastapi dev app/main.py` y `curl :8000/health`.
2. **`chore: add local Postgres via docker compose and env template`**
   - `docker-compose.yml` (raíz): servicio `postgres` (`postgres:18-alpine`), puerto `5433:5432`, usuario, contraseña y BD `podcast`, volumen `pgdata`. Script de init que crea también `podcast_test`.
   - `.env.example` con todas las variables de `00-contratos §3` (valores de ejemplo, sin secretos). Añadir a `.gitignore`: `.env.local`, `data/`, `__pycache__/`, `.venv/`, `node_modules/`, `dist/`.
3. **`feat(backend): settings and database session`**
   - `config.py`: `class Settings(BaseSettings)` con los campos de §3; `model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")`. Listas separadas por comas → `list[str]` con un validador. `settings = Settings()`.
   - `db.py`: `engine = create_engine(settings.database_url, pool_pre_ping=True)` y `get_session()` como generador para `Depends`.
4. **`feat(backend): data models and initial migration`**
   - `models.py`: `User`, `Episode`, `Story`, `Article`, `Event` según §4. JSONB con `sa_column=Column(JSONB)`. Timestamps con `default_factory=lambda: datetime.now(UTC)`. `status` y `trigger` como `str` (validados en la aplicación, sin ENUM de Postgres: migraciones más simples).
   - `schemas.py`: modelos de §5 (aunque se usen después, el contrato vive aquí desde el principio).
   - `alembic init migrations`; `env.py` lee `settings.database_url` y `SQLModel.metadata`; `alembic revision --autogenerate -m "initial schema"`, revisando a mano los índices de §4.
   - Verificación: `uv run alembic upgrade head` y `\dt` en psql muestra las 5 tablas.
5. **`feat(backend): verify Clerk session tokens`**
   - `auth.py`:
     - `_jwks = PyJWKClient(f"{settings.clerk_issuer}/.well-known/jwks.json", cache_keys=True, lifespan=3600)`;
     - `verify_token(token) -> dict`: `jwt.decode(token, key, algorithms=["RS256"], issuer=settings.clerk_issuer, leeway=5, options={"require": ["exp", "iat", "sub"]})`; si existe `azp` y no está en `CLERK_AUTHORIZED_PARTIES` → error;
     - `get_claims` (dependencia: lee `Authorization: Bearer`, 401 si falta o no es válido);
     - `current_user` (upsert por `sub`);
     - `require_admin` (403 si `claims.get("metadata", {}).get("role") != "admin"`).
   - El upsert genera `feed_token = secrets.token_urlsafe(32)` y registra el evento `user_signed_up` solo al crear.
   - Test `tests/test_auth.py`: se genera un par RSA en el test y se firma un JWT; se parchea `_jwks.get_signing_key_from_jwt`. Casos: válido, expirado, `azp` no permitido, emisor incorrecto, sin `sub`.
6. **`feat(backend): GET /me`**
   - `routers/me.py`: devuelve `{id, email, display_name, preferences, onboarded: bool, is_admin: bool, feed_url, next_run_at}`, donde `feed_url = f"{PUBLIC_BASE_URL}/feeds/{feed_token}.xml"`. El email viene del claim `email` (ver la configuración de *custom claims* del README).
   - Modelo de respuesta Pydantic explícito (alimenta los tipos generados del frontend).
7. **`feat(backend): CORS and consistent error responses`**
   - `CORSMiddleware(allow_origins=settings.cors_origins, allow_headers=["Authorization", "Content-Type"], allow_methods=["*"])`.
   - Errores en formato `{"detail": …}` (el que trae FastAPI por defecto). Sin manejador global propio.
8. **`test(backend): database fixture and /me test`**
   - `tests/conftest.py`: `DATABASE_URL` apuntando a `podcast_test`; `SQLModel.metadata.create_all` y `drop_all` por sesión de tests; `TestClient` con `get_claims` sobrescrito.
   - Test: la primera llamada a `/me` crea el usuario y el evento `user_signed_up`; la segunda no duplica ninguno de los dos.
9. **`docs: backend local setup in README`**
   - Sección "Desarrollo local" del README raíz: `docker compose up -d`, `cp .env.example .env`, `cd backend && uv sync && uv run alembic upgrade head && uv run fastapi dev app/main.py`.

## Verificación final
- `uv run ruff check . && uv run ruff format --check . && uv run pytest` en verde.
- `curl localhost:8000/health` → `{"ok":true}`; `curl localhost:8000/me` → 401.
- La prueba con un JWT real de Clerk se hace en la rama 2 (frontend local).

## Criterios de aceptación
- [ ] Las 5 tablas existen tras `alembic upgrade head` en una BD vacía.
- [ ] `/me` con un token inválido → 401; con un token válido crea el usuario una sola vez.
- [ ] Ningún secreto en el repo; `.env.example` completo.

## Riesgos y notas
- **Claim de email:** el token de Clerk por defecto no trae el email; se añade en *Customize session token*: `{"metadata": "{{user.public_metadata}}", "email": "{{user.primary_email_address}}", "name": "{{user.first_name}}"}`. El upsert actualiza `email` y `display_name` en cada login si cambian.
- **Postgres 18:** la imagen `postgres:18` usa `/var/lib/postgresql` como `PGDATA` padre; montar el volumen en `/var/lib/postgresql` (no en `/data`). Verificar en la documentación de la imagen al implementar.
