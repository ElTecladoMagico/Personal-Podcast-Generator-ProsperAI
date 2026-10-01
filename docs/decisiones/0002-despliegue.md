# 0002 · Despliegue: Netlify (frontend) + VPS con docker compose (backend)

**Estado:** Aceptada

## Contexto
Disponemos de Netlify, Google Cloud Run (activo) y una VPS. La generación de un episodio tarda 1–3 min y hay un programador que debe despertarse cada pocos minutos. Los evaluadores probarán el producto en una URL pública.

## Decisión
- **Frontend:** build estático de Vite en **Netlify** (CDN, HTTPS y deploy por git gratis).
- **Backend:** **VPS** con `docker compose`: `caddy` (HTTPS automático), `api` (FastAPI + programador + pipeline en el mismo proceso), `postgres` y un volumen para audio.

## Alternativas

| Opción | Pros | Contras |
|---|---|---|
| **VPS + docker compose (elegida)** | Un proceso siempre vivo: el programador en proceso y las tareas en segundo plano funcionan sin infraestructura extra. Disco persistente para BD y audio. Coste 0 (ya la tenemos). `docker compose up` reproduce producción en local. | Somos responsables de backups, actualizaciones y seguridad del host. No escala horizontalmente. Necesita dominio o subdominio para TLS (vale `sslip.io`). |
| Cloud Run | Gestionado, escala a cero, capa gratuita generosa | Contenedores efímeros y sin estado: obliga a BD externa, almacenamiento externo (GCS/R2), Cloud Scheduler para el cron y una solución para el trabajo en segundo plano (por defecto la CPU solo está asignada durante la petición; harían falta Cloud Tasks o Cloud Run Jobs). Son 3–4 piezas más que explicar. |
| Railway | DX excelente, volúmenes, Postgres en un clic | **No es gratis de forma sostenida**: prueba de 5 $ durante 30 días, luego un plan Free de 1 $/mes con 0,5 GB de RAM (insuficiente) o Hobby de 5 $/mes. Ventaja real solo frente a gestionar la VPS, que ya tenemos. |
| Vercel / Netlify Functions para el backend | Mismo proveedor que el frontend | Límites de duración de función frente a generaciones de minutos. Sin proceso persistente ni disco. |

## Concreción
- **Servidor:** VPS Hetzner CX23 existente (2 vCPU, 4 GB RAM, 40 GB disco, Helsinki), **compartida con otro proyecto** para no pagar más.
- **Dominio:** `scuda.es`. Subdominios previstos: `podcast.scuda.es` → Netlify (CNAME) y `api.podcast.scuda.es` → VPS (registro A).
- **Estado del servidor (inspeccionado el 2026-10-01):** Ubuntu 26.04, Docker 29 + Compose 2.40. Ocupa 19 de 38 GB de disco y quedan ~1,8 GiB de RAM disponible. El proyecto `instanta` (compose en `/opt/instanta`) corre `caddy:2-alpine` en 80/443, `app`, `worker` y `postgres:18` (solo en `127.0.0.1:5432`).
- **Convivencia: un solo Caddy, enrutado por subdominio.** No levantamos otro proxy ni tocamos los puertos 80/443:
  - nuestro compose vive en `/opt/podcast`;
  - el contenedor `podcast-api` **no publica puertos** y se une a la red externa `instanta_default`;
  - añadimos al `Caddyfile` de instanta un bloque `api.podcast.scuda.es { reverse_proxy podcast-api:8000 }` y recargamos Caddy (`caddy reload`, sin cortar el otro proyecto). Caddy obtiene el certificado TLS automáticamente.
- **Postgres propio** (contenedor `podcast-postgres` en nuestra red interna, sin puertos expuestos), no el de instanta. Cuesta unos 100 MB de RAM, pero los proyectos quedan desacoplados: backups, versiones y reinicios independientes.
- **Presupuesto de recursos:** Postgres ~100 MB + API ~300 MB en reposo. La generación hace sobre todo esperas de red (poca CPU). `mem_limit` en el compose para no afectar a instanta.
- **Tradeoff aceptado:** dependemos del Caddy y de la red de instanta. Si ese compose se baja, nuestra API deja de ser accesible desde fuera (aunque sigue funcionando). Está documentado en el runbook de despliegue.

## Consecuencias
- El "dolor de cabeza" que ahorraría Railway (TLS, reinicios, logs) lo cubren Caddy y `restart: unless-stopped`.
- Backups: `pg_dump` diario por cron del host hacia el disco o R2. Lo documentaremos.
- **Camino de escalado** (para `solution.md`): Cloud Run + Postgres gestionado (Neon o Cloud SQL) + R2/GCS + Cloud Scheduler + Cloud Tasks. Hemos hecho el código portable a propósito: `DATABASE_URL` y una función `save_audio()` son los únicos puntos de cambio.

## Revisar si
Hace falta más de una instancia del backend, o la VPS se queda corta de CPU/RAM.
