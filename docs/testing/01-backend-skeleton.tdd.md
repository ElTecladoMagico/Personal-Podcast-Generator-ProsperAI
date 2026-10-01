# TDD · `feat/backend-skeleton`

**Plan:** [`docs/plans/01-backend-skeleton.md`](../plans/01-backend-skeleton.md).

## Recorridos de usuario
- Como usuario, entro con Clerk y la API me reconoce, creando mi cuenta solo la primera vez.
- Como usuario, si mi token es falso, ha caducado o se emitió para otra web, la API me rechaza.
- Como admin (`publicMetadata.role = "admin"`), la API me identifica como tal.
- Como desarrollador, unas preferencias inválidas (zona horaria, hora, número de presentadores) se rechazan antes de llegar a la BD.

## Ciclos RED → GREEN

| Tarea | RED (comando y fallo) | GREEN |
|---|---|---|
| Settings: listas separadas por comas | `uv run pytest tests/test_config.py` → `ModuleNotFoundError: app.config` | 1 passed |
| Esquemas `Preferences` | `uv run pytest tests/test_schemas.py` → `ModuleNotFoundError: app.schemas` | 15 passed |
| Verificación JWT | `uv run pytest tests/test_auth.py` → `ImportError: cannot import name 'auth'` | 8 passed |
| `GET /me` | `uv run pytest` → 4 failed (404: la ruta no existía) | Tras implementar: **3 failed por `ForeignKeyViolation`** (bug real, ver abajo) → corregido → 28 passed |
| CORS | `uv run pytest tests/test_cors.py` → 1 failed (`KeyError: access-control-allow-origin`) | 2 passed |

**Bug cazado por los tests:** al crear el usuario, el evento `user_signed_up` se insertaba antes que la fila de `users` (SQLAlchemy no ordena los INSERT por FK sin `relationship()`), y el `except IntegrityError` se tragaba el error. Corregido en `fix(backend): insert new user before its signup event`.

## Qué garantizan los tests

| # | Garantía | Test | Tipo |
|---|---|---|---|
| 1 | `CORS_ORIGINS` y `CLERK_AUTHORIZED_PARTIES` se parsean como listas separadas por comas | `test_config.py` | unidad |
| 2 | Las preferencias rellenan valores por defecto; el número de presentadores cuadra con el formato | `test_schemas.py` | unidad |
| 3 | Se rechazan zona horaria desconocida, hora fuera de rango, `weekly` sin día e intereses vacíos, demasiados o con peso fuera de 1..5 | `test_schemas.py` | unidad |
| 4 | Un JWT válido se acepta, también sin `azp` | `test_auth.py` | unidad |
| 5 | Se rechazan tokens caducados, de otro `azp`, de otro emisor, sin `sub` o firmados con otra clave | `test_auth.py` | unidad |
| 6 | `require_admin` solo deja pasar `metadata.role == "admin"` (403 en otro caso) | `test_auth.py` | unidad |
| 7 | `/me` sin token o con un token mal formado → 401 con `detail` legible | `test_me.py` | integración |
| 8 | El primer `/me` crea el usuario y un único `user_signed_up`; las siguientes llamadas no duplican nada | `test_me.py` | integración (Postgres) |
| 9 | `/me` devuelve email, nombre, `onboarded`, `is_admin` y `feed_url`, y sigue los cambios de los claims | `test_me.py` | integración (Postgres) |
| 10 | CORS: solo los orígenes configurados reciben `Access-Control-Allow-Origin` | `test_cors.py` | integración |

Además, **prueba E2E manual** con un token real de Clerk (usuario temporal creado con `clerk api` y borrado después): `/me` respondió 200 con `email`, `display_name` e `is_admin: true` verificados vía JWKS.

## Cobertura y huecos
`uv run --with pytest-cov pytest --cov=app` → **98 %** (31 tests). Sin cubrir:
- `auth.py` 65-67: la carrera entre dos primeras peticiones simultáneas (necesitaría concurrencia real; es un `rollback` y un `select`).
- `config.py` 31 y `schemas.py` 34: ramas triviales de los validadores.
- `main.py` 19: `/health`, comprobado con `curl`.
