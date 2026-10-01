# Runbook de despliegue

- **Frontend:** Netlify (`scuda-podcast`), construido desde `main` con [`netlify.toml`](../netlify.toml). Dominio `https://podcast.scuda.es`.
- **Backend:** VPS Hetzner compartido con *instanta* (`ssh instanta`). Código en `/opt/podcast/repo`, secretos en `/opt/podcast/.env` (600), backups en `/opt/podcast/backups`. Dominio `https://api.podcast.scuda.es`, servido por el proxy neutral **edge** (ver abajo).

```
Internet ──443──▶ edge-caddy ──red edge──▶ podcast-api:8000 ──▶ podcast-postgres:5432
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
4. Proxy edge (ver abajo).
5. Cron de backups: `/etc/cron.d/podcast-backup` → `30 3 * * * root /opt/podcast/repo/deploy/backup.sh`.

## Proxy edge (HTTPS de todo el VPS)
Caddy no pertenece a ningún proyecto: vive en `/opt/edge` (fuente versionada en [`deploy/edge/`](edge/)). Cada proyecto une sus contenedores públicos a la red externa `edge` y **ninguno depende del compose de otro**: si instanta se redespliega o se apaga, el podcast sigue funcionando, y viceversa.

```
Internet ──443──▶ edge-caddy ──red edge──▶ podcast-api:8000
                              └──────────▶ instanta-app-1:3000, instanta-demo-store-1:4000
```

- **Creado una vez a mano** (ya hecho el 2026-10-01): `docker network create edge` y el volumen `edge_caddy_data` (con los certificados copiados del Caddy anterior). El compose de edge los declara `external`, así sobreviven a recrear el proxy.
- **Cambiar un sitio:** editar `deploy/edge/Caddyfile` → `scp deploy/edge/Caddyfile instanta:/opt/edge/` → validar → `docker restart edge-caddy` (~2 s de corte para todos los sitios):
  ```bash
  ssh instanta 'docker run --rm -v /opt/edge/Caddyfile:/etc/caddy/Caddyfile:ro caddy:2-alpine \
    caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile && docker restart edge-caddy'
  ```
  Se reinicia en lugar de `caddy reload` porque el Caddyfile es un *bind mount de un fichero*: si se sustituye el fichero, el contenedor sigue viendo el antiguo hasta reiniciar.
- **Los despliegues del podcast no tocan edge.** Los de instanta (`infra/deploy.sh` en su repo) tampoco: su compose ya no tiene Caddy y une `app` y `demo-store` a `edge`.
- **Historia:** al principio el podcast se colgaba del Caddy de instanta (un bloque añadido a su Caddyfile). Un despliegue de instanta sobrescribió ese fichero y tumbó `api.podcast.scuda.es`; por eso se sacó Caddy a este proyecto neutral (decisión del autor: el reto no debe depender de instanta).
- **Volver atrás:** `cd /opt/edge && docker compose down`, restaurar `caddy` en el compose de instanta y redesplegarlo.

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
