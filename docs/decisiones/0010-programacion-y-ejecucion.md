# 0010 · Programación y ejecución: APScheduler + tareas en el propio proceso

**Estado:** Aceptada

## Contexto
Cada usuario elige frecuencia y hora (en su zona horaria). También existe "Generar ahora". Una generación tarda 1–3 min.

## Decisión
- **APScheduler** dentro del proceso de FastAPI: un único job cada 10 min → `generate_due_episodes()`. Busca usuarios cuyo próximo episodio toca y lo encola.
- "Generar ahora" crea el episodio `queued` y lo envía a un **`ThreadPoolExecutor(max_workers=3)`**. El pipeline es código **síncrono** (más fácil de leer y depurar que `async`). El pool es a la vez la cola en memoria y el límite de concurrencia, para no saturar las APIs ni la VPS.
- Uvicorn con **un solo worker**, para que el programador no se duplique.
- Al arrancar, los episodios que quedaron a medias (proceso reiniciado) se marcan para reintentar.
- El progreso llega al navegador por **polling** (`GET /episodes/{id}` cada 1,5 s) leyendo `episode.status`.
- **Antelación:** cada ejecución programada se lanza 20 min antes de la hora del usuario, para que el episodio esté listo a esa hora.

### Revisión durante la planificación (2026-10-01): SSE → polling
El ADR proponía SSE. Se cambia a polling porque `EventSource` no permite la cabecera `Authorization` (habría que poner el JWT en la URL o usar un cliente SSE con `fetch`). Con TanStack Query, el polling es una línea (`refetchInterval`); unas 100 peticiones ligeras por generación son irrelevantes a esta escala. Revisar si hay miles de generaciones simultáneas.

## Alternativas

| Opción | Pros | Contras |
|---|---|---|
| **APScheduler + pool de hilos en proceso (elegida)** | Cero infraestructura. Una función que se entiende de un vistazo. | Una sola instancia: si hubiera dos, ambas programarían (evitable con un `SELECT … FOR UPDATE SKIP LOCKED`). |
| Celery/RQ + Redis | Reintentos y escalado horizontal estándar | Dos servicios más y otro modelo mental |
| Cloud Scheduler + Cloud Tasks | Gestionado, encaja con Cloud Run | Atado a GCP. Más configuración. Ver [0002](0002-despliegue.md). |
| Cron del sistema + script | Muy simple | Separa la lógica del proceso y complica "Generar ahora" |

## Revisar si
Hay más de una instancia del backend. Entonces: `FOR UPDATE SKIP LOCKED` en la tabla `episodes` (Postgres como cola) antes que añadir Redis.
