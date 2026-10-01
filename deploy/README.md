# Runbook de despliegue

- **Frontend:** Netlify (`scuda-podcast`), construido desde `main` con [`netlify.toml`](../netlify.toml). Dominio `https://podcast.scuda.es`.
- **Backend:** VPS Hetzner compartido con *instanta* (`ssh instanta`). Código en `/opt/podcast/repo`, secretos en `/opt/podcast/.env` (600), backups en `/opt/podcast/backups`. Dominio `https://api.podcast.scuda.es`, servido por el Caddy de instanta.

```
Internet ──443──▶ instanta-caddy-1 ──red instanta_default──▶ podcast-api:8000 ──▶ podcast-postgres:5432
```
Ni `podcast-api` ni `podcast-postgres` publican puertos.

## Desplegar
```bash
deploy/deploy.sh        # desde tu máquina: git pull en el VPS + build + up -d + curl /health
```
Las migraciones de Alembic se aplican solas al arrancar el contenedor. Netlify despliega solo en cada push a `main`.

## Primera instalación (ya hecha el 2026-10-01)
1. `mkdir -p /opt/podcast/backups && git clone https://github.com/ElTecladoMagico/Personal-Podcast-Generator-ProsperAI /opt/podcast/repo`
2. `/opt/podcast/.env` a partir de [`.env.production.example`](.env.production.example), con `chmod 600`. Se genera en local con una contraseña aleatoria de Postgres y se sube con `scp`; la copia local se borra.
3. `cd /opt/podcast/repo && docker compose -f deploy/docker-compose.yml up -d --build`
4. Caddy de instanta (ver abajo).
5. Cron de backups: `/etc/cron.d/podcast-backup` → `30 3 * * * root /opt/podcast/repo/deploy/backup.sh`.

## Lo que tocamos de instanta (y cómo revertirlo)
Solo su Caddyfile: se añadió al final el bloque de [`Caddyfile.snippet`](Caddyfile.snippet).
- **Añadir o cambiar:** `cp /opt/instanta/Caddyfile /opt/instanta/Caddyfile.bak-$(date +%F-%H%M)`, editar, validar el **fichero del host** con un Caddy temporal y reiniciar:
  ```bash
  docker run --rm -e DOMAIN=instanta.scuda.es -v /opt/instanta/Caddyfile:/etc/caddy/Caddyfile:ro \
    caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
  docker restart instanta-caddy-1
  ```
- **Por qué `restart` y no `caddy reload`:** el Caddyfile está montado como *bind mount de un fichero*. Si el fichero del host se reemplaza (no se edita en sitio), el contenedor sigue viendo el inode antiguo y `reload` carga la configuración vieja. Pasó el 2026-10-01: el despliegue de instanta había sustituido el fichero. `docker restart` vuelve a montarlo por ruta (corte de ~2 s; los certificados viven en el volumen `instanta_caddy_data`). **Esto también afecta a instanta.** Para comprobarlo: `stat -c %i /opt/instanta/Caddyfile` debe coincidir con `docker exec instanta-caddy-1 stat -c %i /etc/caddy/Caddyfile`.
- **Revertir:** restaurar el `.bak-*` y `docker restart instanta-caddy-1`.
- **Si instanta hace `docker compose down`**, su red `instanta_default` se recrea y `podcast-api` pierde la conexión: `cd /opt/podcast/repo && docker compose -f deploy/docker-compose.yml up -d`.

## Operación
| Tarea | Comando (en el VPS) |
|---|---|
| Logs | `docker logs -f podcast-api` |
| Estado y memoria | `docker ps`, `docker stats --no-stream` |
| Shell de Postgres | `docker exec -it podcast-postgres psql -U podcast` |
| Migración a mano | `docker exec podcast-api alembic upgrade head` |
| Backup a mano | `/opt/podcast/repo/deploy/backup.sh` (guarda 7 días) |
| Restaurar backup | `gunzip -c /opt/podcast/backups/podcast-AAAA-MM-DD.sql.gz \| docker exec -i podcast-postgres psql -U podcast podcast` (sobre una BD vacía) |
| Rollback | `cd /opt/podcast/repo && git checkout <sha> && docker compose -f deploy/docker-compose.yml up -d --build` (volver luego con `git switch main`) |

## Rotar secretos
- **Claves de OpenAI o ElevenLabs:** editar `/opt/podcast/.env` y `docker compose -f deploy/docker-compose.yml up -d` (recrea el contenedor con el nuevo entorno).
- **Contraseña de Postgres:** `ALTER USER podcast PASSWORD '…'` dentro de psql, actualizar `POSTGRES_PASSWORD` y `DATABASE_URL` en el `.env` y recrear `podcast-api`.
- **Feed tokens:** por usuario, desde la app (rama 10).

## Netlify
Variables del sitio: `VITE_CLERK_PUBLISHABLE_KEY` (la misma que `frontend/.env.local`; es pública) y `VITE_API_URL=https://api.podcast.scuda.es`. Las `VITE_*` se fijan **al compilar**: si cambian, hay que redesplegar (*Deploys → Trigger deploy*).
