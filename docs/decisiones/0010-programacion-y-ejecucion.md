# 0010 · Programación y ejecución: APScheduler + tareas en el propio proceso

**Estado:** Aceptada

## Contexto
Cada usuario elige frecuencia y hora (en su zona horaria). También existe "Generar ahora". Una generación tarda 1–3 min.

## Decisión
- **APScheduler** dentro del proceso de FastAPI: un único job cada 10 min → `generate_due_episodes()`. Busca usuarios cuyo próximo episodio toca y lo encola.
- "Generar ahora" crea el episodio `queued` y lanza `generate_episode()` en segundo plano (`asyncio`).
- **Límite de concurrencia** con un semáforo (p. ej. 3 generaciones simultáneas) para no saturar las APIs ni la VPS.
- Al arrancar, los episodios que quedaron a medias (proceso reiniciado) se marcan para reintentar.
- El progreso llega al navegador por **SSE** (Server-Sent Events) leyendo `episode.status`.

## Alternativas

| Opción | Pros | Contras |
|---|---|---|
| **APScheduler + asyncio en proceso (elegida)** | Cero infraestructura. Una función que se entiende de un vistazo. | Una sola instancia: si hubiera dos, ambas programarían (evitable con un `SELECT … FOR UPDATE SKIP LOCKED`). |
| Celery/RQ + Redis | Reintentos y escalado horizontal estándar | Dos servicios más y otro modelo mental |
| Cloud Scheduler + Cloud Tasks | Gestionado, encaja con Cloud Run | Atado a GCP. Más configuración. Ver [0002](0002-despliegue.md). |
| Cron del sistema + script | Muy simple | Separa la lógica del proceso y complica "Generar ahora" |

## Revisar si
Hay más de una instancia del backend. Entonces: `FOR UPDATE SKIP LOCKED` en la tabla `episodes` (Postgres como cola) antes que añadir Redis.
