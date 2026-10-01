# 03 · `chore/deploy`

**Objetivo:** el esqueleto (ramas 1–2) en producción: `https://podcast.scuda.es` (Netlify) y `https://api.podcast.scuda.es` (VPS), con login funcionando. A partir de aquí **cada merge se despliega**.
**Depende de:** 1, 2. **ADRs:** 0002, 0003, 0004.

## Contexto del servidor (inspeccionado el 2026-10-01)
- Hetzner CX23 "instanta" (`ssh instanta`, root), Ubuntu 26.04, Docker 29, Compose 2.40; 2 vCPU, 3,7 GiB de RAM (~1,8 GiB disponibles), 18 GB de disco libres.
- Proyecto existente en `/opt/instanta`: `instanta-caddy-1` (`caddy:2-alpine`, puertos 80/443, `Caddyfile` en `/opt/instanta/Caddyfile`, red `instanta_default`), `instanta-app-1`, `instanta-worker-1` e `instanta-postgres-1` (`127.0.0.1:5432`).
- DNS: el registro A `api.podcast.scuda.es → 2.29.26.129` ya está creado.

## Commits (en orden)
1. **`chore(backend): production Dockerfile`**:
   - `python:3.13-slim`; `apt-get install -y --no-install-recommends ffmpeg`; `COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv`; `uv sync --frozen --no-dev`.
   - `ENTRYPOINT`: `sh -c "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips='*'"`.
   - `HEALTHCHECK` con `/health`. `.dockerignore` (`.venv`, `tests`, `data`).
2. **`chore(deploy): production compose`**: `deploy/docker-compose.yml`:
   - `podcast-api`: `build: ../backend`, `container_name: podcast-api`, `env_file: /opt/podcast/.env`, volumen `podcast_audio:/data/audio`, redes `default` + `edge`, `mem_limit: 768m`, `restart: unless-stopped`, `depends_on: podcast-postgres (healthy)`. **Sin `ports`.**
   - `podcast-postgres`: `postgres:18-alpine`, `container_name: podcast-postgres`, `env_file: /opt/podcast/.env` (`POSTGRES_USER/PASSWORD/DB`), volumen `podcast_pg`, red `default`, `mem_limit: 256m`, `healthcheck: pg_isready`. **Sin `ports`.**
   - `networks.edge: {external: true, name: instanta_default}`.
3. **`chore(deploy): Caddy site block`**: `deploy/Caddyfile.snippet`:
   ```
   api.podcast.scuda.es {
   	encode zstd gzip
   	reverse_proxy podcast-api:8000
   }
   ```
4. **`chore(deploy): deploy and backup scripts`**:
   - `deploy/deploy.sh` (se ejecuta en local): `ssh instanta 'cd /opt/podcast/repo && git pull --ff-only && docker compose -f deploy/docker-compose.yml up -d --build' && curl -fsS https://api.podcast.scuda.es/health`.
   - `deploy/backup.sh`: `docker exec podcast-postgres pg_dump -U podcast podcast | gzip > /opt/podcast/backups/podcast-$(date +%F).sql.gz && find /opt/podcast/backups -mtime +7 -delete`.
5. **`docs(deploy): runbook`**: `deploy/README.md` con la primera instalación, el despliegue, los logs (`docker logs -f podcast-api`), migraciones, cómo restaurar un backup, *rollback* (`git checkout <sha>` + `up -d --build`), rotación de secretos y qué tocamos del proyecto instanta y cómo revertirlo.

## Pasos en el servidor (no son commits; **pedir confirmación al autor antes de tocar `/opt/instanta`**)
1. `ssh instanta 'mkdir -p /opt/podcast/backups && git clone https://github.com/ElTecladoMagico/Personal-Podcast-Generator-ProsperAI /opt/podcast/repo'`.
2. Crear `/opt/podcast/.env` (permisos 600) a partir de `.env.example`:
   - `DATABASE_URL=postgresql+psycopg://podcast:<pw>@podcast-postgres:5432/podcast`, `POSTGRES_USER/PASSWORD/DB`;
   - `PUBLIC_BASE_URL=https://api.podcast.scuda.es`, `AUDIO_DIR=/data/audio`, `EPISODE_MAX_MINUTES=10`, `MAX_MANUAL_EPISODES_PER_DAY=5`;
   - CORS y `azp` con `https://podcast.scuda.es` (+ `https://scuda-podcast.netlify.app`);
   - keys reales.
   Se sube con `scp` desde un fichero local temporal que se borra después.
3. `docker compose -f deploy/docker-compose.yml up -d --build` y comprobar con `docker ps` y los logs.
4. **Caddy de instanta** (con confirmación):
   - `cp /opt/instanta/Caddyfile /opt/instanta/Caddyfile.bak-$(date +%F)`;
   - añadir el snippet al final;
   - `docker exec instanta-caddy-1 caddy validate --config /etc/caddy/Caddyfile`;
   - `docker exec instanta-caddy-1 caddy reload --config /etc/caddy/Caddyfile`.
   Comprobar que el dominio de instanta sigue respondiendo.
5. Cron de backups: `/etc/cron.d/podcast-backup` → `30 3 * * * root /opt/podcast/repo/deploy/backup.sh`.
6. `curl https://api.podcast.scuda.es/health` → `{"ok":true}` con certificado válido.

## Netlify y DNS (autor + Claude)
1. El autor crea el sitio "Import from Git" → repo, nombre `scuda-podcast`. La configuración la lee de `netlify.toml`.
2. Variables en Netlify: `VITE_CLERK_PUBLISHABLE_KEY`, `VITE_API_URL=https://api.podcast.scuda.es`.
3. Dominio personalizado `podcast.scuda.es` en Netlify y DNS `CNAME podcast → scuda-podcast.netlify.app`. Netlify emite el certificado.

## Clerk: desarrollo frente a producción

| Opción | Pros | Contras |
|---|---|---|
| **Instancia de desarrollo (recomendada para empezar)** | Cero configuración; funciona en cualquier origen | Muestra la marca "Development mode"; límites de usuarios de desarrollo |
| Instancia de producción | Aspecto final profesional | Exige registros DNS de Clerk en `scuda.es` y credenciales OAuth propias de Google (Google Cloud Console) |

Decisión: desarrollo ahora; valorar pasar a producción en la rama 13 si hay tiempo (anotado como tarea pendiente). Si se hace, el CLI tiene `clerk deploy`, que guía la creación de la instancia de producción; después, repetir el `clerk config patch` de los *custom claims* con `--instance prod`.

## Verificación final
- Login en `https://podcast.scuda.es` → `Home` con el email → la fila existe en el Postgres de producción (`docker exec podcast-postgres psql …`).
- El dominio de instanta sigue funcionando tras recargar Caddy.
- `docker stats`: `podcast-api` < 300 MB y `podcast-postgres` < 100 MB en reposo.

## Criterios de aceptación
- [ ] HTTPS válido en los dos subdominios.
- [ ] Postgres y la API sin puertos públicos (`ss -tlnp` no muestra 8000 ni otro 5432).
- [ ] `deploy/deploy.sh` despliega en un comando; existe un backup tras ejecutar `backup.sh` a mano.

## Riesgos
- **Recarga de Caddy:** un error de sintaxis tumbaría instanta → siempre `caddy validate` antes de `reload`, y backup del Caddyfile.
- **RAM:** con ~1,8 GiB libres vamos holgados, pero el pipeline con 3 hilos y ffmpeg puede subir picos → `mem_limit` y vigilar con `docker stats` en la rama 6.
- **Si instanta recrea su red** (`docker compose down`), nuestro contenedor pierde la conexión → `docker compose up -d` de nuestro compose la recupera. Documentado en el runbook.

## Notas de implementación (2026-10-01)
- **Dockerfile:** usuario sin privilegios (`app`), `PATH` al venv (sin `uv run` en el arranque) y `curl` para el `HEALTHCHECK`. Imagen de ~1,2 GB por las dependencias de ffmpeg; aceptable con 18 GB libres.
- **`/opt/podcast/.env`** generado en local (contraseña de Postgres aleatoria, claves del `.env` local) a partir de `deploy/.env.production.example`, subido con `scp` y borrado en local.
- **Caddy de instanta, sorpresa:** `caddy reload` decía *config is unchanged*. El Caddyfile es un *bind mount de un fichero* y el despliegue de instanta lo había **reemplazado** (otro inode): el contenedor seguía viendo el antiguo. Solución: validar el fichero del host con un Caddy temporal y `docker restart instanta-caddy-1` (~2 s de corte; certificados conservados). Documentado en `deploy/README.md`. Afecta también a los cambios futuros de instanta.
- **Verificado:** `https://api.podcast.scuda.es/health` con Let's Encrypt; instanta sigue respondiendo 200; sin puertos publicados; `podcast-api` 95 MB y `podcast-postgres` 48 MB en reposo; backup manual creado y cron instalado.
- **Netlify:** el autor creó el sitio importando el repo (despliegue continuo desde `main`, sin builds manuales) y las variables `VITE_*`. Login E2E en `https://scuda-podcast.netlify.app` → `/me` 200 en producción → `/onboarding`.
- **DNS:** el *Target* del CNAME es un nombre de host (`scuda-podcast.netlify.app`), sin `https://`.
