# Plan de implementación

Cada fase es **una rama** (`feat/…`, `chore/…`) con commits atómicos que se mergea a `main` al completarse y verificarse. El orden busca tener cuanto antes un **esqueleto desplegado de punta a punta** (*walking skeleton*) y añadir valor encima.

Estructura del repo:
```
backend/    FastAPI (Python 3.12, uv)
frontend/   React + Vite + TS + shadcn
deploy/     docker-compose.yml, bloque de Caddy, runbook
docs/       decisiones/, arquitectura/, este plan
solution.md  sample.mp3
```

| # | Rama | Entregable | Hecho cuando |
|---|---|---|---|
| 1 | `feat/backend-skeleton` | FastAPI + Postgres (compose) + SQLModel + Alembic, las 4 tablas, verificación de JWT de Clerk, `GET /health`, `GET /me` | `docker compose up` local; `/me` responde con un JWT válido |
| 2 | `feat/frontend-skeleton` | Vite + React + shadcn + Tailwind, Clerk (`<SignIn/>`), routing (`/`, `/onboarding`, `/episodes/:id`, `/admin`), cliente tipado generado desde OpenAPI | Login funcionando contra el backend local |
| 3 | `chore/deploy` | Compose de producción en `/opt/podcast` unido a `instanta_default`, bloque de Caddy `api.podcast.scuda.es`, sitio de Netlify `podcast.scuda.es`, runbook y backups con `pg_dump` | Login en producción con HTTPS |
| 4 | `spike/google-news` | Prueba de 1 h: resolver enlaces de Google News a la URL real y extraer con trafilatura | Decisión documentada en ADR 0006 |
| 5 | `feat/news-sources` | `fetch_google_news`, `fetch_guardian`, `fetch_hn` → `Candidate`; extracción de texto con caché por URL | Test: candidatos para 3 intereses en ES/EN |
| 6 | `feat/episode-pipeline` | `generate_episode()`: editor → documentación → guionista → verificador → locutores; estados, reintento por etapa, costes; audio en disco | Episodio de 1–2 min generado por CLI con transcripción sincronizada |
| 7 | `feat/generation-progress` | "Generar ahora" + SSE de progreso + UI de pasos animados | Se ve la redacción trabajando en directo |
| 8 | `feat/onboarding` | Preferencias (intereses con peso, evitar, formato, tono, duración, idioma, voces con muestra, frecuencia/hora/zona) + importar desde tu IA | Usuario nuevo → primer episodio sin tocar nada más |
| 9 | `feat/player` | Reproductor inmersivo: karaoke, tarjetas de historia, capítulos, 👍/👎/saltar, velocidad, Media Session, portada generativa; eventos a `events` | Reproducción completa registrando eventos |
| 10 | `feat/scheduler-rss` | APScheduler (episodios pendientes cada 10 min, limpieza de audios de más de 30 días), feed RSS privado con token, memoria y seguimientos | Suscripción en Apple Podcasts y episodio programado recibido |
| 11 | `feat/ask-hosts` | `POST /episodes/{id}/ask` + UI "Preguntar" en el reproductor | Pregunta respondida con voz de los presentadores |
| 12 | `feat/admin-dashboard` | `metrics.py` + `/admin` con gráficos + `seed_mock_metrics.py` | Dashboard con datos simulados y reales |
| 13 | `docs/solution` | `solution.md` (visión general, arquitectura, decisiones, tradeoffs), `sample.mp3` del mejor episodio, README con instrucciones | Entrega lista |

Calidad en cada rama: un test mínimo de la lógica no trivial (parsers, selección, verificación, consultas de métricas), sin suites exhaustivas. Revisión con `/code-review` antes de mergear.
