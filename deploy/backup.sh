#!/bin/sh
# Runs on the VPS (cron, 03:30): daily Postgres dump, keep 7 days.
set -eu
mkdir -p /opt/podcast/backups
docker exec podcast-postgres pg_dump -U podcast podcast | gzip > "/opt/podcast/backups/podcast-$(date +%F).sql.gz"
find /opt/podcast/backups -name '*.sql.gz' -mtime +7 -delete
